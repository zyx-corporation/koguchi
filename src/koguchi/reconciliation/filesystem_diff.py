"""Filesystem Diff Reconciliation — read-only expected-vs-observed comparison。

v0.10 implementation spike. 修復・削除・上書き・rollback・commit・deploy は行わない。
"""

import hashlib
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class DiffKind(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"
    IGNORED = "ignored"
    UNKNOWN = "unknown"


class ReconciliationStatus(StrEnum):
    MATCHED = "matched"
    MISMATCH_OBSERVED = "mismatch_observed"
    MISSING_EXPECTED_ARTIFACT = "missing_expected_artifact"
    MISSING_OBSERVED_ARTIFACT = "missing_observed_artifact"
    STALE_OBSERVATION = "stale_observation"
    AUDIT_GAP = "audit_gap"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class ExpectedArtifact:
    path: str
    sha256: str | None = None


@dataclass(frozen=True)
class FilesystemReconciliationInput:
    backend_id: str
    execution_id: str
    expected_artifacts: list[ExpectedArtifact] = field(default_factory=list)
    observed_root: Path = Path(".")
    ignored_paths: list[str] = field(default_factory=list)
    timestamp_tolerance_seconds: int = 0
    audit_event_refs: list[str] = field(default_factory=list)
    result_store_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FilesystemDifference:
    path: str
    kind: DiffKind
    expected_sha256: str | None = None
    observed_sha256: str | None = None


@dataclass(frozen=True)
class FilesystemReconciliationOutput:
    status: ReconciliationStatus
    summary: str
    observed_differences: list[FilesystemDifference] = field(default_factory=list)
    missing_artifacts: list[str] = field(default_factory=list)
    stale_artifacts: list[str] = field(default_factory=list)
    audit_gaps: list[str] = field(default_factory=list)
    recommended_review_focus: list[str] = field(default_factory=list)


def _compute_sha256(file_path: Path) -> str | None:
    try:
        return hashlib.sha256(file_path.read_bytes()).hexdigest()
    except Exception:
        return None


def _matches_ignore(path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if pattern.startswith("*"):
            if path.endswith(pattern[1:]):
                return True
        elif pattern == path or path.startswith(pattern):
            return True
    return False


def reconcile_filesystem_diff(
    request: FilesystemReconciliationInput,
) -> FilesystemReconciliationOutput:
    """Read-only filesystem diff reconciliation。

    ファイルを読むだけ。書き込み・削除・rename・chmod・commit・deploy は行わない。
    """
    if not request.backend_id or not request.execution_id:
        raise ValueError("backend_id and execution_id are required")

    observed_root = request.observed_root
    if not observed_root.exists():
        return FilesystemReconciliationOutput(
            status=ReconciliationStatus.INCONCLUSIVE,
            summary="Observed root does not exist or is not accessible.",
        )

    differences: list[FilesystemDifference] = []
    missing_expected: list[str] = []
    review_focus: list[str] = []

    expected_paths = {a.path for a in request.expected_artifacts}

    # Check expected artifacts against observed filesystem
    for artifact in request.expected_artifacts:
        if _matches_ignore(artifact.path, request.ignored_paths):
            differences.append(FilesystemDifference(
                path=artifact.path, kind=DiffKind.IGNORED,
                expected_sha256=artifact.sha256,
            ))
            continue

        observed_path = observed_root / artifact.path
        if not observed_path.exists():
            missing_expected.append(artifact.path)
            differences.append(FilesystemDifference(
                path=artifact.path, kind=DiffKind.REMOVED,
                expected_sha256=artifact.sha256,
            ))
            review_focus.append(
                f"Review missing {artifact.path} before "
                "regenerating artifacts."
            )
            continue

        observed_hash = _compute_sha256(observed_path)
        if observed_hash is None:
            differences.append(FilesystemDifference(
                path=artifact.path, kind=DiffKind.UNKNOWN,
                expected_sha256=artifact.sha256,
            ))
            review_focus.append(
                f"Could not read {artifact.path} for hash comparison. "
                "Check file permissions."
            )
            continue

        if artifact.sha256 and artifact.sha256 != observed_hash:
            differences.append(FilesystemDifference(
                path=artifact.path, kind=DiffKind.MODIFIED,
                expected_sha256=artifact.sha256,
                observed_sha256=observed_hash,
            ))
            review_focus.append(
                f"Review modified {artifact.path} before treating "
                "this run as complete."
            )
        else:
            differences.append(FilesystemDifference(
                path=artifact.path, kind=DiffKind.UNCHANGED,
                expected_sha256=artifact.sha256,
                observed_sha256=observed_hash,
            ))

    # Check for extra files in observed root not in expected
    try:
        for observed_file in observed_root.rglob("*"):
            if observed_file.is_file():
                rel_path = str(observed_file.relative_to(observed_root))
                if rel_path not in expected_paths and not _matches_ignore(
                    rel_path, request.ignored_paths
                ):
                    differences.append(FilesystemDifference(
                        path=rel_path, kind=DiffKind.ADDED,
                    ))
                    review_focus.append(
                        f"Review added {rel_path} before adopting it "
                        "as expected output."
                    )
    except Exception:
        pass  # observation-only — do not crash on read errors

    # Determine status
    has_differences = any(
        d.kind in (DiffKind.ADDED, DiffKind.REMOVED, DiffKind.MODIFIED, DiffKind.UNKNOWN)
        for d in differences
    )
    has_inconclusive = any(d.kind == DiffKind.UNKNOWN for d in differences)

    if has_differences and not has_inconclusive:
        status = ReconciliationStatus.MISMATCH_OBSERVED
        summary = (
            "Differences were observed between expected and observed "
            "filesystem artifacts."
        )
    elif has_inconclusive:
        status = ReconciliationStatus.INCONCLUSIVE
        summary = (
            "Some artifacts could not be observed conclusively."
        )
    else:
        status = ReconciliationStatus.MATCHED
        summary = (
            "No differences were observed between expected and observed "
            "filesystem artifacts."
        )

    return FilesystemReconciliationOutput(
        status=status,
        summary=summary,
        observed_differences=differences,
        missing_artifacts=missing_expected,
        stale_artifacts=[],
        audit_gaps=[],
        recommended_review_focus=review_focus,
    )
