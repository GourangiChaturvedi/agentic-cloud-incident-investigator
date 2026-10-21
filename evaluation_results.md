# Investigator Evaluation Results
**Date:** October 21, 2026
**Evidence source:** Simulated incident data
**Incident:** INC-001 — High CPU / possible application overload
## Agent Results
- Predicted diagnosis: Application or workload CPU saturation
- Expected category: `possible_application_overload`
- Correct: Yes
- Diagnostic tools used: 3
- Investigation time: 5.766 seconds
- Confidence: Medium

## Rule-Based Baseline Results
- Predicted diagnosis: Application or workload CPU saturation
- Expected category: `possible_application_overload`
- Correct: Yes
- Diagnostic time: 0.001 seconds
- Confidence: Medium

## Remediation Safety
- Proposal-only safety tests passed.
- Human approval is required by the proposal interface.
- No remediation or cloud changes were executed.
- Actual enforcement of a cloud-action approval gate has not been tested.

## AWS Telemetry
- Region checked: `ap-southeast-2`
- Running EC2 instances found: 0
- Configured CloudWatch log group: unavailable
- Real AWS incident investigation: not demonstrated.

## Limitations
Only one simulated incident has been evaluated. The observed accuracy is 1/1 for both methods and is not evidence of general accuracy. Timing is based on a single run. The full automated test suite has not yet been verified under a unified test runner.
