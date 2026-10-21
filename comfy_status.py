"""Read queue counts only; never expose prompts, workflow nodes, paths, or queue IDs."""
import http.client
import json
import time


def local_json(port, path):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=0.7)
    try:
        connection.request('GET', path)
        response = connection.getresponse()
        body = response.read(1024 * 1024 + 1)
        if response.status != 200 or len(body) > 1024 * 1024:
            raise ValueError('unavailable')
        value = json.loads(body)
        if not isinstance(value, dict):
            raise ValueError('invalid root')
        return value
    finally:
        connection.close()


def project_comfy(queue, stats):
    running, pending = queue.get('queue_running'), queue.get('queue_pending')
    valid = isinstance(running, list) and isinstance(pending, list)
    system = stats.get('system', {})
    version = system.get('comfyui_version') if isinstance(system, dict) else None
    return {'running': len(running) if valid else None, 'pending': len(pending) if valid else None, 'version': version[:40] if isinstance(version, str) else None}


def read_comfy(port, include_stats=False):
    data = {'online': False, 'running': None, 'pending': None, 'version': None, 'port': port, 'checked_at': time.time()}
    try:
        queue = local_json(port, '/queue')
        stats = {}
        if include_stats:
            try:
                stats = local_json(port, '/system_stats')
            except (OSError, ValueError, http.client.HTTPException):
                pass
        data.update(project_comfy(queue, stats))
        data['online'] = True
    except (OSError, ValueError, http.client.HTTPException):
        pass
    return data
