import csv
import io

import pytest
from conftest import DATA, json_out

from issue_digest import main
from issue_digest.loader import Issue, merge_issues, repository_of

REPO_A = str(DATA / "multi_repo_a.json")
REPO_B = str(DATA / "multi_repo_b.json")

A1 = "- [alpha/tools#1](https://github.com/alpha/tools/issues/1) alpha の着手可能"
A2 = "- [alpha/tools#2](https://github.com/alpha/tools/issues/2) alpha のレビュー"
B1 = "- [Beta/app#1](https://github.com/Beta/app/issues/1) Beta の着手可能"
B5 = "- [Beta/app#5](https://github.com/Beta/app/pull/5) Beta の判断待ち"
NO_REPO3 = "- [#3](https://example.com/tickets/3) リポジトリ名のない URL"

EXPECTED_MARKDOWN = (
    "# Issue ダイジェスト（全 5 件）\n"
    "\n## 判断待ち (agent:needs-decision) - 1件\n\n"
    f"{B5}\n"
    "\n## 中断 (agent:blocked) - 0件\n\nなし\n"
    "\n## レビュー待ち (agent:review) - 1件\n\n"
    f"{A2}\n"
    "\n## 作業中 (agent:working) - 0件\n\nなし\n"
    "\n## 着手可能 (agent:ready) - 3件\n\n"
    f"{A1}\n{B1}\n{NO_REPO3}\n"
    "\n## 未分類 - 0件\n\nなし\n"
)


def test_main_merges_multiple_inputs(capsys):
    # 別のリポジトリの同じ番号（#1）はどちらも出る。URL が同じ #2 は最初の入力のものだけを使う
    assert main([REPO_A, REPO_B]) == 0
    assert capsys.readouterr().out == EXPECTED_MARKDOWN


def test_main_input_order_decides_duplicates(capsys):
    # 後に指定した入力の重複は捨てる（b を先にすると #2 は作業中になる）
    assert main([REPO_B, REPO_A]) == 0
    out = capsys.readouterr().out
    assert "## 作業中 (agent:working) - 1件\n\n- [Alpha/Tools#2]" in out
    assert "## レビュー待ち (agent:review) - 0件\n\nなし\n" in out
    assert "（全 5 件）" in out


def test_main_stdin_can_be_mixed(capsys, monkeypatch):
    with open(REPO_B, encoding="utf-8") as f:
        monkeypatch.setattr("sys.stdin", io.StringIO(f.read()))
    assert main([REPO_A, "-"]) == 0
    assert capsys.readouterr().out == EXPECTED_MARKDOWN


def test_main_stdin_twice_is_error(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("[]"))
    assert main(["-", REPO_A, "-"]) == 2
    captured = capsys.readouterr()
    assert captured.err == "エラー: -（標準入力）は1回だけ指定できます\n"
    assert captured.out == ""


