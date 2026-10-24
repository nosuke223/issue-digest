import json
import sys
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


def load_issues(path: str | Path) -> list[Issue]:
    """`gh issue list --json number,title,labels,url` の出力ファイルを読み込む。"""
    with open(path, encoding="utf-8") as f:
        return parse_issues(f.read())


def parse_issues(text: str) -> list[Issue]:
    """`gh issue list --json number,title,labels,url` の出力（JSON 文字列）を解釈する。

    各 Issue の `updatedAt`（ISO 8601 形式）は任意。ないときや null のときは None になる。
    `assignees`（`[{"login": "alice"}]` の形）も任意。ないとき、null、空のときは担当者なし。

    必須の項目がない、または形が違う Issue は読み飛ばし、標準エラーに警告を出す。
    """
    data = json.loads(text)
    issues = []
    for index, item in enumerate(data, start=1):
        try:
            issues.append(_to_issue(item))
        except (KeyError, TypeError) as e:
            print(
                f"警告: {index} 件目の Issue を読み飛ばしました ({type(e).__name__})",
                file=sys.stderr,
            )
    return issues


def _to_issue(item: dict) -> Issue:
    return Issue(
        number=item["number"],
        title=item["title"],
        labels=[label["name"] for label in item["labels"]],
        url=item["url"],
        updated_at=_parse_datetime(item.get("updatedAt")),
        assignees=[a["login"] for a in item.get("assignees") or []],
    )


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    # タイムゾーンがない値は UTC とみなす
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
