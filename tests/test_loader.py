from datetime import UTC, datetime
from pathlib import Path

from issue_digest.loader import Issue, load_issues, parse_issues

DATA = Path(__file__).parent / "data"


def test_load_issues_extracts_label_names():
    issues = load_issues(DATA / "issues.json")
    assert issues[0] == Issue(
        number=1,
        title="サンプルの Issue A",
        labels=["bug", "agent:ready"],
        url="https://github.com/example/repo/issues/1",
    )


def test_load_issues_accepts_issue_without_labels():
    issues = load_issues(DATA / "issues.json")
    assert issues[1].labels == []


def test_load_issues_reads_updated_at():
    issues = load_issues(DATA / "stale.json")
    assert issues[0].updated_at == datetime(2026, 10, 10, tzinfo=UTC)


def test_load_issues_updated_at_is_optional():
    assert load_issues(DATA / "issues.json")[0].updated_at is None
    assert load_issues(DATA / "stale.json")[3].updated_at is None


def test_parse_issues_accepts_null_updated_at():
    text = '[{"number": 1, "title": "t", "labels": [], "url": "u", "updatedAt": null}]'
    assert parse_issues(text)[0].updated_at is None


def test_load_issues_reads_assignees_in_order():
    assert load_issues(DATA / "assignees.json")[0].assignees == ["bob", "alice"]


def test_load_issues_assignees_missing_empty_or_null_means_none():
    issues = load_issues(DATA / "assignees.json")
    assert [i.assignees for i in issues[1:]] == [[], [], []]
    assert load_issues(DATA / "issues.json")[0].assignees == []


def test_load_issues_returns_empty_list_for_empty_file():
    assert load_issues(DATA / "empty.json") == []
