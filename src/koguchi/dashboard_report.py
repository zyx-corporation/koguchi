"""Dashboard Static HTML Report — read-only review artifact。

v0.8: DashboardSnapshot から static HTML を生成する。
control plane ではない。security proof ではない。
"""

import html
from dataclasses import dataclass
from typing import Any

from koguchi.dashboard import DashboardSnapshot


@dataclass(frozen=True)
class HtmlReportOptions:
    title: str = "Koguchi Dashboard Report"
    include_generated_at: bool = True
    include_limitations: bool = True


def _esc(s: object) -> str:
    return html.escape(str(s))


def render_html_report(
    snapshot: DashboardSnapshot,
    options: HtmlReportOptions | None = None,
) -> str:
    """DashboardSnapshot から read-only static HTML report を生成する。"""
    if options is None:
        options = HtmlReportOptions()
    a = snapshot.audit
    r = snapshot.reconciliation
    c = snapshot.chokepoint
    rr = getattr(snapshot, "reconciliation_results", None)

    sections: list[str] = []

    sections.append(_render_header(options))
    sections.append(_render_status_scope())
    if options.include_generated_at:
        sections.append(_render_generated_at(snapshot))
    sections.append(_render_audit_summary(a))
    sections.append(_render_reconciliation_summary(r))
    if rr:
        sections.append(_render_result_summary(rr))
    sections.append(_render_backend_counts(a))
    sections.append(_render_chokepoint(c))
    if options.include_limitations:
        sections.append(_render_limitations())

    body = "\n".join(sections)
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{_esc(options.title)}</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 1em; }}
h1 {{ border-bottom: 2px solid #333; }}
h2 {{ border-bottom: 1px solid #999; }}
table {{ border-collapse: collapse; width: 100%; }}
td, th {{ border: 1px solid #ddd; padding: 4px 8px; text-align: left; }}
.note {{ font-style: italic; color: #666; }}
.limitations {{ font-size: 0.9em; color: #666; }}
</style>
</head>
<body>
{body}
</body>
</html>"""


def _render_header(options: HtmlReportOptions) -> str:
    return f"<h1>{_esc(options.title)}</h1>"


def _render_status_scope() -> str:
    return """\
<div class="note">
<p>This report is a <strong>read-only static observation artifact</strong>.
It is not a control plane, not a security proof, and not a compliance certification.</p>
</div>"""


def _render_generated_at(snapshot: DashboardSnapshot) -> str:
    return f"<p><strong>Generated at:</strong> {_esc(snapshot.generated_at)}</p>"


def _render_audit_summary(a: Any) -> str:
    rows = f"""\
  <tr><td>Total events</td><td>{a.total_events}</td></tr>
  <tr><td>Allowed</td><td>{a.allowed_events}</td></tr>
  <tr><td>Denied</td><td>{a.denied_events}</td></tr>
  <tr><td>Errors</td><td>{a.error_events}</td></tr>
  <tr><td>Malformed</td><td>{a.malformed_events}</td></tr>"""
    tools = "".join(
        f"<tr><td>Tool: {_esc(t)}</td><td>{c}</td></tr>"
        for t, c in sorted(a.tools.items())
    )
    # Recent request_ids (max 5)
    recent = "".join(
        f"<tr><td>Request ID</td><td>{_esc(rid)}</td></tr>"
        for rid in a.recent_request_ids[:5]
    )
    return f"""\
<h2>Audit Summary</h2>
<table>{rows}{tools}{recent}</table>"""


def _render_reconciliation_summary(r: Any) -> str:
    return f"""\
<h2>Reconciliation Summary</h2>
<table>
  <tr><td>Total jobs</td><td>{r.total_jobs}</td></tr>
  <tr><td>Pending</td><td>{r.pending}</td></tr>
  <tr><td>Passed</td><td>{r.passed}</td></tr>
  <tr><td>Failed</td><td>{r.failed}</td></tr>
  <tr><td>Skipped</td><td>{r.skipped}</td></tr>
</table>"""


def _render_result_summary(rr: Any) -> str:
    rows = f"""\
  <tr><td>Total results</td><td>{rr.total_results}</td></tr>
  <tr><td>Passed</td><td>{rr.passed}</td></tr>
  <tr><td>Failed</td><td>{rr.failed}</td></tr>
  <tr><td>Skipped</td><td>{rr.skipped}</td></tr>"""
    if rr.last_checked_at:
        rows += f"  <tr><td>Last checked</td><td>{_esc(rr.last_checked_at)}</td></tr>"
    backend_rows = "".join(
        f"<tr><td>Backend: {_esc(b)}</td><td>{c}</td></tr>"
        for b, c in sorted(getattr(rr, "backend_counts", {}).items())
    )
    return f"""\
<h2>Reconciliation Results</h2>
<p class="note">Audit records describe what happened during execution.
Reconciliation results describe how those executions were later checked.</p>
<table>{rows}{backend_rows}</table>"""


def _render_backend_counts(a: Any) -> str:
    rows = "".join(
        f"<tr><td>{_esc(b)}</td><td>{c}</td></tr>"
        for b, c in sorted(getattr(a, "backend_counts", {}).items())
    )
    if not rows:
        return ""
    return f"""\
<h2>Execution Backends</h2>
<table>
  <tr><th>Backend</th><th>Count</th></tr>
  {rows}
</table>"""


def _render_chokepoint(c: Any) -> str:
    return f"""\
<h2>Rust Chokepoint</h2>
<table>
  <tr><td>Configured</td><td>{c.configured}</td></tr>
  <tr><td>Available</td><td>{c.available}</td></tr>
  <tr><td>Binary path</td><td>{_esc(c.binary_path or '—')}</td></tr>
  <tr><td>Note</td><td>{_esc(c.note or '—')}</td></tr>
</table>"""


def _render_limitations() -> str:
    return """\
<h2>Known Limitations</h2>
<div class="limitations">
<ul>
<li>Koguchi is not a security sandbox.</li>
<li>Python RuntimeBoundary is best-effort.</li>
<li>Rust Chokepoint is an optional experimental backend, not a production sandbox.</li>
<li>Dashboard report is read-only and static.</li>
<li>Audit and reconciliation logs are JSONL, not cryptographically sealed.</li>
</ul>
</div>"""
