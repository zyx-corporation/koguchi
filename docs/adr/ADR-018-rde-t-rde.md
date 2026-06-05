# ADR-018: Phase 7 — RDE / T-RDE Integration

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 背景

Koguchi は Phase 6 までで、外部副作用の実行・判断・policy・reconciliation・redaction を扱える最小 CAH 基盤になった。しかし、副作用が「成功したか」だけでなく、元の意図からどのような意味変化が起きたかを監査する仕組みがない。

本 ADR は、RDE（Resonant Deviation Evaluator）および T-RDE（Test-level RDE）の基盤を追加する。

---

## 決定 A: RDE は自動裁定器ではない

この Phase では、LLM や rule engine による自動良否判定は実装しない。実装するのは、意味変化を記録・テスト・レビューしやすくする構造である。

RDE を PolicyGate に直結しない。RDE は意味変化の監査であり、実行前拒否の policy とは別層である。

---

## 決定 B: ΔM は価値そのものではない

ΔM は意味変化の測度または候補であり、価値そのものではない。RDE は、生成物や外部副作用が元の意図からどう変化したかを分類するための監査構造である。

---

## 決定 C: RdeHint / RdeReview schema

```python
class RdeCategory(StrEnum):
    PRESERVED = "preserved"
    TRANSFORMED = "transformed"
    SUPPLEMENTED = "supplemented"
    UNRESOLVED = "unresolved"
    RISK = "risk"
    NEXT_POLICY = "next_policy"

class RdeHint(BaseModel):
    preserved: list[str] = []
    transformed: list[str] = []
    supplemented: list[str] = []
    unresolved: list[str] = []
    risks: list[str] = []
    next_policy: str | None = None

class RdeReview(BaseModel):
    review_id: str
    action_id: str
    hint: RdeHint
    reviewer: str | None = None
    automated: bool = False
```

---

## 決定 D: RDE Store は Phase 7.B に延期

RdeReviewStore は今回実装しない。まず schema + T-RDE helper + docs を整備する。永続化は次のサブフェーズで行う。

---

## 決定 E: ExecutionEvent に rde_ref を追加

```python
rde_ref: str | None = None  # RdeReview.review_id への参照
```

Phase 7.A では空フックとして追加する。RdeReviewStore 実装時に接続する。

---

## 決定 F: RDE metadata は redaction 対象

RDE hint には元意図やリスクが自然言語で入る。したがって RDE metadata も監査ログと同じく debug note ではなく、公開 export では redaction 対象にする。

---

## 意図的に延ばす論点

- 自動評価器 / LLM judge
- RDE score の数値化
- RDE ReviewStore
- UI / dashboard
- RDE を PolicyGate の deny 条件にすること

---

## 参照

- [ADR-001](ADR-001-development-method.md) — SLS + RDE 開発手法
- [docs/roadmap.md](../roadmap.md) §11 — Phase 7 RDE / T-RDE
