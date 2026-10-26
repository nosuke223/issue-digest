import csv
import io
import json
from datetime import UTC, datetime, timedelta

from issue_digest.classifier import UNCLASSIFIED
from issue_digest.diff import Diff, DiffEntry
from issue_digest.loader import Issue

HEADINGS = {
    "agent:needs-decision": "判断待ち",
    "agent:blocked": "中断",
    "agent:review": "レビュー待ち",
    "agent:working": "作業中",
    "agent:ready": "着手可能",
    UNCLASSIFIED: "未分類",
}


def _heading_of(category: str, headings: dict[str, str] | None) -> str:
    """分類の見出しを返す。headings に書かれていれば、それを優先する。"""
    if headings is not None and category in headings:
        return headings[category]
    return HEADINGS[category]


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
    exclude: list[str] | None = None,
    limit: int | None = None,
    show_labels: bool = False,
    title: str | None = None,
    diff: Diff | None = None,
    headings: dict[str, str] | None = None,
) -> str:
    """分類結果を JSON のダイジェストにする。末尾は改行で終わる。

    引数の意味は format_digest と同じ。stale_days を指定したとき、印が付く Issue にだけ
    `stale_days`（経過日数）を加える。show_assignees が True のとき、各 Issue に
    `assignees`（login の配列。担当者がいなければ空の配列）を加える。
    limit を指定したとき、各分類の `issues` を先頭 limit 件にし（`count` は全件のまま）、
    出力しなかった件数を `omitted` に入れる。show_labels が True のとき、各 Issue に
    `labels`（`agent:` で始まらないラベルの配列。なければ空の配列）を加える。
    title を指定したとき、JSON の先頭に `title` を加える。
    diff を指定したとき、末尾に `diff`（`added`、`removed`、`moved` の配列）を加える。
    `added` と `removed` の各要素は `number`、`title`、`url`、`categories`（今回・前回の分類）、
    `moved` の各要素は `number`、`title`、`url`、`from`、`to`（前回・今回の分類）。
    headings に書かれた分類は、各分類の `title` をその文字列に置き換える。
    """
    if stale_days is not None and now is None:
        now = datetime.now(UTC)
    total = len({issue.number for issues in classified.values() for issue in issues})
    categories = []
    for category, issues in _selected_categories(classified, hide_empty, only, sort, exclude):
        items = []
        shown = issues if limit is None else issues[:limit]
        for issue in shown:
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
            if show_labels:
                item["labels"] = _other_labels(issue)
            items.append(item)
        entry: dict[str, object] = {
            "label": category,
            "title": _heading_of(category, headings),
            "count": len(issues),
            "issues": items,
        }
        if limit is not None:
            entry["omitted"] = len(issues) - len(shown)
        categories.append(entry)
    body: dict[str, object] = {}
    if title is not None:
        body["title"] = title
    body["total"] = total
    body["categories"] = categories
    if diff is not None:
        body["diff"] = {
            "added": [_diff_item(e, categories=list(e.after)) for e in diff.added],
            "removed": [_diff_item(e, categories=list(e.before)) for e in diff.removed],
            "moved": [
                _diff_item(e, **{"from": list(e.before), "to": list(e.after)}) for e in diff.moved
            ],
        }
    return json.dumps(body, ensure_ascii=False, indent=2) + "\n"


def _diff_item(entry: DiffEntry, **extra: object) -> dict[str, object]:
    return {"number": entry.number, "title": entry.title, "url": entry.url, **extra}


