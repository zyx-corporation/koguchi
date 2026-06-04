# ADR-002: Phase 1 — Side-Effect Chokepoint 設計判断の記録

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-04 |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 背景

Koguchi Phase 1 の設計仕様書（v1.1）に基づき、Side-Effect Chokepoint を実装した。本 ADR は、その設計判断の要点と意図的に延ばした論点を来歴として記録する。仕様書の全文は `koguchi-phase1-side-effect-chokepoint.md` v1.1 を正とする。

---

## 主要な設計判断（保存された要素）

### 1. 四点セット不変条件（INV-1/1a/1b/1c）

- **INV-1**: すべての管理対象副作用は `ActionEnvelope` を伴い、`ToolProxy` 経由で実行し、実行前後に append-only で記録する。
- **INV-1a**: `ActionEnvelope` なしの副作用は `REJECTED`。
- **INV-1b（二相記録の核）**: `intent_pending` を書けなければ副作用を起こさない。commit 記録を書けなければ `SUCCESS` を返さない（`UNCONFIRMED`）。
- **INV-1c（境界の正直さ）**: 迂回は完全封じ込めではなく reconciliation による**検出**で扱う。

### 2. 状態の三層分離

Store の event 列・Proxy の戻り値・reconciliation 診断は、それぞれ別の層であり混在させない。特に `UNCONFIRMED` は Store の永続状態ではなく、Proxy の戻り値としてのみ存在する（Store には `intent_pending` が残存する）。

### 3. `filesystem.write` の atomic write

temp ファイルへの書込み・fsync・atomic rename により副作用を「全か無か」に強制する。Phase 1 において `FAILURE = 副作用なし` はツールの性質ではなく**実装の選択**に由来する。スキーマは `partial` / `unknown` の余地を保ち一般性を維持する。

### 4. append-only SQLite + hash chain

各 event に `previous_hash` を持たせ、改竄・ロストを hash chain の不整合として検出可能にする。`GENESIS_HASH` を空 chain の起点とする。

### 5. 縮退防止フック

`ExecutionEvent` に `intent` / `decision_ref` / `context_ref` を空フックとして持たせる。Phase 1 では埋めないが、後から Decision Logger / Context Resolver を接続する穴を最初から用意することで、「安全な Tool Runtime」への縮退を設計レベルで防ぐ。

---

## 変換された要素（v1.0 → v1.1 の ΔM）

`FAILURE` の意味論を「副作用なし」から「Tool Proxy が成功完了を確認できなかった」へ再定義した。この変換に伴い、`side_effect_observed`（`none` / `partial` / `unknown` / `confirmed`）を `ExecutionEvent` に追加し、`expected_result_digest` を `ActionEnvelope` に追加した。atomic write の §6 は、この意味論の変更を Phase 1 の実装で畳むための処方である。

---

## 意図的に延ばした論点（未解決のまま残した要素）

| 論点 | 延ばした理由 |
| --- | --- |
| `partial` / `unknown` の `side_effect_observed` | atomic write では発生しない。非 atomic なツール（shell / network）は後段フェーズ。 |
| `expected_result_digest` の非決定論ツールへの一般化 | 非決定論的ツールでは事前計算不可。将来 ADR で扱う。 |
| `intent` / `decision_ref` / `context_ref` の実装 | Phase 2（Decision Logger）の責務。空フックのみ。 |
| Python での副作用経路の完全封じ込め | Phase 4（Policy Gate）以降。現時点は検出（INV-1c）で扱う。 |
| reconciliation の `_all_committed` ヘルパー | `ExecutionStore` Protocol への `committed()` 追加は Phase 2 で行う。現時点は内部実装への直アクセスで暫定対応。 |

---

## 既知の限界（喪失の明示）

- reconciliation は静的スナップショット照合であり、副作用時点と照合時点の間の第三者変更を区別できない。診断は確定ではなく最尤推定。
- `committed_diverged` の最尤推定性は `expected_result_digest` を導入しても解消されない。
- Python 単体では副作用経路の完全封じ込めは保証できない。INV-1c はこれを「予防」ではなく「検出」で扱う。
- Agent が提示する候補集合の問題は本 Phase の監査対象外。

---

## 次回更新方針

- Phase 2（Decision Logger）着手時に ADR-003 を作成し、`decision_ref` の接続設計を記録する。
- `_all_committed` の暫定実装を `ExecutionStore` Protocol に `committed()` を追加して解消する時点で本 ADR を参照した ADR を作成する。
- Rust 化（Phase 4 Policy Gate）の時点で、スキーマの安定化と差し替え境界を ADR で確定する。

---

## 参照

- `koguchi-phase1-side-effect-chokepoint.md` v1.1 — 設計仕様書（正本）
- [`ADR-001-development-method.md`](ADR-001-development-method.md) — 本手法の採用 ADR
- `src/koguchi/` — 実装
- `tests/` — 不変条件の証拠（§10 赤テスト 3 本 + hash chain + reconciliation）

---

## 追記 — 2026-06-04: 実装バグの修正（境界の前方一致漏れ）

初版実装（`src/koguchi/proxy.py`）の workspace 境界チェックが文字列前方一致（`startswith`）で行われており、`/ws` を workspace とするとき兄弟ディレクトリ `/ws-evil/` への書込みを許す漏れがあった。これは §12 スコープ「`workspace_dir` 以下への書込みのみ」および INV-1c の境界保証に対する**喪失**である（`SUCCESS` で workspace 外に書けることを実証）。

**修正**: `Path.is_relative_to` による境界判定へ変更し、前方一致漏れと `..` による親脱出の双方を塞いだ。回帰テスト `tests/test_workspace_boundary.py`（前方一致・親脱出の 2 本）を追加し、不変条件の証拠とした。

本追記は ADR-002 の**決定**（`workspace_dir` 以下に限定する境界）を変更しない。決定は維持したまま、その実装上の欠陥と修正を来歴として記録する。

---

## 追記 — 2026-06-04: ExecutionStore Protocol の拡張（Issue #9）

`reconcile.py` の `_all_committed()` が `SQLiteExecutionStore._conn` に直接アクセスする暫定実装を解消した。`ExecutionStore` Protocol に `committed() -> list[ExecutionEvent]` を追加し、`SQLiteExecutionStore` に実装した。`reconcile.py` は `store.committed()` 経由で committed event を取得するようになり、Store の内部実装に依存しなくなった。

---

## 追記 — 2026-06-04: hash chain 検証 API の追加（Issue #10）

hash chain を「積む」実装はあったが「検証する」入口がなかった。`SQLiteExecutionStore.verify_chain()` を追加し、payload 改竄・`previous_hash` 不整合・chain 断絶を検出できるようにした。

`verify_chain()` を正しく実装するため、`_make_event()` の hash 計算を内部 dict ベースから `model_dump_json()` ベースへ変更した（`hash` フィールドを除いた全フィールドから計算）。これにより「保存されたペイロードから hash を再計算できる」という不変条件が成立する。既存の hash chain との互換性は保たれない（Phase 1 は開発段階であり、既存の event log は破棄して再作成する）。
