import json
from pathlib import Path
import tempfile
import unittest

from adapters import QuotaReader, normalize_quota


class QuotaTests(unittest.TestCase):
    def test_zero_is_available_and_missing_is_unknown(self):
        q = normalize_quota({'weeklyPercent': 0, 'updatedAt': 1_792_000_000_000}, now=1_792_000_010)
        self.assertEqual(q['windows'][0]['used_percent'], 0)
        self.assertFalse(q['stale'])
        self.assertEqual(normalize_quota({}, now=1)['windows'], [])

    def test_bad_percent_cannot_be_displayed_as_real_usage(self):
        for value in [True, -1, 101, '6', float('nan')]:
            self.assertEqual(normalize_quota({'weeklyPercent': value}, now=1)['windows'], [])

    def test_stale_and_unknown_timestamps_are_explicit(self):
        self.assertTrue(normalize_quota({'weeklyPercent': 6}, now=2000)['stale'])
        self.assertTrue(normalize_quota({'updatedAt': 1000}, now=2000)['stale'])
        self.assertFalse(normalize_quota({'updatedAt': 1100}, now=2000)['stale'])
        self.assertTrue(normalize_quota({'updatedAt': 3000}, now=2000)['stale'])

    def test_google_pools_are_separate(self):
        q = normalize_quota({'customWindows': [{'label': 'Gem (Weekly)', 'percent': 15}, {'label': 'Cla (Weekly)', 'percent': 40}]}, now=1)
        self.assertEqual([x['used_percent'] for x in q['windows']], [15, 40])

    def test_secrets_and_account_ids_never_reach_public_projection(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p/'provider-account-quota-cache.json').write_text(json.dumps({'rows': {'anthropic\0private-id': {'weeklyPercent': 6, 'token': 'secret'}}}))
            result = QuotaReader(p).read(now=2000)
            self.assertEqual(result['claude']['windows'][0]['used_percent'], 6)
            self.assertNotIn('private-id', json.dumps(result))
            self.assertNotIn('secret', json.dumps(result))

    def test_corrupt_cache_preserves_last_value_and_marks_read_error(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            cache = p/'codex-quota-cache.json'
            cache.write_text(json.dumps({'quotas': {'__main__': {'weeklyPercent': 6, 'updatedAt': 1000}}}))
            reader = QuotaReader(p)
            self.assertEqual(reader.read(now=1010)['codex']['windows'][0]['used_percent'], 6)
            cache.write_text('{broken')
            result = reader.read(now=1011)['codex']
            self.assertEqual(result['windows'][0]['used_percent'], 6)
            self.assertTrue(result['stale'])
            self.assertTrue(result['read_error'])

    def test_ambiguous_accounts_are_not_combined(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p/'provider-account-quota-cache.json').write_text(json.dumps({'rows': {'xai\0a': {'weeklyPercent': 6}, 'xai\0b': {'weeklyPercent': 7}}}))
            self.assertEqual(QuotaReader(p).read(now=1)['grok']['windows'], [])


if __name__ == '__main__':
    unittest.main()
