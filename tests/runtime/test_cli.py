"""Public CLI rejects malformed requests and resolves policies without writes."""
import json
import os
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

    def test_host_preflight_reports_capabilities_without_claiming_sandbox(self):
        code, result = self.request('host.preflight')
        self.assertEqual(code, 0, result)
        self.assertIn('enforcement', result['result'])
        self.assertEqual(result['result']['enforcement']['os_sandbox'], 'unsupported')

    def test_host_preflight_blocks_unavailable_required_controls(self):
        code, result = self.request('host.preflight', required_capabilities=['os_sandbox'])
        self.assertEqual(code, 2)
        self.assertIn('required host capabilities unavailable', result['error']['message'])

    def test_host_preflight_accepts_enforced_runtime_controls(self):
        code, result = self.request('host.preflight', required_capabilities=['sqlite_protocol', 'dispatch_leases'])
        self.assertEqual(code, 0, result)
        self.assertTrue(result['result']['ready'])

    def test_trace_adapt_requires_key_and_returns_signed_event(self):
        event = {'type': 'agentic.command.completed', 'evidence_id': 'e1', 'run_id': 'r',
                 'source_revision': 1, 'command': 'pytest', 'cwd': '.',
                 'source_hash': 'sha256:abc', 'exit_status': 0}
        payload = {'api_version': '1.0.0', 'operation': 'trace.adapt', 'event': event,
                   'identity': 'codex', 'issued_at': 10, 'expires_at': 20}
        missing = subprocess.run([sys.executable, str(ROOT / 'runtime/run.py')],
            input=json.dumps(payload), text=True, capture_output=True)
        self.assertEqual(missing.returncode, 2)
        env = dict(os.environ, AGENTIC_HOST_KEY='test-key')
        response = subprocess.run([sys.executable, str(ROOT / 'runtime/run.py')],
            input=json.dumps(payload), text=True, capture_output=True, env=env)
        self.assertEqual(response.returncode, 0, response.stderr)
        result = json.loads(response.stdout)
        self.assertTrue(result['ok'])
        self.assertEqual(result['result']['host_record']['identity'], 'codex')

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
            code, legacy = request('legacy.export', run_id='run-x', destination=str(pathlib.Path(root) / 'legacy-view'))
            self.assertEqual(code, 0, legacy)
            self.assertEqual(json.loads((pathlib.Path(root) / 'legacy-view' / 'meta.json').read_text())['status'], 'running')
            code, waiting = request('run.transition', run_id='run-x', target='waiting_for_user', coordinator_id='c1', lease_epoch=epoch,
                                    expected_revision=status['result']['revision'])
            self.assertEqual(code, 0, waiting)
            code, resumed = request('run.transition', run_id='run-x', target='running', coordinator_id='c1', lease_epoch=epoch, expected_revision=waiting['result']['revision'])
            self.assertEqual(code, 0, resumed)
            code, cancelled = request('run.cancel', run_id='run-x', coordinator_id='c1')
            self.assertEqual(code, 0, cancelled)
            self.assertEqual(cancelled['result']['state'], 'cancelled')

    def test_task_result_is_the_versioned_public_completion_operation(self):
        with tempfile.TemporaryDirectory() as root:
            worktree = pathlib.Path(root) / 'work-task-result'
            subprocess.run(['git', 'init', '-q', str(worktree)], check=True)
            subprocess.run(['git', '-C', str(worktree), 'checkout', '-q', '-b', 'feature/task-result'], check=True)
            def request(operation, **payload):
                payload['root'] = root
                return self.request(operation, **payload)
            code, started = request('run.start', task_input='task result', coordinator_id='c1',
                                    branch='feature/task-result', worktree=str(worktree),
                                    run_id='run-task-result', precondition={'ownership': 'verified'})
            self.assertEqual(code, 0, started)
            epoch = started['result']['lease_epoch']
            revision = started['result']['revision']
            code, reserved = request('task.dispatch', run_id='run-task-result',
                                     reservation_id='reservation-1', coordinator_id='c1',
                                     lease_epoch=epoch, expected_revision=revision)
            self.assertEqual(code, 0, reserved)
            code, status = request('run.status', run_id='run-task-result')
            self.assertEqual(code, 0, status)
            code, started_dispatch = request('dispatch.start', run_id='run-task-result',
                                             reservation_id='reservation-1', worker_id='worker-1',
                                             coordinator_id='c1', lease_epoch=epoch,
                                             expected_revision=status['result']['revision'])
            self.assertEqual(code, 0, started_dispatch)
            code, status = request('run.status', run_id='run-task-result')
            self.assertEqual(code, 0, status)
            code, result = request('task.result', run_id='run-task-result',
                                   reservation_id='reservation-1', outcome='succeeded',
                                   coordinator_id='c1', lease_epoch=epoch,
                                   expected_revision=status['result']['revision'])
            self.assertEqual(code, 0, result)
            self.assertEqual(result['result']['outcome'], 'succeeded')
            self.assertIsNotNone(result['result']['finished_at'])

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
            self.assertEqual(code, 2, terminal)
            self.assertIn('completion', terminal['error']['message'])
            code, terminal = request('run.cancel', run_id='run-terminal', coordinator_id='c1')
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

    def test_mailbox_caller_identity_never_discloses_messages(self):
        from runtime.agentic_runtime.store import RuntimeStore
        with tempfile.TemporaryDirectory() as root:
            store = RuntimeStore(root, clock=lambda: 100)
            store.create_run('mailbox')
            store.create_assignment('mailbox', 'a', 'worker', owned_paths=[], context_refs=[], acceptance=[])
            store.send_peer_message('mailbox', message_id='secret', assignment_id='a', assignment_revision=0,
                                    correlation_id='c', sender='worker', recipient='victim',
                                    message_type='task.progress', deadline=110, payload={'private': 'mailbox-content'})
            for reader in ('victim', 'attacker'):
                code, result = self.request('message.receive', root=root, run_id='mailbox', recipient='victim', reader_id=reader)
                self.assertEqual(code, 2)
                self.assertIn('host-issued', result['error']['message'])
                self.assertNotIn('result', result)
                self.assertNotIn('mailbox-content', json.dumps(result))
