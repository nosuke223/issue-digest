import pytest
from conftest import DATA, NOW, issue_numbers_in_output

from issue_digest import main
from issue_digest.classifier import classify_issues
from issue_digest.formatter import format_digest_by_assignee
from issue_digest.loader import Issue

GROUP_BY = str(DATA / "group_by.json")
URL = "https://github.com/example/repo/issues"


def _sections(out: str) -> dict[str, list[str]]:
    """`## ` の見出しごとに、その下の空でない行を返す（`## 前回からの変化` より前だけ）。"""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in out.splitlines():
        if line == "## 前回からの変化":
            break
        if line.startswith("## "):
            current = line
            sections[current] = []
        elif current is not None and line:
            sections[current].append(line)
    return sections


def test_group_by_assignee_full_output(capsys):
    assert main(["--group-by", "assignee", GROUP_BY]) == 0
    assert capsys.readouterr().out == (
        "# Issue ダイジェスト（全 6 件）\n"
        "\n"
        "## @alice - 3件\n"
        "\n"
        f"- [example/repo#1]({URL}/1) 共同の Issue（作業中, 着手可能）\n"
        f"- [example/repo#2]({URL}/2) レビュー中（レビュー待ち）\n"
        f"- [example/repo#5]({URL}/5) 判断待ち（判断待ち）\n"
        "\n"
        "## @bob - 1件\n"
        "\n"
        f"- [example/repo#1]({URL}/1) 共同の Issue（作業中, 着手可能）\n"
        "\n"
        "## @Carol - 1件\n"
        "\n"
        f"- [example/repo#4]({URL}/4) 未分類の Issue（未分類）\n"
        "\n"
        "## 担当者なし - 2件\n"
        "\n"
        f"- [example/repo#3]({URL}/3) 担当者なしで着手可能（着手可能）\n"
        f"- [example/repo#6]({URL}/6) 担当者なしの判断待ち（判断待ち）\n"
    )


def test_group_by_assignee_counts_duplicated_login_once():
    issue = Issue(
        number=1,
        title="重複",
        labels=["agent:ready"],
        url=f"{URL}/1",
        assignees=["alice", "alice"],
    )
    out = format_digest_by_assignee(classify_issues([issue]))
    assert "## @alice - 1件" in out
    assert issue_numbers_in_output(out) == [1]


def test_group_by_assignee_without_unassigned_has_no_unassigned_heading():
    issue = Issue(number=1, title="A", labels=[], url=f"{URL}/1", assignees=["alice"])
    out = format_digest_by_assignee(classify_issues([issue]))
    assert "担当者なし" not in out


def test_group_by_assignee_empty_input(capsys):
    assert main(["--group-by", "assignee", str(DATA / "empty.json")]) == 0
    assert capsys.readouterr().out == "# Issue ダイジェスト（全 0 件）\n\nなし\n"


def test_group_by_assignee_only_filters_issues_and_category_names(capsys):
    assert main(["--group-by", "assignee", "--only", "agent:ready", GROUP_BY]) == 0
    out = capsys.readouterr().out
    assert out.startswith("# Issue ダイジェスト（全 6 件）\n")
    assert _sections(out) == {
        "## @alice - 1件": [f"- [example/repo#1]({URL}/1) 共同の Issue（着手可能）"],
        "## @bob - 1件": [f"- [example/repo#1]({URL}/1) 共同の Issue（着手可能）"],
        "## 担当者なし - 1件": [f"- [example/repo#3]({URL}/3) 担当者なしで着手可能（着手可能）"],
    }


def test_group_by_assignee_only_without_matches_prints_none(capsys):
    assert main(["--group-by", "assignee", "--only", "agent:blocked", GROUP_BY]) == 0
    assert capsys.readouterr().out == "# Issue ダイジェスト（全 6 件）\n\nなし\n"


def test_group_by_assignee_exclude(capsys):
    excludes = ["--exclude", "agent:needs-decision", "--exclude", "agent:ready"]
    assert main(["--group-by", "assignee", *excludes, GROUP_BY]) == 0
    sections = _sections(capsys.readouterr().out)
    assert list(sections) == ["## @alice - 2件", "## @bob - 1件", "## @Carol - 1件"]
    assert sections["## @bob - 1件"] == [f"- [example/repo#1]({URL}/1) 共同の Issue（作業中）"]


