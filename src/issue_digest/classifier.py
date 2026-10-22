from issue_digest.loader import Issue

UNCLASSIFIED = "unclassified"

# 人間の対応が必要なものを先に並べる
CATEGORIES = [
    "agent:needs-decision",
    "agent:blocked",
    "agent:review",
    "agent:working",
    "agent:ready",
    UNCLASSIFIED,
]


def classify_issues(issues: list[Issue]) -> dict[str, list[Issue]]:
    """Issue を `agent:*` ラベルごとに分類する。

    キーは CATEGORIES の順で、Issue がない分類も空のリストで含まれる。
    各分類の中は Issue 番号の小さい順。複数の `agent:*` ラベルを持つ Issue は
    該当するすべての分類に入る。CATEGORIES にない `agent:*` ラベルは無視する。
    """
    result: dict[str, list[Issue]] = {category: [] for category in CATEGORIES}
    for issue in sorted(issues, key=lambda i: i.number):
        agent_labels = [label for label in issue.labels if label.startswith("agent:")]
        if not agent_labels:
            result[UNCLASSIFIED].append(issue)
            continue
        for category in CATEGORIES[:-1]:
            if category in agent_labels:
                result[category].append(issue)
    return result
