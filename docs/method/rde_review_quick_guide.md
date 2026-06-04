# RDE／レビュー運用ガイド（短文・非規範）

公開向けの**要約**である。詳しい観測カテゴリと背景は [SLS + RDE に基づく開発手法](sls_rde_development_method.md)、規範判断は [`docs/adr/`](../adr/) を正とする。**確定した運用規程ではない**。

元文書: [kotonoha-docs — RDE／レビュー運用ガイド](https://github.com/zyx-corporation/kotonoha-docs/blob/main/ja/method/rde_review_quick_guide.md)

---

## 1. RDE／レビューを検討するタイミング（目安）

| 変化の例 | メモ |
| --- | --- |
| **スキーマ・不変条件**の変更（`envelope.py`, `events.py`, `store.py`） | PR 本文に保存／変換／喪失を書く。ADR への影響を確認する。 |
| **ToolProxy の実行経路**を変える変更 | 隘路の単一性（INV-1）が保たれているか。迂回経路が生まれていないか。 |
| **reconciliation の診断ロジック**を変える変更 | `pending_executed_unconfirmed` / `unrecorded_external_change` の検出精度への影響を明示する。 |
| **空フック（`intent` / `decision_ref` / `context_ref`）**を埋める変更 | 縮退防止フックの意図と整合しているか ADR で確認する。 |
| **Phase 境界**をまたぐ設計変更 | 新 ADR を作成し、旧 ADR を supersede する。 |

---

## 2. RDE に期待しないこと

- **承認・採決の代替**にならない。`UNCONFIRMED` を `SUCCESS` に読み替えないのと同じく、未確定をレビュー通過と読み替えない。
- 「次回更新方針」を**誰かが Issue または次 ADR で文章化するまで**宙に浮かせない。未解決だけを書いて締めることを目的にしない。

---

## 3. PR／Issue に残すトレース（最低ライン）

次が**後から読み手に説明できる**状態を、暫定的な合格として使える。

1. **どの差分・どのレビュー**についての議論か（Issue／PR の番号または URL）。
2. **影響する不変条件**（INV-1 / INV-1a / INV-1b / INV-1c）を明示しているか。
3. **意図的に延ばした論点**（スコープ外・将来フェーズへの持越し）が一文で書けるか。
4. **まだ ADR に載らない論点**は Issue で追跡する。

---

## 4. 喪失（lost）と ADR 昇格の扱い

- **実装だけで決め打ち**したときは、ADR での追跡・記録への接続を検討する。
- **規範的な変更**が必要になったタイミングでは `docs/adr/` に新 ADR を作成し、本手法説明文書で規範本文を重複複製しない。

---

## 5. 参照

| 種別 | リンク |
| --- | --- |
| 手法の詳細 | [`sls_rde_development_method.md`](sls_rde_development_method.md) |
| 採用 ADR | [`docs/adr/ADR-001-development-method.md`](../adr/ADR-001-development-method.md) |
| Phase 1 設計仕様 | [`docs/adr/ADR-002-phase1-side-effect-chokepoint.md`](../adr/ADR-002-phase1-side-effect-chokepoint.md) |
