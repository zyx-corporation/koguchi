"""INV-1c / スコープ境界: workspace_dir 外への書込みは前方一致でも漏れない。"""
import pytest

from koguchi.errors import WorkspaceBoundaryError
from koguchi.proxy import ToolProxy
from koguchi.store import SQLiteExecutionStore
from tests.conftest import make_envelope


def test_write_to_sibling_prefix_dir_is_rejected(tmp_path):
    """/ws と /ws-evil のような前方一致する兄弟ディレクトリへ漏れないこと。"""
    ws = tmp_path / "ws"; ws.mkdir()
    evil = tmp_path / "ws-evil"; evil.mkdir()
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(ws), store)

    escaped = evil / "leak.txt"
    envelope = make_envelope(str(evil), "leak.txt", b"escaped")

    with pytest.raises(WorkspaceBoundaryError):
        proxy.write_file(envelope=envelope, content=b"escaped")

    assert not escaped.exists()
    assert store.pending() == []


def test_write_with_parent_traversal_is_rejected(tmp_path):
    """.. による親への脱出も拒否されること。"""
    ws = tmp_path / "ws"; ws.mkdir()
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(ws), store)

    escaped = ws / ".." / "outside.txt"
    envelope = make_envelope(str(tmp_path), "outside.txt", b"x")
    envelope.target = str(escaped)

    with pytest.raises(WorkspaceBoundaryError):
        proxy.write_file(envelope=envelope, content=b"x")
