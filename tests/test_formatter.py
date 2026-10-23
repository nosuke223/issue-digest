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
        "# Issue ダイジェスト（全 1 件）\n"
        "\n"
        "## 判断待ち (agent:needs-decision) - 1件\n"
        "\n"
        "- [#5](https://github.com/example/repo/issues/5) CLI を作る\n"
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
    assert out.count("- [#1](https://github.com/example/repo/issues/1) 両方") == 2
    assert out.startswith("# Issue ダイジェスト（全 1 件）\n")


def test_format_digest_total_counts_each_issue_once():
    issues = [
        make_issue(1, "両方", ["agent:review", "agent:working"]),
        make_issue(2, "ready", ["agent:ready"]),
        make_issue(3, "ラベルなし", []),
    ]
    out = format_digest(classify_issues(issues))
    assert out.splitlines()[0] == "# Issue ダイジェスト（全 3 件）"


def test_format_digest_hide_empty_omits_empty_categories():
    issues = [make_issue(5, "CLI を作る", ["agent:needs-decision"])]
    out = format_digest(classify_issues(issues), hide_empty=True)
    assert out == (
        "# Issue ダイジェスト（全 1 件）\n"
        "\n"
        "## 判断待ち (agent:needs-decision) - 1件\n"
        "\n"
        "- [#5](https://github.com/example/repo/issues/5) CLI を作る\n"
    )


def test_format_digest_hide_empty_all_empty():
    out = format_digest(classify_issues([]), hide_empty=True)
    assert out == "# Issue ダイジェスト（全 0 件）\n"


def test_format_digest_default_shows_empty_categories():
    classified = classify_issues([make_issue(1, "A", ["agent:ready"])])
    assert format_digest(classified) == format_digest(classified, hide_empty=False)
    assert "なし" in format_digest(classified)


def test_format_digest_only_keeps_total_of_all_issues():
    issues = [
        make_issue(1, "A", ["agent:ready"]),
        make_issue(2, "B", ["agent:review"]),
    ]
    out = format_digest(classify_issues(issues), only=["agent:review"])
    assert out == (
        "# Issue ダイジェスト（全 2 件）\n"
        "\n"
        "## レビュー待ち (agent:review) - 1件\n"
        "\n"
        "- [#2](https://github.com/example/repo/issues/2) B\n"
    )


SUMMARY_LINE = "判断待ち 1 / 中断 0 / レビュー待ち 2 / 作業中 0 / 着手可能 3 / 未分類 1"


def _summary_issues():
    return [
        make_issue(1, "A", ["agent:needs-decision"]),
        make_issue(2, "B", ["agent:review"]),
        make_issue(3, "C", ["agent:review"]),
        make_issue(4, "D", ["agent:ready"]),
        make_issue(5, "E", ["agent:ready"]),
        make_issue(6, "F", ["agent:ready"]),
        make_issue(7, "G", []),
    ]


def test_format_digest_summary_line_after_total():
    out = format_digest(classify_issues(_summary_issues()), summary=True)
    assert out.startswith(f"# Issue ダイジェスト（全 7 件）\n\n{SUMMARY_LINE}\n\n## 判断待ち")


def test_format_digest_summary_ignores_only_and_hide_empty():
    out = format_digest(
        classify_issues(_summary_issues()),
        hide_empty=True,
        only=["agent:review"],
        summary=True,
    )
    assert out.startswith(f"# Issue ダイジェスト（全 7 件）\n\n{SUMMARY_LINE}\n\n## レビュー待ち")
    assert "## 判断待ち" not in out


def test_format_digest_without_summary_unchanged():
    classified = classify_issues(_summary_issues())
    assert format_digest(classified) == format_digest(classified, summary=False)
    assert SUMMARY_LINE not in format_digest(classified)


def test_format_digest_total_zero():
    out = format_digest(classify_issues([]))
    assert out.splitlines()[0] == "# Issue ダイジェスト（全 0 件）"
