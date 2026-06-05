# T-RDE

Test-level RDE — 意味変化をテストで監査するための補助。

## RDE は自動裁定器ではない

RDE は、生成物や外部副作用が元の意図からどう変化したかを分類するための監査構造である。「良い/悪い」を自動判定しない。

ΔM は価値そのものではない。分類のための測度であり候補である。

## RdeHint

```python
from koguchi import RdeHint

hint = RdeHint(
    preserved=[
        "GitHub Issue として作成する",
        "Koguchi の hash chain 検証 API を追加する",
    ],
    transformed=[
        "会話中の作業意図を Issue title/body に圧縮した",
    ],
    unresolved=[
        "verify_chain() を Protocol に含めるか SQLite 実装に限定するか",
    ],
    risks=[
        "監査可能性を hash の存在だけで満たしたと誤解する",
    ],
    next_policy="ADR で verify_chain の抽象境界を決める",
)
```

## T-RDE helpers

```python
from koguchi import assert_preserved, assert_risk_declared, assert_no_unresolved_hidden

# preserved に特定の項目が含まれているか
assert_preserved(hint, "GitHub Issue として作成する")

# risks に特定のキーワードが含まれているか
assert_risk_declared(hint, "監査可能性")

# unresolved がある場合、対応する risks も宣言されているか
assert_no_unresolved_hidden(hint)
```

## Redaction との関係

RDE hint には元意図やリスクが自然言語で入る。したがって:

- RDE hint は監査ログと同じく debug note ではない
- 個人情報や secret を書かない
- 公開 export では RDE hint も redaction 対象にする
- risks / unresolved に機密情報を直接書かない

## 次のステップ

- [Getting Started](getting-started.md) — Koguchi の基本使い方
- [AuditGate Integration](auditgate-integration.md) — アプリケーションへの組み込み
- [Roadmap](../roadmap.md) — 全体フェーズ計画
