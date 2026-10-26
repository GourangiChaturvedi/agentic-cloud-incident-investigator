import boto3
import copy
import json
import time
import re

from diagnostic_tools import (
    get_cpu_metrics,
    get_live_cpu_metrics,
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
    """Run local simulated diagnostics and return a rule-based diagnosis."""
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

        tools_succeeded = all(
            result.get("status") == "success"
            for result in (cpu_result, database_result, logs_result)
        )

        log_findings = logs_result.get("data", {}).get("findings", [])

        log_issue = any(
            not (
                isinstance(item, str)
                and "no matching" in item.lower()
            )
            for item in log_findings
        )

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

    if "<diagnosis>" in text and "</diagnosis>" in text:
        text = text.split("<diagnosis>", 1)[1]
        text = text.split("</diagnosis>", 1)[0].strip()

    if "<response>" in text and "</response>" in text:
        text = text.split("<response>", 1)[1]
        text = text.split("</response>", 1)[0].strip()

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
        raise ValueError(f"Diagnosis is missing fields: {sorted(missing)}")

    if not isinstance(diagnosis["probable_root_cause"], str):
        raise ValueError("probable_root_cause must be a string.")

    if not isinstance(diagnosis["supporting_evidence"], (str, list, dict)):
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
    """
    Normalize equivalent diagnosis wording into evaluation categories.

    Combined resource pressure is checked before individual resources.
    Matching is based on the predicted root-cause text, not the expected label.
    """
    if not isinstance(root_cause, str) or not root_cause.strip():
        return "unclassified"

    text = root_cause.lower().replace("-", " ").replace("_", " ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = " ".join(text.split())

    # Combined pressure must be checked before database-only or CPU-only.
    combined_patterns = (
        "combined cpu",
        "combined resource",
        "combined pressure",
        "cpu and database",
        "database and cpu",
        "both cpu and database",
        "cpu plus database",
        "cpu together with database",
    )

    if any(term in text for term in combined_patterns):
        return "combined_resource_pressure"

    # Database connection pressure, including common paraphrases.
    database_patterns = (
        "database connection pressure",
        "database connection limit",
        "connection limit",
        "database connections limit",
        "database connection saturation",
        "database connections saturated",
        "database connections exhausted",
        "database connection exhaustion",
        "database connection pool exhausted",
        "database connection pool saturation",
        "database connections reached",
        "database connections are high",
        "database pressure",
        "database overload",
        "connection pressure",
        "connection pool exhausted",
        "connection pool saturation",
        "too many database connections",
        "too many connections",
        "connection limit being reached",
        "connection limit reached",
    )

    if any(term in text for term in database_patterns):
        return "database_connection_pressure"

    # Application or CPU overload.
    cpu_patterns = (
        "application overload",
        "application saturation",
        "application or workload cpu saturation",
        "workload cpu saturation",
        "cpu saturation",
        "high cpu",
        "cpu overload",
        "cpu utilization overload",
        "cpu usage is high",
        "cpu utilization is high",
        "application cpu pressure",
    )

    if any(term in text for term in cpu_patterns):
        return "possible_application_overload"

    # No significant resource-pressure cause detected.
    normal_patterns = (
        "no confirmed resource pressure cause",
        "no confirmed resource pressure",
        "no major issue",
        "normal operation",
        "no significant issue",
        "no resource pressure",
        "resources are normal",
        "normal resource utilization",
    )

    if any(term in text for term in normal_patterns):
        return "no_confirmed_resource_pressure"

    # Insufficient evidence or an unresolved cause.
    inconclusive_patterns = (
        "inconclusive",
        "cannot be established",
        "cannot be determined",
        "cause is unclear",
        "unclear cause",
        "unknown cause",
        "undetermined cause",
        "insufficient evidence",
        "insufficient information",
        "unable to determine",
        "unable to establish",
    )

    if any(term in text for term in inconclusive_patterns):
        return "inconclusive"

    if "deployment" in text:
        return "deployment_related_issue"

    return "unclassified"


def evaluate_diagnosis(diagnosis, expected_root_cause):
    """Compare normalized diagnosis categories."""
    if not isinstance(diagnosis, dict):
        diagnosis = {}

    predicted_root_cause = diagnosis.get("probable_root_cause", "")

    predicted_category = normalize_root_cause(predicted_root_cause)
    expected_category = normalize_root_cause(expected_root_cause)

    return {
        "predicted_root_cause": predicted_root_cause or None,
        "expected_root_cause": expected_root_cause,
        "predicted_category": predicted_category,
        "expected_category": expected_category,
        "correct": (
            predicted_category != "unclassified"
            and predicted_category == expected_category
        ),
    }


def investigate_incident(
    incident,
    client=None,
    max_model_requests=6,
    evaluation_mode=False,
):
    """
    Investigate an incident without executing remediation.

    Default mode:
        Uses live AWS CPU telemetry.

    Evaluation mode:
        Uses the supplied simulated CPU fixture so the agent and baseline
        can be compared on the same incident inputs.

    The expected root-cause label is never sent to the agent.
    """
    if not isinstance(incident, dict):
        return {
            "status": "error",
            "source": "none",
            "diagnosis": None,
            "evidence": [],
            "message": "Incident must be supplied as a dictionary.",
        }

    started_at = time.perf_counter()
    evidence = []

    agent_incident = {
        "incident_id": incident.get("incident_id"),
        "incident_type": incident.get("incident_type"),
        "cpu_usage_percent": incident.get("cpu_usage_percent"),
        "database_connections": incident.get("database_connections"),
        "recent_deployment": incident.get("recent_deployment"),
        "logs": incident.get("logs", []),
    }

    active_tool_config = copy.deepcopy(TOOL_CONFIG)

    if evaluation_mode:
        for tool in active_tool_config["tools"]:
            spec = tool.get("toolSpec", {})

            if spec.get("name") == "get_cpu_metrics":
                spec["description"] = (
                    "Read the simulated CPU utilization for the supplied "
                    "evaluation incident. The value is fixture data, not "
                    "live AWS telemetry. Use this tool when investigating "
                    "CPU-related incidents in controlled evaluation mode."
                )

    def fallback_result(reason):
        """Return an explicitly labeled simulated baseline result."""
        fallback_diagnosis = run_rule_based_fallback(incident)
        elapsed = time.perf_counter() - started_at

        if fallback_diagnosis is None:
            return {
                "status": "error",
                "source": "none",
                "diagnosis": None,
                "evidence": evidence,
                "message": f"{reason} Rule-based fallback also failed.",
                "elapsed_seconds": round(elapsed, 3),
                "tool_call_count": len(evidence),
            }

        return {
            "status": "fallback",
            "source": "simulated_rule_based_fallback",
            "diagnosis": fallback_diagnosis,
            "evidence": evidence,
            "message": (
                f"{reason} The returned diagnosis uses simulated incident "
                "data and is not a successful AI-agent diagnosis."
            ),
            "elapsed_seconds": round(elapsed, 3),
            "tool_call_count": len(evidence),
        }

    try:
        if client is None:
            client = boto3.client(
                "bedrock-runtime",
                region_name=REGION,
            )
    except Exception as error:
        return fallback_result(
            f"Could not initialize the Bedrock client: {error}"
        )

    if evaluation_mode:
        system_prompt = (
            "You are an application incident investigator operating in "
            "CONTROLLED SIMULATED EVALUATION MODE. All incident measurements, "
            "logs, database connection counts, and deployment information "
            "are simulated fixture data. Do not query or claim to have "
            "queried live AWS telemetry. The get_cpu_metrics tool returns "
            "the CPU value for this supplied simulated incident. "
            "Use the available diagnostic tools and base your diagnosis "
            "only on their results and the supplied incident context. "
            "Do not assume that a recent deployment proves causation. "
            "Distinguish direct observations from hypotheses. "
            "When evidence is incomplete or competing explanations remain, "
            "state uncertainty and use medium or low confidence. "
            "Use high confidence only when multiple independent pieces "
            "of evidence strongly support the same cause. "
            "The expected answer is withheld; determine the diagnosis "
            "independently. Do not invent evidence or claim a tool was "
            "called unless its result is available. "
            "Return only a valid JSON object with exactly these fields: "
            '"probable_root_cause", "supporting_evidence", "uncertainty", '
            'and "confidence". Supporting evidence must identify the '
            "simulated observations used. If the cause cannot be established, "
            "state that it is inconclusive."
        )
    else:
        system_prompt = (
            "You are an application incident investigator. "
            "Treat AWS CloudWatch metrics as the authoritative source "
            "for live CPU utilization. CloudWatch CPU values are already "
            "percentages on a scale from 0 to 100. Never multiply "
            "maximum_cpu_percent by 100. Use the tool's assessment field "
            "directly. Only describe CPU as high when the observed maximum "
            "CPU meets or exceeds 80 percent. If live CPU metrics are available "
            "and their maximum is below 80%, do not describe CPU as high "
            "based on simulated incident data. "
            "Distinguish live AWS evidence from simulated logs, database "
            "metrics, and deployment information. Do not present simulated "
            "evidence as live AWS telemetry. "
            "Prioritize direct diagnostic evidence over temporal correlations. "
            "High CPU together with timeouts may support a hypothesis of "
            "application or workload CPU saturation, but does not prove it. "
            "A recent deployment is contextual evidence only and must not be "
            "claimed as the cause without supporting evidence. "
            "Use the available tools and do not repeat a tool with identical "
            "input when its result is already available. "
            "Distinguish observations from hypotheses. Do not claim a diagnostic "
            "was run unless its result is available. "
            "When evidence is incomplete or competing explanations remain "
            "possible, explicitly state uncertainty and use medium or low "
            "confidence. Use high confidence only when multiple independent "
            "pieces of evidence strongly support the same cause. "
            "Return only a valid JSON object with exactly these fields: "
            '"probable_root_cause", "supporting_evidence", "uncertainty", '
            'and "confidence". Supporting evidence must identify which '
            "evidence is live AWS data and which is simulated. If the cause "
            "cannot be established, state that it is inconclusive."
        )

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "text": (
                        "Investigate this incident using the diagnostic tools. "
                        "The expected root-cause label is not provided. "
                        + (
                            "All data is simulated for controlled evaluation."
                            if evaluation_mode
                            else (
                                "Do not assume fixture values are live AWS "
                                "observations."
                            )
                        )
                        + "\n\nIncident data:\n"
                        + json.dumps(agent_incident)
                    )
                }
            ],
        }
    ]

    for request_number in range(1, max_model_requests + 1):
        try:
            response = client.converse(
                modelId=MODEL_ID,
                system=[{"text": system_prompt}],
                messages=messages,
                inferenceConfig={
                    "maxTokens": 800,
                    "temperature": 0,
                },
                toolConfig={
                    **active_tool_config,
                    "toolChoice": {"auto": {}},
                },
            )
        except Exception as error:
            return fallback_result(f"Bedrock request failed: {error}")

        assistant_message = response.get("output", {}).get("message", {})
        content = assistant_message.get("content", [])

        if not content:
            return fallback_result("Bedrock returned an empty response.")

        tool_uses = [
            block["toolUse"]
            for block in content
            if "toolUse" in block
        ]

        if not tool_uses:
            for block in content:
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
                except (json.JSONDecodeError, ValueError):
                    continue

                return {
                    "status": "success",
                    "source": "bedrock_agent",
                    "diagnosis": diagnosis,
                    "evidence": evidence,
                    "message": (
                        "The Bedrock agent returned a valid diagnosis. "
                        + (
                            "Evidence is simulated for controlled evaluation."
                            if evaluation_mode
                            else (
                                "Check each evidence item's source before "
                                "treating it as live AWS evidence."
                            )
                        )
                    ),
                    "elapsed_seconds": round(
                        time.perf_counter() - started_at, 3
                    ),
                    "tool_call_count": len(evidence),
                    "model_id": MODEL_ID,
                    "region": REGION,
                    "evaluation_mode": evaluation_mode,
                }

            return fallback_result(
                "The Bedrock agent did not produce a valid JSON diagnosis."
            )

        if request_number == max_model_requests:
            return fallback_result(
                "The Bedrock agent reached its model-request limit."
            )

        tool_results = []

        for tool_use in tool_uses:
            tool_name = tool_use["name"]
            tool_input = tool_use.get("input", {})

            try:
                if tool_name == "get_cpu_metrics":
                    if evaluation_mode:
                        result = get_cpu_metrics(agent_incident)
                    else:
                        result = get_live_cpu_metrics()

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

            except Exception as error:
                result = {
                    "status": "error",
                    "tool": tool_name,
                    "data": {},
                    "message": str(error),
                }

            evidence.append({
                "tool": tool_name,
                "result": result,
            })

            tool_results.append({
                "toolResult": {
                    "toolUseId": tool_use["toolUseId"],
                    "content": [{"json": result}],
                }
            })

        messages.extend([
            {
                "role": "assistant",
                "content": content,
            },
            {
                "role": "user",
                "content": tool_results,
            },
        ])

    return fallback_result(
        "The Bedrock agent stopped without producing a final diagnosis."
    )


