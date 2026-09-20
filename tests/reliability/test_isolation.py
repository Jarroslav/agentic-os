"""Kernel-backed offline containment controls; never invokes a model host."""
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('isolation', Path(__file__).with_name('isolation.py'))
isolation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(isolation)


class IsolationTests(unittest.TestCase):
    @unittest.skipUnless(isolation.executable(), 'requires macOS sandbox-exec')
    def test_kernel_controls_preserve_allowed_io_and_deny_external_io(self):
        result = isolation.probe_filesystem_boundary()
        self.assertTrue(result['filesystem_enforced'], result)
        self.assertEqual(len(result['checks']), 16)
        self.assertFalse(result['host_certified'])

    def test_missing_platform_is_not_certification(self):
        with mock.patch.object(isolation, 'executable', return_value=None):
            result = isolation.probe_filesystem_boundary()
        self.assertFalse(result['filesystem_enforced'])
        self.assertIn('unavailable', result['error'])

    def test_empty_or_forged_controls_do_not_pass(self):
        for payload in ({}, {'fixture_read': True}, {'fixture_read': 'true'}):
            with mock.patch.object(isolation, 'executable', return_value='/sandbox'), \
                 mock.patch.object(isolation.subprocess, 'run', return_value=
                                   subprocess.CompletedProcess([], 0, json.dumps(payload), '')):
                result = isolation.probe_filesystem_boundary()
            self.assertFalse(result['filesystem_enforced'])

    def test_timeout_is_not_certification(self):
        with mock.patch.object(isolation, 'executable', return_value='/sandbox'), \
             mock.patch.object(isolation.subprocess, 'run', side_effect=subprocess.TimeoutExpired([], 1)):
            result = isolation.probe_filesystem_boundary()
        self.assertFalse(result['filesystem_enforced'])
        self.assertIn('TimeoutExpired', result['error'])

    def test_auth_exception_is_exact_not_home_subtree(self):
        home = Path('/private/synthetic-home')
        profile = isolation.filesystem_profile(Path('/private/fixture'), [], [home / 'auth.json'])
        self.assertIn('(literal "/private/synthetic-home/auth.json")', profile)
        self.assertNotIn('(subpath "/private/synthetic-home")', profile)


if __name__ == '__main__':
    unittest.main()
