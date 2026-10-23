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
    sort: str | None = None,
    show_assignees: bool = False,
) -> str:
    """分類結果を JSON のダイジェストにする。末尾は改行で終わる。

    引数の意味は format_digest と同じ。stale_days を指定したとき、印が付く Issue にだけ
    `stale_days`（経過日数）を加える。show_assignees が True のとき、各 Issue に
    `assignees`（login の配列。担当者がいなければ空の配列）を加える。
    """
    if stale_days is not None and now is None:
        now = datetime.now(UTC)
    total = len({issue.number for issues in classified.values() for issue in issues})
    categories = []
    for category, issues in _selected_categories(classified, hide_empty, only, sort):
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
            if show_assignees:
                item["assignees"] = list(issue.assignees)
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


def _selected_categories(
    classified: dict[str, list[Issue]],
    hide_empty: bool,
    only: list[str] | None,
    sort: str | None,
) -> list[tuple[str, list[Issue]]]:
    """出力する分類と、その中の Issue の並びを返す（Markdown と JSON で共通）。"""
    selected = []
    for category, issues in classified.items():
        if only is not None and category not in only:
            continue
        if hide_empty and not issues:
            continue
        if sort == "updated":
            issues = _sort_by_updated(issues)
        selected.append((category, issues))
    return selected


def _sort_by_updated(issues: list[Issue]) -> list[Issue]:
    """updatedAt の古い順（同じなら番号順）。updatedAt がない Issue は末尾に番号順。"""
    dated = [i for i in issues if i.updated_at is not None]
    undated = [i for i in issues if i.updated_at is None]
    dated.sort(key=lambda i: (i.updated_at, i.number))
    undated.sort(key=lambda i: i.number)
    return dated + undated


def format_digest(
    classified: dict[str, list[Issue]],
    hide_empty: bool = False,
    only: list[str] | None = None,
    stale_days: int | None = None,
    now: datetime | None = None,
    sort: str | None = None,
    summary: bool = False,
    show_assignees: bool = False,
) -> str:
    """分類結果を Markdown のダイジェストにする。末尾は改行で終わる。

    hide_empty が True のとき、0件の分類は見出しも「なし」も出力しない。
    only を指定すると、そこに含まれる分類だけを出力する（総件数は全件のまま）。
    stale_days を指定すると、最終更新から stale_days 日以上たった Issue の行末に
    `（N日更新なし）` を付ける。経過日数は now（省略時は現在時刻）から計算する。
    sort が "updated" のとき、各分類の中を updatedAt の古い順に並べる
    （同じ場合は番号順。updatedAt がない Issue は末尾）。
    summary が True のとき、総件数の見出しの次に全分類の件数を1行で出力する。
    この行は only や hide_empty に関係なく、常に全分類を含む。
    show_assignees が True のとき、担当者がいる Issue の行末に `（担当: @alice, @bob）` を
    付ける（`--stale` の印があればその後ろ）。
    """
    if stale_days is not None and now is None:
        now = datetime.now(UTC)
    # 複数の分類に入る Issue を二重に数えないよう、番号で重複を除く
    total = len({issue.number for issues in classified.values() for issue in issues})
    lines = [f"# Issue ダイジェスト（全 {total} 件）"]
    if summary:
        counts = " / ".join(
            f"{HEADINGS[category]} {len(issues)}" for category, issues in classified.items()
        )
        lines += ["", counts]
    for category, issues in _selected_categories(classified, hide_empty, only, sort):
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
