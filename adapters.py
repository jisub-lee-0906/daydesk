"""Read-only, allowlisted projection of OpenCodex quota caches. No auth files."""
from copy import deepcopy
import json
import math
from pathlib import Path
import time


def timestamp(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        return None
    return value / 1000 if value > 100_000_000_000 else value


def percent(value):
    return float(value) if not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and 0 <= value <= 100 else None


def normalize_quota(raw, now):
    raw = raw if isinstance(raw, dict) else {}
    updated = timestamp(raw.get('updatedAt'))
    windows = []
    for field, label, reset in [('fiveHourPercent', '5시간', 'fiveHourResetAt'), ('weeklyPercent', '주간', 'weeklyResetAt')]:
        value = percent(raw.get(field))
        if value is not None:
            windows.append({'label': label, 'used_percent': value, 'reset_at': timestamp(raw.get(reset))})
    for item in raw.get('customWindows', []) if isinstance(raw.get('customWindows'), list) else []:
        if not isinstance(item, dict):
            continue
        labels = {'Gem (Weekly)': 'Gemini 주간', 'Cla (Weekly)': 'Claude 주간'}
        value = percent(item.get('percent'))
        if item.get('label') in labels and value is not None and item.get('percentType', 'consumed') in ('used', 'consumed') and item.get('unit', 'percent') == 'percent':
            windows.append({'label': labels[item['label']], 'used_percent': value, 'reset_at': timestamp(item.get('resetAt'))})
    return {'windows': windows, 'updated_at': updated, 'stale': updated is None or now - updated > 900 or updated > now + 60, 'read_error': False, 'source': 'OpenCodex 로컬 캐시'}


class QuotaReader:
    MAX_BYTES = 2 * 1024 * 1024

    def __init__(self, home=None):
        self.home = Path(home) if home else Path.home() / '.opencodex'
        self.previous = {}

    def _read(self, filename):
        path = self.home / filename
        try:
            stat = path.stat()
            if stat.st_size > self.MAX_BYTES:
                raise ValueError('oversized')
            signature = (stat.st_mtime_ns, stat.st_size)
            old = self.previous.get(filename)
            if old and old[0] == signature:
                return old[1], False
            with path.open('rb') as stream:
                data = json.loads(stream.read(self.MAX_BYTES + 1).decode('utf-8-sig'))
            if not isinstance(data, dict):
                raise ValueError('bad root')
            self.previous[filename] = (signature, data)
            return data, False
        except (OSError, UnicodeError, ValueError):
            old = self.previous.get(filename)
            return old[1] if old else {}, True

    def read(self, now=None):
        now = time.time() if now is None else now
        codex, codex_error = self._read('codex-quota-cache.json')
        providers, provider_error = self._read('provider-account-quota-cache.json')
        quotas = codex.get('quotas', {})
        raw = quotas.get('__main__', {}) if isinstance(quotas, dict) else {}
        result = {'codex': normalize_quota(raw, now)}
        rows = providers.get('rows', {})
        rows = rows if isinstance(rows, dict) else {}
        for key, provider in [('claude', 'anthropic'), ('grok', 'xai'), ('gemini', 'google-antigravity')]:
            matches = [v for k, v in rows.items() if isinstance(k, str) and k.startswith(provider + '\0') and isinstance(v, dict)]
            result[key] = normalize_quota(matches[0] if len(matches) == 1 else {}, now)
        for key, value in result.items():
            value['read_error'] = codex_error if key == 'codex' else provider_error
            value['stale'] = value['stale'] or value['read_error']
        return deepcopy(result)
