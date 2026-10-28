import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from issue_digest.loader import Issue

DATA = Path(__file__).parent / "data"
NOW = datetime(2026, 10, 23, 12, 0, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def in_tmp_dir(tmp_path, monkeypatch):
    """カレントディレクトリを空の一時ディレクトリにして、実際のリポジトリの設定に依存しない。"""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def make_issue(number: int, title: str | None = None, labels: list[str] | None = None) -> Issue:
    return Issue(
        number=number,
        title=title if title is not None else f"Issue {number}",
        labels=labels if labels is not None else [],
        url=f"https://github.com/example/repo/issues/{number}",
    )


def issue_numbers_in_output(out: str) -> list[int]:
    """Markdown の Issue の行（`- [owner/repo#12](url)` または `- [#12](url)`）の番号を返す。"""
    numbers = []
    for line in out.splitlines():
        match = re.match(r"- \[[^\]#]*#(\d+)\]\(", line)
        if match:
            numbers.append(int(match[1]))
    return numbers


def json_out(capsys) -> dict:
    return json.loads(capsys.readouterr().out)
