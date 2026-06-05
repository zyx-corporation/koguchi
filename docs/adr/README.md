# Architecture Decision Records

Koguchi の設計判断を append-only で記録する。変更時は既存 ADR を上書きせず、新 ADR で supersede する。

| ADR | Title | Phase | Status | Summary |
| --- | --- | --- | --- | --- |
| [001](ADR-001-development-method.md) | SLS + RDE に基づく開発手法の採用 | 0 | Accepted | 開発プロセスの規範。七つの観測カテゴリ、ADR 正本化、テストを不変条件の証拠に |
| [002](ADR-002-phase1-side-effect-chokepoint.md) | Phase 1 — Side-Effect Chokepoint 設計判断の記録 | 1 | Accepted | INV-1/1a/1b/1c 四点セット、三層分離、atomic write、hash chain、縮退防止フック |
| [003](ADR-003-mkdir-scope-and-envelope-semantics.md) | Phase 1 スコープ確定 — 親ディレクトリ作成と Envelope 意味論 | 1 | Accepted | mkdir 除去、envelope=None は例外、親 dir なしは REJECTED |
| [004](ADR-004-decision-logger-phase2.md) | Phase 2 — Decision Logger と縮退防止フックの実装 | 2 | Accepted | Decision, DecisionStore, intent/decision_ref/context_ref の接続 |
| [005](ADR-005-non-atomic-shell-execute.md) | Phase 2.B — 非 atomic ツール対応（`shell.execute`）| 2 | Accepted | shell.execute, side_effect_observed=unknown, partial の延期 |
| [006](ADR-006-i18n-multilingual-messages.md) | i18n 対応 — 多言語メッセージとコーディング規約 | 2 | Accepted | 三層言語ポリシー、JSON メッセージカタログ、ja/en/zh-CN/zh-TW/ko |
| [007](ADR-007-quality-infrastructure.md) | 品質基盤 — ruff + mypy による静的解析と型チェック | 2 | Accepted | ruff lint+format、mypy strict、CI 品質ゲート |
| [008](ADR-008-filesystem-mkdir.md) | Phase 2.D — `filesystem.mkdir` の独立実装 | 2 | Accepted | mkdir の独立副作用管理、exist_ok=True で冪等 |
| [009](ADR-009-network-http-partial.md) | Phase 3 — ネットワークツールと `partial` の意味論 | 3 | Accepted | network.http_get, IncompleteRead→partial, 全4値生成可能に |
| [010](ADR-010-context-resolver.md) | Phase 3 — Context Resolver（コンテキスト自動キャプチャ）| 3 | Accepted | ContextResolver Protocol, SystemContextResolver, 自動キャプチャ |
| [011](ADR-011-decision-hash-chain.md) | DecisionStore の hash chain 化 | 3 | Accepted | Decision に previous_hash/hash 追加、verify_chain() |
| [012](ADR-012-policy-gate.md) | Policy Gate — 監査開示制御と `redaction_policy` | 6 | Accepted | RedactionPolicy (full/without_intent/without_context/minimal), 墨消し |
| [013](ADR-013-reconcile-tool-specific.md) | reconcile — ツールタイプ別 pending 診断ロジック | 5 | Accepted | filesystem/shell/network のツールタイプ分岐、confidence 調整 |
| [014](ADR-014-policy-gate-execution.md) | Phase 3 — Policy Gate（実行前許可判定）| 3 | Accepted | PolicyDecision (allow/deny/require_approval), PolicyRule, ExecutionPolicyGate |
| [015](ADR-015-audit-gate.md) | Phase 4 — AuditGate Protocol と KoguchiAuditGate | 4 | Accepted | AuditGate Protocol, KoguchiAuditGate, アプリ抽象化層 |
| [016](ADR-016-reconciliation-v2.md) | Phase 5 — Reconciliation v2（外部 API 実状態との照合）| 5 | Accepted | ReconciliableProvider, ProviderReconciler, Provider 照合フレームワーク |
