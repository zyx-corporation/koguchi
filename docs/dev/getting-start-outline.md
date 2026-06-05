# Koguchi 入門技術マニュアル

## 外部副作用を監査可能にする最小実装ガイド

作成者: Tomoyuki Kano
対象: Koguchi を初めて利用する開発者
想定ユースケース: JouJou における Todo 作成の監査
状態: Draft v0.2

## 1. このマニュアルの目的

このマニュアルは、Koguchi を初めて利用する開発者が、外部副作用を安全に記録するコードを書けるようになることを目的とする。

Koguchi は、AIエージェントやアプリケーションが外部世界へ副作用を起こすとき、その実行前後を監査可能な event log として残すための小さな基盤である。

ここでいう副作用とは、関数の戻り値を返すだけではなく、外部状態を変える操作を指す。

たとえば、次のような操作である。

```text
- ファイルを書き込む
- GitHub Issue を作成する
- Notion Page を作成する
- Google Tasks に Todo を追加する
- 外部 API に POST する
- データベースに record を追加する
```

Koguchi の Phase 1 実装では、まず `filesystem.write` を対象にしている。しかし、このマニュアルでは JouJou の Todo 作成を例にしながら、外部 API 書き込みにも同じ考え方をどう適用するかを説明する。

## 2. Koguchi が解決する問題

AIエージェントや MCP tool は、外部システムへの操作を簡単に実行できる。

たとえば、JouJou では AIクライアントから `create_todo` が呼ばれ、GitHub Issues や Notion Tasks DB に Todo を作成する。

このとき、Provider を直接呼ぶだけなら実装は簡単である。

```python
result = await github_provider.create_todo(todo)
```

しかし、この書き方では問題がある。

外部 API の呼び出し前に、何を実行しようとしていたのかが記録されない。

外部 API の呼び出し後に、何が成功したのかが監査できない。

外部 API への作成は成功したが、ローカル記録に失敗した場合、状態が不確定になる。

失敗したと思って再実行すると、GitHub Issue や Notion Page が重複する可能性がある。

Koguchi はこの問題に対して、外部副作用の前後を append-only event として記録する。

基本は次の流れである。

```text
1. ActionEnvelope を作る
2. intent_pending を Store に記録する
3. 外部副作用を実行する
4. 成功なら execution_committed を記録する
5. 失敗なら execution_failed を記録する
6. 実行後の記録に失敗したら UNCONFIRMED として扱う
```

重要なのは、Koguchi が「失敗をなかったことにする」仕組みではないという点である。

外部世界に副作用が起きたあと、その事実を取り消せない場合がある。Koguchi はその不可逆性を前提に、少なくとも「どこまで記録され、どこから不確定になったか」を見える形で残す。

## 3. 最小構成

Koguchi の最小構成は、次の要素から成る。

```text
ActionEnvelope
ExecutionEvent
ProxyResult
ExecutionStore
ToolProxy または AuditGate
Reconciliation
```

それぞれの役割は次の通りである。

`ActionEnvelope` は、実行しようとしている副作用の封筒である。何を、どのツールで、どの対象に、どの権限で実行するのかを表す。

`ExecutionEvent` は、監査ログに保存される event である。`intent_pending`、`execution_committed`、`execution_failed`、`reconciliation_observed` などを記録する。

`ProxyResult` は、呼び出し側に返す実行結果である。`SUCCESS`、`FAILURE`、`REJECTED`、`UNCONFIRMED` がある。

`ExecutionStore` は、event を append-only に保存する Store である。Phase 1 では SQLite を使う。

`ToolProxy` は、副作用を実際に通す隘路である。Phase 1 では `write_file()` が実装されている。

`AuditGate` は、アプリケーション側から Koguchi を使いやすくするための抽象レイヤーである。JouJou では `KoguchiAuditGate` として利用する。

`Reconciliation` は、監査ログと外部状態をあとから照合する仕組みである。

## 4. Koguchi の基本状態

