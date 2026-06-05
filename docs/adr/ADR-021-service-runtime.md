# ADR-021: Service Runtime as Accountable Execution Surface

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 背景

Phase 9 で `RuntimeBoundary` が導入され、PolicyGate と runtime-level boundary の責務が分離された。しかし tool execution が process-local な呼び出しに閉じており、将来の daemon 化、API 化、dashboard、sandbox、Rust chokepoint に接続する安定した実行面が存在しない。

---

## 決定

Koguchi は Service Runtime を導入する。Service Runtime は Tool Proxy の execution backend として機能し、tool execution request を受け取り、RuntimeBoundary 判定、実行、audit emission を一貫して扱う。

Service Runtime は PolicyGate の代替ではなく、PolicyGate は envelope/policy 上の許可判定を担う。RuntimeBoundary は runtime/tool/env/workspace 上の境界判定を担う。Service Runtime はそれらを接続する execution surface である。

---

## Non-goals

- 完全な security sandbox の提供
- Rust chokepoint の実装
- seccomp/container/network namespace の実装
- dashboard からの destructive control
- Agent からの Service Runtime 直接呼び出し
- PolicyGate と RuntimeBoundary の統合

---

## Consequences

Service Runtime により、実行経路、監査、reconciliation の接続点が明確になる。Service Runtime は権限主体ではなく、観測可能な実行面である。

---

## 参照

- [ADR-014](ADR-014-policy-gate-execution.md) — Policy Gate
- [ADR-020](ADR-020-runtime-hardening.md) — Runtime Hardening
