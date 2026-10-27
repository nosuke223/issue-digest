import json

from conftest import DATA, NOW

from issue_digest import main
from issue_digest.loader import load_issues

MILESTONE = str(DATA / "milestone.json")


def test_load_issues_reads_milestone_title():
    by_number = {i.number: i for i in load_issues(MILESTONE)}
    assert by_number[1].milestone == "v1.0"
    assert by_number[2].milestone is None
    assert by_number[3].milestone is None


def test_main_show_milestone_appends_to_line_end(capsys):
    assert main(["--show-milestone", MILESTONE]) == 0
    out = capsys.readouterr().out
    assert "マイルストーンがある Issue（マイルストーン: v1.0）\n" in out
    assert "milestone が null の Issue\n" in out
    assert "milestone キーがない Issue\n" in out


def test_main_show_milestone_after_other_marks(capsys):
    args = [
        "--show-milestone",
        "--age",
        "--show-labels",
        "--show-assignees",
        "--stale",
        "7",
        MILESTONE,
    ]
    assert main(args, now=NOW) == 0
    out = capsys.readouterr().out
    line = next(line for line in out.splitlines() if "マイルストーンがある Issue" in line)
    assert line.endswith("（13日更新なし）（担当: @alice）（作成から22日）（マイルストーン: v1.0）")


def test_main_without_show_milestone_unchanged(capsys):
    assert main([MILESTONE]) == 0
    assert "（マイルストーン:" not in capsys.readouterr().out


def test_main_json_show_milestone(capsys):
    assert main(["--json", "--show-milestone", MILESTONE]) == 0
    body = json.loads(capsys.readouterr().out)
    by_number = {i["number"]: i for c in body["categories"] for i in c["issues"]}
    assert by_number[1]["milestone"] == "v1.0"
    assert by_number[2]["milestone"] is None
    assert by_number[3]["milestone"] is None


def test_main_json_without_show_milestone_has_no_milestone(capsys):
    assert main(["--json", MILESTONE]) == 0
    assert '"milestone"' not in capsys.readouterr().out


def test_main_csv_ignores_show_milestone(capsys):
    assert main(["--csv", MILESTONE]) == 0
    expected = capsys.readouterr().out
    assert main(["--csv", "--show-milestone", MILESTONE]) == 0
    assert capsys.readouterr().out == expected


def test_main_group_by_assignee_show_milestone(capsys):
    assert main(["--group-by", "assignee", "--show-milestone", MILESTONE]) == 0
    out = capsys.readouterr().out
    assert "マイルストーンがある Issue（着手可能）（マイルストーン: v1.0）\n" in out


def test_main_diff_section_has_no_milestone_mark(capsys, tmp_path):
    previous = tmp_path / "previous.json"
    previous.write_text(json.dumps({"total": 0, "categories": []}), encoding="utf-8")
    assert main(["--show-milestone", "--diff", str(previous), MILESTONE]) == 0
    out = capsys.readouterr().out
    diff_section = out.split("## 前回からの変化", 1)[1]
    assert "マイルストーンがある Issue" in diff_section
    assert "マイルストーン:" not in diff_section


def test_main_json_with_display_options_works_as_previous_json(capsys, tmp_path):
    previous = tmp_path / "previous.json"
    args = ["--json", "--sort", "created", "--reverse", "--summary", "--age", "--show-milestone"]
    assert main([*args, "--output", str(previous), MILESTONE]) == 0
    capsys.readouterr()
    assert main(["--diff", str(previous), MILESTONE]) == 0
    assert capsys.readouterr().out.endswith("## 前回からの変化\n\n変化なし\n")


def test_main_usage_mentions_show_milestone(capsys):
    assert main(["--help"]) == 0
    assert "--show-milestone" in capsys.readouterr().out
