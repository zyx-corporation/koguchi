# ADR-015: Phase 4 — AuditGate Protocol と KoguchiAuditGate

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 背景

ロードマップ Phase 4 では、Koguchi を JouJou 等の実アプリケーションに組み込むための抽象化層を導入する。アプリケーションのサービス層（`TodoService` 等）が Koguchi の内部実装（`ActionEnvelope`, `ToolProxy`, `SQLiteExecutionStore`）に直接依存すると、Koguchi の変更がアプリケーション全体に波及する。

`AuditGate` Protocol は、アプリケーションが依存する唯一の Koguchi インターフェースである。Koguchi の実装詳細は `KoguchiAuditGate` に閉じ込める。

---

## 決定 A: `AuditGate` Protocol

```python
class AuditGate(Protocol):
    def audit(
        self,
        tool: str,
        target: str,
        params_digest: str,
        permission_scope: str,
        risk_class: list[str],
        intent: str | None = None,
        context: dict[str, object] | None = None,
    ) -> "AuditResult": ...
```

### `AuditResult`

```python
@dataclass
class AuditResult:
    action_id: str
    result: ProxyResult
    side_effect_observed: str | None
```

### 理由

- `audit()` は `ActionEnvelope` の生成から `ToolProxy` の実行までを一つの呼び出しに集約する。
- アプリケーションは `ActionEnvelope` や `ProxyResult` の内部構造を知らなくてよい。
- `AuditResult` はアプリケーションが必要とする最小限の情報（action_id, 結果, 副作用観測値）だけを返す。

---

## 決定 B: `KoguchiAuditGate`

**`ToolProxy` + `ExecutionStore` + `DecisionStore` + `PolicyGate` をラップする具象実装。**

```python
class KoguchiAuditGate:
    def __init__(self, proxy: ToolProxy): ...

    def audit(self, ...) -> AuditResult:
        envelope = ActionEnvelope(action_id=..., tool=..., ...)
        result = self._proxy.write_file(envelope, content, intent, context)
        return AuditResult(action_id=..., result=result, ...)
```

Phase 4 では `filesystem.write` のみを対象とする。マルチツール・マルチプロバイダ対応は Phase 8。

---

## 影響

| ファイル | 変更内容 |
| --- | --- |
| `src/koguchi/audit.py`（新規） | `AuditGate` Protocol, `AuditResult`, `KoguchiAuditGate` |
| `src/koguchi/__init__.py` | 新規 export 追加 |
| `tests/test_audit_gate.py`（新規） | AuditGate 経由の write テスト |

---

## 参照

- [docs/roadmap.md](../roadmap.md) §8 — Phase 4 AuditGate Integration
- [ADR-014](ADR-014-policy-gate-execution.md) — Policy Gate
