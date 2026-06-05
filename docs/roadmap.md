# Koguchi 全体ロードマップ

## Side-Effect Chokepoint から CAH 基盤へ

作成者: Tomoyuki Kano
対象リポジトリ: `zyx-corporation/koguchi`
状態: Draft v0.2
関連ユースケース: JouJou / `joujou-core` / `joujou-todo-mcp`
参照: [Getting Started](dev/getting-started.md) | [AuditGate Integration](dev/auditgate-integration.md) | [Reconciliation v2](dev/reconciliation-v2.md) | [ADR](adr/) | [README](../README.md)

## 実装進捗

| Phase | 名称 | 状態 | 主成果物 |
| -----:| ---- | ---- | -------- |
| 0 | Foundation | ✅ | README, ADR 001-003, SLS+RDE 開発手法 |
| 1 | Side-Effect Chokepoint | ✅ | ToolProxy, ActionEnvelope, ExecutionStore, UNCONFIRMED, hash chain, reconciliation, ADR 004-005,007-008 |
| 2 | Decision Logger | ✅ | Decision, DecisionStore, decision_ref, intent, context_ref, Context Resolver, ADR 006,009-011 |
| 3 | Policy Gate | ✅ | PolicyDecision, PolicyRule, ExecutionPolicyGate, DenyShellExecution, ADR 012,014 |
| 4 | AuditGate Integration | ✅ | AuditGate Protocol, KoguchiAuditGate, AuditResult, ADR 015 |
| 5 | Reconciliation v2 | ✅ | ReconciliableProvider, ProviderReconciler, ADR 013,016 |
| 6 | Redaction / Secret Safety | Next | redacted view, safe audit export, secret/PII guard |
| 7 | RDE / T-RDE | Planned | RdeHint, RdeReview, T-RDE tests |
| 8 | Multi-tool / Multi-provider | Planned | GitHub / Notion / Google Tasks, Provider adapter |
| 9 | Runtime Hardening | Planned | sandbox, seccomp, Rust chokepoint |
| 10 | Service Runtime | Planned | daemon, API, dashboard |

## 1. 位置づけ

Koguchi は、AIエージェントやアプリケーションが外部世界へ副作用を起こすとき、その副作用を監査可能な来歴へ変換するための基盤である。

ここでいう副作用とは、単なる内部計算や応答生成ではなく、外部状態を変える操作を指す。たとえば、ファイルを書き込む、GitHub Issue を作成する、Notion Page を作成する、Google Tasks に Todo を追加する、外部 API に POST する、データベースに record を追加する、といった操作である。

Koguchi の中核は、Side-Effect Chokepoint、すなわち「副作用の隘路」である。外部副作用を複数の経路から自由に発生させるのではなく、必ず監査可能な単一経路を通す。これにより、実行前の意図、実行後の結果、失敗、不確定状態を後から確認できるようにする。

Koguchi は、単なる安全な Tool Runtime ではない。副作用の実行を制御するだけでなく、その副作用がどの文脈から発生し、どの判断を経由し、どの結果を生み、どの意味変化を含んだかを、段階的に接続していくための CAH（Context-Aware Harness）基盤である。

ただし、最初から CAH 全体を作るのではない。最初に固めるべきなのは、後から取り返しがつかない不可逆境界である。副作用経路が分裂すると、監査基盤は最初から穴を持つ。したがって Koguchi は、Side-Effect Chokepoint から始める。

## 2. 基本方針

Koguchi の開発は、次の方針に基づく。

第一に、外部副作用を必ず監査可能な経路に通す。

第二に、副作用実行前に intent を記録する。記録できない場合、実行しない。

第三に、副作用実行後に結果を記録する。結果記録に失敗した場合、成功扱いしない。

第四に、外部世界の不可逆性を直視する。記録は副作用を取り消せない。したがって、不確定状態を隠さず `UNCONFIRMED` として扱う。

第五に、最初は完全封じ込めではなく検出から始める。Python Phase では副作用経路の完全封じ込めは難しいため、reconciliation によって記録と実態の乖離を検出する。

第六に、本文や会話文脈を無制限に平文保存しない。digest、summary、redaction policy を使う。

第七に、Koguchi を単なる Tool Proxy に縮退させない。`intent`、`decision_ref`、`context_ref` を通じて Decision Logger、Context Resolver、RDE へ接続できる構造を維持する。

## 3. 全体フェーズ一覧

