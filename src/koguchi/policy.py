"""Policy Gate — redaction_policy に基づく監査ログの開示制御と実行前許可判定。"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from koguchi.decision import Decision
from koguchi.envelope import ActionEnvelope
from koguchi.events import ExecutionEvent

REDACTED = "[REDACTED]"


class RedactionPolicy(StrEnum):
    FULL = "full"
    WITHOUT_INTENT = "without_intent"
    WITHOUT_CONTEXT = "without_context"
    MINIMAL = "minimal"


class PolicyGate:
    """redaction_policy に基づいて ExecutionEvent / Decision を墨消しする。"""

    @staticmethod
    def redact_event(
        event: ExecutionEvent, policy: RedactionPolicy
    ) -> dict[str, object]:
        data: dict[str, object] = {
            "event_id": event.event_id,
            "record_id": event.record_id,
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type,
            "side_effect_observed": event.side_effect_observed,
        }

        if policy == RedactionPolicy.MINIMAL:
            return data

        data["result_digest"] = event.result_digest
        data["error_digest"] = event.error_digest
        data["envelope"] = (
            event.envelope.model_dump() if event.envelope else None
        )
        data["confidence"] = event.confidence
        data["previous_hash"] = event.previous_hash
        data["hash"] = event.hash
        data["decision_ref"] = event.decision_ref
        data["context_ref"] = event.context_ref

        if policy == RedactionPolicy.WITHOUT_INTENT:
            data["intent"] = REDACTED
        else:
            data["intent"] = event.intent

        return data

    @staticmethod
    def redact_decision(
        decision: Decision, policy: RedactionPolicy
    ) -> dict[str, object]:
        data: dict[str, object] = {
            "decision_id": decision.decision_id,
            "action_id": decision.action_id,
            "timestamp": decision.timestamp.isoformat(),
        }

        if policy == RedactionPolicy.MINIMAL:
            return data

        data["previous_hash"] = decision.previous_hash
        data["hash"] = decision.hash

        if policy == RedactionPolicy.WITHOUT_INTENT:
            data["intent"] = REDACTED
        else:
            data["intent"] = decision.intent

        if policy != RedactionPolicy.WITHOUT_CONTEXT:
            data["context_snapshot"] = decision.context_snapshot

        return data


# --- 実行前許可判定 (Phase 3) ---


class PolicyDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class PolicyRule(Protocol):
    def evaluate(self, envelope: ActionEnvelope) -> PolicyDecision:
        """ActionEnvelope を評価し、判定を返す。"""
        ...


@dataclass
class PolicyResult:
    decision: PolicyDecision
    reason: str
    rule_name: str | None = None


class DenyShellExecution:
    """shell.execute を拒否するルール。"""

    def evaluate(self, envelope: ActionEnvelope) -> PolicyDecision:
        if envelope.tool == "shell.execute":
            return PolicyDecision.DENY
        return PolicyDecision.ALLOW


class ExecutionPolicyGate:
    """複数の PolicyRule を評価し、最初の DENY で停止する実行時ゲート。"""

    def __init__(self, rules: list[PolicyRule] | None = None):
        self._rules: list[PolicyRule] = rules or []

    def add_rule(self, rule: PolicyRule) -> None:
        self._rules.append(rule)

    def evaluate(self, envelope: ActionEnvelope) -> PolicyResult:
        for rule in self._rules:
            decision = rule.evaluate(envelope)
            if decision == PolicyDecision.DENY:
                return PolicyResult(
                    decision=PolicyDecision.DENY,
                    reason=f"denied by rule: {rule.__class__.__name__}",
                    rule_name=rule.__class__.__name__,
                )
        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason="all rules passed",
        )
