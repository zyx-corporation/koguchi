# AuditGate Integration

Koguchi をアプリケーションに組み込む開発者向けの手引き。

## 概念

| レイヤ | 役割 | 知っていること |
|--------|------|---------------|
| **ToolProxy** | Koguchi core の低レベル副作用隘路 | `ActionEnvelope`, `ExecutionStore`, hash chain |
| **AuditGate** (Protocol) | アプリケーション統合用の抽象インターフェース | `audit(tool, target, ...)` のみ |
| **KoguchiAuditGate** | AuditGate の Koguchi 実装 | ToolProxy を内包 |

## なぜ AuditGate が必要か

`ToolProxy` をアプリケーション全体に露出させると：

- アプリケーションが `ActionEnvelope` の生成責務を負う
- `ExecutionStore` への依存が広がる
- Koguchi の内部変更がアプリケーション全体に波及する

AuditGate はこれらの詳細を隠蔽し、アプリケーションは `audit()` メソッドだけを知ればよい。

## 基本構成

```python
from koguchi import (
    KoguchiAuditGate,
    SQLiteExecutionStore,
    ExecutionPolicyGate,
    DenyShellExecution,
    ToolProxy,
)

store = SQLiteExecutionStore("audit.db")
policy_gate = ExecutionPolicyGate([DenyShellExecution()])
proxy = ToolProxy("./workspace", store, policy_gate=policy_gate)
gate = KoguchiAuditGate(proxy)
```

## JouJou をユースケースとした統合パターン

### create_todo の流れ

```
TodoInput
  ↓
KoguchiAuditGate.audit(...)     ← ActionEnvelope 生成 + ToolProxy 実行
  ↓
Provider.create_todo(todo)      ← 外部 API 実行（Koguchi は知らない）
  ↓
TodoResult
```

### コード例

```python
from koguchi.audit import AuditGate, AuditResult
from koguchi.events import ProxyResult


class TodoService:
    def __init__(self, audit_gate: AuditGate, provider):
        self._audit_gate = audit_gate
        self._provider = provider

    async def create_todo(self, todo: dict, intent: str) -> AuditResult:
        # 1. 監査経路で intent を記録
        result = self._audit_gate.audit(
            tool="todo.create",
            target=todo.get("title", ""),
            params_digest=hashlib.sha256(
                json.dumps(todo).encode()
            ).hexdigest(),
            permission_scope="todo",
            risk_class=["external_api"],
            intent=intent,
        )

        # 2. Policy Gate による拒否
        if result.result == ProxyResult.REJECTED:
            raise PermissionError(
                f"Todo creation denied: {todo.get('title')}"
            )

        # 3. 外部 Provider に実行委譲
        try:
            external_result = await self._provider.create(todo)
        except Exception:
            raise

        return result
```

## UNCONFIRMED の扱い

`audit()` の内部で `write_file`（Phase 4 では filesystem.write のみ）が成功したが commit 記録に失敗した場合、`AuditResult.result` は `UNCONFIRMED` になる。

```python
if result.result == ProxyResult.UNCONFIRMED:
    # 副作用は成功した可能性がある
    # Store には intent_pending が残っている
    # Reconciliation で外部状態と照合する
    # 再実行はしてはならない
```

## 設計原則

1. **Provider は Koguchi を知らない**: Provider は外部 API を実行するだけ
2. **TodoService は AuditGate Protocol だけを知る**: KoguchiAuditGate への依存は DI で注入
3. **Koguchi の内部実装は KoguchiAuditGate に閉じ込める**: ActionEnvelope, ExecutionStore, hash chain

## 次のステップ

- [Reconciliation v2](reconciliation-v2.md) — 外部 API 実状態との照合
- [Getting Started](getting-started.md) — Koguchi の基本使い方
- [ADR-015](../adr/ADR-015-audit-gate.md) — AuditGate の設計判断
