"""Runtime Hardening — 実行時境界の抽象化と最小防御。

Python 単体では完全封じ込めは保証できない。
このモジュールは将来 Rust/seccomp/container へ差し替え可能な抽象境界を定義する。
"""

from typing import Protocol

from pydantic import BaseModel


class RuntimeCapability(BaseModel):
    name: str
    scope: str
    description: str | None = None


class RuntimeBoundaryDecision(BaseModel):
    allowed: bool
    reason: str


class RuntimeBoundary(Protocol):
    def evaluate_tool(self, tool: str) -> RuntimeBoundaryDecision:
        """ツールの実行可否を判定する。"""
        ...

    def filter_environment(self, env: dict[str, str]) -> dict[str, str]:
        """subprocess に渡す環境変数をフィルタする。"""
        ...


_SECRET_ENV_PATTERNS = [
    "token", "secret", "api_key", "apikey", "authorization",
    "cookie", "password", "refresh_token", "access_token",
    "key", "credential",
]

_SAFE_ENV_KEYS = {"PATH", "HOME", "USER", "LANG", "SHELL", "PWD", "TMPDIR"}

_DEFAULT_ALLOWED_TOOLS = {
    "filesystem.write",
    "filesystem.mkdir",
    "network.http_get",
    "todo.create",
}

_DEFAULT_DENIED_TOOLS = {
    "shell.execute",
}


class DefaultRuntimeBoundary:
    """最小防御を提供する RuntimeBoundary のデフォルト実装。

    - shell.execute を default deny
    - workspace 外 path を deny
    - secret-like env key を filter
    """

    def __init__(
        self,
        allowed_tools: set[str] | None = None,
        denied_tools: set[str] | None = None,
        safe_env_keys: set[str] | None = None,
    ) -> None:
        self._allowed = allowed_tools or _DEFAULT_ALLOWED_TOOLS.copy()
        self._denied = denied_tools or _DEFAULT_DENIED_TOOLS.copy()
        self._safe_env = safe_env_keys or _SAFE_ENV_KEYS.copy()

    def evaluate_tool(self, tool: str) -> RuntimeBoundaryDecision:
        if tool in self._denied:
            return RuntimeBoundaryDecision(
                allowed=False,
                reason=f"Tool '{tool}' is denied by default",
            )
        if tool in self._allowed:
            return RuntimeBoundaryDecision(
                allowed=True,
                reason=f"Tool '{tool}' is allowed",
            )
        return RuntimeBoundaryDecision(
            allowed=False,
            reason=f"Tool '{tool}' is not in allowed list",
        )

    def filter_environment(self, env: dict[str, str]) -> dict[str, str]:
        result: dict[str, str] = {}
        for key, value in env.items():
            key_lower = key.lower()
            if key in self._safe_env:
                result[key] = value
            elif any(pattern in key_lower for pattern in _SECRET_ENV_PATTERNS):
                continue
            else:
                result[key] = value
        return result
