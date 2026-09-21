import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "plugins/agentic-sdlc/skills/qa-e2e-generator/scripts/qa-append-event.sh"
ASSEMBLE = ROOT / "plugins/agentic-sdlc/skills/qa-e2e-generator/scripts/qa-assemble-meta.sh"


class LegacyWriteGuardTests(unittest.TestCase):
    def run_script(self, run_dir):
        return subprocess.run([str(SCRIPT), str(run_dir), "1", "preflight", "complete"],
                              text=True, capture_output=True, env=os.environ.copy())

    def test_unmanaged_legacy_fixture_remains_compatible(self):
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_script(Path(temp) / "e2e")
            self.assertEqual(result.returncode, 0, result.stderr)
            event = json.loads((Path(temp) / "e2e/events.jsonl").read_text())
            self.assertEqual(event["status"], "complete")

    def test_managed_runtime_fails_closed_before_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir = root / "docs" / "run" / "e2e"
            run_dir.mkdir(parents=True)
            (root / ".agentic/state").mkdir(parents=True)
            (root / ".agentic/state/runtime.sqlite3").write_bytes(b"marker")
            result = self.run_script(run_dir)
            self.assertEqual(result.returncode, 2)
            self.assertIn("managed SQLite run", result.stderr)
            self.assertFalse((run_dir / "events.jsonl").exists())

    def test_meta_assembler_has_the_same_managed_run_guard(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir = root / "docs" / "run" / "e2e"
            run_dir.mkdir(parents=True)
            (root / ".agentic/state").mkdir(parents=True)
            (root / ".agentic/state/runtime.sqlite3").write_bytes(b"marker")
            result = subprocess.run([str(ASSEMBLE), str(run_dir)], text=True,
                                    capture_output=True, env=os.environ.copy())
            self.assertEqual(result.returncode, 2)
            self.assertIn("managed SQLite run", result.stderr)
            self.assertFalse((run_dir / "meta.json").exists())


if __name__ == "__main__":
    unittest.main()