def test_main_broken_second_input_is_error(capsys, tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    assert main([REPO_A, str(broken)]) == 1
    captured = capsys.readouterr()
    assert captured.err == f"エラー: ファイルを読み込めません: {broken} (JSONDecodeError)\n"
    assert captured.out == ""


def test_main_duplicate_within_one_input_counted_once(capsys, tmp_path):
    assert main([REPO_A, REPO_A]) == 0
    out = capsys.readouterr().out
    assert out.startswith("# Issue ダイジェスト（全 3 件）\n")
    assert out.count(A1) == 1


def test_main_summary_counts_without_duplicates(capsys):
    assert main(["--summary", REPO_A, REPO_B]) == 0
    assert capsys.readouterr().out.startswith(
        "# Issue ダイジェスト（全 5 件）\n\n"
        "判断待ち 1 / 中断 0 / レビュー待ち 1 / 作業中 0 / 着手可能 3 / 未分類 0\n"
    )


def test_main_json_has_repository(capsys):
    assert main(["--json", REPO_A, REPO_B]) == 0
    data = json_out(capsys)
    assert data["total"] == 5
    ready = next(c for c in data["categories"] if c["label"] == "agent:ready")
    assert [(i["repository"], i["number"]) for i in ready["issues"]] == [
        ("alpha/tools", 1),
        ("Beta/app", 1),
        (None, 3),
    ]
    assert list(ready["issues"][0]) == ["number", "title", "url", "repository"]


def test_main_csv_has_repository_column(capsys):
    assert main(["--csv", "--only", "agent:ready", REPO_A, REPO_B]) == 0
    rows = list(csv.reader(io.StringIO(capsys.readouterr().out, newline="")))
    assert rows[0] == ["label", "number", "title", "url", "repository"]
    assert [(r[1], r[4]) for r in rows[1:]] == [("1", "alpha/tools"), ("1", "Beta/app"), ("3", "")]


def test_main_sort_updated_ties_use_repository_order(capsys):
    assert main(["--sort", "updated", "--only", "agent:ready", REPO_B, REPO_A]) == 0
    out = capsys.readouterr().out
    assert f"{A1}\n{B1}\n{NO_REPO3}\n" in out
    assert main(["--sort", "updated", "--reverse", "--only", "agent:ready", REPO_A, REPO_B]) == 0
    assert f"{NO_REPO3}\n{B1}\n{A1}\n" in capsys.readouterr().out


def test_main_group_by_assignee_with_multiple_repositories(capsys):
    assert main(["--group-by", "assignee", REPO_A, REPO_B]) == 0
    assert capsys.readouterr().out == (
        "# Issue ダイジェスト（全 5 件）\n"
        "\n## @alice - 2件\n\n"
        f"{A1}（着手可能）\n{B1}（着手可能）\n"
        "\n## 担当者なし - 3件\n\n"
        f"{A2}（レビュー待ち）\n{B5}（判断待ち）\n{NO_REPO3}（着手可能）\n"
    )


def test_main_max_chars_counts_repository(capsys):
    assert main([REPO_A, REPO_B]) == 0
    full = capsys.readouterr().out
    assert main(["--max-chars", str(len(full) - 1), REPO_A, REPO_B]) == 0
    out = capsys.readouterr().out
    assert len(out) <= len(full) - 1
    assert f"{A1}\n{B1}\n- ほか 1 件\n" in out
    assert NO_REPO3 not in out


@pytest.fixture
def previous_b(tmp_path, capsys):
    previous = tmp_path / "previous.json"
    assert main(["--json", "--output", str(previous), REPO_B]) == 0
    capsys.readouterr()
    return str(previous)


def test_main_diff_matches_by_url(capsys, previous_b):
    # 前回の Beta/app#1 と今回の alpha/tools#1 を取り違えない。
    # #2 は URL の大文字と小文字が違っても同じ Issue
    assert main(["--diff", previous_b, REPO_A]) == 0
    assert capsys.readouterr().out.endswith(
        "\n## 前回からの変化\n\n"
        "### 新しい Issue - 2件\n\n"
        f"{A1}\n{NO_REPO3}\n\n"
        "### なくなった Issue - 2件\n\n"
        f"{B1}\n{B5}\n\n"
        "### 分類が変わった Issue - 1件\n\n"
        f"{A2}: 作業中 → レビュー待ち\n"
    )


def test_main_diff_json_has_repository(capsys, previous_b):
    assert main(["--json", "--diff", previous_b, REPO_A]) == 0
    diff = json_out(capsys)["diff"]
    assert [(i["repository"], i["number"]) for i in diff["added"]] == [
        ("alpha/tools", 1),
        (None, 3),
    ]
    assert [(i["repository"], i["number"]) for i in diff["removed"]] == [
        ("Beta/app", 1),
        ("Beta/app", 5),
    ]
    assert [(i["repository"], i["number"], i["from"], i["to"]) for i in diff["moved"]] == [
        ("alpha/tools", 2, ["agent:working"], ["agent:review"])
    ]


def test_main_diff_previous_of_multiple_inputs_in_other_order(capsys, tmp_path):
    previous = tmp_path / "previous.json"
    assert main(["--json", "--output", str(previous), REPO_A, REPO_B]) == 0
    assert main(["--diff", str(previous), REPO_B, REPO_A]) == 0
    # b を先に読むと #2 は b のもの（作業中）になるので、分類が変わった Issue としてだけ出る
    assert capsys.readouterr().out.endswith(
        "### 新しい Issue - 0件\n\nなし\n\n"
        "### なくなった Issue - 0件\n\nなし\n\n"
        "### 分類が変わった Issue - 1件\n\n"
        "- [Alpha/Tools#2](https://github.com/Alpha/Tools/issues/2) a と同じ Issue（大文字の URL）"
        ": レビュー待ち → 作業中\n"
    )


def test_main_diff_with_same_order_has_no_change(capsys, tmp_path):
    previous = tmp_path / "previous.json"
    assert main(["--json", "--output", str(previous), REPO_A, REPO_B]) == 0
    assert main(["--diff", str(previous), REPO_A, REPO_B]) == 0
    assert capsys.readouterr().out.endswith("\n## 前回からの変化\n\n変化なし\n")


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/owner/repo/issues/12", "owner/repo"),
        ("https://github.com/owner/repo/pull/12", "owner/repo"),
        ("https://ghe.example.com/Org/my.repo/issues/3", "Org/my.repo"),
        ("https://github.com/owner/repo/issues/12#issuecomment-1", "owner/repo"),
        ("https://github.com/owner/repo/issues", None),
        ("https://github.com/owner/repo/discussions/12", None),
        ("https://github.com/repo/issues/12", None),
        ("u", None),
        ("", None),
    ],
)
def test_repository_of(url, expected):
    assert repository_of(url) == expected


def test_merge_issues_keeps_first_by_url_ignoring_case():
    first = Issue(1, "first", [], "https://github.com/o/r/issues/1")
    second = Issue(1, "second", [], "https://github.com/O/R/issues/1")
    other = Issue(1, "other", [], "https://github.com/o/other/issues/1")
    assert merge_issues([[first], [second, other]]) == [first, other]
