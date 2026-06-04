# ADR-001: SLS + RDE に基づく開発手法の採用

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-04 |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 背景

Koguchi は、AIエージェントの副作用を監査可能な来歴へ変換する単一の隘路（Side-Effect Chokepoint）を実装するプロダクトである。その設計原則は「外部世界の不可逆性を直視する」ことにあり、実行後の `UNCONFIRMED` という戻り値はその誠実さの表れである。

Koguchi 自身の開発プロセスも、この原則と整合していなければならない。変更が「何を保存し、何を失い、どこに逸脱リスクがあるか」を見えない状態で積み上げると、設計の隘路が形骸化する——これは副作用経路が分裂することと同型の問題である。

ZAI プロダクト群（Kotonoha 等）では、**Semantic Lineage System（SLS）** と **Resonant Deviation Evaluator（RDE）** の考え方に基づく開発手法が実践されている。Koguchi においても同手法を採用し、プロダクトの設計思想と開発プロセスを一致させる。

---

## 決定

**Koguchi の開発に SLS + RDE に基づく開発手法を採用する。**

具体的には以下を規範とする。

1. **RDE の七つの観測カテゴリ**（保存・変換・補完・未解決・喪失・逸脱リスク・次回更新方針）を、設計変更・スキーマ変更・ADR 更新のレビュー観点として使う。
2. **ΔM（意味変化）** を、diff だけでなく不変条件（INV-1/1a/1b/1c）・責任境界・設計意図への影響として捉える。
3. **ADR を判断の正本**とし、規範的な変更は必ず ADR で記録する（`docs/adr/` に追記、上書きしない）。
4. **テストを不変条件の証拠**として位置づける。テストは §10 の赤テストを起点とし、「機能が動く」ではなく「不変条件が守られているか」を突く構造を維持する。
5. **隘路の単一性を崩す変更**（Tool Proxy を迂回する経路の追加等）は逸脱リスクとして明示的にレビューする。
6. **縮退防止フック**（`intent` / `decision_ref` / `context_ref`）の意図を維持し、「安全な Tool Runtime」への縮退を repeating agenda として警戒する。

手法の詳細は [`docs/method/sls_rde_development_method.md`](../method/sls_rde_development_method.md) に記述する。

---

## 理由

### なぜ SLS + RDE か

Koguchi の設計仕様書（Phase 1 v1.1）は、変更履歴に次を明示している。

> `FAILURE` の意味論を「副作用なし」から「Tool Proxy が成功完了を確認できなかった」へ再定義した（§3）。

この変更は単なる文言変更ではなく、**`side_effect_observed` の導入・`expected_result_digest` の追加・atomic write の正当化・reconciliation 精度の上限の明示**という複数の変換を伴う ΔM の大きい変更であった。RDE の観測カテゴリを使えば、この種の変換が「暗黙のすり替え」でないことを来歴として残せる。

### なぜ ADR を正本とするか

Koguchi は現時点で単一リポジトリであり、kotonoha のような「spec リポジトリ」を持たない。ADR を `docs/adr/` に置くことで、規範的な判断の正本をコードと同じリポジトリ内で追跡可能にする。ADR は append-only——上書きせず、変更時は新 ADR で supersede する。これは Koguchi の `ExecutionStore` が event を append-only で積む原則と同型である。

### なぜ今か

**副作用経路と同じ理由**——設計負債が複利で効くのは実行経路だけでなく、開発プロセスの記録経路でも同様である。プロセスの来歴が分裂すると、後から塞げない。Koguchi の最初のコミットが `Initial commit` のみである現時点が、来歴を整備する最も低コストなタイミングである。

---

## 受け入れたトレードオフ

| トレードオフ | 判断 |
| --- | --- |
| レビューに観測カテゴリを意識する分のオーバーヘッド | 小さい変更では「§3 の重大な喪失や逸脱が見えない状態を避ける」を最低ラインとし、全カテゴリへの長文回答を義務化しない。 |
| ADR が増えると参照が複雑になる | `docs/adr/` の INDEX（本ディレクトリの `README.md`）で一覧を管理する。 |
| kotonoha-docs との同期コスト | 元文書の URL を明記し、方針の乖離が生じた場合は Koguchi 側の ADR で差分を記録する。独自進化を妨げない。 |

---

## 意図的に延ばした論点

- RDE の観測カテゴリを CI で機械的にチェックする仕組み（PR テンプレート等）は、Phase 2 以降に検討する。
- kotonoha-docs との同期頻度・差分管理の方針は未確定。問題が顕在化した時点で ADR を追加する。

---

## 参照

- [`docs/method/sls_rde_development_method.md`](../method/sls_rde_development_method.md) — 手法の詳細
- [`docs/method/rde_review_quick_guide.md`](../method/rde_review_quick_guide.md) — 運用ガイド（短文）
- [kotonoha-docs — SLS + RDE に基づく開発手法](https://github.com/zyx-corporation/kotonoha-docs/blob/main/ja/method/sls_rde_development_method.md) — 元文書
- `koguchi-phase1-side-effect-chokepoint.md` v1.1 — Phase 1 設計仕様（ADR-002 に要約予定）
