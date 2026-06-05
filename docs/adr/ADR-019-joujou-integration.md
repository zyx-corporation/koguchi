# ADR-019: Phase 8 — JouJou Practical Integration

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 背景

Koguchi は Phase 7 までで監査基盤を備えた。Phase 8 では、最初の実用統合例として JouJou の `create_todo` を題材にした integration pattern を確立する。

目的は JouJou 本体の実装ではなく、Koguchi 側に「アプリケーションがどう Koguchi を使うべきか」を示すことである。

---

## 決定 A: Koguchi は JouJou 専用にしない

JouJou は最初の実用統合例であり、Koguchi の core schema を JouJou 専用に変形しない。integration adapter は `src/koguchi/integrations/` に置き、core とは分離する。

---

## 決定 B: Provider は Koguchi を知らない

Provider は GitHub / Notion / Google Tasks 等の外部 API を呼ぶだけ。Koguchi を知るのは integration adapter だけ。

```
TodoService → AuditGate Protocol → KoguchiTodoAuditGate → Provider
```

---

## 決定 C: create_todo のみを対象

Phase 8 では `create_todo` のみ。list/complete/delete/bulk update は対象外。

---

## 決定 D: UNCONFIRMED の実用例

Provider 作成は成功したが audit commit に失敗した場合、`UnconfirmedSideEffectError` を raise する。通常成功にも通常失敗にもしない。

---

## 決定 E: RDE hint を TodoInput から受け取る

`TodoInput.rde` に `RdeHint | None` を持たせ、`KoguchiTodoAuditGate` が受け取る。Phase 7 の `rde_ref` 空フックに接続する余地を残す。

---

## 決定 F: Redaction policy のデフォルト

`create_todo` の `ActionEnvelope` では `redaction_policy="without_context"` をデフォルトとする。Todo 本文や context_summary は context_snapshot として保存するが、export 時は policy に従う。

---

## 意図的に延ばす論点

- GitHub 実 Provider
- Notion 実 Provider
- Google Tasks OAuth
- JouJou 本体 repo への移植
- provider-specific reconciliation の本実装

---

## 参照

- [ADR-015](ADR-015-audit-gate.md) — AuditGate Protocol
- [ADR-018](ADR-018-rde-t-rde.md) — RDE / T-RDE
- [docs/roadmap.md](../roadmap.md) §12 — Phase 8
