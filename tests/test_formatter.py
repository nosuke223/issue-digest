from issue_digest.classifier import classify_issues
from issue_digest.formatter import format_digest
from issue_digest.loader import Issue


def make_issue(number: int, title: str, labels: list[str]) -> Issue:
    return Issue(
        number=number,
        title=title,
        labels=labels,
        url=f"https://github.com/example/repo/issues/{number}",
    )


def test_format_digest_lists_issues_and_none():
    issues = [make_issue(5, "CLI を作る", ["agent:needs-decision"])]
    out = format_digest(classify_issues(issues))
    assert out.startswith(
        "# Issue ダイジェスト\n"
        "\n"
        "## 判断待ち (agent:needs-decision) - 1件\n"
        "\n"
        "- #5 CLI を作る\n"
        "\n"
        "## 中断 (agent:blocked) - 0件\n"
        "\n"
        "なし\n"
    )


def test_format_digest_heading_order_and_unclassified():
    out = format_digest(classify_issues([]))
    headings = [line for line in out.splitlines() if line.startswith("## ")]
    assert headings == [
        "## 判断待ち (agent:needs-decision) - 0件",
        "## 中断 (agent:blocked) - 0件",
        "## レビュー待ち (agent:review) - 0件",
        "## 作業中 (agent:working) - 0件",
        "## 着手可能 (agent:ready) - 0件",
        "## 未分類 - 0件",
    ]
    assert out.endswith("なし\n")


def test_format_digest_issue_in_multiple_categories():
    issues = [make_issue(1, "両方", ["agent:review", "agent:working"])]
    out = format_digest(classify_issues(issues))
    assert out.count("- #1 両方") == 2
