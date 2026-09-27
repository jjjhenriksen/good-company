import importlib.util
import io
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
spec=importlib.util.spec_from_file_location('provider_probe', Path('scripts/provider_probe.py'))
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)

class ProbeTests(unittest.TestCase):
    def check_error(self, payload):
        error=HTTPError('https://api.plow.co',503,'unavailable',{},io.BytesIO(payload))
        with patch.dict(os.environ,{'PLOW_API_BASE':'https://api.plow.co','PLOW_AGENT_TOKEN':'test-private-token'}), patch.object(probe.urllib.request.OpenerDirector,'open',side_effect=error):
            return probe.probe()
    def test_disconnected_device_has_specific_recovery(self):
        result=self.check_error(b'{"detail":"Device is not connected"}')
        self.assertEqual(result['reason'],'latch_device_disconnected')
        self.assertFalse(result['ready'])
    def test_arbitrary_provider_error_never_echoes_private_body(self):
        result=self.check_error(b'{"detail":"secret-token-or-private-mail"}')
        self.assertNotIn('secret-token',str(result))
        self.assertEqual(result['reason'],'connected_tool_http_error')
