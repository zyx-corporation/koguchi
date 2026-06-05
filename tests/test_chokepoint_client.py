"""v0.4 Rust Chokepoint Spike — Python client の証拠。"""
import json
import os
import tempfile
from pathlib import Path

import pytest

from koguchi.chokepoint_client import (
    ChokepointProtocolError,
    ChokepointUnavailableError,
    RustChokepointClient,
)


def test_missing_binary_raises():
    with pytest.raises(ChokepointUnavailableError):
        RustChokepointClient(Path("/nonexistent/binary"))


def test_fake_binary_returns_valid_result():
    """fake binary が valid JSON result を返す。"""
    script = _make_fake_binary(
        stdout=json.dumps({
            "schema_version": 1,
            "request_id": "req-1",
            "allowed": True,
            "status": "ok",
            "exit_code": 0,
            "stdout": "done",
            "stderr": "",
            "error": None,
        })
    )
    client = RustChokepointClient(Path(script))
    result = client.execute("write_text", Path("/tmp"), "test.txt", request_id="req-1")
    assert result.allowed is True
    assert result.request_id == "req-1"


def test_fake_binary_invalid_json_raises():
    script = _make_fake_binary(stdout="not json")
    client = RustChokepointClient(Path(script))
    with pytest.raises(ChokepointProtocolError):
        client.execute("write_text", Path("/tmp"), "test.txt")


def test_request_id_conserved_in_result():
    script = _make_fake_binary(
        stdout=json.dumps({
            "schema_version": 1,
            "request_id": "my-id",
            "allowed": True,
            "status": "ok",
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "error": None,
        })
    )
    client = RustChokepointClient(Path(script))
    result = client.execute("write_text", Path("/tmp"), "t", request_id="my-id")
    assert result.request_id == "my-id"


def test_denied_result_handled():
    script = _make_fake_binary(
        stdout=json.dumps({
            "schema_version": 1,
            "request_id": "r1",
            "allowed": False,
            "status": "denied",
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "error": "path escapes workspace",
        })
    )
    client = RustChokepointClient(Path(script))
    result = client.execute("write_text", Path("/tmp"), "../evil")
    assert result.allowed is False
    assert result.error == "path escapes workspace"


def test_rust_binary_integration():
    """実 Rust binary を使う integration test。binary がない場合は skip。"""
    binary = Path(
        "crates/koguchi-chokepoint/target/debug/koguchi-chokepoint"
    ).resolve()
    if not binary.exists():
        pytest.skip(f"Rust binary not built: {binary}")

    with tempfile.TemporaryDirectory() as ws:
        client = RustChokepointClient(binary)
        # write
        result = client.execute(
            "write_text", Path(ws), "hello.txt",
            content="world", request_id="int-1",
        )
        assert result.allowed is True
        assert result.status == "ok"

        # read
        result2 = client.execute(
            "read_text", Path(ws), "hello.txt", request_id="int-2",
        )
        assert result2.allowed is True
        assert result2.stdout == "world"

        # path traversal
        result3 = client.execute(
            "write_text", Path(ws), "../evil.txt", request_id="int-3",
        )
        assert result3.allowed is False


def _make_fake_binary(stdout: str) -> str:
    """subprocess.run で実行可能な fake binary（shell script）を作る。"""
    script = tempfile.mktemp(suffix=".sh")
    with open(script, "w") as f:
        f.write(f"#!/bin/sh\necho '{stdout}'\n")
    os.chmod(script, 0o755)
    return script
