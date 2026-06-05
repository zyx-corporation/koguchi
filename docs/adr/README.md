# Architecture Decision Records

Koguchi の設計判断を append-only で記録する。変更時は既存 ADR を上書きせず、新 ADR で supersede する。

| ADR | タイトル | Status |
| --- | --- | --- |
| [ADR-001](ADR-001-development-method.md) | SLS + RDE に基づく開発手法の採用 | Accepted |
| [ADR-002](ADR-002-phase1-side-effect-chokepoint.md) | Phase 1 — Side-Effect Chokepoint 設計判断の記録 | Accepted |
| [ADR-003](ADR-003-mkdir-scope-and-envelope-semantics.md) | Phase 1 スコープ確定 — 親ディレクトリ作成と Envelope 意味論 | Accepted |
| [ADR-004](ADR-004-decision-logger-phase2.md) | Phase 2 — Decision Logger と縮退防止フックの実装 | Accepted |
| [ADR-005](ADR-005-non-atomic-shell-execute.md) | Phase 2.B — 非 atomic ツール対応（`shell.execute`）| Accepted |
| [ADR-006](ADR-006-i18n-multilingual-messages.md) | i18n 対応 — 多言語メッセージとコーディング規約 | Accepted |
| [ADR-007](ADR-007-quality-infrastructure.md) | 品質基盤 — ruff + mypy による静的解析と型チェック | Accepted |
| [ADR-008](ADR-008-filesystem-mkdir.md) | Phase 2.D — `filesystem.mkdir` の独立実装 | Accepted |
| [ADR-009](ADR-009-network-http-partial.md) | Phase 3 — ネットワークツールと `partial` の意味論確定 | Accepted |
| [ADR-010](ADR-010-context-resolver.md) | Phase 3 — Context Resolver（コンテキスト自動キャプチャ）| Accepted |
| [ADR-011](ADR-011-decision-hash-chain.md) | DecisionStore の hash chain 化 | Accepted |
| [ADR-012](ADR-012-policy-gate.md) | Policy Gate — 監査開示制御と `redaction_policy` | Accepted |
| [ADR-013](ADR-013-reconcile-tool-specific.md) | reconcile — ツールタイプ別 pending 診断ロジック | Accepted |
| [ADR-014](ADR-014-policy-gate-execution.md) | Phase 3 — Policy Gate（実行前許可判定）| Accepted |
| [ADR-015](ADR-015-audit-gate.md) | Phase 4 — AuditGate Protocol と KoguchiAuditGate | Accepted |
| [ADR-016](ADR-016-reconciliation-v2.md) | Phase 5 — Reconciliation v2（外部 API 照合）| Accepted |
