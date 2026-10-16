
import boto3
import json

from diagnostic_tools import (
    get_cpu_metrics,
    get_database_metrics,
    analyze_logs,
    get_recent_deployments,
)

from llm_tool_schema import (
    CPU_TOOL_CONFIG,
    DATABASE_TOOL_CONFIG,
    LOG_TOOL_CONFIG,
    DEPLOYMENT_TOOL_CONFIG,
)


REGION = "ap-southeast-2"
MODEL_ID = "amazon.nova-lite-v1:0"


TOOL_CONFIG = {
    "tools": (
        CPU_TOOL_CONFIG["tools"]
        + DATABASE_TOOL_CONFIG["tools"]
        + LOG_TOOL_CONFIG["tools"]
        + DEPLOYMENT_TOOL_CONFIG["tools"]
    )
}


def run_rule_based_fallback():
    """Run local diagnostics without calling the LLM."""
    print("\nRunning rule-based fallback...")

    try:
        with open("data/incident.json", "r", encoding="utf-8") as file:
            incident = json.load(file)

        cpu_result = get_cpu_metrics(incident)
        database_result = get_database_metrics(incident)
        logs_result = analyze_logs(incident.get("logs", []))

        print("CPU diagnostic:", cpu_result)
        print("Database diagnostic:", database_result)
        print("Log analysis:", logs_result)

    except (OSError, json.JSONDecodeError, ValueError, TypeError) as error:
        print("Fallback could not complete:", error)


def parse_diagnosis(raw_text):
    """Extract and validate the model's JSON diagnosis."""
    text = raw_text.strip()

    # Remove optional XML-like wrappers.
    if "<diagnosis>" in text and "</diagnosis>" in text:
        text = text.split("<diagnosis>", 1)[1]
        text = text.split("</diagnosis>", 1)[0].strip()

    if "<response>" in text and "</response>" in text:
        text = text.split("<response>", 1)[1]
        text = text.split("</response>", 1)[0].strip()

    # Handle JSON enclosed in Markdown code fences.
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    diagnosis = json.loads(text)

    required_fields = {
        "probable_root_cause",
        "supporting_evidence",
        "uncertainty",
        "confidence",
    }

    if not isinstance(diagnosis, dict):
        raise ValueError("Diagnosis must be a JSON object.")

    missing = required_fields - diagnosis.keys()
    if missing:
        raise ValueError(
            f"Diagnosis is missing fields: {sorted(missing)}"
        )

    if not isinstance(diagnosis["probable_root_cause"], str):
        raise ValueError("probable_root_cause must be a string.")

    if not isinstance(diagnosis["supporting_evidence"], (str, list)):
        raise ValueError("supporting_evidence must be a string or list.")

    if not isinstance(diagnosis["uncertainty"], str):
        raise ValueError("uncertainty must be a string.")

    if diagnosis["confidence"].lower() not in {
        "low", "medium", "high"
    }:
        raise ValueError("confidence must be low, medium, or high.")

    return diagnosis


def evaluate_diagnosis(diagnosis, expected_root_cause):
    """Compare the agent's diagnosis with the expected root cause."""
    predicted = diagnosis["probable_root_cause"].strip().lower()
    expected = expected_root_cause.strip().lower()

    correct = predicted == expected

    result = {
        "predicted_root_cause": diagnosis["probable_root_cause"],
        "expected_root_cause": expected_root_cause,
        "correct": correct,
    }

    return result


