import hashlib
import uuid
from pathlib import Path

import pytest

from koguchi.envelope import ActionEnvelope
from koguchi.store import SQLiteExecutionStore


def make_envelope(
    workspace_dir: str,
    filename: str = "out.txt",
    content: bytes = b"hello",
) -> ActionEnvelope:
    target = str(Path(workspace_dir) / filename)
    params_digest = hashlib.sha256(content).hexdigest()
    return ActionEnvelope(
        action_id=str(uuid.uuid4()),
        tool="filesystem.write",
        target=target,
        parameters_digest=params_digest,
        expected_result_digest=hashlib.sha256(content).hexdigest(),
        permission_scope="workspace",
        risk_class=["file_write"],
    )


@pytest.fixture
def store():
    return SQLiteExecutionStore(":memory:")


@pytest.fixture
def workspace(tmp_path):
    return tmp_path
