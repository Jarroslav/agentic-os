import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from suite import trial_schedule, reserve_trial, finish_trial, report, write_new, capture_boundary, run_trial


class SuiteTests(unittest.TestCase):
    def test_schedule_is_exactly_authorized_trials(self):
        baseline = trial_schedule('baseline')
        candidate = trial_schedule('candidate')
        self.assertEqual(len(baseline), 24)
        self.assertEqual(len(candidate), 24)
        self.assertEqual(len({s['id'] for s in baseline + candidate}), 48)
        self.assertEqual({s['repetition'] for s in baseline}, {1, 2, 3})
        self.assertEqual({s['host'] for s in baseline}, {'claude', 'codex'})
        with self.assertRaises(ValueError):
            trial_schedule('extra')

    def test_slot_is_consumed_before_launch_and_cannot_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            slot = trial_schedule('baseline')[0]
            reserve_trial(root, slot)
            with self.assertRaises(FileExistsError):
                reserve_trial(root, slot)
            receipt = json.loads((root / 'trials' / slot['id'] / 'reservation.json').read_text())
            self.assertEqual(receipt['status'], 'reserved')
            self.assertEqual(receipt['slot'], slot)

    def test_trial_finishes_once_and_coordinates_cannot_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            slot = trial_schedule('baseline')[0]
            reserve_trial(root, slot)
            with self.assertRaises(ValueError):
                finish_trial(root, slot, {'host': 'other', 'status': 'completed'})
            finish_trial(root, slot, {'status': 'infrastructure_failed', 'error': 'no credentials'})
            with self.assertRaises(FileExistsError):
                finish_trial(root, slot, {'status': 'completed'})

    def test_report_rejects_unfrozen_fabricated_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            slot = trial_schedule('baseline')[0]
            location = root / 'trials' / slot['id']
            location.mkdir(parents=True)
            (location / 'result.json').write_text(json.dumps({
                **slot, 'status': 'completed', 'observations': {'user_files_preserved': True},
                'evidence': ['/does/not/exist'], 'source_revision': 'wrong'}))
            with self.assertRaises((ValueError, FileNotFoundError)):
                report(root)

    def test_self_consistent_fake_candidate_100_is_rejected(self):
        from suite import tree_hash, runner_hashes
        from scoring import RUBRIC
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / 'source').mkdir()
            (root / 'dependency').mkdir()
            write_new(root / 'manifest.json', {'phase': 'candidate', 'revision': 'fake',
                'source_sha256': tree_hash(root / 'source'),
                'dependency_sha256': tree_hash(root / 'dependency'),
                'runner_sha256': runner_hashes()})
            for slot in trial_schedule('candidate'):
                directory = reserve_trial(root, slot)
                observations = {a['observation']: True for a in RUBRIC}
                write_new(directory / 'oracle.json', observations)
                write_new(directory / 'fixture-manifest.json', {})
                finish_trial(root, slot, {'status': 'completed', 'source_revision': 'fake',
                    'observations': observations, 'evidence': [str(directory / 'oracle.json'),
                    str(directory / 'fixture-manifest.json')]})
            with self.assertRaises(ValueError):
                report(root)

    def make_report_fixture(self, root):
        from scenarios import prepare_fixture, prompt_for
        from suite import file_hash
        profile = {'model': 'fixture-model', 'isolation_supported': True}
        manifest = {'phase': 'baseline', 'revision': 'fixed',
                    'hosts': {'claude': {'profile': profile}}}
        write_new(root / 'manifest.json', manifest)
        slot = trial_schedule('baseline')[0]
        directory = reserve_trial(root, slot)
        metadata = prepare_fixture(directory / 'fixture', slot['scenario'])
        write_new(directory / 'fixture-manifest.json', metadata)
        write_new(directory / 'before-oracle.json', {})
        (directory / 'prompt.txt').write_text(prompt_for(slot['scenario'], root / 'source'))
        (directory / 'trace').mkdir()
        stdout = directory / 'trace/stdout.jsonl'
        stderr = directory / 'trace/stderr.txt'
        stdout.write_text(json.dumps({'type': 'system', 'model': 'fixture-model'}) + '\n')
        stderr.write_text('')
        write_new(directory / 'execution-receipt.json', {'schema': 1, 'slot': slot,
            'profile': profile, 'manifest_sha256': file_hash(root / 'manifest.json'),
            'status': 'completed', 'segments': [{'host': 'claude', 'status': 'completed', 'argv': ['fixture-host'],
            'observed_model': 'fixture-model', 'raw_stdout_path': str(stdout),
            'raw_stderr_path': str(stderr)}]})
        from observations import collect_observer_inputs, replay_observations
        inputs = collect_observer_inputs(directory / 'fixture', slot['scenario'], metadata,
                                         stdout.read_text(), execution_receipts=json.loads(
                                             (directory / 'execution-receipt.json').read_text())['segments'])
        observations = replay_observations(inputs)
        if observations.get('unauthorized_action_paths'):
            observations['required_approval_enforced'] = False
        if observations.get('user_files_preserved') is False:
            observations['scope_enforced'] = False
        write_new(directory / 'observer-inputs.json', inputs)
        write_new(directory / 'oracle.json', observations)
        finish_trial(root, slot, {'status': 'completed', 'source_revision': 'fixed',
                     'observations': observations, 'fixture_sha256': metadata['fixture_hash'],
                     'evidence': [str(directory / name) for name in ('oracle.json',
                     'fixture-manifest.json', 'before-oracle.json', 'prompt.txt',
                     'execution-receipt.json', 'observer-inputs.json', 'trace/stdout.jsonl', 'trace/stderr.txt')]})
        return directory

    @patch('hosts.inspect_host', return_value={'available': False, 'profile': None})
    def test_manifest_binds_revision_archive_and_baseline(self, inspect):
        from suite import freeze, verify_freeze
        from scenarios import prepare_fixture
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            metadata = prepare_fixture(root / 'repo', 'fresh_feature')
            (root / 'dep').mkdir()
            baseline = freeze(root / 'baseline', root / 'repo', metadata['initial_revision'], root / 'dep')
            candidate = freeze(root / 'candidate', root / 'repo', metadata['initial_revision'],
                               root / 'dep', 'candidate', root / 'baseline')
            verify_freeze(root / 'candidate', candidate)
            for field, value in (('schema', 1), ('revision', 'a' * 40),
                                 ('baseline_manifest_sha256', 'b' * 64)):
                with self.subTest(field=field), self.assertRaises(ValueError):
                    verify_freeze(root / 'candidate', {**candidate, field: value})
            (root / 'candidate/source/TASK.md').write_text('changed')
            with self.assertRaises(ValueError):
                verify_freeze(root / 'candidate', candidate)

    def test_receipt_rejects_rehashed_missing_traces_model_and_fixture_forgery(self):
        from suite import validate_execution
        for corruption in ('missing_trace', 'model', 'profile', 'fixture', 'prompt'):
            with self.subTest(corruption=corruption), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                directory = self.make_report_fixture(root)
                trial = json.loads((directory / 'result.json').read_text())
                receipt = json.loads((directory / 'execution-receipt.json').read_text())
                if corruption == 'missing_trace':
                    trial['evidence'].remove(str(directory / 'trace/stdout.jsonl'))
                elif corruption == 'model':
                    (directory / 'trace/stdout.jsonl').write_text('{}')
                elif corruption == 'profile':
                    receipt['profile']['model'] = 'different'
                elif corruption == 'fixture':
                    (directory / 'fixture-manifest.json').write_text('{}')
                elif corruption == 'prompt':
                    (directory / 'prompt.txt').write_text('fabricated')
                (directory / 'execution-receipt.json').write_text(json.dumps(receipt))
                with self.assertRaises(ValueError):
                    validate_execution(directory, trial,
                        json.loads((root / 'manifest.json').read_text()), trial_schedule('baseline')[0])

    @patch('suite.verify_freeze')
    def test_report_requires_bound_evidence(self, verify):
        for corrupt in ('none', 'revision', 'phase', 'reservation', 'missing', 'changed', 'observation'):
            with self.subTest(corrupt=corrupt), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                trial = self.make_report_fixture(root)
                result_path = trial / 'result.json'
                result = json.loads(result_path.read_text())
                if corrupt == 'revision':
                    result['source_revision'] = 'other'
                elif corrupt == 'phase':
                    result['phase'] = 'candidate'
                elif corrupt == 'reservation':
                    (trial / 'reservation.json').unlink()
                elif corrupt == 'missing':
                    (trial / 'oracle.json').unlink()
                elif corrupt == 'changed':
                    (trial / 'oracle.json').write_text('{}')
                elif corrupt == 'observation':
                    result['observations']['user_files_preserved'] = False
                result_path.write_text(json.dumps(result))
                if corrupt == 'none':
                    self.assertEqual(report(root)['completed_trial_records'], 1)
                else:
                    with self.assertRaises((ValueError, FileNotFoundError)):
                        report(root)

    @patch('suite.verify_freeze')
    def test_rehashed_oracle_verdict_is_rejected_by_replay(self, verify):
        from suite import file_hash
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            directory = self.make_report_fixture(root)
            trial = json.loads((directory / 'result.json').read_text())
            trial['observations']['user_files_preserved'] = False
            (directory / 'oracle.json').write_text(json.dumps(trial['observations']))
            trial['evidence_sha256'][str(directory / 'oracle.json')] = file_hash(directory / 'oracle.json')
            (directory / 'result.json').write_text(json.dumps(trial))
            with self.assertRaisesRegex(ValueError, 'replayed'):
                report(root)

    @patch('scenarios.oracle_observations', return_value={'remaining_work_verified': False})
    def test_checkpoint_retains_legacy_state_without_awarding_recovery(self, oracle):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            state = fixture / 'docs/superpowers/runs/original-run'
            state.mkdir(parents=True)
            payload = b'{"run_id":"original-run","status":"interrupted"}'
            (state / 'meta.json').write_bytes(payload)
            (state / 'escape.json').symlink_to('/etc/passwd')
            captured = capture_boundary(fixture, 'delegation_resume', {})
            records = captured['artifact_claims']
            self.assertEqual(bytes.fromhex(records['docs/superpowers/runs/original-run/meta.json']['content_hex']), payload)
            self.assertEqual(records['docs/superpowers/runs/original-run/escape.json']['error'], 'not a regular file')
            self.assertFalse(captured['behavior']['remaining_work_verified'])
            self.assertIsNone(captured['recovery_verified'])

    @patch('suite.verify_freeze')
    @patch('hosts.inspect_host')
    def test_host_preflight_does_not_consume_trial_budget(self, inspect, verify):
        for changed in (False, True):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                host = {'available': True, 'profile': {'model': 'fixture-model',
                        'isolation_supported': False, 'unsupported_channels': ['uncertified']}}
                write_new(root / 'manifest.json', {'phase': 'baseline', 'hosts': {'claude': host}})
                inspect.return_value = ({**host, 'version': 'changed'} if changed else host)
                with self.assertRaises(ValueError):
                    run_trial(root, trial_schedule('baseline')[0])
                self.assertFalse((root / 'trials').exists())


if __name__ == '__main__':
    unittest.main()
