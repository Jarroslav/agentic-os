"""Durable runtime lifecycle store backed by the authoritative SQLite database."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Mapping
from uuid import uuid4

from .contracts import load_registry, validate_identifier, validate_transition


SCHEMA_VERSION = "1"


class RuntimeStore:
    """Small transactional API for runtime state.

    Every mutating operation commits one SQLite transaction.  ``expected_revision``
    and ``lease_epoch`` are checked in the same transaction as the write, so a
    stale coordinator cannot append a lifecycle event after ownership changes.
    """

    def __init__(self, root: str | os.PathLike[str], clock: Callable[[], float] | None = None,
                 fault: Callable[[str], None] | None = None):
        self.root = Path(root)
        self.db_path = self.root / ".agentic" / "state" / "runtime.sqlite3"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.clock = clock or time.time
        self.fault = fault
        self._initialize()

    def _commit(self, db):
        if self.fault:
            self.fault("before_commit")
        db.commit()
        if self.fault:
            self.fault("after_commit")

    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _initialize(self):
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY, state TEXT NOT NULL, revision INTEGER NOT NULL,
                    lease_epoch INTEGER NOT NULL DEFAULT 0, coordinator_id TEXT,
                    created_at REAL NOT NULL, updated_at REAL NOT NULL,
                    active_seconds REAL NOT NULL DEFAULT 0, active_since REAL,
                    dispatch_count INTEGER NOT NULL DEFAULT 0, metadata_json TEXT NOT NULL,
                    precondition_json TEXT
                );
                CREATE TABLE IF NOT EXISTS transitions (
                    run_id TEXT NOT NULL, sequence INTEGER NOT NULL, source TEXT,
                    target TEXT NOT NULL, revision INTEGER NOT NULL, at REAL NOT NULL,
                    reason TEXT, PRIMARY KEY(run_id, sequence), FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS decisions (
                    run_id TEXT NOT NULL, sequence INTEGER NOT NULL, decision_key TEXT NOT NULL,
                    value_json TEXT NOT NULL, revision INTEGER NOT NULL, at REAL NOT NULL,
                    PRIMARY KEY(run_id, sequence), FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS counters (
                    run_id TEXT NOT NULL, name TEXT NOT NULL, value INTEGER NOT NULL,
                    PRIMARY KEY(run_id, name), FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS dispatch_reservations (
                    run_id TEXT NOT NULL, reservation_id TEXT NOT NULL, created_at REAL NOT NULL,
                    PRIMARY KEY(run_id, reservation_id), FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS messages (
                    run_id TEXT NOT NULL, sequence INTEGER NOT NULL, sender TEXT,
                    body TEXT NOT NULL, at REAL NOT NULL, revision INTEGER NOT NULL,
                    PRIMARY KEY(run_id, sequence), FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS external_actions (
                    run_id TEXT NOT NULL, idempotency_key TEXT NOT NULL, action TEXT NOT NULL,
                    request_json TEXT NOT NULL, status TEXT NOT NULL, result_json TEXT,
                    created_at REAL NOT NULL, updated_at REAL NOT NULL,
                    PRIMARY KEY(run_id, idempotency_key), FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS migration_receipts (
                    run_id TEXT NOT NULL, source TEXT NOT NULL, sha256 TEXT NOT NULL,
                    imported_at REAL NOT NULL, receipt_json TEXT NOT NULL,
                    PRIMARY KEY(run_id, source), FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );
                """
            )
            db.execute("INSERT OR IGNORE INTO metadata(key,value) VALUES('schema_version',?)", (SCHEMA_VERSION,))
            db.execute("INSERT OR IGNORE INTO metadata(key,value) VALUES('registry_contract_version',?)", (load_registry()["contract_version"],))
            self._commit(db)

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    def _run(self, db, run_id: str) -> dict[str, Any]:
        row = db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError("unknown run: " + run_id)
        result = dict(row)
        result["metadata"] = json.loads(result.pop("metadata_json"))
        raw = result.pop("precondition_json")
        result["precondition"] = json.loads(raw) if raw else None
        return result

    def _guard(self, db, run_id, expected_revision, lease_epoch, coordinator_id=None):
        row = db.execute("SELECT revision, lease_epoch, coordinator_id, state FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError("unknown run: " + run_id)
        if expected_revision is not None and row["revision"] != expected_revision:
            raise RuntimeError("revision mismatch")
        if row["coordinator_id"] is not None:
            if lease_epoch != row["lease_epoch"]:
                raise RuntimeError("lease epoch mismatch")
            if not coordinator_id or coordinator_id != row["coordinator_id"]:
                raise RuntimeError("coordinator identity mismatch")
        if row["state"] in {"completed", "failed", "cancelled"}:
            raise RuntimeError("run is terminal")
        return row

    def create_run(self, run_id: str | None = None, *, branch: str | None = None,
                   worktree: str | None = None, metadata: Mapping[str, Any] | None = None,
                   precondition: Mapping[str, Any] | None = None) -> dict[str, Any]:
        run_id = run_id or uuid4().hex
        validate_identifier(run_id)
        if (branch is None) != (worktree is None):
            raise ValueError("branch and worktree must be supplied together")
        condition = dict(precondition or {})
        if branch is not None:
            if condition.get("ownership") != "verified":
                raise ValueError("branch/worktree ownership must be verified before run creation")
            worktree_path = Path(worktree)
            if not worktree_path.is_dir():
                raise ValueError("worktree must be an existing directory")
            try:
                inside = subprocess.run(
                    ["git", "-C", str(worktree_path), "rev-parse", "--is-inside-work-tree"],
                    check=True, capture_output=True, text=True,
                ).stdout.strip()
                current_branch = subprocess.run(
                    ["git", "-C", str(worktree_path), "branch", "--show-current"],
                    check=True, capture_output=True, text=True,
                ).stdout.strip()
            except (OSError, subprocess.CalledProcessError) as exc:
                raise ValueError("worktree ownership could not be verified") from exc
            if inside != "true" or current_branch != branch:
                raise ValueError("worktree branch does not match requested branch")
            condition.update({"branch": branch, "worktree": worktree, "ownership": "verified"})
        now = self.clock()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                db.execute("INSERT INTO runs(run_id,state,revision,created_at,updated_at,metadata_json,precondition_json) VALUES(?,?,?,?,?,?,?)",
                           (run_id, "pending", 0, now, now, self._json(dict(metadata or {})), self._json(condition) if condition else None))
            except sqlite3.IntegrityError as exc:
                db.rollback()
                raise ValueError("run already exists: " + run_id) from exc
            db.execute("INSERT INTO transitions VALUES(?,?,?,?,?,?,?)", (run_id, 1, None, "pending", 0, now, "created"))
            self._commit(db)
            return self._run(db, run_id)

    def get_run(self, run_id: str) -> dict[str, Any]:
        """Read authoritative state without trusting an export."""
        with self._connect() as db:
            return self._run(db, run_id)

    def acquire_lease(self, run_id: str, coordinator_id: str, *, expected_revision: int | None = None) -> dict[str, Any]:
        if not coordinator_id:
            raise ValueError("coordinator_id is required")
        now = self.clock()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT revision, lease_epoch, state FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if row is None:
                raise KeyError("unknown run: " + run_id)
            if row["state"] in {"completed", "failed", "cancelled"}:
                db.rollback()
                raise RuntimeError("cannot acquire a lease for a terminal run")
            if expected_revision is not None and row["revision"] != expected_revision:
                raise RuntimeError("revision mismatch")
            epoch = row["lease_epoch"] + 1
            revision = row["revision"] + 1
            db.execute("UPDATE runs SET coordinator_id=?,lease_epoch=?,revision=?,updated_at=? WHERE run_id=?", (coordinator_id, epoch, revision, now, run_id))
            self._commit(db)
            return self._run(db, run_id)

    def transition(self, run_id: str, target: str, *, expected_revision: int | None = None,
                   lease_epoch: int | None = None, coordinator_id: str | None = None,
                   reason: str | None = None) -> dict[str, Any]:
        now = self.clock()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._guard(db, run_id, expected_revision, lease_epoch, coordinator_id)
            current = db.execute("SELECT state,active_seconds,active_since FROM runs WHERE run_id=?", (run_id,)).fetchone()
            validate_transition(current["state"], target)
            active = current["active_seconds"]
            if current["active_since"] is not None and target != "running":
                active += max(0, now - current["active_since"])
            since = now if target == "running" else None
            revision = row["revision"] + 1
            seq = db.execute("SELECT COALESCE(MAX(sequence),0)+1 FROM transitions WHERE run_id=?", (run_id,)).fetchone()[0]
            db.execute("UPDATE runs SET state=?,revision=?,updated_at=?,active_seconds=?,active_since=? WHERE run_id=?", (target, revision, now, active, since, run_id))
            db.execute("INSERT INTO transitions VALUES(?,?,?,?,?,?,?)", (run_id, seq, current["state"], target, revision, now, reason))
            self._commit(db)
            return self._run(db, run_id)

    def reserve_dispatch(self, run_id: str, reservation_id: str, *, max_dispatches: int | None = None,
                         expected_revision: int | None = None, lease_epoch: int | None = None,
                         coordinator_id: str | None = None) -> dict[str, Any]:
        default_limit = int(load_registry()["policy_defaults"]["max_dispatches"])
        if max_dispatches is None:
            max_dispatches = default_limit
        if type(max_dispatches) is not int or max_dispatches < 1 or max_dispatches > default_limit:
            raise ValueError("max_dispatches must be within the registry ceiling")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._guard(db, run_id, expected_revision, lease_epoch, coordinator_id)
            if db.execute("SELECT 1 FROM dispatch_reservations WHERE run_id=? AND reservation_id=?", (run_id, reservation_id)).fetchone():
                count = db.execute("SELECT COALESCE(value,0) FROM counters WHERE run_id=? AND name='dispatches'", (run_id,)).fetchone()[0]
                db.rollback()
                return {"reserved": True, "reservation_id": reservation_id, "count": count}
            existing = db.execute("SELECT value FROM counters WHERE run_id=? AND name=?", (run_id, "dispatches")).fetchone()
            count = existing[0] if existing else 0
            if max_dispatches is not None and count >= max_dispatches:
                db.rollback()
                return {"reserved": False, "reservation_id": reservation_id, "count": count}
            db.execute("INSERT INTO counters(run_id,name,value) VALUES(?,?,?) ON CONFLICT(run_id,name) DO UPDATE SET value=value+1", (run_id, "dispatches", 1))
            db.execute("INSERT INTO dispatch_reservations VALUES(?,?,?)", (run_id, reservation_id, self.clock()))
            db.execute("UPDATE runs SET dispatch_count=dispatch_count+1,revision=?,updated_at=? WHERE run_id=?", (row["revision"] + 1, self.clock(), run_id))
            self._commit(db)
            return {"reserved": True, "reservation_id": reservation_id, "count": count + 1}

    def record_decision(self, run_id: str, decision_key: str, value: Any, *, expected_revision: int | None = None, lease_epoch: int | None = None, coordinator_id: str | None = None) -> dict[str, Any]:
        return self._append(run_id, "decisions", (decision_key, self._json(value)), expected_revision, lease_epoch, coordinator_id)

    def record_message(self, run_id: str, body: str, *, sender: str | None = None, expected_revision: int | None = None, lease_epoch: int | None = None, coordinator_id: str | None = None, max_messages: int | None = None, max_bytes: int | None = None) -> dict[str, Any]:
        if not isinstance(body, str):
            raise ValueError("body must be a string")
        policy = load_registry()["policy_defaults"]
        max_messages = int(policy["max_messages_per_worker"] if max_messages is None else max_messages)
        max_bytes = int(policy["max_message_bytes"] if max_bytes is None else max_bytes)
        if len(body.encode("utf-8")) > max_bytes:
            raise ValueError("message exceeds byte limit")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._guard(db, run_id, expected_revision, lease_epoch, coordinator_id)
            count = db.execute("SELECT COUNT(*) FROM messages WHERE run_id=?", (run_id,)).fetchone()[0]
            if count >= max_messages:
                raise RuntimeError("message budget exhausted")
            seq = db.execute("SELECT COALESCE(MAX(sequence),0)+1 FROM messages WHERE run_id=?", (run_id,)).fetchone()[0]
            now = self.clock(); revision = row["revision"] + 1
            db.execute("INSERT INTO messages VALUES(?,?,?,?,?,?)", (run_id, seq, sender, body, now, revision))
            db.execute("UPDATE runs SET revision=?,updated_at=? WHERE run_id=?", (revision, now, run_id))
            self._commit(db)
            return self._run(db, run_id)

    def _append(self, run_id, kind, values, expected_revision, lease_epoch, coordinator_id=None):
        now = self.clock()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._guard(db, run_id, expected_revision, lease_epoch, coordinator_id)
            seq = db.execute(f"SELECT COALESCE(MAX(sequence),0)+1 FROM {kind} WHERE run_id=?", (run_id,)).fetchone()[0]
            revision = row["revision"] + 1
            if kind == "decisions":
                db.execute("INSERT INTO decisions VALUES(?,?,?,?,?,?)", (run_id, seq, values[0], values[1], revision, now))
            else:
                db.execute("INSERT INTO messages VALUES(?,?,?,?,?,?)", (run_id, seq, values[0], values[1], now, revision))
            db.execute("UPDATE runs SET revision=?,updated_at=? WHERE run_id=?", (revision, now, run_id))
            self._commit(db)
            return self._run(db, run_id)

    def record_external_intent(self, run_id: str, idempotency_key: str, action: str, request: Any, *, expected_revision: int | None = None, lease_epoch: int | None = None, coordinator_id: str | None = None) -> dict[str, Any]:
        now = self.clock()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._guard(db, run_id, expected_revision, lease_epoch, coordinator_id)
            found = db.execute("SELECT * FROM external_actions WHERE run_id=? AND idempotency_key=?", (run_id, idempotency_key)).fetchone()
            if found:
                if found["action"] != action or found["request_json"] != self._json(request):
                    db.rollback()
                    raise ValueError("idempotency key reused with different action or request")
                db.rollback()
                return self._external(found)
            db.execute("INSERT INTO external_actions VALUES(?,?,?,?,?,?,?,?)", (run_id, idempotency_key, action, self._json(request), "pending", None, now, now))
            db.execute("UPDATE runs SET revision=?,updated_at=? WHERE run_id=?", (row["revision"] + 1, now, run_id))
            self._commit(db)
            return self._external(db.execute("SELECT * FROM external_actions WHERE run_id=? AND idempotency_key=?", (run_id, idempotency_key)).fetchone())

    def _external(self, row):
        result = dict(row)
        result["request"] = json.loads(result.pop("request_json"))
        raw_result = result.pop("result_json")
        result["result"] = json.loads(raw_result) if raw_result else None
        return result

    def reconcile_external(self, run_id: str, idempotency_key: str, *, status: str, result: Any = None, expected_revision: int | None = None, lease_epoch: int | None = None, coordinator_id: str | None = None) -> dict[str, Any]:
        if status not in {"pending", "succeeded", "failed", "uncertain"}:
            raise ValueError("invalid external status")
        now = self.clock()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._guard(db, run_id, expected_revision, lease_epoch, coordinator_id)
            if db.execute("SELECT 1 FROM external_actions WHERE run_id=? AND idempotency_key=?", (run_id, idempotency_key)).fetchone() is None:
                raise KeyError("unknown external intent")
            db.execute("UPDATE external_actions SET status=?,result_json=?,updated_at=? WHERE run_id=? AND idempotency_key=?", (status, self._json(result) if result is not None else None, now, run_id, idempotency_key))
            revision = row["revision"] + 1
            current = db.execute("SELECT state,active_seconds,active_since FROM runs WHERE run_id=?", (run_id,)).fetchone()
            current_state = current["state"]
            if status == "uncertain" and current_state in {"running", "interrupted"}:
                seq = db.execute("SELECT COALESCE(MAX(sequence),0)+1 FROM transitions WHERE run_id=?", (run_id,)).fetchone()[0]
                db.execute("INSERT INTO transitions VALUES(?,?,?,?,?,?,?)", (run_id, seq, current_state, "reconciliation_required", revision, now, "external outcome uncertain"))
                active = current["active_seconds"]
                if current["active_since"] is not None:
                    active += max(0, now - current["active_since"])
                db.execute("UPDATE runs SET state='reconciliation_required',revision=?,updated_at=?,active_seconds=?,active_since=NULL WHERE run_id=?", (revision, now, active, run_id))
            else:
                db.execute("UPDATE runs SET revision=?,updated_at=? WHERE run_id=?", (revision, now, run_id))
            self._commit(db)
            return self._external(db.execute("SELECT * FROM external_actions WHERE run_id=? AND idempotency_key=?", (run_id, idempotency_key)).fetchone())

    def export_run(self, run_id: str, *, fault: Callable[[str], None] | None = None) -> Path:
        with self._connect() as db:
            run = self._run(db, run_id)
            precondition = run.get("precondition") or {}
            if precondition.get("ownership") != "verified" or not precondition.get("branch") or not precondition.get("worktree"):
                raise RuntimeError("branch/worktree ownership precondition is required before export")
            transitions = [dict(r) for r in db.execute("SELECT * FROM transitions WHERE run_id=? ORDER BY sequence", (run_id,))]
            decisions = [dict(r) for r in db.execute("SELECT * FROM decisions WHERE run_id=? ORDER BY sequence", (run_id,))]
            messages = [dict(r) for r in db.execute("SELECT * FROM messages WHERE run_id=? ORDER BY sequence", (run_id,))]
            external = [self._external(r) for r in db.execute("SELECT * FROM external_actions WHERE run_id=? ORDER BY created_at", (run_id,))]
        destination = self.root / ".agentic" / "runs" / run_id / f"revision-{run['revision']}"
        parent = destination.parent
        parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if (destination / "run.json").is_file():
                return destination
            raise RuntimeError("incomplete export requires reconciliation: " + destination.as_posix())
        temp = Path(tempfile.mkdtemp(prefix=".export-", dir=parent))
        try:
            if fault: fault("before_write")
            (temp / "run.json").write_text(self._json({"run": run, "transitions": transitions, "decisions": decisions, "messages": messages, "external_actions": external}), encoding="utf-8")
            if fault: fault("after_write")
            try:
                temp.rename(destination)
            except OSError:
                if (destination / "run.json").is_file():
                    shutil.rmtree(temp, ignore_errors=True)
                    return destination
                raise
            if fault: fault("after_rename")
        except Exception:
            shutil.rmtree(temp, ignore_errors=True)
            raise
        return destination

    def import_legacy(self, run_id: str, source: str | os.PathLike[str] | bytes) -> dict[str, Any]:
        if isinstance(source, (str, os.PathLike)):
            path = Path(source)
            payload = path.read_bytes()
            name = str(path)
        else:
            payload = bytes(source)
            name = "<bytes>"
        receipt = {"run_id": run_id, "source": name, "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload), "imported_at": self.clock()}
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM runs WHERE run_id=?", (run_id,)).fetchone() is None:
                raise KeyError("unknown run: " + run_id)
            existing = db.execute("SELECT sha256,receipt_json FROM migration_receipts WHERE run_id=? AND source=?", (run_id, name)).fetchone()
            if existing:
                if existing["sha256"] != receipt["sha256"]:
                    raise ValueError("legacy source changed after migration receipt")
                return json.loads(existing["receipt_json"])
            db.execute("INSERT INTO migration_receipts VALUES(?,?,?,?,?)", (run_id, name, receipt["sha256"], receipt["imported_at"], self._json(receipt)))
            self._commit(db)
        return receipt
