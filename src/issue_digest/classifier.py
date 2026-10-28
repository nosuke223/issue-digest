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
    各分類の中はリポジトリ名の順、同じリポジトリの中は Issue 番号の小さい順
    （リポジトリ名がない Issue は最後に番号順。Issue.order を参照）。複数の `agent:*` ラベルを
    持つ Issue は該当するすべての分類に入る。CATEGORIES にない `agent:*` ラベルは無視するため、
    それしか持たない Issue は未分類に入る。
    """
    result: dict[str, list[Issue]] = {category: [] for category in CATEGORIES}
    for issue in sorted(issues, key=lambda i: i.order):
        matched = [c for c in CATEGORIES[:-1] if c in issue.labels]
        for category in matched or [UNCLASSIFIED]:
            result[category].append(issue)
    return result
