import json
from wilo import data
db = data.connect()
u = [d.id for d in db.collection('users').stream() if d.id.startswith('iHi6rR')][0]
ds = data.recent(db, u, 'completed', 10)
full = len(json.dumps(ds, default=str))
def slim(w):
    return {'name': w.get('name'), 'finishedAt': w.get('finishedAt'),
            'ex': [{'n': e['name'], 's': [[s.get('reps'), s.get('lbs'), s.get('done')] for s in e['sets']]} for e in w['exercises']]}
s = len(json.dumps([slim(w) for w in ds], default=str))
print(len(ds), 'docs: full', full, 'chars; signal only', s, 'chars;', f'{100*s//full}%')
print(json.dumps(slim(ds[0]))[:400])
