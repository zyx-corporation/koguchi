"""CLI Read-only Reconciliation Inspection — spike。

v0.14: read-only inspection of reconciliation records.
CLI は制御平面、修復ツール、retry trigger ではない。
mismatch_observed は exit code 0（プロセス失敗ではない）。
"""

from dataclasses import dataclass

from koguchi.persistence.reconciliation_records import (
    InMemoryReconciliationAuditStore,
    InMemoryReconciliationResultStore,
)


@dataclass(frozen=True)
class CliInspectionResult:
    exit_code: int
    output: str


_ALLOWED_COMMANDS = {"list", "show", "audit"}
_FORBIDDEN_COMMANDS = {
    "retry", "repair", "approve", "reject",
    "deploy", "commit", "rollback", "delete", "enforce",
}


def inspect_reconciliation_records(
    args: list[str],
    audit_store: InMemoryReconciliationAuditStore,
    result_store: InMemoryReconciliationResultStore,
) -> CliInspectionResult:
    """CLI read-only inspection entry point。

    args[0]: command (list|show|audit)
    args[1]: optional id for show/audit
    """
    if not args:
        return CliInspectionResult(
            exit_code=1,
            output="Usage: koguchi reconciliation <list|show <id>|audit <id>>",
        )

    command = args[0]

    if command in _FORBIDDEN_COMMANDS:
        return CliInspectionResult(
            exit_code=1,
            output=f"Command '{command}' is prohibited. Reconciliation CLI is read-only.",
        )

    if command not in _ALLOWED_COMMANDS:
        return CliInspectionResult(
            exit_code=1,
            output=f"Unknown command: {command}. Allowed: list, show <id>, audit <id>",
        )

    if command == "list":
        return _handle_list(result_store)
    elif command == "show":
        return _handle_show(args, result_store)
    elif command == "audit":
        return _handle_audit(args, audit_store)

    return CliInspectionResult(exit_code=2, output="Internal error")


def _handle_list(
    result_store: InMemoryReconciliationResultStore,
) -> CliInspectionResult:
    records = result_store.list_all()
    if not records:
        return CliInspectionResult(exit_code=0, output="No reconciliation results.")
    lines = ["Reconciliation results:"]
    for r in records:
        if r.recommended_review_focus:
            lines.append(f"  {r.result_id}: {len(r.recommended_review_focus)} review focus item(s)")
    return CliInspectionResult(exit_code=0, output="\n".join(lines))


def _handle_show(
    args: list[str],
    result_store: InMemoryReconciliationResultStore,
) -> CliInspectionResult:
    if len(args) < 2:
        return CliInspectionResult(exit_code=1, output="Usage: show <result_id>")
    rid = args[1]
    record = result_store.get(rid)
    if record is None:
        return CliInspectionResult(exit_code=1, output=f"Result not found: {rid}")

    lines = [
        f"result_id: {record.result_id}",
        f"status: {record.status.value}",
        f"summary: {record.summary}",
    ]
    if record.recommended_review_focus:
        lines.append("review_focus:")
        for item in record.recommended_review_focus:
            lines.append(f"  - {item}")
    lines.append(f"boundary: {record.boundary}")
    return CliInspectionResult(exit_code=0, output="\n".join(lines))


def _handle_audit(
    args: list[str],
    audit_store: InMemoryReconciliationAuditStore,
) -> CliInspectionResult:
    if len(args) < 2:
        return CliInspectionResult(exit_code=1, output="Usage: audit <audit_id>")
    aid = args[1]
    record = audit_store.get(aid)
    if record is None:
        return CliInspectionResult(exit_code=1, output=f"Audit record not found: {aid}")

    lines = [
        f"audit_id: {record.audit_id}",
        f"request_id: {record.request_id}",
        f"route: {record.route}",
        f"backend_id: {record.backend_id}",
        f"execution_id: {record.execution_id}",
        f"kind: {record.reconciliation_kind}",
        f"mode: {record.mode}",
        f"boundary: {record.boundary}",
    ]
    return CliInspectionResult(exit_code=0, output="\n".join(lines))
