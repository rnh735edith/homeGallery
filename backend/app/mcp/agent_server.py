# HomeGallery MCP Server for Agent Control
"""
Provides tools for managing and monitoring agents via MCP protocol.

Tools:
- get_agent_status() — Status of all agents
- run_agent(name) — Trigger agent immediately
- stop_agent(name) — Stop an agent
- start_agent(name) — Start an agent
- get_task_queue(filter) — Query task queue
- cancel_task(task_id) — Cancel a running task
"""

import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("homegallery.mcp.agent")

# Tool Definitions
TOOLS = [
    {
        "name": "get_agent_status",
        "description": "Return status of all registered agents (name, running state, last run, processed count)",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "run_agent",
        "description": "Trigger an agent to run immediately",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Agent name (metadata, organization, enhancement, analysis, search)"}
            },
            "required": ["name"],
        },
    },
    {
        "name": "stop_agent",
        "description": "Stop a running agent",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Agent name"}
            },
            "required": ["name"],
        },
    },
    {
        "name": "start_agent",
        "description": "Start a stopped agent",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Agent name"}
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_task_queue",
        "description": "Query the task queue with optional filters",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filter by status (pending, running, completed, failed)"},
                "type": {"type": "string", "description": "Filter by agent type"},
                "limit": {"type": "integer", "description": "Max results (default: 50)"},
            },
            "required": [],
        },
    },
    {
        "name": "cancel_task",
        "description": "Cancel a running or pending task",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID to cancel"}
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "get_processing_stats",
        "description": "Return overall processing statistics (total photos, processed by agent, pending)",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


def handle_tool_call(name: str, arguments: dict) -> dict:
    """Route tool call to appropriate function.
    
    Note: These functions need to connect to the running FastAPI app.
    In production, this would use HTTP calls to the API endpoints.
    """
    try:
        import urllib.request
        import urllib.parse

        api_base = os.environ.get("API_BASE_URL", "http://localhost:8080/api")

        if name == "get_agent_status":
            url = f"{api_base}/agents/status"
            with urllib.request.urlopen(url) as resp:
                return json.loads(resp.read())

        elif name == "run_agent":
            agent_name = arguments["name"]
            url = f"{api_base}/agents/{agent_name}/run"
            req = urllib.request.Request(url, method="POST")
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())

        elif name == "stop_agent":
            agent_name = arguments["name"]
            url = f"{api_base}/agents/{agent_name}/stop"
            req = urllib.request.Request(url, method="POST")
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())

        elif name == "start_agent":
            agent_name = arguments["name"]
            url = f"{api_base}/agents/{agent_name}/start"
            req = urllib.request.Request(url, method="POST")
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())

        elif name == "get_task_queue":
            params = {}
            if "status" in arguments:
                params["status"] = arguments["status"]
            if "type" in arguments:
                params["type"] = arguments["type"]
            if "limit" in arguments:
                params["limit"] = str(arguments["limit"])

            query = urllib.parse.urlencode(params)
            url = f"{api_base}/queue/tasks?{query}" if query else f"{api_base}/queue/tasks"
            with urllib.request.urlopen(url) as resp:
                return json.loads(resp.read())

        elif name == "cancel_task":
            task_id = arguments["task_id"]
            url = f"{api_base}/queue/tasks/{task_id}/cancel"
            req = urllib.request.Request(url, method="POST")
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())

        elif name == "get_processing_stats":
            # Aggregate stats from agents
            url = f"{api_base}/agents/status"
            with urllib.request.urlopen(url) as resp:
                agents = json.loads(resp.read())
                stats = {"agents": []}
                for agent in agents:
                    stats["agents"].append({
                        "name": agent.get("name"),
                        "running": agent.get("running", False),
                        "processed": agent.get("total_processed", 0),
                        "last_run": agent.get("last_run"),
                        "errors": len(agent.get("errors", [])),
                    })
                return stats

        else:
            return {"error": f"Unknown tool: {name}"}

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import sys

    def send_response(response: dict):
        json.dump(response, sys.stdout)
        sys.stdout.write("\n")
        sys.stdout.flush()

    # Send tools list
    send_response({"tools": TOOLS})

    # Process tool calls
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            tool_name = request.get("tool")
            arguments = request.get("arguments", {})
            result = handle_tool_call(tool_name, arguments)
            send_response({"tool": tool_name, "result": result})
        except Exception as e:
            send_response({"error": str(e)})
