
def validate_incident(incident):
    """Validate the shared incident input format."""
    if not isinstance(incident, dict):
        return {
            "status": "error",
            "message": "Incident data must be a dictionary.",
        }

    required_fields = {
        "incident_id": str,
        "incident_type": str,
        "cpu_usage_percent": (int, float),
        "database_connections": int,
        "recent_deployment": bool,
        "logs": list,
    }

    for field, expected_type in required_fields.items():
        if field not in incident:
            return {
                "status": "error",
                "message": f"Required incident field is missing: {field}",
            }

        value = incident[field]

        if field == "cpu_usage_percent" and isinstance(value, bool):
            return {
                "status": "error",
                "message": "CPU usage must be a number.",
            }

        if field == "database_connections" and isinstance(value, bool):
            return {
                "status": "error",
                "message": "Database connections must be an integer.",
            }

        if not isinstance(value, expected_type):
            return {
                "status": "error",
                "message": f"Invalid type for incident field: {field}",
            }

    if not incident["incident_id"].strip():
        return {
            "status": "error",
            "message": "Incident ID must not be empty.",
        }

    if not incident["incident_type"].strip():
        return {
            "status": "error",
            "message": "Incident type must not be empty.",
        }

    if not 0 <= incident["cpu_usage_percent"] <= 100:
        return {
            "status": "error",
            "message": "CPU usage must be between 0 and 100.",
        }

    if incident["database_connections"] < 0:
        return {
            "status": "error",
            "message": "Database connections must be non-negative.",
        }

    return {
        "status": "success",
        "message": "Incident input is valid.",
    }



