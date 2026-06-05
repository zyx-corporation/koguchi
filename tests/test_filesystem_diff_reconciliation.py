"""v0.10 Filesystem Diff Reconciliation — read-only spike の証拠。"""
from pathlib import Path

import pytest

from koguchi.reconciliation.filesystem_diff import (
    DiffKind,
    ExpectedArtifact,
    FilesystemReconciliationInput,
    ReconciliationStatus,
    reconcile_filesystem_diff,
)


def _write_file(root: Path, rel_path: str, content: str) -> Path:
    full = root / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content)
    return full


def test_matched_when_all_unchanged(tmp_path):
    obs = tmp_path / "obs"
    obs.mkdir()
    _write_file(obs, "a.txt", "hello")
    _write_file(obs, "b.txt", "world")

    req = FilesystemReconciliationInput(
        backend_id="fs", execution_id="e1",
        expected_artifacts=[
            ExpectedArtifact(path="a.txt"),
            ExpectedArtifact(path="b.txt"),
        ],
        observed_root=obs,
    )
    output = reconcile_filesystem_diff(req)
    assert output.status == ReconciliationStatus.MATCHED
    assert "No differences" in output.summary


def test_modified_when_hash_differs(tmp_path):
    obs = tmp_path / "obs"
    obs.mkdir()
    _write_file(obs, "x.txt", "original")

    import hashlib
    req = FilesystemReconciliationInput(
        backend_id="fs", execution_id="e2",
        expected_artifacts=[
            ExpectedArtifact(path="x.txt", sha256=hashlib.sha256(b"different").hexdigest()),
        ],
        observed_root=obs,
    )
    output = reconcile_filesystem_diff(req)
    assert output.status == ReconciliationStatus.MISMATCH_OBSERVED
    assert any(d.kind == DiffKind.MODIFIED for d in output.observed_differences)


def test_removed_when_expected_missing(tmp_path):
    obs = tmp_path / "obs"
    obs.mkdir()

    req = FilesystemReconciliationInput(
        backend_id="fs", execution_id="e3",
        expected_artifacts=[ExpectedArtifact(path="missing.txt")],
        observed_root=obs,
    )
    output = reconcile_filesystem_diff(req)
    assert any(d.kind == DiffKind.REMOVED for d in output.observed_differences)
    assert "missing.txt" in output.missing_artifacts


def test_added_when_extra_file_in_observed(tmp_path):
    obs = tmp_path / "obs"
    obs.mkdir()
    _write_file(obs, "extra.log", "unexpected")

    req = FilesystemReconciliationInput(
        backend_id="fs", execution_id="e4",
        expected_artifacts=[],
        observed_root=obs,
    )
    output = reconcile_filesystem_diff(req)
    assert any(d.kind == DiffKind.ADDED for d in output.observed_differences)


def test_ignored_paths_are_ignored(tmp_path):
    obs = tmp_path / "obs"
    obs.mkdir()
    _write_file(obs, "file.tmp", "temp")

    req = FilesystemReconciliationInput(
        backend_id="fs", execution_id="e5",
        expected_artifacts=[ExpectedArtifact(path="file.tmp")],
        observed_root=obs,
        ignored_paths=["*.tmp"],
    )
    output = reconcile_filesystem_diff(req)
    assert any(d.kind == DiffKind.IGNORED for d in output.observed_differences)


def test_no_repair_language_in_output(tmp_path):
    obs = tmp_path / "obs"
    obs.mkdir()

    req = FilesystemReconciliationInput(
        backend_id="fs", execution_id="e6",
        expected_artifacts=[ExpectedArtifact(path="missing.txt")],
        observed_root=obs,
    )
    output = reconcile_filesystem_diff(req)

    text = output.summary + " ".join(output.recommended_review_focus)
    for forbidden in ["delete", "overwrite", "rollback", "commit", "deploy", "retry"]:
        assert forbidden not in text.lower(), f"'{forbidden}' found in output"


def test_files_not_modified_by_reconciliation(tmp_path):
    obs = tmp_path / "obs"
    obs.mkdir()
    f = _write_file(obs, "keep.txt", "original content")

    before = f.read_text()
    req = FilesystemReconciliationInput(
        backend_id="fs", execution_id="e7",
        expected_artifacts=[ExpectedArtifact(path="keep.txt")],
        observed_root=obs,
    )
    reconcile_filesystem_diff(req)
    after = f.read_text()
    assert before == after, "File was modified by reconciliation"


def test_empty_backend_id_raises():
    req = FilesystemReconciliationInput(
        backend_id="", execution_id="e8",
        expected_artifacts=[],
        observed_root=Path("."),
    )
    with pytest.raises(ValueError):
        reconcile_filesystem_diff(req)


def test_missing_observed_root_is_inconclusive(tmp_path):
    req = FilesystemReconciliationInput(
        backend_id="fs", execution_id="e9",
        expected_artifacts=[],
        observed_root=tmp_path / "nonexistent",
    )
    output = reconcile_filesystem_diff(req)
    assert output.status == ReconciliationStatus.INCONCLUSIVE


def test_review_focus_includes_path_hints(tmp_path):
    obs = tmp_path / "obs"
    obs.mkdir()

    req = FilesystemReconciliationInput(
        backend_id="fs", execution_id="e10",
        expected_artifacts=[ExpectedArtifact(path="modified.txt")],
        observed_root=obs,
    )
    output = reconcile_filesystem_diff(req)
    assert any("modified.txt" in r for r in output.recommended_review_focus)
