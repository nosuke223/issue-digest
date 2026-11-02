import pytest
from conftest import DATA

from issue_digest import USAGE, main

# 着手可能 1件、未分類 1件。ほかの分類は 0件
ISSUES = str(DATA / "issues.json")


def write_config(directory, text):
    (directory / ".issue-digest.toml").write_text(text, encoding="utf-8")


def test_config_fail_if_any_exits_3_when_category_has_issues(in_tmp_dir, capsys):
    write_config(in_tmp_dir, 'fail_if_any = ["agent:ready"]\n')
    assert main([ISSUES]) == 3
    # ダイジェストはいつもどおり出力する
    assert "## 着手可能 (agent:ready) - 1件" in capsys.readouterr().out


def test_config_fail_if_any_exits_0_when_category_is_empty(in_tmp_dir):
    write_config(in_tmp_dir, 'fail_if_any = ["agent:blocked"]\n')
    assert main([ISSUES]) == 0


def test_config_fail_if_any_multiple_any_match_exits_3(in_tmp_dir):
    write_config(in_tmp_dir, 'fail_if_any = ["agent:blocked", "unclassified"]\n')
    assert main([ISSUES]) == 3


def test_config_fail_if_any_empty_array_is_same_as_unset(in_tmp_dir):
    write_config(in_tmp_dir, "fail_if_any = []\n")
    assert main([ISSUES]) == 0


def test_command_line_fail_if_any_replaces_config(in_tmp_dir):
    write_config(in_tmp_dir, 'fail_if_any = ["agent:ready"]\n')
    assert main(["--fail-if-any", "agent:blocked", ISSUES]) == 0
    write_config(in_tmp_dir, 'fail_if_any = ["agent:blocked"]\n')
    assert main(["--fail-if-any", "agent:ready", ISSUES]) == 3


def test_config_fail_if_any_with_config_only(in_tmp_dir):
    # 判定は出力の絞り込み（設定の only）に左右されない
    write_config(in_tmp_dir, 'only = ["agent:blocked"]\nfail_if_any = ["agent:ready"]\n')
    assert main([ISSUES]) == 3


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (
            'fail_if_any = ["agent:nothing"]\n',
            "エラー: 設定ファイルの fail_if_any に指定できないラベルです: agent:nothing",
        ),
        (
            'fail_if_any = "agent:blocked"\n',
            "エラー: 設定ファイルの fail_if_any には文字列の配列を指定してください",
        ),
        (
            "fail_if_any = [1]\n",
            "エラー: 設定ファイルの fail_if_any には文字列の配列を指定してください",
        ),
    ],
)
def test_invalid_config_fail_if_any_exits_2(in_tmp_dir, capsys, text, message):
    write_config(in_tmp_dir, text)
    assert main([ISSUES]) == 2
    captured = capsys.readouterr()
    assert captured.err.startswith(message)
    assert captured.out == ""


def test_usage_mentions_config_fail_if_any():
    assert "fail_if_any" in USAGE.split("--config で読む設定ファイル")[1]
