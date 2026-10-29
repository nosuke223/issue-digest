import tomllib
from pathlib import Path
from typing import Any

from issue_digest.classifier import CATEGORIES

DEFAULT_CONFIG_PATH = ".issue-digest.toml"

_BOOL_KEYS = (
    "hide_empty",
    "summary",
    "show_assignees",
    "json",
    "show_labels",
    "age",
    "show_milestone",
    "reverse",
)
_KEYS = (
    *_BOOL_KEYS,
    "only",
    "exclude",
    "stale",
    "sort",
    "headings",
    "title",
    "limit",
    "max_chars",
    "group_by",
    "category_labels",
)


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
            raise ConfigError(f"設定ファイルを UTF-8 として読み込めません: {target} ({e})") from e
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
        elif key == "limit":
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ConfigError(
                    f"設定ファイルの limit には1以上の整数を指定してください: {value}"
                )
        elif key == "max_chars":
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ConfigError(
                    f"設定ファイルの max_chars には1以上の整数を指定してください: {value}"
                )
        elif key == "group_by":
            if value != "assignee":
                raise ConfigError(
                    f'設定ファイルの group_by には "assignee" を指定してください: {value}'
                )
        elif key == "title":
            if not isinstance(value, str) or value == "":
                raise ConfigError("設定ファイルの title には1文字以上の文字列を指定してください")
        elif key == "sort":
            if value not in ("updated", "created"):
                raise ConfigError(
                    f'設定ファイルの sort には "updated" か "created" を指定してください: {value}'
                )
        elif key in ("only", "exclude"):
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                raise ConfigError(f"設定ファイルの {key} には文字列の配列を指定してください")
            for label in value:
                if label not in CATEGORIES:
                    raise ConfigError(
                        f"設定ファイルの {key} に指定できないラベルです: {label}\n"
                        f"指定できるラベル: {', '.join(CATEGORIES)}"
                    )
        elif key == "headings":
            if not isinstance(value, dict):
                raise ConfigError(
                    "設定ファイルの headings はテーブル（[headings]）で指定してください"
                )
            for label, heading in value.items():
                if label not in CATEGORIES:
                    raise ConfigError(
                        f"設定ファイルの headings に指定できないラベルです: {label}\n"
                        f"指定できるラベル: {', '.join(CATEGORIES)}"
                    )
                if not isinstance(heading, str) or heading == "":
                    raise ConfigError(
                        f"設定ファイルの headings.{label} には1文字以上の文字列を指定してください"
                    )
        elif key == "category_labels":
            if not isinstance(value, dict):
                raise ConfigError(
                    "設定ファイルの category_labels はテーブル（[category_labels]）で"
                    "指定してください"
                )
            for category, labels in value.items():
                if category not in CATEGORIES[:-1]:
                    raise ConfigError(
                        f"設定ファイルの category_labels に指定できない分類です: {category}\n"
                        f"指定できる分類: {', '.join(CATEGORIES[:-1])}"
                    )
                if (
                    not isinstance(labels, list)
                    or not labels
                    or not all(isinstance(v, str) and v != "" for v in labels)
                ):
                    raise ConfigError(
                        f'設定ファイルの category_labels."{category}" には、'
                        "1文字以上の文字列を1つ以上入れた配列を指定してください"
                    )
    return data