| Phase | 名称                          | 主目的                    | 主成果物                                                   |
| ----: | --------------------------- | ---------------------- | ------------------------------------------------------ |
|     0 | Foundation                  | 仕様・ADR・開発手法の整備         | README, ADR, docs, SLS/RDE 開発手法                        |
|     1 | Side-Effect Chokepoint      | `filesystem.write` の監査 | ToolProxy, ActionEnvelope, ExecutionStore, UNCONFIRMED |
|     2 | Decision Logger             | なぜ実行したかを記録             | DecisionRecord, DecisionStore, decision_ref            |
|     3 | Policy Gate                 | 実行前許可判定                | PolicyDecision, allow/deny/require_approval            |
|     4 | AuditGate Integration       | JouJou 等へ組み込み          | KoguchiAuditGate                                       |
|     5 | Reconciliation v2           | 外部 API 実状態との照合         | Provider reconciliation                                |
|     6 | Redaction / Secret Safety   | 平文ログ最小化                | redacted view, redaction policy                        |
|     7 | RDE / T-RDE                 | 意味変化監査                 | RDE hints, T-RDE tests                                 |
|     8 | Multi-tool / Multi-provider | 副作用型の拡張                | GitHub / Notion / Google Tasks 等                       |
|     9 | Runtime Hardening           | 実行境界の強化                | sandbox, seccomp, Rust chokepoint                      |
|    10 | Service Runtime             | 共通監査サービス化              | daemon, API, dashboard                                 |

## 4. Phase 0: Foundation

Phase 0 は、Koguchi が何であり、何でないかを固定する段階である。

Koguchi は、外部副作用を監査可能な来歴へ変換する Side-Effect Chokepoint である。安全な Tool Runtime、MCP server、単なるログライブラリ、RDE evaluator そのものではない。これらと接続可能ではあるが、Koguchi の最初の責務は、副作用経路の単一化と監査可能化である。

Phase 0 では、リポジトリ基盤、README、設計仕様、ADR、開発手法、テスト方針を整備する。

主な成果物は次である。

```text
README.md
docs/adr/
docs/method/
Phase 1 設計仕様
SLS + RDE 開発手法
TDD 方針
RDE review guide
```

Phase 0 の完了条件は、Koguchi の設計判断が ADR として記録され、Phase 1 の赤テストを書き始められる状態になっていることである。

## 5. Phase 1: Side-Effect Chokepoint

Phase 1 は、Koguchi の最初の中核実装である。

目的は、外部副作用を必ず `ActionEnvelope`、`ToolProxy`、`ExecutionStore` を通して実行し、実行前後を append-only event として記録することである。

対象は最初は `filesystem.write` のみでよい。重要なのは対象範囲の広さではなく、不変条件を守ることである。

Phase 1 の主な要素は次である。

```text
ActionEnvelope
ProxyResult
ExecutionEvent
SQLiteExecutionStore
ToolProxy.write_file()
hash chain
reconciliation
UNCONFIRMED
```

Phase 1 の不変条件は次である。

```text
INV-1  管理対象副作用は Envelope + Proxy + Store を通る
INV-1a Envelope なしの扱いを明確化する
INV-1b intent_pending を書けなければ実行しない
INV-1c 迂回は初期段階では prevention ではなく reconciliation で検出する
```

`intent_pending` は副作用実行前に記録される。これを書けない場合、副作用は実行しない。

`execution_committed` は副作用成功後に記録される。副作用は成功したが commit 記録に失敗した場合、`SUCCESS` を返してはならない。この状態は `UNCONFIRMED` として扱う。

`UNCONFIRMED` は Store の event ではない。Store には `intent_pending` が残る。呼び出し側には `UNCONFIRMED` が返る。あとから reconciliation が pending record と外部状態を照合し、`pending_executed_unconfirmed` などの診断を行う。

Phase 1 の直近課題は次である。

```text
#7  親ディレクトリ作成副作用の扱い
#8  Envelopeなしの扱い
#9  ExecutionStore.committed()
#10 hash chain verify_chain()
```

Phase 1 の完了条件は、`filesystem.write` の赤テストが緑であり、hash chain 検証 API、reconciliation、ADR-003 の判断、getting started 文書への導線が揃っていることである。

## 6. Phase 2: Decision Logger

Phase 1 は「何を実行したか」を記録する。Phase 2 は「なぜ実行したか」を記録する。

