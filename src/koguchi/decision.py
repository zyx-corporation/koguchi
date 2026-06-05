import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from pydantic import BaseModel

from koguchi.hashchain import GENESIS_HASH, compute_hash
from koguchi.i18n import t


class Decision(BaseModel):
    """意思決定の来歴レコード。ExecutionEvent とは別層で「なぜ」を記録する。"""

    decision_id: str
    action_id: str
    intent: str
    context_snapshot: dict[str, object] | None = None
    timestamp: datetime
    previous_hash: str = GENESIS_HASH
    hash: str = ""


class DecisionStore(Protocol):
    def record(self, decision: Decision) -> None:
        """意思決定を追記する。失敗時は例外を送出する。"""
        ...

    def get(self, action_id: str) -> Decision | None:
        """action_id に紐づく意思決定を取得する。"""
        ...

    def last_hash(self) -> str:
        """直近 Decision の hash。空なら GENESIS_HASH。"""
        ...


@dataclass
class DecisionChainFinding:
    ok: bool
    row_index: int | None
    decision_id: str | None
    diagnosis: str  # "ok" | "previous_hash_mismatch" | "hash_mismatch"
    detail: str


class SQLiteDecisionStore:
    """SQLite バックエンドの DecisionStore。

    ExecutionStore と同じ DB ファイルを共有し、別テーブルで管理する。
    """

    def __init__(self, db_path: str = ":memory:"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                decision_id   TEXT PRIMARY KEY,
                action_id     TEXT NOT NULL,
                intent        TEXT NOT NULL,
                context_json  TEXT,
                timestamp     TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                hash          TEXT NOT NULL
            )
        """)
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_decision_action_id ON decisions(action_id)"
        )
        self._conn.commit()

    def record(self, decision: Decision) -> None:
        context_json = (
            json.dumps(decision.context_snapshot, sort_keys=True, ensure_ascii=False)
            if decision.context_snapshot is not None
            else None
        )
        try:
            self._conn.execute(
                """INSERT INTO decisions
                   (decision_id, action_id, intent, context_json, timestamp,
                    previous_hash, hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    decision.decision_id,
                    decision.action_id,
                    decision.intent,
                    context_json,
                    decision.timestamp.isoformat(),
                    decision.previous_hash,
                    decision.hash,
                ),
            )
            self._conn.commit()
        except sqlite3.Error as e:
            raise RuntimeError(t("err.decision_store_record_failed", error=str(e))) from e

    def last_hash(self) -> str:
        row = self._conn.execute(
            "SELECT hash FROM decisions ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else GENESIS_HASH

    def get(self, action_id: str) -> Decision | None:
        row = self._conn.execute(
            "SELECT decision_id, action_id, intent, context_json, timestamp,"
            " previous_hash, hash"
            " FROM decisions WHERE action_id = ? ORDER BY timestamp DESC LIMIT 1",
            (action_id,),
        ).fetchone()
        if row is None:
            return None
        return Decision(
            decision_id=row[0],
            action_id=row[1],
            intent=row[2],
            context_snapshot=json.loads(row[3]) if row[3] else None,
            timestamp=datetime.fromisoformat(row[4]),
            previous_hash=row[5],
            hash=row[6],
        )

    def verify_chain(self) -> list[DecisionChainFinding]:
        """Decision の hash chain 整合性を検証する。"""
        rows = self._conn.execute(
            "SELECT decision_id, previous_hash, hash FROM decisions ORDER BY rowid"
        ).fetchall()
        findings: list[DecisionChainFinding] = []
        prev_hash = GENESIS_HASH

        for i, (decision_id, recorded_prev, stored_hash) in enumerate(rows):
            if recorded_prev != prev_hash:
                findings.append(DecisionChainFinding(
                    ok=False, row_index=i, decision_id=decision_id,
                    diagnosis="previous_hash_mismatch",
                    detail=t(
                        "chain.previous_hash_mismatch",
                        expected=prev_hash[:12],
                        actual=str(recorded_prev)[:12],
                    ),
                ))
            prev_hash = stored_hash

        return findings


def make_decision(
    action_id: str,
    intent: str,
    context_snapshot: dict[str, object] | None = None,
    *,
    previous_hash: str = GENESIS_HASH,
) -> Decision:
    """Decision レコードのファクトリ関数。hash chain を自動計算する。"""
    decision = Decision(
        decision_id=str(uuid.uuid4()),
        action_id=action_id,
        intent=intent,
        context_snapshot=context_snapshot,
        timestamp=datetime.now(UTC),
        previous_hash=previous_hash,
        hash="",  # placeholder
    )
    payload_for_hash = {
        k: v
        for k, v in json.loads(decision.model_dump_json()).items()
        if k != "hash"
    }
    h = compute_hash(previous_hash, payload_for_hash)
    return decision.model_copy(update={"hash": h})
