# Example Index

Koguchi の全 example 一覧。各 example は設計理解の入口であり、production-ready ではない。

## 読み順（推奨）

1. [minimal_tool_proxy](#minimal_tool_proxy) — 最小の Chokepoint 体験
2. [persistent_audit_store](#persistent_audit_store) — Audit 永続化
3. [reconciliation_scheduler](#reconciliation_scheduler) — 後続検証
4. [rust_chokepoint_spike](#rust_chokepoint_spike) — 外部 enforcement 候補
5. [dashboard_observation](#dashboard_observation) — 状態の可視化
6. [serviceruntime_chokepoint_backend](#serviceruntime_chokepoint_backend) — Backend 統合
7. [dashboard_static_html_report](#dashboard_static_html_report) — Static HTML 成果物

---

## minimal_tool_proxy

**目的**: ToolProxy による副作用の単一隘路を最小構成で体験する。

**関連設計要素**: ToolProxy, PolicyGate, ServiceRuntime, RuntimeBoundary

```bash
PYTHONPATH=src python examples/minimal_tool_proxy.py
```

**期待出力**: ALLOW / DENY / Audit Events

**注意**: Koguchi は security sandbox ではない。この example は design pattern のデモである。

---

## persistent_audit_store

**目的**: JsonlAuditEventSink による AuditEvent の永続化を体験する。

**関連設計要素**: AuditEvent, JsonlAuditEventSink, ServiceRuntime

```bash
PYTHONPATH=src python examples/persistent_audit_store.py
```

**期待出力**: ALLOW / DENY の event が JSONL に保存され、読み戻される。

**注意**: JSONL は暗号学的に封印されていない。arguments / env は保存されない。

---

## reconciliation_scheduler

**目的**: 永続 audit event からの Reconciliation job 生成と実行を体験する。

**関連設計要素**: ReconciliationScheduler, ReconciliationJob, JsonlAuditEventSink

```bash
PYTHONPATH=src python examples/reconciliation_scheduler.py
```

**期待出力**: plan → run → summary。deny event は skipped。

**注意**: v0.3 は schema-level verification のみ。filesystem diff や自動修復は行わない。

---

## rust_chokepoint_spike

**目的**: Rust chokepoint binary を外部 enforcement candidate として体験する。

**関連設計要素**: RustChokepointClient, koguchi-chokepoint binary

```bash
cargo build --manifest-path crates/koguchi-chokepoint/Cargo.toml
PYTHONPATH=src python examples/rust_chokepoint_spike.py
```

**期待出力**: write_text / read_text / path traversal denial。

**注意**: Rust binary が存在しない場合は graceful skip。Rust chokepoint は optional spike であり、production sandbox ではない。

---

## dashboard_observation

**目的**: DashboardSnapshot による audit / reconciliation / chokepoint 状態の可視化を体験する。

**関連設計要素**: DashboardBuilder, DashboardSnapshot, render_text

```bash
PYTHONPATH=src python examples/dashboard_observation.py
```

**期待出力**: テキスト形式の Dashboard Snapshot。

**注意**: Dashboard は observation plane であり、control plane ではない。tool 実行・承認・再実行は行わない。

---

## serviceruntime_chokepoint_backend

**目的**: Rust chokepoint を ServiceRuntime の optional backend として統合する。

**関連設計要素**: ServiceRuntime, ExecutionBackend, RustChokepointExecutionBackend

```bash
cargo build --manifest-path crates/koguchi-chokepoint/Cargo.toml
PYTHONPATH=src python examples/serviceruntime_chokepoint_backend.py
```

**期待出力**: filesystem.write/read via Rust backend。shell.execute は RuntimeBoundary deny。

**注意**: Rust backend は explicit opt-in。既定 backend は Python。RuntimeBoundary は backend の前に評価される。

---

## dashboard_static_html_report

**目的**: DashboardSnapshot から read-only static HTML report を生成する。

**関連設計要素**: DashboardBuilder, render_html_report, HtmlReportOptions

```bash
PYTHONPATH=src python examples/dashboard_static_html_report.py
```

**期待出力**: `/tmp/koguchi-dashboard-report.html`。

**注意**: HTML report は read-only review artifact。form / button / script を含まない。control plane / security proof / compliance certification ではない。
