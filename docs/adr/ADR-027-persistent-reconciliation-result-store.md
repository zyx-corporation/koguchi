# ADR-027: Persistent Reconciliation Result Store

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 背景

v0.3 で ReconciliationScheduler が導入されたが ReconciliationResult は永続化されていない。実行記録だけでなく後続検証の結果も記録される必要がある。

---

## 決定

Koguchi は v0.7 で `JsonlReconciliationResultStore` を導入する。各 ReconciliationResult は JSONL 形式で append-only に保存される。audit log とは別ファイルとする。

保存 record: schema_version, result_id, job_id, request_id, status, message, error, checked_at, source_event_backend。

raw source_event, arguments, env, secrets は保存しない。

---

## Non-goals

- 自動修復 / rollback / LLM judge / backend-specific diff / cryptographic sealing

---

## 参照

- [ADR-023](ADR-023-reconciliation-scheduler.md)
