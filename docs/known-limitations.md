# Known Limitations

## Not a security sandbox

The current implementation does not provide strong isolation.

## Python best-effort boundary

RuntimeBoundary can prevent ordinary tool execution paths but cannot prevent arbitrary Python-level escape in a hostile runtime.

## Deferred isolation mechanisms

- Rust chokepoint
- seccomp
- container isolation
- network namespace
- macOS sandbox

## Audit persistence

Audit events are currently in-memory unless a custom `AuditEventSink` is provided. Persistent audit store is deferred to v0.2.

## Dashboard

Dashboard support is observation-oriented only (`DashboardSnapshot`, `render_text`, `render_html_report`). Destructive control plane is not part of any v0.x release. The Static HTML Report is a read-only review artifact — it does not execute, approve, rerun, repair, or mutate.

## Remote API

Remote API server is not part of v0.1.

## Threat model

The current version assumes a cooperative or semi-trusted execution environment. Hostile code execution requires stronger isolation than v0.1 provides.

## Reconciliation

Reconciliation is snapshot-based. It cannot distinguish between "side effect never happened" and "side effect happened then was externally reverted." Confidence values represent estimation, not probability.

## Audit log integrity

v0.2 persistent audit logs are append-oriented JSONL files. They are not cryptographically sealed and do not prevent local tampering.

## Concurrent writes

v0.2 JSONL audit store is intended for local single-process use. Multi-process write coordination is deferred.

## Reconciliation scope

v0.3 reconciliation is schema-level deferred verification. v0.10 contains a read-only filesystem diff reconciliation spike (`koguchi/reconciliation/filesystem_diff.py`). v0.11 defines a ToolProxy integration design gate for reconciliation (`docs/release/v0.11-toolproxy-reconciliation-design-gate.md`). Production backend-specific reconciliation, Scheduler integration, ToolProxy reconciliation integration, AuditStore/ResultStore persistence, automatic repair, and rollback remain unimplemented.

## Rust chokepoint spike

The v0.4 Rust chokepoint is an experimental external enforcement candidate. It does not provide seccomp, namespace isolation, container isolation, macOS sandboxing, or production-grade security hardening.

## Dashboard scope

v0.5 dashboard support is read-only and local-first. It does not provide a web server, remote API, authentication, live updates, destructive controls, or production monitoring.

## Dashboard scope

v0.5 Dashboard Observation Plane is read-only and local-first.

It does not provide:

- web server
- remote API
- authentication
- live updates
- approval controls
- tool execution
- job rerun
- repair / rollback
- audit log mutation
- production monitoring

## Static HTML report

v0.8 Static HTML Report is read-only and local.

It does not provide:
- web server, remote API, authentication, live updates
- approval controls, tool execution, job rerun
- repair / rollback, audit/result mutation
- Rust chokepoint execution
- security proof, compliance certification, production monitoring
