"""Tool definitions and handlers for WILO MCP server."""

import os
import sys
import json
from typing import Any, Dict

# Import wilo_fs
from wilo_fs import session as get_session, latest_session, get_doc, query, list_docs, create_program, WiloError

# Get auth session
def auth_session():
    """Get authenticated Firestore session."""
    try:
        return get_session()
    except WiloError as e:
        raise RuntimeError(f"Auth failed: {e}")

# Tool definitions
TOOLS = {
    "wilo/latest-session": {
        "description": "Get the most recent finished workout session",
        "inputSchema": {"type": "object", "properties": {}},
    },
    "wilo/get-session": {
        "description": "Get a specific finished workout session by ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Session document ID"}
            },
            "required": ["id"]
        },
    },
    "wilo/history": {
        "description": "Get recent finished workout sessions",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to look back (0 = all)"},
                "limit": {"type": "integer", "description": "Max sessions to return"}
            }
        },
    },
    "wilo/list-programs": {
        "description": "Get planned workout programs",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max programs to return"}
            }
        },
    },
    "wilo/get-program": {
        "description": "Get a specific planned workout program by ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Program document ID"}
            },
            "required": ["id"]
        },
    },
    "wilo/create-program": {
        "description": "Create a new planned workout program",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spec": {
                    "type": "object",
                    "description": "Program spec (simple shape: {name, notes?, exercises[]})"
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, validate but don't write"
                }
            },
            "required": ["spec"]
        },
    },
    "wilo/update-program": {
        "description": "Update an existing program, merging changes while preserving tracking data",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Program document ID"},
                "changes": {
                    "type": "object",
                    "description": "Changes to apply (exercises to add/remove/reorder)"
                }
            },
            "required": ["id", "changes"]
        },
    },
}

def handle_tool_call(tool_name: str, args: Dict[str, Any]) -> Any:
    """Route and execute a tool call."""

    if tool_name == "wilo/latest-session":
        s = auth_session()
        return latest_session(s)

    elif tool_name == "wilo/get-session":
        s = auth_session()
        return get_doc(s, "sessions", args["id"])

    elif tool_name == "wilo/history":
        s = auth_session()
        days = args.get("days", 21)
        limit = args.get("limit", 20)
        from wilo_fs import history
        return history(s, days=days or None, limit=limit)

    elif tool_name == "wilo/list-programs":
        s = auth_session()
        limit = args.get("limit", 50)
        return list_docs(s, "programs", limit)

    elif tool_name == "wilo/get-program":
        s = auth_session()
        return get_doc(s, "programs", args["id"])

    elif tool_name == "wilo/create-program":
        spec = args["spec"]
        dry_run = args.get("dry_run", False)
        if dry_run:
            return create_program(None, spec, dry_run=True)
        else:
            s = auth_session()
            return create_program(s, spec)

    elif tool_name == "wilo/update-program":
        # TODO: implement update logic
        raise NotImplementedError("wilo/update-program not yet implemented")

    else:
        raise ValueError(f"Unknown tool: {tool_name}")
