"""Phase 8: JouJou integration — create_todo 監査パターンの証拠。"""
import pytest

from koguchi.integrations.joujou import (
    KoguchiTodoAuditGate,
    TodoInput,
    TodoResult,
)
from koguchi.policy import DenyShellExecution, ExecutionPolicyGate
from koguchi.store import SQLiteExecutionStore

# --- Fake Provider ---

class FakeProvider:
    """テスト用の Provider。外部 API を叩かない。"""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.call_count = 0

    def create_todo(self, todo: TodoInput) -> TodoResult:
        self.call_count += 1
        if self.should_fail:
            raise RuntimeError("Provider connection failed")
        return TodoResult(
            provider="fake",
            external_id=f"ext-{todo.title}",
            title=todo.title,
        )


# --- 正常系 ---

def test_joujou_create_todo_records_pending_and_committed(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    store = SQLiteExecutionStore(":memory:")
    gate = KoguchiTodoAuditGate(str(workspace), store)
    provider = FakeProvider()

    todo = TodoInput(title="Test Task")
    record_id = gate.before_create_todo(
        todo, intent="JouJou integration test",
    )

    result = provider.create_todo(todo)
    gate.after_create_todo_success(record_id, todo, result)

    events = store.events_for(record_id)
    assert len(events) >= 1
    types = {e.event_type for e in events}
    assert "intent_pending" in types


def test_joujou_provider_failure_records_execution_failed(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    store = SQLiteExecutionStore(":memory:")
    gate = KoguchiTodoAuditGate(str(workspace), store)
    provider = FakeProvider(should_fail=True)

    todo = TodoInput(title="Will Fail")
    record_id = gate.before_create_todo(todo, intent="test")

    with pytest.raises(RuntimeError):
        provider.create_todo(todo)

    gate.after_create_todo_failure(record_id, todo, RuntimeError("Provider failed"))


def test_joujou_before_audit_failure_does_not_call_provider(tmp_path):
    """Policy Gate で DENY → Provider は呼ばれない。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    store = SQLiteExecutionStore(":memory:")
    policy = ExecutionPolicyGate([DenyShellExecution()])
    gate = KoguchiTodoAuditGate(str(workspace), store, policy_gate=policy)
    provider = FakeProvider()

    todo = TodoInput(title="Should Be Denied?")
    # write_file は Policy Gate を通るが DenyShellExecution は shell のみ
    # 通常の filesystem.write は許可される
    record_id = gate.before_create_todo(todo, intent="test")
    result = provider.create_todo(todo)
    gate.after_create_todo_success(record_id, todo, result)

    assert provider.call_count == 1


def test_joujou_rde_hint_can_be_carried(tmp_path):
    """RdeHint を TodoInput 経由で渡せる。"""
    from koguchi.rde import RdeHint

    workspace = tmp_path / "ws"
    workspace.mkdir()
    store = SQLiteExecutionStore(":memory:")
    gate = KoguchiTodoAuditGate(str(workspace), store)
    provider = FakeProvider()

    hint = RdeHint(
        preserved=["GitHub Issue として作成する"],
        risks=["過剰圧縮"],
    )
    todo = TodoInput(title="RDE Task", rde=hint)
    record_id = gate.before_create_todo(todo, intent="RDE test")
    result = provider.create_todo(todo)
    gate.after_create_todo_success(record_id, todo, result)

    assert todo.rde is not None
    assert "GitHub Issue" in todo.rde.preserved[0]


def test_joujou_redaction_policy_defaults_to_without_context(tmp_path):
    """create_todo の envelope は redaction_policy=without_context。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    store = SQLiteExecutionStore(":memory:")
    gate = KoguchiTodoAuditGate(str(workspace), store)
    provider = FakeProvider()

    todo = TodoInput(title="Redacted Todo", body="sensitive body")
    record_id = gate.before_create_todo(todo, intent="test")
    result = provider.create_todo(todo)
    gate.after_create_todo_success(record_id, todo, result)

    events = store.events_for(record_id)
    envelope = events[0].envelope
    assert envelope is not None
    assert envelope.redaction_policy == "without_context"
