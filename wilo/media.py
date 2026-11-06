"""
Exercise videos and photos (#152): a client's form checks, and the coach's one demo per exercise.

The files live in Backblaze B2 (private bucket; Firebase Storage needs Blaze, which we can't turn on). The phone
uploads straight to B2 with a short-lived signed URL; this server only signs, after checking the Firebase ID token
and who may upload or see what. Same auth and allow-list as /chat.

    POST /media/upload  {kind: "form"|"demo", exercise, contentType, docId?, exId?}
                     →  {key, url, headers}         PUT the file to url with these headers within 10 minutes
    POST /media/done    {key, exercise?}
                     →  {key, type, size}           checks the upload (size cap); a demo becomes the exercise's demo
    POST /media/urls    {keys?: [...], demos?: [exercise names]}
                     →  {urls: {key: url}, demos: {name: {key, type, url}}, coach}   signed links to watch, 1 hour

Where things are:
    B2  users/{uid}/{docId}/{exId}/{stamp}.{ext}   a client's form video/photo; the tracker keeps the key in the
                                                   workout's log, on the exercise: media: [{key, type, at}]
    B2  demos/{slug}/{stamp}.{ext}                 the coach's demo
    Firestore exercise_media/{slug}                name, key, type, by, at: the current demo (server only)

Who: a client sees their own files and every demo. The coach (WILO_COACH_UIDS, default the config uid) uploads demos
and sees everyone's files. Video length (30 s form, 10 s demo) is checked in the browser; size is capped here.

Env: B2_KEY_ID, B2_APP_KEY, B2_BUCKET, B2_ENDPOINT (https://s3.<region>.backblazeb2.com), WILO_COACH_UIDS.
"""

import os
import re
import secrets
from datetime import datetime, timezone

from wilo import data as wilo_data

TYPES = {'video/mp4': 'mp4', 'video/quicktime': 'mov', 'video/webm': 'webm',
         'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp', 'image/heic': 'heic'}
MB = 1024 * 1024
LIMIT = {('form', 'video'): 100 * MB, ('demo', 'video'): 40 * MB, ('form', 'image'): 15 * MB, ('demo', 'image'): 15 * MB}
SECONDS = {'form': 30, 'demo': 10}  # enforced in the browser (it reads the video's duration before uploading)
PUT_EXPIRES, GET_EXPIRES = 600, 3600
ID = re.compile(r'[A-Za-z0-9:_.-]{1,80}')

_s3 = None


def s3():
    global _s3
    if _s3 is None:
        import boto3
        from botocore.config import Config
        _s3 = boto3.client('s3', endpoint_url=os.environ['B2_ENDPOINT'], aws_access_key_id=os.environ['B2_KEY_ID'],
                           aws_secret_access_key=os.environ['B2_APP_KEY'],
                           config=Config(signature_version='s3v4', region_name=_region()))
    return _s3


def _region():
    m = re.search(r's3\.([a-z0-9-]+)\.backblazeb2\.com', os.environ.get('B2_ENDPOINT', ''))
    return m.group(1) if m else 'us-east-1'


def bucket():
    return os.environ['B2_BUCKET']


def coach_uids():
    return {u.strip() for u in os.environ.get('WILO_COACH_UIDS', wilo_data.CONFIG['uid']).split(',') if u.strip()}


def slug(name):
    """Goblet Squat / goblet-squat / 'Goblet  squat ' all share one demo."""
    return re.sub(r'[^a-z0-9]+', '-', str(name).lower()).strip('-')[:80]


def kind_of(content_type):
    return content_type.split('/')[0] if content_type in TYPES else None


def may_see(uid, key):
    return key.startswith('demos/') or key.startswith(f'users/{uid}/') or uid in coach_uids()


def upload_key(uid, body, now):
    """(key, content_type) for a new upload, or raise ValueError with what's wrong."""
    kind, ctype = body.get('kind'), body.get('contentType')
    if kind not in ('form', 'demo'):
        raise ValueError('kind is form or demo')
    if ctype not in TYPES:
        raise ValueError(f'contentType is one of {", ".join(TYPES)}')
    stamp = f'{now:%Y%m%dT%H%M%S}-{secrets.token_hex(3)}.{TYPES[ctype]}'
    if kind == 'demo':
        if uid not in coach_uids():
            raise PermissionError('only the coach uploads demos')
        s = slug(body.get('exercise', ''))
        if not s:
            raise ValueError('exercise is required for a demo')
        return f'demos/{s}/{stamp}', ctype
    doc_id, ex_id = body.get('docId'), body.get('exId')
    if not (isinstance(doc_id, str) and ID.fullmatch(doc_id) and isinstance(ex_id, str) and ID.fullmatch(ex_id)):
        raise ValueError('a form video needs the workout docId and the exercise exId')
    return f'users/{uid}/{doc_id}/{ex_id}/{stamp}', ctype


