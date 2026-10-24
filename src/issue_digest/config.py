import tomllib
from pathlib import Path
from typing import Any

from issue_digest.classifier import CATEGORIES

DEFAULT_CONFIG_PATH = ".issue-digest.toml"

_BOOL_KEYS = ("hide_empty", "summary", "show_assignees", "json")
_KEYS = (*_BOOL_KEYS, "only", "stale", "sort")


class ConfigError(Exception):
    """設定ファイルの内容が不正なとき。メッセージは利用者にそのまま見せる。"""


def load_config(path: str | None) -> dict[str, Any]:
    """設定ファイルを読んで検査した辞書を返す。

    path が None のときはカレントディレクトリの既定のファイルを探し、なければ空の辞書を返す。
    path を指定してファイルがなければ FileNotFoundError を投げる。
    """
    target = Path(DEFAULT_CONFIG_PATH if path is None else path)
    if path is None and not target.is_file():
        return {}
    with open(target, "rb") as f:
        try:
            data = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ConfigError(f"設定ファイルを TOML として読み込めません: {target} ({e})") from e
        except UnicodeDecodeError as e:
            raise ConfigError(
                f"設定ファイルを UTF-8 として読み込めません: {target} ({e})"
            ) from e
    return _validate(data)


def _validate(data: dict[str, Any]) -> dict[str, Any]:
    for key, value in data.items():
        if key not in _KEYS:
            raise ConfigError(f"設定ファイルに知らないキーがあります: {key}")
        if key in _BOOL_KEYS:
            if not isinstance(value, bool):
                raise ConfigError(f"設定ファイルの {key} には true か false を指定してください")
        elif key == "stale":
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ConfigError(
                    f"設定ファイルの stale には0以上の整数を指定してください: {value}"
                )
        elif key == "sort":
            if value != "updated":
                raise ConfigError(
                    f'設定ファイルの sort に指定できるのは "updated" だけです: {value}'
                )
        elif key == "only":
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                raise ConfigError("設定ファイルの only には文字列の配列を指定してください")
            for label in value:
                if label not in CATEGORIES:
                    raise ConfigError(
                        f"設定ファイルの only に指定できないラベルです: {label}\n"
                        f"指定できるラベル: {', '.join(CATEGORIES)}"
                    )
    return data
