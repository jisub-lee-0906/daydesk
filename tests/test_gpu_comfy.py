import unittest
from unittest.mock import patch

from gpu import GpuMonitor
from comfy_status import project_comfy, read_comfy


class GpuComfyTests(unittest.TestCase):
    def test_missing_driver_does_not_break_pc_dashboard(self):
        with patch('gpu.C.CDLL', side_effect=OSError('no driver')):
            monitor = GpuMonitor()
        self.assertEqual(monitor.sample(), [])
        monitor.close()

    def test_queue_projection_only_exposes_counts(self):
        result = project_comfy({'queue_running': [[1,'private-prompt']], 'queue_pending': [1,2]}, {'devices':[{'name':'GPU','vram_free':12}], 'system':{'comfyui_version':'0.42.1','argv':['private-path']}})
        self.assertEqual((result['running'], result['pending']), (1,2))
        self.assertEqual(result['version'], '0.42.1')
        self.assertNotIn('private', str(result))

    def test_broken_or_missing_queue_is_unknown_not_idle(self):
        for queue in [{}, {'queue_running':{},'queue_pending':[]}]:
            data = project_comfy(queue,{})
            self.assertIsNone(data['running'])
            self.assertIsNone(data['pending'])
        self.assertEqual(project_comfy({'queue_running':[],'queue_pending':[]},{})['running'],0)

    def test_offline_comfy_is_explicit(self):
        with patch('comfy_status.local_json', side_effect=OSError('offline')):
            result = read_comfy(8188)
        self.assertFalse(result['online'])
        self.assertIsNone(result['running'])
        self.assertIsNone(result['pending'])


if __name__ == '__main__':
    unittest.main()
