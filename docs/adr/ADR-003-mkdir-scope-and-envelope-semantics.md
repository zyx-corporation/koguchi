# ADR-003: Phase 1 スコープ確定 — 親ディレクトリ作成と Envelope 意味論

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-04 |
| **Supersedes** | — |
| **Superseded by** | — |
| **Closes** | Issue #7, Issue #8 |

---

## 背景

Phase 1 実装レビュー（Issue #7, #8）で、二つの意味論上の曖昧さが指摘された。

1. `ToolProxy.write_file()` が `target.parent.mkdir(parents=True, exist_ok=True)` を暗黙に実行していた。これは `filesystem.write` の単一副作用モデルを濁らせ、「rename 前に失敗したら副作用なし」という atomic write の保証を崩す。

2. `ActionEnvelope` が `None` の場合に `ProxyResult.REJECTED` を返すか `EnvelopeRequiredError` を raise するかが、仕様（INV-1a「戻り値は REJECTED」）と実装（例外を raise）で食い違っていた。

---

## 決定 A: 親ディレクトリ作成は Phase 1 のスコープ外

**`ToolProxy.write_file()` から `mkdir` を除去する。親ディレクトリが存在しない場合は `ProxyResult.REJECTED` を返す（`intent_pending` を書く前に弾く）。**

### 理由

- `mkdir` は `filesystem.write` とは別の外部副作用である。管理対象として扱うなら独立した `ActionEnvelope`・`intent_pending`・commit record を持つべきだが、Phase 1 ではそこまで実装しない。
- 暗黙の `mkdir` を残すと、atomic write の「全か無か」保証が「ファイル本文については全か無か」に限定されることが不明瞭になる。`FAILURE = 副作用なし`（§6）の意味が濁る。
- 既存ディレクトリ内への atomic file write に限定することで、Phase 1 の副作用モデルが単純かつ正直に保たれる。

### スコープ

- Phase 1 では `target.parent.exists()` を事前チェックし、存在しない場合は `REJECTED`（Store と workspace に何も書かない）。
- 将来の `filesystem.mkdir` ツールは独立した `ActionEnvelope` と二相記録を持つ。これは後段フェーズの設計課題とする。

---

## 決定 B: `envelope=None` は `EnvelopeRequiredError`（契約違反例外）

**`ActionEnvelope` が `None` で渡された場合は `EnvelopeRequiredError` を raise する。`ProxyResult.REJECTED` には変更しない。**

INV-1a の記述「戻り値は REJECTED」を、実装側に合わせて次のように読み替える。

| 状況 | 扱い |
| --- | --- |
| `envelope=None`（呼び出し契約違反） | `EnvelopeRequiredError` を raise。CAH 管理対象として成立していない呼び出し。Store にも workspace にも副作用なし。 |
| `envelope` あり + workspace 境界違反 | `WorkspaceBoundaryError` を raise。 |
| `envelope` あり + 親ディレクトリなし | `ProxyResult.REJECTED`。Store にも workspace にも副作用なし。 |
| `envelope` あり + Store への pending 書込み失敗 | `ProxyResult.REJECTED`。副作用なし。 |

### 理由

`ActionEnvelope` は ToolProxy の実行単位そのものであり、`None` は「拒否された副作用」ではなく「CAH 管理対象として構成されていない呼び出し」である。例外として扱うことで、開発者 API の誤用を明確に可視化できる。`ProxyResult` は「適切に構成された操作が、policy / permission / workspace 境界によって拒否された結果」を表す観測値として純化する。

---

## 影響

- `proxy.py`: `mkdir` 除去・親 dir 存在チェックを intent_pending の前に追加。
- `tests/test_mkdir_scope.py`: 親 dir なし → REJECTED の回帰テストを追加。
- `test_envelope_required.py`: 既存の `EnvelopeRequiredError` 期待は維持。
- INV-1a の記述: 本 ADR で「`envelope=None` は例外、管理対象操作の拒否は `REJECTED`」と明文化。仕様書側の更新は次回改訂に委ねる。

---

## 意図的に延ばした論点

- `filesystem.mkdir` の独立した副作用管理は後段フェーズ。
- `WorkspaceBoundaryError` も `REJECTED` に統一すべきかは Issue で追跡する（現時点は例外のまま。ツール境界違反とポリシー拒否の区別が利用側で有用）。

---

## 参照

- [ADR-002](ADR-002-phase1-side-effect-chokepoint.md) — Phase 1 設計判断
- Issue #7 — 親ディレクトリ作成副作用の扱い
- Issue #8 — Envelope なしの意味論
