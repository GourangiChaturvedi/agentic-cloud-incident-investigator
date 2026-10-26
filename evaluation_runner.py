import json
import statistics
import time
from pathlib import Path

from llm_tool_test import (
    evaluate_diagnosis,
    investigate_incident,
    normalize_root_cause,
    run_rule_based_fallback,
)


CASES_PATH = Path("data/evaluation_cases.json")
RESULTS_PATH = Path("data/evaluation_results.json")

# Only these fields are supplied to either diagnostic system.
# The expected label is kept exclusively for scoring.
INCIDENT_INPUT_FIELDS = (
    "incident_id",
    "incident_type",
    "cpu_usage_percent",
    "database_connections",
    "recent_deployment",
    "logs",
)


def make_incident_input(case):
    """Create a consistent incident input without the expected answer."""
    return {field: case[field] for field in INCIDENT_INPUT_FIELDS}


def load_cases():
    """Load and validate the evaluation dataset without calling AWS."""
    with CASES_PATH.open("r", encoding="utf-8") as file:
        cases = json.load(file)

    if not isinstance(cases, list) or not cases:
        raise ValueError("Evaluation cases must be a non-empty JSON list.")

    required_fields = set(INCIDENT_INPUT_FIELDS) | {"expected_root_cause"}
    seen_ids = set()

    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            raise ValueError(f"Case {index} must be a JSON object.")

        missing = required_fields - case.keys()
        if missing:
            raise ValueError(
                f"Case {index} is missing fields: {sorted(missing)}"
            )

        incident_id = case["incident_id"]

        if not isinstance(incident_id, str) or not incident_id.strip():
            raise ValueError(f"Case {index} has an invalid incident_id.")

        if incident_id in seen_ids:
            raise ValueError(f"Duplicate incident_id: {incident_id}")

        seen_ids.add(incident_id)

        cpu = case["cpu_usage_percent"]
        if (
            isinstance(cpu, bool)
            or not isinstance(cpu, (int, float))
            or not 0 <= cpu <= 100
        ):
            raise ValueError(
                f"{incident_id}: CPU must be a number from 0 to 100."
            )

        connections = case["database_connections"]
        if (
            isinstance(connections, bool)
            or not isinstance(connections, int)
            or connections < 0
        ):
            raise ValueError(
                f"{incident_id}: database_connections must be "
                "a non-negative integer."
            )

        if not isinstance(case["recent_deployment"], bool):
            raise ValueError(
                f"{incident_id}: recent_deployment must be boolean."
            )

        if (
            not isinstance(case["logs"], list)
            or not all(isinstance(log, str) for log in case["logs"])
        ):
            raise ValueError(
                f"{incident_id}: logs must be a list of strings."
            )

        expected = case["expected_root_cause"]
        if not isinstance(expected, str) or not expected.strip():
            raise ValueError(
                f"{incident_id}: expected_root_cause must be non-empty."
            )

        if normalize_root_cause(expected) == "unclassified":
            raise ValueError(
                f"{incident_id}: expected_root_cause does not map "
                "to a recognized evaluation category."
            )

    return cases


def score_prediction(diagnosis, expected_root_cause):
    """Score a diagnosis while preserving the expected category on failures."""
    expected_category = normalize_root_cause(expected_root_cause)

    if (
        not isinstance(diagnosis, dict)
        or not isinstance(diagnosis.get("probable_root_cause"), str)
        or not diagnosis["probable_root_cause"].strip()
    ):
        return {
            "predicted_root_cause": None,
            "expected_root_cause": expected_root_cause,
            "predicted_category": None,
            "expected_category": expected_category,
            "correct": False,
        }

    return evaluate_diagnosis(diagnosis, expected_root_cause)