ただし、ここで Chain of Thought をそのまま保存してはならない。保存対象は、推論全文ではなく、副作用を正当化するための decision summary、intent、user request reference、policy decision、context reference である。

Phase 2 の主な要素は次である。

```text
DecisionRecord
DecisionStore
decision_ref
intent summary
user_request_digest
approval_state
```

`DecisionRecord` は、外部副作用がどの判断に基づいて実行されたかを表す。

たとえば JouJou では、「この Todo はどの会話から、どの作業意図として、どの Provider に送られたのか」を記録する。

Phase 2 の完了条件は、`ExecutionEvent.decision_ref` が実際の `DecisionRecord` に接続され、外部副作用の「なぜ」が監査可能になることである。

## 7. Phase 3: Policy Gate

Phase 3 は、実行前に「これは実行してよい副作用か」を判定する段階である。

Phase 1 では、workspace boundary や envelope required などの最小制約だけを扱う。Phase 3 では、より一般的な policy 判定を導入する。

Policy Gate が扱うルールの例は次である。

```text
対象 workspace 外への書き込みは禁止
任意 shell 実行は禁止
Todo 削除は禁止
Provider token のログ保存は禁止
センシティブ本文の full logging 禁止
GitHub Issue 作成は許可
Notion Page 作成は許可
Google Tasks 作成は許可
```

Policy Gate の結果は、単純な boolean ではなく、少なくとも次を持つ。

```text
allow
deny
require_approval
```

Phase 3 の主な成果物は次である。

```text
PolicyGate
PolicyDecision
PolicyRule
PolicyViolation
policy test
```

Phase 3 の完了条件は、ToolProxy / AuditGate が Provider 実行前に必ず PolicyGate を通り、deny の場合は外部副作用を起こさないことである。

## 8. Phase 4: AuditGate Integration

Phase 4 では、Koguchi を実アプリケーションへ組み込む。

最初の対象は JouJou である。JouJou では、AIクライアントから発生した Todo 作成要求を、GitHub Issues、Notion Tasks DB、Google Tasks などへ渡す。そのとき外部システムへの作成操作は副作用であり、Koguchi の監査対象になる。

JouJou における統合形は次である。

```text
JouJou TodoService
  ↓
AuditGate Protocol
  ↓
KoguchiAuditGate
  ↓
ExecutionStore / DecisionStore / PolicyGate
  ↓
GitHub Issues / Notion / Google Tasks
```

重要なのは、Koguchi をアプリケーション全体へ散らさないことである。JouJou の `TodoService` は `AuditGate` Protocol だけを知る。Koguchi 固有の `ActionEnvelope`、`ExecutionEvent`、`SQLiteExecutionStore` は `KoguchiAuditGate` に閉じ込める。

Provider は Koguchi を知らない。Provider は外部 API を実行するだけである。Provider を直接呼ぶのではなく、必ず `TodoService` と `AuditGate` を経由する。

Phase 4 の完了条件は、JouJou の `create_todo` が Provider を直接呼ばず、必ず `KoguchiAuditGate` を通ることである。

## 9. Phase 5: Reconciliation v2

Phase 1 の reconciliation は、主に Store と workspace の照合である。Phase 5 では、外部 API の実状態と照合する。

JouJou の場合、GitHub Issue、Notion Page、Google Task が実際に存在するかどうかを確認する必要がある。

たとえば、GitHub Issue 作成で `UNCONFIRMED` が発生した場合、次のように照合する。

```text
pending のままの GitHub Issue 作成 record がある
  ↓
GitHub API を検索する
  ↓
audit_record_id / title / metadata から外部 Issue を探す
  ↓
見つかれば pending_executed_unconfirmed
  ↓
見つからなければ pending_not_executed
```

Provider ごとに reconciliation strategy を用意する。

```python
class ReconciliableProvider(Protocol):
    async def find_by_audit_record_id(self, record_id: str):
        ...

    async def exists(self, external_id: str) -> bool:
        ...
```

Phase 5 の完了条件は、`UNCONFIRMED` や pending record を、GitHub / Notion / Google Tasks などの外部状態と照合できることである。

## 10. Phase 6: Redaction / Secret Safety

Phase 6 では、監査ログに何を保存してよいかを本格的に扱う。

Koguchi は監査基盤であるが、監査ログは debug log ではない。Todo本文、会話全文、個人情報、Provider token、機密情報を無制限に平文保存してはならない。

初期から `redaction_policy` は器として用意されている。この Phase で、実際に redaction view を提供する。

