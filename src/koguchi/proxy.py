import contextlib
import hashlib
import http.client
import json
import os
import subprocess
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from koguchi.context import ContextResolver
from koguchi.decision import DecisionStore, make_decision
from koguchi.envelope import ActionEnvelope
from koguchi.errors import EnvelopeRequiredError, StoreWriteError, WorkspaceBoundaryError
from koguchi.events import ExecutionEvent, ProxyResult
from koguchi.hashchain import compute_hash
from koguchi.i18n import t
from koguchi.store import ExecutionStore


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_event(
    record_id: str,
    event_type: str,
    previous_hash: str,
    envelope: ActionEnvelope | None = None,
    **kwargs: Any,
) -> ExecutionEvent:
    """ExecutionEvent を生成し、hash を model_dump() から計算する。

    hash は保存ペイロード（model_dump_json）から再計算可能でなければならない。
    そのため、まず hash="" で event を組み立て、その model_dump() の hash フィールドを
    除いたものから compute_hash する。これにより verify_chain() が機能する。
    """
    event_id = str(uuid.uuid4())
    timestamp = datetime.now(UTC)
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

    def __init__(
        self,
        workspace_dir: str,
        store: ExecutionStore,
        decision_store: DecisionStore | None = None,
        context_resolver: ContextResolver | None = None,
    ):
        self._workspace = Path(workspace_dir).resolve()
        self._store = store
        self._decision_store = decision_store
        self._context_resolver = context_resolver

    def _prepare_execution(
        self,
        record_id: str,
        envelope: ActionEnvelope,
        intent: str | None,
        context: dict[str, object] | None,
    ) -> tuple[str | None, str | None] | None:
        """Decision 記録と intent_pending 書込みを行い、decision_id と context_ref を返す。
        失敗時は呼び出し元が ProxyResult で戻るよう None を返す。
        """
        # コンテキスト自動キャプチャ（明示的コンテキストがない場合）
        effective_context = context
        if effective_context is None and self._context_resolver is not None:
            effective_context = self._context_resolver.resolve()

        # Decision 記録
        decision_id: str | None = None
        context_ref: str | None = None
        if self._decision_store is not None and intent is not None:
            decision = make_decision(
                action_id=record_id,
                intent=intent,
                context_snapshot=effective_context,
                previous_hash=self._decision_store.last_hash(),
            )
            try:
                self._decision_store.record(decision)
            except Exception:
                return None  # 呼び出し元で REJECTED にする
            decision_id = decision.decision_id
            if effective_context is not None:
                context_ref = _digest(
                    json.dumps(effective_context, sort_keys=True, ensure_ascii=False).encode()
                )

        # intent_pending 書込み
        try:
            previous_hash = self._store.last_hash()
            pending_event = _make_event(
                record_id=record_id,
                event_type="intent_pending",
                previous_hash=previous_hash,
                envelope=envelope,
                side_effect_observed="none",
                intent=intent,
                decision_ref=decision_id,
                context_ref=context_ref,
            )
            self._store.append(pending_event)
        except (StoreWriteError, Exception):
            return None

        return decision_id, context_ref

    def write_file(
        self,
        envelope: ActionEnvelope | None,
        content: bytes,
        intent: str | None = None,
        context: dict[str, object] | None = None,
    ) -> ProxyResult:
        """
        filesystem.write の atomic 実装。

        INV-1a: envelope が None なら EnvelopeRequiredError を raise。
        INV-1b 第一相: intent_pending を書けなければ副作用を起こさず REJECTED。
        INV-1b 第二相: rename 成功後に commit 記録が失敗すれば UNCONFIRMED。
        §6 atomic write: temp + fsync + rename により partial を構造的に排除。
        §12 スコープ: 親ディレクトリが存在しない場合は REJECTED（mkdir は行わない）。

        Phase 2: decision_store が注入されている場合、intent をもとに Decision を
        記録し、ExecutionEvent の intent / decision_ref / context_ref を埋める。
        Decision 記録に失敗した場合は副作用を起こさず REJECTED。
        """
        # INV-1a: Envelope なし → 呼び出し契約違反
        if envelope is None:
            raise EnvelopeRequiredError(t("err.envelope_required"))

        target = Path(envelope.target).resolve()

        # workspace_dir 境界チェック（is_relative_to で前方一致漏れと .. 脱出を両方塞ぐ）
        if not target.is_relative_to(self._workspace):
            raise WorkspaceBoundaryError(t("err.workspace_boundary", target=str(target)))

        # §12 スコープ: Phase 1 は既存ディレクトリ内の書込みのみ。
        # mkdir は暗黙の副作用になるため行わない。親が存在しない場合は REJECTED。
        if not target.parent.exists():
            return ProxyResult.REJECTED

        record_id = envelope.action_id

        # --- INV-1b 第一相 + Phase 2 Decision 記録 ---
        prepared = self._prepare_execution(record_id, envelope, intent, context)
        if prepared is None:
            return ProxyResult.REJECTED
        decision_id, context_ref = prepared

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
                with contextlib.suppress(OSError):
                    tmp_path.unlink()
            try:
                prev = self._store.last_hash()
                failed_event = _make_event(
                    record_id=record_id,
                    event_type="execution_failed",
                    previous_hash=prev,
                    envelope=envelope,
                    error_digest=_digest(str(exec_err).encode()),
                    side_effect_observed="none",
                    intent=intent,
                    decision_ref=decision_id,
                    context_ref=context_ref,
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
                intent=intent,
                decision_ref=decision_id,
                context_ref=context_ref,
            )
            self._store.append(committed_event)
            return ProxyResult.SUCCESS
        except Exception:
            # 副作用は成功したが commit 記録に失敗 → UNCONFIRMED
            # Store には intent_pending が残存 → reconcile: pending_executed_unconfirmed
            return ProxyResult.UNCONFIRMED

    def execute_shell(
        self,
        envelope: ActionEnvelope | None,
        command: list[str],
        timeout: float | None = None,
        intent: str | None = None,
        context: dict[str, object] | None = None,
    ) -> ProxyResult:
        """
        shell.execute の非 atomic 実装。

        INV-1a: envelope が None なら EnvelopeRequiredError を raise。
        INV-1b 第一相: intent_pending を書けなければ副作用を起こさず REJECTED。
        INV-1b 第二相: 実行後に commit 記録が失敗すれば UNCONFIRMED。

        非 atomic のため side_effect_observed は:
        - "confirmed": プロセスが完了（exit code に関わらず）
        - "unknown": タイムアウト（プロセスがまだ実行中の可能性）
        - "none": プロセス起動失敗
        """
        if envelope is None:
            raise EnvelopeRequiredError(t("err.envelope_required"))

        record_id = envelope.action_id

        # --- INV-1b 第一相 + Phase 2 Decision 記録 ---
        prepared = self._prepare_execution(record_id, envelope, intent, context)
        if prepared is None:
            return ProxyResult.REJECTED
        decision_id, context_ref = prepared

        # --- 非 atomic 実行 ---
        try:
            proc = subprocess.run(
                command,
                capture_output=True,
                cwd=str(self._workspace),
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            # タイムアウト → side_effect_observed = unknown → FAILURE
            try:
                prev = self._store.last_hash()
                failed_event = _make_event(
                    record_id=record_id,
                    event_type="execution_failed",
                    previous_hash=prev,
                    envelope=envelope,
                    error_digest=_digest(b"timeout"),
                    side_effect_observed="unknown",
                    intent=intent,
                    decision_ref=decision_id,
                    context_ref=context_ref,
                )
                self._store.append(failed_event)
            except Exception:
                pass
            return ProxyResult.FAILURE
        except Exception as exec_err:
            # プロセス起動失敗 → side_effect_observed = none → FAILURE
            try:
                prev = self._store.last_hash()
                failed_event = _make_event(
                    record_id=record_id,
                    event_type="execution_failed",
                    previous_hash=prev,
                    envelope=envelope,
                    error_digest=_digest(str(exec_err).encode()),
                    side_effect_observed="none",
                    intent=intent,
                    decision_ref=decision_id,
                    context_ref=context_ref,
                )
                self._store.append(failed_event)
            except Exception:
                pass
            return ProxyResult.FAILURE

        # プロセス完了 → side_effect_observed = confirmed
        result_digest = _digest(
            proc.stdout + proc.stderr + str(proc.returncode).encode()
        )

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
                intent=intent,
                decision_ref=decision_id,
                context_ref=context_ref,
            )
            self._store.append(committed_event)
            return ProxyResult.SUCCESS
        except Exception:
            # 副作用は成功したが commit 記録に失敗 → UNCONFIRMED
            return ProxyResult.UNCONFIRMED

    def make_directory(
        self,
        envelope: ActionEnvelope | None,
        intent: str | None = None,
        context: dict[str, object] | None = None,
    ) -> ProxyResult:
        """
        filesystem.mkdir の実装。冪等（exist_ok=True）。

        INV-1a: envelope が None なら EnvelopeRequiredError を raise。
        INV-1b 第一相: intent_pending を書けなければ REJECTED。
        INV-1b 第二相: mkdir 後に commit 記録が失敗すれば UNCONFIRMED。
        """
        if envelope is None:
            raise EnvelopeRequiredError(t("err.envelope_required"))

        target = Path(envelope.target).resolve()

        if not target.is_relative_to(self._workspace):
            raise WorkspaceBoundaryError(
                t("err.workspace_boundary", target=str(target))
            )

        record_id = envelope.action_id

        prepared = self._prepare_execution(record_id, envelope, intent, context)
        if prepared is None:
            return ProxyResult.REJECTED
        decision_id, context_ref = prepared

        # --- mkdir 実行 ---
        try:
            target.mkdir(parents=True, exist_ok=True)
        except Exception as exec_err:
            try:
                prev = self._store.last_hash()
                failed_event = _make_event(
                    record_id=record_id,
                    event_type="execution_failed",
                    previous_hash=prev,
                    envelope=envelope,
                    error_digest=_digest(str(exec_err).encode()),
                    side_effect_observed="none",
                    intent=intent,
                    decision_ref=decision_id,
                    context_ref=context_ref,
                )
                self._store.append(failed_event)
            except Exception:
                pass
            return ProxyResult.FAILURE

        result_digest = _digest(str(target).encode())

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
                intent=intent,
                decision_ref=decision_id,
                context_ref=context_ref,
            )
            self._store.append(committed_event)
            return ProxyResult.SUCCESS
        except Exception:
            return ProxyResult.UNCONFIRMED

    def http_get(
        self,
        envelope: ActionEnvelope | None,
        url: str,
        timeout: float | None = None,
        intent: str | None = None,
        context: dict[str, object] | None = None,
    ) -> ProxyResult:
        """
        network.http_get の実装。urllib による HTTP GET。

        side_effect_observed:
        - "confirmed": レスポンスを完全に受信
        - "partial": IncompleteRead（部分受信）
        - "unknown": タイムアウト
        - "none": 接続失敗（DNS/拒否）
        """
        if envelope is None:
            raise EnvelopeRequiredError(t("err.envelope_required"))

        record_id = envelope.action_id

        prepared = self._prepare_execution(record_id, envelope, intent, context)
        if prepared is None:
            return ProxyResult.REJECTED
        decision_id, context_ref = prepared

        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                body = resp.read()
        except http.client.IncompleteRead as e:
            # partial: レスポンスの一部だけ受信
            result_digest = _digest(
                str(e.status if hasattr(e, "status") else 0).encode()
                + b"\n"
                + (e.partial if hasattr(e, "partial") else b"")
            )
            try:
                prev = self._store.last_hash()
                failed_event = _make_event(
                    record_id=record_id,
                    event_type="execution_failed",
                    previous_hash=prev,
                    envelope=envelope,
                    error_digest=_digest(str(e).encode()),
                    side_effect_observed="partial",
                    result_digest=result_digest,
                    intent=intent,
                    decision_ref=decision_id,
                    context_ref=context_ref,
                )
                self._store.append(failed_event)
            except Exception:
                pass
            return ProxyResult.FAILURE
        except TimeoutError as e:
            # unknown: タイムアウト
            try:
                prev = self._store.last_hash()
                failed_event = _make_event(
                    record_id=record_id,
                    event_type="execution_failed",
                    previous_hash=prev,
                    envelope=envelope,
                    error_digest=_digest(str(e).encode()),
                    side_effect_observed="unknown",
                    intent=intent,
                    decision_ref=decision_id,
                    context_ref=context_ref,
                )
                self._store.append(failed_event)
            except Exception:
                pass
            return ProxyResult.FAILURE
        except urllib.error.HTTPError as e:
            # HTTP エラー（4xx/5xx）— レスポンスは得た → confirmed
            result_digest = _digest(
                str(e.code).encode() + b"\n" + e.read()
            )
        except urllib.error.URLError as e:
            # none: 接続失敗
            try:
                prev = self._store.last_hash()
                failed_event = _make_event(
                    record_id=record_id,
                    event_type="execution_failed",
                    previous_hash=prev,
                    envelope=envelope,
                    error_digest=_digest(str(e).encode()),
                    side_effect_observed="none",
                    intent=intent,
                    decision_ref=decision_id,
                    context_ref=context_ref,
                )
                self._store.append(failed_event)
            except Exception:
                pass
            return ProxyResult.FAILURE
        else:
            # 正常完了
            result_digest = _digest(
                str(resp.status).encode() + b"\n" + body
            )

        # INV-1b 第二相: commit 記録
        try:
            prev = self._store.last_hash()
            committed_event = _make_event(
                record_id=record_id,
                event_type="execution_committed",
                previous_hash=prev,
                envelope=envelope,
                result_digest=result_digest,
                side_effect_observed="confirmed",
                intent=intent,
                decision_ref=decision_id,
                context_ref=context_ref,
            )
            self._store.append(committed_event)
            return ProxyResult.SUCCESS
        except Exception:
            return ProxyResult.UNCONFIRMED
