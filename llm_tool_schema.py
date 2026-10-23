CPU_TOOL_CONFIG = {
    "tools": [
        {
            "toolSpec": {
                "name": "get_cpu_metrics",
                "description": (
                    "Retrieve actual EC2 CPU utilization metrics from "
                    "AWS CloudWatch in the configured AWS region. "
                    "Do not infer live CPU utilization from incident "
                    "fixture data. The returned metrics are the source "
                    "of truth for observed CPU utilization. "
                    "Use this tool when investigating CPU-related incidents."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {},
                    }
                }
            }
        }
    ]
}


DATABASE_TOOL_CONFIG = {
    "tools": [
        {
            "toolSpec": {
                "name": "get_database_metrics",
                "description": (
                    "Check database connections for an incident. "
                    "Returns the connection count and whether it is high. "
                    "Use this tool when investigating database-related incidents."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "incident": {
                                "type": "object",
                                "properties": {
                                    "database_connections": {
                                        "type": "integer",
                                        "description": (
                                            "The number of active database connections."
                                        )
                                    }
                                },
                                "required": ["database_connections"]
                            }
                        },
                        "required": ["incident"]
                    }
                }
            }
        }
    ]
}


LOG_TOOL_CONFIG = {
    "tools": [
        {
            "toolSpec": {
                "name": "analyze_logs",
                "description": (
                    "Analyze incident logs for errors, request timeouts, "
                    "and increased application response times. "
                    "Use this tool when investigating incident logs."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "logs": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": (
                                    "A list of log messages from the incident."
                                )
                            }
                        },
                        "required": ["logs"]
                    }
                }
            }
        }
    ]
}


DEPLOYMENT_TOOL_CONFIG = {
    "tools": [
        {
            "toolSpec": {
                "name": "get_recent_deployments",
                "description": (
                    "Check whether a recent deployment occurred for an incident. "
                    "Returns whether a deployment was detected. "
                    "Use this tool when investigating whether a recent deployment "
                    "may be related to an incident."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "incident": {
                                "type": "object",
                                "properties": {
                                    "recent_deployment": {
                                        "type": "boolean",
                                        "description": (
                                            "Whether a recent deployment occurred."
                                        )
                                    }
                                },
                                "required": ["recent_deployment"]
                            }
                        },
                        "required": ["incident"]
                    }
                }
            }
        }
    ]
}