def summarize_system(records, system_name):
    """Summarize accuracy, timing, actual tool calls, and check counts."""
    total = len(records)
    correct = sum(record["correct"] for record in records)
    failures = sum(record["status"] != "success" for record in records)

    times = [
        record["elapsed_seconds"]
        for record in records
        if (
            isinstance(record["elapsed_seconds"], (int, float))
            and not isinstance(record["elapsed_seconds"], bool)
        )
    ]

    actual_tool_counts = [
        record["tool_call_count"]
        for record in records
        if (
            isinstance(record["tool_call_count"], int)
            and not isinstance(record["tool_call_count"], bool)
        )
    ]

    diagnostic_check_counts = [
        record["diagnostic_check_count"]
        for record in records
        if (
            isinstance(record["diagnostic_check_count"], int)
            and not isinstance(record["diagnostic_check_count"], bool)
        )
    ]

    return {
        "system": system_name,
        "total_cases": total,
        "correct_diagnoses": correct,
        "accuracy_percent": round(100 * correct / total, 2) if total else 0,
        "failed_runs": failures,
        "successful_runs": total - failures,
        "mean_elapsed_seconds": (
            round(statistics.mean(times), 3) if times else None
        ),
        "median_elapsed_seconds": (
            round(statistics.median(times), 3) if times else None
        ),
        "mean_actual_tool_calls": (
            round(statistics.mean(actual_tool_counts), 2)
            if actual_tool_counts
            else None
        ),
        "mean_diagnostic_checks": (
            round(statistics.mean(diagnostic_check_counts), 2)
            if diagnostic_check_counts
            else None
        ),
    }


def run_baseline(case):
    """Run the rule-based baseline on fixture fields only."""
    started = time.perf_counter()
    baseline_input = make_incident_input(case)

    try:
        diagnosis = run_rule_based_fallback(baseline_input)
        elapsed = round(time.perf_counter() - started, 3)

        if (
            not isinstance(diagnosis, dict)
            or not isinstance(diagnosis.get("probable_root_cause"), str)
            or not diagnosis["probable_root_cause"].strip()
        ):
            return {
                "status": "error",
                "source": "rule_based_baseline",
                "diagnosis": None,
                "elapsed_seconds": elapsed,
                "tool_call_count": None,
                "diagnostic_check_count": None,
                "message": "Baseline did not return a valid diagnosis.",
            }

        return {
            "status": "success",
            "source": "rule_based_baseline",
            "diagnosis": diagnosis,
            "elapsed_seconds": elapsed,
            # Function-level checks, not instrumented tool calls.
            "tool_call_count": None,
            "diagnostic_check_count": 3,
            "message": (
                "Baseline ran CPU, database, and log diagnostic checks. "
                "The count represents the three checks in the baseline code."
            ),
        }

    except Exception as error:
        return {
            "status": "error",
            "source": "rule_based_baseline",
            "diagnosis": None,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "tool_call_count": None,
            "diagnostic_check_count": None,
            "message": f"{type(error).__name__}: {error}",
        }


def run_agent(case):
    """Run the agent and only score genuine Bedrock-agent successes."""
    agent_input = make_incident_input(case)

    try:
        result = investigate_incident(
            agent_input,
            evaluation_mode=True,
        )

        if not isinstance(result, dict):
            raise ValueError("Agent returned an invalid result object.")

        source = result.get("source", "none")
        reported_status = result.get("status", "error")

        # A valid diagnosis from a fallback is not an AI-agent success.
        is_genuine_agent_success = (
            reported_status == "success"
            and source == "bedrock_agent"
            and isinstance(result.get("diagnosis"), dict)
            and isinstance(
                result["diagnosis"].get("probable_root_cause"), str
            )
            and bool(result["diagnosis"]["probable_root_cause"].strip())
        )

        if is_genuine_agent_success:
            status = "success"
            diagnosis = result["diagnosis"]
        else:
            # Prevent a fallback or malformed response from being scored
            # as a successful AI-agent diagnosis.
            status = (
                reported_status
                if reported_status != "success"
                else "error"
            )
            diagnosis = None

        return {
            "status": status,
            "source": source,
            "diagnosis": diagnosis,
            "elapsed_seconds": result.get("elapsed_seconds"),
            "tool_call_count": result.get("tool_call_count"),
            "diagnostic_check_count": None,
            "message": result.get("message", ""),
            "model_id": result.get("model_id"),
            "region": result.get("region"),
        }

    except Exception as error:
        return {
            "status": "error",
            "source": "none",
            "diagnosis": None,
            "elapsed_seconds": None,
            "tool_call_count": None,
            "diagnostic_check_count": None,
            "message": f"{type(error).__name__}: {error}",
        }


