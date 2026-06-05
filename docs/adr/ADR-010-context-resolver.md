# ADR-010: Phase 3 — Context Resolver（コンテキスト自動キャプチャ）

| 項目 | 内容 |
| --- | --- |
| **Status** | Accepted |
| **Date** | 2026-06-05 |
| **Supersedes** | — |
| **Superseded by** | — |
| **Closes** | ADR-004 延ばした論点「Context Resolver の実装」|

---

## 背景

Phase 2 で Decision Logger を実装し、`context_snapshot`（判断時点のコンテキスト）を `Decision` レコードに保存できるようになった。しかし現状、コンテキストは caller が明示的に `context` パラメータを渡さなければ記録されない。これは運用上の負荷であり、コンテキスト欠落による監査の質低下を招く。

本 ADR は、コンテキストを自動キャプチャする Context Resolver を導入する。

---

## 決定 A: `ContextResolver` Protocol

```python
class ContextResolver(Protocol):
    def resolve(self) -> dict[str, object]:
        """現在のコンテキストを辞書として返す。"""
        ...
```

### `SystemContextResolver`

デフォルト実装として、以下をキャプチャする：

- `timestamp`: ISO 8601 形式の現在時刻
- `python_version`: `sys.version`
- `platform`: `sys.platform`
- `pid`: `os.getpid()`
- `env_summary`: 環境変数から安全なキーのみ抜粋（`PATH`, `HOME`, `USER`, `LANG` 等）

---

## 決定 B: ToolProxy への統合（オプショナル注入 + 明示的コンテキスト優先）

**`ToolProxy.__init__` に `context_resolver: ContextResolver | None = None` を追加する。**

コンテキスト決定の優先順位：

1. caller が明示的に `context` を渡した → それを使う
2. `context_resolver` が注入されている → `resolve()` を呼ぶ
3. どちらもない → `None`（Phase 2 と同じ、後方互換）

### `_prepare_execution` の変更

```python
effective_context = context
if effective_context is None and self._context_resolver is not None:
    effective_context = self._context_resolver.resolve()
```

---

## 決定 C: キャプチャタイミング

コンテキストは副作用実行の直前（`intent_pending` 書込みと同時）にキャプチャする。実行後のキャプチャではない——意思決定時点のスナップショットである。

---

## 影響

| ファイル | 変更内容 |
| --- | --- |
| `src/koguchi/context.py`（新規） | `ContextResolver` Protocol + `SystemContextResolver` |
| `src/koguchi/proxy.py` | `ToolProxy.__init__` に `context_resolver` 追加、`_prepare_execution` 修正 |
| `src/koguchi/__init__.py` | 新規 export 追加 |
| `tests/test_context_resolver.py`（新規） | 自動キャプチャ・明示的上書き・未注入のテスト |

---

## 参照

- [ADR-004](ADR-004-decision-logger-phase2.md) — Decision Logger / Context Resolver の延期判断
- `src/koguchi/proxy.py` — `_prepare_execution`
