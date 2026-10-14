
CPU_TOOL_CONFIG = {
    "tools": [
        {
            "toolSpec": {
                "name": "get_cpu_metrics",
                "description": (
                    "Check CPU usage for an incident. "
                    "Returns the CPU percentage and whether usage is high. "
                    "Use this tool when investigating CPU-related incidents."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "incident": {
                                "type": "object",
                                "properties": {
                                    "cpu_usage_percent": {
                                        "type": "number",
                                        "description": (
                                            "CPU utilization percentage, "
                                            "from 0 to 100."
                                        )
                                    }
                                },
                                "required": ["cpu_usage_percent"]
                            }
                        },
                        "required": ["incident"]
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
