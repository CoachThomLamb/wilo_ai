"""Helpers for hand-written synthetic training items (eval item format). Content is authored in batchN.py.

    cd ml/synth && python batch1.py     # (re)writes items synth-001..050 in ml/train_synth.jsonl
"""
import copy
import json
import re
from pathlib import Path

ML = Path(__file__).resolve().parent.parent
OUT = ML / 'train_synth.jsonl'
MON = {'09': 'sep', '10': 'oct', '11': 'nov'}


def sets(spec):
    """'3x10@45' | '3x10' | 't300' (timed seconds) | '2x45t' | '4x6@5 RL' (alternating sides)."""
    spec = spec.strip()
    side = None
    if spec.endswith(' RL'):
        spec, side = spec[:-3], ['R', 'L']
    if spec.startswith('t'):
        return [{'reps': int(spec[1:]), 'lbs': 0, 'done': False}]
    timed = spec.endswith('t')
    spec = spec.rstrip('t')
    m = re.fullmatch(r'(\d+)x(\d+)(?:@(\d+))?', spec)
    n, reps, lbs = int(m[1]), int(m[2]), m[3]
    out = []
    for i in range(n * (2 if side else 1)):
        s = {'reps': reps, 'lbs': int(lbs) if lbs else ('' if timed else 0), 'done': False}
        if side:
            s['custom'] = side[i % 2]
        out.append(s)
    return out


def ex(name, spec, cue=None):
    e = {'name': name}
    if spec.startswith('t') or spec.endswith('t'):
        e['timed'] = True
    if spec.endswith(' RL'):
        e['custom_name'] = 'Side'
    if cue:
        e['cue'] = cue
    e['sets'] = sets(spec)
    return e


def workout(name, date, exercises, wid=None):
    return {'id': wid or name, 'name': name, 'assignedFor': date, 'exercises': exercises}


def doc_id(name, date, hhmm):
    _, mm, dd = date.split('-')
    return f'{dd}-{MON[mm]}-{hhmm}-{name[:5]}'


def summary(w):
    """How Wilo lists a workout: '1. Treadmill 5 min 2. Leg press 3x10 @ 200 ...'"""
    parts = []
    for i, e in enumerate(w['exercises'], 1):
        s = e['sets']
        if e.get('timed'):
            r = s[0]['reps']
            desc = f'{r // 60} min' if r >= 120 and len(s) == 1 else f'{len(s)}x{r}s'
        else:
            n = len(s) // 2 if e.get('custom_name') == 'Side' else len(s)
            desc = f"{n}x{s[0]['reps']}" + (f" @ {s[-1]['lbs']}" if s[-1]['lbs'] not in (0, '') else '')
        parts.append(f"{i}. {e['name']} {desc}")
    return ' '.join(parts)


def edit(w, fn):
    w2 = copy.deepcopy(w)
    fn(w2['exercises'])
    return w2


def idx(exs, name):
    return next(i for i, e in enumerate(exs) if e['name'].lower().startswith(name.lower()))


def U(text):
    return {'role': 'user', 'text': text}


def A(text, *tools):
    d = {'role': 'assistant', 'text': text}
    if tools:
        d['tools'] = list(tools)
    return d


def item(n, date, context, message, tool, args=None, screen=None):
    """screen: (name, docId) of the on-screen workout, or None."""
    return {'id': f'synth-{n:03d}', 'source': 'synthetic', 'date': date, 'context': context[-6:],
            'screen': {'assignedDocId': screen[1], 'name': screen[0]} if screen else None,
            'message': message,
            'expected': {'tool': tool, 'args': args if tool else None, 'args_complete': True}, 'review': ''}


def write(items, start):
    tools = {t['function']['name']: t['function']['parameters'] for t in
             json.loads((ML / 'wilo_tools.json').read_text())}
    for it in items:
        t = it['expected']['tool']
        if t:
            p = tools[t]
            missing = [r for r in p.get('required', []) if r not in it['expected']['args']]
            extra = [k for k in it['expected']['args'] if k not in p['properties']]
            assert not missing and not extra, (it['id'], t, missing, extra)
    lines = [l for l in OUT.read_text().splitlines() if l] if OUT.exists() else []
    keep = [l for l in lines if not (start <= int(json.loads(l)["id"].split("-")[1]) < start + 50)]
    keep += [json.dumps(it, ensure_ascii=False) for it in items]
    OUT.write_text('\n'.join(sorted(keep, key=lambda l: json.loads(l)['id'])) + '\n')
    print(f'wrote {len(items)}; file has {len(keep)}')


# Edits for edit(w, ...): each returns a function that changes the exercise list in place.
def ins(after, e):
    """Insert e after the exercise named `after` ('' = at the start, None = at the end)."""
    def f(exs):
        exs.insert(0 if after == '' else len(exs) if after is None else idx(exs, after) + 1, e)
    return f


def rm(name):
    return lambda exs: exs.pop(idx(exs, name))


def rep(name, e):
    def f(exs):
        exs[idx(exs, name)] = e
    return f


def mv(name, after):
    def f(exs):
        e = exs.pop(idx(exs, name))
        exs.insert(0 if after == '' else idx(exs, after) + 1, e)
    return f


def swap(a, b):
    def f(exs):
        i, j = idx(exs, a), idx(exs, b)
        exs[i], exs[j] = exs[j], exs[i]
    return f


def resets(name, spec):
    def f(exs):
        e = exs[idx(exs, name)]
        e['sets'] = sets(spec)
    return f


def chain(*fs):
    def f(exs):
        for g in fs:
            g(exs)
    return f
