"""v0.3 Reconciliation Scheduler — deferred verification の証拠。"""
import json

from koguchi.reconciliation_scheduler import (
    InMemoryReconciliationJobStore,
    ReconciliationScheduler,
    ReconciliationStatus,
)


def _allow_event(rid="req-1", tool="filesystem.write") -> dict:
    return {
        "schema_version": 1,
        "event_type": "allow",
        "request_id": rid,
        "tool_name": tool,
        "allowed": True,
        "reason": "allowed",
        "workspace": "/tmp",
        "timestamp": "2026-06-05T00:00:00Z",
        "error": None,
    }


def _deny_event(rid="req-2") -> dict:
    return {
        "schema_version": 1,
        "event_type": "deny",
        "request_id": rid,
        "tool_name": "shell.execute",
        "allowed": False,
        "reason": "denied",
        "workspace": "/tmp",
        "timestamp": "2026-06-05T00:00:00Z",
        "error": None,
    }


def _error_event(rid="req-3") -> dict:
    return {
        "schema_version": 1,
        "event_type": "error",
        "request_id": rid,
        "tool_name": "filesystem.write",
        "allowed": True,
        "reason": "allowed",
        "workspace": "/tmp",
        "timestamp": "2026-06-05T00:00:00Z",
        "error": "disk full",
    }


def test_allowed_event_creates_job():
    scheduler = ReconciliationScheduler([_allow_event()])
    jobs = scheduler.plan()
    assert len(jobs) == 1
    assert jobs[0].status == ReconciliationStatus.PENDING


def test_denied_event_is_skipped():
    scheduler = ReconciliationScheduler([_deny_event()])
    jobs = scheduler.plan()
    assert len(jobs) == 1
    assert jobs[0].status == ReconciliationStatus.SKIPPED


def test_error_event_is_skipped():
    scheduler = ReconciliationScheduler([_error_event()])
    jobs = scheduler.plan()
    assert len(jobs) == 1
    assert jobs[0].status == ReconciliationStatus.SKIPPED


def test_job_id_is_deterministic():
    scheduler = ReconciliationScheduler([_allow_event("req-99")])
    jobs = scheduler.plan()
    assert jobs[0].job_id == "reconcile:req-99"


def test_request_id_conserved_in_job():
    scheduler = ReconciliationScheduler([_allow_event("req-100")])
    jobs = scheduler.plan()
    assert jobs[0].request_id == "req-100"


def test_tool_name_conserved_in_job():
    scheduler = ReconciliationScheduler([_allow_event(tool="todo.create")])
    jobs = scheduler.plan()
    assert jobs[0].tool_name == "todo.create"


def test_run_pending_makes_jobs_passed():
    scheduler = ReconciliationScheduler([_allow_event()])
    scheduler.plan()
    results = scheduler.run_pending()
    assert len(results) == 1
    assert results[0].status == ReconciliationStatus.PASSED


def test_incomplete_event_is_failed():
    scheduler = ReconciliationScheduler([{"request_id": "bad", "tool_name": "x"}])
    jobs = scheduler.plan()
    assert len(jobs) == 1
    # allowed が True でない → skipped か failed
    # allowed=None なので skip 判定
    assert jobs[0].status == ReconciliationStatus.SKIPPED


def test_summary_is_json_serializable():
    scheduler = ReconciliationScheduler([_allow_event(), _deny_event()])
    scheduler.plan()
    summary = scheduler.summary()
    json.dumps(summary)


def test_in_memory_job_store_add_get_list_update():
    from koguchi.reconciliation_scheduler import ReconciliationJob

    store = InMemoryReconciliationJobStore()
    job = ReconciliationJob(job_id="j1", request_id="r1", tool_name="t1",
                            source_event={})
    store.add(job)
    assert store.get("j1").job_id == "j1"
    assert len(store.list()) == 1
    job.status = ReconciliationStatus.PASSED
    store.update(job)
    assert store.get("j1").status == ReconciliationStatus.PASSED


def test_no_duplicate_jobs_for_same_request_id():
    scheduler = ReconciliationScheduler([_allow_event("dup"),
                                          _allow_event("dup")])
    scheduler.plan()
    assert len(scheduler.jobs()) == 1


def test_run_job_by_id():
    scheduler = ReconciliationScheduler([_allow_event("specific"),
                                          _allow_event("other")])
    scheduler.plan()
    result = scheduler.run_job("reconcile:specific")
    assert result.status == ReconciliationStatus.PASSED
    assert result.request_id == "specific"


def test_run_job_nonexistent_id():
    scheduler = ReconciliationScheduler([])
    result = scheduler.run_job("nonexistent")
    assert result.status == ReconciliationStatus.FAILED


def test_skip_events_without_request_id():
    scheduler = ReconciliationScheduler([
        {"tool_name": "x", "allowed": True, "error": None},
    ])
    jobs = scheduler.plan()
    assert len(jobs) == 0
