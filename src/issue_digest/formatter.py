import json
from datetime import UTC, datetime, timedelta

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


def _elapsed_days(elapsed: timedelta) -> int:
    """経過時間を日数に直す（1日未満は切り捨て）。"""
    return elapsed.days


def _stale_days_of(issue: Issue, stale_days: int | None, now: datetime | None) -> int | None:
    """印を付ける Issue の経過日数を返す。印を付けないときは None。"""
    if stale_days is None or now is None or issue.updated_at is None:
        return None
    days = _elapsed_days(now - issue.updated_at)
    return days if days >= stale_days else None


def _stale_mark(issue: Issue, stale_days: int | None, now: datetime | None) -> str:
    days = _stale_days_of(issue, stale_days, now)
    return "" if days is None else f"（{days}日更新なし）"


def format_json(
    classified: dict[str, list[Issue]],
    hide_empty: bool = False,
    only: list[str] | None = None,
    stale_days: int | None = None,
    now: datetime | None = None,
) -> str:
    """分類結果を JSON のダイジェストにする。末尾は改行で終わる。

    引数の意味は format_digest と同じ。stale_days を指定したとき、印が付く Issue にだけ
    `stale_days`（経過日数）を加える。
    """
    if stale_days is not None and now is None:
        now = datetime.now(UTC)
    total = len({issue.number for issues in classified.values() for issue in issues})
    categories = []
    for category, issues in classified.items():
        if only is not None and category not in only:
            continue
        if hide_empty and not issues:
            continue
        items = []
        for issue in issues:
            item: dict[str, object] = {
                "number": issue.number,
                "title": issue.title,
                "url": issue.url,
            }
            days = _stale_days_of(issue, stale_days, now)
            if days is not None:
                item["stale_days"] = days
            items.append(item)
        categories.append(
            {
                "label": category,
                "title": HEADINGS[category],
                "count": len(issues),
                "issues": items,
            }
        )
    body = {"total": total, "categories": categories}
    return json.dumps(body, ensure_ascii=False, indent=2) + "\n"


def _assignees_mark(issue: Issue, show_assignees: bool) -> str:
    if not show_assignees or not issue.assignees:
        return ""
    return "（担当: " + ", ".join(f"@{login}" for login in issue.assignees) + "）"


def format_digest(
    classified: dict[str, list[Issue]],
    hide_empty: bool = False,
    only: list[str] | None = None,
    stale_days: int | None = None,
    now: datetime | None = None,
    show_assignees: bool = False,
) -> str:
    """分類結果を Markdown のダイジェストにする。末尾は改行で終わる。

    hide_empty が True のとき、0件の分類は見出しも「なし」も出力しない。
    only を指定すると、そこに含まれる分類だけを出力する（総件数は全件のまま）。
    stale_days を指定すると、最終更新から stale_days 日以上たった Issue の行末に
    `（N日更新なし）` を付ける。経過日数は now（省略時は現在時刻）から計算する。
    show_assignees が True のとき、担当者がいる Issue の行末に `（担当: @alice, @bob）` を
    付ける（`--stale` の印があればその後ろ）。
    """
    if stale_days is not None and now is None:
        now = datetime.now(UTC)
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
            for issue in issues:
                lines.append(
                    f"- [#{issue.number}]({issue.url}) {issue.title}"
                    f"{_stale_mark(issue, stale_days, now)}"
                    f"{_assignees_mark(issue, show_assignees)}"
                )
        else:
            lines.append("なし")
    return "\n".join(lines) + "\n"