Koguchi では、状態を一つの値として単純化しない。

特に重要なのは、Store の event、Proxy の戻り値、reconciliation の診断を分けることである。

```text
Store の event:
- intent_pending
- execution_committed
- execution_failed
- reconciliation_observed

Proxy / AuditGate の戻り値:
- SUCCESS
- FAILURE
- REJECTED
- UNCONFIRMED

reconciliation の診断:
- pending_not_executed
- pending_executed_unconfirmed
- unrecorded_external_change
- committed_consistent
- committed_diverged
```

`UNCONFIRMED` は Store に保存される event ではない。

これは重要である。

`UNCONFIRMED` とは、外部副作用は成功した可能性があるが、その結果を Store に確定記録できなかった状態である。もし Store に `UNCONFIRMED` と書けるなら、それはすでに記録できていることになる。したがって、Store 上には `intent_pending` が残り、呼び出し側には `UNCONFIRMED` が返る。

あとから reconciliation が、その pending record を見て、外部状態と照合する。

## 5. まず filesystem.write を理解する

Koguchi Phase 1 の最小対象は `filesystem.write` である。

典型的な利用コードは次の形になる。

```python
from koguchi.envelope import ActionEnvelope
from koguchi.proxy import ToolProxy
from koguchi.store import SQLiteExecutionStore

store = SQLiteExecutionStore("koguchi.db")
proxy = ToolProxy(
    workspace_dir="./workspace",
    store=store,
)

envelope = ActionEnvelope(
    action_id="write-001",
    tool="filesystem.write",
    target="./workspace/out.txt",
    parameters_digest="sha256-of-input",
    expected_result_digest="sha256-of-output",
    permission_scope="workspace:write",
    risk_class=["filesystem_write"],
    redaction_policy="without_context",
)

result = proxy.write_file(
    envelope=envelope,
    content=b"hello koguchi\n",
)

print(result)
```

このコードでは、`proxy.write_file()` が呼ばれる前に `ActionEnvelope` を作る。

Koguchi はこの envelope に基づき、まず `intent_pending` を Store に記録する。これに失敗した場合、ファイル書き込みは実行されない。

その後、実際にファイルを書き込む。

ファイル書き込みに成功し、`execution_committed` を Store に記録できれば `SUCCESS` が返る。

ファイル書き込み前に拒否された場合は `REJECTED`、実行に失敗した場合は `FAILURE`、ファイル書き込みには成功したが commit 記録に失敗した場合は `UNCONFIRMED` になる。

## 6. ActionEnvelope の書き方

`ActionEnvelope` は、副作用を実行するための最小監査単位である。

```python
ActionEnvelope(
    action_id="...",
    tool="...",
    target="...",
    parameters_digest="...",
    expected_result_digest="...",
    permission_scope="...",
    risk_class=[...],
    redaction_policy="...",
)
```

`action_id` は、その副作用を一意に識別する ID である。通常は UUID を使う。

`tool` は、どの種類の副作用かを表す。例として `filesystem.write`、`todo.create`、`github.issue.create` などが考えられる。

`target` は、副作用の対象である。ファイルならパス、GitHub Issue なら repo、Notion Page なら database ID などになる。

`parameters_digest` は、入力パラメータの digest である。本文や機密情報をそのまま保存せず、ハッシュで記録する。

`expected_result_digest` は、期待される結果の digest である。決定論的な操作では有効である。非決定論的な外部 API では `None` でもよい。

`permission_scope` は、必要な権限範囲である。たとえば `workspace:write`、`todo:create:github` などを使う。

`risk_class` は、その副作用のリスク分類である。たとえば `external_api_write`、`todo_creation`、`filesystem_write` などを指定する。

`redaction_policy` は、監査ログにどこまで情報を残すかを示す。

## 7. JouJou の create_todo に Koguchi を組み込む

ここから JouJou を例にする。

JouJou では、AIクライアントから Todo 作成要求が来る。

