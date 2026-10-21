
import boto3
import json
import time

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


def run_rule_based_fallback(incident=None):
    """Run local diagnostics and return their results."""
    print("\nRunning rule-based baseline...")

    try:
        if incident is None:
            with open("data/incident.json", "r", encoding="utf-8") as file:
                incident = json.load(file)

        cpu_result = get_cpu_metrics(incident)
        database_result = get_database_metrics(incident)
        logs_result = analyze_logs(incident.get("logs", []))

        print("CPU diagnostic:", cpu_result)
        print("Database diagnostic:", database_result)
        print("Log analysis:", logs_result)

        cpu_high = (
            cpu_result.get("status") == "success"
            and cpu_result.get("data", {}).get("assessment") == "high"
        )
        db_high = (
            database_result.get("status") == "success"
            and database_result.get("data", {}).get("assessment") == "high"
        )

        tools_succeeded = (
            cpu_result.get("status") == "success"
            and database_result.get("status") == "success"
            and logs_result.get("status") == "success"
        )

        log_findings = logs_result.get("data", {}).get("findings", [])
        log_issue = bool(log_findings)

        if not tools_succeeded:
            cause = "Inconclusive"
            confidence = "Low"
            uncertainty = (
                "One or more diagnostic tools failed; evidence is incomplete."
            )
        elif cpu_high and db_high:
            cause = "Combined CPU and database connection pressure"
            confidence = "Medium"
            uncertainty = (
                "Both resources show pressure; the initiating cause is unknown."
            )
        elif cpu_high:
            cause = "Application or workload CPU saturation"
            confidence = "Medium"
            uncertainty = (
                "High CPU is observed, but its underlying cause is not proven."
            )
        elif db_high:
            cause = "Database connection pressure"
            confidence = "Medium"
            uncertainty = (
                "Database connection pressure is observed, but its cause is unknown."
            )
        elif not log_issue:
            cause = "No confirmed resource-pressure cause"
            confidence = "Medium"
            uncertainty = (
                "The available checks did not detect a resource-pressure cause."
            )
        else:
            cause = "Inconclusive"
            confidence = "Low"
            uncertainty = (
                "Logs indicate a possible issue, but its cause is unclear."
            )

        diagnosis = {
            "probable_root_cause": cause,
            "supporting_evidence": {
                "cpu": cpu_result,
                "database": database_result,
                "logs": logs_result,
            },
            "uncertainty": uncertainty,
            "confidence": confidence,
        }

        print("\n=== Rule-Based Baseline Diagnosis ===")
        print(json.dumps(diagnosis, indent=2))
        return diagnosis

    except (OSError, json.JSONDecodeError, ValueError, TypeError) as error:
        print("Baseline could not complete:", error)
        return None

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

    if not isinstance(diagnosis, dict):
        raise ValueError("Diagnosis must be a JSON object.")

    required_fields = {
        "probable_root_cause",
        "supporting_evidence",
        "uncertainty",
        "confidence",
    }

    missing = required_fields - diagnosis.keys()
    if missing:
        raise ValueError(
            f"Diagnosis is missing fields: {sorted(missing)}"
        )

    if not isinstance(diagnosis["probable_root_cause"], str):
        raise ValueError("probable_root_cause must be a string.")

    if not isinstance(
        diagnosis["supporting_evidence"], (str, list, dict)
    ):
        raise ValueError(
            "supporting_evidence must be a string, list, or object."
        )

    if not isinstance(diagnosis["uncertainty"], str):
        raise ValueError("uncertainty must be a string.")

    if (
        not isinstance(diagnosis["confidence"], str)
        or diagnosis["confidence"].lower() not in {"low", "medium", "high"}
    ):
        raise ValueError("confidence must be low, medium, or high.")

    return diagnosis


