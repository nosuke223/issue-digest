import io
from datetime import UTC, datetime
from pathlib import Path

import pytest

from issue_digest import main

DATA = Path(__file__).parent / "data"


def test_main_prints_digest(capsys):
    assert main([str(DATA / "issues.json")]) == 0
    out = capsys.readouterr().out
    assert out.startswith("# Issue ダイジェスト（全 2 件）\n")
    assert (
        "## 着手可能 (agent:ready) - 1件\n\n"
        "- [#1](https://github.com/example/repo/issues/1) サンプルの Issue A\n"
    ) in out
    assert (
        "## 未分類 - 1件\n\n- [#2](https://github.com/example/repo/issues/2) ラベルなしの Issue B\n"
    ) in out


def test_main_prints_none_for_empty_input(capsys):
    assert main([str(DATA / "empty.json")]) == 0
    out = capsys.readouterr().out
    assert out.count("なし") == 6


def test_main_hide_empty(capsys):
    assert main(["--hide-empty", str(DATA / "issues.json")]) == 0
    out = capsys.readouterr().out
    assert "なし" not in out.splitlines()
    assert "(agent:blocked)" not in out
    assert (
        "## 着手可能 (agent:ready) - 1件\n\n"
        "- [#1](https://github.com/example/repo/issues/1) サンプルの Issue A\n"
    ) in out
    assert (
        "## 未分類 - 1件\n\n- [#2](https://github.com/example/repo/issues/2) ラベルなしの Issue B\n"
    ) in out


def test_main_hide_empty_after_path(capsys):
    assert main([str(DATA / "empty.json"), "--hide-empty"]) == 0
    assert capsys.readouterr().out == "# Issue ダイジェスト（全 0 件）\n"


def test_main_without_hide_empty_unchanged(capsys):
    assert main([str(DATA / "issues.json")]) == 0
    assert "## 中断 (agent:blocked) - 0件\n\nなし\n" in capsys.readouterr().out


def test_main_hide_empty_only_shows_usage(capsys):
    assert main(["--hide-empty"]) == 2
    assert "使い方" in capsys.readouterr().err


def test_main_only_shows_single_category(capsys):
    assert main(["--only", "agent:ready", str(DATA / "issues.json")]) == 0
    out = capsys.readouterr().out
    assert out.startswith("# Issue ダイジェスト（全 2 件）\n")
    assert "## 着手可能 (agent:ready) - 1件" in out
    assert "(agent:blocked)" not in out
    assert "## 未分類" not in out


def test_main_only_multiple(capsys):
    assert main(["--only", "agent:ready", "--only", "unclassified", str(DATA / "issues.json")]) == 0
    out = capsys.readouterr().out
    assert "## 着手可能 (agent:ready) - 1件" in out
    assert "## 未分類 - 1件" in out
    assert "(agent:blocked)" not in out


def test_main_only_empty_category_shows_none(capsys):
    assert main(["--only", "agent:needs-decision", str(DATA / "issues.json")]) == 0
    out = capsys.readouterr().out
    assert "## 判断待ち (agent:needs-decision) - 0件\n\nなし\n" in out
    assert "## 着手可能" not in out


def test_main_only_with_hide_empty(capsys):
    args = ["--only", "agent:needs-decision", "--only", "agent:ready", "--hide-empty"]
    assert main([*args, str(DATA / "issues.json")]) == 0
    out = capsys.readouterr().out
    assert "## 着手可能 (agent:ready) - 1件" in out
    assert "agent:needs-decision" not in out


def test_main_only_unknown_label(capsys):
    assert main(["--only", "agent:nope", str(DATA / "issues.json")]) == 2
    captured = capsys.readouterr()
    assert "agent:nope" in captured.err
    assert captured.out == ""


def test_main_only_without_value_shows_usage(capsys):
    assert main([str(DATA / "issues.json"), "--only"]) == 2
    assert "使い方" in capsys.readouterr().err


