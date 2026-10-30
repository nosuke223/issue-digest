import json
from datetime import UTC, datetime

import pytest
from conftest import DATA

from issue_digest import USAGE, main

SINCE = str(DATA / "since.json")
SINCE_NOW = datetime(2026, 10, 17, tzinfo=UTC)


def write_config(directory, text):
    (directory / ".issue-digest.toml").write_text(text, encoding="utf-8")


def _run(capsys, args):
    code = main(args, now=SINCE_NOW)
    return code, capsys.readouterr()


def test_config_since_matches_command_line(in_tmp_dir, capsys):
    _, expected = _run(capsys, ["--since", "7d", SINCE])
    write_config(in_tmp_dir, 'since = "7d"\n')
    code, got = _run(capsys, [SINCE])
    assert code == 0
    assert got.out == expected.out
    assert got.err == expected.err
    assert "# Issue ダイジェスト（全 2 件）" in got.out


@pytest.mark.parametrize("args", [["--since", "2026-10-01"], ["--since", "3d"], ["--since", "0d"]])
def test_command_line_since_ignores_config_since(in_tmp_dir, capsys, args):
    _, expected = _run(capsys, [*args, SINCE])
    write_config(in_tmp_dir, 'since = "7d"\n')
    code, got = _run(capsys, [*args, SINCE])
    assert code == 0
    assert got.out == expected.out


def test_command_line_since_wins_even_when_config_would_differ(in_tmp_dir, capsys):
    write_config(in_tmp_dir, 'since = "0d"\n')
    _, got = _run(capsys, ["--since", "7d", SINCE])
    assert "（全 2 件）" in got.out


@pytest.mark.parametrize("value", ['"2026-10-01"', '"7"', '"7D"', "7", "true", '"d"', '"-1d"'])
def test_invalid_config_since_exits_2_with_key(in_tmp_dir, capsys, value):
    write_config(in_tmp_dir, f"since = {value}\n")
    code, got = _run(capsys, [SINCE])
    assert code == 2
    assert got.err.startswith("エラー: 設定ファイルの since ")
    assert got.out == ""


def test_config_since_date_error_says_only_days_allowed(in_tmp_dir, capsys):
    write_config(in_tmp_dir, 'since = "2026-10-01"\n')
    _, got = _run(capsys, [SINCE])
    assert "日数の形だけ" in got.err


def test_invalid_config_since_is_error_even_with_command_line_since(in_tmp_dir, capsys):
    write_config(in_tmp_dir, 'since = "2026-10-01"\n')
    code, got = _run(capsys, ["--since", "7d", SINCE])
    assert code == 2
    assert got.err.startswith("エラー: 設定ファイルの since ")


def test_config_since_same_base_time_as_stale_and_age(in_tmp_dir, capsys):
    _, expected = _run(capsys, ["--json", "--since", "7d", "--age", "--stale", "7", SINCE])
    write_config(in_tmp_dir, 'since = "7d"\n')
    code, got = _run(capsys, ["--json", "--age", "--stale", "7", SINCE])
    assert code == 0
    assert got.out == expected.out
    by_number = {i["number"]: i for c in json.loads(got.out)["categories"] for i in c["issues"]}
    assert by_number[2]["age_days"] == 16
    assert by_number[2]["stale_days"] == 7


def test_config_since_not_used_for_diff_comparison(in_tmp_dir, capsys):
    previous = in_tmp_dir / "previous.json"
    assert main(["--json", "--output", str(previous), SINCE], now=SINCE_NOW) == 0
    capsys.readouterr()
    write_config(in_tmp_dir, 'since = "7d"\n')
    code, got = _run(capsys, ["--json", "--diff", str(previous), SINCE])
    assert code == 0
    body = json.loads(got.out)
    assert body["total"] == 2
    assert body["diff"] == {"added": [], "removed": [], "moved": []}


def test_without_config_since_unchanged(in_tmp_dir, capsys):
    write_config(in_tmp_dir, "stale = 7\n")
    _, got = _run(capsys, [SINCE])
    _, expected = _run(capsys, ["--stale", "7", SINCE])
    assert got.out == expected.out
    assert "（全 4 件）" in got.out


def test_config_since_huge_days_exits_2(in_tmp_dir, capsys):
    write_config(in_tmp_dir, f'since = "{10**12}d"\n')
    code, got = _run(capsys, [SINCE])
    assert code == 2
    assert got.err.startswith("エラー: 設定ファイルの since ")


def test_usage_mentions_since_key():
    config_part = USAGE.split("--config で読む設定ファイル")[1]
    assert "since" in config_part
