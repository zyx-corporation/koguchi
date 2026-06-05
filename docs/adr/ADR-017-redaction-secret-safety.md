# ADR-017: Phase 6 — Redaction / Secret Safety

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 背景

Koguchi の監査ログは debug log ではない。Todo本文、会話全文、intent、context_snapshot、Provider token、個人情報、機密情報を無制限に保存・表示・export してはならない。

Phase 6 の目的は、RedactionPolicy を実運用可能な形にし、安全な audit view / export を提供することである。

---

## 決定 A: RedactionPolicy の4分類と意味論

```python
class RedactionPolicy(StrEnum):
    FULL = "full"                   # デバッグ用途。原則 export 非推奨
    WITHOUT_CONTEXT = "without_context"  # 通常利用のデフォルト
    WITHOUT_INTENT = "without_intent"    # intent がセンシティブな場合
    MINIMAL = "minimal"             # 外部共有・サポート・公開用
```

| フィールド | FULL | WITHOUT_INTENT | WITHOUT_CONTEXT | MINIMAL |
|-----------|------|---------------|-----------------|---------|
| event_id, record_id, timestamp, event_type | ○ | ○ | ○ | ○ |
| side_effect_observed | ○ | ○ | ○ | ○ |
| result_digest, error_digest | ○ | ○ | ○ | ✕ |
| envelope | ○ | ○ | ○ | ✕ |
| intent | ○ | ✕ | ○ | ✕ |
| decision_ref, context_ref | ○ | ○ | ○ | ✕ |
| context_snapshot | ○ | ○ | ✕ | ✕ |
| previous_hash, hash | ○ | ○ | ○ | ✕ |
| **secret-like keys** | **✕** | **✕** | **✕** | **✕** |

secret-like keys は FULL でも表示してはならない。

---

## 決定 B: Secret-like key guard

key 名ベースで secret-like value を `[REDACTED]` に置換する。

```python
SECRET_PATTERNS = [
    "token", "secret", "api_key", "apikey", "authorization",
    "cookie", "password", "refresh_token", "access_token",
]
```

再帰的に `dict`/`list` を走査し、該当 key の value をマスクする。

---

## 決定 C: Export API

```python
def export_events(
    store: ExecutionStore,
    policy: RedactionPolicy,
) -> list[dict[str, object]]:
```

export は必ず `RedactionPolicy` を要求する。policy なしの export は提供しない。

---

## やらないこと

- 暗号化 Store
- 認可ロール管理（RBAC）
- 外部共有 UI
- PII 機械学習検出
- 監査ダッシュボード

---

## 参照

- [ADR-012](ADR-012-policy-gate.md) — 先行実装された RedactionPolicy
- [docs/roadmap.md](../roadmap.md) §10 — Phase 6 Redaction / Secret Safety
