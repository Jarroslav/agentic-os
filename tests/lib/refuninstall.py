#!/usr/bin/env python3
"""Reference executor of agentic-uninstall (deterministic convergence only).

The acceptance harness's stand-in for a human/agent following
plugins/agentic-os/skills/agentic-uninstall/SKILL.md by hand. Like refinstall.py
for init, this is the executable proof that the spec is followable: if a step
here cannot be derived from the SKILL.md, that is a harness finding.

HOW DESIRED STATE IS COMPUTED. The spec defines uninstall as "recompute what an
install of the remaining presets would produce, then converge to it". This
executor takes that literally: it runs refinstall.py into a scratch directory
for the remaining union and uses the result as the desired state. That is a
harness shortcut, not a claim about a real implementation, and it is sound for
what T9 asserts -- rendering correctness is already covered by T1-T8, whereas
every failure mode unique to *removal* (files not deleted, journal entries left
behind, settings still wired to a deleted script, the repo's own git hook not
restored, a user-edited file destroyed) still shows up as a tree difference
against an independently built install of the remaining roles.

What this executor deliberately does NOT model:
  * Phase 5 generation (refinstall skips it too), so gen/* slots never appear.
  * The interactive triples. --assume-keep / --assume-delete stand in for the
    human, mirroring refinstall.py's COLLISION-skip convention.
  * The HITL re-ask. The journaled HITL_MODE answer is carried through
    unchanged, which is the "keep the journaled answer" branch of the spec.

Usage: refuninstall.py <PLUGIN_ROOT> <TARGET_REPO> --remove qa[,devops]
                       [--all] [--assume-keep|--assume-delete] [--dry-run]
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import subprocess as sp
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def die(msg: str) -> None:
    print("  FAIL refuninstall: %s" % msg)
    sys.exit(1)


def option(argv: list[str], name: str, default: str | None = None) -> str | None:
    for i, a in enumerate(argv):
        if a == name and i + 1 < len(argv):
            return argv[i + 1]
    return default


def main() -> None:
    argv = sys.argv[1:]
    if len(argv) < 2:
        die("usage: refuninstall.py <PLUGIN> <TARGET> --remove a[,b] | --all")
    plugin, target = Path(argv[0]).resolve(), Path(argv[1]).resolve()
    rest = argv[2:]
    remove_all = "--all" in rest
    dry_run = "--dry-run" in rest
    # Default keep, matching the spec's B5/B6 default and refinstall's skip default.
    assume_delete = "--assume-delete" in rest
    removed = [r for r in (option(rest, "--remove", "") or "").split(",") if r]

    jpath = target / ".agentic/agentic-os/install.json"
    if not jpath.is_file():
        die("not installed — no %s" % jpath.relative_to(target))
    journal = json.loads(jpath.read_text())
    answers = journal.get("answers", {})
    p_old = list(answers.get("presets") or ([answers["preset"]] if answers.get("preset") else []))
    if not p_old:
        die("journal records no presets")

    unknown = [r for r in removed if r not in p_old]
    if unknown:
        die("not installed: %s (installed: %s)" % (",".join(unknown), ",".join(p_old)))

    p_new = [] if remove_all else [p for p in p_old if p not in removed]
    if not p_new and not remove_all:
        die("removing %s would empty the preset list — that is the whole-layer "
            "case, pass --all explicitly" % ",".join(removed))
    if journal.get("adoption", {}).get("mode") == "adopt-existing":
        print("  ok   refuninstall: adopt-existing mode — reporting only, nothing deleted")
        return

    # ---- desired state: what an install of the remaining union would produce ----
    desired_files: dict[str, Path] = {}
    scratch = Path(tempfile.mkdtemp(prefix="refuninstall-desired-"))
    try:
        if p_new:
            # The reference install must run in THIS repo, not an empty one: the
            # installer's stack discovery reads marker files, so a bare scratch
            # repo would render different stack-derived content and the diff
            # would be noise. Copy the target, strip everything agentic-os
            # wrote, and install the remaining union into that.
            # Same basename as the target: the installer derives the project
            # name from the directory, so a differently-named scratch dir would
            # render a different heading in every governance file.
            ref = scratch / target.name
            shutil.copytree(target, ref, symlinks=True)
            strip_agentic(ref, journal)
            cmd = [sys.executable, str(HERE / "refinstall.py"), str(plugin), str(ref),
                   "--presets", ",".join(p_new)]
            mcp_state = answers.get("mcp_state")
            if mcp_state:
                cmd += ["--mcp-state", mcp_state]
            r = sp.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                die("reference install for %s failed: %s" % (",".join(p_new), r.stderr.strip()))
            ref_journal = json.loads((ref / ".agentic/agentic-os/install.json").read_text())
            for rel in ref_journal["files"]:
                if (ref / rel).is_file():
                    desired_files[rel] = ref / rel

        plan = converge(target, journal, desired_files, p_new, assume_delete, dry_run)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    for line in plan:
        print("  " + line)


def strip_agentic(root: Path, journal: dict) -> None:
    """Return a copied tree to its pre-install state, as far as the journal knows.

    Everything agentic-os wrote goes, so the reference install starts from the
    repo's own content and rediscovers the same stack. Files it merely adopted
    (owner user / origin adopted-existing) stay — a fresh install would find
    them there too.
    """
    for rel, entry in journal.get("files", {}).items():
        if entry.get("owner") == "user" or entry.get("origin") == "adopted-existing":
            continue
        p = root / rel
        if p.is_file():
            p.unlink()
    shutil.rmtree(root / ".agentic", ignore_errors=True)
    sc = root / "docs/audits/instruction-scorecard.json"
    if sc.is_file():
        sc.unlink()
    # Put the git-hook chain back the way the repo had it, so the reference
    # install performs the same displacement the real one did.
    hooks = root / ".git" / "hooks"
    live, local = hooks / "pre-commit", hooks / "pre-commit.local"
    if live.is_file() and "agentic-os:" in live.read_text(errors="replace"):
        live.unlink()
    if local.is_file() and not live.is_file():
        local.rename(live)
        live.chmod(0o755)


def converge(target: Path, journal: dict, desired: dict[str, Path], p_new: list[str],
             assume_delete: bool, dry_run: bool) -> list[str]:
    """Classify every journaled file, then converge. Returns report lines."""
    report: list[str] = []
    files = journal["files"]
    removed_rel: list[str] = []
    rerendered: list[str] = []
    kept_by_choice: list[str] = []
    never_touch: list[str] = []

    # Which hook scripts will exist afterwards — drives the settings subtraction.
    scripts_after = {rel for rel in desired if rel.startswith(".claude/hooks/") and rel.endswith(".py")}

    for rel in sorted(files):
        entry = files[rel]
        live = target / rel
        # B0 — never touch.
        if entry.get("owner") == "user" or entry.get("origin") == "adopted-existing":
            never_touch.append(rel)
            continue
        # B7 hybrid: settings is subtracted below, never treated as B4/B5 —
        # except under --all, where the union is empty and the whole file goes
        # (leaving an un-wired husk behind would make a later install merge into
        # residue instead of starting clean).
        if rel == ".claude/settings.json":
            if not desired:
                if not dry_run:
                    if live.is_file():
                        live.unlink()
                    files.pop(rel, None)
                removed_rel.append(rel)
            continue
        if rel in desired:
            # Retained. Re-render when the desired content differs.
            if not live.is_file():
                continue
            want = desired[rel].read_bytes()
            if live.read_bytes() == want:
                continue
            if sha(live) != entry.get("sha256"):
                # B3 — retained but locally modified.
                if not assume_delete:
                    kept_by_choice.append("%s (retained, local edits kept)" % rel)
                    entry["owner"] = "user"
                    continue
            if not dry_run:
                live.write_bytes(want)
                entry["sha256"] = hashlib.sha256(want).hexdigest()
            rerendered.append(rel)
        else:
            # Removed from the union.
            dirty = live.is_file() and sha(live) != entry.get("sha256")
            if entry.get("owner") == "generated" or dirty:
                # B5 / B6 — default keep.
                if not assume_delete:
                    kept_by_choice.append("%s (%s, kept)" %
                                          (rel, "generated" if entry.get("owner") == "generated"
                                           else "locally modified"))
                    entry["owner"] = "user"
                    continue
            if not dry_run:
                if live.is_file():
                    live.unlink()
                files.pop(rel, None)
            removed_rel.append(rel)

    settings_dropped = subtract_settings(target, journal, scripts_after, dry_run)
    hook_notes = converge_git_hooks(target, desired, dry_run)

    if not dry_run:
        if not p_new:
            # --all: the journal is deleted LAST, so a crash anywhere above
            # still leaves a readable record of what was installed. Nothing is
            # written back — a rewritten journal would resurrect the very
            # directory the run just emptied.
            sc = target / "docs/audits/instruction-scorecard.json"
            if sc.is_file():
                sc.unlink()          # the whole manifest goes with the layer
            shutil.rmtree(target / ".agentic/agentic-os", ignore_errors=True)
            for d in (".agentic", ".claude", "docs/audits"):
                prune_empty_dirs(target / d)
        else:
            prune_scorecard(target, journal, removed_rel)
            journal.setdefault("answers", {})["presets"] = p_new
            journal["answers"]["ROLE_PRESETS_ACTIVE"] = ",".join(p_new)
            (target / ".agentic/agentic-os/install.json").write_text(
                json.dumps(journal, indent=2) + "\n")

    report.append("ok   refuninstall: %d removed, %d re-rendered, %d kept by choice, "
                  "%d never-touch, %d settings entries un-wired"
                  % (len(removed_rel), len(rerendered), len(kept_by_choice),
                     len(never_touch), settings_dropped))
    for n in hook_notes:
        report.append("ok   " + n)
    if dry_run:
        report.append("ok   --dry-run: nothing written")
    return report


def prune_empty_dirs(root: Path) -> None:
    """Remove directories the removal emptied, deepest first.

    A fresh install creates these on demand, so leaving empty husks behind
    would diverge from a never-installed repo — visible in `git status` as
    stray untracked directories.
    """
    if not root.is_dir():
        return
    for p in sorted(root.rglob("*"), key=lambda q: len(q.parts), reverse=True):
        if p.is_dir() and not any(p.iterdir()):
            p.rmdir()
    if not any(root.iterdir()):
        root.rmdir()


def subtract_settings(target: Path, journal: dict, scripts_after: set[str],
                      dry_run: bool) -> int:
    """Drop hook wirings whose script will not exist afterwards.

    Ordered before script deletion by the caller's contract: a crash here leaves
    'wired nothing' (harmless), never 'wired but missing' (which doctor Check 5
    reports as exit 2 on every event, blocking all tool use).
    """
    sp_path = target / ".claude/settings.json"
    if not sp_path.is_file():
        return 0
    settings = json.loads(sp_path.read_text())
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return 0
    dropped = 0
    for event in list(hooks):
        groups = hooks[event]
        if not isinstance(groups, list):
            continue
        kept_groups = []
        for group in groups:
            entries = group.get("hooks", []) if isinstance(group, dict) else []
            kept = []
            for h in entries:
                cmd = h.get("command", "") if isinstance(h, dict) else ""
                script = None
                for token in cmd.split():
                    if token.startswith(".claude/hooks/") and token.endswith(".py"):
                        script = token
                        break
                if script and script not in scripts_after:
                    dropped += 1
                    continue
                kept.append(h)
            # Empty groups and empty event keys are KEPT. A fresh install leaves
            # them: the installer's prune reaches each matcher group through its
            # "matcher" branch, which filters the group's hooks in place and
            # returns, so the group shape survives even when it ends up empty.
            # Collapsing them here would produce a settings file no install can
            # produce — which is exactly what the round-trip caught.
            group["hooks"] = kept
            kept_groups.append(group)
        hooks[event] = kept_groups
    if dropped and not dry_run:
        sp_path.write_text(json.dumps(settings, indent=2) + "\n")
        journal["files"][".claude/settings.json"]["sha256"] = sha(sp_path)
    return dropped


def converge_git_hooks(target: Path, desired: dict, dry_run: bool) -> list[str]:
    """Remove our hook and restore the repo's own, when the git layer leaves."""
    if ".githooks/pre-commit" in desired:
        return []
    try:
        hooks_dir = Path(subprocess.run(
            ["git", "-C", str(target), "rev-parse", "--git-path", "hooks"],
            capture_output=True, text=True, check=True).stdout.strip())
    except subprocess.CalledProcessError:
        return []
    if not hooks_dir.is_absolute():
        hooks_dir = target / hooks_dir
    live, local = hooks_dir / "pre-commit", hooks_dir / "pre-commit.local"
    notes: list[str] = []
    if live.is_file():
        if "agentic-os:" in live.read_text(errors="replace"):
            if not dry_run:
                live.unlink()
            notes.append("git hook: removed our .git/hooks/pre-commit")
        else:
            return ["git hook: .git/hooks/pre-commit is not ours — left in place"]
    if local.is_file():
        if live.is_file():
            return notes + ["git hook: both pre-commit and pre-commit.local present — "
                            "stopped, restore by hand"]
        if not dry_run:
            local.rename(live)
            live.chmod(0o755)
        notes.append("git hook: restored the repo's own pre-commit from .local")
    return notes


def prune_scorecard(target: Path, journal: dict, removed_rel: list[str]) -> None:
    sc = target / "docs/audits/instruction-scorecard.json"
    if not sc.is_file():
        return
    doc = json.loads(sc.read_text())
    entries = doc.get("files", {})
    for rel in removed_rel:
        entries.pop(rel, None)
    for rel in list(entries):
        p = target / rel
        if not p.is_file():
            entries.pop(rel, None)
            continue
        if rel in journal["files"]:
            entries[rel]["content_sha256"] = sha(p)
    sc.write_text(json.dumps(doc, indent=2) + "\n")


if __name__ == "__main__":
    main()