想定する redaction policy は次である。

```text
full             デバッグ用。原則非推奨
without_context  通常利用
without_intent   意図自体がセンシティブな場合
minimal          共有・外部出力向け
```

Phase 6 の主な成果物は次である。

```text
RedactionPolicy
redacted view
safe export
secret scanner
log inspection tool
```

Phase 6 の完了条件は、`ActionEnvelope`、`DecisionRecord`、`ExecutionEvent` に対して、用途別の redacted view が提供されることである。

## 11. Phase 7: RDE / T-RDE

Phase 7 で、Koguchi は単なる副作用監査から、意味変化監査へ接続する。

対象は、外部副作用そのものだけではない。ユーザーの元意図が、Todo title、Issue body、Provider target、context_summary に変換される過程を監査する。

JouJou では、たとえば次のような検査が必要になる。

```text
会話意図が Todo title に過剰圧縮されていないか
context_summary が元意図を歪めていないか
rde.preserved が保存されているか
target routing が不自然に変換されていないか
実装上の都合で思想的主張が変形していないか
```

Phase 7 では、少なくとも手動または半自動で次の分類ができるようにする。

```text
preserved
transformed
supplemented
unresolved
risks
next_policy
```

Phase 7 の完了条件は、外部副作用の「実行されたかどうか」だけでなく、「元意図からどのように意味が変化したか」を監査できることである。

## 12. Phase 8: Multi-tool / Multi-provider

Phase 8 では、副作用対象を増やす。

対象候補は次である。

```text
filesystem.write
todo.create
github.issue.create
notion.page.create
google_task.create
calendar.event.create
note.create
inbox.append
```

ただし、削除、一括更新、任意 HTTP、任意 shell は慎重に後回しにする。

この Phase の目的は、「何でもできるツール」にすることではない。許可された副作用型を、安全に少しずつ増やすことである。

副作用型を追加するときは、必ず次を用意する。

```text
ActionEnvelope adapter
Policy rule
ExecutionEvent mapping
Reconciliation strategy
Redaction rule
TDD test
T-RDE test
```

Phase 8 の完了条件は、Provider ごとの ActionEnvelope adapter と reconciliation strategy があり、複数の副作用型を同じ監査構造で扱えることである。

## 13. Phase 9: Runtime Hardening

Phase 9 では、実行境界を強化する。

Phase 1 では、迂回経路を完全には防がず、reconciliation で検出するところから始めた。Phase 9 では、より強い prevention を導入する。

候補は次である。

```text
workspace isolation
container execution
seccomp
Linux namespace
macOS sandbox
Rust implementation of chokepoint
capability-based permission
```

Rust 化はこの Phase で検討するのが自然である。初期から Rust に寄せると、まだ揺れているスキーマの変更が重くなる。しかし Phase 9 では、副作用隘路の型と境界が固まっているため、Rust の強みが出る。

Phase 9 の完了条件は、迂回経路を reconciliation で検出するだけでなく、実行環境としてもかなり抑制できることである。

## 14. Phase 10: Service Runtime

Phase 10 では、Koguchi をライブラリから常駐基盤へ広げる。

候補は次である。

```text
koguchi daemon
local audit service
MCP gateway integration
HTTP API
gRPC API
OpenTelemetry export
audit dashboard
```

JouJou、Kotonoha、Sayane、他の MCP tool が、同じ Koguchi daemon を使って副作用監査する構成が見えてくる。

この段階で、Koguchi は単一ライブラリではなく、ローカルファーストな監査サービスとなる。

Phase 10 の完了条件は、複数アプリケーションが共通の Koguchi audit service を使えることである。

## 15. 推奨実装順（更新）

実装済みの Phase 0〜5 に続き、推奨する次ステップは以下である。

```text
Phase 1〜5 実装済み ✅
  ↓
Phase 6 Redaction / Secret Safety（Next）
  ↓
Phase 7 RDE / T-RDE
  ↓
Phase 8 Multi-provider（JouJou 実運用統合）
  ↓
Phase 9 Runtime Hardening
  ↓
Phase 10 Service Runtime
```

理由は、監査ログが audit export 可能になる前に redaction を固める必要があるからである。安全な開示制御なしに audit export を広げると、secret / token / PII の漏洩リスクが残る。

## 16. Koguchi の三つの発展軸

Koguchi の発展は、単なる機能追加ではなく、三つの軸で考える。

