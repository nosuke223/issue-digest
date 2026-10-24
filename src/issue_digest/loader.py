import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    labels: list[str]
    url: str
    updated_at: datetime | None = None
    assignees: list[str] = field(default_factory=list)
    created_at: datetime | None = None


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
    """
    data = json.loads(text)
    return [
        Issue(
            number=item["number"],
            title=item["title"],
            labels=[label["name"] for label in item["labels"]],
            url=item["url"],
            updated_at=_parse_datetime(item["number"], item.get("updatedAt"), "updatedAt"),
            assignees=[a["login"] for a in item.get("assignees") or []],
            created_at=_parse_datetime(item["number"], item.get("createdAt"), "createdAt"),
        )
        for item in data
    ]


def _parse_datetime(number: int, value: str | None, key: str) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except (ValueError, TypeError) as e:
        raise InvalidUpdatedAtError(number, value, key) from e
    # タイムゾーンがない値は UTC とみなす
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