def normalize_root_cause(root_cause):
    """Map diagnosis wording to a consistent evaluation category."""
    text = root_cause.strip().lower().replace("-", "_")

    if any(term in text for term in (
        "database connection pressure",
        "database_pressure",
        "connection pressure",
    )):
        return "database_connection_pressure"

    if any(term in text for term in (
        "combined cpu",
        "cpu and database",
        "combined resource",
    )):
        return "combined_resource_pressure"

    if any(term in text for term in (
        "application overload",
        "application_overload",
        "cpu saturation",
        "workload cpu",
        "high cpu",
    )):
        return "possible_application_overload"

    if any(term in text for term in (
        "inconclusive",
        "cannot be established",
        "cause is unclear",
        "unknown cause",
    )):
        return "inconclusive"

    if any(term in text for term in (
        "no confirmed resource-pressure cause",
        "normal operation",
        "no major issue",
    )):
        return "no_confirmed_resource_pressure"

    if "deployment" in text:
        return "deployment_related_issue"

    return "unclassified"


def evaluate_diagnosis(diagnosis, expected_root_cause):
    """Compare normalized diagnosis categories."""
    predicted_category = normalize_root_cause(
        diagnosis["probable_root_cause"]
    )
    expected_category = normalize_root_cause(expected_root_cause)

    return {
        "predicted_root_cause": diagnosis["probable_root_cause"],
        "expected_root_cause": expected_root_cause,
        "predicted_category": predicted_category,
        "expected_category": expected_category,
        "correct": (
            predicted_category != "unclassified"
            and predicted_category == expected_category
        ),
    }

def main():
    # Step 1: Load incident data.
    try:
        with open("data/incident.json", "r", encoding="utf-8") as file:
            incident = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not load incident data: {error}")
        return

    expected_root_cause = incident.get("expected_root_cause")
    agent_start = time.perf_counter()

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
                        "Prioritize direct diagnostic evidence over temporal correlations. "
"When CPU is assessed as high and logs show timeouts or increased "
"response time, explicitly consider application or workload CPU "
"saturation as a leading hypothesis. "
"A detected recent deployment is contextual evidence only and "
"must not be preferred without evidence connecting it to the incident. "
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
            print("Agent investigation failed; running baseline only.")
            run_rule_based_fallback(incident)
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

            diagnosis = None

            for block in assistant_message["content"]:
                if "text" not in block:
                    continue

                raw_text = block["text"].strip()

                if "<thinking>" in raw_text and "</thinking>" in raw_text:
                    raw_text = (
                        raw_text.split("<thinking>", 1)[0]
                        + raw_text.split("</thinking>", 1)[1]
                    ).strip()

                try:
                    diagnosis = parse_diagnosis(raw_text)
                    break
                except (json.JSONDecodeError, ValueError) as error:
                    print("Invalid diagnosis format:", error)
                    print("Raw model response:", raw_text)

            if diagnosis is None:
                print("The agent did not produce a valid diagnosis.")
                print(f"Diagnostic results collected: {len(evidence)}")
                return

            print(json.dumps(diagnosis, indent=2))

            # Evaluate the agent against the expected label.
            agent_elapsed = time.perf_counter() - agent_start

            print("\n=== Agent Evaluation ===")
            if expected_root_cause:
                agent_evaluation = evaluate_diagnosis(
                    diagnosis, expected_root_cause
                )
                print(json.dumps(agent_evaluation, indent=2))
            else:
                print("Evaluation skipped: expected label is missing.")

            # Run the baseline on the exact same incident.
            baseline_start = time.perf_counter()
            baseline_diagnosis = run_rule_based_fallback(incident)
            baseline_elapsed = time.perf_counter() - baseline_start

            print("\n=== Evaluation Summary ===")
            print(f"Agent investigation time: {agent_elapsed:.3f} seconds")

            if baseline_diagnosis and expected_root_cause:
                baseline_evaluation = evaluate_diagnosis(
                    baseline_diagnosis, expected_root_cause
                )
                print(
                    "Baseline evaluation:",
                    json.dumps(baseline_evaluation, indent=2),
                )
                print(
                    f"Baseline diagnostic time: "
                    f"{baseline_elapsed:.3f} seconds"
                )
            elif not baseline_diagnosis:
                print("Baseline evaluation unavailable.")

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
