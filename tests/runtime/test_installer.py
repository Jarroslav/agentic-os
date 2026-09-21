import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

from runtime.agentic_runtime.installer import apply_install, plan_install, remove_install


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

    def test_path_escape_and_malformed_journal_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            target = pathlib.Path(temp)
            with self.assertRaises(ValueError):
                plan_install(target, {"../escape": "x"})
            journal = target / ".agentic/agentic-os/install.json"
            journal.parent.mkdir(parents=True)
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


if __name__ == "__main__":
    unittest.main()
