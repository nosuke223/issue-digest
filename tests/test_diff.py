import json

import pytest
from conftest import DATA, json_out, make_issue

from issue_digest import main
from issue_digest.classifier import classify_issues
from issue_digest.diff import (
    DiffEntry,
    InvalidPreviousError,
    PreviousIssue,
    compute_diff,
    load_previous,
    parse_previous,
)

PREVIOUS = str(DATA / "diff_previous.json")
CURRENT = str(DATA / "diff_current.json")


def _url(number: int) -> str:
    return f"https://github.com/example/repo/issues/{number}"


def _previous(number: int, *categories: str) -> PreviousIssue:
    return PreviousIssue(number, f"Issue {number}", _url(number), categories)


def test_load_previous_collects_categories_per_issue():
    previous = load_previous(PREVIOUS)
    assert sorted(previous) == sorted(_url(n) for n in (1, 2, 3, 4))
    assert previous[_url(4)].categories == ("agent:working", "agent:ready")
    assert previous[_url(3)] == PreviousIssue(3, "片付いた Issue *C*", _url(3), ("agent:review",))


def _by_key(*issues: PreviousIssue) -> dict[str, PreviousIssue]:
    return {issue.url.lower(): issue for issue in issues}


def test_compute_diff_single_category_move():
    previous = _by_key(_previous(1, "agent:ready"))
    classified = classify_issues([make_issue(1, labels=["agent:review"])])
    diff = compute_diff(previous, classified)
    assert diff.added == [] and diff.removed == []
    assert diff.moved == [DiffEntry(1, "Issue 1", _url(1), ("agent:ready",), ("agent:review",))]


def test_compute_diff_same_category_set_is_not_moved():
    previous = _by_key(_previous(1, "agent:working", "agent:ready"))
    classified = classify_issues([make_issue(1, labels=["agent:ready", "agent:working"])])
    assert compute_diff(previous, classified).is_empty()


def test_compute_diff_sorted_by_number():
    previous = _by_key(*(_previous(n, "agent:ready") for n in (9, 7)))
    classified = classify_issues([make_issue(n) for n in (6, 2)])
    diff = compute_diff(previous, classified)
    assert [e.number for e in diff.added] == [2, 6]
    assert [e.number for e in diff.removed] == [7, 9]


@pytest.mark.parametrize(
    "text",
    [
        "[]",
        "{}",
        '{"total": 0}',
        '{"total": 0, "categories": {}}',
        '{"total": 0, "categories": [1]}',
        '{"total": 0, "categories": [{"label": "bug", "issues": []}]}',
        '{"total": 0, "categories": [{"label": "agent:ready"}]}',
        '{"total": 0, "categories": [{"label": "agent:ready", "issues": [1]}]}',
        '{"total": 0, "categories": [{"label": "agent:ready", "issues": [{"number": 1}]}]}',
        '{"total": true, "categories": []}',
        '{"total": 1, "categories": [{"label": "agent:ready",'
        ' "issues": [{"number": "1", "title": "t", "url": "u"}]}]}',
    ],
)
def test_parse_previous_rejects_other_shapes(text):
    with pytest.raises(InvalidPreviousError):
        parse_previous(text)


EXPECTED_MARKDOWN = (
    "\n## 前回からの変化\n\n"
    "### 新しい Issue - 1件\n\n"
    f"- [example/repo#5]({_url(5)}) 新しい Issue E\n\n"
    "### なくなった Issue - 1件\n\n"
    f"- [example/repo#3]({_url(3)}) 片付いた Issue \\*C\\*\n\n"
    "### 分類が変わった Issue - 1件\n\n"
    f"- [example/repo#4]({_url(4)}) 複数の分類の Issue D: 作業中, 着手可能 → レビュー待ち\n"
)


def test_main_diff_markdown(capsys):
    assert main(["--diff", PREVIOUS, CURRENT]) == 0
    out = capsys.readouterr().out
    assert out.endswith(EXPECTED_MARKDOWN)
    # 「前回からの変化」より前は --diff なしと同じ
    body = out.removesuffix(EXPECTED_MARKDOWN)
    assert main([CURRENT]) == 0
    assert capsys.readouterr().out == body


