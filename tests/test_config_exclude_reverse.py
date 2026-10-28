import pytest
from conftest import DATA, NOW

from issue_digest import USAGE, main

ISSUES = str(DATA / "issues.json")
SORT = str(DATA / "sort.json")
GROUP_BY = str(DATA / "group_by.json")
BOTH_ERROR = "エラー: --only と --exclude は同時に指定できません\n"


def write_config(directory, text):
    (directory / ".issue-digest.toml").write_text(text, encoding="utf-8")


def _run(capsys, args):
    code = main(args, now=NOW)
    return code, capsys.readouterr()


def test_config_exclude_matches_command_line(in_tmp_dir, capsys):
    _, expected = _run(capsys, ["--exclude", "unclassified", ISSUES])
    write_config(in_tmp_dir, 'exclude = ["unclassified"]\n')
    code, got = _run(capsys, [ISSUES])
    assert code == 0
    assert got.out == expected.out
    assert "## 未分類" not in got.out
    assert "## 着手可能" in got.out


def test_command_line_only_ignores_config_exclude(in_tmp_dir, capsys):
    _, expected = _run(capsys, ["--only", "unclassified", ISSUES])
    write_config(in_tmp_dir, 'exclude = ["unclassified"]\n')
    code, got = _run(capsys, ["--only", "unclassified", ISSUES])
    assert code == 0
    assert got.out == expected.out
    assert "## 未分類" in got.out


@pytest.mark.parametrize(
    "text",
    ['exclude = ["agent:ready"]\n', 'only = ["unclassified"]\n'],
)
def test_command_line_exclude_ignores_config_only_and_exclude(in_tmp_dir, capsys, text):
    _, expected = _run(capsys, ["--exclude", "agent:working", ISSUES])
    write_config(in_tmp_dir, text)
    code, got = _run(capsys, ["--exclude", "agent:working", ISSUES])
    assert code == 0
    assert got.out == expected.out
    assert "## 着手可能" in got.out
    assert "## 未分類" in got.out


def test_config_only_and_exclude_exits_2(in_tmp_dir, capsys):
    write_config(in_tmp_dir, 'only = ["agent:ready"]\nexclude = ["unclassified"]\n')
    code, got = _run(capsys, [ISSUES])
    assert code == 2
    assert got.err == BOTH_ERROR
    assert got.out == ""


@pytest.mark.parametrize(
    "args",
    [["--only", "agent:ready"], ["--exclude", "agent:ready"]],
)
def test_config_only_and_exclude_ignored_with_command_line(in_tmp_dir, capsys, args):
    _, expected = _run(capsys, [*args, ISSUES])
    write_config(in_tmp_dir, 'only = ["agent:ready"]\nexclude = ["unclassified"]\n')
    code, got = _run(capsys, [*args, ISSUES])
    assert code == 0
    assert got.out == expected.out


@pytest.mark.parametrize(
    ("text", "args"),
    [
        ('only = []\nexclude = ["unclassified"]\n', ["--exclude", "unclassified"]),
        ('only = ["unclassified"]\nexclude = []\n', ["--only", "unclassified"]),
        ("only = []\nexclude = []\n", []),
    ],
)
def test_config_empty_array_is_same_as_unset(in_tmp_dir, capsys, text, args):
    _, expected = _run(capsys, [*args, ISSUES])
    write_config(in_tmp_dir, text)
    code, got = _run(capsys, [ISSUES])
    assert code == 0
    assert got.out == expected.out


@pytest.mark.parametrize(
    "text",
    [
        'exclude = ["nothing"]\n',
        'exclude = "unclassified"\n',
        "exclude = [1]\n",
        "exclude = true\n",
    ],
)
def test_invalid_config_exclude_exits_2_with_key(in_tmp_dir, capsys, text):
    write_config(in_tmp_dir, text)
    code, got = _run(capsys, [ISSUES])
    assert code == 2
    assert got.err.startswith("エラー: 設定ファイルの exclude ")
    assert got.out == ""


@pytest.mark.parametrize("text", ['reverse = "yes"\n', "reverse = 1\n"])
def test_invalid_config_reverse_exits_2_with_key(in_tmp_dir, capsys, text):
    write_config(in_tmp_dir, text)
    code, got = _run(capsys, [ISSUES])
    assert code == 2
    assert got.err.startswith("エラー: 設定ファイルの reverse ")


@pytest.mark.parametrize(
    ("path", "args"),
    [
        (SORT, []),
        (SORT, ["--sort", "updated"]),
        (SORT, ["--sort", "created"]),
        (SORT, ["--limit", "2"]),
        (SORT, ["--max-chars", "450"]),
        (SORT, ["--json"]),
        (SORT, ["--csv"]),
        (GROUP_BY, ["--group-by", "assignee"]),
        (GROUP_BY, ["--group-by", "assignee", "--sort", "updated", "--limit", "1"]),
    ],
)
def test_config_reverse_matches_command_line(in_tmp_dir, capsys, path, args):
    _, plain = _run(capsys, [*args, path])
    _, expected = _run(capsys, ["--reverse", *args, path])
    write_config(in_tmp_dir, "reverse = true\n")
    code, got = _run(capsys, [*args, path])
    assert code == 0
    assert got.out == expected.out
    assert got.err == expected.err
    assert got.out != plain.out
    if "--max-chars" in args:
        # 一部の行だけを削って「- ほか N 件」にしている
        assert "- ほか " in got.out
        assert "- [example/repo#" in got.out


def test_config_reverse_with_command_line_reverse(in_tmp_dir, capsys):
    _, expected = _run(capsys, ["--reverse", SORT])
    write_config(in_tmp_dir, "reverse = true\n")
    _, got = _run(capsys, ["--reverse", SORT])
    assert got.out == expected.out


def test_config_reverse_false_does_nothing(in_tmp_dir, capsys):
    _, expected = _run(capsys, [SORT])
    write_config(in_tmp_dir, "reverse = false\n")
    _, got = _run(capsys, [SORT])
    assert got.out == expected.out


def test_usage_mentions_exclude_and_reverse_keys():
    config_part = USAGE.split("--config で読む設定ファイル")[1]
    assert "exclude" in config_part
    assert "reverse" in config_part
