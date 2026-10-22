from pathlib import Path

from issue_digest import main

DATA = Path(__file__).parent / "data"


def test_main_prints_digest(capsys):
    assert main([str(DATA / "issues.json")]) == 0
    out = capsys.readouterr().out
    assert out.startswith("# Issue ダイジェスト\n")
    assert "## 着手可能 (agent:ready) - 1件\n\n- #1 サンプルの Issue A\n" in out
    assert "## 未分類 - 1件\n\n- #2 ラベルなしの Issue B\n" in out


def test_main_prints_none_for_empty_input(capsys):
    assert main([str(DATA / "empty.json")]) == 0
    out = capsys.readouterr().out
    assert out.count("なし") == 6


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


def test_main_without_args_shows_usage(capsys):
    assert main([]) != 0
    captured = capsys.readouterr()
    assert "使い方" in captured.err
    assert captured.out == ""


def test_main_with_too_many_args_shows_usage(capsys):
    assert main(["a.json", "b.json"]) != 0
    assert "使い方" in capsys.readouterr().err
