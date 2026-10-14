
import json

from diagnostic_tools import (
    analyze_logs,
    search_logs,
    get_cpu_metrics,
    get_database_metrics,
    get_recent_deployments
)

print("\nTesting search_logs():")

test_logs = [
    "Repeated request timeouts detected",
    "CPU utilization exceeded 90%",
    "Database connection failed",
    "Application response time increased"
]

result = search_logs(test_logs, "timeout")
print(json.dumps(result, indent=4))


print("\nTesting get_cpu_metrics():")

cpu_result = get_cpu_metrics({
    "cpu_usage_percent": 96
})

print(json.dumps(cpu_result, indent=4))


print("\nTesting get_database_metrics():")

database_result = get_database_metrics({
    "database_connections": 85
})

print(json.dumps(database_result, indent=4))


print("\nTesting get_recent_deployments():")

deployment_result = get_recent_deployments({
    "recent_deployment": True
})

print(json.dumps(deployment_result, indent=4))



print("\n========== INTEGRATED DIAGNOSTIC TEST ==========")

test_incident = {
    "cpu_usage_percent": 96,
    "database_connections": 35,
    "recent_deployment": True,
    "logs": [
        "Repeated request timeouts detected",
        "CPU utilization exceeded 90%",
        "Application response time increased"
    ]
}

diagnostic_results = {
    "cpu": get_cpu_metrics(test_incident),
    "database": get_database_metrics(test_incident),
    "deployment": get_recent_deployments(test_incident),
    "log_search": search_logs(test_incident["logs"], "timeout")
}

print(json.dumps(diagnostic_results, indent=4))


print("\n========== INVALID DATA TESTS ==========")

print("\n1. Missing CPU data:")
print(json.dumps(
    get_cpu_metrics({}),
    indent=4
))

print("\n2. Invalid CPU data:")
print(json.dumps(
    get_cpu_metrics({"cpu_usage_percent": "high"}),
    indent=4
))

print("\n3. Missing database data:")
print(json.dumps(
    get_database_metrics({}),
    indent=4
))

print("\n4. Invalid database connections:")
print(json.dumps(
    get_database_metrics({"database_connections": -5}),
    indent=4
))

print("\n5. Missing deployment data:")
print(json.dumps(
    get_recent_deployments({}),
    indent=4
))

print("\n6. Invalid log input:")
print(json.dumps(
    search_logs("not a list", "timeout"),
    indent=4
))


print("\nTesting analyze_logs() with invalid entries:")

test_logs = [
    "Request timeout detected",
    None,
    123,
    "Application response time increased"
]

print(json.dumps(analyze_logs(test_logs), indent=4))