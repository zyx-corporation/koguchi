"""v0.11 ToolProxy Reconciliation — read-only integration spike の証拠。"""
from pathlib import Path

import pytest

from koguchi.reconciliation.filesystem_diff import ExpectedArtifact
from koguchi.toolproxy.reconciliation import (
    ToolProxyReconciliationRequest,
    handle_toolproxy_reconciliation_request,
)


def _write_file(root: Path, rel_path: str, content: str) -> Path:
    full = root / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content)
    return full


def test_handles_filesystem_diff_request(tmp_path):
    obs = tmp_path / "obs"
    obs.mkdir()
    _write_file(obs, "a.txt", "hello")

    req = ToolProxyReconciliationRequest(
        request_id="r1", kind="filesystem_diff_reconciliation",
        backend_id="fs", execution_id="e1",
        expected_artifacts=[ExpectedArtifact(path="a.txt")],
        observed_root=obs,
    )
    resp = handle_toolproxy_reconciliation_request(req)
    assert resp.status.value == "matched"


def test_response_has_read_only_boundary(tmp_path):
    obs = tmp_path / "obs"
    obs.mkdir()
    req = ToolProxyReconciliationRequest(
        request_id="r2", kind="filesystem_diff_reconciliation",
        backend_id="fs", execution_id="e2", observed_root=obs,
    )
    resp = handle_toolproxy_reconciliation_request(req)
    assert resp.boundary["read_only"] is True
    assert resp.boundary["no_repair"] is True
    assert resp.boundary["no_control_decision"] is True


def test_rejects_non_readonly_mode():
    req = ToolProxyReconciliationRequest(
        request_id="r3", kind="filesystem_diff_reconciliation",
        backend_id="fs", execution_id="e3", mode="repair",
    )
    with pytest.raises(ValueError):
        handle_toolproxy_reconciliation_request(req)


def test_rejects_unknown_kind():
    req = ToolProxyReconciliationRequest(
        request_id="r4", kind="unknown_kind",
        backend_id="fs", execution_id="e4",
    )
    with pytest.raises(ValueError):
        handle_toolproxy_reconciliation_request(req)


def test_mismatch_is_not_enforcement(tmp_path):
    obs = tmp_path / "obs"
    obs.mkdir()
    req = ToolProxyReconciliationRequest(
        request_id="r5", kind="filesystem_diff_reconciliation",
        backend_id="fs", execution_id="e5",
        expected_artifacts=[ExpectedArtifact(path="missing.txt")],
        observed_root=obs,
    )
    resp = handle_toolproxy_reconciliation_request(req)
    text = " ".join(resp.review_focus)
    for forbidden in [
        "delete", "overwrite", "rollback", "commit", "deploy", "retry",
        "repair", "safe", "unsafe", "approved", "rejected", "enforce",
    ]:
        assert forbidden not in text.lower(), f"'{forbidden}' found"


def test_files_not_modified(tmp_path):
    obs = tmp_path / "obs"
    obs.mkdir()
    f = _write_file(obs, "keep.txt", "original")
    before = f.read_text()
    req = ToolProxyReconciliationRequest(
        request_id="r6", kind="filesystem_diff_reconciliation",
        backend_id="fs", execution_id="e6",
        expected_artifacts=[ExpectedArtifact(path="keep.txt")],
        observed_root=obs,
    )
    handle_toolproxy_reconciliation_request(req)
    assert f.read_text() == before