def test_group_by_assignee_since(capsys):
    assert main(["--group-by", "assignee", "--since", "2026-10-10", GROUP_BY]) == 0
    out = capsys.readouterr().out
    assert out.startswith("# Issue ダイジェスト（全 3 件）\n")
    assert list(_sections(out)) == ["## @alice - 1件", "## @Carol - 1件", "## 担当者なし - 1件"]
    assert sorted(issue_numbers_in_output(out)) == [2, 3, 4]


@pytest.mark.parametrize(
    ("sort", "expected"),
    [(None, [1, 2, 5]), ("updated", [1, 5, 2]), ("created", [2, 1, 5])],
)
def test_group_by_assignee_sort_within_assignee(capsys, sort, expected):
    args = ["--group-by", "assignee"] + ([] if sort is None else ["--sort", sort])
    assert main([*args, GROUP_BY]) == 0
    sections = _sections(capsys.readouterr().out)
    assert issue_numbers_in_output("\n".join(sections["## @alice - 3件"])) == expected
    # 担当者の順は変わらない
    assert list(sections) == [
        "## @alice - 3件",
        "## @bob - 1件",
        "## @Carol - 1件",
        "## 担当者なし - 2件",
    ]


def test_group_by_assignee_limit_within_assignee(capsys):
    assert main(["--group-by", "assignee", "--limit", "1", "--sort", "updated", GROUP_BY]) == 0
    sections = _sections(capsys.readouterr().out)
    assert sections["## @alice - 3件"] == [
        f"- [example/repo#1]({URL}/1) 共同の Issue（作業中, 着手可能）",
        "- ほか 2 件",
    ]
    assert sections["## @bob - 1件"] == [
        f"- [example/repo#1]({URL}/1) 共同の Issue（作業中, 着手可能）"
    ]
    assert sections["## 担当者なし - 2件"] == [
        f"- [example/repo#3]({URL}/3) 担当者なしで着手可能（着手可能）",
        "- ほか 1 件",
    ]


def test_group_by_assignee_marks_follow_category_names(capsys):
    args = ["--group-by", "assignee", "--stale", "7", "--show-assignees", "--show-labels"]
    assert main([*args, GROUP_BY], now=NOW) == 0
    sections = _sections(capsys.readouterr().out)
    assert sections["## @bob - 1件"] == [
        f"- [example/repo#1]({URL}/1) 共同の Issue（作業中, 着手可能）（22日更新なし）"
        "（担当: @bob, @alice）（ラベル: bug）"
    ]
    # 印が付かない Issue は分類の名前だけ
    assert (
        sections["## 担当者なし - 2件"][1]
        == f"- [example/repo#6]({URL}/6) 担当者なしの判断待ち（判断待ち）"
    )


def test_group_by_assignee_age_follows_other_marks(capsys):
    args = ["--group-by", "assignee", "--age", "--stale", "7", "--show-labels"]
    assert main([*args, str(DATA / "age.json")], now=NOW) == 0
    out = capsys.readouterr().out
    assert (
        "12日前に作られた Issue（着手可能）（13日更新なし）（ラベル: docs）（作成から12日）\n"
        in out
    )
    assert "半日前に作られた Issue（着手可能）（作成から0日）\n" in out
    # createdAt がない Issue には付かない
    assert "作成日時がない Issue（着手可能）\n" in out


def test_group_by_assignee_summary(capsys):
    assert main(["--group-by", "assignee", "--summary", GROUP_BY]) == 0
    out = capsys.readouterr().out
    assert out.startswith(
        "# Issue ダイジェスト（全 6 件）\n"
        "\n"
        "@alice 3 / @bob 1 / @Carol 1 / 担当者なし 2\n"
        "\n"
        "## @alice"
    )


