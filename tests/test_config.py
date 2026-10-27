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


def test_config_sort_created_orders_oldest_first(in_tmp_dir, capsys):
    write_config(in_tmp_dir, 'sort = "created"\n')
    assert main([str(DATA / "sort_created.json")]) == 0
    assert issue_numbers_in_output(capsys.readouterr().out) == [7, 8, 3, 4, 1, 6, 2, 5]


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


def test_command_line_stale_takes_precedence(in_tmp_dir, capsys):
    write_config(in_tmp_dir, "stale = 1000\n")
    assert main(["--stale", "0", str(DATA / "stale.json")], now=NOW) == 0
    assert "日更新なし" in capsys.readouterr().out


def test_command_line_sort_takes_precedence(in_tmp_dir, capsys):
    write_config(in_tmp_dir, 'sort = "updated"\n')
    assert main(["--sort", "created", str(DATA / "sort_created.json")]) == 0
    assert issue_numbers_in_output(capsys.readouterr().out) == [7, 8, 3, 4, 1, 6, 2, 5]


def test_command_line_sort_updated_takes_precedence_over_config_created(in_tmp_dir, capsys):
    write_config(in_tmp_dir, 'sort = "created"\n')
    assert main(["--sort", "updated", str(DATA / "sort.json")]) == 0
    assert issue_numbers_in_output(capsys.readouterr().out) == [8, 7, 6, 3, 4, 1, 2, 5]


def test_config_show_labels(in_tmp_dir, capsys):
    write_config(in_tmp_dir, "show_labels = true\n")
    assert main([str(DATA / "show_labels.json")]) == 0
    assert "（ラベル: " in capsys.readouterr().out


def test_config_show_milestone(in_tmp_dir, capsys):
    write_config(in_tmp_dir, "show_milestone = true\n")
    milestone = str(DATA / "milestone.json")
    assert main([milestone]) == 0
    assert "マイルストーンがある Issue（マイルストーン: v1.0）\n" in capsys.readouterr().out
    assert main(["--json", milestone]) == 0
    body = json.loads(capsys.readouterr().out)
    by_number = {i["number"]: i for c in body["categories"] for i in c["issues"]}
    assert by_number[1]["milestone"] == "v1.0"
    assert main(["--group-by", "assignee", milestone]) == 0
    assert "（着手可能）（マイルストーン: v1.0）\n" in capsys.readouterr().out


def test_config_show_milestone_false_does_nothing(in_tmp_dir, capsys):
    write_config(in_tmp_dir, "show_milestone = false\n")
    assert main([str(DATA / "milestone.json")]) == 0
    assert "（マイルストーン:" not in capsys.readouterr().out


def test_config_title(in_tmp_dir, capsys):
    write_config(in_tmp_dir, 'title = "my-repo"\n')
    assert main([ISSUES]) == 0
    assert capsys.readouterr().out.startswith("# my-repo（全 ")


def test_command_line_title_takes_precedence(in_tmp_dir, capsys):
    write_config(in_tmp_dir, 'title = "my-repo"\n')
    assert main(["--title", "other", ISSUES]) == 0
    out = capsys.readouterr().out
    assert out.startswith("# other（全 ")
    assert "my-repo" not in out


def test_config_limit(in_tmp_dir, capsys):
    write_config(in_tmp_dir, "limit = 1\n")
    assert main([str(DATA / "sort.json")]) == 0
    assert "- ほか " in capsys.readouterr().out


def test_command_line_limit_takes_precedence(in_tmp_dir, capsys):
    write_config(in_tmp_dir, "limit = 1\n")
    assert main(["--limit", "100", str(DATA / "sort.json")]) == 0
    assert "- ほか " not in capsys.readouterr().out


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
        ('sort = "name"\n', "sort"),
        ("sort = 1\n", "sort"),
        ('show_labels = "yes"\n', "show_labels"),
        ('show_milestone = "yes"\n', "show_milestone"),
        ("show_milestone = 1\n", "show_milestone"),
        ("title = 1\n", "title"),
        ('title = ""\n', "title"),
        ("limit = 0\n", "limit"),
        ("limit = -1\n", "limit"),
        ('limit = "5"\n', "limit"),
        ("limit = true\n", "limit"),
        ("limit = 1.5\n", "limit"),
        ('headings = "x"\n', "headings"),
        ('[headings]\n"agent:nothing" = "x"\n', "agent:nothing"),
        ('[headings]\n"agent:review" = 1\n', "agent:review"),
        ('[headings]\n"agent:review" = ""\n', "agent:review"),
        ('[headings]\nunclassified = ["x"]\n', "unclassified"),
    ],
)
def test_invalid_config_exits_2_with_key(in_tmp_dir, capsys, text, key):
    write_config(in_tmp_dir, text)
    assert main([ISSUES]) == 2
    err = capsys.readouterr().err
    assert err.startswith("エラー: ")
    assert key in err


HEADINGS_CONFIG = '[headings]\n"agent:review" = "確認待ち"\nunclassified = "その他"\n'


def test_config_headings_in_markdown_and_summary(in_tmp_dir, capsys):
    write_config(in_tmp_dir, "summary = true\n" + HEADINGS_CONFIG)
    assert main([ISSUES]) == 0
    out = capsys.readouterr().out
    assert "## 確認待ち (agent:review) - " in out
    assert "## その他 - " in out
    assert "レビュー待ち" not in out
    assert "未分類" not in out
    assert "判断待ち 0 / 中断 0 / 確認待ち 0 / 作業中 0 / 着手可能 1 / その他 1\n" in out
    # 設定しない分類の見出しは変わらない
    assert "## 作業中 (agent:working) - " in out


