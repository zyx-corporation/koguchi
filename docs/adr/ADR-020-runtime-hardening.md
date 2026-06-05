# ADR-020: Phase 9 — Runtime Hardening

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 背景

Phase 1〜8 では、迂回経路は主に reconciliation によって検出してきた。Phase 9 では、より強い実行時境界（prevention）へ進む。

ただし Python 単体では完全な副作用封じ込めは保証できない。この Phase では RuntimeBoundary の抽象境界を定義し、Python でできる最小防御を追加し、将来 Rust/seccomp/container へ差し替え可能な構造を用意する。

---

## 決定 A: prevention / detection / reconciliation の区別

| 層 | 責務 | 実装 |
|----|------|------|
| prevention | 実行前に防ぐ | RuntimeBoundary, PolicyGate |
| detection | 実行後に検出する | ExecutionEvent, hash chain |
| reconciliation | 記録と実態を照合する | reconcile(), ProviderReconciler |

---

## 決定 B: Python 単体では完全封じ込めできない

できること: workspace boundary 強化、allowed/denied tool registry、env filtering、shell default deny、timeout。

できないこと: OS レベル封じ込め、任意プロセス制御、ファイルシステム完全禁止、ネットワーク完全遮断。

---

## 決定 C: RuntimeBoundary Protocol

```python
class RuntimeBoundary(Protocol):
    def evaluate_tool(self, tool: str) -> RuntimeBoundaryDecision: ...
    def filter_environment(self, env: dict[str, str]) -> dict[str, str]: ...
```

### DefaultRuntimeBoundary

- workspace 外 path を deny
- shell.execute を default deny
- secret-like env key を subprocess に渡さない
- allowed tool list / denied tool list

---

## 決定 D: PolicyGate との責務分離

- PolicyGate: envelope/policy 上の許可判定（allow/deny/require_approval）
- RuntimeBoundary: 実行環境・tool runtime 上の境界制御

両者は直交する。PolicyGate が allow しても RuntimeBoundary が deny すれば実行されない。

---

## 決定 E: ToolProxy に RuntimeBoundary を注入

`ToolProxy.__init__` に `runtime_boundary: RuntimeBoundary | None = None` を追加。None の場合は境界チェックなし（後方互換）。

---

## 意図的に延ばす論点

- Rust chokepoint
- seccomp
- container isolation
- network namespace
- macOS sandbox

---

## 参照

- [ADR-014](ADR-014-policy-gate-execution.md) — Policy Gate
- [docs/roadmap.md](../roadmap.md) §13 — Phase 9
