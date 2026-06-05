# Getting Started

Koguchi を初めて使う開発者のための技術マニュアル。

## 1. Koguchi が守るもの

Koguchi は、外部副作用が必ず監査可能な単一経路を通ることを保証する。
守るのは以下である。

- **INV-1**: 全管理対象副作用は `ActionEnvelope` + `ToolProxy` + `ExecutionStore` を通る
- **INV-1a**: `ActionEnvelope` なしの副作用は実行されない
- **INV-1b**: `intent_pending` を書けなければ副作用を起こさない。commit 記録失敗は `UNCONFIRMED`
- **INV-1c**: 迂回された副作用は `reconcile` で検出する

Koguchi が守らないもの：任意コード実行の防止、ネットワークの完全封じ込め、暗号化。

## 2. 最小構成

```python
from koguchi import (
    ActionEnvelope,
    ExecutionPolicyGate,
    DenyShellExecution,
    SQLiteExecutionStore,
    ToolProxy,
)

store = SQLiteExecutionStore("audit.db")
policy_gate = ExecutionPolicyGate([DenyShellExecution()])
proxy = ToolProxy("./workspace", store, policy_gate=policy_gate)
```

## 3. ActionEnvelope の作り方

```python
import hashlib

envelope = ActionEnvelope(
    action_id="write-001",
    tool="filesystem.write",
    target="./workspace/out.txt",
    parameters_digest=hashlib.sha256(b"content").hexdigest(),
    expected_result_digest=hashlib.sha256(b"content").hexdigest(),
    permission_scope="workspace",
    risk_class=["file_write"],
    redaction_policy="without_context",
)
```

## 4. ToolProxy の使い方

```python
result = proxy.write_file(
    envelope=envelope,
    content=b"hello koguchi\n",
    intent="生成された内容をワークスペースに書き込む",
)
# → ProxyResult.SUCCESS
```

## 5. PolicyGate の使い方

```python
# shell.execute を拒否するポリシー
policy_gate = ExecutionPolicyGate([DenyShellExecution()])
proxy = ToolProxy("./workspace", store, policy_gate=policy_gate)

result = proxy.execute_shell(
    envelope=shell_envelope, command=["echo", "x"],
)
# → ProxyResult.REJECTED（副作用なし）
```

## 6. AuditGate の使い方

`ToolProxy` を直接使う代わりに、`AuditGate` で抽象化する。

```python
from koguchi import KoguchiAuditGate

gate = KoguchiAuditGate(proxy)
result = gate.audit(
    tool="filesystem.write",
    target="./workspace/out.txt",
    params_digest=hashlib.sha256(b"data").hexdigest(),
    permission_scope="workspace",
    risk_class=["file_write"],
    intent="監査テスト",
    data=b"data",
)
# → AuditResult(action_id=..., result=ProxyResult.SUCCESS, side_effect_observed="confirmed")
```

## 7. UNCONFIRMED の扱い

副作用は成功したが commit 記録に失敗した場合、`UNCONFIRMED` が返る。

```python
result = proxy.write_file(envelope=envelope, content=b"data")
if result == ProxyResult.UNCONFIRMED:
    # Store には intent_pending が残っている
    # reconciliation で後から照合する
    findings = reconcile("./workspace", store)
```

`UNCONFIRMED` は `SUCCESS` でも `FAILURE` でもない。再実行してはならない。

## 8. Reconciliation の扱い

```python
from koguchi.reconcile import reconcile

findings = reconcile("./workspace", store)
for f in findings:
    print(f.diagnosis, f.confidence, f.detail)
# pending_not_executed / pending_executed_unconfirmed / unrecorded_external_change
# committed_consistent / committed_diverged
```

診断は最尤推定であり、確定的真実ではない。

## 9. JouJou create_todo での利用例

```python
class TodoService:
    def __init__(self, audit_gate: AuditGate, provider: ReconciliableProvider):
        self._audit_gate = audit_gate
        self._provider = provider

    async def create_todo(self, todo: dict, intent: str) -> AuditResult:
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

        if result.result == ProxyResult.REJECTED:
            raise PermissionError("Policy denied")

        # Provider に実行委譲（Koguchi は知らない）
        await self._provider.create(todo)

        return result
```

## 10. よくある実装ミス

- **Provider を直接呼ぶ**: `ToolProxy` / `AuditGate` を経由せずに外部 API を直接呼ぶと、監査経路が分裂する
- **before audit に失敗しても外部副作用を実行する**: `REJECTED` を無視して副作用を起こしてはならない
- **after audit 失敗を通常失敗にして再実行を促す**: commit 記録失敗は `UNCONFIRMED` であり、再実行は二重副作用を生む
- **UNCONFIRMED を Store event として保存しようとする**: `UNCONFIRMED` は Proxy の戻り値であり、Store には `intent_pending` が残る
- **redaction_policy なしに本文や文脈を保存する**: `ActionEnvelope` に適切な `redaction_policy` を設定する
- **PolicyGate の deny を例外処理だけで握り潰す**: `REJECTED` は呼び出し元まで伝播させる
- **Reconciliation の診断を確定的真実として扱う**: 診断は最尤推定。confidence を確認する

## 11. テストを書く順序

1. 不変条件を壊す赤テストを書く（例: envelope なしで write_file を呼ぶ）
2. 実装で緑にする
3. 正常系・エラー系・境界系の回帰テストを追加する

```bash
make test
```

## セットアップ

```bash
git clone https://github.com/zyx-corporation/koguchi.git
cd koguchi
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 次のステップ

- [AuditGate Integration](auditgate-integration.md) — アプリケーションへの組み込み詳細
- [Reconciliation v2](reconciliation-v2.md) — 外部 API 照合
- [Roadmap](../roadmap.md) — 全体フェーズ計画
- [ADR](../adr/) — 設計判断の正本
