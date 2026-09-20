"""Offline macOS filesystem containment experiment, not host certification.

The canary never executes a model, reads credentials, or changes user settings.
A passing result establishes only the stated kernel file restrictions. Production
host startup/authentication and retained hook execution require separate evidence.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def executable() -> str | None:
    path = Path('/usr/bin/sandbox-exec')
    return str(path) if sys.platform == 'darwin' and path.is_file() else None


def filesystem_profile(fixture: Path, runtime_roots: list[Path],
                       read_files: list[Path] = ()) -> str:
    """Allow fixture writes, exact auth-file reads, runtime reads, and networking.

    No home directory permission is implied by an exact auth-file exception.
    This is an experimental outer boundary; it does not replace host tool policy.
    """
    fixture = fixture.resolve()
    reads = sorted({str(fixture), *(str(p.resolve()) for p in runtime_roots)})
    literals = sorted({str(p.resolve()) for p in read_files})
    return ('(version 1)(deny default)'
            '(allow process-exec process-fork signal sysctl-read mach-lookup network*)'
            '(allow file-read-metadata)'
            '(allow file-read* (literal "/") (literal "/dev/null")'
            ' (literal "/dev/urandom") ' +
            ' '.join('(subpath ' + json.dumps(p) + ')' for p in reads) + ' ' +
            ' '.join('(literal ' + json.dumps(p) + ')' for p in literals) + ')'
            '(allow file-write* (subpath ' + json.dumps(str(fixture)) + ')'
            ' (literal "/dev/null"))')


_PROGRAM = r'''
import json, pathlib, socket, subprocess, sys
root = pathlib.Path(sys.argv[1])
fixture = root / 'fixture'
checks = {}
checks['fixture_read'] = (fixture / 'input').read_text() == 'allowed'
(fixture / 'output').write_text('written')
checks['fixture_write'] = (fixture / 'output').read_text() == 'written'
checks['auth_exact_read'] = (root / 'auth' / 'auth.json').read_text() == 'synthetic auth'
checks['plugin_read'] = (root / 'plugin' / 'SKILL.md').read_text() == 'synthetic plugin'
for name in ('snapshot', 'evidence', 'global-instructions', 'other-auth', 'fixture/escape'):
    path = root / name
    for mode in ('r', 'w'):
        try:
            with path.open(mode):
                pass
        except PermissionError:
            checks[name + ':' + mode] = True
        else:
            checks[name + ':' + mode] = False
# Network availability is tested locally, without contacting any service.
with socket.socket() as server, socket.socket() as client:
    server.bind(('127.0.0.1', 0)); server.listen(1)
    client.connect(server.getsockname())
    conn, _ = server.accept()
    with conn:
        client.sendall(b'ok')
        checks['loopback_network'] = conn.recv(2) == b'ok'
child = subprocess.run([sys.executable, '-I', '-B', '-c',
    "import pathlib,sys; pathlib.Path(sys.argv[1]).read_text()", str(root / 'snapshot')],
    capture_output=True, text=True)
checks['descendant_read_denied'] = child.returncode != 0 and 'PermissionError' in child.stderr
print(json.dumps(checks, sort_keys=True))
'''


def probe_filesystem_boundary(timeout_seconds: float = 3) -> dict:
    """Retain bounded, secret-free canary evidence; fail closed on any mismatch."""
    sandbox = executable()
    result = {'schema_version': 1, 'filesystem_enforced': False,
              'host_certified': False, 'checks': {}, 'error': None,
              'probe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if sandbox is None:
        result['error'] = 'macOS /usr/bin/sandbox-exec is unavailable'
        return result
    with tempfile.TemporaryDirectory(prefix='host-isolation-') as temp:
        root = Path(temp).resolve()
        fixture = root / 'fixture'
        fixture.mkdir()
        (fixture / 'input').write_text('allowed')
        for name in ('snapshot', 'evidence', 'global-instructions', 'other-auth'):
            (root / name).write_text('protected')
        (root / 'auth').mkdir()
        (root / 'auth' / 'auth.json').write_text('synthetic auth')
        (root / 'plugin').mkdir()
        (root / 'plugin' / 'SKILL.md').write_text('synthetic plugin')
        (fixture / 'escape').symlink_to(root / 'snapshot')
        runtime = [Path(sys.prefix), Path(sys.base_prefix),
                   Path(sys.executable).resolve().parent, Path('/System/Library'),
                   Path('/usr/lib'), Path('/Library/Apple/System/Library'), root / 'plugin']
        profile = filesystem_profile(fixture, runtime, [root / 'auth' / 'auth.json'])
        try:
            process = subprocess.run([sandbox, '-p', profile, sys.executable, '-I', '-B',
                                      '-c', _PROGRAM, str(root)], capture_output=True,
                                     text=True, timeout=timeout_seconds,
                                     env={'PATH': '/usr/bin:/bin'}, cwd=fixture)
            if process.returncode:
                result['error'] = 'Offline sandbox canary failed with exit ' + str(process.returncode)
                return result
            checks = json.loads(process.stdout)
            expected = {'fixture_read', 'fixture_write', 'auth_exact_read', 'plugin_read',
                        'loopback_network', 'descendant_read_denied'} | {
                name + ':' + mode for name in ('snapshot', 'evidence', 'global-instructions',
                                               'other-auth', 'fixture/escape') for mode in ('r', 'w')}
            result['checks'] = checks
            result['filesystem_enforced'] = (isinstance(checks, dict) and set(checks) == expected
                                             and all(value is True for value in checks.values())
                                             and all((root / name).read_text() == 'protected'
                                                     for name in ('snapshot', 'evidence',
                                                                  'global-instructions', 'other-auth')))
            if not result['filesystem_enforced']:
                result['error'] = 'Offline sandbox canary evidence did not match every required control'
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            result['error'] = 'Offline sandbox canary failed: ' + type(exc).__name__
    return result
