"""내 PC 데스크: one local sampler, fixed read-only HTTP routes."""
import argparse
from collections import deque
from copy import deepcopy
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time

from adapters import QuotaReader
from monitor import WindowsMonitor
from gpu import GpuMonitor
from comfy_status import read_comfy
from public_data import PublicData

ROOT = Path(__file__).resolve().parent
APP_ID = 'my-pc-desk-' + hashlib.sha256(str(ROOT).encode()).hexdigest()[:12]
STATIC = {'/': ('index.html', 'text/html; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8'), '/logic.js': ('logic.js', 'text/javascript; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/favicon.svg': ('favicon.svg', 'image/svg+xml'), '/location.js': ('location.js', 'text/javascript; charset=utf-8')}


def service_health(port):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=0.7)
    try:
        connection.request('GET', '/healthz')
        response = connection.getresponse()
        body = response.read(4096)
        # No redirects, authentication, or provider calls.
        return {'online': response.status == 200, 'checked_at': time.time(), 'port': port}
    except (OSError, http.client.HTTPException):
        return {'online': False, 'checked_at': time.time(), 'port': port}
    finally:
        connection.close()


class Sampler:
    def __init__(self, port=10100, comfy_port=8188):
        self.monitor = WindowsMonitor()
        self.gpu = GpuMonitor()
        self.reader = QuotaReader()
        self.port = port
        self.comfy_port = comfy_port
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.wake = threading.Event()
        self.last_client = time.monotonic()
        self.history = deque(maxlen=60)
        self.data = {'sampled_at': None, 'pc': {}, 'apps': None, 'quotas': {}, 'service': {}, 'history': [], 'sample_error': False}
        self.thread = threading.Thread(target=self.run, name='desk-sampler', daemon=True)

    def snapshot(self):
        with self.lock:
            idle = time.monotonic() - self.last_client >= 20
            self.last_client = time.monotonic()
            if idle:
                self.wake.set()
            return deepcopy(self.data)

    def run(self):
        last_apps = last_external = last_comfy = last_stats = -1000
        while not self.stop.is_set():
            now = time.monotonic()
            with self.lock:
                data = deepcopy(self.data)
            try:
                data['pc'] = self.monitor.sample()
                data['gpus'] = self.gpu.sample()
                data['sampled_at'] = time.time()
                data['sample_error'] = False
                if now - last_apps >= 15:
                    data['apps'] = self.monitor.apps()
                    data['apps_sampled_at'] = time.time()
                    last_apps = now
                if now - last_external >= 30:
                    data['quotas'] = self.reader.read()
                    data['service'] = service_health(self.port)
                    last_external = now
                if now - last_comfy >= 6:
                    include_stats = now - last_stats >= 60
                    previous_version = data.get('comfy', {}).get('version')
                    data['comfy'] = read_comfy(self.comfy_port, include_stats)
                    if not include_stats and data['comfy']['online']:
                        data['comfy']['version'] = previous_version
                    if include_stats:
                        last_stats = now
                    last_comfy = now
                self.history.append({'cpu': data['pc']['cpu_percent'], 'ram': (data['pc']['memory'] or {}).get('percent')})
                data['history'] = list(self.history)
            except (OSError, ValueError, TypeError):
                data['sample_error'] = True
            with self.lock:
                self.data = data
                active = now - self.last_client < 20
            self.wake.wait(3 if active else 30)
            self.wake.clear()


def make_server(sampler, port=8765, public=None):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.0'

        def log_message(self, *args):
            pass

        def reply(self, code, body, content_type='application/json; charset=utf-8'):
            if isinstance(body, dict):
                body = json.dumps(body, ensure_ascii=False, allow_nan=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            hosts = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            origins = {'http://' + host for host in hosts}
            if self.headers.get('Host') not in hosts or self.headers.get('Origin') not in (None, *origins) or self.headers.get('Sec-Fetch-Site') == 'cross-site':
                return self.reply(403, {'error': 'local_only'})
            path = self.path.split('?', 1)[0]
            if path == '/api/health':
                return self.reply(200, {'app': APP_ID, 'pid': __import__('os').getpid()})
            if path == '/api/status':
                return self.reply(200, sampler.snapshot())
            if path == '/api/public':
                return self.reply(200, public.snapshot() if public else {'weather': {}, 'news': [], 'sources': {}})
            if path == '/api/info':
                return self.reply(200, json.loads((ROOT / 'dashboard.json').read_text(encoding='utf-8')))
            if path in STATIC:
                filename, content_type = STATIC[path]
                return self.reply(200, (ROOT / 'web' / filename).read_bytes(), content_type)
            return self.reply(404, {'error': 'not_found'})

        def do_POST(self):
            origins = {f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'}
            hosts = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            if self.headers.get('Host') not in hosts or self.headers.get('Origin') not in origins or self.headers.get('Sec-Fetch-Site') == 'cross-site':
                return self.reply(403, {'error': 'local_only'})
            if self.path != '/api/location' or public is None:
                return self.reply(404, {'error': 'not_found'})
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.reply(415, {'error': 'json_required'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 512:
                    return self.reply(413, {'error': 'body_size'})
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict) or data.get('mode') not in ('current', 'default'):
                    raise ValueError()
                if data['mode'] == 'current':
                    if data.get('latitude') is None or data.get('longitude') is None:
                        raise ValueError()
                    accepted = public.set_location(data.get('latitude'), data.get('longitude'), owner=data.get('owner'))
                else:
                    accepted = public.set_location(owner=data.get('owner'))
                return self.reply(200 if accepted else 409, {'accepted': accepted})
            except (ValueError, TypeError, UnicodeError, OverflowError):
                return self.reply(400, {'error': 'invalid_location'})

    httpd = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    httpd.daemon_threads = True
    return httpd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    config = json.loads((ROOT / 'dashboard.json').read_text(encoding='utf-8'))
    sampler = Sampler(config.get('opencodex_port', 10100), config.get('comfyui_port', 8188))
    public = PublicData(ROOT / ".run" / "public-cache.json")
    server = make_server(sampler, args.port, public)
    sampler.thread.start()
    public.thread.start()
    print(f'내 PC 데스크  http://127.0.0.1:{server.server_port}  (Ctrl+C로 종료)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        public.close()
        sampler.stop.set()
        sampler.wake.set()
        server.server_close()
        sampler.thread.join(timeout=3)
        if not sampler.thread.is_alive():
            sampler.gpu.close()


if __name__ == '__main__':
    main()
