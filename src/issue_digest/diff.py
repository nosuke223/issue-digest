import json
from dataclasses import dataclass, field
from pathlib import Path

from issue_digest.classifier import CATEGORIES
from issue_digest.loader import Issue


class InvalidPreviousError(ValueError):
    """前回の JSON が `--json` の出力の形でないときのエラー。"""


@dataclass(frozen=True)
class PreviousIssue:
    number: int
    title: str
    url: str
    categories: tuple[str, ...]


@dataclass(frozen=True)
class DiffEntry:
    """変化した Issue。before / after は前回・今回の分類（CATEGORIES の順）。"""

    number: int
    title: str
    url: str
    before: tuple[str, ...]
    after: tuple[str, ...]


@dataclass(frozen=True)
class Diff:
    added: list[DiffEntry] = field(default_factory=list)
    removed: list[DiffEntry] = field(default_factory=list)
    moved: list[DiffEntry] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.added or self.removed or self.moved)


def load_previous(path: str | Path) -> dict[int, PreviousIssue]:
    """前回の `--json` の出力ファイルを読み込み、Issue 番号ごとの情報を返す。

    ファイルが読めないときは OSError、JSON として読めないときは ValueError、
    `--json` の出力の形でないときは InvalidPreviousError を送出する。
    """
    with open(path, encoding="utf-8") as f:
        return parse_previous(f.read())


def parse_previous(text: str) -> dict[int, PreviousIssue]:
    """前回の `--json` の出力（JSON 文字列）を解釈する。`diff` などほかのキーは無視する。"""
    data = json.loads(text)
    if not isinstance(data, dict) or not _is_int(data.get("total")):
        raise InvalidPreviousError
    entries = data.get("categories")
    if not isinstance(entries, list):
        raise InvalidPreviousError
    found: dict[int, tuple[str, str, set[str]]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise InvalidPreviousError
        label = entry.get("label")
        issues = entry.get("issues")
        if label not in CATEGORIES or not isinstance(issues, list):
            raise InvalidPreviousError
        for item in issues:
            if not isinstance(item, dict):
                raise InvalidPreviousError
            number, title, url = item.get("number"), item.get("title"), item.get("url")
            if not (_is_int(number) and isinstance(title, str) and isinstance(url, str)):
                raise InvalidPreviousError
            found.setdefault(number, (title, url, set()))[2].add(label)
    return {
        number: PreviousIssue(number, title, url, _ordered(categories))
        for number, (title, url, categories) in found.items()
    }


def compute_diff(previous: dict[int, PreviousIssue], classified: dict[str, list[Issue]]) -> Diff:
    """前回の Issue と今回の分類結果を比べる。各リストは Issue 番号の小さい順。"""
    current: dict[int, tuple[Issue, set[str]]] = {}
    for category, issues in classified.items():
        for issue in issues:
            current.setdefault(issue.number, (issue, set()))[1].add(category)
    diff = Diff()
    for number in sorted(current.keys() | previous.keys()):
        if number not in previous:
            issue, categories = current[number]
            diff.added.append(DiffEntry(number, issue.title, issue.url, (), _ordered(categories)))
        elif number not in current:
            old = previous[number]
            diff.removed.append(DiffEntry(number, old.title, old.url, old.categories, ()))
        else:
            issue, categories = current[number]
            after = _ordered(categories)
            if after != previous[number].categories:
                diff.moved.append(
                    DiffEntry(number, issue.title, issue.url, previous[number].categories, after)
                )
    return diff


def _ordered(categories: set[str]) -> tuple[str, ...]:
    return tuple(c for c in CATEGORIES if c in categories)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)