第一の軸は、副作用対象の拡張である。

```text
filesystem.write
→ todo.create
→ issue.create
→ note.create
→ calendar.create
→ controlled update
```

第二の軸は、監査深度の拡張である。

```text
what happened
→ why it happened
→ whether it was allowed
→ whether meaning changed
→ whether humans can assume responsibility
```

第三の軸は、実行境界の強化である。

```text
library convention
→ ToolProxy
→ PolicyGate
→ reconciliation
→ sandbox
→ daemon / service
→ hardened runtime
```

この三軸を混同してはならない。

`filesystem.write` から `todo.create` へ増やすこと、PolicyGate を入れること、Rust 化することは、それぞれ別の前進である。全部を一度にやろうとすると、Koguchi は重くなりすぎる。

## 17. 直近の優先課題（更新）

Phase 0〜5 が完了した現在、直近の優先課題は以下である。

```text
Phase 6: Redaction / Secret Safety
  - redacted view の運用整理
  - safe audit export の設計
  - secret / token / PII の漏洩防止テスト
  - docs/ops/audit-export.md

Phase 7: RDE / T-RDE
  - RdeHint スキーマ定義
  - RdeReview metadata
  - T-RDE テスト例
```

Phase 1 の Issue #7〜#10 はすべて解決済みである。

## 18. RDE 差異検証（v0.2 更新）

### 18.1 保存された要素

Koguchi は、外部副作用を監査可能な来歴へ変換する Side-Effect Chokepoint である。

Phase 1 では、`ActionEnvelope`、`ToolProxy`、`ExecutionStore`、`UNCONFIRMED`、reconciliation を中核にする。

JouJou は Koguchi の最初の実用ユースケースとして扱うが、Koguchi は JouJou 専用ではない。

### 18.2 変換された要素

初期の filesystem.write 中心の仕様から、JouJou の Todo 作成、GitHub Issue 作成、Notion Page 作成などの外部 API 書き込みへ拡張するロードマップへ変換した。

ただし、実装順としては Phase 1 を先に固定し、Provider 拡張を急がない方針を維持した。

### 18.3 補完された要素

Decision Logger、Policy Gate、Reconciliation v2、Redaction、RDE / T-RDE、Multi-provider、Runtime Hardening、Service Runtime を追加した。

また、Koguchi の発展を「副作用対象」「監査深度」「実行境界」の三軸として整理した。

### 18.4 未解決の要素

DecisionRecord の詳細スキーマ。

PolicyGate のルール表現。

Provider reconciliation の具体的実装。

Redaction policy の実際の適用単位。

RDE 自動判定の範囲。

Rust 化の境界。

daemon 化の時期。

### 18.5 逸脱リスク

Koguchi が安全な Tool Runtime に縮退するリスク。

Koguchi が逆に巨大な CAH 全体を抱え込みすぎるリスク。

JouJou 統合を急ぎすぎて Phase 1 の不変条件が緩むリスク。

監査ログが debug log 化し、平文保存が増えすぎるリスク。

RDE を早期に自動化しすぎ、未検証の意味判断を確定済みに見せるリスク。

PolicyGate が責任主体であるかのように誤読されるリスク。PolicyGate は判断支援であり、人間の責任を代替しない。

Reconciliation が確定的真実を返すように誤解されるリスク。診断は最尤推定であり、外部ログとの突合が必要である。

Redaction 未整備のまま audit export が広がるリスク。secret / token / PII の漏洩が監査ログ経由で起こる。

### 18.6 次回更新方針

Phase 6 Redaction / Secret Safety の設計を具体化し、ADR を作成する。

Phase 7 RDE / T-RDE の RdeHint スキーマと T-RDE テスト例を定義する。

## 19. 結論

Koguchi のロードマップは、次の一文に圧縮できる。

外部副作用を、実行前の意図・実行後の結果・未確定状態・意味変化・責任帰属へと、段階的に接続していく。

最初の Phase 1 は小さいが、もっとも重要である。

ここで Side-Effect Chokepoint が壊れると、その後に Decision Logger や RDE を載せても、実行経路の穴は塞げない。

逆に、Phase 1 が堅ければ、JouJou、Kotonoha、Sayane、他の MCP tool に対して、Koguchi を共通の副作用監査基盤として展開できる。

Koguchi は、外部世界に触れる知性のための小さな虎口である。そこを通ったものだけが、あとから人間によって引き受け可能な来歴となる。
