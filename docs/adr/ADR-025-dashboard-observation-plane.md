# ADR-025: Dashboard Observation Plane

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 背景

v0.1〜v0.4 で実行・監査・後続検証・外部 chokepoint 候補の構造が整ったが、状態は個別ファイルや example を見なければ把握しにくい。開発者やレビュー担当者が現在の状態を一目で確認できる観測面が必要である。

---

## 決定

Koguchi は v0.5 で Dashboard Observation Plane を導入する。Dashboard は read-only な snapshot を生成し、audit records、reconciliation jobs、chokepoint availability を JSON serializable な形でまとめる。

Dashboard は control plane ではない。tool execution、approval、repair、rollback、audit mutation、job rerun は実装しない。

---

## Non-goals

- Web server / remote API / auth / live update
- destructive control / approval UI
- production monitoring / SIEM integration

---

## 参照

- [ADR-022](ADR-022-persistent-audit-store.md)
- [ADR-023](ADR-023-reconciliation-scheduler.md)
- [ADR-024](ADR-024-rust-chokepoint-spike.md)
