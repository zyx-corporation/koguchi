# ADR-013: reconcile — ツールタイプ別 pending 診断ロジック

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |
| **Closes** | ADR-005 延ばした論点「reconcile の shell pending 対応」|

---

## 背景

reconcile の pending event 照合は `target.exists()` に依存している。これは `filesystem.write` / `filesystem.mkdir` では有効だが、`shell.execute`（target = workspace_dir）や `network.http_get`（target = URL）では常に存在確認が成功してしまい、`pending_not_executed` が構造的に発生しない。

本 ADR は、ツールタイプに応じた診断ロジックの分岐を導入する。

---

## 決定 A: ツールタイプによる診断分岐

**`envelope.tool` の値に基づいて診断ロジックを分岐する。**

| ツール | target の意味 | 存在確認 | pending 診断 |
|--------|-------------|---------|-------------|
| `filesystem.write` | ファイルパス | 可能 | `target.exists()` → executed / not_executed |
| `filesystem.mkdir` | ディレクトリパス | 可能 | `target.exists()` → executed / not_executed |
| `shell.execute` | workspace_dir | 不可能（常に存在） | 常に `pending_executed_unconfirmed` |
| `network.http_get` | URL | 不可能 | 常に `pending_executed_unconfirmed` |

### 非ファイルシステムツールの confidence

| ツール | confidence | 理由 |
|--------|-----------|------|
| `shell.execute` | 0.70 | プロセステーブル検査で検証可能だが未実装 |
| `network.http_get` | 0.50 | 完全に外部。リモートログとの突合が必要 |

---

## 決定 B: ツール判別ロジック

```python
_FILESYSTEM_TOOLS = {"filesystem.write", "filesystem.mkdir"}
```

`envelope.tool` がこれに含まれればファイルベース照合、含まれなければ非ファイルシステム照合。

---

## 影響

| ファイル | 変更内容 |
| --- | --- |
| `src/koguchi/reconcile.py` | pending 照合ループにツール判別分岐を追加 |
| `tests/test_reconciliation.py` | shell pending / http pending のテスト追加 |

---

## 参照

- [ADR-005](ADR-005-non-atomic-shell-execute.md) — shell pending の延期判断
- [ADR-009](ADR-009-network-http-partial.md) — network.http_get
- `src/koguchi/reconcile.py` — 現在の実装
