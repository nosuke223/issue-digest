import csv
import io
import json

import pytest
from conftest import DATA, issue_numbers_in_output, make_issue

from issue_digest import main
from issue_digest.classifier import UNCLASSIFIED, classify_issues

INPUT = str(DATA / "category_labels.json")
CONFIG = '[category_labels]\n"agent:ready" = ["status:todo"]\n' + (
    '"agent:working" = ["status:doing", "status:in-progress"]\n'
)


def write_config(directory, text):
    (directory / ".issue-digest.toml").write_text(text, encoding="utf-8")


def numbers_by_label(data: dict) -> dict[str, list[int]]:
    return {c["label"]: [i["number"] for i in c["issues"]] for c in data["categories"]}


def numbers(issues) -> list[int]:
    return [i.number for i in issues]


def test_classifier_uses_configured_labels_instead_of_default():
    issues = [make_issue(1, labels=["status:todo"]), make_issue(2, labels=["agent:ready"])]
    result = classify_issues(issues, {"agent:ready": ["status:todo"]})
    assert numbers(result["agent:ready"]) == [1]
    assert numbers(result[UNCLASSIFIED]) == [2]


def test_classifier_same_label_in_two_categories_goes_to_both():
    result = classify_issues(
        [make_issue(1, labels=["x"])], {"agent:ready": ["x"], "agent:blocked": ["x"]}
    )
    assert numbers(result["agent:blocked"]) == [1]
    assert numbers(result["agent:ready"]) == [1]
    assert result[UNCLASSIFIED] == []


def test_classifier_without_config_is_unchanged():
    issues = [make_issue(1, labels=["agent:ready"]), make_issue(2, labels=["status:todo"])]
    assert classify_issues(issues, None) == classify_issues(issues)
    assert classify_issues(issues, {}) == classify_issues(issues)


def test_markdown_classifies_by_configured_labels(in_tmp_dir, capsys):
    write_config(in_tmp_dir, CONFIG)
    assert main(["--json", INPUT]) == 0
    assert numbers_by_label(json.loads(capsys.readouterr().out)) == {
        "agent:needs-decision": [],
        "agent:blocked": [],
        # 書かなかった分類は既定のラベルのまま
        "agent:review": [5],
        # 複数のラベルのどれを持っていても入る
        "agent:working": [3, 4],
        # agent:ready は使わなくなる
        "agent:ready": [1],
        # 大文字と小文字は区別する
        UNCLASSIFIED: [2, 6],
    }


def test_markdown_heading_keeps_category_name(in_tmp_dir, capsys):
    write_config(in_tmp_dir, CONFIG)
    assert main([INPUT]) == 0
    out = capsys.readouterr().out
    assert "## 着手可能 (agent:ready) - 1件\n\n- [example/repo#1]" in out


def test_only_and_fail_if_any_use_category_name(in_tmp_dir, capsys):
    write_config(in_tmp_dir, CONFIG)
    assert main(["--only", "agent:ready", "--fail-if-any", "agent:ready", INPUT]) == 3
    assert issue_numbers_in_output(capsys.readouterr().out) == [1]


def test_fail_if_any_is_zero_when_only_default_label_remains(in_tmp_dir, capsys):
    write_config(in_tmp_dir, '[category_labels]\n"agent:review" = ["status:review"]\n')
    assert main(["--fail-if-any", "agent:review", INPUT]) == 0


def test_csv_label_is_category_name(in_tmp_dir, capsys):
    write_config(in_tmp_dir, CONFIG)
    assert main(["--csv", "--only", "agent:ready", INPUT]) == 0
    rows = list(csv.reader(io.StringIO(capsys.readouterr().out)))
    assert [(r[0], r[1]) for r in rows[1:]] == [("agent:ready", "1")]


def test_show_labels_hides_configured_labels(in_tmp_dir, capsys):
    write_config(in_tmp_dir, CONFIG)
    assert main(["--show-labels", INPUT]) == 0
    out = capsys.readouterr().out
    assert "status:todo の Issue（ラベル: bug）\n" in out
    assert "status:doing の Issue\n" in out
    assert "status:in-progress の Issue（ラベル: docs）\n" in out
    # 分類に使っていないラベルは出す（大文字と小文字は区別する）
    assert "大文字の Status:Todo の Issue（ラベル: Status:Todo）\n" in out
    # agent: で始まるラベルは今までどおり出さない
    assert "agent:ready だけの Issue\n" in out


