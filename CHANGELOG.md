# Changelog

All notable changes to this project will be documented in this file.

This project uses Developer Preview milestones before stable releases.

## v0.1.0-dev-preview

### Status

Developer Preview.

This release is intended for architectural review, local experimentation, and implementation feedback. It is not a stable or security-hardened release.

### Added

- Foundation structure for Koguchi / Context-Aware Harness
- ToolProxy as the side-effect chokepoint
- Decision logging (Decision, DecisionStore, decision_ref, intent, context_ref)
- PolicyGate for envelope / policy-level decisions (allow/deny/require_approval)
- AuditGate integration (Protocol, KoguchiAuditGate)
- Reconciliation v2 (ReconciliableProvider, ProviderReconciler)
- Redaction / Secret Safety (redacted view, secret guard, export API)
- RDE / T-RDE support (RdeHint, RdeReview, T-RDE helpers)
- JouJou integration (KoguchiTodoAuditGate, UnconfirmedSideEffectError)
- RuntimeBoundary for best-effort runtime boundary checks
- ServiceRuntime as an accountable execution surface
- AuditEvent / AuditEventSink / InMemoryAuditEventSink
- ADR-001 to ADR-021
- ADR index with categorized reading order
- Architecture overview
- Developer getting-started guide
- Minimal tool proxy example
- Known limitations document
- v0.1 Developer Preview checklist

### Quality

- ruff: All checks passed
- pytest: 117 passed
- mypy: Success, 18 source files
- minimal example: allow / deny / audit event paths verified

### Security Notes

Koguchi is not a security sandbox.

The current Python implementation provides best-effort runtime constraint checks. RuntimeBoundary can constrain ordinary execution paths, but it does not provide strong isolation against hostile code execution.

Strong isolation is deferred to future work, including Rust chokepoint and OS/container-level enforcement.

### Deferred

- Persistent audit store
- Reconciliation scheduler
- Rust chokepoint
- seccomp
- container isolation
- network namespace
- macOS sandbox
- full dashboard
- remote API server

### RDE Summary

v0.1.0-dev-preview preserves the Phase 0–10 architectural structure and converts it into an externally reviewable Developer Preview. It adds documentation, examples, known limitations, and release boundaries without claiming completion or security hardening.

## v0.2.0-dev

### Added

- `JsonlAuditEventSink` — persistent append-only JSONL audit store
- `sanitize_audit_event()` — allowlist-based field extraction
- `AuditStoreError`, `AuditSerializationError`, `AuditWriteError`
- `examples/persistent_audit_store.py`
- ADR-022

### Notes

- JSONL files are not cryptographically sealed
- Single-process use only
- Multi-process write coordination deferred

## v0.3.0-dev

### Added

- `ReconciliationScheduler` — deferred verification from audit events
- `ReconciliationJob`, `ReconciliationResult`, `ReconciliationStatus`
- `InMemoryReconciliationJobStore`
- Schema-level verification (request_id, tool_name, allowed check)
- Duplicate job prevention via deterministic job_id
- `examples/reconciliation_scheduler.py`
- ADR-023

### Notes

- Reconciliation is schema-level only; no filesystem diff or auto-repair
- Denied/error events are skipped
- Daemon/cron/background worker not implemented

## v0.4.0-dev

### Added

- Rust chokepoint spike: `crates/koguchi-chokepoint/`
- JSON stdin/stdout protocol (write_text, read_text)
- Workspace boundary + path traversal denial
- `RustChokepointClient` Python client
- `ChokepointResult`, `ChokepointUnavailableError`, `ChokepointProtocolError`
- `examples/rust_chokepoint_spike.py`
- ADR-024

### Notes

- Not a security sandbox
- Rust binary is optional spike; Python client gracefully handles missing binary
- Seccomp/namespace/container/sandbox not implemented

## v0.5.0-dev

### Added

