
from llm_tool_test import evaluate_diagnosis

import json

from llm_tool_test import parse_diagnosis


def test_valid_diagnosis():
    sample = {
        "probable_root_cause": "High CPU load",
        "supporting_evidence": ["CPU at 96%"],
        "uncertainty": "Deployment causation is unconfirmed",
        "confidence": "medium",
    }

    result = parse_diagnosis(json.dumps(sample))

    assert result["probable_root_cause"] == "High CPU load"
    assert result["confidence"] == "medium"
    print("PASS: Valid diagnosis accepted.")


def test_missing_field():
    sample = {
        "probable_root_cause": "High CPU load",
        "supporting_evidence": ["CPU at 96%"],
        "confidence": "medium",
    }

    try:
        parse_diagnosis(json.dumps(sample))
    except ValueError as error:
        assert "uncertainty" in str(error)
        print("PASS: Missing uncertainty field rejected.")
    else:
        raise AssertionError("Invalid diagnosis was accepted.")

def test_evaluate_diagnosis():
    diagnosis = {
        "probable_root_cause": "possible_application_overload",
        "supporting_evidence": ["CPU at 96%"],
        "uncertainty": "Other causes remain possible",
        "confidence": "medium",
    }

    # Matching diagnosis should be correct.
    result = evaluate_diagnosis(
        diagnosis, "possible_application_overload"
    )
    assert result["correct"] is True

    # Different diagnosis should be incorrect.
    result = evaluate_diagnosis(
        diagnosis, "database_connection_exhaustion"
    )
    assert result["correct"] is False

    print("PASS: Diagnosis evaluation tests passed.")


if __name__ == "__main__":
    test_valid_diagnosis()
    test_missing_field()
    test_evaluate_diagnosis()
    print("\nAll diagnosis parser tests passed.")
