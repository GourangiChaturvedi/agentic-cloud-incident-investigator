
import csv
import hashlib
import json
import platform
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

from evaluation_runner import (
    CASES_PATH,
    evaluate_run,
    load_cases,
    make_incident_input,
    run_baseline,
)


CSV_PATH = Path("data/baseline_results.csv")
METADATA_PATH = Path("data/baseline_experiment_metadata.json")


def sha256_file(path):
    """Return the SHA-256 hash of a file for reproducibility."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    # Preserve any earlier experiment results.
    if CSV_PATH.exists() or METADATA_PATH.exists():
        print("Experiment cancelled: an output file already exists.")
        print(f"CSV: {CSV_PATH} (exists: {CSV_PATH.exists()})")
        print(
            f"Metadata: {METADATA_PATH} "
            f"(exists: {METADATA_PATH.exists()})"
        )
        print("Preserve the existing files before choosing new output paths.")
        return

    try:
        cases = load_cases()
        dataset_hash = sha256_file(CASES_PATH)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Dataset validation failed: {error}")
        return

    print(f"Validated cases: {len(cases)}")
    print("System: rule-based baseline only")
    print("Inputs: simulated evaluation fixtures")
    print("AWS/Bedrock model calls: none intended by this runner")
    print("Remediation execution: disabled")
    print(f"Dataset SHA-256: {dataset_hash}")

    confirmation = input(
        "Type RUN_BASELINE to execute the baseline experiment: "
    ).strip()

    if confirmation != "RUN_BASELINE":
        print("Cancelled. No experiment was run.")
        return

    records = []
    started_at = datetime.now(timezone.utc).isoformat()

    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['incident_id']}")

        result = evaluate_run(
            run_baseline(case),
            case["expected_root_cause"],
        )

        incident_input = make_incident_input(case)

        record = {
            "incident_id": case["incident_id"],
            "input_json": json.dumps(
                incident_input,
                ensure_ascii=False,
                sort_keys=True,
            ),
            "expected_root_cause": case["expected_root_cause"],
            "predicted_root_cause": result.get("predicted_root_cause"),
            "expected_category": result.get("expected_category"),
            "predicted_category": result.get("predicted_category"),
            "correct": result["correct"],
            "status": result["status"],
            "elapsed_seconds": result.get("elapsed_seconds"),
            "diagnostic_check_count": result.get(
                "diagnostic_check_count"
            ),
            "tool_call_count": result.get("tool_call_count"),
            "source": result.get("source"),
            "message": result.get("message", ""),
            "remediation_attempted": False,
            "remediation_executed": False,
            "blocked_actions": "not_assessed",
            "safety_failures": "not_assessed",
        }

        records.append(record)

        print(
            f"  status={record['status']}, "
            f"correct={record['correct']}, "
            f"time={record['elapsed_seconds']}s"
        )

    total = len(records)
    correct_count = sum(row["correct"] for row in records)
    failures = sum(row["status"] != "success" for row in records)

    valid_times = [
        row["elapsed_seconds"]
        for row in records
        if isinstance(row["elapsed_seconds"], (int, float))
        and not isinstance(row["elapsed_seconds"], bool)
    ]

    summary = {
        "total_cases": total,
        "successful_runs": total - failures,
        "failed_runs": failures,
        "correct_diagnoses": correct_count,
        "incorrect_or_failed_diagnoses": total - correct_count,
        "accuracy_percent": (
            round(100 * correct_count / total, 2) if total else 0
        ),
        "mean_elapsed_seconds": (
            round(statistics.mean(valid_times), 3)
            if valid_times else None
        ),
        "median_elapsed_seconds": (
            round(statistics.median(valid_times), 3)
            if valid_times else None
        ),
        "diagnostic_checks_per_successful_run": 3,
        "tool_calls_instrumented": False,
    }

    metadata = {
        "experiment": "rule_based_baseline",
        "started_at_utc": started_at,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_path": str(CASES_PATH),
        "dataset_sha256": dataset_hash,
        "case_ids": [case["incident_id"] for case in cases],
        "python_version": sys.version,
        "platform": platform.platform(),
        "evaluation_mode": "simulated_fixtures",
        "baseline_implementation": "run_rule_based_fallback via evaluation_runner",
        "metric_definitions": {
            "accuracy_percent": (
                "Correct diagnoses divided by all cases, including failures."
            ),
            "elapsed_seconds": (
                "Wall-clock time for the baseline run, measured locally."
            ),
            "diagnostic_check_count": (
                "Three function-level CPU, database, and log checks; "
                "not an instrumented tool-call count."
            ),
            "blocked_actions_and_safety_failures": (
                "Not assessed by this diagnosis-only experiment. "
                "No remediation was attempted or executed by this runner."
            ),
        },
        "summary": summary,
    }

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(records[0].keys()) if records else []

    # Exclusive creation avoids intentionally overwriting prior results.
    try:
        with CSV_PATH.open(
            "x", newline="", encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

        with METADATA_PATH.open("x", encoding="utf-8") as file:
            json.dump(metadata, file, indent=2, ensure_ascii=False)

    except OSError as error:
        print(f"Could not save experiment output: {error}")
        print(
            "Check the output files before retrying; a partial output "
            "may exist and will be preserved."
        )
        return

    print("\n=== Rule-Based Baseline Summary ===")
    print(json.dumps(summary, indent=2))
    print(f"\nCSV results: {CSV_PATH}")
    print(f"Reproducibility metadata: {METADATA_PATH}")


if __name__ == "__main__":
    main()
