import json
from datetime import UTC, datetime
from pathlib import Path

from issue_digest.loader import Issue

DATA = Path(__file__).parent / "data"
NOW = datetime(2026, 10, 23, 12, 0, 0, tzinfo=UTC)


def make_issue(number: int, title: str | None = None, labels: list[str] | None = None) -> Issue:
    return Issue(
        number=number,
        title=title if title is not None else f"Issue {number}",
        labels=labels if labels is not None else [],
        url=f"https://github.com/example/repo/issues/{number}",
    )


def issue_numbers_in_output(out: str) -> list[int]:
    lines = [line for line in out.splitlines() if line.startswith("- [#")]
    return [int(line.removeprefix("- [#").split("]")[0]) for line in lines]


def json_out(capsys) -> dict:
    return json.loads(capsys.readouterr().out)
