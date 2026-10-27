import csv
import io

import pytest
from conftest import DATA, issue_numbers_in_output, json_out

from issue_digest import main

SORT = str(DATA / "sort.json")
SORT_CREATED = str(DATA / "sort_created.json")
GROUP_BY = str(DATA / "group_by.json")


def _out(capsys, args: list[str]) -> str:
    assert main(args) == 0
    return capsys.readouterr().out


def _alice_section(out: str) -> str:
    return next(part for part in out.split("\n## ") if part.startswith("@alice - 3件"))


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        # レビュー待ち → 着手可能の順は変わらず、各分類の中だけが逆になる
        ([], [8, 7, 6, 5, 4, 3, 2, 1]),
        # --sort の結果をそのまま逆にする（updatedAt がない Issue は逆にした先頭）
        (["--sort", "updated"], [7, 8, 5, 2, 1, 4, 3, 6]),
    ],
)
def test_reverse_markdown(capsys, args, expected):
    assert issue_numbers_in_output(_out(capsys, ["--reverse", *args, SORT])) == expected


def test_reverse_sort_created(capsys):
    # --sort created は [7, 8] / [3, 4, 1, 6, 2, 5]
    out = _out(capsys, ["--reverse", "--sort", "created", SORT_CREATED])
    assert issue_numbers_in_output(out) == [8, 7, 5, 2, 6, 1, 4, 3]


def test_reverse_limit_counts_from_reversed_head(capsys):
    out = _out(capsys, ["--reverse", "--limit", "2", SORT])
    assert issue_numbers_in_output(out) == [8, 7, 6, 5]
    assert "- ほか 4 件" in out


def test_reverse_limit_with_sort(capsys):
    out = _out(capsys, ["--reverse", "--sort", "updated", "--limit", "1", SORT])
    assert issue_numbers_in_output(out) == [7, 5]


def test_reverse_max_chars_trims_tail_of_reversed_order(capsys):
    full = _out(capsys, ["--reverse", SORT])
    out = _out(capsys, ["--reverse", "--max-chars", str(len(full) - 1), SORT])
    assert issue_numbers_in_output(out) == [8, 7, 6, 5, 4, 3, 2]
    assert "- ほか 1 件" in out


def test_reverse_json(capsys):
    assert main(["--json", "--reverse", "--limit", "2", SORT]) == 0
    categories = json_out(capsys)["categories"]
    numbers = {c["label"]: [i["number"] for i in c["issues"]] for c in categories}
    assert numbers["agent:review"] == [8, 7]
    assert numbers["agent:ready"] == [6, 5]
    counts = {c["label"]: (c["count"], c["omitted"]) for c in categories}
    assert counts["agent:ready"] == (6, 4)


def test_reverse_csv(capsys):
    out = _out(capsys, ["--csv", "--reverse", "--limit", "2", SORT])
    rows = list(csv.reader(io.StringIO(out)))
    assert [int(r[1]) for r in rows[1:]] == [8, 7, 6, 5]


@pytest.mark.parametrize(
    ("sort", "expected"),
    [(None, [5, 2, 1]), ("updated", [2, 5, 1]), ("created", [5, 1, 2])],
)
def test_reverse_group_by_assignee(capsys, sort, expected):
    args = ["--group-by", "assignee", "--reverse"] + ([] if sort is None else ["--sort", sort])
    out = _out(capsys, [*args, GROUP_BY])
    assert issue_numbers_in_output(_alice_section(out)) == expected
    # 担当者の順は変わらない
    headings = [line for line in out.splitlines() if line.startswith("## ")]
    assert headings == [
        "## @alice - 3件",
        "## @bob - 1件",
        "## @Carol - 1件",
        "## 担当者なし - 2件",
    ]


def test_reverse_group_by_assignee_limit(capsys):
    out = _out(capsys, ["--group-by", "assignee", "--reverse", "--limit", "1", GROUP_BY])
    alice = _alice_section(out)
    assert issue_numbers_in_output(alice) == [5]
    assert "- ほか 2 件" in alice


def test_without_reverse_unchanged(capsys):
    assert issue_numbers_in_output(_out(capsys, [SORT])) == [7, 8, 1, 2, 3, 4, 5, 6]
    out = _out(capsys, ["--sort", "updated", SORT])
    assert issue_numbers_in_output(out) == [8, 7, 6, 3, 4, 1, 2, 5]


def test_reverse_keeps_diff_section_order(capsys):
    args = ["--diff", str(DATA / "diff_previous.json"), str(DATA / "diff_current.json")]
    normal = _out(capsys, args)
    reversed_out = _out(capsys, ["--reverse", *args])
    marker = "## 前回からの変化"
    assert marker in normal
    assert normal[normal.index(marker) :] == reversed_out[reversed_out.index(marker) :]


def test_usage_mentions_reverse(capsys):
    assert main(["--help"]) == 0
    assert "--reverse" in capsys.readouterr().out
