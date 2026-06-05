# ADR-016: Phase 5 — Reconciliation v2（外部 API 実状態との照合）

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 背景

Phase 1 の reconciliation は、Store と workspace（ファイルシステム）の照合に限定されている。しかし Koguchi の監査対象はファイルシステムだけでなく、GitHub Issues、Notion Pages、Google Tasks 等の外部 API への副作用も含む（Phase 8）。

外部 API の副作用が `UNCONFIRMED` や `pending` のまま残った場合、外部 API の実状態と照合する必要がある。本 ADR は、Provider ごとの reconciliation strategy を定義するフレームワークを導入する。

---

## 決定 A: `ReconciliableProvider` Protocol

```python
class ReconciliableProvider(Protocol):
    def find_by_audit_record_id(self, record_id: str) -> dict | None:
        """audit record_id から外部リソースを検索する。"""
        ...

    def exists(self, external_id: str) -> bool:
        """外部リソースが存在するか。"""
        ...
```

### 使用フロー

```
pending のままの外部 API 作成 record がある
  ↓
Provider.find_by_audit_record_id(record_id) を呼ぶ
  ↓
見つかれば pending_executed_unconfirmed
  ↓
見つからなければ pending_not_executed
```

---

## 決定 B: `ProviderReconciler`

```python
class ProviderReconciler:
    def __init__(self, store: ExecutionStore, provider: ReconciliableProvider): ...

    def reconcile(self) -> list[ReconciliationFinding]:
        """pending event を Provider 経由で照合する。"""
```

`reconcile.py` の `reconcile()` 関数とは別のレイヤとして実装する。`reconcile()` はファイルシステム照合、`ProviderReconciler` は外部 API 照合。

---

## 影響

| ファイル | 変更内容 |
| --- | --- |
| `src/koguchi/provider_reconcile.py`（新規） | `ReconciliableProvider`, `ProviderReconciler` |
| `tests/test_provider_reconcile.py`（新規） | Mock Provider を使った照合テスト |

---

## 参照

- [docs/roadmap.md](../roadmap.md) §9 — Phase 5 Reconciliation v2
- [ADR-002](ADR-002-phase1-side-effect-chokepoint.md) — Phase 1 reconciliation
