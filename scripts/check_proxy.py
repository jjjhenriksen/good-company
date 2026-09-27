#!/usr/bin/env python3
"""Exercise the pinned development proxy with a private, fictional echo backend."""
import json
import http.client
import os
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from uuid import uuid4

IMAGE = 'caddy:2@sha256:14a9c00d4e833ebc2b65d36515b37bde3b73f0b323a2663aaafc88953d8c4e3f'


def run(port=None):
    name = 'good-company-proxy-check-' + uuid4().hex[:10]
    configured_port = port or '3007'
    with tempfile.TemporaryDirectory() as directory:
        config = Path(directory) / 'Caddyfile'
        config.write_text(Path('dev/Caddyfile').read_text() + '''
:3000 {
    respond `{"user":"{http.request.header.X-Plow-User}","forwarded":"{http.request.header.Forwarded}","real":"{http.request.header.X-Real-IP}","forwarded_host":"{http.request.header.X-Forwarded-Host}"}`
}
''')
        environment = ['-e', 'GOOD_COMPANY_DASHBOARD_PORT=' + port] if port else []
        subprocess.run(['docker', 'run', '-d', '--name', name, '-p', '127.0.0.1::3001',
                        '-v', str(config) + ':/etc/caddy/Caddyfile:ro', *environment, IMAGE], check=True, capture_output=True)
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
                    status, body = request('localhost:' + configured_port, spoof=True)
                    break
                except (urllib.error.URLError, http.client.HTTPException, OSError):
                    time.sleep(0.1)
            else:
                raise AssertionError('Proxy did not start.')
            assert status == 200, (status, body)
            data = json.loads(body)
            assert data['user'] == 'dev-owner', data
            assert 'attacker' not in body, body
            assert request('127.0.0.1:' + configured_port, 'http://127.0.0.1:' + configured_port)[0] == 200
            assert request('localhost:' + configured_port, 'http://localhost:' + configured_port)[0] == 200
            assert request('localhost:' + configured_port, 'https://untrusted.invalid')[0] == 403
            other_port = '3007' if port else '3017'
            assert request('localhost:' + configured_port, 'http://localhost:' + other_port)[0] == 403
            assert request('untrusted.invalid:' + configured_port)[0] == 403
            assert request('localhost.untrusted.invalid')[0] == 403
            print(f'Pinned Caddy on configured port {configured_port}: local hosts accepted; foreign/other-port origins and spoofed identity headers rejected.')
        finally:
            subprocess.run(['docker', 'rm', '-f', name], check=True, capture_output=True)


def run_restart_check(compose_file='compose.yml'):
    """Exercise the actual dependency wiring with a disposable local backend."""
    project = 'good-company-restart-check-' + uuid4().hex[:10]
    env = dict(os.environ, PLOW_CREDENTIAL_FILE='/dev/null', GOOD_COMPANY_DASHBOARD_PORT='3007')
    source = json.loads(subprocess.check_output(
        ['docker', 'compose', '-f', compose_file, 'config', '--format', 'json'], env=env, text=True))
    proxy = source['services']['dev-dashboard']
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / 'backend').write_text(':3000 {\n respond "restart-fixture"\n}\n')
        (root / 'proxy').write_text(Path('dev/Caddyfile').read_text())
        # A delayed stop makes the old parallel-restart race deterministic.
        # Neither container has credentials, real state, or external services.
        config = {'services': {
            'agent': {'image': IMAGE, 'stop_grace_period': '5s',
                      'entrypoint': ['/bin/sh', '-c',
                          "caddy run --config /etc/caddy/Caddyfile & trap 'sleep 2; exit 0' TERM; wait"],
                      'volumes': [str(root / 'backend') + ':/etc/caddy/Caddyfile:ro'],
                      'ports': ['127.0.0.1::3001']},
            'dev-dashboard': {'image': IMAGE, 'network_mode': proxy['network_mode'],
                              'depends_on': proxy['depends_on'],
                              'environment': proxy['environment'],
                              'volumes': [str(root / 'proxy') + ':/etc/caddy/Caddyfile:ro']}}}
        path = root / 'compose.json'
        path.write_text(json.dumps(config))
        command = ['docker', 'compose', '-p', project, '-f', str(path)]

        def check_ready():
            binding = subprocess.check_output(command + ['port', 'agent', '3001'], text=True).strip()
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                try:
                    request = urllib.request.Request('http://' + binding, headers={'Host': 'localhost:3007'})
                    with urllib.request.urlopen(request, timeout=1) as response:
                        if response.status == 200 and response.read().decode() == 'restart-fixture':
                            break
                except (urllib.error.URLError, http.client.HTTPException, OSError):
                    pass
                time.sleep(0.1)
            else:
                raise AssertionError('Dashboard did not reattach after Compose restart.')
            namespaces = [subprocess.check_output(command + ['exec', '-T', service, 'readlink', '/proc/1/ns/net'], text=True).strip()
                          for service in ('agent', 'dev-dashboard')]
            assert namespaces[0] == namespaces[1], namespaces

        try:
            subprocess.run(command + ['up', '-d'], check=True, capture_output=True)
            check_ready()
            for services in ([], ['agent']):
                subprocess.run(command + ['restart', *services], check=True, capture_output=True)
                check_ready()
            print('Compose whole-project and targeted agent restarts preserve the dashboard network namespace.')
        finally:
            subprocess.run(command + ['down', '--volumes'], check=True, capture_output=True)


if __name__ == '__main__':
    run()
    run('3017')
    run_restart_check()
