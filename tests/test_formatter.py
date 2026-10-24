import json
from datetime import UTC, datetime

from conftest import make_issue

from issue_digest.classifier import classify_issues
from issue_digest.formatter import format_digest, format_json
from issue_digest.loader import Issue


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


def test_format_digest_only_keeps_category_order_and_ignores_duplicates():
    issues = [
        make_issue(1, "A", ["agent:ready"]),
        make_issue(2, "B", ["agent:blocked"]),
    ]
    classified = classify_issues(issues)
    expected = format_digest(classified, only=["agent:blocked", "agent:ready"])
    assert format_digest(classified, only=["agent:ready", "agent:blocked"]) == expected
    assert (
        format_digest(classified, only=["agent:ready", "agent:ready", "agent:blocked"]) == expected
    )
    headings = [line for line in expected.splitlines() if line.startswith("## ")]
    assert headings == [
        "## 中断 (agent:blocked) - 1件",
        "## 着手可能 (agent:ready) - 1件",
    ]


def test_format_json_only_keeps_category_order_and_ignores_duplicates():
    issues = [
        make_issue(1, "A", ["agent:ready"]),
        make_issue(2, "B", ["agent:blocked"]),
    ]
    out = format_json(classify_issues(issues), only=["agent:ready", "agent:ready", "agent:blocked"])
    labels = [c["label"] for c in json.loads(out)["categories"]]
    assert labels == ["agent:blocked", "agent:ready"]


def test_format_digest_show_assignees_appends_in_input_order():
    issue = Issue(1, "A", ["agent:ready"], "u", assignees=["bob", "alice"])
    out = format_digest(classify_issues([issue]), show_assignees=True)
    assert "- [#1](u) A（担当: @bob, @alice）\n" in out


def test_format_digest_show_assignees_skips_issue_without_assignees():
    out = format_digest(classify_issues([make_issue(1, "A", ["agent:ready"])]), show_assignees=True)
    assert "- [#1](https://github.com/example/repo/issues/1) A\n" in out
    assert "担当" not in out


def test_format_digest_assignees_hidden_by_default():
    issue = Issue(1, "A", ["agent:ready"], "u", assignees=["alice"])
    assert "担当" not in format_digest(classify_issues([issue]))


def test_format_digest_stale_mark_comes_before_assignees():
    now = datetime(2026, 10, 23, tzinfo=UTC)
    updated = datetime(2026, 10, 10, tzinfo=UTC)
    issue = Issue(1, "A", ["agent:ready"], "u", updated_at=updated, assignees=["alice"])
    out = format_digest(classify_issues([issue]), stale_days=7, now=now, show_assignees=True)
    assert "- [#1](u) A（13日更新なし）（担当: @alice）\n" in out


def test_format_json_show_assignees_adds_login_list():
    issues = [
        Issue(1, "A", ["agent:ready"], "u", assignees=["alice", "bob"]),
        make_issue(2, "B", ["agent:ready"]),
    ]
    body = json.loads(format_json(classify_issues(issues), show_assignees=True))
    ready = next(c for c in body["categories"] if c["label"] == "agent:ready")
    assert [i["assignees"] for i in ready["issues"]] == [["alice", "bob"], []]


def test_format_json_without_show_assignees_has_no_assignees():
    issue = Issue(1, "A", ["agent:ready"], "u", assignees=["alice"])
    out = format_json(classify_issues([issue]))
    assert '"assignees":' not in out


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


def test_format_digest_escapes_markdown_in_title():
    issue = make_issue(1, "[WIP] a](x) *b*", ["agent:ready"])
    out = format_digest(classify_issues([issue]))
    assert "- [#1](https://github.com/example/repo/issues/1) \\[WIP\\] a\\](x) \\*b\\*\n" in out


def test_format_digest_escapes_all_special_characters():
    issue = make_issue(1, "\\ ` * _ [ ] < >", ["agent:ready"])
    out = format_digest(classify_issues([issue]))
    assert " \\\\ \\` \\* \\_ \\[ \\] \\< \\>\n" in out


def test_format_json_keeps_title_unescaped():
    issue = make_issue(1, "[WIP] a](x) *b*", ["agent:ready"])
    body = json.loads(format_json(classify_issues([issue])))
    ready = next(c for c in body["categories"] if c["label"] == "agent:ready")
    assert ready["issues"][0]["title"] == "[WIP] a](x) *b*"


def test_format_digest_keeps_title_of_40_characters():
    title = "あ" * 40
    out = format_digest(classify_issues([make_issue(1, title, ["agent:ready"])]))
    assert f" {title}\n" in out


def test_format_digest_shortens_title_over_40_characters():
    out = format_digest(classify_issues([make_issue(1, "あ" * 41, ["agent:ready"])]))
    assert f" {'あ' * 40}…\n" in out
    assert "あ" * 41 not in out


def test_format_digest_escapes_after_shortening():
    # 40文字目までに `*` が入るときだけエスケープされ、切り捨てられた `*` は残らない
    title = "*" + "a" * 38 + "*" + "*b"
    out = format_digest(classify_issues([make_issue(1, title, ["agent:ready"])]))
    assert f" \\*{'a' * 38}\\*…\n" in out


def test_format_json_keeps_long_title():
    title = "あ" * 41
    body = json.loads(format_json(classify_issues([make_issue(1, title, ["agent:ready"])])))
    ready = next(c for c in body["categories"] if c["label"] == "agent:ready")
    assert ready["issues"][0]["title"] == title


def test_format_digest_total_zero():
    out = format_digest(classify_issues([]))
    assert out.splitlines()[0] == "# Issue ダイジェスト（全 0 件）"