def test_group_by_assignee_summary_ignores_only_but_follows_since(capsys):
    args = ["--group-by", "assignee", "--summary", "--only", "agent:ready"]
    assert main([*args, GROUP_BY]) == 0
    assert "\n@alice 3 / @bob 1 / @Carol 1 / 担当者なし 2\n" in capsys.readouterr().out
    assert main(["--group-by", "assignee", "--summary", "--since", "2026-10-10", GROUP_BY]) == 0
    assert "\n@alice 1 / @Carol 1 / 担当者なし 1\n" in capsys.readouterr().out


def test_group_by_assignee_hide_empty_has_no_effect(capsys):
    assert main(["--group-by", "assignee", GROUP_BY]) == 0
    without = capsys.readouterr().out
    assert main(["--group-by", "assignee", "--hide-empty", GROUP_BY]) == 0
    assert capsys.readouterr().out == without


def test_group_by_assignee_diff_section_unchanged(capsys, tmp_path):
    previous = tmp_path / "previous.json"
    assert main(["--json", "--output", str(previous), GROUP_BY]) == 0
    assert main(["--diff", str(previous), GROUP_BY]) == 0
    by_category = capsys.readouterr().out
    assert main(["--group-by", "assignee", "--diff", str(previous), GROUP_BY]) == 0
    out = capsys.readouterr().out
    assert out.endswith("\n\n## 前回からの変化\n\n変化なし\n")
    section = by_category[by_category.index("## 前回からの変化") :]
    assert out.endswith(section)


def test_group_by_assignee_uses_config_headings_and_title(capsys, tmp_path):
    config = tmp_path / "my.toml"
    config.write_text('[headings]\n"agent:ready" = "すぐ着手"\n', encoding="utf-8")
    args = ["--group-by", "assignee", "--config", str(config), "--title", "repo"]
    assert main([*args, GROUP_BY]) == 0
    out = capsys.readouterr().out
    assert out.startswith("# repo（全 6 件）\n")
    assert f"- [example/repo#1]({URL}/1) 共同の Issue（作業中, すぐ着手）" in out


def test_group_by_assignee_ignores_config_json(capsys, tmp_path):
    config = tmp_path / "my.toml"
    config.write_text("json = true\n", encoding="utf-8")
    assert main(["--group-by", "assignee", "--config", str(config), GROUP_BY]) == 0
    assert "## @alice - 3件" in capsys.readouterr().out


def _group_by_digest(capsys, args: list[str]) -> str:
    assert main(["--group-by", "assignee", *args, GROUP_BY], now=NOW) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    return captured.out


def test_group_by_max_chars_exact_length_keeps_output(capsys):
    full = _group_by_digest(capsys, [])
    assert _group_by_digest(capsys, ["--max-chars", str(len(full))]) == full


def test_group_by_max_chars_trims_unassigned_from_end(capsys):
    full = _group_by_digest(capsys, [])
    out = _group_by_digest(capsys, ["--max-chars", str(len(full) - 1)])
    assert len(out) <= len(full) - 1
    assert _sections(out)["## 担当者なし - 2件"] == [
        f"- [example/repo#3]({URL}/3) 担当者なしで着手可能（着手可能）",
        "- ほか 1 件",
    ]
    assert issue_numbers_in_output(out) == [1, 2, 5, 1, 4, 3]


def test_group_by_max_chars_moves_to_previous_assignee(capsys):
    full = _group_by_digest(capsys, [])
    # 担当者なしの Issue の行をすべて削った出力
    expected = full.replace(
        f"- [example/repo#3]({URL}/3) 担当者なしで着手可能（着手可能）\n"
        f"- [example/repo#6]({URL}/6) 担当者なしの判断待ち（判断待ち）\n",
        "- ほか 2 件\n",
    )
    assert _group_by_digest(capsys, ["--max-chars", str(len(expected))]) == expected
    out = _group_by_digest(capsys, ["--max-chars", str(len(expected) - 1)])
    assert len(out) <= len(expected) - 1
    sections = _sections(out)
    assert sections["## @Carol - 1件"] == ["- ほか 1 件"]
    assert sections["## 担当者なし - 2件"] == ["- ほか 2 件"]
    assert issue_numbers_in_output(out) == [1, 2, 5, 1]


