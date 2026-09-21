"""Public CLI rejects malformed requests and resolves policies without writes."""
import json
import pathlib
import subprocess
import sys
import tempfile
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

    def test_run_start_status_dispatch_and_cancel_are_versioned(self):
        with tempfile.TemporaryDirectory() as root:
            worktree = pathlib.Path(root) / 'work-x'
            subprocess.run(['git', 'init', '-q', str(worktree)], check=True)
            subprocess.run(['git', '-C', str(worktree), 'checkout', '-q', '-b', 'feature/x'], check=True)
            def request(operation, **payload):
                payload['root'] = root
                return self.request(operation, **payload)
            code, result = request('run.start', task_input='bounded task', coordinator_id='c1',
                                   branch='feature/x', worktree=str(worktree), run_id='run-x',
                                   precondition={'ownership': 'verified'})
            self.assertEqual(code, 0, result)
            self.assertEqual(result['result']['state'], 'running')
            epoch = result['result']['lease_epoch']
            code, status = request('run.status', run_id='run-x')
            self.assertEqual(code, 0, status)
            code, dispatched = request('task.dispatch', run_id='run-x', reservation_id='d1', max_dispatches=1, lease_epoch=epoch,
                                       coordinator_id='c1', expected_revision=status['result']['revision'])
            self.assertEqual(code, 0, dispatched)
            self.assertTrue(dispatched['result']['reserved'])
            code, status = request('run.status', run_id='run-x')
            self.assertEqual(code, 0, status)
            code, waiting = request('run.transition', run_id='run-x', target='waiting_for_user', coordinator_id='c1', lease_epoch=epoch,
                                    expected_revision=status['result']['revision'])
            self.assertEqual(code, 0, waiting)
            code, resumed = request('run.transition', run_id='run-x', target='running', coordinator_id='c1', lease_epoch=epoch, expected_revision=waiting['result']['revision'])
            self.assertEqual(code, 0, resumed)
            code, cancelled = request('run.cancel', run_id='run-x', coordinator_id='c1')
            self.assertEqual(code, 0, cancelled)
            self.assertEqual(cancelled['result']['state'], 'cancelled')

    def test_legacy_import_is_reachable_through_versioned_runtime(self):
        with tempfile.TemporaryDirectory() as root:
            source = pathlib.Path(root) / 'legacy.json'
            source.write_bytes(b'legacy fixture')
            worktree = pathlib.Path(root) / 'work-import'
            subprocess.run(['git', 'init', '-q', str(worktree)], check=True)
            subprocess.run(['git', '-C', str(worktree), 'checkout', '-q', '-b', 'feature/import'], check=True)
            def request(operation, **payload):
                payload['root'] = root
                return self.request(operation, **payload)
            code, _ = request('run.start', task_input='import', coordinator_id='c1',
                              branch='feature/import', worktree=str(worktree), run_id='run-import',
                              precondition={'ownership': 'verified'})
            self.assertEqual(code, 0)
            code, result = request('legacy.import', run_id='run-import', source=str(source))
            self.assertEqual(code, 0, result)
            self.assertEqual(result['result']['bytes'], len(b'legacy fixture'))

    def test_invalid_resume_and_cancel_do_not_mutate_terminal_runs(self):
        with tempfile.TemporaryDirectory() as root:
            worktree = pathlib.Path(root) / 'work'
            subprocess.run(['git', 'init', '-q', str(worktree)], check=True)
            subprocess.run(['git', '-C', str(worktree), 'checkout', '-q', '-b', 'feature/work'], check=True)
            def request(operation, **payload):
                payload['root'] = root
                return self.request(operation, **payload)
            code, started = request('run.start', task_input='done', coordinator_id='c1',
                                    branch='feature/work', worktree=str(worktree), run_id='run-terminal',
                                    precondition={'ownership': 'verified'})
            self.assertEqual(code, 0, started)
            code, terminal = request('run.transition', run_id='run-terminal', target='completed',
                                     coordinator_id='c1', lease_epoch=started['result']['lease_epoch'],
                                     expected_revision=started['result']['revision'])
            self.assertEqual(code, 0, terminal)
            revision = terminal['result']['revision']
            code, result = request('run.resume', run_id='run-terminal', coordinator_id='c2')
            self.assertEqual(code, 2)
            self.assertFalse(result['ok'])
            code, result = request('run.cancel', run_id='run-terminal', coordinator_id='c2')
            self.assertEqual(code, 2)
            self.assertFalse(result['ok'])
            code, status = request('run.status', run_id='run-terminal')
            self.assertEqual(code, 0, status)
            self.assertEqual(status['result']['revision'], revision)
