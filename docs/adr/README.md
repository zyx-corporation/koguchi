# Architecture Decision Records

Koguchi の設計判断を append-only で記録する。変更時は既存 ADR を上書きせず、新 ADR で supersede する。

## 読み順

初見の開発者は以下の順で読むことを推奨する。

1. [001](ADR-001-development-method.md) — 開発手法の全体像
2. [002](ADR-002-phase1-side-effect-chokepoint.md) — Chokepoint 中核設計
3. [014](ADR-014-policy-gate-execution.md) — Policy Gate
4. [015](ADR-015-audit-gate.md) — AuditGate
5. [020](ADR-020-runtime-hardening.md) — Runtime Boundary
6. [021](ADR-021-service-runtime.md) — Service Runtime
7. [026](ADR-026-serviceruntime-chokepoint-backend.md) — Execution Backend
8. [025](ADR-025-dashboard-observation-plane.md) — Dashboard Observation Plane
9. [028](ADR-028-dashboard-static-html-report.md) — Static HTML Report
10. [027](ADR-027-persistent-reconciliation-result-store.md) — Persistent Result Store
11. その他は関心に応じて

## Foundation

| ADR | Title | Status | Summary |
| --- | --- | --- | --- |
| [001](ADR-001-development-method.md) | SLS + RDE に基づく開発手法の採用 | Accepted | 開発プロセス規範 |
| [002](ADR-002-phase1-side-effect-chokepoint.md) | Phase 1 — Side-Effect Chokepoint | Accepted | INV-1/1a/1b/1c, atomic write, hash chain |
| [003](ADR-003-mkdir-scope-and-envelope-semantics.md) | Phase 1 スコープ確定 | Accepted | mkdir 除去, envelope=None 意味論 |

## Side-Effect Chokepoint / Proxy

| ADR | Title | Status | Summary |
| --- | --- | --- | --- |
| [004](ADR-004-decision-logger-phase2.md) | Decision Logger | Accepted | Decision, DecisionStore, intent/decision_ref/context_ref |
| [005](ADR-005-non-atomic-shell-execute.md) | shell.execute | Accepted | 非atomic, side_effect_observed=unknown |
| [008](ADR-008-filesystem-mkdir.md) | filesystem.mkdir | Accepted | 独立副作用管理, exist_ok |
| [009](ADR-009-network-http-partial.md) | network.http_get + partial | Accepted | IncompleteRead→partial, 全4値生成 |
| [010](ADR-010-context-resolver.md) | Context Resolver | Accepted | 自動キャプチャ |
| [011](ADR-011-decision-hash-chain.md) | DecisionStore hash chain | Accepted | verify_chain |

## Policy / Approval

| ADR | Title | Status | Summary |
| --- | --- | --- | --- |
| [014](ADR-014-policy-gate-execution.md) | Policy Gate（実行前許可判定）| Accepted | PolicyDecision, PolicyRule, ExecutionPolicyGate |

## Audit / Logging

| ADR | Title | Status | Summary |
| --- | --- | --- | --- |
| [006](ADR-006-i18n-multilingual-messages.md) | i18n 多言語対応 | Accepted | ja/en/zh-CN/zh-TW/ko |
| [007](ADR-007-quality-infrastructure.md) | 品質基盤 | Accepted | ruff, mypy strict, CI |
| [015](ADR-015-audit-gate.md) | AuditGate | Accepted | Protocol, KoguchiAuditGate |

## Reconciliation

| ADR | Title | Status | Summary |
| --- | --- | --- | --- |
| [013](ADR-013-reconcile-tool-specific.md) | ツールタイプ別 reconcile | Accepted | filesystem/shell/network 分岐 |
| [016](ADR-016-reconciliation-v2.md) | Reconciliation v2 | Accepted | ReconciliableProvider, ProviderReconciler |

## Secret / Redaction

| ADR | Title | Status | Summary |
| --- | --- | --- | --- |
| [012](ADR-012-policy-gate.md) | RedactionPolicy | Accepted | full/without_intent/without_context/minimal |
| [017](ADR-017-redaction-secret-safety.md) | Redaction / Secret Safety | Accepted | secret guard, export API |

## RDE / T-RDE

| ADR | Title | Status | Summary |
| --- | --- | --- | --- |
| [018](ADR-018-rde-t-rde.md) | RDE / T-RDE | Accepted | RdeHint, RdeReview, T-RDE helpers |

## Runtime / Boundary

| ADR | Title | Status | Summary |
| --- | --- | --- | --- |
| [020](ADR-020-runtime-hardening.md) | Runtime Hardening | Accepted | RuntimeBoundary, DefaultRuntimeBoundary |
| [021](ADR-021-service-runtime.md) | Service Runtime | Accepted | ServiceRuntime, AuditEventSink |

## Audit Store

| ADR | Title | Status | Summary |
| --- | --- | --- | --- |
| [022](ADR-022-persistent-audit-store.md) | Persistent Audit Store | Accepted | JsonlAuditEventSink, JSONL append-only |
| [023](ADR-023-reconciliation-scheduler.md) | Reconciliation Scheduler | Accepted | ReconciliationScheduler, schema-level deferred verification |

## Rust Chokepoint

| ADR | Title | Status | Summary |
| --- | --- | --- | --- |
| [024](ADR-024-rust-chokepoint-spike.md) | Rust Chokepoint Spike | Accepted | Rust crate, JSON protocol, Python client |

## Integration

| ADR | Title | Status | Summary |
| --- | --- | --- | --- |
| [025](ADR-025-dashboard-observation-plane.md) | Dashboard Observation Plane | Accepted | DashboardSnapshot, read-only observation plane |
| [019](ADR-019-joujou-integration.md) | JouJou Integration | Accepted | KoguchiTodoAuditGate, UnconfirmedSideEffectError |
| [027](ADR-027-persistent-reconciliation-result-store.md) | Persistent Reconciliation Result Store | Accepted | JsonlReconciliationResultStore, JSONL append-only |
|[028](ADR-028-dashboard-static-html-report.md) | Dashboard Static HTML Report | Accepted | render_html_report, static review artifact |
