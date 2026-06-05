# JouJou Integration

Koguchi を JouJou に組み込むための integration pattern。

## なぜ JouJou が Koguchi を使うのか

JouJou の `create_todo` は、AIクライアントの指示を GitHub Issues / Notion Pages / Google Tasks 等の外部 API に書き込む操作である。これは外部副作用であり、監査可能でなければならない。

## Todo 作成は外部副作用である

Todo 作成は単なる内部状態変更ではない。外部 API への書き込みを伴い、一度実行すると取り消せない。Koguchi の Side-Effect Chokepoint を通すことで、実行前の意図・実行後の結果・失敗・不確定状態を監査可能にする。

## Provider を直接呼んではいけない

```python
# ❌ 悪い例: Provider を直接呼ぶ
result = github_provider.create_issue(todo)

# ✅ 良い例: AuditGate を通す
record_id = audit_gate.before_create_todo(todo, intent)
result = provider.create_todo(todo)
audit_gate.after_create_todo_success(record_id, todo, result)
```

## KoguchiTodoAuditGate の責務

| メソッド | 責務 |
|----------|------|
| `before_create_todo` | ActionEnvelope 生成、intent_pending 記録、Policy Gate 判定 |
| `after_create_todo_success` | execution_committed 記録。失敗時は UnconfirmedSideEffectError |
| `after_create_todo_failure` | execution_failed 記録 |

## create_todo の正常系

```python
from koguchi.integrations.joujou import (
    KoguchiTodoAuditGate, TodoInput, TodoResult
)

store = SQLiteExecutionStore("audit.db")
gate = KoguchiTodoAuditGate("./workspace", store)

todo = TodoInput(title="Implement hash chain", target="koguchi")
record_id = gate.before_create_todo(todo, intent="Phase 1 core feature")
result = provider.create_todo(todo)
gate.after_create_todo_success(record_id, todo, result)
```

## Provider failure

```python
try:
    result = provider.create_todo(todo)
except Exception as error:
    gate.after_create_todo_failure(record_id, todo, error)
    raise
```

## Audit after success failure = UNCONFIRMED

```python
try:
    gate.after_create_todo_success(record_id, todo, result)
except UnconfirmedSideEffectError:
    # 副作用は成功したが audit commit に失敗
    # Store には intent_pending が残っている
    # Reconciliation で後から照合する
```

## RDE hint の渡し方

```python
from koguchi.rde import RdeHint

hint = RdeHint(
    preserved=["GitHub Issue として作成する"],
    risks=["過剰圧縮"],
)
todo = TodoInput(title="Task", rde=hint)
```

## Redaction policy

`create_todo` では `redaction_policy="without_context"` がデフォルト。
Todo 本文や context_summary は context_snapshot として保存されるが、export 時は policy に従って墨消しされる。

## Reconciliation の設計

GitHub Issue 作成時は audit_record_id を body / label / comment に残す。
UNCONFIRMED 発生時は `ProviderReconciler` が外部状態を照合する。

## 実装チェックリスト

- [ ] `before_create_todo` が intent_pending を記録する
- [ ] Policy Gate が DENY の場合 Provider を呼ばない
- [ ] Provider failure で execution_failed を記録する
- [ ] after audit failure を UNCONFIRMED として扱う
- [ ] RdeHint を TodoInput から渡せる
- [ ] redaction_policy が適切に設定されている

## 次のステップ

- [Getting Started](getting-started.md) — Koguchi の基本使い方
- [AuditGate Integration](auditgate-integration.md) — 汎用 AuditGate
- [Roadmap](../roadmap.md) — 全体フェーズ計画
