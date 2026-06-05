# Getting Started

Koguchi の開発環境セットアップと最初のステップ。

## 前提

- Python 3.11 以上
- Git

## セットアップ

```bash
git clone https://github.com/zyx-corporation/koguchi.git
cd koguchi
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 品質チェック

```bash
# 全チェック
make quality

# 個別
make lint        # ruff check
make typecheck   # mypy
make test        # pytest
```

## ドキュメント生成

```bash
make docs        # API ドキュメントを docs/api/ に生成
open docs/api/index.html
```

## プロジェクト構造

```
koguchi/
├── src/koguchi/          # ソースコード
│   ├── proxy.py          # ToolProxy（副作用の単一隘路）
│   ├── store.py          # ExecutionStore（append-only 来歴）
│   ├── reconcile.py      # 実世界との照合
│   ├── decision.py       # Decision Logger（なぜ実行したか）
│   ├── policy.py         # Policy Gate + Redaction
│   ├── audit.py          # AuditGate（アプリ抽象化層）
│   ├── context.py        # Context Resolver
│   ├── i18n.py           # 多言語対応
│   └── locales/          # メッセージカタログ
├── tests/                # 不変条件の証拠としてのテスト
├── docs/
│   ├── adr/              # Architecture Decision Records
│   ├── dev/              # 開発者向け文書
│   ├── method/           # 開発手法（SLS+RDE）
│   └── roadmap.md        # 全体ロードマップ
└── pyproject.toml
```

## コーディング規約

- **コード識別子**: 英語
- **docstring・コメント**: 日本語
- **ユーザー向け文字列**: メッセージキー経由（`t("key")`）、ja/en/zh-CN/zh-TW/ko 対応
- **型ヒント**: 全関数・メソッドに必須（mypy strict）
- **テスト**: 不変条件の証拠として書く。TDD の赤テスト起点

## 次のステップ

- [全体ロードマップ](../roadmap.md) — Koguchi の全体像とフェーズ計画
- [ADR](../adr/) — 設計判断の正本
- [SLS+RDE 開発手法](../method/sls_rde_development_method.md) — 開発プロセスの規範