def test_main_diff_markdown_empty_sections_show_none(capsys, tmp_path):
    previous = tmp_path / "previous.json"
    assert main(["--json", "--output", str(previous), str(DATA / "issues.json")]) == 0
    current = tmp_path / "current.json"
    data = json.loads((DATA / "issues.json").read_text(encoding="utf-8"))
    current.write_text(json.dumps(data[:1]), encoding="utf-8")
    assert main(["--diff", str(previous), str(current)]) == 0
    out = capsys.readouterr().out
    assert out.endswith(
        "### 新しい Issue - 0件\n\nなし\n\n"
        "### なくなった Issue - 1件\n\n"
        f"- [example/repo#2]({_url(2)}) ラベルなしの Issue B\n\n"
        "### 分類が変わった Issue - 0件\n\nなし\n"
    )


def test_main_diff_no_change(capsys, tmp_path):
    previous = tmp_path / "previous.json"
    assert main(["--json", "--output", str(previous), str(DATA / "issues.json")]) == 0
    assert main(["--diff", str(previous), str(DATA / "issues.json")]) == 0
    assert capsys.readouterr().out.endswith("\n## 前回からの変化\n\n変化なし\n")


def test_main_diff_json(capsys):
    assert main(["--json", "--diff", PREVIOUS, CURRENT]) == 0
    data = json_out(capsys)
    assert data["diff"] == {
        "added": [
            {
                "number": 5,
                "title": "新しい Issue E",
                "url": _url(5),
                "repository": "example/repo",
                "categories": ["agent:needs-decision", "agent:blocked"],
            }
        ],
        "removed": [
            {
                "number": 3,
                "title": "片付いた Issue *C*",
                "url": _url(3),
                "repository": "example/repo",
                "categories": ["agent:review"],
            }
        ],
        "moved": [
            {
                "number": 4,
                "title": "複数の分類の Issue D",
                "url": _url(4),
                "repository": "example/repo",
                "from": ["agent:working", "agent:ready"],
                "to": ["agent:review"],
            }
        ],
    }
    assert list(data) == ["total", "categories", "diff"]


def test_main_diff_json_no_change(capsys, tmp_path):
    previous = tmp_path / "previous.json"
    assert main(["--json", "--output", str(previous), str(DATA / "issues.json")]) == 0
    assert main(["--json", "--diff", str(previous), str(DATA / "issues.json")]) == 0
    assert json_out(capsys)["diff"] == {"added": [], "removed": [], "moved": []}


def test_main_diff_output_can_be_next_previous(capsys, tmp_path):
    previous = tmp_path / "previous.json"
    assert main(["--json", "--diff", PREVIOUS, "--output", str(previous), CURRENT]) == 0
    assert main(["--diff", str(previous), CURRENT]) == 0
    assert capsys.readouterr().out.endswith("変化なし\n")


def test_main_diff_compares_all_categories_regardless_of_only(capsys):
    assert main(["--only", "agent:ready", "--hide-empty", "--diff", PREVIOUS, CURRENT]) == 0
    assert capsys.readouterr().out.endswith(EXPECTED_MARKDOWN)


def test_main_diff_compares_all_categories_regardless_of_config(capsys, tmp_path):
    config = tmp_path / "config.toml"
    config.write_text('hide_empty = true\nonly = ["agent:ready"]\n', encoding="utf-8")
    assert main(["--config", str(config), "--diff", PREVIOUS, CURRENT]) == 0
    assert capsys.readouterr().out.endswith(EXPECTED_MARKDOWN)


def test_main_diff_compares_all_categories_regardless_of_config_exclude(capsys, tmp_path):
    config = tmp_path / "config.toml"
    config.write_text(
        'exclude = ["agent:ready", "agent:working", "agent:review", "unclassified"]\n',
        encoding="utf-8",
    )
    assert main(["--config", str(config), "--diff", PREVIOUS, CURRENT]) == 0
    assert capsys.readouterr().out.endswith(EXPECTED_MARKDOWN)


def _write_issues(path, issues):
    path.write_text(json.dumps(issues), encoding="utf-8")
    return str(path)