```python
class TodoInput(BaseModel):
    title: str
    body: str | None = None
    target: str | None = None
    source: str = "manual"
    context_summary: str | None = None
```

Provider を直接呼ぶのではなく、次のように AuditGate を挟む。

```python
class TodoService:
    def __init__(self, router, providers, audit_gate):
        self.router = router
        self.providers = providers
        self.audit_gate = audit_gate

    async def create_todo(self, todo, intent, context=None):
        provider_name = self.router.route(todo)
        provider = self.providers[provider_name]

        record_id = await self.audit_gate.before_create_todo(
            todo=todo,
            intent=intent,
            context=context,
        )

        try:
            result = await provider.create_todo(todo)
        except Exception as error:
            await self.audit_gate.after_create_todo_failure(
                record_id=record_id,
                todo=todo,
                error=error,
            )
            raise

        await self.audit_gate.after_create_todo_success(
            record_id=record_id,
            todo=todo,
            result=result,
        )

        result.audit_record_id = record_id
        return result
```

この構造により、Provider 実行前に必ず監査 record が作られる。

`before_create_todo()` が失敗した場合、Provider は呼ばれない。

Provider が成功した後、`after_create_todo_success()` が失敗した場合、外部副作用はすでに起きている可能性がある。そのため、通常の成功として返してはいけない。この場合は `UNCONFIRMED` 相当として扱う必要がある。

## 8. KoguchiAuditGate の最小実装イメージ

JouJou で Koguchi を使う場合、`KoguchiAuditGate` は `TodoInput` を `ActionEnvelope` に変換し、Koguchi の Store に event を積む。

最小イメージは次の通りである。

```python
import hashlib
import json
import uuid
from datetime import datetime, timezone

from koguchi.envelope import ActionEnvelope
from koguchi.events import ExecutionEvent
from koguchi.hashchain import compute_hash
from koguchi.store import SQLiteExecutionStore


def digest_object(obj) -> str:
    data = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


class KoguchiAuditGate:
    def __init__(self, store: SQLiteExecutionStore):
        self.store = store

    async def before_create_todo(self, todo, intent, context=None) -> str:
        record_id = str(uuid.uuid4())

        envelope = ActionEnvelope(
            action_id=record_id,
            tool="todo.create",
            target=f"todo:{todo.target or 'auto'}",
            parameters_digest=digest_object(todo.model_dump()),
            expected_result_digest=None,
            permission_scope=f"todo:create:{todo.target or 'auto'}",
            risk_class=["external_api_write", "todo_creation"],
            redaction_policy="without_context",
        )

        previous_hash = self.store.last_hash()

        event = ExecutionEvent(
            event_id=str(uuid.uuid4()),
            record_id=record_id,
            timestamp=datetime.now(timezone.utc),
            event_type="intent_pending",
            envelope=envelope,
            side_effect_observed="none",
            previous_hash=previous_hash,
            hash=compute_hash(
                previous_hash,
                {
                    "record_id": record_id,
                    "event_type": "intent_pending",
                    "tool": "todo.create",
                    "target": envelope.target,
                },
            ),
            intent=intent,
            context_ref=None,
            decision_ref=None,
        )

        self.store.append(event)
        return record_id

    async def after_create_todo_success(self, record_id, todo, result) -> None:
        previous_hash = self.store.last_hash()

        event = ExecutionEvent(
            event_id=str(uuid.uuid4()),
            record_id=record_id,
            timestamp=datetime.now(timezone.utc),
            event_type="execution_committed",
            result_digest=digest_object(result.model_dump()),
            side_effect_observed="confirmed",
            previous_hash=previous_hash,
            hash=compute_hash(
                previous_hash,
                {
                    "record_id": record_id,
                    "event_type": "execution_committed",
                    "external_id": result.external_id,
                },
            ),
        )

        self.store.append(event)

    async def after_create_todo_failure(self, record_id, todo, error) -> None:
        previous_hash = self.store.last_hash()

        event = ExecutionEvent(
            event_id=str(uuid.uuid4()),
            record_id=record_id,
            timestamp=datetime.now(timezone.utc),
            event_type="execution_failed",
            error_digest=hashlib.sha256(str(error).encode()).hexdigest(),
            side_effect_observed="unknown",
            previous_hash=previous_hash,
            hash=compute_hash(
                previous_hash,
                {
                    "record_id": record_id,
                    "event_type": "execution_failed",
                    "error": type(error).__name__,
                },
            ),
        )

        self.store.append(event)
```

