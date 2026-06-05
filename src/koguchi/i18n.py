"""Koguchi i18n — 軽量 JSON メッセージカタログによる多言語対応。

フォールバックチェーン: 要求ロケール → ja → キー名そのまま
ロケール指定: 環境変数 KOGUCHI_LOCALE > set_locale() > デフォルト "ja"
"""

import json
import os
from pathlib import Path

_LOCALES_DIR = Path(__file__).resolve().parent / "locales"
_DEFAULT_LOCALE = "ja"
_locale = os.environ.get("KOGUCHI_LOCALE", _DEFAULT_LOCALE)
_catalogs: dict[str, dict[str, str]] = {}


def _load_catalog(locale: str) -> dict[str, str]:
    """ロケールに対応する JSON カタログを読み込む。"""
    path = _LOCALES_DIR / f"{locale}.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as fh:
        return dict(json.load(fh))


def _get_catalog(locale: str) -> dict[str, str]:
    if locale not in _catalogs:
        _catalogs[locale] = _load_catalog(locale)
    return _catalogs[locale]


def set_locale(locale: str) -> None:
    """現在のロケールを設定する。"""
    global _locale
    _locale = locale


def get_locale() -> str:
    """現在のロケールを返す。"""
    return _locale


def t(key: str, **params: object) -> str:
    """メッセージキーを現在のロケールで翻訳し、パラメータを展開する。

    Args:
        key: メッセージキー（例: "err.envelope_required"）
        **params: プレースホルダ展開用のパラメータ

    Returns:
        翻訳・展開された文字列

    Fallback:
        1. 現在のロケールにキーがあればそれを返す
        2. なければ ja（ベース言語）を試す
        3. それもなければキー名をそのまま返す（開発者向けシグナル）
    """
    template: str | None = None

    # 1. 要求ロケール
    if _locale != _DEFAULT_LOCALE:
        template = _get_catalog(_locale).get(key)

    # 2. ベース言語フォールバック
    if template is None and _locale != _DEFAULT_LOCALE or template is None:
        template = _get_catalog(_DEFAULT_LOCALE).get(key)

    # 3. キー名そのまま
    if template is None:
        template = key

    # プレースホルダ展開（{{param}} → str.format 互換の {param} に変換）
    format_template = template.replace("{{", "{").replace("}}", "}")
    try:
        return format_template.format(**params)
    except KeyError:
        # パラメータ不足時はテンプレートをそのまま返す
        return format_template
