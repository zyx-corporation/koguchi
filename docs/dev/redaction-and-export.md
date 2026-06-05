# Redaction and Export

監査ログの安全な開示とエクスポート。

## なぜ redaction が必要か

Koguchi の監査ログは debug log ではない。Todo 本文、会話全文、intent、context_snapshot、Provider token、個人情報を無制限に保存・表示・export してはならない。

Redaction は、監査ログを「誰に・何を・どこまで」開示するかの制御層である。

## RedactionPolicy の使い分け

| Policy | 用途 | 開示内容 |
|--------|------|---------|
| `FULL` | デバッグのみ。本番 export には使わない | intent/context/envelope を含む全フィールド（ただし secret は常にマスク） |
| `WITHOUT_CONTEXT` | 通常利用のデフォルト | intent は開示、context_snapshot は非開示 |
| `WITHOUT_INTENT` | intent 自体がセンシティブな場合 | intent を `[REDACTED]` に、context_snapshot も非開示 |
| `MINIMAL` | 外部共有・サポート・公開用 | event_id, timestamp, event_type, side_effect_observed のみ |

## FULL を本番 export に使わない

`FULL` は envelope の中身（target, parameters_digest 等）や intent を含む。通常の export では `WITHOUT_CONTEXT` または `MINIMAL` を使う。

## secret-like key は常に伏せる

`FULL` でも以下の key 名を含む値は `[REDACTED]` に置換される:

```
token, secret, api_key, apikey, authorization,
cookie, password, refresh_token, access_token
```

## JouJou の Todo 作成で何を保存し、何を保存しないか

**保存するもの:**
- action_id（監査トレース用）
- event_type, timestamp
- side_effect_observed
- result_digest（Todo title + Provider response の digest）

**保存しないもの:**
- Todo 本文の平文
- Provider token
- 会話全文
- context_snapshot（`WITHOUT_CONTEXT` 時）

## UNCONFIRMED 調査時に minimal export を使う例

```python
from koguchi import export_events, RedactionPolicy

exported = export_events(store, policy=RedactionPolicy.MINIMAL)
for event in exported:
    print(event["event_id"], event["event_type"], event["side_effect_observed"])
```

## サポート依頼時に共有してよい audit 情報の範囲

| 情報 | 共有可 |
|------|--------|
| event_id, timestamp | ○ |
| event_type, side_effect_observed | ○ |
| intent | ✕（`WITHOUT_INTENT` でマスク） |
| target（ファイルパス等） | ○（MINIMAL では ✕） |
| digest | ○（MINIMAL では ✕） |
| context_snapshot | ✕ |
| token / secret | 常に ✕ |

## 次のステップ

- [Getting Started](getting-started.md) — Koguchi の基本使い方
- [AuditGate Integration](auditgate-integration.md) — アプリケーションへの組み込み
- [Roadmap](../roadmap.md) — 全体フェーズ計画
