"""Phase 6: Redaction / Secret Safety — 墨消しと秘密情報保護の証拠。"""
from datetime import UTC, datetime

from koguchi.decision import make_decision
from koguchi.envelope import ActionEnvelope
from koguchi.events import ExecutionEvent
from koguchi.policy import (
    REDACTED,
    PolicyGate,
    RedactionPolicy,
    export_events,
    redact_dict,
)
from koguchi.proxy import ToolProxy
from koguchi.store import SQLiteExecutionStore
from tests.conftest import make_envelope


def _make_event() -> ExecutionEvent:
    return ExecutionEvent(
        event_id="ev-1",
        record_id="rec-1",
        timestamp=datetime.now(UTC),
        event_type="execution_committed",
        envelope=ActionEnvelope(
            action_id="rec-1",
            tool="filesystem.write",
            target="/tmp/test.txt",
            parameters_digest="abc",
            permission_scope="workspace",
            risk_class=["file_write"],
        ),
        side_effect_observed="confirmed",
        result_digest="digest123",
        intent="重要な設定変更",
        decision_ref="dec-1",
        context_ref="ctx-1",
        confidence=0.95,
        previous_hash="0" * 64,
        hash="a" * 64,
    )


# --- 各 policy の墨消し範囲 ---

def test_redact_event_minimal_hides_envelope_intent_context():
    event = _make_event()
    redacted = PolicyGate.redact_event(event, RedactionPolicy.MINIMAL)
    assert "intent" not in redacted
    assert "decision_ref" not in redacted
    assert "context_ref" not in redacted
    assert "result_digest" not in redacted
    assert "envelope" not in redacted
    assert redacted["event_id"] == "ev-1"
    assert redacted["event_type"] == "execution_committed"


def test_redact_event_without_context_hides_context():
    event = _make_event()
    redacted = PolicyGate.redact_event(event, RedactionPolicy.WITHOUT_CONTEXT)
    assert redacted["intent"] == "重要な設定変更"
    # context_ref は残るが envelope 内の詳細は開示される


def test_redact_event_without_intent_masks_intent():
    event = _make_event()
    redacted = PolicyGate.redact_event(event, RedactionPolicy.WITHOUT_INTENT)
    assert redacted["intent"] == REDACTED
    assert redacted["decision_ref"] == "dec-1"


def test_redact_decision_minimal_hides_intent_and_context():
    decision = make_decision(
        action_id="rec-1", intent="テスト",
        context_snapshot={"key": "value"},
    )
    redacted = PolicyGate.redact_decision(decision, RedactionPolicy.MINIMAL)
    assert "intent" not in redacted
    assert "context_snapshot" not in redacted
    assert "previous_hash" not in redacted


# --- Secret guard ---

def test_full_redaction_still_hides_secret_like_keys():
    """FULL policy でも secret-like key は常に [REDACTED]。"""
    data = {
        "event_id": "ev-1",
        "github_token": "ghp_1234567890abcdef",
        "env": {
            "NOTION_API_KEY": "secret_xxx",
            "safe_value": "hello",
        },
        "list_of_configs": [
            {"name": "db", "password": "p@ssw0rd"},
            {"name": "cache", "host": "localhost"},
        ],
    }
    redacted = redact_dict(data)
    assert redacted["github_token"] == REDACTED
    assert redacted["env"]["NOTION_API_KEY"] == REDACTED
    assert redacted["env"]["safe_value"] == "hello"
    assert redacted["list_of_configs"][0]["password"] == REDACTED
    assert redacted["list_of_configs"][1]["host"] == "localhost"


# --- Export ---

def test_export_requires_redaction_policy(workspace):
    """export_events は RedactionPolicy を必須とする。"""
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(workspace), store)
    envelope = make_envelope(str(workspace), content=b"exported")
    proxy.write_file(envelope=envelope, content=b"exported")

    # MINIMAL export — intent は含まれない
    exported = export_events(store, RedactionPolicy.MINIMAL)
    assert len(exported) >= 1
    assert "intent" not in exported[0]


def test_redacted_export_does_not_leak_tokens(workspace):
    """export に GitHub token 等が含まれない。"""
    data = {"event_id": "ev-1", "authorization": "Bearer xyz", "safe": "ok"}
    redacted = redact_dict(data)
    assert redacted["authorization"] == REDACTED
    assert redacted["safe"] == "ok"
