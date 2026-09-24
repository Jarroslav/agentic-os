import json
import hashlib
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from runtime.agentic_runtime import installer
from runtime.agentic_runtime.installer import apply_install, merge_settings_file, plan_install, remove_install


ROOT = pathlib.Path(__file__).resolve().parents[2]


class InstallerTests(unittest.TestCase):
    def test_plan_is_read_only_and_apply_creates_journal(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            files = {".agentic/config.json": {"content": '{"mode":"hitl"}\n',
                                                "template": "config", "owner": "managed"}}
            plan = plan_install(target, files)
            self.assertEqual(plan["actions"][0]["action"], "create")
            self.assertFalse((target / ".agentic/config.json").exists())
            result = apply_install(target, files, agentic_os_version="0.1.0")
            self.assertEqual(result["applied"], [".agentic/config.json"])
            journal = json.loads((target / ".agentic/agentic-os/install.json").read_text())
            self.assertEqual(journal["files"][".agentic/config.json"]["owner"], "managed")

    def test_user_modified_files_are_preserved_and_managed_files_can_replace(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            managed = {"config.json": {"content": "v1\n"}}
            apply_install(target, managed)
            managed_update = {"config.json": {"content": "v2\n"}}
            self.assertEqual(plan_install(target, managed_update)["actions"][0]["action"], "replace")
            apply_install(target, managed_update)
            self.assertEqual((target / "config.json").read_text(), "v2\n")
            (target / "config.json").write_text("user edit\n")
            user_update = {"config.json": {"content": "v3\n"}}
            self.assertEqual(plan_install(target, user_update)["actions"][0]["action"], "preserve_modified")
            result = apply_install(target, user_update)
            self.assertEqual(result["preserved"], ["config.json"])
            self.assertEqual((target / "config.json").read_text(), "user edit\n")

    def test_matching_preexisting_file_is_not_claimed_for_uninstall(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            (target / "config.json").write_text("same\n")
            result = apply_install(target, {"config.json": "same\n"})
            self.assertEqual(result["actions"][0]["action"], "unchanged")
            removed = remove_install(target)
            self.assertEqual(removed["removed"], [])
            self.assertEqual((target / "config.json").read_text(), "same\n")

    def test_same_bytes_user_replacement_is_not_reclaimed(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            path = target / "config.txt"
            apply_install(target, {"config.txt": "same\n"})
            old_inode = path.stat().st_ino
            path.unlink()
            path.write_text("same\n")
            self.assertNotEqual(path.stat().st_ino, old_inode)
            result = apply_install(target, {"config.txt": "same\n"})
            self.assertEqual(result["preserved"], ["config.txt"])
            removed = remove_install(target)
            self.assertEqual(removed["removed"], [])
            self.assertEqual(path.read_text(), "same\n")

    def test_same_bytes_replacement_during_plan_does_not_journal_stale_inode(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            path = target / "config.txt"
            apply_install(target, {"config.txt": "v1\n"})
            original_plan = installer.plan_install

            def replace_before_plan(*args, **kwargs):
                replacement = target / "replacement.txt"
                replacement.write_text("v1\n")
                replacement.replace(path)
                return original_plan(*args, **kwargs)

            with patch.object(installer, "plan_install", side_effect=replace_before_plan):
                with self.assertRaises(RuntimeError):
                    apply_install(target, {"config.txt": "v2\n"})
            self.assertEqual(path.read_text(), "v1\n")
            journal = json.loads((target / ".agentic/agentic-os/install.json").read_text())
            self.assertNotEqual(journal["files"]["config.txt"]["inode"], path.stat().st_ino)
            self.assertEqual(apply_install(target, {"config.txt": "v2\n"})["preserved"],
                             ["config.txt"])
            updated = json.loads((target / ".agentic/agentic-os/install.json").read_text())
            self.assertEqual(updated["files"]["config.txt"]["inode"], path.stat().st_ino)
            self.assertEqual(updated["files"]["config.txt"]["owner"], "user")

    def test_same_bytes_user_replacement_survives_direct_uninstall(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            path = target / "config.txt"
            apply_install(target, {"config.txt": "same\n"})
            path.unlink()
            path.write_text("same\n")
            result = remove_install(target)
            self.assertEqual(result["removed"], [])
            self.assertEqual(path.read_text(), "same\n")

    def test_legacy_managed_entry_without_file_identity_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            path = target / "config.txt"
            path.write_text("same\n")
            journal = target / ".agentic/agentic-os/install.json"
            journal.parent.mkdir(parents=True)
            journal.write_text(json.dumps({"files": {"config.txt": {
                "sha256": hashlib.sha256(b"same\n").hexdigest(),
                "owner": "managed", "template": "old", "origin": "plugin"}}}))
            result = remove_install(target)
            self.assertEqual(result["removed"], [])
            self.assertEqual(path.read_text(), "same\n")

    def test_detected_user_edit_remains_user_owned_after_bytes_restored(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            path = target / "config.txt"
            apply_install(target, {"config.txt": "managed-v1\n"})
            path.write_text("user-custom\n")
            result = apply_install(target, {"config.txt": "managed-v2\n"})
            self.assertEqual(result["preserved"], ["config.txt"])
            path.write_text("managed-v1\n")
            removed = remove_install(target)
            self.assertEqual(removed["removed"], [])
            self.assertEqual(path.read_text(), "managed-v1\n")

    def test_invalid_version_does_not_create_files(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            with self.assertRaises(ValueError):
                apply_install(target, {"created.txt": "payload\n"}, agentic_os_version="")
            self.assertFalse((target / "created.txt").exists())
            self.assertFalse((target / ".agentic/agentic-os/install.json").exists())

    def test_invalid_stored_or_supplied_version_blocks_before_file_write(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            journal = target / ".agentic/agentic-os/install.json"
            journal.parent.mkdir(parents=True)
            for invalid in (123, [], "", "not-a-version"):
                journal.write_text(json.dumps({"agentic_os_version": invalid, "files": {}}))
                with self.assertRaises((RuntimeError, ValueError)):
                    apply_install(target, {"created.txt": "payload\n"})
                self.assertFalse((target / "created.txt").exists())
            journal.unlink()
            with self.assertRaises(ValueError):
                apply_install(target, {"created.txt": "payload\n"},
                              agentic_os_version="not-a-version")
            self.assertFalse((target / "created.txt").exists())

    def test_path_escape_and_malformed_journal_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            with self.assertRaises(ValueError):
                plan_install(target, {"../escape": "x"})
            with self.assertRaises(ValueError):
                plan_install(target, {".": "x"})
            with self.assertRaises(ValueError):
                apply_install(target, {".": "x"})
            with self.assertRaises(ValueError):
                merge_settings_file(target, ".", {"x": True})
            with self.assertRaises(ValueError):
                apply_install(target, {"a": "first\n", "a/b": "second\n"},
                              agentic_os_version="1.2.3")
            self.assertFalse((target / "a").exists())
            with self.assertRaises(ValueError):
                apply_install(target, {".agentic": "not a directory\n"})
            self.assertFalse((target / ".agentic").exists())
            journal = target / ".agentic/agentic-os/install.json"
            journal.parent.mkdir(parents=True)
            journal.write_text(json.dumps({"files": {".": {
                "sha256": hashlib.sha256(b"x").hexdigest(), "owner": "managed"}}}))
            with self.assertRaises(ValueError):
                remove_install(target)
            journal.unlink()
            journal.write_text("not-json")
            with self.assertRaises(RuntimeError):
                plan_install(target, {"config.json": "x"})

    def test_remove_preserves_modified_files_and_removes_managed_files(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            apply_install(target, {"managed.txt": "managed\n", "user.txt": "original\n"})
            (target / "user.txt").write_text("user edit\n")
            result = remove_install(target)
            self.assertEqual(result["removed"], ["managed.txt"])
            self.assertEqual(result["preserved"], ["user.txt"])
            self.assertFalse((target / "managed.txt").exists())
            self.assertEqual((target / "user.txt").read_text(), "user edit\n")
            journal = json.loads((target / ".agentic/agentic-os/install.json").read_text())
            self.assertEqual(journal["files"]["user.txt"]["owner"], "user")

    def test_settings_merge_preserves_user_values_and_journals_result(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            settings = target / ".claude/settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(json.dumps({
                "permissions": {"allow": ["Read"], "mode": "user"},
                "custom": True,
            }))
            result = merge_settings_file(target, ".claude/settings.json", {
                "permissions": {"allow": ["Read", "Write"], "deny": ["Bash"], "mode": "managed"},
                "hooks": {"Stop": ["agentic-stop"]},
            }, agentic_os_version="0.2.0")
            merged = json.loads(settings.read_text())
            self.assertEqual(merged["permissions"]["allow"], ["Read", "Write"])
            self.assertEqual(merged["permissions"]["mode"], "user")
            self.assertEqual(merged["custom"], True)
            self.assertEqual(merged["hooks"]["Stop"], ["agentic-stop"])
            journal = json.loads((target / ".agentic/agentic-os/install.json").read_text())
            self.assertEqual(journal["files"][".claude/settings.json"]["template"], "settings-merge")
            self.assertTrue(result["changed"])

    def test_settings_merge_rejects_invalid_existing_json_without_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            path = target / ".claude/settings.json"
            path.parent.mkdir(parents=True)
            path.write_text("not-json")
            with self.assertRaisesRegex(RuntimeError, "invalid JSON"):
                merge_settings_file(target, ".claude/settings.json", {"hooks": {}})
            self.assertEqual(path.read_text(), "not-json")

    def test_settings_merge_rejects_bad_journal_before_changing_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            settings = target / ".claude/settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text('{"user": true}\n')
            journal = target / ".agentic/agentic-os/install.json"
            journal.parent.mkdir(parents=True)
            journal.write_text("not-json")
            with self.assertRaisesRegex(RuntimeError, "journal is unreadable"):
                merge_settings_file(target, ".claude/settings.json", {"hooks": {"Stop": ["x"]}})
            self.assertEqual(settings.read_text(), '{"user": true}\n')

    def test_settings_merge_preserves_preexisting_file_on_uninstall(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            settings = target / ".claude/settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text('{"user": true}\n')
            merge_settings_file(target, ".claude/settings.json", {"hooks": {"Stop": ["x"]}})
            result = remove_install(target)
            self.assertIn(".claude/settings.json", result["preserved"])
            self.assertTrue(settings.exists())

    def test_settings_merge_preserves_modified_managed_file_on_uninstall(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            settings = target / ".claude/settings.json"
            merge_settings_file(target, ".claude/settings.json", {"hooks": {"Stop": ["x"]}})
            settings.write_text('{"hooks": {"Stop": ["x"]}, "user": true}\n')
            merge_settings_file(target, ".claude/settings.json", {"hooks": {"Stop": ["y"]}})
            result = remove_install(target)
            self.assertIn(".claude/settings.json", result["preserved"])
            self.assertTrue(settings.exists())

    def test_installer_rejects_symlinked_parent_and_leaf(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            target = root / "target"
            outside = root / "outside"
            target.mkdir()
            outside.mkdir()
            (target / ".claude").symlink_to(outside, target_is_directory=True)
            for operation in (
                lambda: plan_install(target, {".claude/settings.json": "x"}),
                lambda: apply_install(target, {".claude/settings.json": "x"}),
                lambda: merge_settings_file(target, ".claude/settings.json", {"x": True}),
            ):
                with self.assertRaises(ValueError):
                    operation()
            self.assertFalse((outside / "settings.json").exists())
            (target / ".claude").unlink()
            (target / "settings.json").symlink_to(outside / "settings.json")
            with self.assertRaises(ValueError):
                merge_settings_file(target, "settings.json", {"x": True})

    def test_installer_rejects_symlinked_journal_parent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            target = root / "target"
            outside = root / "outside"
            target.mkdir()
            outside.mkdir()
            (target / ".agentic").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                apply_install(target, {"config.json": "x\n"})
            self.assertFalse((target / "config.json").exists())
            self.assertEqual(list(outside.iterdir()), [])

    def test_parent_swap_after_validation_cannot_redirect_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            target = root / "target"
            outside = root / "outside"
            target.mkdir()
            outside.mkdir()
            (target / "sub").mkdir()
            original = installer._destination
            calls = 0

            def swap_after_check(base, relative):
                nonlocal calls
                result = original(base, relative)
                if relative == "sub/pwn.txt":
                    calls += 1
                    if calls == 2:
                        (target / "sub").rename(target / "saved")
                        (target / "sub").symlink_to(outside, target_is_directory=True)
                return result

            with patch.object(installer, "_destination", side_effect=swap_after_check):
                with self.assertRaises((ValueError, OSError)):
                    apply_install(target, {"sub/pwn.txt": "outside\n"})
            self.assertFalse((outside / "pwn.txt").exists())

    def test_edit_after_plan_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            path = target / "config.txt"
            apply_install(target, {"config.txt": "v1\n"})
            original = installer._atomic_write

            def edit_before_write(root, relative, content, **kwargs):
                if relative == "config.txt":
                    path.write_text("USER EDIT\n")
                return original(root, relative, content, **kwargs)

            with patch.object(installer, "_atomic_write", side_effect=edit_before_write):
                with self.assertRaises(RuntimeError):
                    apply_install(target, {"config.txt": "v2\n"})
            self.assertEqual(path.read_text(), "USER EDIT\n")

    def test_edit_after_uninstall_check_is_not_deleted(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            path = target / "config.txt"
            apply_install(target, {"config.txt": "v1\n"})
            original = installer._unlink

            def edit_before_unlink(root, relative, **kwargs):
                path.write_text("USER EDIT\n")
                return original(root, relative, **kwargs)

            with patch.object(installer, "_unlink", side_effect=edit_before_unlink):
                with self.assertRaises(RuntimeError):
                    remove_install(target)
            self.assertEqual(path.read_text(), "USER EDIT\n")

    def test_same_bytes_new_inode_after_check_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            path = target / "config.txt"
            apply_install(target, {"config.txt": "v1\n"})
            original = installer._atomic_write

            def replace_before_write(root, relative, content, **kwargs):
                if relative == "config.txt":
                    replacement = target / "replacement.txt"
                    replacement.write_text("v1\n")
                    replacement.replace(path)
                return original(root, relative, content, **kwargs)

            with patch.object(installer, "_atomic_write", side_effect=replace_before_write):
                with self.assertRaises(RuntimeError):
                    apply_install(target, {"config.txt": "v2\n"})
            self.assertEqual(path.read_text(), "v1\n")

    def test_journal_edit_before_write_is_not_lost(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            apply_install(target, {"config.txt": "v1\n"})
            journal = target / ".agentic/agentic-os/install.json"
            original = installer._atomic_write

            def edit_journal(root, relative, content, **kwargs):
                if relative == installer.JOURNAL_RELATIVE.as_posix():
                    value = json.loads(journal.read_text())
                    value["operator_note"] = "preserve"
                    journal.write_text(json.dumps(value))
                return original(root, relative, content, **kwargs)

            with patch.object(installer, "_atomic_write", side_effect=edit_journal):
                with self.assertRaises(RuntimeError):
                    apply_install(target, {"config.txt": "v2\n"})
            self.assertEqual(json.loads(journal.read_text())["operator_note"], "preserve")
            self.assertEqual((target / "config.txt").read_text(), "v1\n")
            retry = apply_install(target, {"config.txt": "v2\n"})
            self.assertEqual(retry["applied"], ["config.txt"])

    def test_settings_journal_conflict_restores_user_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            settings = target / "settings.json"
            settings.write_text('{"user": true}\n')
            merge_settings_file(target, "settings.json", {"hooks": {"Stop": ["x"]}})
            before = settings.read_bytes()
            journal = target / ".agentic/agentic-os/install.json"
            original = installer._atomic_write

            def edit_journal(root, relative, content, **kwargs):
                if relative == installer.JOURNAL_RELATIVE.as_posix():
                    value = json.loads(journal.read_text())
                    value["operator_note"] = "preserve"
                    journal.write_text(json.dumps(value))
                return original(root, relative, content, **kwargs)

            with patch.object(installer, "_atomic_write", side_effect=edit_journal):
                with self.assertRaises(RuntimeError):
                    merge_settings_file(target, "settings.json", {"hooks": {"Stop": ["y"]}})
            self.assertEqual(settings.read_bytes(), before)

    def test_uninstall_journal_conflict_restores_removed_file(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            apply_install(target, {"config.txt": "v1\n"})
            journal = target / ".agentic/agentic-os/install.json"
            original = installer._atomic_write

            def edit_journal(root, relative, content, **kwargs):
                if relative == installer.JOURNAL_RELATIVE.as_posix():
                    value = json.loads(journal.read_text())
                    value["operator_note"] = "preserve"
                    journal.write_text(json.dumps(value))
                return original(root, relative, content, **kwargs)

            with patch.object(installer, "_atomic_write", side_effect=edit_journal):
                with self.assertRaises(RuntimeError):
                    remove_install(target)
            self.assertEqual((target / "config.txt").read_text(), "v1\n")
            retry = remove_install(target)
            self.assertEqual(retry["removed"], ["config.txt"])

    def test_journal_directory_sync_failure_does_not_undo_visible_commit(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            apply_install(target, {"config.txt": "v1\n"})
            real_fsync = os.fsync
            calls = 0

            def fail_journal_parent(fd):
                nonlocal calls
                calls += 1
                if calls == 4:
                    raise OSError("injected journal directory sync failure")
                return real_fsync(fd)

            with patch.object(installer.os, "fsync", side_effect=fail_journal_parent):
                with self.assertRaises(OSError):
                    apply_install(target, {"config.txt": "v2\n"})
            self.assertEqual((target / "config.txt").read_text(), "v2\n")
            journal = json.loads((target / ".agentic/agentic-os/install.json").read_text())
            self.assertEqual(journal["files"]["config.txt"]["inode"],
                             (target / "config.txt").stat().st_ino)
            retry = apply_install(target, {"config.txt": "v2\n"})
            self.assertEqual(retry["actions"][0]["action"], "unchanged")

    def test_data_directory_sync_failure_restores_original_inode(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            apply_install(target, {"config.txt": "v1\n"})
            original_inode = (target / "config.txt").stat().st_ino
            real_fsync = os.fsync
            calls = 0

            def fail_data_parent(fd):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("injected data directory sync failure")
                return real_fsync(fd)

            with patch.object(installer.os, "fsync", side_effect=fail_data_parent):
                with self.assertRaises(OSError):
                    apply_install(target, {"config.txt": "v2\n"})
            self.assertEqual((target / "config.txt").read_text(), "v1\n")
            self.assertEqual((target / "config.txt").stat().st_ino, original_inode)
            self.assertEqual(apply_install(target, {"config.txt": "v2\n"})["applied"],
                             ["config.txt"])

    def test_later_conflict_keeps_earlier_write_journaled(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            apply_install(target, {"a.txt": "v1\n", "b.txt": "v1\n"})
            original = installer._atomic_write

            def conflict_after_a(root, relative, content, **kwargs):
                result = original(root, relative, content, **kwargs)
                if relative == "a.txt":
                    (target / "b.txt").write_text("USER\n")
                return result

            with patch.object(installer, "_atomic_write", side_effect=conflict_after_a):
                with self.assertRaises(RuntimeError):
                    apply_install(target, {"a.txt": "v2\n", "b.txt": "v2\n"})
            journal = json.loads((target / ".agentic/agentic-os/install.json").read_text())
            self.assertEqual(journal["files"]["a.txt"]["sha256"], hashlib.sha256(b"v2\n").hexdigest())
            self.assertEqual((target / "a.txt").read_text(), "v2\n")
            self.assertEqual((target / "b.txt").read_text(), "USER\n")

    def test_uninstall_rejects_path_escape_in_journal_before_deletion(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            target = root / "target"
            target.mkdir()
            external = root / "external.txt"
            external.write_text("keep\n")
            journal = target / ".agentic/agentic-os/install.json"
            journal.parent.mkdir(parents=True)
            for escaped in (str(external), "../external.txt"):
                journal.write_text(json.dumps({"files": {
                    escaped: {"sha256": hashlib.sha256(b"keep\n").hexdigest(),
                              "owner": "managed"}}}))
                with self.assertRaises(ValueError):
                    remove_install(target)
            self.assertEqual(external.read_text(), "keep\n")

    def test_malformed_journal_entry_cannot_claim_user_file(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            path = target / "user.txt"
            path.write_text("mine\n")
            journal = target / ".agentic/agentic-os/install.json"
            journal.parent.mkdir(parents=True)
            journal.write_text(json.dumps({"files": {"user.txt": {
                "sha256": hashlib.sha256(b"mine\n").hexdigest()}}}))
            with self.assertRaises(RuntimeError):
                remove_install(target)
            with self.assertRaises(RuntimeError):
                apply_install(target, {"user.txt": "replacement\n"})
            self.assertEqual(path.read_text(), "mine\n")

    def test_journal_ancestor_collisions_and_null_files_fail_before_write(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            journal = target / ".agentic/agentic-os/install.json"
            journal.parent.mkdir(parents=True)
            entry = {"sha256": hashlib.sha256(b"x").hexdigest(), "owner": "managed"}
            for invalid in ({"files": {"a": entry, "a/b": entry}}, {"files": None}):
                journal.write_text(json.dumps(invalid))
                before = journal.read_bytes()
                with self.assertRaises((RuntimeError, ValueError)):
                    remove_install(target)
                self.assertEqual(journal.read_bytes(), before)

    def test_invalid_journal_metadata_fails_before_file_write(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            journal = target / ".agentic/agentic-os/install.json"
            journal.parent.mkdir(parents=True)
            entry = {"sha256": hashlib.sha256(b"x").hexdigest(), "owner": "managed"}
            for invalid in (
                {"phase": 42, "files": {}},
                {"files": {"a": dict(entry, template=[]) }},
                {"files": {"a": dict(entry, origin=None) }},
            ):
                journal.write_text(json.dumps(invalid))
                with self.assertRaises(RuntimeError):
                    apply_install(target, {"created.txt": "payload\n"})
                self.assertFalse((target / "created.txt").exists())

    def test_invalid_manifest_metadata_fails_before_file_write(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            for field in ("template", "origin"):
                with self.subTest(field=field):
                    with self.assertRaises(ValueError):
                        apply_install(target, {"created.txt": {
                            "content": "payload\n", field: object()}})
                    self.assertFalse((target / "created.txt").exists())

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO required")
    def test_fifo_destination_and_journal_reject_without_blocking(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            fifo = target / "pipe"
            os.mkfifo(fifo)
            command = ([sys.executable, "-c",
                        "from runtime.agentic_runtime.installer import plan_install; "
                        "import sys; plan_install(sys.argv[1], {'pipe':'x'})", str(target)])
            result = subprocess.run(command, capture_output=True, text=True, timeout=3,
                                    cwd=ROOT)
            self.assertNotEqual(result.returncode, 0)
            journal = target / ".agentic/agentic-os/install.json"
            journal.parent.mkdir(parents=True)
            os.mkfifo(journal)
            command = ([sys.executable, "-c",
                        "from runtime.agentic_runtime.installer import plan_install; "
                        "import sys; plan_install(sys.argv[1], {'safe.txt':'x'})", str(target)])
            result = subprocess.run(command, capture_output=True, text=True, timeout=3,
                                    cwd=ROOT)
            self.assertNotEqual(result.returncode, 0)

    def test_uninstall_preflights_all_selected_file_types(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            apply_install(target, {"a.txt": "owned\n"})
            os.mkfifo(target / "zpipe")
            journal = target / ".agentic/agentic-os/install.json"
            value = json.loads(journal.read_text())
            value["files"]["zpipe"] = {"sha256": hashlib.sha256(b"x").hexdigest(),
                                       "owner": "managed"}
            journal.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                remove_install(target)
            self.assertEqual((target / "a.txt").read_text(), "owned\n")

    def test_real_directory_swap_after_planning_cannot_redirect_write(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            target = base / "target"
            target.mkdir()
            (target / "sub").mkdir()
            original = installer._atomic_write
            swapped = False

            def swap_parent(root, relative, content, **kwargs):
                nonlocal swapped
                if relative == "sub/pwn.txt" and not swapped:
                    swapped = True
                    (target / "sub").rename(target / "old-sub")
                    (target / "sub").mkdir()
                return original(root, relative, content, **kwargs)

            with patch.object(installer, "_atomic_write", side_effect=swap_parent):
                with self.assertRaises(RuntimeError):
                    apply_install(target, {"sub/pwn.txt": "payload\n"})
            self.assertFalse((target / "sub/pwn.txt").exists())

    def test_root_directory_swap_after_planning_cannot_redirect_write(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            target = base / "target"
            target.mkdir()
            original = installer._atomic_write
            swapped = False

            def swap_root(root, relative, content, **kwargs):
                nonlocal swapped
                if relative == "pwn.txt" and not swapped:
                    swapped = True
                    target.rename(base / "old-target")
                    target.mkdir()
                return original(root, relative, content, **kwargs)

            with patch.object(installer, "_atomic_write", side_effect=swap_root):
                with self.assertRaises(RuntimeError):
                    apply_install(target, {"pwn.txt": "payload\n"})
            self.assertFalse((target / "pwn.txt").exists())

    def test_parent_move_at_rename_cannot_report_success(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            (target / "sub").mkdir()
            original_rename = os.rename
            moved = False

            def move_at_write(source, destination, *args, **kwargs):
                nonlocal moved
                if destination == "pwn.txt" and not moved:
                    moved = True
                    original_rename(target / "sub", target / "old-sub")
                    (target / "sub").mkdir()
                return original_rename(source, destination, *args, **kwargs)

            with patch.object(installer.os, "rename", side_effect=move_at_write):
                with self.assertRaises(RuntimeError):
                    apply_install(target, {"sub/pwn.txt": "payload\n"})
            self.assertFalse((target / "sub/pwn.txt").exists())
            self.assertFalse((target / "old-sub/pwn.txt").exists())

    def test_settings_merge_does_not_replace_existing_null_or_scalar_shapes(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            path = target / "settings.json"
            path.write_text(json.dumps({"nullable": None, "scalar": "user", "items": None}))
            with self.assertRaisesRegex(ValueError, "non-object setting: nullable"):
                merge_settings_file(target, "settings.json", {"nullable": {"x": 1}})
            self.assertEqual(json.loads(path.read_text())["nullable"], None)
            with self.assertRaisesRegex(ValueError, "non-array setting: items"):
                merge_settings_file(target, "settings.json", {"items": ["x"]})
            self.assertEqual(json.loads(path.read_text())["scalar"], "user")

    def test_public_install_operations_are_versioned(self):
        with tempfile.TemporaryDirectory() as temp:
            payload = {
                "api_version": "1.0.0", "operation": "install.plan",
                "target": temp, "files": {"config.json": "x\n"},
            }
            response = subprocess.run([sys.executable, str(ROOT / "runtime/run.py")],
                                      input=json.dumps(payload), text=True,
                                      capture_output=True)
            self.assertEqual(response.returncode, 0, response.stderr)
            result = json.loads(response.stdout)
            self.assertTrue(result["ok"])
            self.assertEqual(result["result"]["actions"][0]["action"], "create")

    def test_public_settings_merge_operation_is_versioned(self):
        with tempfile.TemporaryDirectory() as temp:
            payload = {
                "api_version": "1.0.0", "operation": "install.merge-settings",
                "target": temp, "path": ".claude/settings.json",
                "fragment": {"hooks": {"Stop": ["agentic-stop"]}},
            }
            response = subprocess.run([sys.executable, str(ROOT / "runtime/run.py")],
                                      input=json.dumps(payload), text=True,
                                      capture_output=True)
            self.assertEqual(response.returncode, 0, response.stderr)
            result = json.loads(response.stdout)
            self.assertTrue(result["ok"])
            self.assertTrue((pathlib.Path(temp) / ".claude/settings.json").is_file())


if __name__ == "__main__":
    unittest.main()
