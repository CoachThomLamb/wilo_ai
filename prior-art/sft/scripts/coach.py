#!/usr/bin/env python3
"""Chat with Qwen about your workout history."""
import json, csv, sys, urllib.request, urllib.error, glob, os
from datetime import datetime

OLLAMA_URL = "http://10.0.0.117:11434/api/generate"
MODEL = "qwen2.5:3b"
CSV_PATH = "/home/thom/wilo/workout_data (1).csv"
JSON_GLOB = "/home/thom/wilo/fe/sess_*.json"

def load_csv(path):
    with open(path, newline="") as f:
        return f.read()

def load_jsons(pattern):
    parts = []
    for p in sorted(glob.glob(pattern)):
        with open(p) as f:
            parts.append(f"--- {p} ---\n{f.read()}")
    return "\n\n".join(parts)

def build_system():
    csv_data = load_csv(CSV_PATH)
    json_data = load_jsons(JSON_GLOB)
    return f"""You are a personal strength coach. You have access to the user's full workout history.

## Hevy CSV export (all sets):
{csv_data}

## Recent WILO session JSONs:
{json_data}

Use this data to answer questions, track progress, and suggest next workouts."""

def chat(system, history, user_input):
    prompt = system + "\n\n"
    for role, content in history:
        prompt += f"{role.upper()}: {content}\n"
    prompt += f"USER: {user_input}\nCOACH:"
    payload = json.dumps({"model": MODEL, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["response"]

def main():
    print("Loading workout data...")
    system = build_system()
    history = []
    log_path = f"/home/thom/wilo/coach_ai/logs/{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}.md"
    print("Ready. Type your question (Ctrl+C to quit).\n")

    with open(log_path, "w") as log:
        log.write(f"# Coach session {datetime.now().isoformat()}\n\n")

        while True:
            try:
                user_input = input("You: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nBye.")
                break
            if not user_input:
                continue
            print("Coach: ", end="", flush=True)
            try:
                reply = chat(system, history, user_input)
                print(reply)
                history.append(("user", user_input))
                history.append(("coach", reply))
                log.write(f"**You:** {user_input}\n\n**Coach:** {reply}\n\n---\n\n")
                log.flush()
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    main()
