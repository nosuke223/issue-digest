from conftest import make_issue

from issue_digest.classifier import CATEGORIES, UNCLASSIFIED, classify_issues
from issue_digest.loader import Issue


def numbers(issues: list[Issue]) -> list[int]:
    return [i.number for i in issues]


def test_categories_are_in_specified_order():
    result = classify_issues([])
    assert list(result) == [
        "agent:needs-decision",
        "agent:blocked",
        "agent:review",
        "agent:working",
        "agent:ready",
        UNCLASSIFIED,
    ]
    assert list(result) == CATEGORIES


def test_empty_categories_are_included_as_empty_lists():
    result = classify_issues([make_issue(1, labels=["agent:ready"])])
    assert numbers(result["agent:ready"]) == [1]
    assert result["agent:needs-decision"] == []
    assert result["agent:blocked"] == []
    assert result[UNCLASSIFIED] == []


def test_issues_are_sorted_by_number_within_category():
    issues = [make_issue(5, labels=["agent:ready"]), make_issue(2, labels=["agent:ready"])]
    assert numbers(classify_issues(issues)["agent:ready"]) == [2, 5]


def test_issue_without_agent_label_is_unclassified():
    issues = [make_issue(3, labels=[]), make_issue(1, labels=["bug"])]
    assert numbers(classify_issues(issues)[UNCLASSIFIED]) == [1, 3]


def test_non_agent_labels_do_not_affect_classification():
    result = classify_issues([make_issue(1, labels=["bug", "agent:review"])])
    assert numbers(result["agent:review"]) == [1]
    assert result[UNCLASSIFIED] == []


def test_issue_with_multiple_agent_labels_is_in_all_categories():
    result = classify_issues([make_issue(1, labels=["agent:working", "agent:blocked"])])
    assert numbers(result["agent:working"]) == [1]
    assert numbers(result["agent:blocked"]) == [1]
    assert result[UNCLASSIFIED] == []


def test_issue_with_only_unknown_agent_label_is_unclassified():
    result = classify_issues([make_issue(1, labels=["agent:unknown"])])
    assert numbers(result[UNCLASSIFIED]) == [1]
    assert all(result[c] == [] for c in CATEGORIES if c != UNCLASSIFIED)


def test_unknown_agent_label_is_ignored_alongside_known_label():
    result = classify_issues([make_issue(1, labels=["agent:unknown", "agent:ready"])])
    assert numbers(result["agent:ready"]) == [1]
    assert result[UNCLASSIFIED] == []
