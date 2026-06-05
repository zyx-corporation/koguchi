# ADR-028: Dashboard Static HTML Report

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 背景

v0.5 では Dashboard Observation Plane、v0.7 では Persistent Reconciliation Result Store が導入され、Execution → Audit → Reconciliation Result → Dashboard Snapshot の基本閉路が成立した。しかし dashboard は Python dict / text report が中心であり、外部レビュー向けではない。

---

## 決定

v0.8 で static HTML report renderer を導入する。HTML report は `DashboardSnapshot` を入力とし、audit/reconciliation/backend/chokepoint summary を表示する。read-only static artifact であり、form、button、JavaScript、server、remote API を持たない。

---

## Non-goals

- Dashboard control plane / Web server / remote API / live update / security proof

---

## 参照

- [ADR-025](ADR-025-dashboard-observation-plane.md)
- [ADR-027](ADR-027-persistent-reconciliation-result-store.md)
