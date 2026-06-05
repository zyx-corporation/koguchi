# Koguchi

Context-Aware Harness — Side-Effect Chokepoint

Koguchi は、AIエージェントやアプリケーションが外部世界へ副作用を起こすとき、その副作用を監査可能な実行来歴へ変換する Context-Aware Harness 基盤である。

## 現在のステータス

| Phase | 名称 | 状態 |
|-------|------|------|
| 0 | Foundation — 仕様・ADR・開発手法 | ✅ |
| 1 | Side-Effect Chokepoint — `filesystem.write` の監査 | ✅ |
| 2 | Decision Logger — なぜ実行したかを記録 | ✅ |
| 3 | Policy Gate — 実行前許可判定 | ✅ |
| 4 | AuditGate Integration — アプリ抽象化層 | ✅ |
| 5 | Reconciliation v2 — 外部 API 実状態照合 | ✅ |
| 6 | Redaction / Secret Safety — 監査ログの安全な開示 | ✅ |
| 7〜10 | [Roadmap](docs/roadmap.md) 参照 | Planned |

## 主要概念

| 概念 | 説明 |
|------|------|
| **ActionEnvelope** | 副作用を包むラッパー。tool, target, parameters_digest, permission_scope, risk_class, redaction_policy を持つ |
| **ExecutionEvent** | append-only のイベントレコード。intent_pending / execution_committed / execution_failed / reconciliation_observed の4種 |
| **ExecutionStore** | 副作用の実行来歴を保持する append-only ストア。hash chain による改竄検出 |
| **DecisionStore** | 意思決定の来歴を保持するストア。「なぜ」を記録。独立した hash chain を持つ |
| **ToolProxy** | すべての管理対象副作用が通る単一の隘路 |
| **PolicyGate** | 実行前に副作用の許可を判定する（allow / deny / require_approval） |
| **AuditGate** | アプリケーションが依存する唯一の Koguchi インターフェース。内部実装を隠蔽 |
| **Reconciliation** | Store と実世界（ファイルシステム／外部API）の照合。診断は最尤推定 |
| **UNCONFIRMED** | 副作用は成功したが commit 記録に失敗した状態。Store には intent_pending が残る |
| **RedactionPolicy** | 監査ログの開示制御（full / without_intent / without_context / minimal） |

## インストール

```bash
pip install koguchi
```

## クイックスタート

```python
from koguchi import ToolProxy, SQLiteExecutionStore, ActionEnvelope

store = SQLiteExecutionStore("audit.db")
proxy = ToolProxy("./workspace", store)

envelope = ActionEnvelope(
    action_id="write-1",
    tool="filesystem.write",
    target="./workspace/output.txt",
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
| [Getting Started](docs/dev/getting-started.md) | 開発環境セットアップと最初のステップ |
| [AuditGate Integration](docs/dev/auditgate-integration.md) | アプリケーションへの Koguchi 組み込み |
| [Reconciliation v2](docs/dev/reconciliation-v2.md) | 外部 API 実状態との照合 |
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
