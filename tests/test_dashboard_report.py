"""v0.8 Dashboard Static HTML Report — read-only artifact の証拠。"""
from koguchi.dashboard import DashboardBuilder
from koguchi.dashboard_report import HtmlReportOptions, render_html_report


def test_render_returns_html():
    builder = DashboardBuilder()
    snapshot = builder.build()
    html_str = render_html_report(snapshot)
    assert "<!DOCTYPE html>" in html_str
    assert "<html" in html_str


def test_html_includes_title():
    builder = DashboardBuilder()
    snapshot = builder.build()
    html_str = render_html_report(snapshot, HtmlReportOptions(title="My Report"))
    assert "My Report" in html_str


def test_html_includes_generated_at():
    builder = DashboardBuilder()
    snapshot = builder.build()
    html_str = render_html_report(snapshot)
    assert "Generated at:" in html_str


def test_html_includes_audit_summary():
    builder = DashboardBuilder(audit_events=[{
        "request_id": "r1", "tool_name": "filesystem.write",
        "allowed": True, "reason": "ok", "workspace": "/tmp",
        "timestamp": "2026-06-05T00:00:00Z", "error": None,
        "execution_backend": "python",
    }])
    snapshot = builder.build()
    html_str = render_html_report(snapshot)
    assert "Audit Summary" in html_str
    assert "python" in html_str


def test_html_includes_reconciliation_summary():
    builder = DashboardBuilder()
    snapshot = builder.build()
    html_str = render_html_report(snapshot)
    assert "Reconciliation Summary" in html_str


def test_html_includes_chokepoint():
    builder = DashboardBuilder()
    snapshot = builder.build()
    html_str = render_html_report(snapshot)
    assert "Rust Chokepoint" in html_str


def test_html_includes_limitations():
    builder = DashboardBuilder()
    snapshot = builder.build()
    html_str = render_html_report(snapshot)
    assert "not a security sandbox" in html_str


def test_html_has_no_form():
    builder = DashboardBuilder()
    html_str = render_html_report(builder.build())
    assert "<form" not in html_str.lower()


def test_html_has_no_button():
    builder = DashboardBuilder()
    html_str = render_html_report(builder.build())
    assert "<button" not in html_str.lower()


def test_html_has_no_script():
    builder = DashboardBuilder()
    html_str = render_html_report(builder.build())
    assert "<script" not in html_str.lower()


def test_html_escapes_special_chars():
    builder = DashboardBuilder(audit_events=[{
        "request_id": "<script>alert(1)</script>",
        "tool_name": "x&y",
        "allowed": True, "reason": "ok", "workspace": "/tmp",
        "timestamp": "2026-06-05T00:00:00Z", "error": None,
    }])
    snapshot = builder.build()
    html_str = render_html_report(snapshot)
    assert "<script>" not in html_str
    assert "&lt;script&gt;" in html_str
    assert "x&amp;y" in html_str
