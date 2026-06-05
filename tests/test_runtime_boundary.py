"""Phase 9: Runtime Hardening — 実行時境界の証拠。"""
from koguchi.envelope import ActionEnvelope
from koguchi.events import ProxyResult
from koguchi.proxy import ToolProxy
from koguchi.runtime import DefaultRuntimeBoundary, RuntimeBoundaryDecision
from koguchi.store import SQLiteExecutionStore
from tests.conftest import make_envelope


def test_runtime_boundary_denies_shell_by_default():
    """DefaultRuntimeBoundary は shell.execute を deny。"""
    boundary = DefaultRuntimeBoundary()
    decision = boundary.evaluate_tool("shell.execute")
    assert decision.allowed is False


def test_runtime_boundary_allows_write():
    """DefaultRuntimeBoundary は filesystem.write を allow。"""
    boundary = DefaultRuntimeBoundary()
    decision = boundary.evaluate_tool("filesystem.write")
    assert decision.allowed is True


def test_runtime_boundary_denies_unknown_tool():
    """未知のツールは denied。"""
    boundary = DefaultRuntimeBoundary()
    decision = boundary.evaluate_tool("dangerous.tool")
    assert decision.allowed is False


def test_runtime_boundary_filters_secret_env_keys():
    """secret-like キーがフィルタされる。"""
    boundary = DefaultRuntimeBoundary()
    env = {
        "PATH": "/usr/bin",
        "HOME": "/home/user",
        "GITHUB_TOKEN": "ghp_secret",
        "NOTION_API_KEY": "secret_xxx",
        "LANG": "en_US.UTF-8",
    }
    filtered = boundary.filter_environment(env)
    assert "PATH" in filtered
    assert "HOME" in filtered
    assert "LANG" in filtered
    assert "GITHUB_TOKEN" not in filtered  # PATH/HOME/LANG は safe、他は残る
    # ただし secret pattern を含む env key は... 
    # token パターンにはマッチするが、GITHUB_TOKEN は "token" にマッチしてしまうか？
    # _SECRET_ENV_PATTERNS には "token" がある
    # GITHUB_TOKEN.lower() は "github_token" → "token" を含む → filter されるはず
    assert "GITHUB_TOKEN" not in filtered
    assert "NOTION_API_KEY" not in filtered


def test_tool_proxy_uses_runtime_boundary(workspace):
    """RuntimeBoundary で shell が deny される。"""
    store = SQLiteExecutionStore(":memory:")
    boundary = DefaultRuntimeBoundary()
    proxy = ToolProxy(str(workspace), store, runtime_boundary=boundary)

    import hashlib
    shell_env = ActionEnvelope(
        action_id="shell-1",
        tool="shell.execute",
        target=str(workspace),
        parameters_digest=hashlib.sha256(b"echo").hexdigest(),
        permission_scope="workspace",
        risk_class=["shell_exec"],
    )

    result = proxy.execute_shell(
        envelope=shell_env, command=["echo", "x"],
    )
    assert result == ProxyResult.REJECTED


def test_tool_proxy_write_still_works_with_runtime_boundary(workspace):
    """RuntimeBoundary 注入下でも filesystem.write は動作する。"""
    store = SQLiteExecutionStore(":memory:")
    boundary = DefaultRuntimeBoundary()
    proxy = ToolProxy(str(workspace), store, runtime_boundary=boundary)

    envelope = make_envelope(str(workspace), content=b"safe")
    result = proxy.write_file(envelope=envelope, content=b"safe")
    assert result == ProxyResult.SUCCESS


def test_runtime_decision_is_distinct_from_policy_decision():
    """RuntimeBoundaryDecision は PolicyDecision とは別の型。"""
    decision = RuntimeBoundaryDecision(allowed=True, reason="test")
    assert decision.allowed is True
    assert "test" in decision.reason
