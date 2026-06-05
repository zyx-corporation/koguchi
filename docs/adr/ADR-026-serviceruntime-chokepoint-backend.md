# ADR-026: ServiceRuntime Optional Chokepoint Backend Integration

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 背景

v0.4 で Rust chokepoint spike、v0.5 で Dashboard Observation Plane が導入されたが、Rust chokepoint は ServiceRuntime の実行経路に接続されていない。ToolProxy → PolicyGate → ServiceRuntime の正規経路から Rust chokepoint を利用する構造が必要である。

---

## 決定

Koguchi は ServiceRuntime に execution backend abstraction を導入する。既定 backend は Python、Rust chokepoint backend は explicit opt-in とする。

ServiceRuntime は PolicyGate の代替ではなく、RuntimeBoundary の代替でもない。Rust chokepoint backend は RuntimeBoundary 通過後に実行される optional external backend である。

AuditEvent には `execution_backend` を記録し観測可能にする。

### Tool mapping

- `filesystem.write` → `write_text`
- `filesystem.read` → `read_text`
- 未対応 tool → unsupported error

---

## Non-goals

- Rust backend の既定化 / security sandbox の完成 / OS-level isolation / arbitrary shell

---

## 参照

- [ADR-024](ADR-024-rust-chokepoint-spike.md)
- [ADR-025](ADR-025-dashboard-observation-plane.md)
