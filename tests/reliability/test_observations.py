import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from observations import collect_observer_inputs, replay_observations
from scenarios import prepare_fixture


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.fixture = self.root / 'fixture'
        self.metadata = prepare_fixture(self.fixture, 'fresh_feature')

    def collect(self):
        return collect_observer_inputs(self.fixture, 'fresh_feature', self.metadata,
                                       '{"type":"assistant","text":"all checks pass"}')

    @patch('scenarios._sandbox_executable', return_value=None)
    @patch('scenarios._linux_executable', return_value=None)
    def test_replay_never_uses_injected_verdict(self, linux_sandbox, sandbox):
        inputs = self.collect()
        self.assertIsNone(replay_observations(inputs)['behavior_verified'])
        inputs['observations'] = {'behavior_verified': True}
        with self.assertRaises(ValueError):
            replay_observations(inputs)

    @patch('scenarios._sandbox_executable', return_value=None)
    @patch('scenarios._linux_executable', return_value=None)
    def test_metadata_and_source_bytes_are_bound(self, linux_sandbox, sandbox):
        original = self.collect()
        for key in ('metadata', 'files'):
            with self.subTest(key=key):
                inputs = copy.deepcopy(original)
                if key == 'metadata':
                    inputs['metadata']['fixture_hash'] = 'invented'
                else:
                    inputs['files']['app.py']['data'] = 'eA=='
                with self.assertRaises(ValueError):
                    replay_observations(inputs)

    def test_symlink_target_is_not_read_or_retained(self):
        secret = self.root / 'private.txt'
        secret.write_text('private-canary')
        (self.fixture / 'app.py').unlink()
        (self.fixture / 'app.py').symlink_to(secret)
        inputs = self.collect()
        self.assertEqual(inputs['files']['app.py'], {'kind': 'unsafe'})
        self.assertNotIn('private-canary', str(inputs))
        self.assertFalse(replay_observations(inputs)['behavior_verified'])

    def test_replay_is_stable_and_executes_retained_source(self):
        (self.fixture / 'app.py').write_text(
            'def normalize_tags(tags):\n    return sorted({tag.strip().lower() for tag in tags if tag.strip()})\n')
        inputs = self.collect()
        first = replay_observations(inputs)
        second = replay_observations(inputs)
        self.assertEqual(first, second)
        if first['sandbox_enforced']:
            self.assertTrue(first['behavior_verified'])
        else:
            self.assertIsNone(first['behavior_verified'])

    def test_extra_paths_and_large_files_are_rejected(self):
        inputs = self.collect()
        inputs['files']['../outside'] = {'kind': 'missing'}
        with self.assertRaises(ValueError):
            replay_observations(inputs)
        (self.fixture / 'app.py').write_bytes(b'x' * (1024 * 1024 + 1))
        with self.assertRaises(ValueError):
            self.collect()

    @patch('scenarios._sandbox_executable', return_value=None)
    def test_deleted_peer_checkpoint_is_not_reconstructed_as_preserved(self, sandbox):
        fixture = self.root / 'peer-fixture'
        metadata = prepare_fixture(fixture, 'delegation_resume')
        (fixture / '.fixture/checkpoint.json').unlink()
        inputs = collect_observer_inputs(fixture, 'delegation_resume', metadata, '')
        self.assertEqual(inputs['files']['.fixture/checkpoint.json'], {'kind': 'missing'})
        result = replay_observations(inputs)
        self.assertFalse(result['checkpoint_preserved'])
        self.assertFalse(result['user_files_preserved'])

    def test_unchanged_user_files_without_an_observed_upgrade_are_unverified(self):
        fixture = self.root / 'mature-fixture'
        metadata = prepare_fixture(fixture, 'mature_escalation')
        inputs = collect_observer_inputs(fixture, 'mature_escalation', metadata, '')
        result = replay_observations(inputs)
        self.assertTrue(result['user_file_bytes_unchanged'])
        self.assertIsNone(result['user_files_preserved'])

    def test_unvalidated_upgrade_receipts_do_not_earn_preservation_credit(self):
        fixture = self.root / 'mature-receipt-fixture'
        metadata = prepare_fixture(fixture, 'mature_escalation')
        inputs = collect_observer_inputs(fixture, 'mature_escalation', metadata, '')
        inputs['execution_receipts'] = [{'type': 'managed.upgrade.completed', 'status': 'success'}]
        inputs['backend_events'] = [{'type': 'managed.content.changed', 'paths': ['plugin/README.md']}]
        result = replay_observations(inputs)
        self.assertTrue(result['user_file_bytes_unchanged'])
        self.assertIsNone(result['user_files_preserved'])

    def test_changed_user_files_fail_even_when_upgrade_is_unobserved(self):
        fixture = self.root / 'mature-changed-fixture'
        metadata = prepare_fixture(fixture, 'mature_escalation')
        (fixture / 'POLICY.md').write_text('changed by candidate\n')
        inputs = collect_observer_inputs(fixture, 'mature_escalation', metadata, '')
        result = replay_observations(inputs)
        self.assertFalse(result['user_file_bytes_unchanged'])
        self.assertFalse(result['user_files_preserved'])


if __name__ == '__main__':
    unittest.main()
