# ADR-011: DecisionStore の hash chain 化

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |
| **Closes** | ADR-004 延ばした論点「DecisionStore の hash chain 化」|

---

## 背景

ExecutionStore は各 `ExecutionEvent` に `previous_hash` と `hash` を持ち、`verify_chain()` で改竄・ロストを検出できる。一方、DecisionStore は単純な append-only であり、Decision レコードの改竄検出機能がない。

DecisionStore は意思決定の来歴を保持する監査上重要な層であり、ExecutionStore と同等の改竄耐性を持つべきである。

---

## 決定 A: 独立した hash chain

**DecisionStore に ExecutionStore と独立した hash chain を導入する。**

```python
class Decision(BaseModel):
    decision_id: str
    action_id: str
    intent: str
    context_snapshot: dict[str, object] | None = None
    timestamp: datetime
    previous_hash: str       # 新規
    hash: str                # 新規
```

### `GENESIS_HASH` の共有

ExecutionStore と同じ `"0" * 64` を genesis として使う。

### `verify_chain()` 

ExecutionStore と同じパターンで実装する：
- `previous_hash` の連鎖検証
- 保存ペイロードからの hash 再計算

---

## 決定 B: 二重管理ではない理由

ExecutionStore の chain と DecisionStore の chain は異なる来歴層の完全性を保証する。一方が破壊されても他方で検出できる構造は、むしろ冗長性として監査上有益である。

---

## 影響

| ファイル | 変更内容 |
| --- | --- |
| `src/koguchi/decision.py` | `Decision` に `previous_hash`, `hash` 追加。`SQLiteDecisionStore.verify_chain()` 追加 |
| `src/koguchi/proxy.py` | `_prepare_execution` で Decision 作成時に `previous_hash` を取得 |
| `tests/test_decision_chain.py`（新規） | verify_chain 正常・改竄検出テスト |

---

## 参照

- [ADR-002](ADR-002-phase1-side-effect-chokepoint.md) — ExecutionStore の hash chain
- [ADR-004](ADR-004-decision-logger-phase2.md) — DecisionStore の延期判断
