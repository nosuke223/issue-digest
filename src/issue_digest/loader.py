import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    labels: list[str]
    url: str


def load_issues(path: str | Path) -> list[Issue]:
    """`gh issue list --json number,title,labels,url` の出力ファイルを読み込む。"""
    with open(path, encoding="utf-8") as f:
        return parse_issues(f.read())


def parse_issues(text: str) -> list[Issue]:
    """`gh issue list --json number,title,labels,url` の出力（JSON 文字列）を解釈する。"""
    data = json.loads(text)
    return [
        Issue(
            number=item["number"],
            title=item["title"],
            labels=[label["name"] for label in item["labels"]],
            url=item["url"],
        )
        for item in data
    ]
