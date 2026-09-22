"""Kernel-backed offline containment controls; never invokes a model host."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
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


def _bwrap_usable() -> bool:
    bwrap = isolation.linux_executable()
    if bwrap is None:
        return False
    probe = subprocess.run(isolation.linux_argv(bwrap, Path('/tmp'), command=['/bin/true']),
                           capture_output=True)
    return probe.returncode == 0


def _git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / 'file').write_text('v1')
    env = {'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t', 'GIT_COMMITTER_NAME': 't',
           'GIT_COMMITTER_EMAIL': 't@t', 'PATH': '/usr/bin:/bin'}
    for args in (['init', '-q'], ['add', '.'], ['commit', '-qm', 'init']):
        subprocess.run(['git', '-C', str(path), *args], check=True, env=env)
    return path


class LinuxIsolationTests(unittest.TestCase):
    @unittest.skipUnless(_bwrap_usable(), 'requires bubblewrap with user namespaces')
    def test_bubblewrap_controls_pass_on_real_kernel(self):
        result = isolation.probe_linux_boundary()
        self.assertTrue(result['filesystem_enforced'], result)
        self.assertEqual(set(result['checks']), isolation.LINUX_CHECKS)
        self.assertFalse(result['host_certified'])
        self.assertEqual(result['host_identity']['mechanism'], 'bubblewrap')

    @unittest.skipUnless(_bwrap_usable(), 'requires bubblewrap with user namespaces')
    def test_evidence_is_stable_so_frozen_profiles_do_not_drift(self):
        self.assertEqual(isolation.probe_linux_boundary(), isolation.probe_linux_boundary())

    @unittest.skipUnless(_bwrap_usable(), 'requires bubblewrap with user namespaces')
    def test_real_host_globals_are_invisible(self):
        with tempfile.TemporaryDirectory() as home:
            for name in ('.claude', '.codex', '.agents'):
                (Path(home) / name).mkdir()
                (Path(home) / name / 'AGENTS.md').write_text('global instruction')
            result = isolation.probe_linux_boundary(home=Path(home))
        self.assertEqual(result['host_globals_checked'], 3)
        self.assertTrue(result['checks']['host_globals_hidden'], result)
        self.assertTrue(result['filesystem_enforced'], result)

    @unittest.skipUnless(sys.platform.startswith('linux'), 'requires Linux')
    def test_unsandboxed_canary_detects_every_missing_control(self):
        with tempfile.TemporaryDirectory() as home:
            (Path(home) / '.claude').mkdir()
            with mock.patch.object(isolation, 'linux_executable', return_value='/usr/bin/bwrap'), \
                 mock.patch.object(isolation, 'linux_argv',
                                   side_effect=lambda *a, **k: list(a[5])):
                result = isolation.probe_linux_boundary(home=Path(home))
        self.assertFalse(result['filesystem_enforced'])
        failed = {name for name, ok in result['checks'].items() if ok is not True}
        self.assertTrue({'snapshot:r', 'snapshot:w', 'auth_sibling_denied', 'plugin_write_denied',
                         'unselected_hook_denied', 'host_globals_hidden',
                         'descendant_read_denied', 'descendant_pid_namespace'} <= failed, failed)

    def test_missing_bubblewrap_is_not_certification(self):
        with mock.patch.object(isolation, 'linux_executable', return_value=None):
            result = isolation.probe_linux_boundary()
        self.assertFalse(result['filesystem_enforced'])
        self.assertIn('bubblewrap', result['error'])

    def test_namespace_failure_is_not_certification(self):
        failure = subprocess.CompletedProcess([], 1, '', 'bwrap: setting up uid map: Permission denied\n')
        with mock.patch.object(isolation, 'linux_executable', return_value='/usr/bin/bwrap'), \
             mock.patch.object(isolation.subprocess, 'run', return_value=failure):
            result = isolation.probe_linux_boundary()
        self.assertFalse(result['filesystem_enforced'])
        self.assertIn('uid map', result['error'])

    def test_forged_all_true_output_without_hook_side_effect_fails(self):
        forged = json.dumps({name: True for name in isolation.LINUX_CHECKS})
        with mock.patch.object(isolation, 'linux_executable', return_value='/usr/bin/bwrap'), \
             mock.patch.object(isolation.subprocess, 'run',
                               return_value=subprocess.CompletedProcess([], 0, forged, '')):
            result = isolation.probe_linux_boundary()
        self.assertFalse(result['filesystem_enforced'])

    def test_dispatch_never_uses_the_other_platform_mechanism(self):
        with mock.patch.object(isolation.sys, 'platform', 'linux'), \
             mock.patch.object(isolation, 'probe_linux_boundary', return_value={'m': 'linux'}):
            self.assertEqual(isolation.probe_host_boundary(), {'m': 'linux'})
        with mock.patch.object(isolation.sys, 'platform', 'darwin'), \
             mock.patch.object(isolation, 'probe_filesystem_boundary', return_value={'m': 'mac'}):
            self.assertEqual(isolation.probe_host_boundary(), {'m': 'mac'})

    def test_argv_binds_fixture_writable_and_auth_exact_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            (root / 'home' / '.codex').mkdir(parents=True)
            auth = root / 'home' / '.codex' / 'auth.json'
            auth.write_text('{}')
            (root / 'fixture').mkdir()
            argv = isolation.linux_argv('/usr/bin/bwrap', root / 'fixture', read_files=[auth],
                                        command=['/bin/true'])
            writable = [argv[i + 1] for i, a in enumerate(argv) if a == '--bind']
            self.assertEqual(writable, [str(root / 'fixture')])
            self.assertIn(str(auth), argv)
            self.assertNotIn(str(root / 'home'), argv)
            self.assertNotIn(str(root / 'home' / '.codex'), argv)
            for flag in ('--unshare-pid', '--unshare-user', '--die-with-parent',
                         '--new-session', '--remount-ro'):
                self.assertIn(flag, argv)
            self.assertEqual(argv[-2:], ['--', '/bin/true'])
            with self.assertRaises(FileNotFoundError):
                isolation.linux_argv('/usr/bin/bwrap', root / 'fixture', read_files=[root / 'missing'])


class IsolationReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name).resolve()
        self.repo = _git_repo(root / 'repo')
        self.fixture = _git_repo(root / 'fixture')
        self.key = b'test-host-key'
        self.evidence = {'mechanism': 'bubblewrap', 'probe_sha256': 'p', 'filesystem_enforced': True,
                         'host_identity': {'system': 'Linux'}}

    def sign(self, **overrides):
        args = dict(key=self.key, host='codex', model='model-fixture-1', argv=['codex', 'exec'],
                    exit_status=0, repository=isolation.repository_revision(self.repo),
                    fixture=isolation.fixture_binding(self.fixture), isolation=self.evidence,
                    issued_at=1.0)
        args.update(overrides)
        return isolation.sign_command_receipt(**args)

    def verify(self, record, **overrides):
        args = dict(repository_revision=isolation.repository_revision(self.repo)['revision'],
                    fixture_sha256=isolation.fixture_binding(self.fixture)['tree_sha256'],
                    host='codex', model='model-fixture-1')
        args.update(overrides)
        return isolation.verify_command_receipt(record, self.key, **args)

    def test_receipt_binds_revision_fixture_host_and_model(self):
        record = self.verify(self.sign())
        self.assertEqual(len(record['repository_revision']), 40)
        self.assertEqual(record['fixture_git_head'], isolation.fixture_binding(self.fixture)['git_head'])
        self.assertEqual(record['host_identity'], {'system': 'Linux'})
        self.assertFalse(record['host_certified'])

    def test_tampered_or_rebound_receipts_are_rejected(self):
        record = self.sign()
        for field, value in (('exit_status', 1), ('model', 'other'), ('host_certified', True),
                             ('fixture_sha256', '0' * 64)):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'signature'):
                self.verify(dict(record, **{field: value}))
        with self.assertRaisesRegex(ValueError, 'signature'):
            isolation.verify_command_receipt(record, b'other-key', repository_revision=record['repository_revision'],
                                             fixture_sha256=record['fixture_sha256'], host='codex',
                                             model='model-fixture-1')
        with self.assertRaisesRegex(ValueError, 'repository'):
            self.verify(record, repository_revision='f' * 40)
        with self.assertRaisesRegex(ValueError, 'identity'):
            self.verify(record, model='other')
        (self.fixture / 'file').write_text('changed by trial')
        with self.assertRaisesRegex(ValueError, 'fixture'):
            self.verify(record)

    def test_dirty_repository_cannot_produce_a_valid_receipt(self):
        (self.repo / 'file').write_text('uncommitted')
        record = self.sign()
        self.assertTrue(record['repository_dirty'])
        with self.assertRaisesRegex(ValueError, 'clean repository'):
            self.verify(record)

    def test_fixture_digest_ignores_git_metadata_but_not_content(self):
        before = isolation.fixture_binding(self.fixture)['tree_sha256']
        (self.fixture / '.git' / 'extra').write_text('x')
        self.assertEqual(isolation.fixture_binding(self.fixture)['tree_sha256'], before)
        (self.fixture / 'new').write_text('x')
        self.assertNotEqual(isolation.fixture_binding(self.fixture)['tree_sha256'], before)

    def test_signing_key_comes_only_from_agentic_host_key(self):
        with self.assertRaisesRegex(RuntimeError, 'AGENTIC_HOST_KEY'):
            isolation.host_key({})
        self.assertEqual(isolation.host_key({'AGENTIC_HOST_KEY': 'k'}), b'k')
        with self.assertRaises(ValueError):
            self.sign(key=b'')


if __name__ == '__main__':
    unittest.main()
