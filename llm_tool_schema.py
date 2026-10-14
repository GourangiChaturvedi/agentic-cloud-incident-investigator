
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