def main():
    """Run the standalone live agent and baseline demonstration."""
    try:
        with open("data/incident.json", "r", encoding="utf-8") as file:
            incident = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not load incident data: {error}")
        return

    expected_root_cause = incident.get("expected_root_cause")

    result = investigate_incident(incident)

    print("\n=== Agent Investigation Result ===")
    print(json.dumps(result, indent=2))

    if result.get("status") != "success":
        print(
            "\nThe AI-agent run did not complete successfully. "
            "Any fallback result is labeled separately."
        )
        return

    diagnosis = result["diagnosis"]

    if expected_root_cause:
        print("\n=== Agent Evaluation ===")
        evaluation = evaluate_diagnosis(diagnosis, expected_root_cause)
        evaluation["evaluation_note"] = (
            "This standalone demonstration uses live AWS CPU metrics and "
            "simulated supporting evidence. Do not treat this as the "
            "controlled benchmark."
        )
        print(json.dumps(evaluation, indent=2))

    print("\n=== Rule-Based Baseline Comparison ===")
    baseline_start = time.perf_counter()
    baseline_diagnosis = run_rule_based_fallback(incident)
    baseline_elapsed = time.perf_counter() - baseline_start

    if baseline_diagnosis and expected_root_cause:
        baseline_evaluation = evaluate_diagnosis(
            baseline_diagnosis,
            expected_root_cause,
        )
        print(json.dumps(baseline_evaluation, indent=2))

    print(f"Agent investigation time: {result['elapsed_seconds']:.3f} seconds")
    print(f"Baseline diagnostic time: {baseline_elapsed:.3f} seconds")


if __name__ == "__main__":
    main()
