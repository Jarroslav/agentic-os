"""Public CLI rejects malformed requests and resolves policies without writes."""
import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]


class CLITests(unittest.TestCase):
    def request(self, operation, **payload):
        response = subprocess.run([sys.executable, str(ROOT / 'runtime/run.py')],
            input=json.dumps({'api_version': '1.0.0', 'operation': operation, **payload}),
            text=True, capture_output=True)
        self.assertNotIn('Traceback', response.stderr)
        return response.returncode, json.loads(response.stdout)

    def test_policy_resolves(self):
        code, result = self.request('policy.resolve', entrypoint='sdlc-auto')
        self.assertEqual(code, 0, result)
        self.assertTrue(result['ok'])
        self.assertEqual(result['result']['max_dispatches'], 64)

    def test_unknown_request_field_is_rejected(self):
        code, result = self.request('registry.get', ignored=True)
        self.assertEqual(code, 2)
        self.assertFalse(result['ok'])

    def test_duplicate_json_keys_are_rejected(self):
        response = subprocess.run([sys.executable, str(ROOT / 'runtime/run.py')],
            input='{"api_version":"2.0.0","api_version":"1.0.0","operation":"registry.get"}',
            text=True, capture_output=True)
        self.assertEqual(response.returncode, 2)
        self.assertFalse(json.loads(response.stdout)['ok'])

    def test_unknown_operation_is_rejected(self):
        code, result = self.request('run.complete')
        self.assertEqual(code, 2)
        self.assertFalse(result['ok'])

    def test_normalization_requires_explicit_legacy_adapter(self):
        payload = {'contract_version': '1.0.0', 'raw_input': 'fix fixture'}
        code, _ = self.request('input.normalize', payload=payload)
        self.assertEqual(code, 2)
        code, result = self.request('input.normalize', payload=payload, legacy=True)
        self.assertEqual(code, 0, result)
        self.assertEqual(result['result']['task_input'], 'fix fixture')

    def test_transition_and_retry_validation(self):
        code, result = self.request('transition.validate', source='running', target='completed')
        self.assertEqual(code, 0, result)
        code, _ = self.request('transition.validate', source='completed', target='running')
        self.assertEqual(code, 2)
        code, result = self.request('retry.allowed', loop_id='gate-runner.retry', attempts_used=3)
        self.assertEqual(code, 0, result)
        self.assertFalse(result['result'])

    def test_lookup_rejects_unknown_contract_ids(self):
        code, result = self.request('contract.lookup', section='gates', identifier='plan.approved')
        self.assertEqual(code, 0, result)
        self.assertEqual(result['result']['phase'], 5)
        for section, identifier in [('gates', 'invented'), ('phases', '13'), ('unknown', 'x')]:
            code, _ = self.request('contract.lookup', section=section, identifier=identifier)
            self.assertEqual(code, 2)