def evaluate_run(result, expected_root_cause):
    """Score after the system finishes, never during its investigation."""
    score = score_prediction(
        result["diagnosis"],
        expected_root_cause,
    )

    result["predicted_root_cause"] = score["predicted_root_cause"]
    result["predicted_category"] = score["predicted_category"]
    result["expected_category"] = score["expected_category"]
    result["correct"] = (
        result["status"] == "success" and score["correct"]
    )

    return result


def main():
    try:
        cases = load_cases()
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"Dataset validation failed: {error}")
        return

    print(f"Validated {len(cases)} evaluation cases.")
    print("Both systems will receive the same fixture fields.")
    print("Expected root-cause labels are withheld until scoring.")
    print("Agent CPU evidence will use simulated fixtures, not live CloudWatch.")
    print("This runner does not execute remediation actions.")
    print("Bedrock model requests may incur charges.")

    # Protect any previous report before making paid model requests.
    if RESULTS_PATH.exists():
        print(
            f"Evaluation cancelled: {RESULTS_PATH} already exists. "
            "Preserve or rename that report before running a new evaluation."
        )
        return

    confirmation = input("Type RUN to start the evaluation: ").strip()

    if confirmation != "RUN":
        print("Evaluation cancelled. No model calls were made.")
        return

    results = []

    for index, case in enumerate(cases, start=1):
        print(f"\n[{index}/{len(cases)}] {case['incident_id']}")

        baseline = evaluate_run(
            run_baseline(case),
            case["expected_root_cause"],
        )

        agent = evaluate_run(
            run_agent(case),
            case["expected_root_cause"],
        )

        results.append({
            "incident_id": case["incident_id"],
            "expected_root_cause": case["expected_root_cause"],
            "baseline": baseline,
            "agent": agent,
        })

        print(
            f"Baseline: {baseline['status']}, "
            f"correct={baseline['correct']}, "
            f"time={baseline['elapsed_seconds']}s"
        )
        print(
            f"Agent: {agent['status']} ({agent['source']}), "
            f"correct={agent['correct']}, "
            f"time={agent['elapsed_seconds']}s"
        )

    baseline_records = [item["baseline"] for item in results]
    agent_records = [item["agent"] for item in results]

    report = {
        "dataset": str(CASES_PATH),
        "total_cases": len(cases),
        "evaluation_mode": "simulated_fixtures",
        "remediation_executed_by_runner": False,
        "safety_evaluation": {
            "automated_by_this_runner": False,
            "human_approval_workflow_verified": False,
            "unauthorized_execution_verified": False,
            "note": (
                "This runner evaluates diagnosis only. Remediation safety "
                "must be documented separately using the application's "
                "approval and audit workflow. No remediation is executed here."
            ),
        },
        "metric_definitions": {
            "accuracy_percent": (
                "Correct successful diagnoses divided by all cases, "
                "including failed runs in the denominator."
            ),
            "mean_elapsed_seconds": (
                "Mean wall-clock duration for each system's run. Agent time "
                "includes model-request latency."
            ),
            "mean_actual_tool_calls": (
                "Mean recorded diagnostic tool invocations; null when "
                "the system's tool-call count is not instrumented."
            ),
            "mean_diagnostic_checks": (
                "Mean baseline function-level diagnostic checks; not an "
                "instrumented tool-call count."
            ),
        },
        "baseline_summary": summarize_system(
            baseline_records,
            "rule_based_baseline",
        ),
        "agent_summary": summarize_system(
            agent_records,
            "bedrock_agent",
        ),
        "results": results,
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Recheck immediately before writing; never overwrite an existing report.
    if RESULTS_PATH.exists():
        print(
            f"\nReport not saved: {RESULTS_PATH} appeared during the run. "
            "The existing report was preserved."
        )
        return

    with RESULTS_PATH.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    print("\n=== Evaluation Summary ===")
    print(json.dumps({
        "baseline": report["baseline_summary"],
        "agent": report["agent_summary"],
        "safety_evaluation": report["safety_evaluation"],
    }, indent=2))
    print(f"\nDetailed results saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    main()