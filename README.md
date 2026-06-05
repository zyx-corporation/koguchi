# Koguchi

Context-Aware Harness — Side-Effect Chokepoint

Koguchi is a Context-Aware Harness reference implementation that routes tool execution through an accountable side-effect chokepoint.

Koguchi は、AIエージェントやアプリケーションが外部世界へ副作用を起こすとき、その副作用を監査可能な実行来歴へ変換する Context-Aware Harness 基盤である。

**Koguchi is not a security sandbox.** The current Python implementation provides best-effort runtime constraint checks. Strong isolation is deferred to Rust chokepoint and OS/container-level enforcement.

**Koguchi は security sandbox ではない。** 現在の Python 実装は best-effort な実行時制約チェックを提供する。強い隔離は Rust chokepoint および OS/container レベルの機構に委ねる。

## Current status

`v0.5.0-observation-preview`

This version provides a read-only observation layer over Koguchi's audit records, reconciliation jobs, and Rust chokepoint availability.

It is intended for architectural review and local experimentation. It is not production-ready, not a security sandbox, and not a dashboard control plane. The dashboard is an observation plane only — it does not execute, approve, rerun, repair, or mutate.

See [docs/known-limitations.md](docs/known-limitations.md).

## Core Idea

```
Agent → ToolProxy → PolicyGate → ServiceRuntime → RuntimeBoundary → Tool Backend
                                              ↘ AuditEventSink
                                              ↘ Reconciliation Hook
```

## Installation

```bash
pip install koguchi
```

## Quick Start

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

## Minimal Example

```bash
python examples/minimal_tool_proxy.py
```

## Running Tests

```bash
make quality   # ruff + mypy + pytest
```

| 指標 | 値 |
|------|-----|
| テスト | 117 passed |
| 型チェック | mypy strict |
| サポート Python | 3.11 / 3.12 / 3.13 |

## Architecture Overview

See [docs/architecture.md](docs/architecture.md) for the full architecture.

### Key Concepts

| 概念 | 説明 |
|------|------|
| **ToolProxy** | Agent から見た唯一の副作用実行経路。PolicyGate と ServiceRuntime を接続 |
| **PolicyGate** | envelope / policy 上の許可判定（allow/deny/require_approval） |
| **RuntimeBoundary** | tool / env / workspace 上の実行時境界判定 |
| **ServiceRuntime** | RuntimeBoundary 判定、tool execution、audit event emission を束ねる accountable execution surface |
| **AuditGate** | アプリケーションが依存する唯一の Koguchi インターフェース |
| **Reconciliation** | Store と実世界の照合。診断は最尤推定 |
| **RedactionPolicy** | 監査ログ開示制御（full/without_intent/without_context/minimal） |
| **RDE / T-RDE** | 意味変化監査。RDE は PolicyGate の代替でも security sandbox でもない |

## Security Model

See [docs/known-limitations.md](docs/known-limitations.md).

## Documentation

| 文書 | 説明 |
|------|------|
| [Architecture](docs/architecture.md) | 全体構造と責務分離 |
| [Getting Started](docs/dev/getting-started.md) | 開発環境セットアップ |
| [Known Limitations](docs/known-limitations.md) | 現状の制約 |
| [ADR](docs/adr/) | 設計判断の正本（001〜021） |
| [Roadmap](docs/roadmap.md) | 全体フェーズ計画 |
| [Release Checklist](docs/release/v0.1-developer-preview-checklist.md) | v0.1 完了条件 |

## License

[LICENSE](LICENSE)
