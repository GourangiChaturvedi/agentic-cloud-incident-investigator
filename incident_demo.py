# Simulated cloud incident evidence
incident = {
    "cpu_usage": 45,
    "request_multiplier": 1,
    "timeouts_increasing": False,
    "database_response_ms": 200,
}

print("CLOUD INCIDENT INVESTIGATION")
print("----------------------------")

print(f"CPU usage: {incident['cpu_usage']}%")
print(
    f"Request volume: "
    f"{incident['request_multiplier']}x normal"
)
print(
    f"Timeouts increasing: "
    f"{incident['timeouts_increasing']}"
)
print(
    f"Database response: "
    f"{incident['database_response_ms']} ms"
)

# Apply a simple diagnostic rule
if (
    incident["cpu_usage"] >= 90
    and incident["request_multiplier"] >= 3
    and incident["timeouts_increasing"]
):
    print("\nPossible diagnosis: Application overload")
    print("Evidence: High CPU, increased requests,")
    print("and increasing timeout errors.")
    print("Status: Further investigation required.")

elif (
    incident["database_response_ms"] >= 1000
    and incident["timeouts_increasing"]
):
    print("\nPossible diagnosis: Slow database responses")
    print("Evidence: Database response is at least 1000 ms,")
    print("and timeout errors are increasing.")
    print("Status: Further investigation required.")

else:
    print("\nDiagnosis: Inconclusive")
    print("Collect more diagnostic evidence.")