このコードは説明用の最小例である。

実運用では、event 生成処理を共通化し、hash payload の canonical serialize を Koguchi 側の規約に合わせるべきである。

## 9. UNCONFIRMED をどう扱うか

Koguchi を使う上で最も重要なのは、実行後記録の失敗を通常成功にしないことである。

たとえば、JouJou で GitHub Issue を作る場合、次の順序になる。

```text
1. intent_pending を記録
2. GitHub API で Issue 作成
3. execution_committed を記録
```

問題は 2 は成功したが、3 に失敗した場合である。

この場合、GitHub Issue はすでに作られている可能性がある。しかしローカル Store には committed event がない。

この状態で通常の成功を返すと、利用者は「正常に記録された」と誤認する。

この状態で通常の失敗を返すと、利用者は再実行してしまい、Issue が重複する可能性がある。

したがって、Koguchi ではこの状態を `UNCONFIRMED` として扱う。

JouJou 側では、次のような例外または Result を用意する。

```python
class UnconfirmedSideEffectError(Exception):
    def __init__(self, record_id: str, provider: str, message: str):
        self.record_id = record_id
        self.provider = provider
        super().__init__(message)
```

`after_create_todo_success()` が失敗した場合は、この例外を返す。

```python
try:
    await self.audit_gate.after_create_todo_success(
        record_id=record_id,
        todo=todo,
        result=result,
    )
except Exception as error:
    raise UnconfirmedSideEffectError(
        record_id=record_id,
        provider=provider_name,
        message="Todo may have been created, but audit commit failed.",
    ) from error
```

利用者や上位アプリケーションは、この状態を見たら即座に再実行してはいけない。

まず外部システムを確認し、すでに作成されているかどうかを調べる。

## 10. Reconciliation の最小実装方針

Reconciliation は、Store に残った pending record と外部状態を照合する処理である。

filesystem.write の場合は workspace を見ればよい。

JouJou のような外部 API の場合は、Provider ごとに照合方法が必要になる。

GitHub Issues なら、作成時の title、labels、metadata、あるいは body に埋め込んだ audit marker を使って照合する。

Notion なら、Page property に audit record ID を保存して照合する。

Google Tasks なら、notes や title に最小の audit marker を残すか、外部IDの保存が必要になる。

JouJou では、MVP段階では外部 API 照合を後回しにしてもよい。ただし、次の確認は初期から実装した方がよい。

```text
- pending のまま閉じていない record があるか
- execution_committed があるか
- execution_failed があるか
- hash chain が壊れていないか
```

将来的には、Provider ごとに次のような interface を用意できる。

```python
class ReconciliableProvider(Protocol):
    async def find_by_audit_record_id(self, record_id: str):
        ...

    async def exists(self, external_id: str) -> bool:
        ...
```

## 11. テスト駆動で書くべき最初のテスト

Koguchi を利用するコードでは、最初に正常系を書くよりも、不変条件を破るテストから書く。

JouJou であれば、最初のテストは次のようになる。

```python
async def test_provider_is_not_called_when_audit_before_fails():
    ...
```

これは、`before_create_todo()` が失敗したら外部副作用を起こしてはいけない、というテストである。

次に、Provider 成功後の audit commit 失敗をテストする。

```python
async def test_provider_success_but_audit_commit_failure_returns_unconfirmed():
    ...
```

