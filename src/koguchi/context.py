"""Context Resolver — 副作用実行時のコンテキストを自動キャプチャする。"""

import os
import sys
from datetime import UTC, datetime
from typing import Protocol


class ContextResolver(Protocol):
    def resolve(self) -> dict[str, object]:
        """現在のコンテキストを辞書として返す。"""
        ...


class SystemContextResolver:
    """システムレベルのコンテキストをキャプチャするデフォルト実装。"""

    def resolve(self) -> dict[str, object]:
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "python_version": sys.version,
            "platform": sys.platform,
            "pid": os.getpid(),
            "env_summary": {
                k: os.environ[k]
                for k in ("PATH", "HOME", "USER", "LANG", "SHELL")
                if k in os.environ
            },
        }