def check_upload(key, head):
    """(kind, type, size) of a finished upload, or raise ValueError (too big, wrong type)."""
    kind = 'demo' if key.startswith('demos/') else 'form'
    ctype = head.get('ContentType', '')
    media = kind_of(ctype)
    if media is None:
        raise ValueError(f'unexpected file type {ctype!r}')
    size = head.get('ContentLength', 0)
    if size > LIMIT[(kind, media)]:
        raise ValueError(f'too big: {size // MB} MB, the limit is {LIMIT[(kind, media)] // MB} MB')
    return kind, media, size


def demos(db, names):
    """{name: {key, type}} for the names that have a demo."""
    out = {}
    for name in names:
        s = slug(name)
        snap = db.collection('exercise_media').document(s).get() if s else None
        if snap is not None and snap.exists:
            d = snap.to_dict()
            out[name] = {'key': d['key'], 'type': d['type']}
    return out


def add_media_routes(s):
    from starlette.responses import JSONResponse, Response
    from wilo import chat, mcp_server as srv

    def route(path):
        def wrap(handler):
            @s.custom_route(path, methods=['POST', 'OPTIONS'])
            async def endpoint(request):
                headers = chat.cors(request)
                if request.method == 'OPTIONS':
                    return Response(status_code=204, headers=headers)

                def fail(status, error):
                    return JSONResponse({'error': error}, status_code=status, headers=headers)

                from firebase_admin import auth as firebase_auth
                db = srv.db()
                try:
                    token = request.headers.get('authorization', '').removeprefix('Bearer ').strip()
                    uid = firebase_auth.verify_id_token(token)['uid']
                except Exception:
                    return fail(401, 'sign in again')
                if uid not in chat.allowed_uids() and uid not in coach_uids():
                    return fail(403, 'uploads are not open for this account yet')
                try:
                    body = await request.json()
                    assert isinstance(body, dict)
                except Exception:
                    return fail(400, 'send a JSON object')
                try:
                    return JSONResponse(handler(db, uid, body), headers=headers)
                except PermissionError as err:
                    return fail(403, str(err))
                except (ValueError, KeyError) as err:
                    return fail(400, str(err))
            return endpoint
        return wrap

    @route('/media/upload')
    def upload(db, uid, body):
        key, ctype = upload_key(uid, body, datetime.now(timezone.utc))
        url = s3().generate_presigned_url('put_object', Params={'Bucket': bucket(), 'Key': key, 'ContentType': ctype},
                                          ExpiresIn=PUT_EXPIRES)
        return {'key': key, 'url': url, 'headers': {'Content-Type': ctype}}

    @route('/media/done')
    def done(db, uid, body):
        key = body.get('key')
        if not isinstance(key, str) or not (key.startswith(f'users/{uid}/') or
                                             (key.startswith('demos/') and uid in coach_uids())):
            raise PermissionError('not your upload')
        try:
            head = s3().head_object(Bucket=bucket(), Key=key)
        except Exception:
            raise ValueError('upload not found; try again')
        try:
            kind, media, size = check_upload(key, head)
        except ValueError:
            s3().delete_object(Bucket=bucket(), Key=key)
            raise
        if kind == 'demo':
            name = body.get('exercise') or ''
            if slug(name) != key.split('/')[1]:
                raise ValueError('exercise does not match the upload')
            db.collection('exercise_media').document(slug(name)).set(
                {'name': name, 'key': key, 'type': media, 'by': uid, 'at': datetime.now(timezone.utc).isoformat()})
        return {'key': key, 'type': media, 'size': size}

    @route('/media/urls')
    def urls(db, uid, body):
        keys, names = body.get('keys') or [], body.get('demos') or []
        if not (isinstance(keys, list) and isinstance(names, list) and len(keys) <= 100 and len(names) <= 100):
            raise ValueError('keys and demos are lists of up to 100')
        sign = lambda k: s3().generate_presigned_url('get_object', Params={'Bucket': bucket(), 'Key': k},
                                                     ExpiresIn=GET_EXPIRES)
        found = demos(db, [n for n in names if isinstance(n, str)])
        return {'urls': {k: sign(k) for k in keys if isinstance(k, str) and may_see(uid, k)},
                'demos': {n: {**d, 'url': sign(d['key'])} for n, d in found.items()},
                'coach': uid in coach_uids()}  # the tracker shows "Upload demo" only to the coach
