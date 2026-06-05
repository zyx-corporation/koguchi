"""v0.12 Scheduler Reconciliation — read-only request spike の証拠。"""
from pathlib import Path

from koguchi.reconciliation.filesystem_diff import ExpectedArtifact
from koguchi.scheduler.reconciliation import (
    SchedulerReconciliationRequest,
    SchedulerReconciliationTrigger,
    request_reconciliation_via_toolproxy,
)
from koguchi.toolproxy.reconciliation import ToolProxyReconciliationRequest


def _write_file(root: Path, rel_path: str, content: str) -> Path:
    full = root / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content)
    return full


def test_scheduler_routes_via_toolproxy(tmp_path):
    obs = tmp_path / "obs"
    obs.mkdir()
    _write_file(obs, "a.txt", "hello")

    tp_req = ToolProxyReconciliationRequest(
        request_id="r1", kind="filesystem_diff_reconciliation",
        backend_id="fs", execution_id="e1",
        expected_artifacts=[ExpectedArtifact(path="a.txt")],
        observed_root=obs,
    )
    sched_req = SchedulerReconciliationRequest(
        request_id="s1",
        trigger=SchedulerReconciliationTrigger(kind="manual", reason="test"),
        reconciliation_request=tp_req,
    )
    result = request_reconciliation_via_toolproxy(sched_req)
    assert result.routed_via == "ToolProxy"


def test_scheduler_action_all_false(tmp_path):
    obs = tmp_path / "obs"
    obs.mkdir()
    tp_req = ToolProxyReconciliationRequest(
        request_id="r2", kind="filesystem_diff_reconciliation",
        backend_id="fs", execution_id="e2", observed_root=obs,
    )
    sched_req = SchedulerReconciliationRequest(
        request_id="s2",
        trigger=SchedulerReconciliationTrigger(kind="manual", reason="test"),
        reconciliation_request=tp_req,
    )
    result = request_reconciliation_via_toolproxy(sched_req)
    assert result.scheduler_action["retry"] is False
    assert result.scheduler_action["repair"] is False
    assert result.scheduler_action["deploy"] is False
    assert result.scheduler_action["commit"] is False
    assert result.scheduler_action["correctness_decision"] is False


def test_mismatch_still_has_false_actions(tmp_path):
    obs = tmp_path / "obs"
    obs.mkdir()
    tp_req = ToolProxyReconciliationRequest(
        request_id="r3", kind="filesystem_diff_reconciliation",
        backend_id="fs", execution_id="e3",
        expected_artifacts=[ExpectedArtifact(path="missing.txt")],
        observed_root=obs,
    )
    sched_req = SchedulerReconciliationRequest(
        request_id="s3",
        trigger=SchedulerReconciliationTrigger(kind="manual", reason="test"),
        reconciliation_request=tp_req,
    )
    result = request_reconciliation_via_toolproxy(sched_req)
    assert result.reconciliation_status.value == "mismatch_observed"
    assert result.scheduler_action["retry"] is False
    assert result.scheduler_action["repair"] is False


def test_review_focus_preserved(tmp_path):
    obs = tmp_path / "obs"
    obs.mkdir()
    tp_req = ToolProxyReconciliationRequest(
        request_id="r4", kind="filesystem_diff_reconciliation",
        backend_id="fs", execution_id="e4",
        expected_artifacts=[ExpectedArtifact(path="missing.txt")],
        observed_root=obs,
    )
    sched_req = SchedulerReconciliationRequest(
        request_id="s4",
        trigger=SchedulerReconciliationTrigger(kind="manual", reason="test"),
        reconciliation_request=tp_req,
    )
    result = request_reconciliation_via_toolproxy(sched_req)
    assert len(result.review_focus) > 0
    assert any("missing.txt" in r for r in result.review_focus)


def test_no_forbidden_wording_in_result(tmp_path):
    obs = tmp_path / "obs"
    obs.mkdir()
    tp_req = ToolProxyReconciliationRequest(
        request_id="r5", kind="filesystem_diff_reconciliation",
        backend_id="fs", execution_id="e5",
        expected_artifacts=[ExpectedArtifact(path="missing.txt")],
        observed_root=obs,
    )
    sched_req = SchedulerReconciliationRequest(
        request_id="s5",
        trigger=SchedulerReconciliationTrigger(kind="manual", reason="test"),
        reconciliation_request=tp_req,
    )
    result = request_reconciliation_via_toolproxy(sched_req)
    text = " ".join(result.review_focus)
    for forbidden in [
        "retry required", "repair required", "delete", "overwrite",
        "rollback", "commit", "deploy", "safe", "unsafe",
        "approved", "rejected", "enforce", "correct", "incorrect",
    ]:
        assert forbidden not in text.lower(), f"'{forbidden}' found"
