from pathlib import Path

from issue_digest.loader import Issue, load_issues

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


def test_load_issues_returns_empty_list_for_empty_file():
    assert load_issues(DATA / "empty.json") == []
