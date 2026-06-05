# ADR-005: Phase 2.B — 非 atomic ツール対応（`shell.execute`）

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |
| **Closes** | ADR-002 延ばした論点「`partial` / `unknown` の `side_effect_observed`」 |

---

## 背景

Phase 1 では `filesystem.write` のみを実装し、atomic write（temp + fsync + rename）によって副作用を「全か無か」に強制した。この制約により `side_effect_observed` は `none` と `confirmed` のみが使われ、`partial` と `unknown` はスキーマ上の余地として残されていた。

非 atomic なツール（shell 実行、ネットワークリクエスト）では、副作用の「全か無か」保証が構造的に成立しない。本 Phase では `shell.execute` を追加し、`side_effect_observed` の全4値を実際に生成する経路を実装する。

---

## 決定 A: `shell.execute` の追加

**`ToolProxy` に `execute_shell(command: list[str], ...) -> ProxyResult` を追加する。**

### シグネチャ

```python
def execute_shell(
    self,
    envelope: ActionEnvelope | None,
    command: list[str],
    timeout: float | None = None,
    intent: str | None = None,
    context: dict | None = None,
) -> ProxyResult:
```

### 実行モデル

`subprocess.run(command, capture_output=True, timeout=timeout)` を用いる。実行パスは以下の3状態に分岐する：

| 状態 | トリガー | `side_effect_observed` | 戻り値 |
|------|----------|------------------------|--------|
| 正常完了 | `subprocess.run()` が `CompletedProcess` を返す | `"confirmed"` | `SUCCESS`（commit 成功時）/ `UNCONFIRMED`（commit 失敗時） |
| タイムアウト | `subprocess.TimeoutExpired` | `"unknown"` | `FAILURE` |
| 実行失敗 | その他の例外（起動失敗など） | `"none"` | `FAILURE` |

### `result_digest`

正常完了時、`(stdout + stderr + str(exit_code))` の SHA-256 を `result_digest` とする。タイムアウト時は `result_digest` なし。

### `expected_result_digest`

非決定論的ツールでは事前計算不可のため、常に `None`。

---

## 決定 B: `partial` は本 Phase では生成しない

`side_effect_observed = "partial"` は、副作用が「部分的に発生したが全容が確定できない」状態を表す。これはネットワークリクエスト（レスポンス喪失）や長時間プロセスのシグナル中断など、より複雑な観測シナリオで発生する。

`shell.execute` の `subprocess.run()` は同期的に完了/タイムアウトするため、`partial` は発生しない。`partial` の意味論と生成経路はネットワークツール（Phase 3 以降）で扱う。

---

## 決定 C: shell の workspace 境界と安全性

**`execute_shell` は workspace_dir を cwd として実行する。workspace 外への操作は shell 自体の権限の問題であり、Koguchi は制限しない——ただし envelope の `risk_class` でリスクを宣言する。**

`filesystem.write` のような target ベースの境界チェックは shell には適用できない（副作用の対象が事前に確定しないため）。代わりに：

- `ActionEnvelope.target` には実行時の cwd（workspace_dir）を設定する
- `risk_class` に `"shell_exec"` を必須とする
- workspace 外への影響は INV-1c（reconciliation による検出）で扱う

### 理由

`filesystem.write` の「このファイルへの書込み」という明示的な境界に対して、`shell.execute` の副作用は「コマンドが行うすべて」であり、事前に対象を列挙できない。この制約を隠蔽せず、`risk_class` と `side_effect_observed = "unknown"`（タイムアウト時）を通じて正直に表明する。

---

## 決定 D: shell pending の reconciliation

**shell の pending event は reconciliation で特別扱いしない。既存のファイルベース照合と同様に `target.exists()` で判定し、workspace が存在すれば `pending_executed_unconfirmed` とする。**

shell には atomic write のような確定検査（ファイルの存在 + digest 一致）ができないため、`pending_executed_unconfirmed` の confidence は `0.70`（ファイル照合より低い）とする。

---

## 影響

| ファイル | 変更内容 |
| --- | --- |
| `src/koguchi/proxy.py` | `execute_shell()` 追加。二相記録の汎用化（ヘルパー抽出の可能性あり） |
| `src/koguchi/reconcile.py` | shell pending の confidence 調整（0.85 → 0.70） |
| `tests/test_shell_execute.py`（新規） | shell 実行・タイムアウト・reconcile の回帰テスト |

---

## 意図的に延ばした論点

| 論点 | 延ばした理由 |
| --- | --- |
| `side_effect_observed = "partial"` の生成経路 | ネットワークツール（Phase 3）で扱う |
| shell 出力のサイズ制限・redaction | 大きな stdout/stderr の扱いは Policy Gate と併せて設計 |
| shell の workspace 境界の強制（sandbox） | Koguchi の責務ではなく上位の sandbox 層の責務。現時点は risk_class 宣言のみ |
| `cwd` のカスタム指定 | Phase 2.B は workspace_dir 固定。柔軟な cwd 指定は後段フェーズ |

---

## 次回更新方針

- Phase 3: ネットワークツール + `partial` の意味論確定
- Phase 4: Policy Gate + `redaction_policy` 実装

---

## 参照

- [ADR-002](ADR-002-phase1-side-effect-chokepoint.md) — Phase 1 設計判断、`side_effect_observed` の4値定義
- [ADR-004](ADR-004-decision-logger-phase2.md) — Decision Logger 統合
- `src/koguchi/events.py` — `ExecutionEvent.side_effect_observed` 定義
- `src/koguchi/proxy.py` — `ToolProxy` 実装