def test_config_headings_in_json_title(in_tmp_dir, capsys):
    write_config(in_tmp_dir, "json = true\n" + HEADINGS_CONFIG)
    assert main([ISSUES]) == 0
    titles = {c["label"]: c["title"] for c in json.loads(capsys.readouterr().out)["categories"]}
    assert titles["agent:review"] == "確認待ち"
    assert titles["unclassified"] == "その他"
    assert titles["agent:working"] == "作業中"
    assert titles["agent:blocked"] == "中断"


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


AGE = str(DATA / "age.json")
GROUP_BY = str(DATA / "group_by.json")
SORT = str(DATA / "sort.json")


def _out(capsys, args):
    code = main(args, now=NOW)
    return code, capsys.readouterr()


def test_config_age_matches_command_line(in_tmp_dir, capsys):
    _, expected = _out(capsys, ["--age", AGE])
    write_config(in_tmp_dir, "age = true\n")
    code, got = _out(capsys, [AGE])
    assert code == 0
    assert got.out == expected.out
    assert "（作成から12日）" in got.out


def test_config_age_in_json(in_tmp_dir, capsys):
    write_config(in_tmp_dir, "age = true\njson = true\n")
    assert main([AGE], now=NOW) == 0
    assert '"age_days": 12' in capsys.readouterr().out


def test_config_max_chars_matches_command_line(in_tmp_dir, capsys):
    _, full = _out(capsys, [SORT])
    limit = len(full.out) - 1
    _, expected = _out(capsys, ["--max-chars", str(limit), SORT])
    write_config(in_tmp_dir, f"max_chars = {limit}\n")
    code, got = _out(capsys, [SORT])
    assert code == 0
    assert got.out == expected.out
    assert got.out != full.out


def test_command_line_max_chars_takes_precedence(in_tmp_dir, capsys):
    _, full = _out(capsys, [SORT])
    write_config(in_tmp_dir, "max_chars = 1\n")
    _, got = _out(capsys, ["--max-chars", str(len(full.out)), SORT])
    assert got.out == full.out
    assert got.err == ""


def test_config_group_by_matches_command_line(in_tmp_dir, capsys):
    _, expected = _out(capsys, ["--group-by", "assignee", GROUP_BY])
    write_config(in_tmp_dir, 'group_by = "assignee"\n')
    code, got = _out(capsys, [GROUP_BY])
    assert code == 0
    assert got.out == expected.out
    assert "## 担当者なし" in got.out


def test_command_line_group_by_takes_precedence_over_config_json(in_tmp_dir, capsys):
    _, expected = _out(capsys, ["--group-by", "assignee", GROUP_BY])
    write_config(in_tmp_dir, "json = true\n")
    _, got = _out(capsys, ["--group-by", "assignee", GROUP_BY])
    assert got.out == expected.out


@pytest.mark.parametrize("option", ["--json", "--csv"])
def test_command_line_format_ignores_config_group_by_and_max_chars(in_tmp_dir, capsys, option):
    _, expected = _out(capsys, [option, GROUP_BY])
    write_config(in_tmp_dir, 'group_by = "assignee"\nmax_chars = 1\n')
    code, got = _out(capsys, [option, GROUP_BY])
    assert code == 0
    assert got.out == expected.out
    assert got.err == ""


def test_config_max_chars_with_command_line_group_by(in_tmp_dir, capsys):
    _, expected = _out(capsys, ["--group-by", "assignee", "--max-chars", "200", GROUP_BY])
    write_config(in_tmp_dir, "max_chars = 200\njson = true\n")
    code, got = _out(capsys, ["--group-by", "assignee", GROUP_BY])
    assert code == 0
    assert got.out == expected.out


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (
            'json = true\ngroup_by = "assignee"\n',
            "エラー: --group-by と --json は同時に指定できません"
            "（--group-by は Markdown だけで使えます）\n",
        ),
        (
            "json = true\nmax_chars = 100\n",
            "エラー: --max-chars は --json、--csv と同時に指定できません"
            "（Markdown だけで使えます）\n",
        ),
    ],
)
def test_config_conflict_exits_2_like_command_line(in_tmp_dir, capsys, text, message):
    write_config(in_tmp_dir, text)
    code, got = _out(capsys, [GROUP_BY])
    assert code == 2
    assert got.err == message
    assert got.out == ""


@pytest.mark.parametrize(
    ("text", "key"),
    [
        ('age = "yes"\n', "age"),
        ("age = 1\n", "age"),
        ("max_chars = 0\n", "max_chars"),
        ("max_chars = -1\n", "max_chars"),
        ('max_chars = "100"\n', "max_chars"),
        ("max_chars = true\n", "max_chars"),
        ("max_chars = 1.5\n", "max_chars"),
        ('group_by = "label"\n', "group_by"),
        ("group_by = 1\n", "group_by"),
        ("group_by = true\n", "group_by"),
    ],
)
def test_invalid_new_config_values_exit_2_with_key(in_tmp_dir, capsys, text, key):
    write_config(in_tmp_dir, text)
    assert main([ISSUES]) == 2
    err = capsys.readouterr().err
    assert err.startswith("エラー: ")
    assert key in err


def test_usage_mentions_new_config_keys():
    for key in ("age", "max_chars", "group_by"):
        assert key in USAGE.split("--config で読む設定ファイル")[1]
