# ADR-023: Reconciliation Scheduler

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 背景

v0.2 では ServiceRuntime の audit events が JSONL に永続化され、durable accountability record となった。しかし audit record が保存されるだけでは、どの実行をいつ検証するか、どの検証が完了したかを追跡できない。

CAH の目的は副作用を単に記録することではなく、実行後に差分を検査し逸脱を検出できる構造を作ることである。

---

## 決定

Koguchi は `ReconciliationScheduler` を導入する。Scheduler は persistent audit store から audit events を読み取り、reconciliation job を生成する。各 job は状態を持ち、manual/in-process trigger により実行される。

v0.3 では schema-level deferred verification に限定し、自動修復やロールバックは行わない。

### Job ID

`reconcile:{request_id}` — deterministic にし、重複生成を防ぐ。

### Event selection

- `allowed=true` → job 作成
- `allowed=false` → skipped
- `error != null` → skipped

### Status transition

```
pending → running → passed
pending → running → failed
pending → skipped
```

---

## Non-goals

- 自動修復 / 自動ロールバック
- daemon / cron / background worker
- tool-specific filesystem diff
- LLM judge
- dashboard / remote API
- persistent reconciliation result store

---

## 参照

- [ADR-022](ADR-022-persistent-audit-store.md) — Persistent Audit Store
- [ADR-021](ADR-021-service-runtime.md) — Service Runtime
