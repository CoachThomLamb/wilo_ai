"""Tests for wilo/media.py (#152): who may upload and see exercise videos. Fake db, fake S3 (no network, no keys).

    .venv/bin/python -m unittest discover tests
"""

import os
import unittest

import firebase_admin.auth
from starlette.testclient import TestClient
from test_wilo_data import FakeDB

from wilo import chat, media
from wilo import mcp_server as srv

CLIENT, OTHER, COACH = 'lijon', 'someone-else', 'thom'
TOKENS = {'client': CLIENT, 'other': OTHER, 'coach': COACH}
TRACKER = 'https://wilo2-1ee44.web.app'


class FakeS3:
    def __init__(self):
        self.objects, self.deleted = {}, []

    def generate_presigned_url(self, op, Params, ExpiresIn):
        return f'https://b2.example/{op}/{Params["Key"]}?expires={ExpiresIn}&type={Params.get("ContentType", "")}'

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise KeyError(Key)
        return self.objects[Key]

    def delete_object(self, Bucket, Key):
        self.deleted.append(Key)
        self.objects.pop(Key, None)


class MediaTest(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB()
        self.s3 = FakeS3()
        self.saved = srv.db, firebase_admin.auth.verify_id_token, chat.allowed_uids, media._s3, dict(os.environ)
        srv.db = lambda: self.db
        firebase_admin.auth.verify_id_token = lambda tok: {'uid': TOKENS[tok]}
        chat.allowed_uids = lambda: {CLIENT}
        media._s3 = self.s3
        os.environ.update({'B2_BUCKET': 'test-bucket', 'WILO_COACH_UIDS': COACH})
        self.http = TestClient(srv.make_server().streamable_http_app()).__enter__()

    def tearDown(self):
        self.http.__exit__(None, None, None)
        srv.db, firebase_admin.auth.verify_id_token, chat.allowed_uids, media._s3, env = self.saved
        os.environ.clear()
        os.environ.update(env)

    def post(self, path, body, token='client'):
        return self.http.post(path, json=body, headers={'Authorization': f'Bearer {token}', 'Origin': TRACKER})

    def uploaded(self, key, ctype='video/mp4', size=5 * media.MB):
        self.s3.objects[key] = {'ContentType': ctype, 'ContentLength': size}

    def test_client_form_video_goes_under_their_own_folder(self):
        r = self.post('/media/upload', {'kind': 'form', 'docId': '07-nov-fortius', 'exId': 'x1', 'contentType': 'video/mp4'})
        self.assertEqual(r.status_code, 200)
        key = r.json()['key']
        self.assertTrue(key.startswith(f'users/{CLIENT}/07-nov-fortius/x1/') and key.endswith('.mp4'), key)
        self.assertEqual(r.json()['headers'], {'Content-Type': 'video/mp4'})
        self.assertIn('put_object', r.json()['url'])
        self.assertEqual(r.headers['access-control-allow-origin'], TRACKER)
        self.uploaded(key)
        self.assertEqual(self.post('/media/done', {'key': key}).json(), {'key': key, 'type': 'video', 'size': 5 * media.MB})

    def test_only_the_coach_uploads_demos(self):
        body = {'kind': 'demo', 'exercise': 'Goblet Squat', 'contentType': 'video/quicktime'}
        self.assertEqual(self.post('/media/upload', body).status_code, 403)
        r = self.post('/media/upload', body, token='coach')
        key = r.json()['key']
        self.assertTrue(key.startswith('demos/goblet-squat/') and key.endswith('.mov'), key)
        self.uploaded(key, 'video/quicktime')
        self.assertEqual(self.post('/media/done', {'key': key, 'exercise': 'Goblet Squat'}, token='coach').status_code, 200)
        # Every client sees it, under any spelling of the name.
        demos = self.post('/media/urls', {'demos': ['goblet  squat', 'Leg Extension']}).json()['demos']
        self.assertEqual(list(demos), ['goblet  squat'])
        self.assertEqual(demos['goblet  squat']['key'], key)
        self.assertIn('get_object', demos['goblet  squat']['url'])

    def test_clients_see_only_their_own_files_and_the_coach_sees_all(self):
        mine, theirs = f'users/{CLIENT}/d/x1/a.mp4', f'users/{OTHER}/d/x1/b.mp4'
        self.assertEqual(list(self.post('/media/urls', {'keys': [mine, theirs, 'demos/x/c.mp4']}).json()['urls']),
                         [mine, 'demos/x/c.mp4'])
        self.assertEqual(list(self.post('/media/urls', {'keys': [mine, theirs]}, token='coach').json()['urls']), [mine, theirs])

    def test_too_big_uploads_are_deleted(self):
        key = f'users/{CLIENT}/d/x1/big.mp4'
        self.uploaded(key, size=200 * media.MB)
        r = self.post('/media/done', {'key': key})
        self.assertEqual(r.status_code, 400)
        self.assertIn('too big', r.json()['error'])
        self.assertEqual(self.s3.deleted, [key])

    def test_cannot_confirm_someone_elses_upload_or_fake_a_demo(self):
        self.assertEqual(self.post('/media/done', {'key': f'users/{OTHER}/d/x1/b.mp4'}).status_code, 403)
        self.assertEqual(self.post('/media/done', {'key': 'demos/goblet-squat/a.mp4', 'exercise': 'Goblet Squat'}).status_code, 403)

    def test_bad_requests(self):
        cases = [{'kind': 'form', 'contentType': 'video/mp4'},                                   # no docId/exId
                 {'kind': 'form', 'docId': '../x', 'exId': 'x1', 'contentType': 'video/mp4'},    # path tricks
                 {'kind': 'form', 'docId': 'd', 'exId': 'x1', 'contentType': 'application/pdf'},
                 {'kind': 'nope', 'contentType': 'video/mp4'}]
        for body in cases:
            self.assertEqual(self.post('/media/upload', body).status_code, 400, body)

    def test_strangers_and_bad_tokens_are_refused(self):
        body = {'kind': 'form', 'docId': 'd', 'exId': 'x1', 'contentType': 'video/mp4'}
        self.assertEqual(self.post('/media/upload', body, token='other').status_code, 403)
        r = self.http.post('/media/upload', json=body, headers={'Authorization': 'Bearer nope'})
        self.assertEqual(r.status_code, 401)


if __name__ == '__main__':
    unittest.main()
