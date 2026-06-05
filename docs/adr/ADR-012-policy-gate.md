# ADR-012: Policy Gate — 監査開示制御と `redaction_policy`

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |
| **Closes** | ADR-004 延ばした論点「`redaction_policy` の意味論と実装」|

---

## 背景

`ActionEnvelope.redaction_policy` は Phase 1 から空フックとして存在していた。Decision Logger（Phase 2）により `intent` / `decision_ref` / `context_ref` が埋まり、監査ログに意思情報が含まれるようになった。しかし、これらの情報を誰に開示するかの制御機構がない。

Policy Gate は、監査ログの開示範囲を `redaction_policy` に基づいて制御する層である。

---

## 決定 A: `RedactionPolicy` の定義

```python
class RedactionPolicy(StrEnum):
    FULL = "full"                   # 全フィールド開示
    WITHOUT_INTENT = "without_intent"   # intent をマスク
    WITHOUT_CONTEXT = "without_context" # context_snapshot を除去
    MINIMAL = "minimal"             # 最小限（事実のみ）
```

### マスクルール

| フィールド | FULL | WITHOUT_INTENT | WITHOUT_CONTEXT | MINIMAL |
|-----------|------|---------------|-----------------|---------|
| event_id, record_id, timestamp, event_type | ○ | ○ | ○ | ○ |
| side_effect_observed | ○ | ○ | ○ | ○ |
| result_digest, error_digest | ○ | ○ | ○ | ✕ |
| envelope | ○ | ○ | ○ | ✕ |
| intent | ○ | ✕ | ○ | ✕ |
| decision_ref, context_ref | ○ | ○ | ○ | ✕ |
| context_snapshot (Decision) | ○ | ○ | ✕ | ✕ |
| confidence, previous_hash, hash | ○ | ○ | ○ | ✕ |

---

## 決定 B: `PolicyGate` ユーティリティ

**`koguchi.policy` モジュールとして、`redact_event()` / `redact_decision()` を提供する。**

```python
from koguchi.policy import PolicyGate

redacted = PolicyGate.redact_event(event, policy)
```

### 理由

- Policy Gate は副作用の実行経路ではなく、監査ログの**表示層**である。したがって ToolProxy の責務ではなく、独立したユーティリティとして実装する。
- `redaction_policy` は `ActionEnvelope` に保存され、監査時に参照される。実行時には関与しない。

---

## 影響

| ファイル | 変更内容 |
| --- | --- |
| `src/koguchi/policy.py`（新規） | `RedactionPolicy` + `PolicyGate.redact_event()` / `redact_decision()` |
| `src/koguchi/__init__.py` | 新規 export 追加 |
| `tests/test_policy_gate.py`（新規） | 各ポリシーのマスク範囲テスト |

---

## 参照

- [ADR-004](ADR-004-decision-logger-phase2.md) — `redaction_policy` の延期判断
- `src/koguchi/envelope.py` — `ActionEnvelope.redaction_policy`
