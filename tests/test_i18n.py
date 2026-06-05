"""i18n モジュール — フォールバックチェーンとパラメータ展開の証拠。"""
from koguchi.i18n import get_locale, set_locale, t


def test_default_locale_is_ja():
    set_locale("ja")
    assert get_locale() == "ja"


def test_t_returns_japanese_by_default():
    set_locale("ja")
    msg = t("err.envelope_required")
    assert "ActionEnvelope" in msg
    assert "必須" in msg


def test_t_english_locale():
    set_locale("en")
    msg = t("err.envelope_required")
    assert msg == "ActionEnvelope is required"


def test_t_chinese_simplified_locale():
    set_locale("zh-CN")
    msg = t("err.envelope_required")
    assert msg == "ActionEnvelope 是必需的"


def test_t_chinese_traditional_locale():
    set_locale("zh-TW")
    msg = t("err.envelope_required")
    assert msg == "ActionEnvelope 是必要的"


def test_t_korean_locale():
    set_locale("ko")
    msg = t("err.envelope_required")
    assert msg == "ActionEnvelope이 필요합니다"


def test_t_parameter_expansion():
    set_locale("ja")
    msg = t("err.workspace_boundary", target="/tmp/evil.txt")
    assert "/tmp/evil.txt" in msg
    assert "workspace_dir" in msg


def test_t_parameter_expansion_en():
    set_locale("en")
    msg = t("err.workspace_boundary", target="/tmp/evil.txt")
    assert msg == "/tmp/evil.txt is outside workspace_dir"


def test_t_fallback_to_ja_for_unknown_locale():
    set_locale("fr")
    msg = t("err.envelope_required")
    # フランス語は未定義 → ja にフォールバック
    assert "必須" in msg


def test_t_fallback_to_key_name_for_missing_key():
    set_locale("ja")
    msg = t("does.not.exist")
    assert msg == "does.not.exist"


def test_t_reconcile_messages_in_all_locales():
    """全 reconciliation メッセージが全ロケールで空文字列にならない。"""
    keys = [
        "reconcile.target_not_found",
        "reconcile.target_exists_unconfirmed",
        "reconcile.target_deleted",
        "reconcile.target_consistent",
        "reconcile.target_diverged",
        "reconcile.unrecorded_external_change",
    ]
    for locale in ["ja", "en", "zh-CN", "zh-TW", "ko"]:
        set_locale(locale)
        for key in keys:
            msg = t(key, target="/tmp/x", digest="abc", path="/tmp/y")
            assert len(msg) > 0, f"{key} in {locale} returned empty"


def test_t_chain_messages_in_all_locales():
    """全 chain メッセージが全ロケールで空文字列にならない。"""
    keys = ["chain.previous_hash_mismatch", "chain.hash_mismatch"]
    for locale in ["ja", "en", "zh-CN", "zh-TW", "ko"]:
        set_locale(locale)
        for key in keys:
            msg = t(key, expected="abc", actual="def", stored="abc", recomputed="def")
            assert len(msg) > 0, f"{key} in {locale} returned empty"
