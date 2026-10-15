


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


if __name__ == "__main__":
    test_valid_diagnosis()
    test_missing_field()
    print("\nAll diagnosis parser tests passed.")
