# ADR-008: Phase 2.D — `filesystem.mkdir` の独立実装

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |
| **Closes** | ADR-003 延ばした論点「`filesystem.mkdir` の独立した副作用管理」|

---

## 背景

ADR-003 で `ToolProxy.write_file()` から暗黙の `mkdir` を除去し、「親ディレクトリが存在しない場合は `REJECTED`」とした。この決定に伴い、`filesystem.mkdir` を独立したツールとして実装する必要がある。本 ADR はその設計判断を記録する。

---

## 決定 A: `make_directory()` の追加

**`ToolProxy` に `make_directory(envelope, ...) -> ProxyResult` を追加する。**

### シグネチャ

```python
def make_directory(
    self,
    envelope: ActionEnvelope | None,
    intent: str | None = None,
    context: dict[str, object] | None = None,
) -> ProxyResult:
```

### 実行モデル

`Path(envelope.target).mkdir(parents=True, exist_ok=True)` を用いる。

| 状態 | 条件 | `side_effect_observed` | 戻り値 |
|------|------|------------------------|--------|
| 成功（作成）| ディレクトリが作成された | `"confirmed"` | `SUCCESS` |
| 成功（既存）| `exist_ok=True` で既存ディレクトリ | `"confirmed"` | `SUCCESS` |
| 失敗 | `mkdir` が例外送出 | `"none"` | `FAILURE` |

### `result_digest`

`hashlib.sha256(target_path_bytes).hexdigest()` — 作成されたディレクトリパスの指紋。

### `expected_result_digest`

決定論的ツールのため事前計算可能。target の SHA-256。

---

## 決定 B: workspace 境界チェックの統一

**`write_file` と同様に、`make_directory` も `workspace_dir` 内に対象を限定する。`..` による親脱出と前方一致漏れは `is_relative_to` で防ぐ。**

### 理由

`filesystem.mkdir` と `filesystem.write` は同じファイルシステム層のツールであり、同じ境界制約を持つべき。

---

## 決定 C: `exist_ok=True` の採用

**`make_directory` は `exist_ok=True` で呼び出し、既存ディレクトリへの mkdir は `SUCCESS` として扱う。**

### 理由

- ディレクトリ作成は冪等であるべき。同じパスに二回 mkdir しても副作用は変わらない。
- `exist_ok=False` にして既存時 `FAILURE` にすると、Agent は呼び出し前にディレクトリ存在確認が必要になり、複雑さが増す。
- 監査の観点では「このディレクトリが確かに存在する」という事実が記録されることに価値がある。

---

## 影響

| ファイル | 変更内容 |
| --- | --- |
| `src/koguchi/proxy.py` | `make_directory()` 追加 |
| `tests/test_mkdir.py`（新規） | mkdir 成功・既存・workspace 境界・envelope なし の回帰テスト |

---

## 参照

- [ADR-003](ADR-003-mkdir-scope-and-envelope-semantics.md) — 親ディレクトリ作成副作用の扱い
- [ADR-005](ADR-005-non-atomic-shell-execute.md) — 非 atomic ツールの設計パターン
- `src/koguchi/proxy.py` — `ToolProxy` 実装
