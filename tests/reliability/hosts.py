"""Bounded, session-local host execution for the opt-in reliability harness.

Profiles freeze an explicit model, settings, permissions, executable hash and CLI
capabilities. Authentication storage is left untouched. CLI isolation flags do
not prove isolation of global skills, instructions or managed policy; unsupported
channels fail closed before model execution. POSIX process groups contain
ordinary descendants, not independently daemonized processes.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time


def _isolation_evidence(timeout_seconds: float = 3) -> dict:
    # Load the sibling explicitly: the harness is also imported by file path.
    path = Path(__file__).with_name("isolation.py")
    spec = importlib.util.spec_from_file_location("reliability_host_isolation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.probe_filesystem_boundary(timeout_seconds=timeout_seconds)


def _validate_host(host: str) -> None:
    if host not in ("claude", "codex"):
        raise ValueError(f"Unsupported host: {host!r}")


def _fixture_path(fixture: Path) -> Path:
    fixture = Path(fixture).resolve()
    if not fixture.is_dir():
        raise FileNotFoundError(f"Fixture directory does not exist: {fixture}")
    return fixture


def _cleanup(process: subprocess.Popen) -> None:
    """Kill the group even when its parent already exited after SIGTERM."""
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        time.sleep(0.1)
        # Reap a dead leader before signaling again: macOS can report EPERM
        # for a process group containing only its unreaped zombie leader.
        process.poll()
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        process.kill()
    process.wait(timeout=5)


def _probe(argv: list[str], cwd: Path | None = None,
           timeout_seconds: float = 10) -> subprocess.CompletedProcess:
    """Read-only CLI probe; inherited auth/config is never modified."""
    with subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, start_new_session=os.name == "posix") as process:
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
            return subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)
        finally:
            _cleanup(process)


def _isolation_limits(host: str) -> list[str]:
    """Name the remaining evidence needed; no environment waiver is accepted."""
    common = ("Offline filesystem controls do not certify actual host startup: require "
              "a no-inference startup probe proving existing authentication, denied global "
              "instructions/skills/plugins and managed policy inputs, plus retained project "
              "and selected-plugin hook execution under the same outer sandbox")
    if host == "claude":
        return [common + "; installed --bare changes auth and skips hooks, while "
                "--safe-mode disables the hooks/plugins under evaluation"]
    return [common + "; installed exec --help/--version do not exercise authentication "
            "or hook discovery; --ignore-user-config retains CODEX_HOME auth but does "
            "not itself establish exclusion of other CODEX_HOME inputs"]


def _profile(host: str, executable: str, help_text: str,
             timeout_seconds: float = 3) -> dict:
    model = os.environ.get(f"RELIABILITY_{host.upper()}_MODEL", "")
    required = (["--setting-sources", "--settings", "--model", "--effort",
                 "--permission-mode", "--strict-mcp-config", "--plugin-dir"]
                if host == "claude" else
                ["--ignore-user-config", "--ignore-rules", "--model", "--sandbox",
                 "--config", "--ephemeral"])
    limits = _isolation_limits(host)
    isolation_evidence = _isolation_evidence(timeout_seconds)
    if not isolation_evidence["filesystem_enforced"]:
        limits.append(isolation_evidence["error"] or "Filesystem containment canary failed")
    if not model or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", model):
        limits.append(f"RELIABILITY_{host.upper()}_MODEL must name an explicit model ID")
    elif model in {"opus", "sonnet", "haiku", "fable", "default", "latest"}:
        limits.append("Model aliases are not frozen model identities")
    missing = [flag for flag in required if flag not in help_text]
    if missing:
        limits.append("Missing required CLI flags: " + ", ".join(missing))
    return {
        "schema_version": 1, "model": model or None,
        "executable_sha256": hashlib.sha256(Path(executable).read_bytes()).hexdigest(),
        "help_sha256": hashlib.sha256(help_text.encode()).hexdigest(),
        "effort": "medium" if host == "claude" else "high",
        "permissions": "dontAsk" if host == "claude" else "workspace-write",
        "settings": ({"setting_sources": "project,local", "settings": {
            "permissions": {"allow": ["Read", "Edit", "Write", "Bash"]}}}
            if host == "claude" else {"ignore_user_config": True, "ignore_rules": True,
                                     "approval_policy": "never"}),
        "isolation_supported": not limits, "unsupported_channels": limits,
        "isolation_evidence": isolation_evidence,
    }


def inspect_host(host: str, timeout_seconds: float = 10) -> dict:
    """Read-only capability/profile probe; never authenticates or runs a task."""
    _validate_host(host)
    executable = shutil.which(host)
    result = {"host": host, "executable": executable, "version": None,
              "available": False, "error": None, "profile": None, "timed_out": False}
    if executable is None:
        result["error"] = f"{host} executable is unavailable"
        return result
    started = time.monotonic()
    try:
        probe = _probe([executable, "--version"], timeout_seconds=timeout_seconds)
        if probe.returncode:
            raise RuntimeError(f"{host} version probe exited {probe.returncode}")
        remaining = timeout_seconds - (time.monotonic() - started)
        if remaining <= 0:
            raise subprocess.TimeoutExpired([executable, "--help"], timeout_seconds)
        help_probe = _probe([executable] + (["exec"] if host == "codex" else []) +
                            ["--help"], timeout_seconds=remaining)
        if help_probe.returncode:
            raise RuntimeError(f"{host} help probe exited {help_probe.returncode}")
        remaining = timeout_seconds - (time.monotonic() - started)
        if remaining <= 0:
            raise subprocess.TimeoutExpired([executable, "isolation-canary"], timeout_seconds)
        result.update(available=True, version=probe.stdout.strip() or None,
                      profile=_profile(host, executable, help_probe.stdout, min(3, remaining)))
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        result["error"] = f"{host} profile probe failed ({type(exc).__name__})"
        result["timed_out"] = isinstance(exc, subprocess.TimeoutExpired)
    return result


def build_command(host: str, fixture: Path, prompt: str,
                  plugin_roots: list[Path], trace_dir: Path) -> list[str]:
    """Build only commands whose explicit host profile passes isolation checks."""
    return _build_command(host, fixture, prompt, plugin_roots, probe_timeout=10)


def _build_command(host: str, fixture: Path, prompt: str,
                   plugin_roots: list[Path], probe_timeout: float,
                   expected_profile: dict | None = None) -> list[str]:
    _validate_host(host)
    fixture = _fixture_path(fixture)
    inspection = inspect_host(host, timeout_seconds=probe_timeout)
    if inspection["timed_out"]:
        raise subprocess.TimeoutExpired([host, "--help"], probe_timeout)
    if not inspection["available"]:
        raise RuntimeError(inspection["error"])
    profile = inspection["profile"]
    if expected_profile is not None and profile != expected_profile:
        raise RuntimeError("Frozen host profile drifted before launch")
    if not profile["isolation_supported"]:
        raise RuntimeError("Host isolation unavailable: " + "; ".join(profile["unsupported_channels"]))
    executable = inspection["executable"]
    roots = [Path(root).resolve() for root in plugin_roots]
    for root in roots:
        if not root.is_dir():
            raise FileNotFoundError(f"Plugin directory does not exist: {root}")
    if host == "claude":
        argv = [executable, "--print", "--verbose", "--output-format", "stream-json",
                "--no-session-persistence", "--strict-mcp-config", "--mcp-config",
                '{"mcpServers":{}}', "--setting-sources", profile["settings"]["setting_sources"],
                "--settings", json.dumps(profile["settings"]["settings"], sort_keys=True),
                "--model", profile["model"], "--effort", profile["effort"],
                "--permission-mode", profile["permissions"]]
        for root in roots:
            argv.extend(["--plugin-dir", str(root)])
        return argv + ["--", prompt]
    argv = [executable, "exec", "--json", "--ephemeral", "--color", "never",
            "--ignore-user-config", "--ignore-rules", "--model", profile["model"],
            "--config", 'model_reasoning_effort="high"',
            "--config", 'approval_policy="never"',
            "--sandbox", profile["permissions"], "--cd", str(fixture)]
    if roots:
        prompt += ("\n\nUse the local plugin source directories below for this task. "
                   "Read the relevant SKILL.md and referenced files directly.\n" +
                   "\n".join(f"- {root}" for root in roots))
    return argv + ["--", prompt]


_INFRA_ERROR = re.compile(
    r"not logged in|not authenticated|authentication (?:failed|required|error)|"
    r"invalid (?:api[ _-]?key|authentication|credentials)|"
    r"(?:api[ _-]?key|auth(?:entication)? token|access token).*(?:missing|expired|invalid)|"
    r"(?:missing|expired|invalid).*(?:api[ _-]?key|auth(?:entication)? token|access token)|"
    r"unauthorized|error (?:loading|parsing) (?:config|settings)|"
    r"(?:invalid|failed to (?:load|parse)) (?:configuration|config\.toml)|"
    r"unexpected argument|unrecognized (?:option|argument)|unknown option",
    re.IGNORECASE,
)


def _trace_metadata(stdout_path: Path) -> dict:
    metadata = {"observed_model": None, "usage": None, "failed": False,
                "infrastructure_failed": False}
    with stdout_path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            kind = event.get("type")
            # Read host metadata, never model-looking strings inside tool output.
            if kind in ("system", "session.started", "thread.started", "result", "turn.completed"):
                if isinstance(event.get("model"), str):
                    metadata["observed_model"] = event["model"]
            if kind in ("result", "turn.completed") and isinstance(event.get("usage"), dict):
                metadata["usage"] = event["usage"]
            if kind == "assistant" and isinstance(event.get("message"), dict):
                if isinstance(event["message"].get("model"), str):
                    metadata["observed_model"] = event["message"]["model"]
            failed = (kind in ("turn.failed", "error") or
                      (kind == "result" and event.get("is_error") is True))
            if failed:
                metadata["failed"] = True
                error = event.get("error", event.get("errors", event.get("result", "")))
                if _INFRA_ERROR.search(json.dumps(error)):
                    metadata["infrastructure_failed"] = True
    return metadata


def run_host(host: str, fixture: Path, prompt: str, plugin_roots: list[Path],
             trace_dir: Path, timeout_seconds: float = 900,
             checkpoint_path: Path | None = None,
             expected_profile: dict | None = None) -> dict:
    """Run one host, retaining private raw traces and normalized outcome metadata."""
    _validate_host(host)
    fixture = _fixture_path(fixture)
    if checkpoint_path is not None:
        checkpoint_path = Path(checkpoint_path)
        if not checkpoint_path.is_absolute():
            checkpoint_path = fixture / checkpoint_path
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive and finite")
    if os.name != "posix":
        raise RuntimeError("Host runs require POSIX process-group cleanup")
    trace_dir = Path(trace_dir).resolve()
    trace_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    trace_dir.chmod(0o700)
    stdout_fd, stdout_name = tempfile.mkstemp(prefix=f"{host}-", suffix=".jsonl", dir=trace_dir)
    stderr_fd, stderr_name = tempfile.mkstemp(prefix=f"{host}-", suffix=".stderr", dir=trace_dir)
    result = {"host": host, "status": "infrastructure_failed", "exit_code": None,
              "elapsed_seconds": 0.0, "argv": [], "raw_stdout_path": stdout_name,
              "raw_stderr_path": stderr_name, "observed_model": None, "usage": None,
              "error": None, "checkpoint_observed": False}
    started = time.monotonic()
    process = None
    with os.fdopen(stdout_fd, "wb") as stdout, os.fdopen(stderr_fd, "wb") as stderr:
        try:
            result["argv"] = _build_command(host, fixture, prompt, plugin_roots,
                                             probe_timeout=min(10, timeout_seconds),
                                             expected_profile=expected_profile)
            remaining = timeout_seconds - (time.monotonic() - started)
            if remaining <= 0:
                result["status"] = "timed_out"
            else:
                process = subprocess.Popen(result["argv"], cwd=fixture,
                                           stdin=subprocess.DEVNULL, stdout=stdout,
                                           stderr=stderr, start_new_session=True)
                while True:
                    if checkpoint_path is not None and checkpoint_path.is_file():
                        result.update(status="interrupted", checkpoint_observed=True)
                        break
                    if process.poll() is not None:
                        result["exit_code"] = process.returncode
                        result["status"] = "completed" if process.returncode == 0 else "product_failed"
                        break
                    remaining = timeout_seconds - (time.monotonic() - started)
                    if remaining <= 0:
                        result["status"] = "timed_out"
                        break
                    time.sleep(min(0.05, remaining))
        except subprocess.TimeoutExpired:
            result["status"] = ("timed_out" if time.monotonic() - started >= timeout_seconds
                                else "infrastructure_failed")
            result["error"] = "Host configuration probe timed out"
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            result["error"] = f"Host setup or execution failed: {exc}"
            stderr.write((result["error"] + "\n").encode("utf-8", errors="replace"))
        finally:
            if process is not None:
                _cleanup(process)
                result["exit_code"] = process.returncode
    metadata = _trace_metadata(Path(stdout_name))
    result.update(observed_model=metadata["observed_model"], usage=metadata["usage"])
    if result["status"] in ("completed", "product_failed"):
        if metadata["failed"]:
            result["status"] = "product_failed"
        with Path(stderr_name).open(encoding="utf-8", errors="replace") as stream:
            infra_stderr = any(_INFRA_ERROR.search(line) for line in stream)
        if metadata["infrastructure_failed"] or (result["exit_code"] != 0 and infra_stderr):
            result["status"] = "infrastructure_failed"
    result["elapsed_seconds"] = round(time.monotonic() - started, 6)
    return result
