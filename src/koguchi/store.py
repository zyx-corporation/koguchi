import json
import sqlite3
from dataclasses import dataclass
from typing import Protocol

from koguchi.errors import StoreWriteError
from koguchi.events import ExecutionEvent
from koguchi.hashchain import GENESIS_HASH, compute_hash
from koguchi.i18n import t


class ExecutionStore(Protocol):
    def append(self, event: ExecutionEvent) -> None:
        """event を追記する。失敗時は例外を送出し、決して暗黙に成功扱いしない。"""

    def last_hash(self) -> str:
        """直近 event の hash。空なら GENESIS_HASH。"""

    def events_for(self, record_id: str) -> list[ExecutionEvent]:
        """同一 record_id に属する event 列を時系列で返す。"""

    def pending(self) -> list[ExecutionEvent]:
        """intent_pending のまま execution_committed / execution_failed で閉じていない event。
        reconciliation の入力となる。"""

    def committed(self) -> list[ExecutionEvent]:
        """execution_committed event の一覧を時系列で返す。"""


@dataclass
class ChainFinding:
    ok: bool
    row_index: int | None
    event_id: str | None
    diagnosis: str   # "ok" | "previous_hash_mismatch" | "hash_mismatch"
    detail: str


class SQLiteExecutionStore:
    """append-only SQLite バックエンド。"""

    def __init__(self, db_path: str = ":memory:"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS execution_events (
                rowid       INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id    TEXT NOT NULL UNIQUE,
                record_id   TEXT NOT NULL,
                timestamp   TEXT NOT NULL,
                event_type  TEXT NOT NULL,
                payload     TEXT NOT NULL,
                hash        TEXT NOT NULL
            )
        """)
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_record_id ON execution_events(record_id)"
        )
        self._conn.commit()

    def append(self, event: ExecutionEvent) -> None:
        payload = json.loads(event.model_dump_json())
        try:
            self._conn.execute(
                """INSERT INTO execution_events
                   (event_id, record_id, timestamp, event_type, payload, hash)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    event.event_id,
                    event.record_id,
                    event.timestamp.isoformat(),
                    event.event_type,
                    json.dumps(payload, sort_keys=True, ensure_ascii=False),
                    event.hash,
                ),
            )
            self._conn.commit()
        except sqlite3.Error as e:
            raise StoreWriteError(str(e)) from e

    def last_hash(self) -> str:
        row = self._conn.execute(
            "SELECT hash FROM execution_events ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else GENESIS_HASH

    def events_for(self, record_id: str) -> list[ExecutionEvent]:
        rows = self._conn.execute(
            "SELECT payload FROM execution_events WHERE record_id = ? ORDER BY rowid",
            (record_id,),
        ).fetchall()
        return [ExecutionEvent(**json.loads(r[0])) for r in rows]

    def pending(self) -> list[ExecutionEvent]:
        """intent_pending のうち、同じ record_id に execution_committed / execution_failed
        が存在しないものを返す。"""
        rows = self._conn.execute("""
            SELECT payload FROM execution_events
            WHERE event_type = 'intent_pending'
              AND record_id NOT IN (
                  SELECT record_id FROM execution_events
                  WHERE event_type IN ('execution_committed', 'execution_failed')
              )
            ORDER BY rowid
        """).fetchall()
        return [ExecutionEvent(**json.loads(r[0])) for r in rows]

    def committed(self) -> list[ExecutionEvent]:
        """execution_committed event の一覧を時系列で返す。"""
        rows = self._conn.execute(
            "SELECT payload FROM execution_events"
            " WHERE event_type = 'execution_committed' ORDER BY rowid"
        ).fetchall()
        return [ExecutionEvent(**json.loads(r[0])) for r in rows]

    def verify_chain(self) -> list[ChainFinding]:
        """hash chain の整合性を検証する。

        各 event について:
        - previous_hash が直前 event の hash と一致するか（chain linkage）
        - 保存ペイロードから hash を再計算し、記録値と一致するか（tampering 検出）

        改竄・ロスト・順序破壊があれば ok=False の ChainFinding を返す。
        正常なら空リストを返す。
        """
        rows = self._conn.execute(
            "SELECT payload, hash FROM execution_events ORDER BY rowid"
        ).fetchall()
        findings: list[ChainFinding] = []
        prev_hash = GENESIS_HASH

        for i, (payload_str, stored_hash) in enumerate(rows):
            payload = json.loads(payload_str)
            event_id = payload.get("event_id")

            # chain linkage: previous_hash == 直前 event の hash
            recorded_prev = payload.get("previous_hash", "")
            if recorded_prev != prev_hash:
                findings.append(ChainFinding(
                    ok=False, row_index=i, event_id=event_id,
                    diagnosis="previous_hash_mismatch",
                    detail=t(
                        "chain.previous_hash_mismatch",
                        expected=prev_hash[:12],
                        actual=str(recorded_prev)[:12],
                    ),
                ))

            # tampering 検出: ペイロードから hash を再計算
            payload_for_hash = {k: v for k, v in payload.items() if k != "hash"}
            recomputed = compute_hash(recorded_prev, payload_for_hash)
            if recomputed != stored_hash:
                findings.append(ChainFinding(
                    ok=False, row_index=i, event_id=event_id,
                    diagnosis="hash_mismatch",
                    detail=t(
                        "chain.hash_mismatch",
                        stored=stored_hash[:12],
                        recomputed=recomputed[:12],
                    ),
                ))

            prev_hash = stored_hash

        return findings
