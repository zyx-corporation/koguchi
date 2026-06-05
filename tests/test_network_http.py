"""Phase 3: network.http_get — 全4値 side_effect_observed の証拠。"""
import hashlib
import http.server
import threading
import uuid

import pytest

from koguchi.envelope import ActionEnvelope
from koguchi.errors import EnvelopeRequiredError
from koguchi.events import ProxyResult
from koguchi.proxy import ToolProxy
from koguchi.store import SQLiteExecutionStore


def _make_http_envelope(url: str) -> ActionEnvelope:
    return ActionEnvelope(
        action_id=str(uuid.uuid4()),
        tool="network.http_get",
        target=url,
        parameters_digest=hashlib.sha256(url.encode()).hexdigest(),
        permission_scope="network",
        risk_class=["http_request"],
    )


# --- テストサーバー ---

Handler = http.server.BaseHTTPRequestHandler


def _start_server(handler: type[Handler]) -> tuple[str, threading.Thread]:
    """指定されたハンドラで HTTP サーバーを起動し、(URL, thread) を返す。"""
    server = http.server.HTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}/"

    def serve():
        server.handle_request()

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    return url, t


class _OkHandler(http.server.BaseHTTPRequestHandler):
    """常に 200 OK + "hello" を返す。"""

    def do_GET(self):
        body = b"hello"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # テストログを抑制


class _PartialHandler(http.server.BaseHTTPRequestHandler):
    """Content-Length を偽って途中で切断する → IncompleteRead。"""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", "100")  # 100 bytes と宣言
        self.end_headers()
        self.wfile.write(b"short")  # 実際は 5 bytes → IncompleteRead

    def log_message(self, format, *args):
        pass


class _SlowHandler(http.server.BaseHTTPRequestHandler):
    """応答を遅延させる → timeout。"""

    def do_GET(self):
        import time

        time.sleep(5)  # timeout より長い

    def log_message(self, format, *args):
        pass


class _ErrorHandler(http.server.BaseHTTPRequestHandler):
    """500 エラーを返す。"""

    def do_GET(self):
        body = b"server error"
        self.send_response(500)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


# --- confirmed ---

def test_http_get_success():
    """正常なレスポンス → SUCCESS, confirmed。"""
    url, _ = _start_server(_OkHandler)
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy("/tmp", store)

    envelope = _make_http_envelope(url)
    result = proxy.http_get(envelope=envelope, url=url)

    assert result == ProxyResult.SUCCESS
    events = store.events_for(envelope.action_id)
    committed = [e for e in events if e.event_type == "execution_committed"][0]
    assert committed.side_effect_observed == "confirmed"
    assert committed.result_digest is not None


def test_http_get_http_error_is_confirmed():
    """4xx/5xx でもレスポンスを得た → confirmed。"""
    url, _ = _start_server(_ErrorHandler)
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy("/tmp", store)

    envelope = _make_http_envelope(url)
    result = proxy.http_get(envelope=envelope, url=url)

    assert result == ProxyResult.SUCCESS
    events = store.events_for(envelope.action_id)
    committed = [e for e in events if e.event_type == "execution_committed"][0]
    assert committed.side_effect_observed == "confirmed"


# --- partial ---

def test_http_get_partial():
    """IncompleteRead → FAILURE, side_effect_observed = partial。"""
    url, _ = _start_server(_PartialHandler)
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy("/tmp", store)

    envelope = _make_http_envelope(url)
    result = proxy.http_get(envelope=envelope, url=url)

    assert result == ProxyResult.FAILURE
    events = store.events_for(envelope.action_id)
    failed = [e for e in events if e.event_type == "execution_failed"][0]
    assert failed.side_effect_observed == "partial"
    assert failed.result_digest is not None  # 部分 body の digest


# --- unknown ---

def test_http_get_timeout():
    """タイムアウト → FAILURE, side_effect_observed = unknown。"""
    url, _ = _start_server(_SlowHandler)
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy("/tmp", store)

    envelope = _make_http_envelope(url)
    result = proxy.http_get(envelope=envelope, url=url, timeout=0.5)

    assert result == ProxyResult.FAILURE
    events = store.events_for(envelope.action_id)
    failed = [e for e in events if e.event_type == "execution_failed"][0]
    assert failed.side_effect_observed == "unknown"


# --- none ---

def test_http_get_connection_refused():
    """接続拒否 → FAILURE, side_effect_observed = none。"""
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy("/tmp", store)

    # 存在しないポートに接続
    envelope = _make_http_envelope("http://127.0.0.1:1/")
    result = proxy.http_get(envelope=envelope, url="http://127.0.0.1:1/", timeout=0.5)

    assert result == ProxyResult.FAILURE
    events = store.events_for(envelope.action_id)
    failed = [e for e in events if e.event_type == "execution_failed"][0]
    assert failed.side_effect_observed == "none"


# --- INV-1a ---

def test_http_get_requires_envelope(workspace, store):
    """envelope=None → EnvelopeRequiredError。"""
    proxy = ToolProxy(str(workspace), store)
    with pytest.raises(EnvelopeRequiredError):
        proxy.http_get(envelope=None, url="http://example.com")
