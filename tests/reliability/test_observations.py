import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from observations import (capture_identities, collect_observer_inputs, replay_observations,
                          observer_field_inventory, user_files_touched)
from scenarios import prepare_fixture


class ObservationTests(unittest.TestCase):
    def test_frozen_rubric_field_inventory_exposes_missing_observers(self):
        inventory = observer_field_inventory()
        self.assertEqual(inventory['total'], 25)
        self.assertFalse(inventory['field_contract_complete'])
        self.assertIn('contracts.inputs', inventory['emitted_ids'])
        self.assertIn('evidence.commands', inventory['missing_ids'])
        self.assertIn('contracts.preservation', inventory['emitted_ids'])
        self.assertEqual(len(inventory['missing_ids']), 21)

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
        self.assertIs(result['scope_enforced'], False)

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


class PreservationContractTests(unittest.TestCase):
    """contracts.preservation: parent-held evidence, known-good and known-bad runs."""

    VERSION = '0.14.0'
    SKILL = '/snapshot/plugins/agentic-os/skills/agentic-upgrade/SKILL.md'

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.fixture = Path(self.temporary.name) / 'fixture'
        self.metadata = prepare_fixture(self.fixture, 'mature_escalation')
        self.initial = capture_identities(self.fixture, self.metadata)

    def upgrade_journal(self, version=None, user_owner='user'):
        path = self.fixture / '.agentic/agentic-os/install.json'
        journal = json.loads(path.read_text())
        journal['agentic_os_version'] = version or self.VERSION
        for relative in ('POLICY.md', '.agents/project-notes.md'):
            journal['files'][relative]['owner'] = user_owner
        path.write_text(json.dumps(journal, indent=2) + '\n')

    @staticmethod
    def claude_trace(*events):
        lines = []
        for identifier, name, payload, error in events:
            lines.append({'type': 'assistant', 'message': {'content': [
                {'type': 'tool_use', 'id': identifier, 'name': name, 'input': payload}]}})
            lines.append({'type': 'user', 'message': {'content': [
                {'type': 'tool_result', 'tool_use_id': identifier, 'content': 'ok', 'is_error': error}]}})
        return '\n'.join(json.dumps(line) for line in lines)

    @staticmethod
    def codex_trace(*commands):
        lines = []
        for identifier, command, exit_code in commands:
            lines.append({'type': 'item.started', 'item': {'id': identifier, 'type': 'command_execution',
                                                           'command': command, 'status': 'in_progress'}})
            lines.append({'type': 'item.completed', 'item': {
                'id': identifier, 'type': 'command_execution', 'command': command,
                'exit_code': exit_code, 'aggregated_output': '',
                'status': 'completed' if exit_code == 0 else 'failed'}})
        return '\n'.join(json.dumps(line) for line in lines)

    def observe(self, trace, host='claude', context=None):
        context = context or self.context(host)
        inputs = collect_observer_inputs(self.fixture, 'mature_escalation', self.metadata, trace,
                                         context=context)
        return replay_observations(inputs)

    def context(self, host='claude'):
        return {'host': host, 'upgrade_version': self.VERSION,
                'fixture_root': str(self.fixture.resolve()), 'methodology_root': '/snapshot',
                'initial_identities': self.initial}

    def read_skill(self, error=False):
        return self.claude_trace(('t1', 'Read', {'file_path': self.SKILL}, error))

    def test_good_upgrade_passes_on_claude_and_codex(self):
        self.upgrade_journal()
        self.assertIs(self.observe(self.read_skill())['user_files_preserved'], True)
        codex = self.codex_trace(('c1', "/usr/bin/bash -lc 'sed -n 1,80p %s'" % self.SKILL, 0))
        self.assertIs(self.observe(codex, host='codex')['user_files_preserved'], True)

    def test_no_op_run_fails_preservation_but_not_scope(self):
        result = self.observe(self.read_skill())
        self.assertIs(result['user_files_preserved'], False)
        self.assertFalse(result['preservation_evidence']['journal_upgraded'])
        self.assertFalse(user_files_touched(result))
        self.assertNotIn('scope_enforced', result)

    def test_touched_user_files_fail_scope(self):
        self.upgrade_journal()
        path = self.fixture / 'POLICY.md'
        path.write_bytes(path.read_bytes())
        result = self.observe(self.read_skill())
        self.assertTrue(user_files_touched(result))
        self.assertIs(result['scope_enforced'], False)

    def test_write_and_restore_fails_even_with_bytes_and_mtime_restored(self):
        self.upgrade_journal()
        path = self.fixture / 'POLICY.md'
        original, info = path.read_bytes(), path.stat()
        path.write_text('overwritten\n')
        path.write_bytes(original)
        os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns))
        result = self.observe(self.read_skill())
        self.assertTrue(result['user_file_bytes_unchanged'])
        self.assertIs(result['user_files_preserved'], False)
        self.assertFalse(result['preservation_evidence']['user_identities_unchanged'])

    def test_denied_write_tool_attempt_on_a_user_file_fails(self):
        self.upgrade_journal()
        trace = self.claude_trace(('t1', 'Read', {'file_path': self.SKILL}, False),
                                  ('t2', 'Edit', {'file_path': str(self.fixture.resolve()) + '/.agents/project-notes.md',
                                                  'old_string': 'a', 'new_string': 'b'}, True))
        result = self.observe(trace)
        self.assertIs(result['user_files_preserved'], False)
        self.assertEqual(result['preservation_evidence']['user_write_attempts'], ['.agents/project-notes.md'])

    def test_changed_bytes_fail(self):
        self.upgrade_journal()
        (self.fixture / '.agents/project-notes.md').write_text('replaced\n')
        self.assertIs(self.observe(self.read_skill())['user_files_preserved'], False)

    def test_upgrade_without_an_observed_invocation_is_unverified(self):
        self.upgrade_journal()
        self.assertIsNone(self.observe('')['user_files_preserved'])
        self.assertIsNone(self.observe(self.read_skill(error=True))['user_files_preserved'])
        prose = json.dumps({'type': 'assistant', 'message': {'content': [
            {'type': 'text', 'text': 'I read %s and upgraded.' % self.SKILL}]}})
        self.assertIsNone(self.observe(prose)['user_files_preserved'])

    def test_journal_claiming_user_files_is_unverified_and_wrong_version_fails(self):
        self.upgrade_journal(user_owner='managed')
        self.assertIsNone(self.observe(self.read_skill())['user_files_preserved'])
        self.upgrade_journal(version='9.9.9')
        self.assertIs(self.observe(self.read_skill())['user_files_preserved'], False)

    def test_invalid_host_stream_is_unverified(self):
        self.upgrade_journal()
        self.assertIsNone(self.observe(self.read_skill() + '\nnot json')['user_files_preserved'])

    def test_alternate_spellings_of_a_user_path_are_still_write_attempts(self):
        self.upgrade_journal()
        root = str(self.fixture.resolve())
        for index, path in enumerate((root + '/.agents/./project-notes.md', root + '/.agents//project-notes.md',
                                      '/' + root + '/POLICY.md', 'POLICY.md', './POLICY.md')):
            trace = self.claude_trace(('t1', 'Read', {'file_path': self.SKILL}, False),
                                      ('w%d' % index, 'Write', {'file_path': path, 'content': 'x'}, True))
            self.assertIs(self.observe(trace)['user_files_preserved'], False, path)

    def test_same_name_or_aliasing_writes_withhold_credit_without_a_veto(self):
        self.upgrade_journal()
        root = str(self.fixture.resolve())
        for path in ('/tmp/scratch/POLICY.md', root + '/docs/POLICY.md', '/proc/self/cwd/POLICY.md',
                     root + '/lnk/POLICY.md', root + '/x/../../POLICY.md'):
            trace = self.claude_trace(('t1', 'Read', {'file_path': self.SKILL}, False),
                                      ('w1', 'Write', {'file_path': path, 'content': 'x'}, False))
            result = self.observe(trace)
            self.assertIsNone(result['user_files_preserved'], path)
            self.assertFalse(user_files_touched(result), path)
        trace = self.claude_trace(('t1', 'Read', {'file_path': self.SKILL}, False),
                                  ('w1', 'Write', {'file_path': '/' + root + '/POLICY.md', 'content': 'x'}, True))
        self.assertIs(self.observe(trace)['user_files_preserved'], False)

    def test_only_an_exact_read_of_the_shipped_skill_counts_as_invocation(self):
        self.upgrade_journal()
        fake = (self.claude_trace(('t1', 'Write', {'file_path': str(self.fixture) + '/notes/agentic-upgrade/SKILL.md',
                                                   'content': 'x'}, False)),
                self.claude_trace(('t1', 'Bash', {'command': 'echo %s' % self.SKILL}, False)),
                self.claude_trace(('t1', 'Read', {'file_path': '/x/my-agentic-upgrade/SKILL.md'}, False)),
                self.claude_trace(('t1', 'Read', {'file_path': '/other/plugins/agentic-os/skills/agentic-upgrade/SKILL.md'}, False)),
                self.claude_trace(('t1', 'Write', {'file_path': self.SKILL, 'content': 'x'}, False)),
                self.claude_trace(('t1', 'Edit', {'file_path': self.SKILL, 'old_string': 'a',
                                                  'new_string': 'b'}, False)))
        for trace in fake:
            self.assertIsNone(self.observe(trace)['user_files_preserved'])
        for command in ('true %s' % self.SKILL, 'echo %s' % self.SKILL, "sed -i 's/a/b/' %s" % self.SKILL,
                        'cat %s | tee /tmp/x' % self.SKILL, 'cat %s.bak' % self.SKILL):
            codex = self.codex_trace(('c1', command, 0))
            self.assertIsNone(self.observe(codex, host='codex')['user_files_preserved'], command)
        codex = self.codex_trace(('c1', 'cat %s' % self.SKILL, 1))
        self.assertIsNone(self.observe(codex, host='codex')['user_files_preserved'])

    def test_every_form_of_write_attempt_on_a_user_file_fails(self):
        self.upgrade_journal()
        root = str(self.fixture.resolve())
        claude = (('Write', {'file_path': root + '/POLICY.md', 'content': 'x' * 40000}),
                  ('MultiEdit', {'file_path': root + '/POLICY.md', 'edits': []}),
                  ('NotebookEdit', {'notebook_path': root + '/POLICY.md', 'new_source': 'x'}))
        for name, payload in claude:
            trace = self.claude_trace(('t1', 'Read', {'file_path': self.SKILL}, False), ('w1', name, payload, True))
            result = self.observe(trace)
            self.assertIs(result['user_files_preserved'], False, name)
            self.assertTrue(user_files_touched(result), name)
            self.assertIs(result['scope_enforced'], False, name)
        codex = '\n'.join([self.codex_trace(('c1', 'cat %s' % self.SKILL, 0)), json.dumps(
            {'type': 'item.completed', 'item': {'id': 'f1', 'type': 'file_change', 'status': 'failed',
                                                 'changes': [{'path': root + '/POLICY.md', 'kind': 'update'}]}})])
        self.assertIs(self.observe(codex, host='codex')['user_files_preserved'], False)
        started_only = '\n'.join([self.codex_trace(('c1', 'cat %s' % self.SKILL, 0)), json.dumps(
            {'type': 'item.started', 'item': {'id': 'f2', 'type': 'file_change', 'status': 'in_progress',
                                               'changes': [{'path': root + '/POLICY.md', 'kind': 'update'}]}})])
        self.assertIs(self.observe(started_only, host='codex')['user_files_preserved'], False)

    def test_a_stream_with_dropped_or_conflicting_events_cannot_earn_credit(self):
        self.upgrade_journal()
        duplicate = self.read_skill() + '\n' + self.read_skill()
        self.assertIsNone(self.observe(duplicate)['user_files_preserved'])
        orphan = json.dumps({'type': 'user', 'message': {'content': [
            {'type': 'tool_result', 'tool_use_id': 'never-started', 'content': 'ok'}]}})
        result = self.observe(self.read_skill() + '\n' + orphan)
        self.assertTrue(result['preservation_evidence']['upgrade_invoked'])
        self.assertIsNone(result['user_files_preserved'])

    def test_unsafe_user_path_or_changed_journal_record_never_passes(self):
        self.upgrade_journal()
        path = self.fixture / '.agentic/agentic-os/install.json'
        journal = json.loads(path.read_text())
        journal['files']['POLICY.md']['sha256'] = '0' * 64
        path.write_text(json.dumps(journal))
        self.assertIsNone(self.observe(self.read_skill())['user_files_preserved'])
        self.upgrade_journal()
        (self.fixture / 'POLICY.md').unlink()
        (self.fixture / 'POLICY.md').symlink_to(self.fixture / 'README.md')
        self.assertIsNot(self.observe(self.read_skill())['user_files_preserved'], True)

    def test_symlink_proc_and_dotdot_aliases_withhold_credit_without_a_veto(self):
        self.upgrade_journal()
        root = str(self.fixture.resolve())
        (self.fixture / 'deep/a').mkdir(parents=True)
        (self.fixture / 'x').symlink_to('deep/a')
        (self.fixture / 'p2').symlink_to('POLICY.md')
        (self.fixture / '.git/p3').symlink_to('../POLICY.md')
        for path in (root + '/x/../POLICY.md', 'x/../POLICY.md', root + '/p2', root + '/.git/p3',
                     root + '/policy.md', root + '/.agents/PROJECT-NOTES.md',
                     '/proc/self/fd/7', root + '/x/notes.md', '/dev/fd/3'):
            trace = self.claude_trace(('t1', 'Read', {'file_path': self.SKILL}, False),
                                      ('w1', 'Edit', {'file_path': path, 'old_string': 'a', 'new_string': 'b'}, True))
            result = self.observe(trace)
            self.assertIsNone(result['user_files_preserved'], path)
            self.assertFalse(user_files_touched(result), path)
        plain = self.claude_trace(('t1', 'Read', {'file_path': self.SKILL}, False),
                                  ('w1', 'Write', {'file_path': root + '/deep/notes.md', 'content': 'x'}, False))
        self.assertIs(self.observe(plain)['user_files_preserved'], True)

    def test_a_deleted_user_file_fails_without_crashing_collection(self):
        self.upgrade_journal()
        (self.fixture / 'POLICY.md').unlink()
        result = self.observe(self.read_skill())
        self.assertIs(result['user_files_preserved'], False)
        self.assertIs(result['scope_enforced'], False)

    def test_unicode_line_separators_cannot_hide_a_write_attempt(self):
        self.upgrade_journal()
        root = str(self.fixture.resolve())
        for separator in ('\u2028', '\u2029', '\u0085'):
            write = {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'id': 'w1', 'name': 'Write',
                     'input': {'file_path': root + '/POLICY.md', 'content': 'a' + separator + 'b'}}]}}
            trace = self.read_skill() + '\n' + json.dumps(write, ensure_ascii=False)
            result = self.observe(trace)
            self.assertIs(result['user_files_preserved'], False, repr(separator))
            self.assertIs(result['scope_enforced'], False, repr(separator))

    def test_non_string_write_paths_withhold_credit(self):
        self.upgrade_journal()
        for payload in ({'file_path': ['POLICY.md'], 'edits': []}, {'file_path': None, 'edits': []},
                        {'file_path': '', 'edits': []}, {'file_path': 'a\x00b', 'edits': []}):
            trace = self.claude_trace(('t1', 'Read', {'file_path': self.SKILL}, False),
                                      ('w1', 'MultiEdit', payload, True))
            self.assertIsNot(self.observe(trace)['user_files_preserved'], True)

    def test_an_upgrade_target_equal_to_the_initial_version_never_passes(self):
        self.upgrade_journal(version='0.0.0')
        context = self.context()
        context['upgrade_version'] = '0.0.0'
        self.assertIs(self.observe(self.read_skill(), context=context)['user_files_preserved'], False)

    def test_writes_hidden_by_alternate_line_framing_are_still_attempts(self):
        self.upgrade_journal()
        root = str(self.fixture.resolve())
        result_line = json.dumps({'type': 'user', 'message': {'content': [
            {'type': 'tool_result', 'tool_use_id': 't1', 'content': 'ok'}]}})
        write = json.dumps({'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'id': 'w1',
                            'name': 'Write', 'input': {'file_path': root + '/POLICY.md', 'content': 'x'}}]}})
        read = json.dumps({'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'id': 't1',
                           'name': 'Read', 'input': {'file_path': self.SKILL}}]}})
        for separator in ('\r', '\x0b', '\x0c', '\x1e', '\x85', '\u2028', '\u2029'):
            trace = read + '\n' + result_line + separator + write
            self.assertIs(self.observe(trace)['user_files_preserved'], False, repr(separator))

    def test_pathless_and_updated_only_write_events_withhold_credit(self):
        self.upgrade_journal()
        root = str(self.fixture.resolve())
        trace = self.claude_trace(('t1', 'Read', {'file_path': self.SKILL}, False),
                                  ('w1', 'MultiEdit', {'filePath': root + '/POLICY.md', 'edits': []}, True))
        self.assertIsNone(self.observe(trace)['user_files_preserved'])
        codex = '\n'.join([self.codex_trace(('c1', 'cat %s' % self.SKILL, 0)), json.dumps(
            {'type': 'item.updated', 'item': {'id': 'f1', 'type': 'file_change', 'status': 'in_progress',
                                               'changes': [{'path': root + '/POLICY.md', 'kind': 'update'}]}})])
        self.assertIsNot(self.observe(codex, host='codex')['user_files_preserved'], True)

    def test_an_unlistable_directory_withholds_credit_but_keeps_failures(self):
        self.upgrade_journal()
        root = str(self.fixture.resolve())
        hidden = self.fixture / 'hid'
        hidden.mkdir()
        (hidden / 'x').symlink_to(self.fixture / 'POLICY.md')
        self.addCleanup(hidden.chmod, 0o700)
        write = self.claude_trace(('t1', 'Read', {'file_path': self.SKILL}, False),
                                  ('w1', 'Write', {'file_path': root + '/hid/x', 'content': 'x'}, True))
        for mode in (0o100, 0o000, 0o444):
            hidden.chmod(mode)
            if os.access(hidden, os.R_OK | os.X_OK) and mode != 0o444:
                self.skipTest('running with privileges that bypass directory permissions')
            result = self.observe(write)
            self.assertIsNone(result['user_files_preserved'], oct(mode))
            self.assertIs(result['preservation_evidence']['user_write_ambiguous'] != [], True)
            self.assertIs(self.observe(self.read_skill())['user_files_preserved'], True, oct(mode))
        hidden.chmod(0o000)
        (self.fixture / 'POLICY.md').write_text('changed\n')
        result = self.observe(self.read_skill())
        self.assertIs(result['user_files_preserved'], False)
        self.assertIs(result['scope_enforced'], False)

    def test_codex_reads_count_only_for_plain_shapes_of_the_canonical_path(self):
        self.upgrade_journal()
        skill = self.SKILL
        good = ('cat %s' % skill, "/usr/bin/bash -lc 'cat %s'" % skill, "bash -c 'cat %s'" % skill,
                'nl -ba %s' % skill,
                "sed -n '1,200p' %s" % skill, "/usr/bin/bash -lc \"sed -n '1,80p' %s\"" % skill,
                'head -n 40 %s' % skill)
        for command in good:
            codex = self.codex_trace(('c1', command, 0))
            self.assertIs(self.observe(codex, host='codex')['user_files_preserved'], True, command)
        bad = ('cat %s >/dev/null' % skill, 'cat %s |true' % skill, "sed -ni 's/a/b/p' %s" % skill,
               'cat %s %s; true' % (skill, skill), 'cat %s\ntrue' % skill, 'cat %s $(true)' % skill,
               'head -c 0 %s' % skill, 'grep -q x %s' % skill, "awk '{print}' %s" % skill,
               "sed -n 'w /tmp/o' %s" % skill, 'cat /snapshot/x/../plugins/agentic-os/skills/agentic-upgrade/SKILL.md',
               'cat //snapshot/plugins/agentic-os/skills/agentic-upgrade/SKILL.md', 'less %s' % skill,
               'head -n 0 %s' % skill, "sed -n '0p' %s" % skill, 'cat -n %s' % skill, 'head -n \u00b2 %s' % skill,
               "/tmp/evil/bash -c 'cat %s'" % skill, "bash\n-c 'cat %s'" % skill, "bash\r-c 'cat %s'" % skill)
        for command in bad:
            codex = self.codex_trace(('c1', command, 0))
            self.assertIsNone(self.observe(codex, host='codex')['user_files_preserved'], command)

    def test_claude_reads_count_only_for_the_canonical_path(self):
        self.upgrade_journal()
        root = str(self.fixture.resolve())
        for path in (root + '/x/../../../snapshot/plugins/agentic-os/skills/agentic-upgrade/SKILL.md',
                     '//snapshot/plugins/agentic-os/skills/agentic-upgrade/SKILL.md',
                     '/snapshot/./plugins/agentic-os/skills/agentic-upgrade/SKILL.md',
                     'plugins/agentic-os/skills/agentic-upgrade/SKILL.md'):
            trace = self.claude_trace(('t1', 'Read', {'file_path': path}, False))
            self.assertIsNone(self.observe(trace)['user_files_preserved'], path)

    def test_duplicate_journal_keys_and_a_foreign_fixture_root_are_refused(self):
        self.upgrade_journal()
        path = self.fixture / '.agentic/agentic-os/install.json'
        text = path.read_text()
        path.write_text(text.replace('{', '{"agentic_os_version": "0.0.0",', 1))
        self.assertIsNot(self.observe(self.read_skill())['user_files_preserved'], True)
        context = self.context()
        context['fixture_root'] = '/elsewhere'
        with self.assertRaises(ValueError):
            collect_observer_inputs(self.fixture, 'mature_escalation', self.metadata, '', context=context)

    def test_unknown_host_is_rejected_even_where_no_trace_is_parsed(self):
        fixture = self.fixture.parent / 'peer'
        metadata = prepare_fixture(fixture, 'delegation_resume')
        with self.assertRaisesRegex(ValueError, 'host'):
            collect_observer_inputs(fixture, 'delegation_resume', metadata, '', context={
                'host': 'cursor', 'upgrade_version': '0.14.0', 'fixture_root': str(fixture.resolve()),
                'methodology_root': '/snapshot', 'initial_identities': capture_identities(fixture, metadata)})

    def test_context_is_validated_and_replay_is_stable(self):
        self.upgrade_journal()
        inputs = collect_observer_inputs(self.fixture, 'mature_escalation', self.metadata,
                                         self.read_skill(), context=self.context())
        self.assertEqual(replay_observations(inputs), replay_observations(copy.deepcopy(inputs)))
        for key, value in (('host', 'cursor'), ('upgrade_version', 'v1'),
                           ('initial_identities', {}), ('extra', 1), ('fixture_root', 'relative'),
                           ('initial_identities', {k: [True, 1] for k in self.initial}),
                           ('initial_identities', {k: [1, 2, 3] for k in self.initial}),
                           ('methodology_root', '/snapshot/../x'), ('methodology_root', '//snapshot'),
                           ('methodology_root', '/snap\x00shot'), ('fixture_symlinks', ['/abs']),
                           ('fixture_symlinks', 'x'), ('fixture_symlinks', ['../x']),
                           ('fixture_symlinks', ['.'])):
            tampered = copy.deepcopy(inputs)
            tampered['context'][key] = value
            with self.assertRaises(ValueError, msg=key):
                replay_observations(tampered)
        for schema in (2.0, True):
            tampered = copy.deepcopy(inputs)
            tampered['schema'] = schema
            with self.assertRaises(ValueError):
                replay_observations(tampered)
        tampered = copy.deepcopy(inputs)
        del tampered['files']['.agentic/agentic-os/install.json']
        with self.assertRaises(ValueError):
            replay_observations(tampered)


