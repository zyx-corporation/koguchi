import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from koguchi.envelope import ActionEnvelope
from koguchi.errors import EnvelopeRequiredError, StoreWriteError, WorkspaceBoundaryError
from koguchi.events import ExecutionEvent, ProxyResult
from koguchi.hashchain import compute_hash
from koguchi.store import ExecutionStore


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_event(
    record_id: str,
    event_type: str,
    previous_hash: str,
    envelope: ActionEnvelope | None = None,
    **kwargs,
) -> ExecutionEvent:
    """ExecutionEvent を生成し、hash を model_dump() から計算する。

    hash は保存ペイロード（model_dump_json）から再計算可能でなければならない。
    そのため、まず hash="" で event を組み立て、その model_dump() の hash フィールドを
    除いたものから compute_hash する。これにより verify_chain() が機能する。
    """
    event_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc)
    event = ExecutionEvent(
        event_id=event_id,
        record_id=record_id,
        timestamp=timestamp,
        event_type=event_type,  # type: ignore[arg-type]
        envelope=envelope,
        previous_hash=previous_hash,
        hash="",  # placeholder — 直後で差し替える
        **kwargs,
    )
    payload_for_hash = {
        k: v for k, v in json.loads(event.model_dump_json()).items() if k != "hash"
    }
    h = compute_hash(previous_hash, payload_for_hash)
    return event.model_copy(update={"hash": h})


class ToolProxy:
    """すべての管理対象副作用が通る単一の隘路。"""

    def __init__(self, workspace_dir: str, store: ExecutionStore):
        self._workspace = Path(workspace_dir).resolve()
        self._store = store

    def write_file(
        self,
        envelope: ActionEnvelope | None,
        content: bytes,
    ) -> ProxyResult:
        """
        filesystem.write の atomic 実装。

        INV-1a: envelope が None なら EnvelopeRequiredError を raise。
        INV-1b 第一相: intent_pending を書けなければ副作用を起こさず REJECTED。
        INV-1b 第二相: rename 成功後に commit 記録が失敗すれば UNCONFIRMED。
        §6 atomic write: temp + fsync + rename により partial を構造的に排除。
        §12 スコープ: 親ディレクトリが存在しない場合は REJECTED（mkdir は行わない）。
        """
        # INV-1a: Envelope なし → 呼び出し契約違反
        if envelope is None:
            raise EnvelopeRequiredError("ActionEnvelope は必須です")

        target = Path(envelope.target).resolve()

        # workspace_dir 境界チェック（is_relative_to で前方一致漏れと .. 脱出を両方塞ぐ）
        if not target.is_relative_to(self._workspace):
            raise WorkspaceBoundaryError(f"{target} は workspace_dir 外です")

        # §12 スコープ: Phase 1 は既存ディレクトリ内の書込みのみ。
        # mkdir は暗黙の副作用になるため行わない。親が存在しない場合は REJECTED。
        if not target.parent.exists():
            return ProxyResult.REJECTED

        record_id = envelope.action_id

        # --- INV-1b 第一相: intent_pending を書く ---
        try:
            previous_hash = self._store.last_hash()
            pending_event = _make_event(
                record_id=record_id,
                event_type="intent_pending",
                previous_hash=previous_hash,
                envelope=envelope,
                side_effect_observed="none",
            )
            self._store.append(pending_event)
        except (StoreWriteError, Exception):
            # pending を書けなかった → 副作用を起こさず REJECTED
            return ProxyResult.REJECTED

        # --- §6 atomic write ---
        tmp_path = target.parent / f"{target.name}.tmp.{record_id}"
        try:
            tmp_path.write_bytes(content)
            # fsync で永続化
            with open(tmp_path, "rb") as fh:
                os.fsync(fh.fileno())
            # atomic rename（OS レベルで不可分）
            tmp_path.replace(target)
        except Exception as exec_err:
            # rename 前に失敗 → side_effect_observed = none → FAILURE
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            try:
                prev = self._store.last_hash()
                failed_event = _make_event(
                    record_id=record_id,
                    event_type="execution_failed",
                    previous_hash=prev,
                    envelope=envelope,
                    error_digest=_digest(str(exec_err).encode()),
                    side_effect_observed="none",
                )
                self._store.append(failed_event)
            except Exception:
                pass  # append 失敗時も PENDING 残存 → reconcile: pending_not_executed
            return ProxyResult.FAILURE

        # rename 成功 → side_effect_observed = confirmed
        result_digest = _digest(content)

        # --- INV-1b 第二相: commit 記録 ---
        try:
            prev = self._store.last_hash()
            committed_event = _make_event(
                record_id=record_id,
                event_type="execution_committed",
                previous_hash=prev,
                envelope=envelope,
                result_digest=result_digest,
                side_effect_observed="confirmed",
            )
            self._store.append(committed_event)
            return ProxyResult.SUCCESS
        except Exception:
            # 副作用は成功したが commit 記録に失敗 → UNCONFIRMED
            # Store には intent_pending が残存 → reconcile: pending_executed_unconfirmed
            return ProxyResult.UNCONFIRMED
