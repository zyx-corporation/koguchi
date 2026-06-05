# Reconciliation v2

外部 API 実状態との照合フレームワーク。

## 概念

Phase 1 の `reconcile()` は、Store と workspace（ファイルシステム）を照合する。
Reconciliation v2 は、Store と外部 API（GitHub Issues、Notion Pages、Google Tasks 等）を照合する。

## なぜ必要か

外部 API への副作用が `UNCONFIRMED` や `pending` のまま残った場合、
ファイルシステム照合では検証できない。外部 API の実状態と突合する必要がある。

## Reconciliation は確定ではなく最尤推定である

- 診断は snapshot 照合であり、副作用時点と照合時点の間の第三者変更を区別できない
- `confidence` は推定の確からしさを表し、確率ではない
- 外部 API 側のログと突合することで精度を上げられる

## ReconciliableProvider Protocol

```python
from koguchi import ReconciliableProvider

class GitHubProvider(ReconciliableProvider):
    def find_by_audit_record_id(self, record_id: str) -> dict | None:
        # GitHub Issues を audit marker で検索
        ...

    def exists(self, external_id: str) -> bool:
        # Issue が存在するか
        ...
```

## ProviderReconciler

```python
from koguchi import ProviderReconciler

reconciler = ProviderReconciler(store, provider)
findings = reconciler.reconcile()

for f in findings:
    # f.diagnosis: pending_executed_unconfirmed / pending_not_executed
    # f.confidence: 0.60〜0.80
    # f.detail: provider returned ...
```

## JouJou 例: GitHub Issue 作成の UNCONFIRMED

```text
1. pending のまま残った todo.create record を取得
2. GitHub Issues API で audit marker / title / external_id を検索
3. 見つかれば pending_executed_unconfirmed（confidence 0.80）
4. 見つからなければ pending_not_executed（confidence 0.60）
5. 既存 committed と外部状態が食い違えば committed_diverged
```

## ファイルシステム照合との使い分け

| 照合対象 | 使用関数 | 対象ツール |
|----------|---------|-----------|
| ファイルシステム | `reconcile()` | filesystem.write, filesystem.mkdir |
| 外部 API | `ProviderReconciler.reconcile()` | shell.execute, network.http_get, todo.create |

## 次のステップ

- [AuditGate Integration](auditgate-integration.md) — アプリケーションへの組み込み
- [Getting Started](getting-started.md) — Koguchi の基本使い方
- [ADR-016](../adr/ADR-016-reconciliation-v2.md) — Reconciliation v2 の設計判断
