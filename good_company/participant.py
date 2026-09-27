"""Opt-in isolated participant evidence endpoint. Never runs an agent or shell."""
import argparse
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
from .core import Coordinator


class AccessDenied(ValueError):
    pass


class ParticipantService:
    def __init__(self, load_config):
        self.load_config = load_config

    def evidence(self, bearer, request):
        # Server-owned configuration is reloaded for revocation. Client JSON never
        # chooses identity, role, organization, database, audience, or a tool.
        config = self.load_config()
        fingerprint = hashlib.sha256(bearer.encode()).hexdigest()
        identity = next((entry for entry in config['credentials']
                         if hmac.compare_digest(entry['sha256'], fingerprint)), None)
        if not identity or identity.get('role') != 'participant' or identity.get('disabled', False):
            raise AccessDenied('Access denied.')
        if not isinstance(request, dict) or set(request) - {'question', 'on'}:
            raise ValueError('Only question and optional on date are supported.')
        question = request.get('question')
        if not isinstance(question, str) or not 1 <= len(question.strip()) <= 2000:
            raise ValueError('Question must contain 1 to 2000 characters.')
        path = Path(config['organizations'][identity['organization']]).resolve(strict=True)
        coordinator = Coordinator.__new__(Coordinator)
        coordinator.db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
        coordinator.db.row_factory = sqlite3.Row
        try:
            # The issuer binds this optional address to the credential. Request
            # JSON cannot select another participant's communication preferences.
            if identity.get('address'):
                return coordinator.accessible_evidence(question=question, address=identity['address'], on=request.get('on'))
            return coordinator.retrieve(question, audience='volunteer', on=request.get('on'))
        finally:
            coordinator.db.close()


def handler(service):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            try:
                if self.path != '/v1/evidence':
                    self.respond(404, {'error': 'Unknown route.'}); return
                authorization = self.headers.get('Authorization', '')
                if not authorization.startswith('Bearer '):
                    raise AccessDenied('Access denied.')
                length = int(self.headers.get('Content-Length', '-1'))
                if not 0 <= length <= 8192:
                    raise ValueError('Request must have a bounded content length.')
                request = json.loads(self.rfile.read(length))
                self.respond(200, service.evidence(authorization[7:], request))
            except AccessDenied:
                self.respond(403, {'error': 'Access denied.'})
            except (ValueError, TypeError):
                self.respond(400, {'error': 'Invalid request.'})
            except (KeyError, OSError, sqlite3.Error):
                self.respond(503, {'error': 'Evidence service unavailable.'})

        def respond(self, status, value):
            data = json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
    return Handler


def main():
    parser = argparse.ArgumentParser(description='Private loopback participant evidence service')
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--port', type=int, default=3018)
    args = parser.parse_args()
    service = ParticipantService(lambda: json.loads(args.config.read_text()))
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler(service))
    server.serve_forever()


if __name__ == '__main__':
    main()
