#!/usr/bin/env python3
"""Exercise the pinned development proxy with a private, fictional echo backend."""
import json
import http.client
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from uuid import uuid4

IMAGE = 'caddy:2@sha256:14a9c00d4e833ebc2b65d36515b37bde3b73f0b323a2663aaafc88953d8c4e3f'


def run():
    name = 'good-company-proxy-check-' + uuid4().hex[:10]
    with tempfile.TemporaryDirectory() as directory:
        config = Path(directory) / 'Caddyfile'
        config.write_text(Path('dev/Caddyfile').read_text() + '''
:3000 {
    respond `{"user":"{http.request.header.X-Plow-User}","forwarded":"{http.request.header.Forwarded}","real":"{http.request.header.X-Real-IP}","forwarded_host":"{http.request.header.X-Forwarded-Host}"}`
}
''')
        subprocess.run(['docker', 'run', '-d', '--name', name, '-p', '127.0.0.1::3001',
                        '-v', str(config) + ':/etc/caddy/Caddyfile:ro', IMAGE], check=True, capture_output=True)
        try:
            binding = subprocess.check_output(['docker', 'port', name, '3001/tcp'], text=True).strip()
            endpoint = 'http://' + binding + '/'
            def request(host, origin=None, spoof=False):
                headers = {'Host': host}
                if origin:
                    headers['Origin'] = origin
                if spoof:
                    headers.update({'X-Plow-User': 'attacker', 'Forwarded': 'for=attacker',
                                    'X-Forwarded-Host': 'attacker', 'X-Real-IP': 'attacker'})
                try:
                    with urllib.request.urlopen(urllib.request.Request(endpoint, headers=headers), timeout=3) as response:
                        return response.status, response.read().decode()
                except urllib.error.HTTPError as error:
                    return error.code, ''
            for attempt in range(40):
                try:
                    status, body = request('localhost:3007', spoof=True)
                    break
                except (urllib.error.URLError, http.client.HTTPException, OSError):
                    time.sleep(0.1)
            else:
                raise AssertionError('Proxy did not start.')
            assert status == 200, (status, body)
            data = json.loads(body)
            assert data['user'] == 'dev-owner', data
            assert 'attacker' not in body, body
            assert request('127.0.0.1:3007', 'http://127.0.0.1:3007')[0] == 200
            assert request('localhost:3007', 'https://untrusted.invalid')[0] == 403
            assert request('untrusted.invalid:3007')[0] == 403
            assert request('localhost.untrusted.invalid')[0] == 403
            print('Pinned Caddy: local hosts accepted; foreign hosts/origins and spoofed identity headers rejected.')
        finally:
            subprocess.run(['docker', 'rm', '-f', name], check=True, capture_output=True)


if __name__ == '__main__':
    run()
