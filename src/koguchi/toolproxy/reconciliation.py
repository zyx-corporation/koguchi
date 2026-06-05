"""ToolProxy Read-only Reconciliation — spike integration path。

v0.11: ToolProxy-facing reconciliation request handler。
reconciliation は read-only observation であり、修復・ enforcement は行わない。
"""

from dataclasses import dataclass, field
from pathlib import Path

from koguchi.reconciliation.filesystem_diff import (
    ExpectedArtifact,
    FilesystemReconciliationInput,
    FilesystemReconciliationOutput,
    ReconciliationStatus,
    reconcile_filesystem_diff,
)


@dataclass(frozen=True)
class ToolProxyReconciliationRequest:
    request_id: str
    kind: str
    backend_id: str
    execution_id: str
    expected_artifacts: list[ExpectedArtifact] = field(default_factory=list)
    observed_root: Path = Path(".")
    ignored_paths: list[str] = field(default_factory=list)
    audit_event_refs: list[str] = field(default_factory=list)
    result_store_refs: list[str] = field(default_factory=list)
    mode: str = "read_only"


@dataclass(frozen=True)
class ToolProxyReconciliationResponse:
    request_id: str
    status: ReconciliationStatus
    result: FilesystemReconciliationOutput
    review_focus: list[str]
    boundary: dict[str, bool]


def handle_toolproxy_reconciliation_request(
    request: ToolProxyReconciliationRequest,
) -> ToolProxyReconciliationResponse:
    """ToolProxy 経由の read-only reconciliation request を処理する。

    read_only モードのみ受け付ける。
    mismatch_observed を enforcement / failure / safety verdict と解釈しない。
    """
    if request.mode != "read_only":
        raise ValueError(
            f"Only read_only mode is supported, got: {request.mode}"
        )

    if request.kind != "filesystem_diff_reconciliation":
        raise ValueError(
            f"Only filesystem_diff_reconciliation is supported, got: {request.kind}"
        )

    fs_input = FilesystemReconciliationInput(
        backend_id=request.backend_id,
        execution_id=request.execution_id,
        expected_artifacts=request.expected_artifacts,
        observed_root=request.observed_root,
        ignored_paths=request.ignored_paths,
        audit_event_refs=request.audit_event_refs,
        result_store_refs=request.result_store_refs,
    )

    output = reconcile_filesystem_diff(fs_input)

    return ToolProxyReconciliationResponse(
        request_id=request.request_id,
        status=output.status,
        result=output,
        review_focus=output.recommended_review_focus,
        boundary={
            "read_only": True,
            "no_repair": True,
            "no_control_decision": True,
        },
    )
