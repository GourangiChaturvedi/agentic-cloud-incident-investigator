
from remediation import (
    propose_remediation,
    validate_remediation_action,
    record_approval,
)


def test_proposal_does_not_execute_actions():
    diagnosis = {
        "probable_root_cause": "Application or workload CPU saturation"
    }

    proposal = propose_remediation(diagnosis)

    assert proposal["status"] == "proposed"
    assert proposal["requires_human_approval"] is True
    assert proposal["executed"] is False


def test_invalid_diagnosis_is_rejected():
    try:
        propose_remediation({})
    except ValueError:
        return

    raise AssertionError("An empty diagnosis should be rejected.")


def test_allowlist_rejects_unsafe_action():
    try:
        validate_remediation_action("delete_production_database")
    except ValueError:
        return

    raise AssertionError("Unsafe action should be rejected.")


def test_approval_and_rejection_never_execute_actions():
    proposal = propose_remediation(
        {"probable_root_cause": "CPU saturation"}
    )

    approved = record_approval(proposal, True)
    rejected = record_approval(proposal, False)

    assert approved["approval_status"] == "approved"
    assert rejected["approval_status"] == "rejected"
    assert approved["executed"] is False
    assert rejected["executed"] is False


def test_invalid_approval_is_rejected():
    proposal = propose_remediation(
        {"probable_root_cause": "CPU saturation"}
    )

    try:
        record_approval(proposal, "yes")
    except ValueError:
        return

    raise AssertionError("Invalid approval should be rejected.")


if __name__ == "__main__":
    tests = [
        test_proposal_does_not_execute_actions,
        test_invalid_diagnosis_is_rejected,
        test_allowlist_rejects_unsafe_action,
        test_approval_and_rejection_never_execute_actions,
        test_invalid_approval_is_rejected,
    ]

    for test in tests:
        test()
        print(f"PASS: {test.__name__}")

    print(f"\nAll {len(tests)} remediation safety tests passed.")
