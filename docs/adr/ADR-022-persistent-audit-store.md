# ADR-022: Persistent Audit Store

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 背景

v0.1.0-dev-preview では、ServiceRuntime が `AuditEvent` を生成し `AuditEventSink` に流す構造が導入された。しかし `InMemoryAuditEventSink` はプロセス終了時に失われるため、後続の検証、reconciliation、外部レビューには不十分である。

CAH の目的は、tool execution の副作用を説明可能な経路に閉じ込めることである。そのためには runtime observation を durable accountability record へ変換する必要がある。

---

## 決定

Koguchi は `PersistentAuditEventSink` の実装として `JsonlAuditEventSink` を導入する。各 `AuditEvent` は JSON Lines 形式で append-only に保存される。

保存 record には `schema_version` を含め、将来の互換性を確保する。保存前には allowlist 方式で安全なフィールドのみ抽出する（arguments, env は保存しない）。

---

## JSONL Schema

```json
{
  "schema_version": 1,
  "event_type": "allow",
  "request_id": "...",
  "tool_name": "...",
  "allowed": true,
  "reason": null,
  "workspace": "/tmp",
  "timestamp": "2026-06-05T00:00:00+00:00",
  "error": null
}
```

---

## Non-goals

- SQLite audit sink（v0.2.1 以降）
- 暗号学的改ざん検出
- 分散監査ログ
- dashboard control plane
- remote query API

---

## Consequences

永続 audit store により実行履歴を後から検証可能になる。保存先ファイル自体のアクセス制御、改ざん耐性、保持期間は別途扱う。

---

## 参照

- [ADR-021](ADR-021-service-runtime.md) — Service Runtime
