# Live Bedrock Investigation Test

**Date:** October 16, 2026
**Model:** Amazon Nova Lite (`amazon.nova-lite-v1:0`)
**Region:** Asia Pacific (Sydney) — `ap-southeast-2`
**Result:** Successful

## Investigation execution

- Investigation rounds: 2
- Diagnostic tools executed: 3
- Tool errors shown: 0

### Tools selected by the agent

1. `get_cpu_metrics`
   - CPU utilization: 96%
   - Assessment: high

2. `analyze_logs`
   - Request timeouts detected
   - Application response time increased

3. `get_recent_deployments`
   - Recent deployment detected: true

## Agent diagnosis

**Probable root cause:** A recent deployment may have introduced a performance issue.

**Supporting evidence:** High CPU usage, request timeouts, and increased application response time.

**Uncertainty:** The correlation between the deployment and the incident has not been established. Further investigation is needed.

**Confidence:** Medium

## Limitations

- The database diagnostic tool was not selected during this run.
- The diagnosis is a hypothesis, not a confirmed root cause.
- This test demonstrates live tool selection and structured diagnosis, but does not establish diagnostic accuracy.
- No actual cloud remediation was performed.

## Conclusion

The live Bedrock agent successfully selected diagnostic tools, collected their results, and generated a structured diagnosis with an explicit uncertainty statement. Further testing is required to evaluate accuracy and tool-selection coverage.
