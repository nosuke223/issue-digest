from issue_digest.classifier import UNCLASSIFIED
from issue_digest.loader import Issue

HEADINGS = {
    "agent:needs-decision": "判断待ち",
    "agent:blocked": "中断",
    "agent:review": "レビュー待ち",
    "agent:working": "作業中",
    "agent:ready": "着手可能",
    UNCLASSIFIED: "未分類",
}


def format_digest(classified: dict[str, list[Issue]]) -> str:
    """分類結果を Markdown のダイジェストにする。末尾は改行で終わる。"""
    lines = ["# Issue ダイジェスト"]
    for category, issues in classified.items():
        title = HEADINGS[category]
        if category == UNCLASSIFIED:
            heading = f"## {title} - {len(issues)}件"
        else:
            heading = f"## {title} ({category}) - {len(issues)}件"
        lines += ["", heading, ""]
        if issues:
            lines += [f"- #{issue.number} {issue.title}" for issue in issues]
        else:
            lines.append("なし")
    return "\n".join(lines) + "\n"
