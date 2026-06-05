# ADR-024: Rust Chokepoint Spike

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 背景

v0.1〜v0.3 では Python 上で RuntimeBoundary が best-effort な制約を提供してきたが、hostile runtime に対する強制隔離ではない。CAH の設計では、将来的に Python process の外側に enforcement backend を置く必要がある。

---

## 決定

Koguchi は v0.4 で Rust Chokepoint Spike を導入する。Rust binary は stdin/stdout JSON protocol により request を受け取り、allowlist と workspace boundary を確認した上で限定された operation を実行し structured result を返す。

v0.4 は optional spike であり、完全な sandbox や production hardening を提供しない。

---

## Non-goals

- 完全 sandbox / seccomp / namespace / container isolation / macOS sandbox
- daemon 化 / remote API / arbitrary shell / production hardening

---

## 参照

- [ADR-020](ADR-020-runtime-hardening.md) — Runtime Hardening
- [ADR-021](ADR-021-service-runtime.md) — Service Runtime
