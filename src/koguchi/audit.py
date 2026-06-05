"""AuditGate — アプリケーションが依存する Koguchi の唯一の抽象インターフェース。"""

import uuid
from dataclasses import dataclass
from typing import Protocol

from koguchi.envelope import ActionEnvelope
from koguchi.events import ProxyResult
from koguchi.proxy import ToolProxy


@dataclass
class AuditResult:
    action_id: str
    result: ProxyResult
    side_effect_observed: str | None


class AuditGate(Protocol):
    def audit(
        self,
        tool: str,
        target: str,
        params_digest: str,
        permission_scope: str,
        risk_class: list[str],
        intent: str | None = None,
        context: dict[str, object] | None = None,
        data: bytes | None = None,
    ) -> AuditResult:
        """副作用を監査可能な経路で実行し、結果を返す。"""
        ...


class KoguchiAuditGate:
    """ToolProxy をラップする AuditGate の具象実装。

    JouJou 等のアプリケーションは AuditGate Protocol に依存し、
    Koguchi の内部実装（ActionEnvelope, ToolProxy, ExecutionStore）を知らない。
    """

    def __init__(self, proxy: ToolProxy):
        self._proxy = proxy

    def audit(
        self,
        tool: str,
        target: str,
        params_digest: str,
        permission_scope: str,
        risk_class: list[str],
        intent: str | None = None,
        context: dict[str, object] | None = None,
        data: bytes | None = None,
    ) -> AuditResult:
        action_id = str(uuid.uuid4())
        envelope = ActionEnvelope(
            action_id=action_id,
            tool=tool,
            target=target,
            parameters_digest=params_digest,
            permission_scope=permission_scope,
            risk_class=risk_class,
        )

        result = self._proxy.write_file(
            envelope=envelope,
            content=data or b"",
            intent=intent,
            context=context,
        )

        events = self._proxy._store.events_for(action_id)
        observed = events[0].side_effect_observed if events else None

        return AuditResult(
            action_id=action_id,
            result=result,
            side_effect_observed=observed,
        )
