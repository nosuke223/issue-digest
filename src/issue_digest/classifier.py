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


def labels_of_categories(
    category_labels: dict[str, list[str]] | None = None,
) -> dict[str, list[str]]:
    """未分類以外の各分類（CATEGORIES の順）に割り当てる GitHub ラベルを返す。

    category_labels に書いた分類はそのラベルだけを使い、書かない分類は分類の名前と同じ
    ラベル（`agent:ready` など）を使う。
    """
    category_labels = category_labels or {}
    return {c: category_labels.get(c, [c]) for c in CATEGORIES[:-1]}


def classify_issues(
    issues: list[Issue], category_labels: dict[str, list[str]] | None = None
) -> dict[str, list[Issue]]:
    """Issue を `agent:*` ラベルごとに分類する。

    キーは CATEGORIES の順で、Issue がない分類も空のリストで含まれる。
    各分類の中はリポジトリ名の順、同じリポジトリの中は Issue 番号の小さい順
    （リポジトリ名がない Issue は最後に番号順。Issue.order を参照）。複数の分類のラベルを
    持つ Issue は該当するすべての分類に入る。どの分類のラベルも持たない Issue
    （CATEGORIES にない `agent:*` ラベルしか持たない Issue を含む）は未分類に入る。
    category_labels で分類に割り当てるラベルを変えられる（labels_of_categories を参照）。
    """
    labels_of = labels_of_categories(category_labels)
    result: dict[str, list[Issue]] = {category: [] for category in CATEGORIES}
    for issue in sorted(issues, key=lambda i: i.order):
        matched = [
            c for c, labels in labels_of.items() if any(label in issue.labels for label in labels)
        ]
        for category in matched or [UNCLASSIFIED]:
            result[category].append(issue)
    return result