- `DashboardObservationPlane` — read-only snapshot from audit + reconciliation + chokepoint
- `AuditSummary`, `ReconciliationSummary`, `ChokepointSummary`
- `DashboardBuilder`, `DashboardSnapshot`
- `render_text()` text report
- `examples/dashboard_observation.py`
- ADR-025

### Notes

- Dashboard is observation plane only; no control actions
- No web server, remote API, auth, or live updates

## v0.5.0-observation-preview

### Status

Observation Preview.

This release provides a read-only operational awareness layer for the Koguchi / Context-Aware Harness reference implementation. It is intended for architectural review, local experimentation, and observation of audit / reconciliation / chokepoint state.

It is not production-ready, not a security sandbox, and not a dashboard control plane.

### Consolidated

- ToolProxy as the single side-effect chokepoint
- PolicyGate / RuntimeBoundary / ServiceRuntime responsibility separation
- JSONL persistent audit records
- Schema-level deferred reconciliation
- Optional Rust external chokepoint candidate
- Read-only dashboard observation plane

### Quality

- ruff: All checks passed
- pytest: 161 passed
- mypy: Success, 22 source files
- Rust: 5 tests passed
- examples: all verified

### Deferred

- ServiceRuntime optional chokepoint backend integration
- Persistent Reconciliation Result Store
- Dashboard Static HTML Report
- remote API server
- dashboard control plane
- production hardening
- full OS/container-level sandboxing

## v0.8.0-review-preview

### Status

Review Preview.

This release provides a static, read-only HTML review artifact for the Koguchi / Context-Aware Harness reference implementation. It is not production-ready, not a security sandbox, not a security proof, not a compliance certification, and not a dashboard control plane.

### Added

- Dashboard Static HTML Report
- `render_html_report`, `HtmlReportOptions`, HTML escaping
- Static HTML report: Audit / Reconciliation / Backend / Chokepoint / Limitations sections
- No form / no button / no script in output
- ADR-028

### Consolidated

- v0.1-v0.8 full architecture
- Execution → Audit → Reconciliation → Result → Dashboard → HTML Report closed loop
- 186 tests, 25 source files, 28 ADRs

### Deferred

- Backend-specific reconciliation
- Rust chokepoint protocol stabilization
- Web dashboard server / remote API / dashboard control plane
- Cryptographic sealing / production hardening / full sandbox

## Unreleased

### Added

- `docs/release/v0.10-backend-reconciliation-design-gate.md` — backend-specific reconciliation design gate (no implementation)
- `docs/examples/filesystem_diff_reconciliation.md` — filesystem diff reconciliation example design (no implementation)
- `src/koguchi/reconciliation/filesystem_diff.py` — read-only filesystem diff reconciliation spike
- `docs/release/v0.10-filesystem-reconciliation-spike-closure.md` — v0.10 spike closure note
- `docs/release/v0.11-toolproxy-reconciliation-design-gate.md` — ToolProxy reconciliation integration design gate
- `src/koguchi/toolproxy/reconciliation.py` — ToolProxy-facing read-only reconciliation spike
- `docs/release/v0.11-toolproxy-reconciliation-spike-closure.md` — v0.11 spike closure note
- `docs/release/v0.12-scheduler-reconciliation-design-gate.md` — Scheduler reconciliation design gate
- `docs/release/v0.12-scheduler-reconciliation-spike-closure.md` — v0.12 spike closure note
- `docs/release/v0.13-reconciliation-persistence-design-gate.md` — reconciliation persistence design gate
- `docs/release/v0.13-reconciliation-persistence-spike-closure.md` — v0.13 spike closure note
- `docs/release/v0.14-cli-readonly-inspection-design-gate.md` — CLI read-only inspection design gate
- `docs/release/v0.14-cli-readonly-inspection-spike-closure.md` — v0.14 spike closure note
- `docs/release/v0.15-reconciliation-framework-consolidation.md` — v0.15 reconciliation framework consolidation
