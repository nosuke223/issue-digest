import io
import json
import tomllib
from datetime import UTC, datetime
from importlib.metadata import version
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


def test_main_summary(capsys):
    assert main(["--summary", str(DATA / "issues.json")]) == 0
    out = capsys.readouterr().out
    assert out.startswith(
        "# Issue ダイジェスト（全 2 件）\n\n"
        "判断待ち 0 / 中断 0 / レビュー待ち 0 / 作業中 0 / 着手可能 1 / 未分類 1\n\n"
    )


def test_main_summary_with_only_and_hide_empty(capsys):
    assert (
        main(["--summary", "--hide-empty", "--only", "agent:ready", str(DATA / "issues.json")]) == 0
    )
    out = capsys.readouterr().out
    assert "判断待ち 0 / 中断 0 / レビュー待ち 0 / 作業中 0 / 着手可能 1 / 未分類 1\n" in out
    assert "## 未分類" not in out


def test_main_without_summary_unchanged(capsys):
    assert main([str(DATA / "issues.json")]) == 0
    assert "判断待ち 0 /" not in capsys.readouterr().out


def test_main_usage_mentions_summary(capsys):
    assert main([]) == 2
    assert "--summary" in capsys.readouterr().err


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


def test_main_show_assignees(capsys):
    assert main(["--show-assignees", str(DATA / "assignees.json")]) == 0
    out = capsys.readouterr().out
    assert "担当者が2人の Issue（担当: @bob, @alice）\n" in out
    assert "担当者が空の Issue\n" in out
    assert "assignees がない Issue\n" in out
    assert "assignees が null の Issue\n" in out


def test_main_show_assignees_with_stale_order(capsys):
    args = ["--stale", "7", "--show-assignees", str(DATA / "assignees.json")]
    assert main(args, now=NOW) == 0
    assert "担当者が2人の Issue（13日更新なし）（担当: @bob, @alice）\n" in capsys.readouterr().out


def test_main_without_show_assignees_unchanged(capsys):
    assert main([str(DATA / "assignees.json")]) == 0
    assert "（担当:" not in capsys.readouterr().out


def test_main_show_assignees_without_assignees_field_does_not_fail(capsys):
    assert main(["--show-assignees", str(DATA / "issues.json")]) == 0
    assert "担当" not in capsys.readouterr().out


def test_main_json_show_assignees(capsys):
    assert main(["--json", "--show-assignees", str(DATA / "assignees.json")]) == 0
    body = json.loads(capsys.readouterr().out)
    by_title = {i["title"]: i for c in body["categories"] for i in c["issues"]}
    assert by_title["担当者が2人の Issue"]["assignees"] == ["bob", "alice"]
    assert by_title["担当者が空の Issue"]["assignees"] == []
    assert by_title["assignees がない Issue"]["assignees"] == []
    assert by_title["assignees が null の Issue"]["assignees"] == []


def test_main_json_without_show_assignees_has_no_assignees(capsys):
    assert main(["--json", str(DATA / "assignees.json")]) == 0
    assert '"assignees":' not in capsys.readouterr().out


def test_main_usage_mentions_show_assignees(capsys):
    assert main([]) == 2
    assert "--show-assignees" in capsys.readouterr().err


def issue_numbers_in_output(out: str) -> list[int]:
    lines = [line for line in out.splitlines() if line.startswith("- [#")]
    return [int(line.removeprefix("- [#").split("]")[0]) for line in lines]


def test_main_sort_updated_orders_oldest_first(capsys):
    assert main(["--sort", "updated", str(DATA / "sort.json")]) == 0
    # レビュー待ち → 着手可能の順。各分類は古い順、同時刻は番号順、updatedAt なしは末尾
    assert issue_numbers_in_output(capsys.readouterr().out) == [8, 7, 6, 3, 4, 1, 2, 5]


def test_main_without_sort_orders_by_number(capsys):
    assert main([str(DATA / "sort.json")]) == 0
    assert issue_numbers_in_output(capsys.readouterr().out) == [7, 8, 1, 2, 3, 4, 5, 6]


def test_main_sort_with_other_options(capsys):
    args = ["--sort", "updated", "--hide-empty", "--only", "agent:ready", "--stale", "7"]
    assert main([*args, str(DATA / "sort.json")], now=NOW) == 0
    out = capsys.readouterr().out
    assert issue_numbers_in_output(out) == [6, 3, 4, 1, 2, 5]
    assert "(agent:review)" not in out
    assert "先頭の古い Issue（番号6）（52日更新なし）" in out


def test_main_sort_reads_stdin(capsys, monkeypatch):
    text = (DATA / "sort.json").read_text(encoding="utf-8")
    monkeypatch.setattr("sys.stdin", io.StringIO(text))
    assert main(["--sort", "updated", "-"]) == 0
    assert issue_numbers_in_output(capsys.readouterr().out) == [8, 7, 6, 3, 4, 1, 2, 5]


