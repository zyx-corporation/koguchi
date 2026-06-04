import sqlite3
import json
from datetime import datetime, timezone
from typing import Protocol

from koguchi.events import ExecutionEvent
from koguchi.hashchain import GENESIS_HASH, compute_hash, canonical_serialize
from koguchi.errors import StoreWriteError


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