def _issue(number, labels, updated_at):
    return {
        "number": number,
        "title": f"Issue {number}",
        "labels": [{"name": label} for label in labels],
        "url": _url(number),
        "updatedAt": updated_at,
    }


def test_main_diff_previous_with_only_reports_missing_issues_as_added_or_moved(capsys, tmp_path):
    issues = _write_issues(
        tmp_path / "issues.json",
        [
            _issue(1, ["agent:ready"], "2026-10-02T00:00:00Z"),
            _issue(2, ["agent:review"], "2026-10-02T00:00:00Z"),
            _issue(3, ["agent:working", "agent:ready"], "2026-10-02T00:00:00Z"),
        ],
    )
    previous = tmp_path / "previous.json"
    assert main(["--json", "--only", "agent:ready", "--output", str(previous), issues]) == 0
    assert main(["--json", "--diff", str(previous), issues]) == 0
    diff = json_out(capsys)["diff"]
    assert [i["number"] for i in diff["added"]] == [2]
    assert diff["removed"] == []
    assert [(i["number"], i["from"], i["to"]) for i in diff["moved"]] == [
        (3, ["agent:ready"], ["agent:working", "agent:ready"])
    ]


def test_main_diff_previous_with_since_reports_missing_issues_as_added(capsys, tmp_path):
    issues = _write_issues(
        tmp_path / "issues.json",
        [
            _issue(1, ["agent:ready"], "2026-09-01T00:00:00Z"),
            _issue(2, ["agent:review"], "2026-10-02T00:00:00Z"),
        ],
    )
    previous = tmp_path / "previous.json"
    assert main(["--json", "--since", "2026-10-01", "--output", str(previous), issues]) == 0
    assert main(["--json", "--diff", str(previous), issues]) == 0
    diff = json_out(capsys)["diff"]
    assert [i["number"] for i in diff["added"]] == [1]
    assert diff["removed"] == []
    assert diff["moved"] == []


def test_main_diff_uses_config_headings(capsys, tmp_path):
    config = tmp_path / "config.toml"
    config.write_text('[headings]\n"agent:review" = "確認待ち"\n', encoding="utf-8")
    assert main(["--config", str(config), "--diff", PREVIOUS, CURRENT]) == 0
    assert capsys.readouterr().out.endswith(
        f"- [example/repo#4]({_url(4)}) 複数の分類の Issue D: 作業中, 着手可能 → 確認待ち\n"
    )


def test_main_without_diff_has_no_diff(capsys):
    assert main(["--json", CURRENT]) == 0
    assert "diff" not in json_out(capsys)
    assert main([CURRENT]) == 0
    assert "前回からの変化" not in capsys.readouterr().out


def test_main_diff_ignored_with_csv(capsys, tmp_path):
    assert main(["--csv", "--diff", str(tmp_path / "missing.json"), CURRENT]) == 0
    out = capsys.readouterr().out
    assert main(["--csv", CURRENT]) == 0
    assert capsys.readouterr().out == out


def test_main_diff_missing_file(capsys, tmp_path):
    missing = tmp_path / "missing.json"
    assert main(["--diff", str(missing), CURRENT]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"エラー: 前回の JSON が見つかりません: {missing}\n"


def test_main_diff_broken_json(capsys, tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    assert main(["--diff", str(broken), CURRENT]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"エラー: 前回の JSON を読み込めません: {broken} (JSONDecodeError)\n"


def test_main_diff_not_json_output_shape(capsys):
    # gh issue list の出力（配列）は --json の出力の形ではない
    assert main(["--diff", CURRENT, CURRENT]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"エラー: 前回の JSON が --json の出力の形ではありません: {CURRENT}\n"


def test_main_diff_without_value(capsys):
    assert main([CURRENT, "--diff"]) == 2
    assert "使い方:" in capsys.readouterr().err


def test_main_usage_mentions_diff(capsys):
    assert main(["--help"]) == 0
    out = capsys.readouterr().out
    assert "[--diff <前回のJSONのパス>]" in out
    assert "--diff last.json" in out
    assert "--limit、--since を付けず" in out
