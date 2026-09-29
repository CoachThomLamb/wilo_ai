# WILO MCP Server

MCP (Model Context Protocol) server for the WILO workout coach. Exposes Firestore workout data and coaching logic as callable tools.

## Setup

1. Install dependencies:
```bash
pip install google-auth requests
```

2. Set up credentials (one of):
```bash
export WILO_SA_KEY=/path/to/service-account.json
# OR
export WILO_SA_JSON='{"type":"service_account",...}'
# OR place at ~/.wilo-claude/service-account.json
```

## Running

```bash
python3 mcp/server.py
```

The server reads JSON-RPC requests from stdin and writes responses to stdout. Perfect for integration with Claude via MCP.

## Tools

### Firestore Data Access

- `wilo/latest-session` — Get most recent finished workout
- `wilo/get-session` — Get specific session by ID
- `wilo/history` — Get recent sessions (with --days, --limit)
- `wilo/list-programs` — Get planned workouts
- `wilo/get-program` — Get specific program by ID
- `wilo/create-program` — Create new program (simple or full shape)
- `wilo/update-program` — Update program, merging changes while preserving tracking data

### Coaching Logic (WIP)

- `wilo/analyze-workout` — Analyze session: volume, trends, pain flags, completion
- `wilo/check-in` — Generate check-in recap + questions
- `wilo/build-next-workout` — Generate next workout spec

## Architecture

- `server.py` — MCP protocol (JSON-RPC over stdio)
- `tools.py` — Tool handlers; wires up wilo_fs.py functions
- `coaching.py` — Coaching logic; analysis, check-in, workout building
- `../scripts/wilo_fs.py` — Firestore abstraction layer (unchanged)

## Protocol

MCP uses JSON-RPC 2.0:

```json
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "wilo/latest-session", "arguments": {}}}
```

## Next Steps

- [ ] Implement `wilo/update-program` (merge changes, preserve tracking)
- [ ] Implement coaching analysis tools (analyze-workout, check-in, build-next-workout)
- [ ] Add error handling and logging
- [ ] Test with Claude MCP integration