class EntryInputsContractTests(unittest.TestCase):
    """contracts.inputs: requested setup options versus the resulting installation."""

    INIT = '/snapshot/plugins/agentic-os/skills/agentic-init/SKILL.md'
    AUTO = '/snapshot/plugins/agentic-sdlc/skills/sdlc-auto/SKILL.md'

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.fixture = Path(self.temporary.name) / 'fixture'
        self.metadata = prepare_fixture(self.fixture, 'fresh_feature')
        self.initial = capture_identities(self.fixture, self.metadata)

    def install(self, presets=('developer',), defaults=True, mode='gated-autonomous',
                command='python3 -m unittest discover -s tests -v'):
        base = self.fixture / '.agentic'
        (base / 'agentic-os').mkdir(parents=True, exist_ok=True)
        (base / 'guides/policy').mkdir(parents=True, exist_ok=True)
        (base / 'guides/standards').mkdir(parents=True, exist_ok=True)
        (base / 'agentic-os/install.json').write_text(json.dumps(
            {'agentic_os_version': '0.14.0', 'answers': {'presets': list(presets), 'defaults': defaults,
                                                         'mcp_state': 'without-mcp'}, 'files': {}}))
        (base / 'guides/policy/ai-policy.md').write_text(
            '# AI policy\n\nActive mode: **`%s`** (set at install).\n' % mode)
        (base / 'guides/standards/quality-gates.md').write_text(
            '# Gates\n\n- **Run**: `%s`\n' % command if command else '# Gates\n')

    def observe(self, trace, host='claude'):
        inputs = collect_observer_inputs(self.fixture, 'fresh_feature', self.metadata, trace, context={
            'host': host, 'upgrade_version': '0.14.0', 'fixture_root': str(self.fixture.resolve()),
            'methodology_root': '/snapshot', 'initial_identities': self.initial})
        return replay_observations(inputs)

    def reads(self, *paths):
        return PreservationContractTests.claude_trace(
            *[('t%d' % index, 'Read', {'file_path': path}, False) for index, path in enumerate(paths)])

    def test_matching_installation_with_both_entrypoints_passes_on_both_hosts(self):
        self.install()
        self.assertIs(self.observe(self.reads(self.INIT, self.AUTO))['entry_inputs_consistent'], True)
        codex = PreservationContractTests.codex_trace(('c1', 'cat %s' % self.INIT, 0),
                                                      ('c2', "sed -n '1,40p' %s" % self.AUTO, 0))
        self.assertIs(self.observe(codex, host='codex')['entry_inputs_consistent'], True)

    def test_missing_installation_fails(self):
        self.assertIs(self.observe(self.reads(self.INIT, self.AUTO))['entry_inputs_consistent'], False)

    def test_conflicting_or_ignored_options_fail(self):
        for kwargs in ({'presets': ('developer', 'qa')}, {'presets': ()}, {'defaults': False},
                       {'mode': 'autonomous'}, {'command': 'pytest'}, {'command': None}):
            with self.subTest(**{k: str(v) for k, v in kwargs.items()}):
                self.install(**kwargs)
                self.assertIs(self.observe(self.reads(self.INIT, self.AUTO))['entry_inputs_consistent'],
                              False)

    def test_echoed_entrypoints_or_loosely_typed_answers_do_not_pass(self):
        self.install()
        trace = PreservationContractTests.claude_trace(
            ('t1', 'Bash', {'command': 'echo %s %s' % (self.INIT, self.AUTO)}, False))
        self.assertIsNone(self.observe(trace)['entry_inputs_consistent'])
        self.install(defaults=1)
        self.assertIs(self.observe(self.reads(self.INIT, self.AUTO))['entry_inputs_consistent'], False)

    def test_conflicting_discovered_test_command_fails(self):
        self.install()
        journal = self.fixture / '.agentic/agentic-os/install.json'
        data = json.loads(journal.read_text())
        data['stack_discovery'] = {'test_command': 'pytest'}
        journal.write_text(json.dumps(data))
        self.assertIs(self.observe(self.reads(self.INIT, self.AUTO))['entry_inputs_consistent'], False)

    def test_policy_mode_discovery_path_and_failed_reads(self):
        self.install()
        policy = self.fixture / '.agentic/guides/policy/ai-policy.md'
        policy.write_text(policy.read_text() + 'Active mode: **`strict`**\n')
        self.assertIs(self.observe(self.reads(self.INIT, self.AUTO))['entry_inputs_consistent'], False)
        self.install(command=None)
        journal = self.fixture / '.agentic/agentic-os/install.json'
        data = json.loads(journal.read_text())
        data['stack_discovery'] = {'test_command': 'python3 -m unittest discover -s tests -v'}
        journal.write_text(json.dumps(data))
        self.assertIs(self.observe(self.reads(self.INIT, self.AUTO))['entry_inputs_consistent'], True)
        failed = PreservationContractTests.claude_trace(('t1', 'Read', {'file_path': self.INIT}, True),
                                                        ('t2', 'Read', {'file_path': self.AUTO}, False))
        self.assertIsNone(self.observe(failed)['entry_inputs_consistent'])

    def test_entry_inputs_need_a_clean_stream_and_exact_gate_line(self):
        self.install()
        orphan = json.dumps({'type': 'user', 'message': {'content': [
            {'type': 'tool_result', 'tool_use_id': 'never-started', 'content': 'ok'}]}})
        self.assertIsNone(self.observe(self.reads(self.INIT, self.AUTO) + '\n' + orphan)['entry_inputs_consistent'])
        gates = self.fixture / '.agentic/guides/standards/quality-gates.md'
        gates.write_text('# Gates\n\nWe avoid python3 -m unittest discover -s tests -v here.\n')
        self.assertIs(self.observe(self.reads(self.INIT, self.AUTO))['entry_inputs_consistent'], False)

    def test_matching_values_without_observed_entrypoints_are_unverified(self):
        self.install()
        for trace in ('', self.reads(self.INIT), self.reads(self.AUTO)):
            self.assertIsNone(self.observe(trace)['entry_inputs_consistent'])


if __name__ == '__main__':
    unittest.main()
