
import json

def check_cpu(cpu_usage):
    if cpu_usage > 90:
        return "High CPU detected"
    return "CPU is normal"


def check_database_connections(connections):
    if connections > 80:
        return "High database connections detected"
    return "Database connections are normal"


def analyze_logs(logs):
    findings = []

    for log in logs:
        log_lower = log.lower()

        if "timeout" in log_lower:
            findings.append("Request timeouts detected")

        if "response time increased" in log_lower:
            findings.append("Application response time increased")

        if "error" in log_lower:
            findings.append("Error mentioned in logs")

    if not findings:
        return ["No matching log patterns detected"]

    return findings


def search_logs(logs, keyword):
    if not isinstance(logs, list):
        return {
            "status": "error",
            "matches": [],
            "message": "Logs must be provided as a list."
        }

    if not isinstance(keyword, str) or not keyword.strip():
        return {
            "status": "error",
            "matches": [],
            "message": "Keyword must be a non-empty string."
        }

    matches = [
        log for log in logs
        if isinstance(log, str) and keyword.lower() in log.lower()
    ]

    return {
        "status": "success",
        "keyword": keyword,
        "match_count": len(matches),
        "matches": matches
    }


def get_cpu_metrics(incident):
    if not isinstance(incident, dict):
        return {
            "status": "error",
            "message": "Incident data must be a dictionary."
        }

    cpu = incident.get("cpu_usage_percent")

    if cpu is None:
        return {
            "status": "error",
            "message": "CPU usage data is missing."
        }

    if isinstance(cpu, bool) or not isinstance(cpu, (int, float)):
        return {
            "status": "error",
            "message": "CPU usage must be a number."
        }

    if not 0 <= cpu <= 100:
        return {
            "status": "error",
            "message": "CPU usage must be between 0 and 100."
        }

    return {
        "status": "success",
        "cpu_usage_percent": cpu,
        "assessment": "high" if cpu > 90 else "normal"
    }


def get_database_metrics(incident):
    if not isinstance(incident, dict):
        return {
            "status": "error",
            "message": "Incident data must be a dictionary."
        }

    connections = incident.get("database_connections")

    if connections is None:
        return {
            "status": "error",
            "message": "Database connection data is missing."
        }

    if isinstance(connections, bool) or not isinstance(connections, (int, float)):
        return {
            "status": "error",
            "message": "Database connections must be a number."
        }

    if connections < 0 or not isinstance(connections, int):
        return {
            "status": "error",
            "message": "Database connections must be a non-negative integer."
        }

    return {
        "status": "success",
        "database_connections": connections,
        "threshold": 80,
        "assessment": "high" if connections > 80 else "normal"
    }


def get_recent_deployments(incident):
    if not isinstance(incident, dict):
        return {
            "status": "error",
            "message": "Incident data must be a dictionary."
        }

    if "recent_deployment" not in incident:
        return {
            "status": "error",
            "message": "Recent deployment data is missing."
        }

    deployment = incident["recent_deployment"]

    if not isinstance(deployment, bool):
        return {
            "status": "error",
            "message": "Recent deployment must be true or false."
        }

    return {
        "status": "success",
        "recent_deployment": deployment,
        "assessment": (
            "deployment_detected"
            if deployment
            else "no_recent_deployment"
        )
    }


try:
    with open("data/incident.json", "r") as file:
        incident = json.load(file)

    print("Incident ID:", incident["incident_id"])
    print("Incident Type:", incident["incident_type"])
    print("CPU Usage:", incident["cpu_usage_percent"], "%")
    print("CPU Assessment:", check_cpu(incident["cpu_usage_percent"]))
    print(
    "Database Assessment:",
    check_database_connections(incident["database_connections"])
)
    print("Recent Deployment:", incident["recent_deployment"])

    print("\nIncident Logs:")
    for log in incident["logs"]:
        print("-", log)
    
    print("\nLog Analysis:")
    for finding in analyze_logs(incident["logs"]):
        print("-", finding)


except FileNotFoundError:
    print("Error: Incident file not found.")

except json.JSONDecodeError:
    print("Error: Invalid JSON format.")

except KeyError as error:
    print("Error: Missing incident field:", error)


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



