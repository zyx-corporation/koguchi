import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from koguchi.events import ExecutionEvent
from koguchi.proxy import _make_event
from koguchi.store import ExecutionStore


DiagnosisType = Literal[
    "pending_not_executed",
    "pending_executed_unconfirmed",
    "unrecorded_external_change",
    "committed_consistent",
    "committed_diverged",
]


@dataclass
class ReconciliationFinding:
    diagnosis: DiagnosisType
    record_id: str | None
    target: str | None
    confidence: float
    detail: str


def _file_digest(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def reconcile(workspace_dir: str, store: ExecutionStore) -> list[ReconciliationFinding]:
    """
    pending event と workspace 実態を照合し、診断を返す。
    診断結果は reconciliation_observed event として Store にも追記する。
    INV-1c: Tool Proxy を通さない workspace 変更を unrecorded_external_change として検出する。
    """
    workspace = Path(workspace_dir).resolve()
    findings: list[ReconciliationFinding] = []

    # --- pending event の照合 ---
    known_targets: set[str] = set()
    for pending in store.pending():
        envelope = pending.envelope
        if envelope is None:
            continue
        target = Path(envelope.target).resolve()
        known_targets.add(str(target))

        exists = target.exists()
        actual_digest = _file_digest(target) if exists else None
        expected_digest = envelope.expected_result_digest

        if not exists:
            diagnosis: DiagnosisType = "pending_not_executed"
            confidence = 0.85
            detail = f"{target} は存在しない"
        else:
            diagnosis = "pending_executed_unconfirmed"
            confidence = 0.85
            if expected_digest and actual_digest:
                confidence = 0.95 if actual_digest == expected_digest else 0.70
            detail = f"{target} が存在する（digest={actual_digest}）"

        findings.append(ReconciliationFinding(
            diagnosis=diagnosis, record_id=pending.record_id,
            target=str(target), confidence=confidence, detail=detail,
        ))
        _append_reconciliation_event(store, pending.record_id, diagnosis, confidence, detail)

    # --- committed event との照合（store.committed() 経由）---
    committed_by_record: dict[str, ExecutionEvent] = {
        ev.record_id: ev for ev in store.committed()
    }
    for record_id, committed in committed_by_record.items():
        envelope = committed.envelope
        if envelope is None:
            continue
        target = Path(envelope.target).resolve()
        known_targets.add(str(target))
        actual_digest = _file_digest(target)
        expected_digest = committed.result_digest

        if actual_digest is None:
            diagnosis = "committed_diverged"
            confidence = 0.80
            detail = f"{target} が存在しない（削除の可能性）"
        elif expected_digest and actual_digest == expected_digest:
            diagnosis = "committed_consistent"
            confidence = 0.95
            detail = f"{target} は記録と一致"
        else:
            diagnosis = "committed_diverged"
            confidence = 0.75
            detail = f"{target} の内容が記録と食い違う"

        findings.append(ReconciliationFinding(
            diagnosis=diagnosis, record_id=record_id,
            target=str(target), confidence=confidence, detail=detail,
        ))

    # --- unrecorded_external_change の検出（INV-1c）---
    for path in workspace.rglob("*"):
        if not path.is_file():
            continue
        if ".tmp." in path.name:
            continue
        if str(path) not in known_targets:
            finding = ReconciliationFinding(
                diagnosis="unrecorded_external_change", record_id=None,
                target=str(path), confidence=0.90,
                detail=f"{path} は Store に対応 record がない",
            )
            findings.append(finding)
            _append_reconciliation_event(
                store, None, "unrecorded_external_change", 0.90, finding.detail
            )

    return findings


def _append_reconciliation_event(
    store: ExecutionStore,
    record_id: str | None,
    diagnosis: str,
    confidence: float,
    detail: str,
) -> None:
    rid = record_id or f"reconcile-{uuid.uuid4()}"
    prev = store.last_hash()
    event = _make_event(
        record_id=rid,
        event_type="reconciliation_observed",
        previous_hash=prev,
        confidence=confidence,
        error_digest=hashlib.sha256(detail.encode()).hexdigest(),
    )
    try:
        store.append(event)
    except Exception:
        pass  # reconciliation 記録の失敗は中断しない
