"""Download a session document from Firestore to data/sessions/<id>.json.

Usage:
    GOOGLE_APPLICATION_CREDENTIALS=~/.config/wilo/service-account.json \\
        python scripts/fetch_session.py [session_id]

If session_id is omitted, fetches the latest session by finishedAt DESC.
"""

import json
import os
import sys
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

PROJECT_ID = "wilo2-1ee44"
DATABASE_ID = "wilo"
REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "data" / "sessions"


def main() -> None:
    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not key_path:
        sys.exit("GOOGLE_APPLICATION_CREDENTIALS env var is required")

    cred = credentials.Certificate(key_path)
    firebase_admin.initialize_app(cred, {"projectId": PROJECT_ID})
    db = firestore.client(database_id=DATABASE_ID)

    if len(sys.argv) > 1:
        session_id = sys.argv[1]
        snap = db.collection("sessions").document(session_id).get()
        if not snap.exists:
            sys.exit(f"no session {session_id}")
    else:
        results = list(
            db.collection("sessions")
            .order_by("finishedAt", direction=firestore.Query.DESCENDING)
            .limit(1)
            .stream()
        )
        if not results:
            sys.exit("no sessions found")
        snap = results[0]
        session_id = snap.id

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{session_id}.json"
    with out_path.open("w") as f:
        json.dump(snap.to_dict(), f, indent=2, default=str)

    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
