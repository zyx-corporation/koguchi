"""JouJou integration — Koguchi の最初の実用統合例。

Koguchi は JouJou 専用ではない。このモジュールは integration pattern の reference 実装である。
"""

import hashlib
import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from koguchi.envelope import ActionEnvelope
from koguchi.events import ProxyResult
from koguchi.policy import ExecutionPolicyGate
from koguchi.proxy import ToolProxy
from koguchi.rde import RdeHint
from koguchi.store import ExecutionStore


class UnconfirmedSideEffectError(Exception):
    """副作用は成功した可能性があるが audit commit に失敗した。"""

    def __init__(
        self,
        record_id: str,
        provider: str | None = None,
        message: str = "Side effect may have succeeded, but audit commit failed.",
    ) -> None:
        self.record_id = record_id
        self.provider = provider
        super().__init__(message)


class TodoInput(BaseModel):
    """JouJou の Todo 作成入力。"""

    title: str
    body: str | None = None
    target: str | None = None
    source: str = "manual"
    context_summary: str | None = None
    rde: RdeHint | None = None


@dataclass
class TodoResult:
    provider: str
    external_id: str
    url: str | None = None
    title: str = ""
    status: str = "created"
    audit_record_id: str | None = None


class KoguchiTodoAuditGate:
    """JouJou の create_todo を Koguchi で監査する integration adapter。

    Provider は Koguchi を知らない。この adapter だけが Koguchi と Provider を接続する。
    """

    def __init__(
        self,
        workspace_dir: str,
        execution_store: ExecutionStore,
        policy_gate: ExecutionPolicyGate | None = None,
    ) -> None:
        self._workspace = workspace_dir
        self._proxy = ToolProxy(workspace_dir, execution_store, policy_gate=policy_gate)
        self._store = execution_store
        Path(workspace_dir, ".koguchi", "audit").mkdir(parents=True, exist_ok=True)

    def _audit_target(self, record_id: str) -> str:
        return str(
            Path(self._workspace) / ".koguchi" / "audit" / f"{record_id}.json"
        )

    def before_create_todo(
        self,
        todo: TodoInput,
        intent: str,
        context: dict[str, object] | None = None,
    ) -> str:
        """副作用実行前の intent 記録。record_id を返す。"""
        record_id = str(uuid.uuid4())
        params_digest = hashlib.sha256(
            json.dumps(todo.model_dump(), sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()

        envelope = ActionEnvelope(
            action_id=record_id,
            tool="todo.create",
            target=self._audit_target(record_id),
            parameters_digest=params_digest,
            permission_scope=f"todo:create:{todo.target or 'auto'}",
            risk_class=["external_api_write", "todo_creation"],
            redaction_policy="without_context",
        )

        result = self._proxy.write_file(
            envelope=envelope,
            content=json.dumps(todo.model_dump(), ensure_ascii=False).encode(),
            intent=intent,
            context=context,
        )

        if result == ProxyResult.REJECTED:
            raise PermissionError(f"Todo creation denied by policy: {todo.title}")

        return record_id

    def after_create_todo_success(
        self,
        record_id: str,
        todo: TodoInput,
        result: TodoResult,
    ) -> None:
        """副作用成功後の commit 記録。失敗時は UnconfirmedSideEffectError。"""
        envelope = ActionEnvelope(
            action_id=record_id,
            tool="todo.create",
            target=self._audit_target(record_id),
            parameters_digest="unused",
            permission_scope=f"todo:create:{todo.target or 'auto'}",
            risk_class=["external_api_write", "todo_creation"],
            redaction_policy="without_context",
        )

        proxy_result = self._proxy.write_file(
            envelope=envelope,
            content=json.dumps(result.__dict__, ensure_ascii=False).encode(),
            intent="audit commit for todo.create",
        )

        if proxy_result == ProxyResult.UNCONFIRMED:
            raise UnconfirmedSideEffectError(
                record_id=record_id, provider=result.provider,
            )

    def after_create_todo_failure(
        self,
        record_id: str,
        todo: TodoInput,
        error: Exception,
    ) -> None:
        """副作用失敗の記録。"""
        envelope = ActionEnvelope(
            action_id=record_id,
            tool="todo.create",
            target=self._audit_target(record_id),
            parameters_digest="unused",
            permission_scope=f"todo:create:{todo.target or 'auto'}",
            risk_class=["external_api_write", "todo_creation"],
            redaction_policy="without_context",
        )

        self._proxy.write_file(
            envelope=envelope,
            content=str(error).encode(),
            intent="audit failure record for todo.create",
        )
