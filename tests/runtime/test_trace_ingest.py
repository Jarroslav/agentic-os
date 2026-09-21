import tempfile
import unittest

from runtime.agentic_runtime.host import sign_dispatch
from runtime.agentic_runtime.store import RuntimeStore
from runtime.agentic_runtime.trace import ingest_command_event


class TraceIngestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.key = b"adapter-key"
        self.store = RuntimeStore(self.tmp.name, host_key=self.key)
        self.store.create_run("r")
        self.store.transition("r", "running")

    def event(self, **changes):
        run = self.store.get_run("r")
        host = sign_dispatch({
            "record_id": "event-host", "purpose": "evidence.record",
            "run_id": "r", "identity": "claude", "evidence_id": "e1",
            "source_revision": run["revision"], "source_hash": "sha256:abc",
            "exit_status": 0, "issued_at": 0, "expires_at": 9999999999,
        }, self.key)
        result = {
            "type": "agentic.command.completed", "evidence_id": "e1",
            "run_id": "r", "source_revision": run["revision"],
            "command": "pytest", "cwd": ".", "source_hash": "sha256:abc",
            "exit_status": 0, "host_record": host,
        }
        result.update(changes)
        return result

    def test_ingest_persists_signed_receipt(self):
        evidence = ingest_command_event(self.store, self.event())
        self.assertEqual(evidence["evidence_id"], "e1")
        self.assertEqual(evidence["host_record_id"], "event-host")

    def test_malformed_event_has_no_store_side_effect(self):
        before = self.store.get_run("r")["revision"]
        with self.assertRaisesRegex(ValueError, "explicit"):
            ingest_command_event(self.store, {"type": "assistant", "text": "passed"})
        self.assertEqual(self.store.get_run("r")["revision"], before)

    def test_event_run_mismatch_is_rejected_by_store(self):
        event = self.event(run_id="other")
        with self.assertRaises((KeyError, RuntimeError)):
            ingest_command_event(self.store, event)


if __name__ == "__main__":
    unittest.main()
