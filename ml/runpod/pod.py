"""Start, check and stop the model-serving pod described in serve.yaml.

    export RUNPOD_API_KEY=...                       # runpod.io → Settings → API Keys
    python ml/runpod/pod.py up                      # create the pod; prints the endpoint
    python ml/runpod/pod.py status                  # waits until the model answers /v1/models
    python ml/runpod/pod.py down                    # terminate it (stop paying)

The endpoint is public (RunPod proxy), so vLLM gets an API key made for this pod. The pod id, URL and key are
saved in ml/.pod.json (gitignored); ml/score.py reads them from there.
"""
import json
import secrets
import sys
import time
import urllib.request
from pathlib import Path

import runpod
import yaml

HERE = Path(__file__).resolve().parent
STATE = HERE.parent / '.pod.json'


def config():
    return yaml.safe_load((HERE / 'serve.yaml').read_text())


def up():
    if STATE.exists():
        sys.exit(f'A pod is already recorded in {STATE}. Run "down" first.')
    c = config()
    key = secrets.token_urlsafe(24)
    args = ['--model', c['model'], '--port', str(c['port']), '--max-model-len', str(c['max_model_len']),
            '--api-key', key, *c['vllm_args']]
    pod = runpod.create_pod(
        name=c['name'], image_name=c['image'], gpu_type_id=c['gpu'], cloud_type=c['cloud'],
        container_disk_in_gb=c['container_disk_gb'], volume_in_gb=c['volume_gb'], volume_mount_path=c['volume_path'],
        ports=f"{c['port']}/http", docker_args=' '.join(args), env=c.get('env') or {})
    url = f"https://{pod['id']}-{c['port']}.proxy.runpod.net/v1"
    STATE.write_text(json.dumps({'id': pod['id'], 'url': url, 'key': key, 'model': c['model']}, indent=2))
    STATE.chmod(0o600)
    print(f"pod {pod['id']} starting: {url}\nFirst start downloads the model (a few minutes). Then: pod.py status")


def status(wait=True):
    s = json.loads(STATE.read_text())
    req = urllib.request.Request(s['url'] + '/models', headers={'Authorization': f"Bearer {s['key']}"})
    for _ in range(120 if wait else 1):
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                print('ready:', [m['id'] for m in json.load(r)['data']], s['url'])
                return
        except Exception as e:
            print(f'not ready ({str(e)[:60]})', flush=True)
            if wait:
                time.sleep(15)
    sys.exit('Still not ready. Check the pod logs on runpod.io.')


def down():
    s = json.loads(STATE.read_text())
    runpod.terminate_pod(s['id'])
    STATE.unlink()
    print(f"pod {s['id']} terminated")


if __name__ == '__main__':
    import os
    runpod.api_key = os.environ.get('RUNPOD_API_KEY') or sys.exit('Set RUNPOD_API_KEY first.')
    {'up': up, 'status': status, 'down': down}[sys.argv[1] if len(sys.argv) > 1 else 'status']()