def analyze_logs(logs):
    """Analyze logs and return a standardized result."""
    if not isinstance(logs, list):
        return {
            "status": "error",
            "tool": "analyze_logs",
            "data": {},
            "message": "Logs must be provided as a list.",
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
        "tool": "analyze_logs",
        "data": {
            "findings": findings,
            "skipped_entries": skipped_entries,
        },
        "message": "Log analysis completed.",
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
    """Return CPU metrics in the standardized diagnostic format."""
    tool_name = "get_cpu_metrics"

    if not isinstance(incident, dict):
        return {
            "status": "error",
            "tool": tool_name,
            "data": {},
            "message": "Incident data must be a dictionary.",
        }

    cpu = incident.get("cpu_usage_percent")

    if cpu is None:
        return {
            "status": "error",
            "tool": tool_name,
            "data": {},
            "message": "CPU usage data is missing.",
        }

    if isinstance(cpu, bool) or not isinstance(cpu, (int, float)):
        return {
            "status": "error",
            "tool": tool_name,
            "data": {},
            "message": "CPU usage must be a number.",
        }

    if not 0 <= cpu <= 100:
        return {
            "status": "error",
            "tool": tool_name,
            "data": {},
            "message": "CPU usage must be between 0 and 100.",
        }

    return {
        "status": "success",
        "tool": tool_name,
        "data": {
            "cpu_usage_percent": cpu,
            "assessment": "high" if cpu > 90 else "normal",
        },
        "message": "CPU metrics retrieved successfully.",
    }


def get_live_cpu_metrics(region="ap-southeast-2", hours=1):
    """Return real EC2 CPU evidence from AWS CloudWatch."""
    result = get_aws_cpu_metrics(region=region, hours=hours)

    if result.get("status") != "success":
        return {
            "status": result.get("status", "error"),
            "tool": "get_cpu_metrics",
            "data": result.get("data", {}),
            "message": result.get(
                "message", "Could not retrieve live CPU metrics."
            ),
        }

    metrics = result.get("data", {}).get("metrics", [])

    if not metrics:
        return {
            "status": "unavailable",
            "tool": "get_cpu_metrics",
            "data": {
                "source": "aws_cloudwatch",
                "metrics": [],
                "metric_count": 0,
            },
            "message": "No live EC2 CPU datapoints were returned.",
        }

    return {
        "status": "success",
        "tool": "get_cpu_metrics",
        "data": {
            "source": "aws_cloudwatch",
            "region": region,
            "metrics": metrics,
"metric_count": len(metrics),
"maximum_cpu_percent": max(
    metric["maximum_cpu"] for metric in metrics
),
"assessment": (
    "high"
    if max(metric["maximum_cpu"] for metric in metrics) >= 80
    else "normal"
),
        },
        "message": "Live AWS CPU metrics retrieved successfully.",
    }

def get_database_metrics(incident):
    """Return database metrics in the standardized diagnostic format."""
    tool_name = "get_database_metrics"

    if not isinstance(incident, dict):
        return {
            "status": "error",
            "tool": tool_name,
            "data": {},
            "message": "Incident data must be a dictionary.",
        }

    connections = incident.get("database_connections")

    if connections is None:
        return {
            "status": "error",
            "tool": tool_name,
            "data": {},
            "message": "Database connection data is missing.",
        }

    if isinstance(connections, bool) or not isinstance(connections, int):
        return {
            "status": "error",
            "tool": tool_name,
            "data": {},
            "message": "Database connections must be an integer.",
        }

    if connections < 0:
        return {
            "status": "error",
            "tool": tool_name,
            "data": {},
            "message": "Database connections must be non-negative.",
        }

    threshold = 80

    return {
        "status": "success",
        "tool": tool_name,
        "data": {
            "database_connections": connections,
            "threshold": threshold,
            "assessment": "high" if connections > threshold else "normal",
        },
        "message": "Database metrics retrieved successfully.",
    }




def get_recent_deployments(incident):
    """Return deployment information in the standardized diagnostic format."""
    tool_name = "get_recent_deployments"

    if not isinstance(incident, dict):
        return {
            "status": "error",
            "tool": tool_name,
            "data": {},
            "message": "Incident data must be a dictionary.",
        }

    recent_deployment = incident.get("recent_deployment")

    if recent_deployment is None:
        return {
            "status": "error",
            "tool": tool_name,
            "data": {},
            "message": "Recent deployment information is missing.",
        }

    if not isinstance(recent_deployment, bool):
        return {
            "status": "error",
            "tool": tool_name,
            "data": {},
            "message": "Recent deployment information must be a boolean.",
        }

    return {
        "status": "success",
        "tool": tool_name,
        "data": {
            "recent_deployment": recent_deployment,
            "assessment": (
                "deployment_detected"
                if recent_deployment
                else "no_recent_deployment"
            ),
        },
        "message": "Deployment information retrieved successfully.",
    }


def collect_diagnostic_evidence(incident, source="simulated"):
    """Collect diagnostic evidence from simulated input or AWS."""

    if source not in ("simulated", "aws"):
        return {
            "status": "error",
            "tool": "collect_diagnostic_evidence",
            "data": {
                "source": source,
                "evidence": [],
                "errors": [],
            },
            "message": "Source must be 'simulated' or 'aws'.",
        }

    # Real AWS telemetry path
    if source == "aws":
        aws_results = [
            get_aws_cpu_metrics(),
            get_aws_log_evidence(
                "/agentic-cloud-incident-investigator/test"
            ),
        ]

        evidence = [
            result for result in aws_results
            if result.get("status") == "success"
        ]

        unavailable = [
            result for result in aws_results
            if result.get("status") == "unavailable"
        ]

        errors = [
            result for result in aws_results
            if result.get("status") == "error"
        ]

        # Keep genuine AWS evidence if at least one source succeeded.
        if evidence:
            return {
                "status": "partial" if unavailable or errors else "success",
                "tool": "collect_diagnostic_evidence",
                "data": {
                    "source": "aws",
                    "fallback_used": False,
                    "evidence": evidence,
                    "unavailable": unavailable,
                    "errors": errors,
                },
                "message": (
                    "AWS evidence collected successfully."
                    if not unavailable and not errors
                    else (
                        "Partial AWS evidence collected; "
                        "check unavailable sources and errors."
                    )
                ),
            }

        # Do not hide AWS errors by silently switching to simulated data.
        if errors:
            return {
                "status": "error",
                "tool": "collect_diagnostic_evidence",
                "data": {
                    "source": "aws",
                    "fallback_used": False,
                    "evidence": [],
                    "unavailable": unavailable,
                    "errors": errors,
                },
                "message": "AWS evidence collection failed: " + "; ".join(
                    item.get("message", "Unknown AWS error")
                    for item in errors
                ),
            }

        # Use simulated evidence only when all AWS sources are unavailable.
        simulated_result = collect_diagnostic_evidence(
            incident,
            source="simulated",
        )

        # Guard against an unexpected invalid result.
        if not isinstance(simulated_result, dict):
            return {
                "status": "error",
                "tool": "collect_diagnostic_evidence",
                "data": {
                    "source": "aws",
                    "fallback_used": False,
                    "evidence": [],
                    "unavailable": unavailable,
                    "errors": [],
                },
                "message": (
                    "Simulated fallback returned an invalid result."
                ),
            }

        simulated_result["data"]["source"] = "simulated_fallback"
        simulated_result["data"]["fallback_used"] = True
        simulated_result["data"]["aws_unavailable"] = unavailable
        simulated_result["message"] = (
            "AWS evidence was unavailable; simulated evidence was used "
            "as a fallback. " + simulated_result["message"]
        )

        return simulated_result

    # Simulated evidence path
    results = [
        get_cpu_metrics(incident),
        get_database_metrics(incident),
        analyze_logs(incident.get("logs", [])),
        get_recent_deployments(incident),
    ]

    evidence = [
        result for result in results
        if result.get("status") == "success"
    ]

    errors = [
        result for result in results
        if result.get("status") == "error"
    ]

    return {
        "status": "partial" if errors else "success",
        "tool": "collect_diagnostic_evidence",
        "data": {
            "source": "simulated",
            "fallback_used": False,
            "evidence": evidence,
            "unavailable": [],
            "errors": errors,
        },
        "message": (
            "Simulated evidence collected successfully."
            if not errors
            else "Simulated evidence collected with some errors."
        ),
    }


def record_investigation(incident, collection_result):
    """Create a structured record of a diagnostic investigation."""
    if not isinstance(incident, dict):
        return {
            "status": "error",
            "message": "Incident data must be a dictionary.",
        }

    if not isinstance(collection_result, dict):
        return {
            "status": "error",
            "message": "Collection result must be a dictionary.",
        }

    data = collection_result.get("data", {})
    evidence = data.get("evidence", [])
    errors = data.get("errors", [])

    if not isinstance(evidence, list) or not isinstance(errors, list):
        return {
            "status": "error",
            "message": "Evidence and errors must be lists.",
        }

    return {
        "status": collection_result.get("status", "error"),
        "incident_id": incident.get("incident_id", "unknown"),
        "successful_tool_count": len(evidence),
        "error_count": len(errors),
        "evidence": evidence,
        "errors": errors,
        "message": collection_result.get("message", "No message provided."),
    }


def get_aws_cpu_metrics(region="ap-southeast-2", hours=1):
    """Retrieve real EC2 CPU evidence from AWS CloudWatch."""
    from aws_cloudwatch import get_ec2_cpu_metrics

    result = get_ec2_cpu_metrics(region=region, hours=hours)

    if result["status"] != "success":
        return {
            "status": "error",
            "tool": "get_aws_cpu_metrics",
            "data": {
                "source": "aws_cloudwatch",
                "region": region,
                "metrics": [],
            },
            "message": result["message"],
        }

    return {
        "status": "success" if result["metrics"] else "unavailable",
        "tool": "get_aws_cpu_metrics",
        "data": {
            "source": "aws_cloudwatch",
            "region": region,
            "metrics": result["metrics"],
            "metric_count": len(result["metrics"]),
        },
        "message": result["message"],
    }


def get_aws_log_evidence(log_group_name, region="ap-southeast-2", minutes=60):
    """Collect real CloudWatch log events as diagnostic evidence."""
    from aws_cloudwatch import get_cloudwatch_logs

    result = get_cloudwatch_logs(
        log_group_name=log_group_name,
        region=region,
        minutes=minutes,
    )

    status = result["status"]

    return {
        "status": status,
        "tool": "get_aws_log_evidence",
        "data": {
            "source": "aws_cloudwatch_logs",
            "region": region,
            "log_group": log_group_name,
            "events": result["events"],
            "event_count": len(result["events"]),
        },
        "message": result["message"],
    }
