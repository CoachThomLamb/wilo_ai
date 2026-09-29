#!/usr/bin/env python3
"""WILO MCP Server — exposes Firestore workout coach as MCP tools."""

import json
import sys
import os
from typing import Any

# Add scripts to path so we can import wilo_fs
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from tools import TOOLS, handle_tool_call

def log(msg: str):
    """Log to stderr."""
    print(msg, file=sys.stderr, flush=True)

def send_response(response: dict):
    """Send JSON response to stdout."""
    json.dump(response, sys.stdout)
    sys.stdout.write('\n')
    sys.stdout.flush()

def handle_request(request: dict) -> dict:
    """Route and handle a JSON-RPC request."""
    method = request.get("method")
    params = request.get("params", {})
    req_id = request.get("id")

    # Initialize
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "wilo-mcp",
                    "version": "0.1.0"
                }
            }
        }

    # List tools
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": tool_name,
                        "description": tool_def["description"],
                        "inputSchema": tool_def.get("inputSchema", {})
                    }
                    for tool_name, tool_def in TOOLS.items()
                ]
            }
        }

    # Call tool
    if method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        if tool_name not in TOOLS:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Tool not found: {tool_name}"
                }
            }

        try:
            result = handle_tool_call(tool_name, tool_args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }
        except Exception as e:
            log(f"Tool error: {tool_name}: {e}")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }

    # Unknown method
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": -32601,
            "message": f"Unknown method: {method}"
        }
    }

def main():
    """Read JSON-RPC requests from stdin, route, send responses to stdout."""
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
                response = handle_request(request)
                send_response(response)
            except json.JSONDecodeError as e:
                log(f"JSON decode error: {e}")
                send_response({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                })
            except Exception as e:
                log(f"Request error: {e}")
                send_response({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                })
    except KeyboardInterrupt:
        log("Shutdown")
        sys.exit(0)

if __name__ == "__main__":
    main()
