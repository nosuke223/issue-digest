import csv
import io

from conftest import DATA, NOW, make_issue

from issue_digest import main
from issue_digest.classifier import classify_issues
from issue_digest.formatter import format_csv


def _rows(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text, newline="")))


def test_format_csv_header_and_order():
    issues = [
        make_issue(1, "A", ["agent:ready"]),
        make_issue(2, "B", ["agent:review"]),
        make_issue(3, "C"),
    ]
    rows = _rows(format_csv(classify_issues(issues)))
    assert rows[0] == ["label", "number", "title", "url"]
    # 分類の順（レビュー待ち → 着手可能 → 未分類）
    assert [(r[0], r[1]) for r in rows[1:]] == [
        ("agent:review", "2"),
        ("agent:ready", "1"),
        ("unclassified", "3"),
    ]
    assert rows[1][3] == "https://github.com/example/repo/issues/2"


def test_format_csv_issue_in_multiple_categories_has_row_per_category():
    issues = [make_issue(1, "A", ["agent:ready", "agent:review"])]
    rows = _rows(format_csv(classify_issues(issues)))
    assert [(r[0], r[1]) for r in rows[1:]] == [("agent:review", "1"), ("agent:ready", "1")]


def test_format_csv_quotes_comma_quote_and_newline():
    title = 'a,b "c"\nd'
    text = format_csv(classify_issues([make_issue(1, title, ["agent:ready"])]))
    assert _rows(text)[1][2] == title
    assert '"a,b ""c""\nd"' in text


def test_format_csv_does_not_shorten_title():
    title = "あ" * 50
    rows = _rows(format_csv(classify_issues([make_issue(1, title)])))
    assert rows[1][2] == title


def test_format_csv_empty_has_only_header():
    assert format_csv(classify_issues([])) == "label,number,title,url\r\n"


def test_main_csv(capsys):
    assert main(["--csv", str(DATA / "issues.json")]) == 0
    rows = _rows(capsys.readouterr().out)
    assert rows[0] == ["label", "number", "title", "url"]
    assert [r[:2] for r in rows[1:]] == [["agent:ready", "1"], ["unclassified", "2"]]


def test_main_csv_with_only_hide_empty_sort_exclude_limit(capsys):
    assert main(["--csv", "--only", "agent:ready", "--hide-empty", str(DATA / "sort.json")]) == 0
    ready = [r[1] for r in _rows(capsys.readouterr().out)[1:]]
    assert ready == ["1", "2", "3", "4", "5", "6"]
    assert (
        main(["--csv", "--only", "agent:ready", "--sort", "updated", str(DATA / "sort.json")]) == 0
    )
    assert [r[1] for r in _rows(capsys.readouterr().out)[1:]] == ["6", "3", "4", "1", "2", "5"]
    assert main(["--csv", "--exclude", "agent:ready", str(DATA / "sort.json")]) == 0
    assert {r[0] for r in _rows(capsys.readouterr().out)[1:]} == {"agent:review"}
    assert main(["--csv", "--only", "agent:ready", "--limit", "2", str(DATA / "sort.json")]) == 0
    assert len(_rows(capsys.readouterr().out)) == 3


def test_main_csv_hide_empty_drops_empty_categories_only(capsys):
    assert main(["--csv", "--hide-empty", str(DATA / "empty.json")]) == 0
    assert capsys.readouterr().out == "label,number,title,url\r\n"


def test_main_csv_ignores_stale_assignees_summary_title(capsys):
    assert main(["--csv", str(DATA / "sort.json")], now=NOW) == 0
    plain = capsys.readouterr().out
    args = ["--csv", "--stale", "7", "--show-assignees", "--summary", "--title", "x"]
    assert main([*args, str(DATA / "sort.json")], now=NOW) == 0
    assert capsys.readouterr().out == plain


def test_main_csv_output_file(capsys, tmp_path):
    out = tmp_path / "digest.csv"
    assert main(["--csv", "--output", str(out), str(DATA / "issues.json")]) == 0
    assert capsys.readouterr().out == ""
    data = out.read_bytes()
    assert data.startswith(b"label,number,title,url\r\n")
    assert b"\r\r" not in data


def test_main_csv_and_json_is_error(capsys):
    assert main(["--json", "--csv", str(DATA / "issues.json")]) == 2
    captured = capsys.readouterr()
    assert captured.err == "エラー: --json と --csv は同時に指定できません\n"
    assert captured.out == ""


def test_main_usage_mentions_csv(capsys):
    assert main(["--help"]) == 0
    assert "--csv" in capsys.readouterr().out
