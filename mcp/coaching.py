"""Coaching logic for WILO workout coach."""

from typing import Any, Dict, List

def analyze_workout(session: Dict[str, Any], history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Analyze a finished workout and recent history.

    Returns:
    {
        "volume": {...},              # reps × weight per exercise
        "custom_trends": {...},        # custom field trends (e.g., riser height)
        "pain_flags": [...],           # exercises with pain/injury cues
        "completion": {...},           # % of planned sets done
        "progression_notes": [...]     # per-exercise progression observations
    }
    """

    if not session or not session.get('sessions'):
        return {"error": "Invalid session format"}

    analysis = {
        "session_id": session.get('_id'),
        "session_name": session.get('program', {}).get('name'),
        "volume": {},
        "custom_trends": {},
        "pain_flags": [],
        "completion": {},
        "progression_notes": []
    }

    # Extract exercises from the session
    blocks = session.get('sessions', [{}])[0].get('blocks', [])
    if not blocks:
        return analysis

    exercises = blocks[0].get('exercises', [])

    # Per-exercise analysis
    for ex in exercises:
        ex_name = ex.get('name', 'unknown')
        sets = ex.get('sets', [])

        if not sets:
            continue

        # Volume: total reps × max weight
        total_reps = sum(s.get('reps') or 0 for s in sets if isinstance(s.get('reps'), int))
        max_weight = max((s.get('lbs') or 0) for s in sets if isinstance(s.get('lbs'), (int, float)))

        analysis['volume'][ex_name] = {
            "total_reps": total_reps,
            "max_weight": max_weight,
            "sets_done": sum(1 for s in sets if s.get('done'))
        }

        # Custom value trends
        if ex.get('custom_name'):
            custom_values = [s.get('custom') for s in sets if s.get('custom')]
            if custom_values:
                analysis['custom_trends'][ex_name] = {
                    "name": ex.get('custom_name'),
                    "values": custom_values
                }

        # Pain/injury flags from cues
        cue = ex.get('cue', '').lower()
        if any(word in cue for word in ['pain', 'twinge', 'hurt', 'ache', 'injured', 'sore']):
            analysis['pain_flags'].append({
                "exercise": ex_name,
                "cue": ex.get('cue')
            })

        # Completion rate
        done_count = sum(1 for s in sets if s.get('done'))
        analysis['completion'][ex_name] = {
            "planned": len(sets),
            "completed": done_count,
            "rate": done_count / len(sets) if sets else 0
        }

    return analysis

def generate_checkin(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a check-in with recap and questions.

    Returns:
    {
        "recap": "...",          # 2-4 line summary
        "questions": [...]       # 3-5 check-in questions
    }
    """

    recap_lines = []
    questions = []

    # Build recap
    if analysis.get('pain_flags'):
        recap_lines.append(f"Noted pain/issues in: {', '.join(f['exercise'] for f in analysis['pain_flags'])}")

    completed = sum(1 for v in analysis.get('completion', {}).values() if v['rate'] == 1.0)
    total = len(analysis.get('completion', {}))
    if total > 0:
        recap_lines.append(f"Completed {completed}/{total} exercises")

    recap = " | ".join(recap_lines) if recap_lines else "Workout logged"

    # Build questions
    if analysis.get('pain_flags'):
        questions.append(f"How did the pain/twinges feel since? (0-10)")

    questions.extend([
        "Energy today? Time available?",
        "What's next: legs, upper, cardio, recovery?",
        "Anything to avoid or push?"
    ])

    return {
        "recap": recap,
        "questions": questions[:5]  # Limit to 5
    }

def build_next_workout(
    analysis: Dict[str, Any],
    user_input: str,
    previous_program: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Generate the next workout spec based on analysis and user feedback.

    Returns simple shape:
    {
        "name": "...",
        "notes": "...",
        "exercises": [...]
    }
    """

    # Placeholder: for now just return a template
    return {
        "name": "Next workout (template)",
        "notes": "User feedback: " + user_input[:100],
        "exercises": []
    }
