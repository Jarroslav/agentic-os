import hashlib
import sqlite3
import subprocess
import unittest

from runtime.agentic_runtime.store import RuntimeStore


class RuntimeStoreTests(unittest.TestCase):
  def worktree(self, root, name, branch):
    path = root / name
    path.mkdir()
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "checkout", "-q", "-b", branch], check=True)
    return str(path)

  def test_store_uses_authoritative_database_and_records_lifecycle(self):
    tmp_path = __import__('tempfile').TemporaryDirectory()
    self.addCleanup(tmp_path.cleanup)
    root = __import__('pathlib').Path(tmp_path.name)
    now = [100.0]
    store = RuntimeStore(root, clock=lambda: now[0])
    run = store.create_run("run-1", branch="feature/run-1", worktree=self.worktree(root, "run-1", "feature/run-1"), precondition={"ownership": "verified"})
    self.assertEqual(run["state"], "pending")
    self.assertTrue((root / ".agentic/state/runtime.sqlite3").exists())

    run = store.acquire_lease("run-1", "coordinator-a")
    assert run["lease_epoch"] == 1
    run = store.transition("run-1", "running", expected_revision=run["revision"], lease_epoch=1, coordinator_id="coordinator-a")
    now[0] = 110.0
    run = store.transition("run-1", "waiting_for_user", expected_revision=run["revision"], lease_epoch=1, coordinator_id="coordinator-a")
    now[0] = 1000.0
    run = store.transition("run-1", "running", expected_revision=run["revision"], lease_epoch=1, coordinator_id="coordinator-a")
    now[0] = 1010.0
    run = store.transition("run-1", "completed", expected_revision=run["revision"], lease_epoch=1, coordinator_id="coordinator-a")
    self.assertAlmostEqual(run["active_seconds"], 20.0)


  def test_revision_and_lease_fence_mutations(self):
    tmp_path = __import__('tempfile').TemporaryDirectory()
    self.addCleanup(tmp_path.cleanup)
    store = RuntimeStore(tmp_path.name)
    run = store.create_run("r")
    run = store.acquire_lease("r", "a")
    with self.assertRaises(RuntimeError):
        store.transition("r", "running", expected_revision=0, lease_epoch=1, coordinator_id="a")
    with self.assertRaises(RuntimeError):
        store.transition("r", "running", expected_revision=run["revision"], lease_epoch=2, coordinator_id="a")


  def test_retry_reservation_is_persistent_and_not_refunded(self):
    tmp_path = __import__('tempfile').TemporaryDirectory()
    self.addCleanup(tmp_path.cleanup)
    store = RuntimeStore(tmp_path.name)
    store.create_run("r")
    first = store.reserve_dispatch("r", "dispatch-1", max_dispatches=1)
    self.assertTrue(first["reserved"])
    self.assertTrue(store.reserve_dispatch("r", "dispatch-1", max_dispatches=1)["reserved"])
    self.assertFalse(store.reserve_dispatch("r", "dispatch-2", max_dispatches=1)["reserved"])


  def test_external_intent_is_idempotent_and_reconciliation_is_durable(self):
    tmp_path = __import__('tempfile').TemporaryDirectory()
    self.addCleanup(tmp_path.cleanup)
    store = RuntimeStore(tmp_path.name)
    run = store.create_run("r")
    intent = store.record_external_intent("r", "charge-1", "charge", {"amount": 10})
    self.assertEqual(intent["status"], "pending")
    self.assertEqual(store.record_external_intent("r", "charge-1", "charge", {"amount": 10}), intent)
    result = store.reconcile_external("r", "charge-1", status="succeeded", result={"id": "ch_1"})
    self.assertEqual(result["status"], "succeeded")

  def test_idempotency_key_cannot_change_request(self):
    tmp_path = __import__('tempfile').TemporaryDirectory()
    self.addCleanup(tmp_path.cleanup)
    store = RuntimeStore(tmp_path.name)
    store.create_run("r")
    store.record_external_intent("r", "key", "charge", {"amount": 10})
    with self.assertRaises(ValueError):
        store.record_external_intent("r", "key", "charge", {"amount": 99})

  def test_uncertain_external_outcome_requires_reconciliation(self):
    tmp_path = __import__('tempfile').TemporaryDirectory()
    self.addCleanup(tmp_path.cleanup)
    now = [100.0]
    store = RuntimeStore(tmp_path.name, clock=lambda: now[0])
    store.create_run("r")
    run = store.acquire_lease("r", "coordinator")
    run = store.transition("r", "running", expected_revision=run["revision"], lease_epoch=run["lease_epoch"], coordinator_id="coordinator")
    store.record_external_intent("r", "key", "charge", {"amount": 10}, lease_epoch=run["lease_epoch"], expected_revision=run["revision"], coordinator_id="coordinator")
    now[0] = 150.0
    store.reconcile_external("r", "key", status="uncertain", lease_epoch=run["lease_epoch"], expected_revision=run["revision"] + 1, coordinator_id="coordinator")
    with store._connect() as db:
        self.assertEqual(db.execute("select state from runs where run_id='r'").fetchone()[0], "reconciliation_required")
        self.assertEqual(db.execute("select active_seconds from runs where run_id='r'").fetchone()[0], 50.0)


  def test_export_is_revision_labelled_and_import_legacy_records_hash(self):
    tmp_path = __import__('tempfile').TemporaryDirectory()
    self.addCleanup(tmp_path.cleanup)
    root = __import__('pathlib').Path(tmp_path.name)
    store = RuntimeStore(root)
    run = store.create_run("r", branch="feature/r", worktree=self.worktree(root, "r", "feature/r"), precondition={"ownership": "verified"})
    exported = store.export_run("r", fault=lambda stage: None)
    self.assertTrue(exported.is_dir())
    self.assertIn(f"revision-{run['revision']}", exported.name)
    self.assertEqual(store.export_run("r"), exported)
    payload = b"legacy bytes"
    source = root / "legacy.json"
    source.write_bytes(payload)
    receipt = store.import_legacy("r", source)
    self.assertEqual(receipt["sha256"], hashlib.sha256(payload).hexdigest())
    with sqlite3.connect(root / ".agentic/state/runtime.sqlite3") as db:
        self.assertEqual(db.execute("select count(*) from migration_receipts").fetchone()[0], 1)

  def test_export_requires_ownership_precondition(self):
    tmp_path = __import__('tempfile').TemporaryDirectory()
    self.addCleanup(tmp_path.cleanup)
    store = RuntimeStore(tmp_path.name)
    store.create_run("r")
    with self.assertRaises(RuntimeError):
        store.export_run("r")

  def test_ownership_requires_real_git_worktree_and_matching_branch(self):
    tmp_path = __import__('tempfile').TemporaryDirectory()
    self.addCleanup(tmp_path.cleanup)
    root = __import__('pathlib').Path(tmp_path.name)
    store = RuntimeStore(root)
    with self.assertRaises(ValueError):
      store.create_run("r", branch="feature/r", worktree=str(root / "missing"), precondition={"ownership": "verified"})

  def test_migration_receipt_rejects_changed_source(self):
    tmp_path = __import__('tempfile').TemporaryDirectory()
    self.addCleanup(tmp_path.cleanup)
    root = __import__('pathlib').Path(tmp_path.name)
    store = RuntimeStore(root)
    store.create_run("r")
    source = root / "legacy.json"
    source.write_bytes(b"first")
    store.import_legacy("r", source)
    source.write_bytes(b"changed")
    with self.assertRaises(ValueError):
      store.import_legacy("r", source)

  def test_coordinator_identity_is_required_once_leased(self):
    tmp_path = __import__('tempfile').TemporaryDirectory()
    self.addCleanup(tmp_path.cleanup)
    store = RuntimeStore(tmp_path.name)
    run = store.create_run("r")
    run = store.acquire_lease("r", "owner")
    with self.assertRaises(RuntimeError):
      store.transition("r", "running", expected_revision=run["revision"], lease_epoch=run["lease_epoch"])

  def test_commit_fault_does_not_leave_partial_run(self):
    tmp_path = __import__('tempfile').TemporaryDirectory()
    self.addCleanup(tmp_path.cleanup)
    active = [False]
    def fail(stage):
      if active[0] and stage == "before_commit":
        raise OSError("injected commit fault")
    store = RuntimeStore(tmp_path.name, fault=fail)
    active[0] = True
    with self.assertRaises(OSError):
      store.create_run("r")
    with self.assertRaises(KeyError):
      store.get_run("r")

  def test_export_fault_leaves_authoritative_state_and_no_partial_view(self):
    tmp_path = __import__('tempfile').TemporaryDirectory()
    self.addCleanup(tmp_path.cleanup)
    root = __import__('pathlib').Path(tmp_path.name)
    store = RuntimeStore(root)
    run = store.create_run("r", branch="feature/r", worktree=self.worktree(root, "r-fault", "feature/r"), precondition={"ownership": "verified"})
    def fail(stage):
      if stage == "after_write":
        raise OSError("injected export fault")
    with self.assertRaises(OSError):
      store.export_run("r", fault=fail)
    self.assertEqual(store.get_run("r")["revision"], run["revision"])
    self.assertFalse(any((root / ".agentic/runs/r").iterdir()))
