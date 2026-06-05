"""Scheduler Read-only Reconciliation Request — spike integration path。

v0.12: Scheduler-originated reconciliation that routes through ToolProxy.
Scheduler は reconciliation を直接実行せず、retry/repair/deploy/correctness decision を行わない。
"""

from dataclasses import dataclass

from koguchi.reconciliation.filesystem_diff import ReconciliationStatus
from koguchi.toolproxy.reconciliation import (
    ToolProxyReconciliationRequest,
    handle_toolproxy_reconciliation_request,
)


@dataclass(frozen=True)
class SchedulerReconciliationTrigger:
    kind: str
    reason: str


@dataclass(frozen=True)
class SchedulerReconciliationRequest:
    request_id: str
    trigger: SchedulerReconciliationTrigger
    reconciliation_request: ToolProxyReconciliationRequest


@dataclass(frozen=True)
class SchedulerReconciliationResult:
    request_id: str
    routed_via: str
    reconciliation_status: ReconciliationStatus
    review_focus: list[str]
    scheduler_action: dict[str, bool]


def request_reconciliation_via_toolproxy(
    request: SchedulerReconciliationRequest,
) -> SchedulerReconciliationResult:
    """Scheduler-originated reconciliation request を ToolProxy 経由で処理する。

    Scheduler は reconciliation を直接実行しない。
    mismatch を retry/repair/deploy/correctness decision に変換しない。
    """
    tp_response = handle_toolproxy_reconciliation_request(
        request.reconciliation_request,
    )

    return SchedulerReconciliationResult(
        request_id=request.request_id,
        routed_via="ToolProxy",
        reconciliation_status=tp_response.status,
        review_focus=tp_response.review_focus,
        scheduler_action={
            "retry": False,
            "repair": False,
            "deploy": False,
            "commit": False,
            "correctness_decision": False,
        },
    )
