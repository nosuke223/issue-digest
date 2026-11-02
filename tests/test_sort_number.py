import re

import pytest
from conftest import DATA, json_out

from issue_digest import main

SORT_NUMBER = str(DATA / "sort_number.json")


def _out(capsys, args: list[str]) -> str:
    assert main(args) == 0
    return capsys.readouterr().out


def _refs(out: str) -> list[str]:
    return re.findall(r"^- \[([^\]]+)\]\(", out, flags=re.MULTILINE)


def test_default_order_is_by_repository(capsys):
    assert _refs(_out(capsys, [SORT_NUMBER])) == [
        "alpha/tools#3",
        "beta/app#4",
        "alpha/tools#2",
        "alpha/tools#5",
        "beta/app#1",
        "beta/app#2",
    ]


def test_sort_number_orders_by_number_then_repository(capsys):
    out = _out(capsys, ["--sort", "number", SORT_NUMBER])
    # レビュー待ち → 着手可能の順は変わらず、各分類の中が番号の小さい順
    assert _refs(out) == [
        "alpha/tools#3",
        "beta/app#4",
        "beta/app#1",
        "alpha/tools#2",
        "beta/app#2",
        "alpha/tools#5",
    ]


def test_sort_number_reverse(capsys):
    out = _out(capsys, ["--sort", "number", "--reverse", SORT_NUMBER])
    assert _refs(out) == [
        "beta/app#4",
        "alpha/tools#3",
        "alpha/tools#5",
        "beta/app#2",
        "alpha/tools#2",
        "beta/app#1",
    ]


def test_sort_number_limit(capsys):
    out = _out(capsys, ["--sort", "number", "--limit", "2", SORT_NUMBER])
    assert _refs(out) == ["alpha/tools#3", "beta/app#4", "beta/app#1", "alpha/tools#2"]
    assert "- ほか 2 件" in out


def test_sort_number_json(capsys):
    assert main(["--json", "--sort", "number", SORT_NUMBER]) == 0
    data = json_out(capsys)
    ready = next(c for c in data["categories"] if c["label"] == "agent:ready")
    assert [i["url"] for i in ready["issues"]] == [
        "https://github.com/beta/app/issues/1",
        "https://github.com/alpha/tools/issues/2",
        "https://github.com/beta/app/issues/2",
        "https://github.com/alpha/tools/issues/5",
    ]


def test_sort_number_csv(capsys):
    out = _out(capsys, ["--csv", "--sort", "number", SORT_NUMBER])
    assert [line.split(",")[1] for line in out.splitlines()[1:]] == [
        "3",
        "4",
        "1",
        "2",
        "2",
        "5",
    ]


def test_sort_number_group_by_assignee(capsys):
    out = _out(capsys, ["--group-by", "assignee", "--sort", "number", SORT_NUMBER])
    assert _refs(out) == [
        "beta/app#1",
        "alpha/tools#2",
        "beta/app#2",
        "alpha/tools#3",
        "beta/app#4",
        "alpha/tools#5",
    ]


def test_sort_invalid_value_mentions_number(capsys):
    assert main(["--sort", "title", SORT_NUMBER]) == 2
    captured = capsys.readouterr()
    assert "updated、created、number" in captured.err
    assert captured.out == ""


def test_config_sort_number(in_tmp_dir, capsys):
    (in_tmp_dir / ".issue-digest.toml").write_text('sort = "number"\n', encoding="utf-8")
    assert _refs(_out(capsys, [SORT_NUMBER]))[2:] == [
        "beta/app#1",
        "alpha/tools#2",
        "beta/app#2",
        "alpha/tools#5",
    ]


def test_command_line_sort_overrides_config_number(in_tmp_dir, capsys):
    (in_tmp_dir / ".issue-digest.toml").write_text('sort = "number"\n', encoding="utf-8")
    out = _out(capsys, ["--sort", "created", SORT_NUMBER])
    assert _refs(out)[2:] == [
        "alpha/tools#2",
        "alpha/tools#5",
        "beta/app#1",
        "beta/app#2",
    ]


@pytest.mark.parametrize("value", ["Number", "title"])
def test_config_sort_invalid_value(in_tmp_dir, capsys, value):
    (in_tmp_dir / ".issue-digest.toml").write_text(f'sort = "{value}"\n', encoding="utf-8")
    assert main([SORT_NUMBER]) == 2
    assert '"number"' in capsys.readouterr().err
