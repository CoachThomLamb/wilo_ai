import os, json, requests

RUNPOD_API_KEY = os.environ["RUNPOD_API_KEY"]
ENDPOINT_ID = os.environ.get("RUNPOD_PUBLIC_ENDPOINT_ID", "").strip()
assert ENDPOINT_ID, "Set RUNPOD_PUBLIC_ENDPOINT_ID to the public endpoint id (e.g. cm...)"

URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync"

HISTORY_PATH = "history.json"

SYSTEM = """You are a practical strength & conditioning coach.
You ask 3-8 clarifying questions, then propose a workout plan.
You must respect constraints: available days, time, equipment, injuries, preferences.
Output the final plan as JSON with fields:
- questions (array)
- assumptions (array)
- weekly_plan (array of days with exercises, sets, reps, RPE, rest, notes)
- progression (string)
- deload_rule (string)
"""

def load_history():
    if not os.path.exists(HISTORY_PATH):
        return [{"role": "system", "content": SYSTEM}]
    with open(HISTORY_PATH, "r") as f:
        return json.load(f)

def save_history(messages):
    with open(HISTORY_PATH, "w") as f:
        json.dump(messages, f, indent=2)

def run_chat(user_msg: str):
    messages = load_history()
    messages.append({"role": "user", "content": user_msg})

    payload = {
        "input": {
            "messages": messages
        }
    }

    r = requests.post(
        URL,
        headers={"Authorization": RUNPOD_API_KEY, "Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=600,
    )
    r.raise_for_status()
    out = r.json()

    # Different public endpoints sometimes wrap output differently.
    # Print the whole response so you can see the shape once, then we’ll tighten parsing.
    print(json.dumps(out, indent=2))

    # Best-effort: append assistant text if present
    assistant_text = None
    if isinstance(out, dict):
        # common shapes: out["output"]["text"] or out["output"][0]...
        output = out.get("output")
        if isinstance(output, dict):
            assistant_text = output.get("text") or output.get("output_text")
        elif isinstance(output, str):
            assistant_text = output

    if assistant_text:
        messages.append({"role": "assistant", "content": assistant_text})
        save_history(messages)

if __name__ == "__main__":
    print("Type your message. Ctrl+C to exit.")
    while True:
        try:
            msg = input("\nYou: ").strip()
            if not msg:
                continue
            run_chat(msg)
        except KeyboardInterrupt:
            print("\nExiting.")
            break