これは、外部副作用が成功した可能性がある状態を、通常成功にも通常失敗にもしてはいけない、というテストである。

Provider 失敗時の記録も必要である。

```python
async def test_provider_failure_records_execution_failed():
    ...
```

さらに、Provider を直接呼ぶ経路を作らないための設計テストも考えられる。

```python
async def test_todo_service_routes_all_create_operations_through_audit_gate():
    ...
```

## 12. よくある実装ミス

### Provider を直接呼んでしまう

悪い例:

```python
await github_provider.create_todo(todo)
```

これは AuditGate を迂回する。

良い例:

```python
await todo_service.create_todo(todo, intent="Create GitHub Issue")
```

### audit before の失敗後に Provider を呼んでしまう

`intent_pending` を書けない状態で外部 API を呼ぶと、監査記録のない副作用が生まれる。

これは Koguchi が最も避けたい状態である。

### audit success commit の失敗を普通の失敗にしてしまう

Provider 実行後に監査記録だけが失敗した場合、外部には作成済みの可能性がある。

これを通常失敗として扱うと、再実行によって重複作成が起きる。

### Todo本文を監査ログへそのまま保存しすぎる

監査ログは便利な debug log ではない。

本文、会話全文、個人情報、機密情報を無制限に保存してはいけない。

digest、要約、redaction policy を使う。

### UNCONFIRMED を Store に書こうとする

`UNCONFIRMED` は Store の event ではない。

Store には `intent_pending` が残る。呼び出し側に `UNCONFIRMED` 相当の結果または例外を返す。あとから reconciliation で回収する。

## 13. 実装チェックリスト

Koguchi を利用するコードを書くときは、最低限次を満たす。

```text
[ ] 外部副作用を直接呼ばず、Proxy または AuditGate を通している
[ ] 副作用前に intent_pending を記録している
[ ] intent_pending 記録失敗時に副作用を起こさない
[ ] 副作用成功後に execution_committed を記録している
[ ] 副作用失敗時に execution_failed を記録している
[ ] 副作用成功後の commit 記録失敗を UNCONFIRMED として扱っている
[ ] 入力本文や会話全文を無制限に平文保存していない
[ ] parameters_digest / result_digest / error_digest を使っている
[ ] reconciliation のための record_id または external_id を保持している
[ ] テストで before failure / provider failure / after failure を分けている
```

## 14. JouJou での推奨統合形

JouJou では、Koguchi を直接アプリケーション全体に散らさない。

推奨は、`joujou_core.audit.koguchi_gate.KoguchiAuditGate` に閉じ込めることである。

```text
joujou-core/
  src/joujou_core/
    audit/
      gate.py
      null_gate.py
      koguchi_gate.py
```

`TodoService` は AuditGate Protocol だけを知る。

`KoguchiAuditGate` は Koguchi の `ActionEnvelope`、`ExecutionEvent`、`SQLiteExecutionStore` を知る。

Provider は Koguchi を知らない。

この分離により、将来 `NullAuditGate`、`PostgresAuditGate`、`OpenTelemetryAuditGate`、`KotonohaAuditGate` へ差し替えることができる。

## 15. まとめ

Koguchi を利用するコードを書くときの中心原則は単純である。

外部副作用の前に記録する。

記録できなければ実行しない。

実行後に結果を記録する。

実行後の記録に失敗したら、成功扱いしない。

不確定なものは不確定なものとして残す。

Koguchi は、外部副作用を完全に無害化する仕組みではない。むしろ、外部世界に触れる操作が不可逆であることを前提に、その痕跡を見失わないための仕組みである。

JouJou の Todo 作成は、Koguchi の最初の実用例として分かりやすい。

AIとの会話から生まれた「用向き」を GitHub Issue や Notion Task に変換する。そのとき、便利さだけを優先して Provider を直接呼ぶのではなく、KoguchiAuditGate を通す。

それにより、AI協働の小さな作業も、あとから人間が引き受けられる形で残る。
