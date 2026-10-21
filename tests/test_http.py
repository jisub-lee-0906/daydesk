import http.client
import json
import threading
import unittest

from server import make_server


class FakeSampler:
    def snapshot(self):
        return {'sampled_at': 10, 'pc': {'cpu_percent': None}, 'history': []}


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(FakeSampler(), 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def get(self, path, headers=None):
        c = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        c.request('GET', path, headers=headers or {})
        response = c.getresponse()
        body = response.read()
        status, headers = response.status, dict(response.getheaders())
        c.close()
        return status, headers, body

    def test_readonly_status_and_security_headers(self):
        code, headers, body = self.get('/api/status')
        self.assertEqual(code, 200)
        self.assertIsNone(json.loads(body)['pc']['cpu_percent'])
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertIn("default-src 'self'", headers['Content-Security-Policy'])
        self.assertNotIn('Access-Control-Allow-Origin', headers)

    def test_foreign_host_and_cross_site_origin_rejected(self):
        for headers in [{'Host': 'evil.test'}, {'Origin': 'https://evil.test'}, {'Sec-Fetch-Site': 'cross-site'}]:
            self.assertEqual(self.get('/api/status', headers)[0], 403)

    def test_private_source_and_traversal_are_not_served(self):
        for path in ['/server.py', '/../EVIDENCE.md', '/.opencodex/auth.json', '/api/unknown']:
            self.assertEqual(self.get(path)[0], 404)

    def test_public_page_and_info_exist(self):
        self.assertEqual(self.get('/')[0], 200)
        code, _, body = self.get('/api/info')
        self.assertEqual(code, 200)
        self.assertIn('subscriptions', json.loads(body))


if __name__ == '__main__':
    unittest.main()
