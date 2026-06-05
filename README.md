# Koguchi

Context-Aware Harness — Side-Effect Chokepoint

AIエージェントの副作用を監査可能な来歴へ変換する単一の隘路。

## 概要

Koguchi は、AIエージェントやアプリケーションが外部世界へ副作用を起こすとき、その副作用を監査可能な来歴へ変換するための基盤である。

副作用は必ず `ToolProxy` を通り、実行前の意図・実行後の結果・失敗・不確定状態が append-only の `ExecutionStore` に記録される。迂回された副作用は `reconcile` によって検出される。

## インストール

```bash
pip install koguchi
```

## クイックスタート

```python
from koguchi import ToolProxy, SQLiteExecutionStore, ActionEnvelope

store = SQLiteExecutionStore("audit.db")
proxy = ToolProxy("/workspace", store)

envelope = ActionEnvelope(
    action_id="write-1",
    tool="filesystem.write",
    target="/workspace/output.txt",
    parameters_digest="abc123",
    permission_scope="workspace",
    risk_class=["file_write"],
)

result = proxy.write_file(envelope=envelope, content=b"Hello, Koguchi")
# ProxyResult.SUCCESS / FAILURE / REJECTED / UNCONFIRMED
```

## ドキュメント

| 文書 | 説明 |
|------|------|
| [Getting Started](docs/dev/getting-started.md) | 開発環境のセットアップと最初のステップ |
| [Roadmap](docs/roadmap.md) | 全体ロードマップとフェーズ計画 |
| [ADR](docs/adr/) | Architecture Decision Records（設計判断の正本） |
| [API Docs](docs/api/) | `make docs` で生成 |

## 品質

```bash
make quality   # ruff + mypy + pytest
```

| 指標 | 値 |
|------|-----|
| テスト | 81 passed |
| カバレッジ | 91% |
| 型チェック | mypy strict |
| サポート Python | 3.11 / 3.12 / 3.13 |

## ライセンス

[LICENSE](LICENSE)
