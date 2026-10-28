import pytest
from conftest import DATA, issue_numbers_in_output, json_out

from issue_digest import main

ESCAPE_MARKS = str(DATA / "escape_marks.json")

MARK_OPTIONS = ["--show-labels", "--show-milestone"]
GROUP_BY_OPTIONS = [[], ["--group-by", "assignee"]]


def _line_of(out: str, number: int) -> str:
    prefix = f"- [example/repo#{number}]("
    return next(line for line in out.splitlines() if line.startswith(prefix))


@pytest.mark.parametrize("group_by", GROUP_BY_OPTIONS)
def test_main_escapes_milestone_and_labels(capsys, group_by):
    assert main([*group_by, *MARK_OPTIONS, ESCAPE_MARKS]) == 0
    line = _line_of(capsys.readouterr().out, 1)
    assert line.endswith(
        "（ラベル: x\\_y\\*z, docs）（マイルストーン: Sprint\\_1 \\*beta\\* \\<x\\>）"
    )


@pytest.mark.parametrize("group_by", GROUP_BY_OPTIONS)
def test_main_escapes_other_symbols_in_marks(capsys, group_by):
    assert main([*group_by, *MARK_OPTIONS, ESCAPE_MARKS]) == 0
    line = _line_of(capsys.readouterr().out, 3)
    assert line.endswith("（ラベル: a\\\\b\\`c\\[d\\]）（マイルストーン: \\[v2\\] \\`rc\\`\\\\）")


@pytest.mark.parametrize("group_by", GROUP_BY_OPTIONS)
def test_main_marks_without_symbols_unchanged(capsys, group_by):
    assert main([*group_by, *MARK_OPTIONS, ESCAPE_MARKS]) == 0
    line = _line_of(capsys.readouterr().out, 2)
    assert line.endswith("（ラベル: bug）（マイルストーン: v1.0）")
    assert "\\" not in line


def test_main_json_keeps_milestone_and_labels(capsys):
    assert main(["--json", *MARK_OPTIONS, ESCAPE_MARKS]) == 0
    body = json_out(capsys)
    by_number = {i["number"]: i for c in body["categories"] for i in c["issues"]}
    assert by_number[1]["milestone"] == "Sprint_1 *beta* <x>"
    assert by_number[1]["labels"] == ["x_y*z", "docs"]
    assert by_number[3]["milestone"] == "[v2] `rc`\\"
    assert by_number[3]["labels"] == ["a\\b`c[d]"]


@pytest.mark.parametrize("group_by", GROUP_BY_OPTIONS)
def test_main_max_chars_counts_escaped_marks(capsys, group_by):
    args = [*group_by, *MARK_OPTIONS]
    assert main([*args, ESCAPE_MARKS]) == 0
    full = capsys.readouterr().out
    assert main([*args, "--max-chars", str(len(full)), ESCAPE_MARKS]) == 0
    assert capsys.readouterr().out == full
    assert main([*args, "--max-chars", str(len(full) - 1), ESCAPE_MARKS]) == 0
    out = capsys.readouterr().out
    assert len(out) <= len(full) - 1
    assert issue_numbers_in_output(out) == [1, 2]
