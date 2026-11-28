"""
The tracker's data API (#241). The browser reads and writes through these routes instead of Firestore, so the
database behind them (WILO_DB, wilo/data.py connect) can change without the pages knowing. Each request carries
the Firebase ID token (Authorization: Bearer ...); the uid comes only from it. Mounted beside /chat on the same
server (wilo/mcp_server.py make_server).

    GET   /api/workouts?from=YYYY-MM-DD&to=YYYY-MM-DD   {"workouts": [{docId, ...doc}]} newest first
    GET   /api/workouts/{docId}                          {docId, ...doc}
    PATCH /api/workouts/{docId}   {log, logBase, status, updatedAt, finishedAt, rating}: any of them; 404 if missing
    PUT   /api/workouts/{docId}   a workout logged with no plan; 409 if it exists
    GET   /api/records                                   {"exercises": {...}, "updatedAt"} or {}
    PUT   /api/records            {"exercises": {...}}

The limits are firestore.rules' (wilo/data.py TRACKER_FIELDS, create_logged, set_records).
"""

import re
from datetime import datetime, timezone

from wilo import data as wilo_data

DAY = re.compile(r'\d{4}-\d{2}-\d{2}')
DOC_ID = re.compile(r'[^/]{1,200}')


def headers(request):
    """CORS for the tracker's own origins (wilo/chat.py ORIGIN), with the methods these routes use."""
    from wilo.chat import ORIGIN
    origin = request.headers.get('origin', '')
    if not ORIGIN.fullmatch(origin):
        return {}
    return {'Access-Control-Allow-Origin': origin, 'Vary': 'Origin',
            'Access-Control-Allow-Methods': 'GET, PUT, PATCH, OPTIONS',
            'Access-Control-Allow-Headers': 'Authorization, Content-Type', 'Access-Control-Max-Age': '600'}


def add_api_routes(s, db, verify=None):
    """db: a function returning the database (mcp_server.db). verify(token) -> uid; default: Firebase."""
    from starlette.responses import JSONResponse, Response

    def firebase_uid(token):
        from firebase_admin import auth as firebase_auth
        db()  # initialises the Firebase app the token check needs
        return firebase_auth.verify_id_token(token)['uid']

    check = verify or firebase_uid

    def route(path, methods):
        """Wraps a handler(request, uid, h): CORS, preflight, sign-in, and JSON errors."""
        def wrap(fn):
            async def handler(request):
                h = headers(request)
                if request.method == 'OPTIONS':
                    return Response(status_code=204, headers=h)
                try:
                    uid = check(request.headers.get('authorization', '').removeprefix('Bearer ').strip())
                except Exception:
                    return JSONResponse({'error': 'sign in again'}, status_code=401, headers=h)
                return await fn(request, uid, h)
            handler.__name__ = fn.__name__
            s.custom_route(path, methods=[*methods, 'OPTIONS'])(handler)
            return fn
        return wrap

    async def body(request):
        try:
            out = await request.json()
        except Exception:
            return None
        return out if isinstance(out, dict) else None

    def result(out, h, ok=200):
        if out.get('ok'):
            return JSONResponse(out, status_code=ok, headers=h)
        status = 404 if out.get('notFound') else 409 if out.get('exists') else 400
        return JSONResponse({'error': '; '.join(out['errors'])}, status_code=status, headers=h)

    @route('/api/workouts', ['GET'])
    async def list_workouts(request, uid, h):
        start, end = request.query_params.get('from'), request.query_params.get('to')
        if any(d and not DAY.fullmatch(d) for d in (start, end)):
            return JSONResponse({'error': 'from/to: YYYY-MM-DD'}, status_code=400, headers=h)
        return JSONResponse({'workouts': wilo_data.tracker_workouts(db(), uid, start, end)}, headers=h)

    @route('/api/workouts/{doc_id}', ['GET', 'PATCH', 'PUT'])
    async def workout(request, uid, h):
        doc_id = request.path_params['doc_id']
        if not DOC_ID.fullmatch(doc_id):
            return JSONResponse({'error': 'bad docId'}, status_code=400, headers=h)
        if request.method == 'GET':
            out = wilo_data.get(db(), uid, doc_id)
            if out.get('ok') is False:
                return JSONResponse({'error': 'not found'}, status_code=404, headers=h)
            return JSONResponse(out, headers=h)
        fields = await body(request)
        if fields is None:
            return JSONResponse({'error': 'send a JSON object'}, status_code=400, headers=h)
        if request.method == 'PATCH':
            return result(wilo_data.save_log(db(), uid, doc_id, fields), h)
        return result(wilo_data.create_logged(db(), uid, doc_id, fields), h, ok=201)

    @route('/api/records', ['GET', 'PUT'])
    async def records(request, uid, h):
        if request.method == 'GET':
            return JSONResponse(wilo_data.get_records(db(), uid), headers=h)
        fields = await body(request)
        if fields is None or 'exercises' not in fields:
            return JSONResponse({'error': 'send {"exercises": {...}}'}, status_code=400, headers=h)
        return result(wilo_data.set_records(db(), uid, fields['exercises'], datetime.now(timezone.utc)), h)