def format_csv(
    classified: dict[str, list[Issue]],
    hide_empty: bool = False,
    only: list[str] | None = None,
    sort: str | None = None,
    exclude: list[str] | None = None,
    limit: int | None = None,
) -> str:
    """分類結果を CSV にする。1行目は見出し行 `label,number,title,url`。

    分類の順、各分類の中の順に1行ずつ出力する（複数の分類に入る Issue は分類ごとに1行）。
    クオートや改行コードは csv モジュールの既定に従う（行末は `\\r\\n`）。
    limit を指定すると、各分類の先頭 limit 件だけを出力する。
    stale や担当者など、CSV に列のない情報は扱わない。
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["label", "number", "title", "url"])
    for category, issues in _selected_categories(classified, hide_empty, only, sort, exclude):
        shown = issues if limit is None else issues[:limit]
        for issue in shown:
            writer.writerow([category, issue.number, issue.title, issue.url])
    return buffer.getvalue()


_MARKDOWN_SPECIAL = str.maketrans({c: "\\" + c for c in "\\`*_[]<>"})


def _escape_markdown(text: str) -> str:
    """Markdown の記号の前にバックスラッシュを付ける。"""
    return text.translate(_MARKDOWN_SPECIAL)


MAX_TITLE_LENGTH = 40


def _shorten_title(text: str) -> str:
    """MAX_TITLE_LENGTH 文字を超えるタイトルを、その長さまでにして末尾に `…` を付ける。"""
    if len(text) <= MAX_TITLE_LENGTH:
        return text
    return text[:MAX_TITLE_LENGTH] + "…"


def _assignees_mark(issue: Issue, show_assignees: bool) -> str:
    if not show_assignees or not issue.assignees:
        return ""
    return "（担当: " + ", ".join(f"@{login}" for login in issue.assignees) + "）"


def _other_labels(issue: Issue) -> list[str]:
    """`agent:` で始まらないラベルを入力の順に返す。"""
    return [label for label in issue.labels if not label.startswith("agent:")]


def _labels_mark(issue: Issue, show_labels: bool) -> str:
    labels = _other_labels(issue)
    if not show_labels or not labels:
        return ""
    return "（ラベル: " + ", ".join(labels) + "）"


def _selected_categories(
    classified: dict[str, list[Issue]],
    hide_empty: bool,
    only: list[str] | None,
    sort: str | None,
    exclude: list[str] | None = None,
) -> list[tuple[str, list[Issue]]]:
    """出力する分類と、その中の Issue の並びを返す（Markdown と JSON で共通）。"""
    selected = []
    for category, issues in classified.items():
        if only is not None and category not in only:
            continue
        if exclude is not None and category in exclude:
            continue
        if hide_empty and not issues:
            continue
        if sort == "updated":
            issues = _sort_by_date(issues, "updated_at")
        elif sort == "created":
            issues = _sort_by_date(issues, "created_at")
        selected.append((category, issues))
    return selected


def _sort_by_date(issues: list[Issue], attr: str) -> list[Issue]:
    """日時（attr）の古い順（同じなら番号順）。日時がない Issue は末尾に番号順。"""
    dated = [i for i in issues if getattr(i, attr) is not None]
    undated = [i for i in issues if getattr(i, attr) is None]
    dated.sort(key=lambda i: (getattr(i, attr), i.number))
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
    exclude: list[str] | None = None,
    limit: int | None = None,
    show_labels: bool = False,
    title: str | None = None,
    diff: Diff | None = None,
    headings: dict[str, str] | None = None,
) -> str:
    """分類結果を Markdown のダイジェストにする。末尾は改行で終わる。

    hide_empty が True のとき、0件の分類は見出しも「なし」も出力しない。
    only を指定すると、そこに含まれる分類だけを出力する（総件数は全件のまま）。
    exclude を指定すると、そこに含まれる分類を出力しない（総件数は全件のまま）。
    stale_days を指定すると、最終更新から stale_days 日以上たった Issue の行末に
    `（N日更新なし）` を付ける。経過日数は now（省略時は現在時刻）から計算する。
    sort が "updated" のとき、各分類の中を updatedAt の古い順に並べる
    （同じ場合は番号順。updatedAt がない Issue は末尾）。"created" のときは createdAt の古い順。
    summary が True のとき、総件数の見出しの次に全分類の件数を1行で出力する。
    この行は only や hide_empty に関係なく、常に全分類を含む。
    show_assignees が True のとき、担当者がいる Issue の行末に `（担当: @alice, @bob）` を
    付ける（`--stale` の印があればその後ろ）。
    limit を指定すると、各分類で（sort の後の）先頭 limit 件だけを出力し、出力しなかった
    Issue があれば分類の最後に `- ほか N 件` を出す。見出しの件数は全件のまま。
    show_labels が True のとき、`agent:` で始まらないラベルがある Issue の行末に
    `（ラベル: bug, docs）` を付ける（担当者の印があればその後ろ）。
    title を指定すると、1行目の `Issue ダイジェスト` をその文字列に置き換える。
    headings に書かれた分類は、分類の見出しと summary の行の名前をその文字列に置き換える。
    Issue のタイトルが40文字を超えるときは、40文字までにして末尾に `…` を付ける
    （エスケープは省略した後のタイトルに行う。JSON のタイトルは省略しない）。
    diff を指定すると、末尾に `## 前回からの変化` の節を加える（_diff_lines を参照）。
    分類が変わった Issue の分類の名前にも headings を使う。
    """
    if stale_days is not None and now is None:
        now = datetime.now(UTC)
    # 複数の分類に入る Issue を二重に数えないよう、番号で重複を除く
    total = len({issue.number for issues in classified.values() for issue in issues})
    heading_title = "Issue ダイジェスト" if title is None else title
    lines = [f"# {heading_title}（全 {total} 件）"]
    if summary:
        counts = " / ".join(
            f"{_heading_of(category, headings)} {len(issues)}"
            for category, issues in classified.items()
        )
        lines += ["", counts]
    for category, issues in _selected_categories(classified, hide_empty, only, sort, exclude):
        category_title = _heading_of(category, headings)
        if category == UNCLASSIFIED:
            heading = f"## {category_title} - {len(issues)}件"
        else:
            heading = f"## {category_title} ({category}) - {len(issues)}件"
        lines += ["", heading, ""]
        if issues:
            shown = issues if limit is None else issues[:limit]
            for issue in shown:
                issue_title = _escape_markdown(_shorten_title(issue.title))
                lines.append(
                    f"- [#{issue.number}]({issue.url}) {issue_title}"
                    f"{_stale_mark(issue, stale_days, now)}"
                    f"{_assignees_mark(issue, show_assignees)}"
                    f"{_labels_mark(issue, show_labels)}"
                )
            if len(shown) < len(issues):
                lines.append(f"- ほか {len(issues) - len(shown)} 件")
        else:
            lines.append("なし")
    if diff is not None:
        lines += _diff_lines(diff, headings)
    return "\n".join(lines) + "\n"


NO_ASSIGNEE = "担当者なし"


def _group_by_assignee(
    classified: dict[str, list[Issue]],
    only: list[str] | None = None,
    exclude: list[str] | None = None,
) -> tuple[list[tuple[str | None, list[Issue]]], dict[int, list[str]]]:
    """only と exclude で選んだ分類の Issue を、担当者ごとにまとめる。

    1つ目の戻り値は (担当者の login、その担当者の Issue を番号順に並べたもの) の配列。
    担当者は login の順（大文字と小文字を区別せずに比べる）で、担当者なしの Issue があれば
    最後に login が None の組を置く。0件の担当者は含まない。
    2つ目の戻り値は、Issue 番号から、その Issue が入る分類（選んだ分類だけ。見出しの順）への辞書。
    """
    categories_of: dict[int, list[str]] = {}
    issue_of: dict[int, Issue] = {}
    for category, issues in _selected_categories(classified, False, only, None, exclude):
        for issue in issues:
            categories_of.setdefault(issue.number, []).append(category)
            issue_of[issue.number] = issue
    by_login: dict[str, list[Issue]] = {}
    unassigned: list[Issue] = []
    for number in sorted(issue_of):
        issue = issue_of[number]
        if not issue.assignees:
            unassigned.append(issue)
        # 同じ担当者が重複して書かれていても、1回だけ数える
        for login in dict.fromkeys(issue.assignees):
            by_login.setdefault(login, []).append(issue)
    groups: list[tuple[str | None, list[Issue]]] = [
        (login, by_login[login]) for login in sorted(by_login, key=lambda s: (s.lower(), s))
    ]
    if unassigned:
        groups.append((None, unassigned))
    return groups, categories_of


def _assignee_heading(login: str | None) -> str:
    return NO_ASSIGNEE if login is None else f"@{login}"


def format_digest_by_assignee(
    classified: dict[str, list[Issue]],
    only: list[str] | None = None,
    stale_days: int | None = None,
    now: datetime | None = None,
    sort: str | None = None,
    summary: bool = False,
    show_assignees: bool = False,
    exclude: list[str] | None = None,
    limit: int | None = None,
    show_labels: bool = False,
    title: str | None = None,
    diff: Diff | None = None,
    headings: dict[str, str] | None = None,
) -> str:
    """分類結果を、担当者ごとの見出しで並べた Markdown のダイジェストにする。

    見出しは `## @alice - 3件` の形で、担当者の login の順、最後に `## 担当者なし - N件`。
    担当者が複数いる Issue は、それぞれの担当者の下に出す。0件の担当者の見出しは出さない。
    only と exclude は出す Issue を選ぶ（選んだ分類のどれかに入る Issue だけを出す）。
    各 Issue の行末に、選んだ分類のうちその Issue が入るものの名前を見出しの順に
    `（作業中, 着手可能）` の形で付け、その後ろに format_digest と同じ印を付ける。
    sort と limit は各担当者の中で効く。総件数と summary の行は only と exclude に関係なく
    全件で数える。出す Issue が1件もなければ、見出しの代わりに「なし」を出す。
    ほかの引数の意味は format_digest と同じ。
    """
    if stale_days is not None and now is None:
        now = datetime.now(UTC)
    total = len({issue.number for issues in classified.values() for issue in issues})
    heading_title = "Issue ダイジェスト" if title is None else title
    lines = [f"# {heading_title}（全 {total} 件）"]
    if summary:
        all_groups, _ = _group_by_assignee(classified)
        counts = " / ".join(
            f"{_assignee_heading(login)} {len(issues)}" for login, issues in all_groups
        )
        lines += ["", counts or "なし"]
    groups, categories_of = _group_by_assignee(classified, only, exclude)
    if not groups:
        lines += ["", "なし"]
    for login, issues in groups:
        lines += ["", f"## {_assignee_heading(login)} - {len(issues)}件", ""]
        if sort == "updated":
            issues = _sort_by_date(issues, "updated_at")
        elif sort == "created":
            issues = _sort_by_date(issues, "created_at")
        shown = issues if limit is None else issues[:limit]
        for issue in shown:
            issue_title = _escape_markdown(_shorten_title(issue.title))
            names = _category_names(tuple(categories_of[issue.number]), headings)
            lines.append(
                f"- [#{issue.number}]({issue.url}) {issue_title}（{names}）"
                f"{_stale_mark(issue, stale_days, now)}"
                f"{_assignees_mark(issue, show_assignees)}"
                f"{_labels_mark(issue, show_labels)}"
            )
        if len(shown) < len(issues):
            lines.append(f"- ほか {len(issues) - len(shown)} 件")
    if diff is not None:
        lines += _diff_lines(diff, headings)
    return "\n".join(lines) + "\n"


def _diff_lines(diff: Diff, headings: dict[str, str] | None = None) -> list[str]:
    """`## 前回からの変化` の節の行。変化がなければ「変化なし」だけを出す。

    変化があるときは、新しい Issue、なくなった Issue、分類が変わった Issue の小見出しを
    すべて出し、0件の小見出しには「なし」を出す。
    """
    lines = ["", "## 前回からの変化", ""]
    if diff.is_empty():
        return lines + ["変化なし"]
    sections = [
        ("新しい Issue", diff.added, False),
        ("なくなった Issue", diff.removed, False),
        ("分類が変わった Issue", diff.moved, True),
    ]
    for i, (heading, entries, show_move) in enumerate(sections):
        if i > 0:
            lines.append("")
        lines += [f"### {heading} - {len(entries)}件", ""]
        if not entries:
            lines.append("なし")
        for entry in entries:
            line = (
                f"- [#{entry.number}]({entry.url}) {_escape_markdown(_shorten_title(entry.title))}"
            )
            if show_move:
                before = _category_names(entry.before, headings)
                after = _category_names(entry.after, headings)
                line += f": {before} → {after}"
            lines.append(line)
    return lines


def _category_names(categories: tuple[str, ...], headings: dict[str, str] | None) -> str:
    return ", ".join(_heading_of(c, headings) for c in categories)
