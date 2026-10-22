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


def format_digest(
    classified: dict[str, list[Issue]],
    hide_empty: bool = False,
    only: list[str] | None = None,
) -> str:
    """分類結果を Markdown のダイジェストにする。末尾は改行で終わる。

    hide_empty が True のとき、0件の分類は見出しも「なし」も出力しない。
    only を指定すると、そこに含まれる分類だけを出力する（総件数は全件のまま）。
    """
    # 複数の分類に入る Issue を二重に数えないよう、番号で重複を除く
    total = len({issue.number for issues in classified.values() for issue in issues})
    lines = [f"# Issue ダイジェスト（全 {total} 件）"]
    for category, issues in classified.items():
        if only is not None and category not in only:
            continue
        if hide_empty and not issues:
            continue
        title = HEADINGS[category]
        if category == UNCLASSIFIED:
            heading = f"## {title} - {len(issues)}件"
        else:
            heading = f"## {title} ({category}) - {len(issues)}件"
        lines += ["", heading, ""]
        if issues:
            lines += [f"- [#{issue.number}]({issue.url}) {issue.title}" for issue in issues]
        else:
            lines.append("なし")
    return "\n".join(lines) + "\n"
