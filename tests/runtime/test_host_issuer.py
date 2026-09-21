import unittest

from runtime.agentic_runtime.host import issue_evidence_record, verify_dispatch


class HostIssuerTests(unittest.TestCase):
    def event(self):
        return {"type": "agentic.command.completed", "evidence_id": "e1", "run_id": "r",
                "source_revision": 2, "command": "pytest", "cwd": ".",
                "source_hash": "sha256:abc", "exit_status": 0}

    def test_issuer_signs_only_explicit_command_claims(self):
        record = issue_evidence_record(self.event(), b"key", identity="codex",
                                       issued_at=10, expires_at=20)
        verified = verify_dispatch(record, b"key", purpose="evidence.record", now=11)
        self.assertEqual(verified["evidence_id"], "e1")
        self.assertEqual(verified["source_revision"], 2)

    def test_prose_and_missing_fields_cannot_be_issued(self):
        with self.assertRaises(ValueError):
            issue_evidence_record({"type": "assistant", "text": "pytest passed"}, b"key",
                                  identity="codex", issued_at=10, expires_at=20)
        with self.assertRaises(ValueError):
            issue_evidence_record({**self.event(), "source_hash": ""}, b"key",
                                  identity="codex", issued_at=10, expires_at=20)


if __name__ == "__main__":
    unittest.main()
