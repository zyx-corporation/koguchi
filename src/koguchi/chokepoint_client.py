"""Rust Chokepoint Client — Python 側の接続面。

v0.4 では optional spike。Rust binary が存在しない場合は ChokepointUnavailableError。
"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ChokepointError(Exception):
    """chokepoint 関連の基底エラー。"""


class ChokepointUnavailableError(ChokepointError):
    """Rust binary が存在しない。"""


class ChokepointProtocolError(ChokepointError):
    """Rust の応答が JSON でない、または不正。"""


@dataclass(frozen=True)
class ChokepointResult:
    request_id: str
    allowed: bool
    status: str
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    error: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChokepointResult":
        return cls(
            request_id=str(data.get("request_id", "")),
            allowed=bool(data.get("allowed", False)),
            status=str(data.get("status", "")),
            exit_code=data.get("exit_code"),
            stdout=str(data.get("stdout", "")),
            stderr=str(data.get("stderr", "")),
            error=data.get("error"),
        )


class RustChokepointClient:
    """Rust chokepoint binary を subprocess で呼び出す client。

    security sandbox ではない。v0.4 optional spike。
    """

    def __init__(self, binary_path: Path) -> None:
        self._binary = binary_path
        if not binary_path.exists():
            raise ChokepointUnavailableError(
                f"Rust chokepoint binary not found: {binary_path}"
            )

    def execute(
        self,
        operation: str,
        workspace: Path,
        path: str,
        content: str = "",
        request_id: str = "",
        timeout: float | None = 5.0,
    ) -> ChokepointResult:
        request = {
            "schema_version": 1,
            "request_id": request_id,
            "operation": operation,
            "workspace": str(workspace),
            "path": path,
            "content": content,
        }
        payload = json.dumps(request, ensure_ascii=False)

        try:
            proc = subprocess.run(
                [str(self._binary)],
                input=payload,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError:
            raise ChokepointUnavailableError(
                f"Rust chokepoint binary not found: {self._binary}"
            ) from None
        except subprocess.TimeoutExpired as e:
            raise ChokepointProtocolError(
                f"Chokepoint timed out after {timeout}s"
            ) from e

        if proc.returncode != 0:
            raise ChokepointProtocolError(
                f"Chokepoint exited with code {proc.returncode}: {proc.stderr}"
            )

        try:
            data = json.loads(proc.stdout)
            return ChokepointResult.from_dict(data)
        except json.JSONDecodeError as e:
            raise ChokepointProtocolError(
                f"Invalid JSON from chokepoint: {e}"
            ) from e
