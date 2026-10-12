
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