NOW = datetime(2026, 10, 23, 12, 0, 0, tzinfo=UTC)


def test_main_stale_marks_only_old_issues(capsys):
    assert main(["--stale", "7", str(DATA / "stale.json")], now=NOW) == 0
    out = capsys.readouterr().out
    assert "古い Issue（13日更新なし）\n" in out
    assert "ちょうど7日の Issue（7日更新なし）\n" in out
    assert "7日に1秒足りない Issue\n" in out
    assert "updatedAt がない Issue\n" in out


def test_main_stale_zero_marks_all_with_updated_at(capsys):
    assert main(["--stale", "0", str(DATA / "stale.json")], now=NOW) == 0
    out = capsys.readouterr().out
    assert "7日に1秒足りない Issue（6日更新なし）\n" in out
    assert "updatedAt がない Issue\n" in out


def test_main_without_stale_unchanged(capsys):
    assert main([str(DATA / "stale.json")], now=NOW) == 0
    assert "更新なし" not in capsys.readouterr().out


def test_main_stale_with_hide_empty_and_only(capsys):
    args = ["--stale", "7", "--hide-empty", "--only", "agent:ready"]
    assert main([*args, str(DATA / "stale.json")], now=NOW) == 0
    out = capsys.readouterr().out
    assert "古い Issue（13日更新なし）" in out
    assert "## 未分類" not in out
    assert "(agent:blocked)" not in out


def test_main_stale_reads_stdin(capsys, monkeypatch):
    text = (DATA / "stale.json").read_text(encoding="utf-8")
    monkeypatch.setattr("sys.stdin", io.StringIO(text))
    assert main(["--stale", "7", "-"], now=NOW) == 0
    assert "古い Issue（13日更新なし）" in capsys.readouterr().out


@pytest.mark.parametrize("value", ["-1", "abc", "1.5", "", "１"])
def test_main_stale_invalid_value(capsys, value):
    assert main(["--stale", value, str(DATA / "stale.json")], now=NOW) == 2
    captured = capsys.readouterr()
    assert "--stale" in captured.err
    assert captured.out == ""


def test_main_stale_without_value_shows_usage(capsys):
    assert main([str(DATA / "stale.json"), "--stale"]) == 2
    assert "使い方" in capsys.readouterr().err


def test_main_invalid_updated_at(capsys, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(
        '[{"number": 1, "title": "t", "labels": [], "url": "u", "updatedAt": "xx"}]',
        encoding="utf-8",
    )
    assert main(["--stale", "7", str(bad)], now=NOW) == 1
    assert "読み込めません" in capsys.readouterr().err


def test_main_missing_file(capsys):
    assert main([str(DATA / "missing.json")]) == 1
    captured = capsys.readouterr()
    assert "ファイルが見つかりません" in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_main_invalid_json(capsys, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    assert main([str(bad)]) == 1
    assert "読み込めません" in capsys.readouterr().err


def test_main_reads_stdin(capsys, monkeypatch):
    text = (DATA / "issues.json").read_text(encoding="utf-8")
    monkeypatch.setattr("sys.stdin", io.StringIO(text))
    assert main(["-"]) == 0
    stdin_out = capsys.readouterr().out
    assert main([str(DATA / "issues.json")]) == 0
    assert stdin_out == capsys.readouterr().out


def test_main_invalid_json_on_stdin(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert main(["-"]) == 1
    captured = capsys.readouterr()
    assert "標準入力を読み込めません" in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_main_usage_mentions_stdin(capsys):
    assert main([]) == 2
    assert "-" in capsys.readouterr().err


def test_main_without_args_shows_usage(capsys):
    assert main([]) != 0
    captured = capsys.readouterr()
    assert "使い方" in captured.err
    assert captured.out == ""


def test_main_with_too_many_args_shows_usage(capsys):
    assert main(["a.json", "b.json"]) != 0
    assert "使い方" in capsys.readouterr().err