@pytest.mark.parametrize("value", ["created", "", "Updated", "asc"])
def test_main_sort_invalid_value(capsys, value):
    assert main(["--sort", value, str(DATA / "sort.json")]) == 2
    captured = capsys.readouterr()
    assert "--sort" in captured.err
    assert captured.out == ""


def test_main_sort_without_value_shows_usage(capsys):
    assert main([str(DATA / "sort.json"), "--sort"]) == 2
    captured = capsys.readouterr()
    assert "使い方" in captured.err
    assert "--sort" in captured.err
    assert captured.out == ""


def test_main_sort_with_show_assignees(capsys):
    assert main(["--sort", "updated", "--show-assignees", str(DATA / "sort.json")]) == 0
    assert issue_numbers_in_output(capsys.readouterr().out) == [8, 7, 6, 3, 4, 1, 2, 5]


def test_main_limit_markdown(capsys):
    assert main(["--limit", "2", str(DATA / "sort.json")]) == 0
    out = capsys.readouterr().out
    assert issue_numbers_in_output(out) == [7, 8, 1, 2]
    # 見出しの件数は全件のまま。省略がある分類だけ「ほか N 件」を出す
    assert "## 着手可能 (agent:ready) - 6件" in out
    assert "- ほか 4 件" in out
    assert out.count("- ほか") == 1


def test_main_limit_after_sort(capsys):
    assert main(["--limit", "2", "--sort", "updated", str(DATA / "sort.json")]) == 0
    assert issue_numbers_in_output(capsys.readouterr().out) == [8, 7, 6, 3]


def test_main_limit_larger_than_count_omits_nothing(capsys):
    assert main(["--limit", "100", str(DATA / "sort.json")]) == 0
    out = capsys.readouterr().out
    assert issue_numbers_in_output(out) == [7, 8, 1, 2, 3, 4, 5, 6]
    assert "ほか" not in out


def test_main_without_limit_unchanged(capsys):
    assert main([str(DATA / "sort.json")]) == 0
    out = capsys.readouterr().out
    assert issue_numbers_in_output(out) == [7, 8, 1, 2, 3, 4, 5, 6]
    assert "ほか" not in out


def test_main_limit_json(capsys):
    assert main(["--json", "--limit", "2", "--sort", "updated", str(DATA / "sort.json")]) == 0
    body = _json_out(capsys)
    by_label = {c["label"]: c for c in body["categories"]}
    ready = by_label["agent:ready"]
    assert [i["number"] for i in ready["issues"]] == [6, 3]
    assert ready["count"] == 6
    assert ready["omitted"] == 4
    review = by_label["agent:review"]
    assert [i["number"] for i in review["issues"]] == [8, 7]
    assert review["omitted"] == 0
    # 0件の分類にも omitted を付ける
    assert by_label["agent:ready"]["omitted"] == 4
    assert by_label["agent:blocked"]["omitted"] == 0
    assert body["total"] == 8


def test_main_json_without_limit_has_no_omitted(capsys):
    assert main(["--json", str(DATA / "sort.json")]) == 0
    assert all("omitted" not in c for c in _json_out(capsys)["categories"])


@pytest.mark.parametrize("value", ["0", "-1", "abc", "1.5", "", "１"])
def test_main_limit_invalid_value(capsys, value):
    assert main(["--limit", value, str(DATA / "sort.json")]) == 2
    captured = capsys.readouterr()
    assert captured.err == f"エラー: --limit には1以上の整数を指定してください: {value}\n"
    assert captured.out == ""


def test_main_limit_without_value_shows_usage(capsys):
    assert main([str(DATA / "sort.json"), "--limit"]) == 2
    captured = capsys.readouterr()
    assert "使い方" in captured.err
    assert captured.out == ""


def test_main_usage_mentions_limit(capsys):
    assert main(["--help"]) == 0
    assert "--limit" in capsys.readouterr().out


