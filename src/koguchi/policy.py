"""Policy Gate — redaction_policy に基づく監査ログの開示制御。"""

from enum import StrEnum

from koguchi.decision import Decision
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
