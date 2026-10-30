import json

from conftest import DATA, NOW

from issue_digest import USAGE, main
from issue_digest.loader import load_issues

AUTHOR = str(DATA / "author.json")


def test_load_issues_reads_author_login():
    by_number = {i.number: i for i in load_issues(AUTHOR)}
    assert by_number[1].author == "bob"
    assert by_number[2].author == "app/dependabot"
    assert by_number[3].author is None
    assert by_number[4].author is None


def test_main_show_author_appends_to_line_end(capsys):
    assert main(["--show-author", AUTHOR]) == 0
    out = capsys.readouterr().out
    assert "作成者がある Issue（作成者: @bob）\n" in out
    assert "ボットが作った Issue（作成者: @app/dependabot）\n" in out
    assert "author が null の Issue\n" in out
    assert "author キーがない Issue\n" in out


def test_main_show_author_after_assignees_before_other_marks(capsys):
    args = [
        "--show-author",
        "--show-milestone",
        "--age",
        "--show-labels",
        "--show-assignees",
        "--stale",
        "7",
        AUTHOR,
    ]
    assert main(args, now=NOW) == 0
    line = next(x for x in capsys.readouterr().out.splitlines() if "作成者がある Issue" in x)
    assert line.endswith(
        "（13日更新なし）（担当: @alice）（作成者: @bob）（ラベル: docs）"
        "（作成から22日）（マイルストーン: v1.0）"
    )


def test_main_without_show_author_unchanged(capsys):
    assert main([AUTHOR]) == 0
    assert "（作成者:" not in capsys.readouterr().out


def test_main_json_show_author(capsys):
    assert main(["--json", "--show-author", AUTHOR]) == 0
    body = json.loads(capsys.readouterr().out)
    by_number = {i["number"]: i for c in body["categories"] for i in c["issues"]}
    assert by_number[1]["author"] == "bob"
    assert by_number[2]["author"] == "app/dependabot"
    assert by_number[3]["author"] is None
    assert by_number[4]["author"] is None


def test_main_json_without_show_author_has_no_author(capsys):
    assert main(["--json", AUTHOR]) == 0
    assert '"author"' not in capsys.readouterr().out


def test_main_csv_ignores_show_author(capsys):
    assert main(["--csv", AUTHOR]) == 0
    expected = capsys.readouterr().out
    assert main(["--csv", "--show-author", AUTHOR]) == 0
    assert capsys.readouterr().out == expected


def test_main_group_by_assignee_with_show_author(capsys):
    args = ["--group-by", "assignee", "--show-assignees", "--show-author", "--show-labels", AUTHOR]
    assert main(args) == 0
    out = capsys.readouterr().out
    assert "作成者がある Issue（着手可能）（担当: @alice）（作成者: @bob）（ラベル: docs）\n" in out
    assert "ボットが作った Issue（着手可能）（作成者: @app/dependabot）\n" in out


def test_main_max_chars_counts_author_mark(capsys):
    assert main(["--show-author", AUTHOR]) == 0
    full = capsys.readouterr().out
    assert main(["--show-author", "--max-chars", str(len(full) - 1), AUTHOR]) == 0
    out = capsys.readouterr().out
    assert len(out) <= len(full) - 1
    assert "- ほか " in out


def test_main_diff_section_has_no_author_mark(capsys, tmp_path):
    previous = tmp_path / "last.json"
    previous.write_text(
        json.dumps({"total": 0, "categories": []}),
        encoding="utf-8",
    )
    assert main(["--show-author", "--diff", str(previous), AUTHOR]) == 0
    out = capsys.readouterr().out
    diff_section = out[out.index("## 前回からの変化") :]
    assert "（作成者:" not in diff_section
    assert "（作成者: @bob）" in out


def test_main_usage_mentions_show_author():
    assert "--show-author" in USAGE
