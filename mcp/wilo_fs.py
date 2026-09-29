#!/usr/bin/env python3
"""wilo_fs — Firestore plumbing for the WILO workout coach.

Owns the current WILO Firestore contract so callers (Claude, scripts, a future
MCP server) never hand-build REST calls or Firestore value encodings.

Contract (current — see SKILL.md):
  project  wilo2-1ee44
  database wilo            (named DB, not "(default)")
  sessions/{id}            finished workouts   (read only)
  programs/{id}            planned workouts    (create only)
  doc id                   {program.id}-{timestamp_ms}, program.id = prog_<ms>
  planned workouts         every set done=false, finishedAt=null

Auth (first match wins):
  --key PATH
  WILO_SA_KEY=PATH         path to service account JSON
  WILO_SA_JSON='{...}'     the JSON itself
  ~/wilo-claude/service-account.json

Commands (all print JSON to stdout; errors go to stderr as JSON, exit 1):
  latest                       most recent finished session
  get ID                       one session
  history [--days N] [--limit N]
                               recent sessions, newest first
  programs [--limit N]         planned workouts
  get-program ID               one program
  create-program FILE|- [--dry-run]
                               create a program from JSON (simple or full shape)

Requires: pip install google-auth requests
"""
from __future__ import annotations

import argparse
import json
import os
import random
import string
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PROJECT = "wilo2-1ee44"
DATABASE = "wilo"
SESSIONS = "sessions"
PROGRAMS = "programs"
BASE = f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/{DATABASE}/documents"
SCOPES = ["https://www.googleapis.com/auth/datastore"]
DEFAULT_KEY = Path.home() / "wilo-claude" / "service-account.json"


class WiloError(Exception):
    pass


# --------------------------------------------------------------------------- auth

def session(key_path: str | None = None):
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import AuthorizedSession
    except ImportError as e:  # pragma: no cover
        raise WiloError("missing dependency: pip install google-auth requests") from e

    path = key_path or os.environ.get("WILO_SA_KEY")
    raw = os.environ.get("WILO_SA_JSON")
    if path:
        creds = service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
    elif raw:
        creds = service_account.Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    elif DEFAULT_KEY.exists():
        creds = service_account.Credentials.from_service_account_file(str(DEFAULT_KEY), scopes=SCOPES)
    else:
        raise WiloError("no credentials: pass --key, or set WILO_SA_KEY or WILO_SA_JSON")
    return AuthorizedSession(creds)


# ----------------------------------------------------------------- value codec

def enc(v: Any) -> dict:
    """Python -> Firestore REST value."""
    if v is None:
        return {"nullValue": None}
    if isinstance(v, bool):
        return {"booleanValue": v}
    if isinstance(v, int):
        return {"integerValue": str(v)}
    if isinstance(v, float):
        return {"doubleValue": v}
    if isinstance(v, str):
        return {"stringValue": v}
    if isinstance(v, list):
        return {"arrayValue": {"values": [enc(x) for x in v]}}
    if isinstance(v, dict):
        return {"mapValue": {"fields": {k: enc(x) for k, x in v.items()}}}
    raise WiloError(f"cannot encode {type(v).__name__}")


def dec(v: dict) -> Any:
    """Firestore REST value -> Python."""
    if "nullValue" in v:
        return None
    if "mapValue" in v:
        return {k: dec(x) for k, x in v["mapValue"].get("fields", {}).items()}
    if "arrayValue" in v:
        return [dec(x) for x in v["arrayValue"].get("values", [])]
    if "integerValue" in v:
        return int(v["integerValue"])
    if "doubleValue" in v:
        return float(v["doubleValue"])
    return next(iter(v.values()))  # string, boolean, timestamp, reference, ...


def doc_to_dict(doc: dict) -> dict:
    out = {k: dec(x) for k, x in doc.get("fields", {}).items()}
    out["_id"] = doc["name"].rsplit("/", 1)[-1]
    return out


# --------------------------------------------------------------------- reads

def _check(r) -> dict:
    try:
        body = r.json()
    except ValueError:
        body = {"raw": r.text}
    if r.status_code >= 400:
        err = body.get("error", body) if isinstance(body, dict) else body
        raise WiloError(f"HTTP {r.status_code}: {json.dumps(err)}")
    return body


def get_doc(s, collection: str, doc_id: str) -> dict:
    return doc_to_dict(_check(s.get(f"{BASE}/{collection}/{doc_id}")))


def query(s, collection: str, limit: int = 10, since_iso: str | None = None) -> list[dict]:
    q: dict = {
        "from": [{"collectionId": collection}],
        "orderBy": [{"field": {"fieldPath": "finishedAt"}, "direction": "DESCENDING"}],
        "limit": limit,
    }
    if since_iso:
        # finishedAt is stored as an ISO-8601 string, so string comparison sorts by time.
        q["where"] = {"fieldFilter": {"field": {"fieldPath": "finishedAt"},
                                      "op": "GREATER_THAN_OR_EQUAL",
                                      "value": {"stringValue": since_iso}}}
    rows = _check(s.post(f"{BASE}:runQuery", json={"structuredQuery": q}))
    return [doc_to_dict(r["document"]) for r in rows if "document" in r]


def list_docs(s, collection: str, limit: int = 50) -> list[dict]:
    body = _check(s.get(f"{BASE}/{collection}", params={"pageSize": limit}))
    return [doc_to_dict(d) for d in body.get("documents", [])]


def latest_session(s) -> dict:
    rows = query(s, SESSIONS, limit=1)
    if not rows:
        raise WiloError("no sessions found")
    return rows[0]