def test_json_labels_hides_configured_labels(in_tmp_dir, capsys):
    write_config(in_tmp_dir, CONFIG)
    assert main(["--json", "--show-labels", INPUT]) == 0
    data = json.loads(capsys.readouterr().out)
    labels = {i["number"]: i["labels"] for c in data["categories"] for i in c["issues"]}
    assert labels == {1: ["bug"], 2: [], 3: [], 4: ["docs"], 5: [], 6: ["Status:Todo"]}


def test_show_labels_with_group_by_hides_configured_labels(in_tmp_dir, capsys):
    write_config(in_tmp_dir, CONFIG)
    assert main(["--show-labels", "--group-by", "assignee", INPUT]) == 0
    assert "status:todo の Issue（着手可能）（ラベル: bug）\n" in capsys.readouterr().out


def test_show_labels_without_config_is_unchanged(capsys):
    assert main(["--show-labels", INPUT]) == 0
    assert "status:todo の Issue（ラベル: status:todo, bug）\n" in capsys.readouterr().out


def test_works_with_headings_only_exclude(in_tmp_dir, capsys):
    write_config(
        in_tmp_dir,
        'only = ["agent:ready", "agent:working"]\n[headings]\n"agent:ready" = "TODO"\n' + CONFIG,
    )
    assert main([INPUT]) == 0
    out = capsys.readouterr().out
    assert "## TODO (agent:ready) - 1件\n" in out
    assert issue_numbers_in_output(out) == [3, 4, 1]

    write_config(in_tmp_dir, 'exclude = ["unclassified", "agent:working"]\n' + CONFIG)
    assert main([INPUT]) == 0
    assert issue_numbers_in_output(capsys.readouterr().out) == [5, 1]


def test_diff_accepts_json_from_before_config(in_tmp_dir, capsys):
    previous = in_tmp_dir / "last.json"
    assert main(["--json", "--output", str(previous), INPUT]) == 0
    write_config(in_tmp_dir, CONFIG)
    assert main(["--json", "--diff", str(previous), INPUT]) == 0
    diff = json.loads(capsys.readouterr().out)["diff"]
    assert diff["added"] == []
    assert diff["removed"] == []
    moved = {m["number"]: (m["from"], m["to"]) for m in diff["moved"]}
    assert moved == {
        1: (["unclassified"], ["agent:ready"]),
        2: (["agent:ready"], ["unclassified"]),
        3: (["unclassified"], ["agent:working"]),
        4: (["unclassified"], ["agent:working"]),
    }


def test_migration_with_both_labels(in_tmp_dir, capsys):
    write_config(in_tmp_dir, '[category_labels]\n"agent:ready" = ["status:todo", "agent:ready"]\n')
    assert main(["--only", "agent:ready", INPUT]) == 0
    assert issue_numbers_in_output(capsys.readouterr().out) == [1, 2]


def test_empty_table_is_unchanged(in_tmp_dir, capsys):
    assert main(["--show-labels", INPUT]) == 0
    expected = capsys.readouterr().out
    write_config(in_tmp_dir, "[category_labels]\n")
    assert main(["--show-labels", INPUT]) == 0
    assert capsys.readouterr().out == expected


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (
            '[category_labels]\nunclassified = ["x"]\n',
            "category_labels に指定できない分類です: unclassified",
        ),
        (
            '[category_labels]\n"agent:unknown" = ["x"]\n',
            "category_labels に指定できない分類です: agent:unknown",
        ),
        ('[category_labels]\n"agent:ready" = "x"\n', 'category_labels."agent:ready" には'),
        ('[category_labels]\n"agent:ready" = [1]\n', 'category_labels."agent:ready" には'),
        ('[category_labels]\n"agent:ready" = []\n', 'category_labels."agent:ready" には'),
        (
            '[category_labels]\n"agent:blocked" = ["x", ""]\n',
            'category_labels."agent:blocked" には',
        ),
        ('category_labels = ["x"]\n', "category_labels はテーブル"),
    ],
)
def test_invalid_category_labels_exit_2(in_tmp_dir, capsys, text, message):
    write_config(in_tmp_dir, text)
    assert main([INPUT]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert message in captured.err
