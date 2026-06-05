# ADR-014: Phase 3 — Policy Gate（実行前許可判定）

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 背景

Phase 1-2 では副作用の記録に注力し、Phase 6 で表示時の墨消し（`RedactionPolicy`）を先行的に実装した。しかしロードマップ Phase 3 の本質は、**実行前に「この副作用を許可してよいか」を判定する Policy Gate** である。

現状、`ToolProxy` は workspace 境界チェックと envelope 必須チェックのみを行い、それ以外のポリシー判定は存在しない。shell 実行や workspace 外操作は境界チェックでのみ弾かれ、ポリシーレイヤとしての許可判定がない。

---

## 決定 A: `PolicyDecision` — 判定結果の三値

```python
class PolicyDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
```

`DENY` の場合は副作用を起こさず `ProxyResult.REJECTED` を返す。`REQUIRE_APPROVAL` は Phase 3 では `DENY` と同様に扱う（承認フローは Phase 4 以降）。

---

## 決定 B: `PolicyRule` Protocol

```python
class PolicyRule(Protocol):
    def evaluate(self, envelope: ActionEnvelope) -> PolicyDecision:
        ...
```

### 組み込みルール

| ルール | 判定 | 条件 |
|--------|------|------|
| `DenyShellExecution` | DENY | `envelope.tool == "shell.execute"` |
| `WorkspaceOnly` | DENY | `filesystem.*` で workspace 外 |

---

## 決定 C: `ExecutionPolicyGate`

**複数の `PolicyRule` を保持し、最初の DENY で停止する。**

```python
class ExecutionPolicyGate:
    def __init__(self, rules: list[PolicyRule]): ...

    def evaluate(self, envelope: ActionEnvelope) -> tuple[PolicyDecision, str]:
        """判定結果と理由を返す。"""
```

### ToolProxy への統合

`ToolProxy.__init__` に `policy_gate: ExecutionPolicyGate | None = None` を追加。全ツールメソッドで `_prepare_execution` の前に判定する。

---

## 影響

| ファイル | 変更内容 |
| --- | --- |
| `src/koguchi/policy.py` | `PolicyDecision`, `PolicyRule`, `ExecutionPolicyGate`, `DenyShellExecution`, `WorkspaceOnly` 追加 |
| `src/koguchi/proxy.py` | `ToolProxy` に `policy_gate` 注入 + `_evaluate_policy()` |
| `tests/test_policy_enforcement.py`（新規） | 各ルールの DENY / ALLOW テスト |

---

## 参照

- [docs/roadmap.md](../roadmap.md) §7 — Phase 3 Policy Gate
- [ADR-012](ADR-012-policy-gate.md) — RedactionPolicy（Phase 6、先行実装済み）