def test_main_output_writes_same_content_as_stdout(capsys, tmp_path):
    assert main([str(DATA / "issues.json")]) == 0
    expected = capsys.readouterr().out
    out_file = tmp_path / "out.md"
    assert main(["--output", str(out_file), str(DATA / "issues.json")]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert out_file.read_bytes() == expected.encode("utf-8")


def test_main_output_overwrites_existing_file(tmp_path):
    out_file = tmp_path / "out.md"
    out_file.write_text("古い内容" * 1000, encoding="utf-8")
    assert main([str(DATA / "empty.json"), "--output", str(out_file)]) == 0
    assert out_file.read_text(encoding="utf-8").startswith("# Issue ダイジェスト（全 0 件）\n")
    assert "古い内容" not in out_file.read_text(encoding="utf-8")


def test_main_output_with_other_options(capsys, tmp_path):
    out_file = tmp_path / "out.md"
    args = ["--stale", "7", "--hide-empty", "--only", "agent:ready"]
    assert main([*args, "--output", str(out_file), str(DATA / "stale.json")], now=NOW) == 0
    assert capsys.readouterr().out == ""
    text = out_file.read_text(encoding="utf-8")
    assert "古い Issue（13日更新なし）" in text
    assert "## 未分類" not in text
    assert "(agent:blocked)" not in text


def test_main_output_with_json_writes_json(capsys, tmp_path):
    assert main(["--json", str(DATA / "issues.json")]) == 0
    expected = capsys.readouterr().out
    out_file = tmp_path / "out.json"
    assert main(["--json", "--output", str(out_file), str(DATA / "issues.json")]) == 0
    assert capsys.readouterr().out == ""
    assert out_file.read_bytes() == expected.encode("utf-8")
    assert json.loads(expected)["total"] >= 0


def test_main_output_reads_stdin(capsys, monkeypatch, tmp_path):
    text = (DATA / "issues.json").read_text(encoding="utf-8")
    monkeypatch.setattr("sys.stdin", io.StringIO(text))
    out_file = tmp_path / "out.md"
    assert main(["--output", str(out_file), "-"]) == 0
    assert capsys.readouterr().out == ""
    assert "## 着手可能 (agent:ready) - 1件" in out_file.read_text(encoding="utf-8")


def test_main_output_unwritable_path(capsys, tmp_path):
    out_file = tmp_path / "no-such-dir" / "out.md"
    assert main(["--output", str(out_file), str(DATA / "issues.json")]) == 1
    captured = capsys.readouterr()
    assert "書き出せません" in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""
    assert not out_file.parent.exists()


def test_main_output_without_value_shows_usage(capsys):
    assert main([str(DATA / "issues.json"), "--output"]) == 2
    captured = capsys.readouterr()
    assert "使い方" in captured.err
    assert captured.out == ""


def test_main_output_not_created_when_input_fails(tmp_path):
    out_file = tmp_path / "out.md"
    assert main(["--output", str(out_file), str(DATA / "missing.json")]) == 1
    assert not out_file.exists()


def test_main_usage_mentions_output(capsys):
    assert main([]) == 2
    assert "--output" in capsys.readouterr().err


def test_main_version_ignores_output(capsys, tmp_path):
    out_file = tmp_path / "out.md"
    assert main(["--version", "--output", str(out_file)]) == 0
    assert capsys.readouterr().out == f"issue-digest {version('issue-digest')}\n"
    assert not out_file.exists()


def test_main_output_with_show_assignees(capsys, tmp_path):
    out_file = tmp_path / "out.md"
    assert main(["--show-assignees", "--output", str(out_file), str(DATA / "assignees.json")]) == 0
    assert capsys.readouterr().out == ""
    assert "担当者が2人の Issue（担当: @bob, @alice）\n" in out_file.read_text(encoding="utf-8")


def test_main_output_with_sort(tmp_path):
    out_file = tmp_path / "out.md"
    assert main(["--sort", "updated", "--output", str(out_file), str(DATA / "sort.json")]) == 0
    assert issue_numbers_in_output(out_file.read_text(encoding="utf-8")) == [8, 7, 6, 3, 4, 1, 2, 5]


def test_main_version(capsys):
    assert main(["--version"]) == 0
    assert capsys.readouterr().out == f"issue-digest {version('issue-digest')}\n"


def test_main_version_matches_pyproject(capsys):
    text = (Path(__file__).parent.parent / "pyproject.toml").read_text(encoding="utf-8")
    expected = tomllib.loads(text)["project"]["version"]
    assert main(["--version"]) == 0
    assert capsys.readouterr().out == f"issue-digest {expected}\n"


def test_main_version_ignores_other_args(capsys):
    args = ["--only", "agent:nope", "--stale", "x", str(DATA / "missing.json"), "--version"]
    assert main(args) == 0
    captured = capsys.readouterr()
    assert captured.out == f"issue-digest {version('issue-digest')}\n"
    assert captured.err == ""


def _json_out(capsys) -> dict:
    return json.loads(capsys.readouterr().out)


def test_main_json_shape(capsys):
    assert main(["--json", str(DATA / "issues.json")]) == 0
    out = capsys.readouterr().out
    assert out.endswith("}\n")
    assert "ラベルなしの Issue B" in out  # 日本語はエスケープしない
    assert '\n  "total": 2,\n  "categories": [\n    {\n' in out  # インデントは2
    data = json.loads(out)
    assert data["total"] == 2
    assert [c["label"] for c in data["categories"]] == [
        "agent:needs-decision",
        "agent:blocked",
        "agent:review",
        "agent:working",
        "agent:ready",
        "unclassified",
    ]
    ready = data["categories"][4]
    assert ready == {
        "label": "agent:ready",
        "title": "着手可能",
        "count": 1,
        "issues": [
            {
                "number": 1,
                "title": "サンプルの Issue A",
                "url": "https://github.com/example/repo/issues/1",
            }
        ],
    }
    assert data["categories"][5]["title"] == "未分類"
    assert data["categories"][0]["issues"] == []


def test_main_json_hide_empty(capsys):
    assert main(["--json", "--hide-empty", str(DATA / "issues.json")]) == 0
    data = _json_out(capsys)
    assert [c["label"] for c in data["categories"]] == ["agent:ready", "unclassified"]


def test_main_json_only_keeps_total(capsys):
    assert main(["--json", "--only", "agent:ready", str(DATA / "issues.json")]) == 0
    data = _json_out(capsys)
    assert data["total"] == 2
    assert [c["label"] for c in data["categories"]] == ["agent:ready"]


def test_main_json_only_with_hide_empty(capsys):
    args = ["--json", "--only", "agent:blocked", "--only", "agent:ready", "--hide-empty"]
    assert main([*args, str(DATA / "issues.json")]) == 0
    data = _json_out(capsys)
    assert [c["label"] for c in data["categories"]] == ["agent:ready"]


def test_main_json_stale_adds_days_only_to_marked(capsys):
    assert main(["--json", "--stale", "7", str(DATA / "stale.json")], now=NOW) == 0
    data = _json_out(capsys)
    issues = {i["number"]: i for c in data["categories"] for i in c["issues"]}
    assert issues[1]["stale_days"] == 13
    assert issues[2]["stale_days"] == 7
    assert "stale_days" not in issues[3]
    assert "stale_days" not in issues[4]


def test_main_json_stale_with_hide_empty_and_only(capsys):
    args = ["--json", "--stale", "7", "--hide-empty", "--only", "agent:ready"]
    assert main([*args, str(DATA / "stale.json")], now=NOW) == 0
    data = _json_out(capsys)
    assert data["total"] == 4
    assert [c["label"] for c in data["categories"]] == ["agent:ready"]
    assert data["categories"][0]["issues"][0]["stale_days"] == 13


def test_main_json_with_sort_orders_oldest_first(capsys):
    assert main(["--json", "--sort", "updated", str(DATA / "sort.json")]) == 0
    data = _json_out(capsys)
    numbers = [i["number"] for c in data["categories"] for i in c["issues"]]
    assert numbers == [8, 7, 6, 3, 4, 1, 2, 5]


def test_main_json_without_stale_has_no_stale_days(capsys):
    assert main(["--json", str(DATA / "stale.json")], now=NOW) == 0
    assert "stale_days" not in capsys.readouterr().out


def test_main_json_reads_stdin(capsys, monkeypatch):
    text = (DATA / "issues.json").read_text(encoding="utf-8")
    monkeypatch.setattr("sys.stdin", io.StringIO(text))
    assert main(["--json", "-"]) == 0
    assert _json_out(capsys)["total"] == 2


def test_main_json_ignores_summary(capsys):
    path = str(DATA / "issues.json")
    assert main(["--json", path]) == 0
    expected = capsys.readouterr().out
    assert main(["--json", "--summary", path]) == 0
    out = capsys.readouterr().out
    assert out == expected
    json.loads(out)


def test_main_without_json_still_markdown(capsys):
    assert main([str(DATA / "issues.json")]) == 0
    assert capsys.readouterr().out.startswith("# Issue ダイジェスト")


def test_main_usage_mentions_json(capsys):
    assert main([]) == 2
    assert "--json" in capsys.readouterr().err


def test_main_usage_mentions_version(capsys):
    assert main([]) == 2
    assert "--version" in capsys.readouterr().err


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


def test_main_unknown_option_shows_usage(capsys):
    assert main(["--foo", str(DATA / "issues.json")]) == 2
    captured = capsys.readouterr()
    assert "使い方" in captured.err
    assert captured.out == ""


def test_main_abbreviated_option_is_rejected(capsys):
    assert main(["--hide", str(DATA / "issues.json")]) == 2
    assert "使い方" in capsys.readouterr().err


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_main_help_prints_usage_to_stdout(capsys, flag):
    assert main([flag]) == 0
    captured = capsys.readouterr()
    assert "使い方" in captured.out
    assert captured.err == ""


def test_main_stale_accepts_equals_form(capsys):
    now = datetime(2026, 1, 1, tzinfo=UTC)
    assert main(["--stale=7", str(DATA / "issues.json")], now=now) == 0
    equals_out = capsys.readouterr().out
    assert main(["--stale", "7", str(DATA / "issues.json")], now=now) == 0
    assert capsys.readouterr().out == equals_out
