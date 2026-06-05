# ADR-009: Phase 3 — ネットワークツール（`network.http_get`）と `partial` の意味論

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |
| **Closes** | ADR-005 延ばした論点「`partial` の意味論と生成経路」|

---

## 背景

これまでの Phase で `side_effect_observed` の4値のうち3値が生成可能になった：

| 値 | 生成条件 | 該当ツール |
|----|----------|-----------|
| `"none"` | 副作用未発生 | write_file, execute_shell, make_directory |
| `"confirmed"` | 副作用完了を確認 | write_file, execute_shell, make_directory |
| `"unknown"` | タイムアウト（状態不明） | execute_shell |
| `"partial"` | **未実装** | — |

`"partial"` は「副作用が部分的に発生したが全容が確定できない」状態であり、ネットワーク越しの副作用に固有の観測シナリオである。本 ADR は `network.http_get` の追加と `partial` の意味論確定を行う。

---

## 決定 A: `network.http_get` の追加

**`ToolProxy` に `http_get(url, ...) -> ProxyResult` を追加する。**

### シグネチャ

```python
def http_get(
    self,
    envelope: ActionEnvelope | None,
    url: str,
    timeout: float | None = None,
    intent: str | None = None,
    context: dict[str, object] | None = None,
) -> ProxyResult:
```

### 実行モデル

`urllib.request.urlopen(url, timeout=timeout)` を用いる。Python 標準ライブラリのみで完結し、追加依存なし。

| 状態 | トリガー | `side_effect_observed` | 戻り値 |
|------|----------|------------------------|--------|
| 正常完了 | レスポンスを完全に受信 | `"confirmed"` | `SUCCESS` |
| 部分受信 | `http.client.IncompleteRead`（Content-Length と実際の body が不一致）| `"partial"` | `FAILURE` |
| タイムアウト | `socket.timeout` / 接続タイムアウト | `"unknown"` | `FAILURE` |
| 接続失敗 | `URLError`（DNS 失敗・接続拒否） | `"none"` | `FAILURE` |
| その他 HTTP エラー | `HTTPError`（4xx/5xx） | `"confirmed"` | `SUCCESS`（HTTP レベルの副作用は「レスポンスを得た」こと） |

### `result_digest`

正常完了時: `SHA-256(str(status_code) + "\n" + response_body)`。
部分受信時: 受信できた部分のみで計算。
HTTPError 時: `SHA-256(str(status_code) + "\n" + error_body)`。

---

## 決定 B: `partial` の意味論確定

### 定義

> `"partial"` は「副作用がリモート側で開始／処理された証拠があるが、結果の全容を取得できなかった」状態を表す。

これは `"unknown"`（副作用の発生自体が確認できない）や `"none"`（副作用が発生していない）と明確に区別される。

### 具体的なシナリオ

| レイヤ | シナリオ | 観測値 |
|--------|----------|--------|
| HTTP | `IncompleteRead`: Content-Length はあるが body が不完全 | `"partial"` |
| HTTP | 接続がレスポンスヘッダ受信後に切断 | `"partial"`（将来） |
| 将来: DB | INSERT 発行後に接続断（auto-commit 不明） | `"partial"` |
| 将来: MQ | メッセージ送信後に ack 喪失 | `"partial"` |

### `partial` と `unknown` の境界

| | `partial` | `unknown` |
|---|---|---|
| リモート側の処理 | 開始された証拠がある（ヘッダ／部分 body 受信） | 証拠がない（タイムアウト、応答なし） |
| 監査上の扱い | 「何か起きた」という事実が残る | 「起きたかどうかわからない」 |
| reconciliation | リモート側のログと突合が必要 | リトライ判断の材料 |

---

## 決定 C: envelope の扱い

**`network.http_get` の `envelope.target` には URL を設定する。workspace 境界チェックは行わない。**

ネットワーク副作用は本質的に workspace 外であり、`filesystem.*` の境界モデルを適用できない。代わりに `permission_scope="network"` と `risk_class=["http_request"]` でリスクを宣言する。

---

## 影響

| ファイル | 変更内容 |
| --- | --- |
| `src/koguchi/proxy.py` | `http_get()` 追加。IncompleteRead / timeout / URLError / HTTPError の分岐 |
| `tests/test_network_http.py`（新規） | HTTP サーバーを使った正常・partial・timeout・error の回帰テスト |

---

## 意図的に延ばした論点

| 論点 | 延ばした理由 |
| --- | --- |
| HTTP POST/PUT/DELETE | GET でパターンが確立した後に追加。リクエストボディの digest 管理の設計が必要。 |
| リダイレクト追跡 | `urllib` のデフォルト動作に従う（追跡する）。ポリシー制御は Policy Gate で扱う。 |
| レスポンスサイズ制限 | 巨大レスポンスのメモリ圧迫は Policy Gate で扱う。 |
| reconciliation の HTTP 対応 | HTTP 副作用はリモートログとの突合が必要であり、ローカル照合では完結しない。Phase 4 で検討。 |

---

## 参照

- [ADR-005](ADR-005-non-atomic-shell-execute.md) — `partial` の延期判断
- [ADR-002](ADR-002-phase1-side-effect-chokepoint.md) — `side_effect_observed` の4値定義
- `src/koguchi/events.py` — `ExecutionEvent.side_effect_observed`
- `src/koguchi/proxy.py` — ToolProxy 実装