def main():
    # Step 1: Load incident data.
    try:
        with open("data/incident.json", "r", encoding="utf-8") as file:
            incident = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not load incident data: {error}")
        return

    # Never expose the expected evaluation label to the agent.
    agent_incident = {
        "incident_id": incident.get("incident_id"),
        "incident_type": incident.get("incident_type"),
        "cpu_usage_percent": incident.get("cpu_usage_percent"),
        "database_connections": incident.get("database_connections"),
        "recent_deployment": incident.get("recent_deployment"),
        "logs": incident.get("logs", []),
    }

    client = boto3.client("bedrock-runtime", region_name=REGION)

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "text": (
                        "You are an application incident investigator. "
"Use diagnostic tools to investigate the incident. "
"Call each relevant tool with the appropriate input. "
"Do not repeat a tool with identical input when its "
"result is already available. "
"Use tool results as evidence, and distinguish direct "
"observations from hypotheses. "
"Do not claim that a recent deployment caused an incident "
"based only on the fact that a deployment occurred. "
"Do not claim a diagnostic was run unless its result "
"is available. "
"When evidence is incomplete or competing explanations "
"remain possible, explicitly state the uncertainty and "
"use medium or low confidence. "
"Use high confidence only when multiple independent "
"pieces of evidence strongly support the same cause. "
"Return a JSON diagnosis with exactly these fields: "
'"probable_root_cause", "supporting_evidence", '
'"uncertainty", and "confidence". '
"Supporting evidence must be based on the incident data "
"or actual diagnostic results. "
"If the cause cannot be established, say so explicitly.\n\n"
"Incident data:\n"

                        + json.dumps(agent_incident)
                    )
                }
            ],
        }
    ]

    evidence = []
    max_model_requests = 6

    # Step 2: Let the model investigate over multiple rounds.
    for request_number in range(1, max_model_requests + 1):
        try:
            response = client.converse(
                modelId=MODEL_ID,
                messages=messages,
                inferenceConfig={
                    "maxTokens": 400,
                    "temperature": 0,
                },
                toolConfig={
                    **TOOL_CONFIG,
                    "toolChoice": {"auto": {}},
                },
            )
        except Exception as error:
            print(f"Bedrock request failed: {error}")
            run_rule_based_fallback()
            return

        assistant_message = response["output"]["message"]
        tool_uses = [
            block["toolUse"]
            for block in assistant_message["content"]
            if "toolUse" in block
        ]

        # No more tool calls: the model has produced its diagnosis.
        if not tool_uses:
            print("\n=== Investigation Diagnosis ===")
            for block in assistant_message["content"]:
              if "text" in block:
                raw_text = block["text"].strip()

                if "<thinking>" in raw_text and "</thinking>" in raw_text:
                  raw_text = (
                raw_text.split("<thinking>", 1)[0]
                + raw_text.split("</thinking>", 1)[1]
            ).strip()

                try:
                  diagnosis = parse_diagnosis(raw_text)
                except (json.JSONDecodeError, ValueError) as error:
                  print("Invalid diagnosis format:", error)
                  print("Raw model response:", raw_text)
                  continue

                print(json.dumps(diagnosis, indent=2))


            print(f"\nDiagnostic results collected: {len(evidence)}")
            return

        # Step 3: Execute every tool requested in this round.
        print(f"\nInvestigation round {request_number}")

        tool_results = []

        for tool_use in tool_uses:
            tool_name = tool_use["name"]
            tool_input = tool_use["input"]

            print(f"Running tool: {tool_name}")
            try:
                if tool_name == "get_cpu_metrics":
                    result = get_cpu_metrics(tool_input["incident"])

                elif tool_name == "get_database_metrics":
                    result = get_database_metrics(tool_input["incident"])

                elif tool_name == "analyze_logs":
                    result = analyze_logs(tool_input["logs"])

                elif tool_name == "get_recent_deployments":
                    result = get_recent_deployments(tool_input["incident"])

                else:
                    result = {
                        "status": "error",
                        "tool": tool_name,
                        "data": {},
                        "message": f"Unknown tool: {tool_name}",
                    }
            except (KeyError, ValueError, TypeError) as error:
                result = {
                    "status": "error",
                    "message": str(error),
                }

            evidence.append({
                "tool": tool_name,
                "result": result,
            })

            print("Diagnostic result:", result)

            tool_results.append({
                "toolResult": {
                    "toolUseId": tool_use["toolUseId"],
                    "content": [{"json": result}],
                }
            })

        # Step 4: Send tool calls and their results back to the model.
        messages.extend([
            {
                "role": "assistant",
                "content": assistant_message["content"],
            },
            {
                "role": "user",
                "content": tool_results,
            },
        ])

    print(
        "\nInvestigation stopped at the model-request limit. "
        "The agent did not produce a final diagnosis."
    )
    print("Evidence collected:", json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
