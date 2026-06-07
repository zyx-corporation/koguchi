"""v0.19 ResultRecord JSON Schema — validation spike の証拠。"""
import json
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate

SCHEMA_DIR = Path(__file__).parent.parent / "schemas"
SCHEMA_FILE = "reconciliation-result-record.v0.schema.json"
SCHEMA_PATH = SCHEMA_DIR / SCHEMA_FILE


def _schema():
    return json.loads(SCHEMA_PATH.read_text())


def _valid_record(**overrides):
    r = {
        "schema_version": "koguchi.reconciliation.result.v0",
        "result_id": "r1",
        "request_id": "req1",
        "status": "matched",
        "summary": "No differences observed.",
        "observed_differences": [],
        "missing_artifacts": [],
        "stale_artifacts": [],
        "audit_gaps": [],
        "recommended_review_focus": [],
        "boundary": {
            "review_focus_only": True,
            "correctness_decision": False,
            "enforcement": False,
            "approval": False,
            "rejection": False,
        },
    }
    r.update(overrides)
    return r


def test_valid_matched_record():
    validate(_valid_record(), _schema())


def test_valid_mismatch_record():
    validate(_valid_record(status="mismatch_observed", summary="Diffs found"), _schema())


def test_missing_schema_version_invalid():
    r = _valid_record()
    del r["schema_version"]
    with pytest.raises(ValidationError):
        validate(r, _schema())


def test_missing_result_id_invalid():
    r = _valid_record()
    del r["result_id"]
    with pytest.raises(ValidationError):
        validate(r, _schema())


def test_invalid_status():
    with pytest.raises(ValidationError):
        validate(_valid_record(status="failure"), _schema())


def test_invalid_kind_in_difference():
    r = _valid_record()
    r["observed_differences"] = [{"path": "x.txt", "kind": "deleted"}]
    with pytest.raises(ValidationError):
        validate(r, _schema())


def test_missing_boundary_invalid():
    r = _valid_record()
    del r["boundary"]
    with pytest.raises(ValidationError):
        validate(r, _schema())


def test_correctness_decision_true_invalid():
    r = _valid_record()
    r["boundary"]["correctness_decision"] = True
    with pytest.raises(ValidationError):
        validate(r, _schema())


def test_enforcement_true_invalid():
    r = _valid_record()
    r["boundary"]["enforcement"] = True
    with pytest.raises(ValidationError):
        validate(r, _schema())


def test_approval_true_invalid():
    r = _valid_record()
    r["boundary"]["approval"] = True
    with pytest.raises(ValidationError):
        validate(r, _schema())


def test_unknown_field_allowed():
    r = _valid_record()
    r["custom_note"] = "extra info"
    validate(r, _schema())


def _diff(path, kind, sha=None):
    return {"path": path, "kind": kind, "expected_sha256": sha, "observed_sha256": sha}


def test_difference_with_removed_is_valid():
    r = _valid_record(
        status="mismatch_observed",
        summary="Diffs found",
        observed_differences=[_diff("x.txt", "removed")],
    )
    validate(r, _schema())


def test_difference_with_added_is_valid():
    r = _valid_record(
        status="mismatch_observed",
        summary="Diffs found",
        observed_differences=[_diff("extra.log", "added")],
    )
    validate(r, _schema())
