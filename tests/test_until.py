from datetime import UTC, datetime

import pytest
from conftest import DATA, issue_numbers_in_output, json_out

from issue_digest import main

UNTIL = str(DATA / "until.json")
UNTIL_ERROR = "エラー: --until には YYYY-MM-DD の形の日付を指定してください: {value}\n"
ORDER_ERROR = "エラー: --since は --until より前の日付にしてください\n"
OCTOBER = ["--since", "2026-10-01", "--until", "2026-10-31"]


def test_main_since_and_until_select_october(capsys):
    assert main([*OCTOBER, UNTIL]) == 0
    out = capsys.readouterr().out
    # 10月1日0時の #2、10月31日の終わりの #3、UTC では10月31日の #5 が出る。
    # 9月30日の #1、11月1日0時の #4、updatedAt がない #6 は出ない
    assert sorted(issue_numbers_in_output(out)) == [2, 3, 5]
    assert out.startswith("# Issue ダイジェスト（全 3 件）\n")
    assert "## 着手可能 (agent:ready) - 1件" in out
    assert "## レビュー待ち (agent:review) - 2件" in out
    assert "## 中断 (agent:blocked) - 0件" in out


def test_main_until_only(capsys):
    assert main(["--until", "2026-10-31", UNTIL]) == 0
    out = capsys.readouterr().out
    assert sorted(issue_numbers_in_output(out)) == [1, 2, 3, 5]
    assert out.startswith("# Issue ダイジェスト（全 4 件）\n")


def test_main_until_previous_day_excludes_boundary_issue(capsys):
    assert main(["--until", "2026-10-30", UNTIL]) == 0
    assert sorted(issue_numbers_in_output(capsys.readouterr().out)) == [1, 2]


def test_main_since_and_until_same_day(capsys):
    assert main(["--since", "2026-10-01", "--until", "2026-10-01", UNTIL]) == 0
    assert issue_numbers_in_output(capsys.readouterr().out) == [2]


def test_main_until_summary_counts_filtered(capsys):
    assert main([*OCTOBER, "--summary", UNTIL]) == 0
    assert (
        "判断待ち 0 / 中断 0 / レビュー待ち 2 / 作業中 0 / 着手可能 1 / 未分類 0\n"
    ) in capsys.readouterr().out


def test_main_until_json(capsys):
    assert main(["--json", *OCTOBER, UNTIL]) == 0
    body = json_out(capsys)
    assert body["total"] == 3
    numbers = [i["number"] for c in body["categories"] for i in c["issues"]]
    assert sorted(numbers) == [2, 3, 5]


