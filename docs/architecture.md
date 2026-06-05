# Architecture Overview

Koguchi / CAH の全体構造と責務分離。

## Koguchi / CAH の目的

AIエージェントやアプリケーションが外部世界へ副作用を起こすとき、その副作用を監査可能な実行来歴へ変換する。

## 全体構造

### 実行経路（Execution Path）

```mermaid
flowchart TD
  A["Caller"] --> B["ToolProxy"]
  B --> C["PolicyGate"]
  B --> I["ExecutionStore"]
  B --> J["DecisionStore"]
  C --> D["ServiceRuntime"]
  D --> E["RuntimeBoundary"]
  E --> F["ExecutionBackend"]
  F --> G["PythonExecutionBackend"]
  F --> H["RustChokepointExecutionBackend"]
  D --> K["AuditEventSink"]
```

ToolProxy が副作用の単一隘路。PolicyGate が envelope/policy 判定。RuntimeBoundary が実行時境界判定。ServiceRuntime が accountable execution surface。ExecutionBackend が具体的な実行先（Python 既定 / Rust opt-in）。

### 観測経路（Observation Path）

```mermaid
flowchart TD
  A["Persistent Audit Store"] --> D["DashboardBuilder"]
  B["Persistent Result Store"] --> D
  C["Rust Chokepoint Availability"] --> D
  D --> E["DashboardSnapshot"]
  E --> F["Text Report"]
  E --> G["Static HTML Report"]
```

Dashboard は observation plane であり control plane ではない。tool 実行・承認・再実行・修復は行わない。Static HTML Report は read-only review artifact である。

## 責務分離

### ToolProxy

Caller から見た唯一の副作用実行経路。PolicyGate と ServiceRuntime を接続する。すべての管理対象副作用は必ず ToolProxy を通る。

### PolicyGate

envelope / policy 上の許可判定を行う。判定結果は allow / deny / require_approval の3値。PolicyGate は RuntimeBoundary を置き換えない。

### RuntimeBoundary

tool / env / workspace / runtime 上の実行時境界を判定する。Python 実装は best-effort であり完全封じ込めではない。Rust chokepoint や OS レベル隔離に差し替え可能な Protocol として設計されている。

### ServiceRuntime

RuntimeBoundary 判定、tool execution、audit event emission を束ねる accountable execution surface。権限主体ではなく観測可能な実行面である。v0.6 以降、ExecutionBackend を optional inject 可能。

### ExecutionBackend

ServiceRuntime の optional execution backend abstraction。既定は PythonExecutionBackend。RustChokepointExecutionBackend は explicit opt-in。filesystem.write/read のみ対応。

### AuditGate

アプリケーションが依存する唯一の Koguchi インターフェース。内部実装（ActionEnvelope, ExecutionStore, hash chain）を隠蔽する。

### Reconciliation

Store と実世界（ファイルシステム／外部 API）の照合。診断は最尤推定であり、確定的真実ではない。confidence 値で推定の確からしさを表現する。

### Redaction / Secret Safety

監査ログの開示制御。RedactionPolicy は full / without_intent / without_context / minimal の4分類。FULL でも secret-like key は常にマスクされる。

### RDE / T-RDE

RDE（Resonant Deviation Evaluator）は、生成された変更が元の設計意図を保存しているのか、許可された変換なのか、補完なのか、あるいは逸脱なのかを評価するための構造である。

T-RDE はこの考え方をテストに適用する。RDE は PolicyGate の代替でも security sandbox でもない。

### Dashboard Observation Plane

read-only な operational awareness 層。DashboardSnapshot は JSON serializable。render_text と render_html_report で人間が読める形に変換する。control plane ではない。

## 現時点で実装していないもの

- backend-specific reconciliation（ファイルシステム diff）
- Rust chokepoint protocol stabilization
- Web dashboard server / remote API
- seccomp / container isolation / network namespace / macOS sandbox
- cryptographic audit sealing

## 参照

- [ADR index](adr/) — 設計判断の正本
- [Known Limitations](../known-limitations.md) — 現状の制約
- [Roadmap](../roadmap.md) — 全体フェーズ計画
- [Example Index](../examples/) — 全 example 一覧
