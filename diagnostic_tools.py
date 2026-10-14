def analyze_logs(logs):
    if not isinstance(logs, list):
        return {
            "status": "error",
            "message": "Logs must be provided as a list.",
            "findings": []
        }

    findings = []
    skipped_entries = 0

    for log in logs:
        if not isinstance(log, str):
            skipped_entries += 1
            continue

        log_lower = log.lower()

        if "timeout" in log_lower:
            findings.append("Request timeouts detected")

        if "response time increased" in log_lower:
            findings.append("Application response time increased")

        if "error" in log_lower:
            findings.append("Error mentioned in logs")

    if not findings:
        findings.append("No matching log patterns detected")

    return {
        "status": "success",
        "findings": findings,
        "skipped_entries": skipped_entries
    }



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