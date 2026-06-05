# ADR-007: 品質基盤 — 静的解析・型チェック・フォーマット

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 背景

Koguchi は現在、テストによる不変条件の検証（35件）は行っているが、静的解析・型チェック・自動フォーマットの基盤がない。コードレビューにおけるスタイル指摘や型不整合の発見は人手に依存し、Python 3.11+ の型ヒントが活用されていない。

本 ADR は、Koguchi の品質基盤として ruff（lint + format）と mypy（型チェック）を導入し、その設定と運用方針を定める。

---

## 決定 A: ruff の採用（lint + format）

**リンターおよびフォーマッターとして ruff を採用する。**

### 設定（`pyproject.toml`）

```toml
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes (未使用 import 等)
    "I",   # isort (import 順序)
    "N",   # pep8-naming
    "UP",  # pyupgrade (モダン Python 構文)
    "B",   # flake8-bugbear
    "SIM", # flake8-simplify
]

[tool.ruff.format]
quote-style = "double"
```

### 理由

- **単一ツール**: lint + format + import 順序を ruff 一つで完結させる。flake8 + black + isort の組み合わせより実行が高速で設定が簡素。
- **pyupgrade (UP)**: Python 3.11+ の新構文（`X | None` 等）の使用を促し、古い `Optional[X]` や `Union[X, Y]` を自動修正する。
- **flake8-bugbear (B)**: よくあるバグパターン（裸の `except:`、ミュータブルなデフォルト引数等）を検出。

---

## 決定 B: mypy の採用（strict 型チェック）

**型チェッカーとして mypy を `strict` モードで採用する。**

### 設定（`pyproject.toml`）

```toml
[tool.mypy]
strict = true
python_version = "3.11"
ignore_missing_imports = true   # サードパーティ（pydantic, sqlite3 等）
```

### 理由

- **strict モード**: Koguchi は全コードに型ヒントを付与済みであり、strict モードの追加コストが低い。新規コードにも型ヒントを強制できる。
- **`ignore_missing_imports = true`**: pydantic 等のサードパーティライブラリの型スタブが不完全な場合のノイズを避ける。Koguchi 自身の型正確性に集中する。

---

## 決定 C: 品質チェックの実行単位

**以下のコマンドを品質ゲートとする。**

```bash
ruff check src/ tests/        # lint
ruff format --check src/ tests/  # フォーマット確認
mypy src/                     # 型チェック
pytest tests/                 # テスト
```

CI 化（GitHub Actions 等）はリポジトリの公開時に行う。現時点ではローカル実行を前提とする。

---

## 決定 D: pyproject.toml への統合

全ツール設定を `pyproject.toml` に一元化する。個別の設定ファイル（`.ruff.toml`, `mypy.ini` 等）は作成しない。

---

## 影響

| ファイル | 変更内容 |
| --- | --- |
| `pyproject.toml` | `[tool.ruff]`, `[tool.ruff.lint]`, `[tool.ruff.format]`, `[tool.mypy]` 追加。dev dependencies に ruff, mypy 追加 |
| `src/koguchi/*.py` | ruff の自動修正（I=import順序、UP=モダン構文）を適用 |
| なし（削除）| 個別設定ファイルは作らない |

---

## 意図的に延ばした論点

| 論点 | 延ばした理由 |
| --- | --- |
| GitHub Actions CI ワークフロー | リポジトリ非公開の現時点ではローカル実行で十分。公開時に `.github/workflows/ci.yml` を作成する。 |
| カバレッジ閾値 | テストは不変条件の証拠であり、カバレッジ率より意味のあるテストを優先する。閾値は Phase 3 以降で検討。 |
| pre-commit hooks | 開発者数が増えた時点で導入する。現時点は手動実行で十分。 |

---

## 次回更新方針

- リポジトリ公開時に GitHub Actions CI ワークフローを追加
- テストカバレッジ計測（pytest-cov は導入済み、閾値設定は将来）

---

## 参照

- [ADR-001](ADR-001-development-method.md) — SLS + RDE 開発手法（CI 機械的チェックへの言及あり）
- [ruff documentation](https://docs.astral.sh/ruff/)
- [mypy documentation](https://mypy.readthedocs.io/)