def test_group_by_max_chars_with_limit_merges_omitted_count(capsys):
    limited = _group_by_digest(capsys, ["--limit", "1"])
    out = _group_by_digest(capsys, ["--limit", "1", "--max-chars", str(len(limited) - 1)])
    assert len(out) <= len(limited) - 1
    sections = _sections(out)
    assert sections["## 担当者なし - 2件"] == ["- ほか 2 件"]
    # 削っていない担当者は --limit の分だけ
    assert sections["## @alice - 3件"] == [
        f"- [example/repo#1]({URL}/1) 共同の Issue（作業中, 着手可能）",
        "- ほか 2 件",
    ]


def test_group_by_max_chars_counts_marks(capsys):
    marks = ["--stale", "0", "--show-assignees", "--show-labels", "--age"]
    marked = _group_by_digest(capsys, marks)
    assert _group_by_digest(capsys, [*marks, "--max-chars", str(len(marked))]) == marked
    out = _group_by_digest(capsys, [*marks, "--max-chars", str(len(marked) - 1)])
    assert len(out) <= len(marked) - 1
    assert issue_numbers_in_output(out) == [1, 2, 5, 1, 4, 3]


def test_group_by_max_chars_cannot_fit_warns_and_keeps_headings(capsys, tmp_path):
    previous = tmp_path / "previous.json"
    assert main(["--json", "--output", str(previous), GROUP_BY]) == 0
    args = ["--group-by", "assignee", "--summary", "--diff", str(previous), "--max-chars", "1"]
    assert main([*args, GROUP_BY]) == 0
    captured = capsys.readouterr()
    assert issue_numbers_in_output(captured.out) == []
    assert captured.out.startswith(
        "# Issue ダイジェスト（全 6 件）\n\n@alice 3 / @bob 1 / @Carol 1 / 担当者なし 2\n"
    )
    assert _sections(captured.out) == {
        "## @alice - 3件": ["- ほか 3 件"],
        "## @bob - 1件": ["- ほか 1 件"],
        "## @Carol - 1件": ["- ほか 1 件"],
        "## 担当者なし - 2件": ["- ほか 2 件"],
    }
    assert captured.out.endswith("\n\n## 前回からの変化\n\n変化なし\n")
    assert captured.err == (
        "警告: Issue の行をすべて削っても --max-chars の 1 文字に収まりません"
        f"（{len(captured.out)} 文字）\n"
    )


@pytest.mark.parametrize("option", ["--json", "--csv"])
def test_group_by_max_chars_with_json_or_csv_is_error(capsys, option):
    assert main(["--group-by", "assignee", "--max-chars", "2000", option, GROUP_BY]) == 2
    captured = capsys.readouterr()
    assert captured.err.startswith("エラー: ")
    assert captured.out == ""


def test_without_group_by_unchanged(capsys):
    assert main([GROUP_BY]) == 0
    out = capsys.readouterr().out
    assert "## 判断待ち (agent:needs-decision) - 2件" in out
    assert "@alice" not in out


@pytest.mark.parametrize("value", ["label", "assignees", "Assignee", ""])
def test_group_by_invalid_value(capsys, value):
    assert main(["--group-by", value, GROUP_BY]) == 2
    captured = capsys.readouterr()
    assert captured.err == f"エラー: --group-by に指定できる値は assignee です: {value}\n"
    assert captured.out == ""


@pytest.mark.parametrize("option", ["--json", "--csv"])
def test_group_by_with_json_or_csv_is_error(capsys, option):
    assert main(["--group-by", "assignee", option, GROUP_BY]) == 2
    captured = capsys.readouterr()
    assert captured.err == (
        f"エラー: --group-by と {option} は同時に指定できません"
        "（--group-by は Markdown だけで使えます）\n"
    )
    assert captured.out == ""


def test_group_by_without_value_shows_usage(capsys):
    assert main([GROUP_BY, "--group-by"]) == 2
    captured = capsys.readouterr()
    assert "使い方" in captured.err
    assert captured.out == ""


def test_usage_mentions_group_by(capsys):
    assert main(["--help"]) == 0
    assert "--group-by assignee" in capsys.readouterr().out
