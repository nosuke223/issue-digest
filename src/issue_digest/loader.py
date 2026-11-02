import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

# https://<ホスト>/<owner>/<repo>/issues/<番号> または .../pull/<番号>（ホストは問わない）
_ISSUE_URL = re.compile(r"https?://[^/]+/([^/]+)/([^/]+)/(?:issues|pull)/\d+/?(?:[?#].*)?")


def repository_of(url: str) -> str | None:
    """Issue の URL からリポジトリ名（`owner/repo`）を読み取る。読み取れなければ None。"""
    match = _ISSUE_URL.fullmatch(url)
    return None if match is None else f"{match[1]}/{match[2]}"


def issue_key(url: str) -> str:
    """Issue を見分けるキー。URL の大文字と小文字を区別しない。"""
    return url.lower()


def order_key(repository: str | None, number: int, url: str) -> tuple:
    """Issue の既定の並びのキー。リポジトリ名（大文字と小文字を区別しない）の順、
    同じリポジトリの中は番号の小さい順。リポジトリ名がないものは最後に番号の小さい順。"""
    if repository is None:
        return (1, "", number, url)
    return (0, repository.lower(), number, url)


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    labels: list[str]
    url: str
    updated_at: datetime | None = None
    assignees: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    milestone: str | None = None
    author: str | None = None

    @property
    def repository(self) -> str | None:
        return repository_of(self.url)

    @property
    def key(self) -> str:
        return issue_key(self.url)

    @property
    def order(self) -> tuple:
        return order_key(self.repository, self.number, self.url)


class InvalidUpdatedAtError(ValueError):
    """`updatedAt`（または `createdAt`）が日時として読めないときのエラー。"""

    def __init__(self, number: object, value: object, key: str = "updatedAt") -> None:
        super().__init__(f"Issue #{number} の {key} を日時として読めません: {value}")
        self.number = number
        self.value = value


def load_issues(path: str | Path) -> list[Issue]:
    """`gh issue list --json number,title,labels,url` の出力ファイルを読み込む。"""
    with open(path, encoding="utf-8") as f:
        return parse_issues(f.read())


def parse_issues(text: str) -> list[Issue]:
    """`gh issue list --json number,title,labels,url` の出力（JSON 文字列）を解釈する。

    各 Issue の `updatedAt` と `createdAt`（ISO 8601 形式）は任意。
    ないときや null のときは None になる。
    `assignees`（`[{"login": "alice"}]` の形）も任意。ないとき、null、空のときは担当者なし。
    `milestone`（`{"title": "v1.0"}` の形）も任意。ないとき、null のときはマイルストーンなし。
    `author`（`{"login": "alice"}` の形）も任意。ないとき、null のときは作成者なし。
    `milestone` と `author` がオブジェクトでないときは TypeError になる。
    項目の型が `gh` の出力と違うとき（`number` が整数でない、`title`、`url`、
    `labels` の各 `name`、`assignees` の各 `login` が文字列でない、
    `milestone` の `title`、`author` の `login` が文字列でも null でもない）も TypeError になる。
    """
    data = json.loads(text)
    return [
        Issue(
            number=_int(item["number"]),
            title=_str(item["title"]),
            labels=[_str(label["name"]) for label in item["labels"]],
            url=_str(item["url"]),
            updated_at=_parse_datetime(item["number"], item.get("updatedAt"), "updatedAt"),
            assignees=[_str(a["login"]) for a in item.get("assignees") or []],
            created_at=_parse_datetime(item["number"], item.get("createdAt"), "createdAt"),
            milestone=_object_field(item.get("milestone"), "title"),
            author=_object_field(item.get("author"), "login"),
        )
        for item in data
    ]


def _int(value: object) -> int:
    """整数であることを確かめる。整数でなければ（真偽値も）TypeError。"""
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"整数ではありません: {value!r}")
    return value


def _str(value: object) -> str:
    """文字列であることを確かめる。文字列でなければ TypeError。"""
    if not isinstance(value, str):
        raise TypeError(f"文字列ではありません: {value!r}")
    return value


def _object_field(value: object, key: str) -> str | None:
    """`{"<key>": ...}` の形の項目から値を読む。null は None、オブジェクト以外は TypeError。
    値は文字列か null（または無い）で、それ以外は TypeError。"""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise TypeError(f"オブジェクトではありません: {value!r}")
    field_value = value.get(key)
    return None if field_value is None else _str(field_value)


def merge_issues(groups: list[list[Issue]]) -> list[Issue]:
    """複数の入力の Issue を1つにまとめる。URL が同じ Issue は最初に出てきた1件だけを使う。"""
    merged: dict[str, Issue] = {}
    for issues in groups:
        for issue in issues:
            merged.setdefault(issue.key, issue)
    return list(merged.values())


def _parse_datetime(number: int, value: str | None, key: str) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except (ValueError, TypeError) as e:
        raise InvalidUpdatedAtError(number, value, key) from e
    # タイムゾーンがない値は UTC とみなす
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
