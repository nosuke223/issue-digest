import json

import pytest
from conftest import DATA, NOW, issue_numbers_in_output

from issue_digest import USAGE, main

ISSUES = str(DATA / "issues.json")


def write_config(directory, text, name=".issue-digest.toml"):
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return path


def test_no_config_file_is_unchanged(capsys):
    assert main([ISSUES]) == 0
    assert "## 中断 (agent:blocked) - 0件\n\nなし\n" in capsys.readouterr().out


def test_default_config_file_in_current_directory(in_tmp_dir, capsys):
    write_config(in_tmp_dir, "hide_empty = true\nsummary = true\n")
    assert main([ISSUES]) == 0
    out = capsys.readouterr().out
    assert "(agent:blocked)" not in out
    assert "判断待ち 0 / 中断 0 / レビュー待ち 0 / 作業中 0 / 着手可能 1 / 未分類 1\n" in out


def test_config_only_and_json(in_tmp_dir, capsys):
    write_config(in_tmp_dir, 'json = true\nonly = ["agent:ready"]\n')
    assert main([ISSUES]) == 0
    data = json.loads(capsys.readouterr().out)
    assert [c["label"] for c in data["categories"]] == ["agent:ready"]


def test_config_stale(in_tmp_dir, capsys):
    write_config(in_tmp_dir, "stale = 0\n")
    assert main([str(DATA / "stale.json")], now=NOW) == 0
    assert "日更新なし" in capsys.readouterr().out


def test_config_sort_orders_oldest_first(in_tmp_dir, capsys):
    write_config(in_tmp_dir, 'sort = "updated"\n')
    assert main([str(DATA / "sort.json")]) == 0
    assert issue_numbers_in_output(capsys.readouterr().out) == [8, 7, 6, 3, 4, 1, 2, 5]


def test_config_show_assignees(in_tmp_dir, capsys):
    write_config(in_tmp_dir, "show_assignees = true\n")
    assert main([str(DATA / "assignees.json")]) == 0
    assert "担当者が2人の Issue（担当: @bob, @alice）\n" in capsys.readouterr().out


def test_config_option_selects_file(in_tmp_dir, capsys):
    path = write_config(in_tmp_dir, "hide_empty = true\n", name="other.toml")
    assert main(["--config", str(path), ISSUES]) == 0
    assert "(agent:blocked)" not in capsys.readouterr().out


def test_config_option_replaces_default_file(in_tmp_dir, capsys):
    write_config(in_tmp_dir, "hide_empty = true\n")
    other = write_config(in_tmp_dir, "summary = false\n", name="other.toml")
    assert main(["--config", str(other), ISSUES]) == 0
    assert "(agent:blocked) - 0件" in capsys.readouterr().out


def test_missing_config_option_file_exits_1(capsys):
    assert main(["--config", "nothing.toml", ISSUES]) == 1
    assert "設定ファイルが見つかりません: nothing.toml" in capsys.readouterr().err


def test_command_line_only_replaces_config_only(in_tmp_dir, capsys):
    write_config(in_tmp_dir, 'only = ["agent:ready"]\n')
    assert main(["--only", "unclassified", ISSUES]) == 0
    out = capsys.readouterr().out
    assert "## 未分類" in out
    assert "## 着手可能" not in out


def test_command_line_exclude_replaces_config_only(in_tmp_dir, capsys):
    write_config(in_tmp_dir, 'only = ["agent:ready"]\n')
    assert main(["--exclude", "agent:ready", ISSUES]) == 0
    out = capsys.readouterr().out
    assert "## 着手可能" not in out
    assert "## 未分類" in out


def test_command_line_stale_and_sort_take_precedence(in_tmp_dir, capsys):
    write_config(in_tmp_dir, 'stale = 1000\nsort = "updated"\n')
    assert main(["--stale", "0", str(DATA / "stale.json")], now=NOW) == 0
    assert "日更新なし" in capsys.readouterr().out


def test_command_line_csv_takes_precedence_over_config_json(in_tmp_dir, capsys):
    write_config(in_tmp_dir, "json = true\n")
    assert main(["--csv", ISSUES]) == 0
    assert capsys.readouterr().out.startswith("label,number,title,url\r\n")


@pytest.mark.parametrize(
    ("text", "key"),
    [
        ("unknown = 1\n", "unknown"),
        ('hide_empty = "yes"\n', "hide_empty"),
        ("summary = 1\n", "summary"),
        ("show_assignees = 0\n", "show_assignees"),
        ('json = "true"\n', "json"),
        ('only = "agent:ready"\n', "only"),
        ("only = [1]\n", "only"),
        ('only = ["nothing"]\n', "only"),
        ("stale = -1\n", "stale"),
        ('stale = "7"\n', "stale"),
        ("stale = true\n", "stale"),
        ("stale = 1.5\n", "stale"),
        ('sort = "created"\n', "sort"),
    ],
)
def test_invalid_config_exits_2_with_key(in_tmp_dir, capsys, text, key):
    write_config(in_tmp_dir, text)
    assert main([ISSUES]) == 2
    err = capsys.readouterr().err
    assert err.startswith("エラー: ")
    assert key in err


def test_broken_toml_exits_2(in_tmp_dir, capsys):
    write_config(in_tmp_dir, "hide_empty = \n")
    assert main([ISSUES]) == 2
    assert "TOML" in capsys.readouterr().err


def test_non_utf8_config_exits_2(in_tmp_dir, capsys):
    path = in_tmp_dir / ".issue-digest.toml"
    path.write_bytes("# 日本語のコメント\nhide_empty = true\n".encode("shift_jis"))
    assert main([ISSUES]) == 2
    err = capsys.readouterr().err
    assert err.startswith("エラー: ")
    assert "UTF-8" in err


def test_usage_mentions_config(capsys):
    assert main(["--help"]) == 0
    assert capsys.readouterr().out.strip() == USAGE
    assert "--config" in USAGE
    assert ".issue-digest.toml" in USAGE