def test_main_until_csv(capsys):
    assert main(["--csv", *OCTOBER, UNTIL]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 4
    assert sorted(line.split(",")[1] for line in lines[1:]) == ["2", "3", "5"]


def test_main_until_group_by_assignee(capsys):
    assert main(["--group-by", "assignee", "--summary", *OCTOBER, UNTIL]) == 0
    out = capsys.readouterr().out
    assert sorted(issue_numbers_in_output(out)) == [2, 3, 5]
    assert out.startswith("# Issue ダイジェスト（全 3 件）\n")
    assert "## @alice - 1件" in out
    assert "## @bob - 1件" in out
    assert "## 担当者なし - 1件" in out
    assert "@alice 1 / @bob 1 / 担当者なし 1\n" in out


def test_main_until_fail_if_any_uses_count_after_until(capsys):
    # #4（blocked）は11月1日の更新なので --until で除かれ、件数は0
    assert main(["--fail-if-any", "agent:blocked", UNTIL]) == 3
    assert main(["--until", "2026-10-31", "--fail-if-any", "agent:blocked", UNTIL]) == 0
    assert main(["--until", "2026-10-31", "--fail-if-any", "agent:review", UNTIL]) == 3
    capsys.readouterr()


def test_main_until_with_diff_compares_all_issues(capsys, tmp_path):
    previous = tmp_path / "previous.json"
    assert main(["--json", "--output", str(previous), UNTIL]) == 0
    capsys.readouterr()
    assert main(["--json", *OCTOBER, "--diff", str(previous), UNTIL]) == 0
    body = json_out(capsys)
    assert body["total"] == 3
    assert body["diff"] == {"added": [], "removed": [], "moved": []}


def test_main_until_last_value_wins(capsys):
    assert main(["--until", "2026-09-30", "--until", "2026-10-31", UNTIL]) == 0
    assert sorted(issue_numbers_in_output(capsys.readouterr().out)) == [1, 2, 3, 5]


def test_main_until_max_date(capsys):
    # 翌日を表せない日付でも、updatedAt がある Issue はすべて出る
    assert main(["--until", "9999-12-31", UNTIL]) == 0
    assert sorted(issue_numbers_in_output(capsys.readouterr().out)) == [1, 2, 3, 4, 5]


@pytest.mark.parametrize(
    "args",
    [
        ["--since", "2026-11-01", "--until", "2026-10-31"],
        ["--until", "2026-10-31", "--since", "2026-11-01"],
    ],
)
def test_main_since_after_until(capsys, args):
    assert main([*args, UNTIL]) == 2
    captured = capsys.readouterr()
    assert captured.err == ORDER_ERROR
    assert captured.out == ""


NOW = datetime(2026, 11, 2, 12, tzinfo=UTC)


def test_main_since_days_after_until(capsys):
    # 1d は 2026-11-01 12時で、日付は11月1日。10月31日より後なのでエラー
    assert main(["--since", "1d", "--until", "2026-10-31", UNTIL], now=NOW) == 2
    captured = capsys.readouterr()
    assert captured.err == ORDER_ERROR
    assert captured.out == ""


def test_main_since_days_same_day_as_until(capsys):
    # 2d は 2026-10-31 12時で、日付は10月31日。同じ日なのでエラーにならない
    assert main(["--since", "2d", "--until", "2026-10-31", UNTIL], now=NOW) == 0
    assert sorted(issue_numbers_in_output(capsys.readouterr().out)) == [3, 5]


@pytest.mark.parametrize(
    "value",
    [
        "2026-02-30",
        "2026-13-01",
        "2026/10/31",
        "20261031",
        "2026-1-31",
        "7d",
        "-1",
        "abc",
        "",
        "２０２６-10-31",
    ],
)
def test_main_until_invalid_value(capsys, value):
    assert main(["--until", value, UNTIL]) == 2
    captured = capsys.readouterr()
    assert captured.err == UNTIL_ERROR.format(value=value)
    assert captured.out == ""


def test_main_until_invalid_value_checked_before_order(capsys):
    assert main(["--since", "2026-11-01", "--until", "2026-02-30", UNTIL]) == 2
    assert capsys.readouterr().err == UNTIL_ERROR.format(value="2026-02-30")


def test_main_until_without_value_shows_usage(capsys):
    assert main([UNTIL, "--until"]) == 2
    captured = capsys.readouterr()
    assert "使い方" in captured.err
    assert captured.out == ""


def test_main_config_until_is_unknown_key(capsys, tmp_path):
    config = tmp_path / "config.toml"
    config.write_text('until = "2026-10-31"\n', encoding="utf-8")
    assert main(["--config", str(config), UNTIL]) == 2
    assert capsys.readouterr().err == "エラー: 設定ファイルに知らないキーがあります: until\n"


def _config_since(tmp_path, value):
    config = tmp_path / "config.toml"
    config.write_text(f'since = "{value}"\n', encoding="utf-8")
    return str(config)


def test_main_config_since_after_until(capsys, tmp_path):
    # 設定の since も --since と同じ決まりで比べる。1d は11月1日で、10月31日より後
    config = _config_since(tmp_path, "1d")
    assert main(["--config", config, "--until", "2026-10-31", UNTIL], now=NOW) == 2
    captured = capsys.readouterr()
    assert captured.err == (
        "エラー: 設定ファイルの since（1d）は --until より前の日付にしてください\n"
    )
    assert captured.out == ""


def test_main_config_since_after_until_with_fail_if_any(capsys, tmp_path):
    # 0件で終了コード 0 にならず、--fail-if-any の判定の前にエラーになる
    config = _config_since(tmp_path, "1d")
    args = ["--config", config, "--until", "2026-10-31", "--fail-if-any", "agent:review"]
    assert main([*args, UNTIL], now=NOW) == 2
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("until", ["2026-11-01", "2026-11-02", "2026-12-31"])
def test_main_config_since_not_after_until_filters_both(capsys, tmp_path, until):
    # 1d は 2026-11-01 12時。--until が11月1日以降ならエラーにせず、両方の条件で絞る。
    # 11月1日0時の #4 も設定の since より前なので出ない
    config = _config_since(tmp_path, "1d")
    assert main(["--config", config, "--until", until, UNTIL], now=NOW) == 0
    assert issue_numbers_in_output(capsys.readouterr().out) == []


def test_main_config_since_same_day_as_until_filters_both(capsys, tmp_path):
    # 2d は 2026-10-31 12時。同じ日なのでエラーにせず、両方の条件で絞る
    config = _config_since(tmp_path, "2d")
    assert main(["--config", config, "--until", "2026-10-31", UNTIL], now=NOW) == 0
    assert sorted(issue_numbers_in_output(capsys.readouterr().out)) == [3, 5]


def test_main_config_since_with_wide_range_and_until(capsys, tmp_path):
    # 32d は 2026-10-01 12時。--until と組み合わせて期間で絞れる
    # （#1、#2 は設定の since で、#4 は --until で除かれる）
    config = _config_since(tmp_path, "32d")
    assert main(["--config", config, "--until", "2026-10-31", UNTIL], now=NOW) == 0
    assert sorted(issue_numbers_in_output(capsys.readouterr().out)) == [3, 5]


def test_main_command_line_since_ignores_config_since_with_until(capsys, tmp_path):
    # --since を指定すると設定の since は使わないので、設定の 1d とは比べない
    config = _config_since(tmp_path, "1d")
    assert main(["--config", config, *OCTOBER, UNTIL], now=NOW) == 0
    assert sorted(issue_numbers_in_output(capsys.readouterr().out)) == [2, 3, 5]


def test_main_usage_mentions_until(capsys):
    assert main(["--help"]) == 0
    assert "--until" in capsys.readouterr().out