def history(s, days: int | None = 21, limit: int = 20) -> list[dict]:
    since = None
    if days:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return query(s, SESSIONS, limit=limit, since_iso=since)


# ----------------------------------------------------------- program building

def _rand5() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=5))


def _num_or_blank(v: Any, field: str, where: str):
    if v is None or v == "":
        return ""  # current contract uses "" for empty reps/lbs
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise WiloError(f"{where}: {field} must be a number or empty, got {v!r}")
    return int(v) if isinstance(v, float) and v.is_integer() else v


def _norm_set(st: dict, where: str) -> dict:
    if not isinstance(st, dict):
        raise WiloError(f"{where}: set must be an object")
    custom = st.get("custom")
    return {
        "custom": None if custom in (None, "") else str(custom),
        "done": False,
        "reps": _num_or_blank(st.get("reps"), "reps", where),
        "lbs": _num_or_blank(st.get("lbs"), "lbs", where),
    }


def _norm_exercise(ex: dict, n: int) -> dict:
    where = f"exercise {n}"
    name = (ex.get("name") or "").strip()
    if not name:
        raise WiloError(f"{where}: name is required")
    sets = ex.get("sets")
    if not isinstance(sets, list) or not sets:
        raise WiloError(f"{where} ({name}): sets must be a non-empty list")
    custom_name = ex.get("custom_name") or None
    norm_sets = [_norm_set(st, f"{where} ({name}) set {i + 1}") for i, st in enumerate(sets)]
    if not custom_name and any(st["custom"] for st in norm_sets):
        raise WiloError(f"{where} ({name}): sets use custom but custom_name is missing")
    return {
        "timed": bool(ex.get("timed", False)),
        "id": f"ex{n}-{_rand5()}",
        "name": name,
        "custom_name": custom_name,
        "swapped": False,
        "sets": norm_sets,
        "cue": ex.get("cue") or "",
    }


def build_program(spec: dict, now_ms: int | None = None) -> tuple[str, dict]:
    """Accepts either the simple shape
         {"name": str, "notes"?: str, "exercises": [ {name, custom_name?, timed?, cue?,
                                                      sets: [{reps, lbs, custom?}]} ]}
       or the full WILO doc shape (with "sessions"); exercises are taken from all blocks.
       Returns (doc_id, document) in the current WILO contract."""
    if not isinstance(spec, dict):
        raise WiloError("program spec must be a JSON object")
    if "sessions" in spec:
        name = spec.get("program", {}).get("name") or spec["sessions"][0].get("name")
        blocks = [b for sess in spec["sessions"] for b in sess.get("blocks", [])]
        exercises = [e for b in blocks for e in b.get("exercises", [])]
        notes = blocks[0].get("notes", "") if blocks else ""
    else:
        name = spec.get("name")
        exercises = spec.get("exercises") or []
        notes = spec.get("notes", "")
    name = (name or "").strip()
    if not name:
        raise WiloError("program name is required")
    if not exercises:
        raise WiloError("program needs at least one exercise")

    now_ms = now_ms or int(time.time() * 1000)
    pid = f"prog_{now_ms}"
    doc = {
        "program": {"id": pid, "name": name},
        "sessions": [{
            "id": pid,
            "name": name,
            "blocks": [{
                "id": "blk_default",
                "name": "",
                "notes": notes or "",
                "exercises": [_norm_exercise(e, i + 1) for i, e in enumerate(exercises)],
            }],
        }],
        "finishedAt": None,
    }
    return f"{pid}-{now_ms}", doc


def create_program(s, spec: dict, dry_run: bool = False) -> dict:
    doc_id, doc = build_program(spec)
    if dry_run:
        return {"dry_run": True, "_id": doc_id, **doc}
    # POST with documentId is create-only: Firestore returns 409 if the id exists.
    body = _check(s.post(f"{BASE}/{PROGRAMS}", params={"documentId": doc_id},
                         json={"fields": {k: enc(v) for k, v in doc.items()}}))
    return doc_to_dict(body)


# ----------------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="wilo_fs", description="WILO Firestore plumbing")
    p.add_argument("--key", help="path to service account JSON")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("latest")
    g = sub.add_parser("get"); g.add_argument("id")
    h = sub.add_parser("history")
    h.add_argument("--days", type=int, default=21, help="0 = no date filter")
    h.add_argument("--limit", type=int, default=20)
    pr = sub.add_parser("programs"); pr.add_argument("--limit", type=int, default=50)
    gp = sub.add_parser("get-program"); gp.add_argument("id")
    cp = sub.add_parser("create-program")
    cp.add_argument("file", help="JSON file, or - for stdin")
    cp.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)

    try:
        if a.cmd == "create-program":
            text = sys.stdin.read() if a.file == "-" else Path(a.file).read_text()
            try:
                spec = json.loads(text)
            except json.JSONDecodeError as e:
                raise WiloError(f"invalid JSON: {e}")
            if a.dry_run:
                out = create_program(None, spec, dry_run=True)
            else:
                out = create_program(session(a.key), spec)
        else:
            s = session(a.key)
            if a.cmd == "latest":
                out = latest_session(s)
            elif a.cmd == "get":
                out = get_doc(s, SESSIONS, a.id)
            elif a.cmd == "history":
                out = history(s, days=a.days or None, limit=a.limit)
            elif a.cmd == "programs":
                out = list_docs(s, PROGRAMS, a.limit)
            elif a.cmd == "get-program":
                out = get_doc(s, PROGRAMS, a.id)
        json.dump(out, sys.stdout, indent=2)
        print()
        return 0
    except WiloError as e:
        json.dump({"error": str(e)}, sys.stderr)
        print(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
