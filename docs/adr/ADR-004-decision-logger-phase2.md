# ADR-004: Phase 2 — Decision Logger と縮退防止フックの実装

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |
| **Closes** | ADR-002 次回更新方針「Phase 2（Decision Logger）着手時」 |

---

## 背景

ADR-002 で Phase 1 実装時に `ExecutionEvent` へ三つの縮退防止フックを空のまま埋め込んだ：

| フィールド | 意図 | Phase 1 の状態 |
| --- | --- | --- |
| `intent` | なぜこの副作用を起こすのか（意思の記録） | `None` |
| `decision_ref` | Decision Logger が発行する意思決定 ID への参照 | `None` |
| `context_ref` | Context Resolver がキャプチャした判断時点のコンテキスト参照 | `None` |

加えて `ActionEnvelope.redaction_policy` も「器だけ（Phase 2 以降）」として空欄のままである。

これらの空フックは意図的な設計判断であり、「安全な Tool Runtime」——ツールを単に呼び出して結果を返すだけの系——への縮退を防ぐための仕掛けである。Phase 2 では、Decision Logger を実装しこれらのフックを埋める。

---

## 決定 A: Decision モデルと DecisionStore の分離

**副作用の実行記録（ExecutionStore）と意思決定の記録（DecisionStore）は異なる来歴層であり、別の Store として分離する。**

### Decision モデル

```python
class Decision(BaseModel):
    decision_id: str
    action_id: str              # ActionEnvelope.action_id と一致
    intent: str                 # 自然言語による意思の記述
    context_snapshot: Optional[dict] = None  # 判断時点のコンテキスト（Context Resolver 由来）
    timestamp: datetime
```

### DecisionStore Protocol

```python
class DecisionStore(Protocol):
    def record(self, decision: Decision) -> None: ...
    def get(self, action_id: str) -> Decision | None: ...
```

### SQLiteDecisionStore

`ExecutionStore` と同じ SQLite ファイルを共有する別テーブルとして実装する。append-only の性質は ExecutionStore と同一。

### 理由

- ExecutionStore は「何が起きたか（副作用の事実）」を記録し、DecisionStore は「なぜ起きたか（意思の来歴）」を記録する。これらは Koguchi の状態三層分離（Store / Proxy / Reconciliation）に意思層を追加するものであり、混在させない。
- 同じ SQLite ファイルを使うことで、一貫性のあるバックアップ・監査・来歴追跡が可能になる。トランザクション境界は分離したままにする（Decision の記録失敗が副作用の実行を妨げない）。
- `context_snapshot` を辞書型にすることで、Context Resolver が後から任意のコンテキスト情報（Agent 状態、prompt digest、環境変数など）を注入できる余地を残す。

---

## 決定 B: ToolProxy への統合（オプショナル注入）

**ToolProxy は DecisionStore をオプショナルで受け取る。DecisionStore が注入された場合のみ Decision を記録し、実行フックを埋める。**

```python
class ToolProxy:
    def __init__(
        self,
        workspace_dir: str,
        store: ExecutionStore,
        decision_store: DecisionStore | None = None,
    ):
```

`write_file()` に以下のパラメータを追加する：

```python
def write_file(
    self,
    envelope: ActionEnvelope | None,
    content: bytes,
    intent: str | None = None,
    context: dict | None = None,
) -> ProxyResult:
```

### Decision 記録のタイミング

Decision 記録は INV-1b 第一相（`intent_pending` 書込み）の**前**に行う。Decision 記録に失敗した場合は副作用を起こさず `REJECTED` とする——なぜなら「なぜ」を記録できない副作用を起こすことは Koguchi の誠実さに反するため。

### ExecutionEvent への反映

`_make_event()` は既に `**kwargs` で `intent` / `decision_ref` / `context_ref` を受け取れる。Decision が記録された場合：

| フィールド | 値 |
| --- | --- |
| `intent` | `Decision.intent` の値をそのまま伝播 |
| `decision_ref` | `Decision.decision_id` |
| `context_ref` | `context_snapshot` の SHA-256 digest（辞書全体の指紋） |

DecisionStore なし（`None`）の場合は、Phase 1 と同じく全フックが `None` になる。これにより後方互換性を保つ。

### 理由

- **オプショナル注入**: Decision Logger がない環境（テスト・簡易利用）を阻害しない。Koguchi は意思の来歴を「強制」ではなく「可能にする」層として提供する。
- **Decision 失敗 = REJECTED**: INV-1b 第一相の精神（「記録できないなら副作用を起こさない」）を意思層にも適用する。意思不在の副作用は Koguchi の隘路として通すべきではない。

---

## 決定 C: `redaction_policy` は引き続き空フック

`ActionEnvelope.redaction_policy` は本 Phase では実装しない。器だけを維持する。

### 理由

`redaction_policy` は「誰にどの意思情報を開示するか」という監査開示制御の責務を持つ。これは Decision Logger の実装完了後、Policy Gate（Phase 4）の設計と併せて扱うべき論点である。現時点で決め打つと、Policy Gate の設計自由度を損なう。

---

## 影響

| ファイル | 変更内容 |
| --- | --- |
| `src/koguchi/decision.py`（新規） | `Decision` モデル、`DecisionStore` Protocol、`SQLiteDecisionStore` |
| `src/koguchi/proxy.py` | `ToolProxy.__init__` に `decision_store` 追加、`write_file` に `intent`/`context` 追加 |
| `src/koguchi/__init__.py` | 新規 export 追加 |
| `tests/test_decision_logger.py`（新規） | Decision 記録・フック伝播・DecisionStore なし後方互換の回帰テスト |

---

## 意図的に延ばした論点

| 論点 | 延ばした理由 |
| --- | --- |
| Context Resolver の実装（コンテキスト自動キャプチャ） | Phase 2 は「意思を残す器」に注力。自動キャプチャは Phase 3 以降。現時点では caller が明示的に `context` を渡す。 |
| `redaction_policy` の意味論と実装 | Policy Gate（Phase 4）と併せて設計する。 |
| Decision の改竄検出（hash chain との統合） | DecisionStore の hash chain 化は自然な拡張だが、ExecutionStore の chain と二重管理になる。Phase 2 では単純な append-only とし、Phase 3 以降で判断する。 |
| DecisionStore を複数回呼び出しで共有するユースケース | Phase 2 は単一の ToolProxy + 単一の DecisionStore を前提とする。 |

---

## 次回更新方針

- Phase 3: Context Resolver（`context_snapshot` の自動キャプチャ）
- Phase 3: DecisionStore の hash chain 化と verify_chain 統合
- Phase 4: Policy Gate + `redaction_policy` 実装

---

## 参照

- [ADR-002](ADR-002-phase1-side-effect-chokepoint.md) — Phase 1 設計判断、縮退防止フックの定義
- [ADR-003](ADR-003-mkdir-scope-and-envelope-semantics.md) — Envelope 意味論
- `src/koguchi/events.py` — `ExecutionEvent` の空フック定義
- `src/koguchi/proxy.py` — `ToolProxy` 実装
