"""Phase 5: Reconciliation v2 — Provider 照合の証拠。"""
import json
import uuid

from koguchi.envelope import ActionEnvelope
from koguchi.events import ExecutionEvent
from koguchi.hashchain import compute_hash
from koguchi.provider_reconcile import ProviderReconciler
from koguchi.store import SQLiteExecutionStore


class MockProvider:
    """テスト用の ReconciliableProvider。"""

    def __init__(self, existing_record_ids: set[str] | None = None):
        self._existing = existing_record_ids or set()

    def find_by_audit_record_id(self, record_id: str) -> dict[str, object] | None:
        if record_id in self._existing:
            return {"external_id": f"ext-{record_id[:8]}", "status": "active"}
        return None

    def exists(self, external_id: str) -> bool:
        return external_id in {f"ext-{r[:8]}" for r in self._existing}


def _make_pending(store: SQLiteExecutionStore, tool: str, action_id: str):
    """指定ツールの pending event を Store に注入する。"""
    envelope = ActionEnvelope(
        action_id=action_id,
        tool=tool,
        target="http://example.com",
        parameters_digest="abc",
        permission_scope="network",
        risk_class=["http_request"],
    )
    event = ExecutionEvent(
        event_id=f"ev-{action_id[:8]}",
        record_id=action_id,
        timestamp="2026-01-01T00:00:00+00:00",
        event_type="intent_pending",
        envelope=envelope,
        side_effect_observed="none",
        previous_hash="0" * 64,
        hash="",
    )
    payload_for_hash = {
        k: v
        for k, v in json.loads(event.model_dump_json()).items()
        if k != "hash"
    }
    h = compute_hash("0" * 64, payload_for_hash)
    event = event.model_copy(update={"hash": h})
    store.append(event)


def test_provider_reconciler_finds_existing_resource(workspace):
    """Provider がリソースを発見 → pending_executed_unconfirmed。"""
    store = SQLiteExecutionStore(":memory:")
    action_id = str(uuid.uuid4())

    _make_pending(store, "network.http_get", action_id)

    provider = MockProvider(existing_record_ids={action_id})
    reconciler = ProviderReconciler(store, provider)

    findings = reconciler.reconcile()
    assert len(findings) == 1
    assert findings[0].diagnosis == "pending_executed_unconfirmed"
    assert findings[0].confidence == 0.80


def test_provider_reconciler_not_found(workspace):
    """Provider がリソース未発見 → pending_not_executed。"""
    store = SQLiteExecutionStore(":memory:")
    action_id = str(uuid.uuid4())

    _make_pending(store, "network.http_get", action_id)

    provider = MockProvider(existing_record_ids=set())  # 空
    reconciler = ProviderReconciler(store, provider)

    findings = reconciler.reconcile()
    assert len(findings) == 1
    assert findings[0].diagnosis == "pending_not_executed"
    assert findings[0].confidence == 0.60


def test_provider_reconciler_skips_filesystem_tools(workspace):
    """filesystem ツールは Provider 照合の対象外。"""
    store = SQLiteExecutionStore(":memory:")
    action_id = str(uuid.uuid4())

    _make_pending(store, "filesystem.write", action_id)

    provider = MockProvider(existing_record_ids={action_id})
    reconciler = ProviderReconciler(store, provider)

    findings = reconciler.reconcile()
    assert len(findings) == 0  # filesystem はスキップ
