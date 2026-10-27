import argparse
import sys
from datetime import UTC, datetime
from importlib.metadata import version

from issue_digest.classifier import CATEGORIES, classify_issues
from issue_digest.config import DEFAULT_CONFIG_PATH, ConfigError, load_config
from issue_digest.diff import Diff, InvalidPreviousError, compute_diff, load_previous
from issue_digest.formatter import (
    format_csv,
    format_digest,
    format_digest_by_assignee,
    format_json,
)
from issue_digest.loader import InvalidUpdatedAtError, load_issues, parse_issues

USAGE = (
    "使い方: issue-digest [--hide-empty] [--summary] [--only <ラベル>]... [--exclude <ラベル>]..."
    " [--stale <日数>] [--age] [--since <YYYY-MM-DD>]"
    " [--json | --csv] [--sort updated|created] [--reverse] [--limit <件数>]"
    " [--max-chars <文字数>]"
    " [--show-assignees]"
    " [--show-labels] [--show-milestone] [--title <文字列>] [--output <パス>]"
    " [--diff <前回のJSONのパス>]"
    " [--config <パス>] [--group-by assignee] [--fail-if-any <ラベル>]..."
    " <JSONファイルのパス | ->\n"
    "       issue-digest --version\n"
    "  - で標準入力から読む / --hide-empty で0件の分類を出力しない\n"
    "  --only で指定した分類だけを出力する（複数回指定できる）\n"
    "  --exclude で指定した分類を出力しない（複数回指定できる。--only とは同時に指定できない）\n"
    "  --summary で見出しの次に全分類の件数を1行で出力する\n"
    "  --stale で最終更新から指定日数以上たった Issue に印を付ける\n"
    "  --age で作成日時がある Issue の行末に作成からの日数（作成から12日）を付ける"
    "（JSON は各 Issue に age_days を加える。createdAt がなければ null）\n"
    "  --since で最終更新（updatedAt）が指定日（YYYY-MM-DD、UTC の0時）以降の Issue だけを出す"
    "（updatedAt がない Issue は出さない。件数も絞った後の数。--diff の比較は全件で行う）\n"
    "  --sort updated で各分類の中を最終更新の古い順に並べる"
    "（--sort created なら作成日時の古い順）\n"
    "  --reverse で各分類（--group-by assignee のときは各担当者）の中の並びを逆にする"
    "（--sort がなければ番号の大きい順、--sort があれば新しい順。--limit と --max-chars は"
    "逆にした後の並びに効く。--diff の節の並びは変わらない）\n"
    "  --limit で各分類の出力を先頭から指定件数までにする（Markdown は最後に「- ほか N 件」、"
    "JSON は各分類に omitted を加える。件数は全件のまま）\n"
    "  --max-chars で Markdown の出力全体（末尾の改行を含む）を指定文字数以内にする"
    "（最後の分類から順に末尾の Issue の行を削り、「- ほか N 件」にする。"
    "見出し、件数、--summary の行、--diff の節は削らない。"
    "収まらなければそのまま出し、標準エラーに警告を出す。--group-by と一緒に指定すると、"
    "最後の担当者から順に削る。--json、--csv とは同時に指定できない）\n"
    "  --json で Markdown の代わりに JSON を出力する\n"
    "  --csv で Markdown の代わりに CSV（見出し行 label,number,title,url）を出力する"
    "（--json とは同時に指定できない。--stale、--age、--show-assignees、--show-labels、"
    "--show-milestone、--summary、--title は無視する）\n"
    "  --show-assignees で担当者を表示する（Markdown は行末に（担当: @alice）、"
    "JSON は各 Issue に assignees の配列を加える）\n"
    "  --show-labels で agent: で始まらないラベルを表示する"
    "（Markdown は行末に（ラベル: bug, docs）、JSON は各 Issue に labels の配列を加える）\n"
    "  --show-milestone でマイルストーンを表示する（Markdown は行末に（マイルストーン: v1.0）、"
    "JSON は各 Issue に milestone を加える。なければ null。"
    "入力は gh issue list --json の milestone）\n"
    "  --title で見出しの「Issue ダイジェスト」を指定した文字列に置き換える"
    "（JSON は先頭に title を加える）\n"
    "  --output でダイジェストを標準出力ではなく指定したファイルに書き出す（上書きする）\n"
    "  --diff で前回の --json の出力と比べ、新しい Issue、なくなった Issue、分類が変わった Issue を"
    "出す（Markdown は末尾に「## 前回からの変化」、JSON は diff を加える。--csv では無視する。"
    "前回の JSON は --only、--exclude、--hide-empty、--limit、--since を付けず、"
    "設定ファイルの hide_empty、only、limit も使わずに出力したもの。"
    "付けて出力した JSON だと、入っていなかった Issue は"
    "新しい Issue や分類が変わった Issue として出る）\n"
    "    例: issue-digest --json --output last.json issues.json で保存し、"
    "次回 issue-digest --diff last.json issues.json\n"
    "  --config で読む設定ファイルを指定する（省略時はカレントディレクトリの .issue-digest.toml。"
    "なければ使わない）。キーは hide_empty、summary、only、stale、sort、show_assignees、"
    "show_labels、title、limit、json、headings で、コマンドラインの指定を優先する"
    "（sort は updated か created、limit は1以上の整数、title は1文字以上の文字列）"
    "（only は --only か --exclude を指定したら使わない。"
    "json = true は --csv、--group-by、--max-chars を指定したら使わない）\n"
    '    例: hide_empty = true / stale = 7 / limit = 5 / only = ["agent:review", "agent:blocked"]\n'
    "    [headings] テーブルで分類の見出しを変えられる"
    '（例: [headings] の下に "agent:review" = "確認待ち"）\n'
    "  --group-by assignee で分類ごとの代わりに担当者ごとの見出し（## @alice - 3件、最後に"
    "## 担当者なし - N件）で並べ、各 Issue の行末に分類の名前を（作業中, 着手可能）の形で付ける"
    "（Markdown だけで使える。--json、--csv とは同時に指定できない。"
    "--sort、--reverse、--limit は各担当者の中で効く。"
    "--max-chars は最後の担当者から順に Issue の行を削る。"
    "--summary は担当者ごとの件数を出す。"
    "--hide-empty は効果がない）\n"
    "  --fail-if-any で指定した分類に Issue が1件以上あるとき、ダイジェストをいつもどおり出力"
    "（--output ならファイルに書き出して）してから終了コード 3 で終わる"
    "（複数回指定でき、どれか1つにあれば 3。判定は --since で絞った後の件数で、"
    "--only、--exclude、--hide-empty、--limit、--max-chars には左右されない。"
    "エラー（終了コード 1、2）のときはそちらを優先する）\n"
    "  --version でバージョンだけを出力する（ほかの指定は無視する）"
)


class _UsageError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str):
        raise _UsageError(message)


def _build_parser() -> argparse.ArgumentParser:
    # 値の検査（--stale、--sort、--only）は日本語のエラーメッセージのため main で行う
    parser = _Parser(add_help=False, allow_abbrev=False)
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("--hide-empty", action="store_true")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--show-assignees", action="store_true")
    parser.add_argument("--show-labels", action="store_true")
    parser.add_argument("--age", action="store_true")
    parser.add_argument("--show-milestone", action="store_true")
    parser.add_argument("--reverse", action="store_true")
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--fail-if-any", action="append", default=[])
    parser.add_argument("--stale")
    parser.add_argument("--sort")
    parser.add_argument("--limit")
    parser.add_argument("--max-chars")
    parser.add_argument("--since")
    parser.add_argument("--output")
    parser.add_argument("--title")
    parser.add_argument("--diff")
    parser.add_argument("--config")
    parser.add_argument("--group-by")
    parser.add_argument("paths", nargs="*")
    return parser


def _parse_since(value: str) -> datetime | None:
    """YYYY-MM-DD を UTC のその日の0時にする。形が不正またはない日付なら None。"""
    if not (len(value) == 10 and value.isascii() and value[4] == "-" and value[7] == "-"):
        return None
    year, month, day = value[:4], value[5:7], value[8:]
    if not (year.isdigit() and month.isdigit() and day.isdigit()):
        return None
    try:
        return datetime(int(year), int(month), int(day), tzinfo=UTC)
    except ValueError:
        return None


def main(argv: list[str] | None = None, now: datetime | None = None) -> int:
    """now は --stale と --age の経過日数の基準時刻。省略時は現在時刻（テストで固定できる）。"""
    args = sys.argv[1:] if argv is None else argv
    if "--version" in args:
        print(f"issue-digest {version('issue-digest')}")
        return 0
    try:
        opts = _build_parser().parse_args(args)
    except _UsageError:
        print(USAGE, file=sys.stderr)
        return 2
    if opts.help:
        print(USAGE)
        return 0
    try:
        config = load_config(opts.config)
    except FileNotFoundError:
        print(f"エラー: 設定ファイルが見つかりません: {opts.config}", file=sys.stderr)
        return 1
    except ConfigError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 2
    except OSError as e:
        print(
            f"エラー: 設定ファイルを読み込めません: {opts.config or DEFAULT_CONFIG_PATH}"
            f" ({type(e).__name__})",
            file=sys.stderr,
        )
        return 1
    # コマンドラインの指定が設定ファイルより優先される
    hide_empty = opts.hide_empty or config.get("hide_empty", False)
    summary = opts.summary or config.get("summary", False)
    as_csv = opts.csv
    group_by: str | None = opts.group_by
    # 設定の json は、コマンドラインの --csv、--group-by、--max-chars があれば使わない
    # （コマンドラインを優先する）
    as_json = opts.json or (
        config.get("json", False) and not as_csv and group_by is None and opts.max_chars is None
    )
    only: list[str] = opts.only
    exclude: list[str] = opts.exclude
    if not only and not exclude:
        # コマンドラインで --only も --exclude も指定しないときだけ、設定の only を使う
        only = config.get("only", [])
    show_assignees = opts.show_assignees or config.get("show_assignees", False)
    show_labels = opts.show_labels or config.get("show_labels", False)
    output: str | None = opts.output
    stale_days: int | None = config.get("stale")
    if opts.stale is not None:
        if not (opts.stale.isascii() and opts.stale.isdigit()):
            print(
                f"エラー: --stale には0以上の整数を指定してください: {opts.stale}",
                file=sys.stderr,
            )
            return 2
        stale_days = int(opts.stale)
    sort: str | None = opts.sort if opts.sort is not None else config.get("sort")
    if sort is not None and sort not in ("updated", "created"):
        print(
            f"エラー: --sort に指定できる値は updated か created です: {sort}",
            file=sys.stderr,
        )
        return 2
    limit: int | None = config.get("limit")
    if opts.limit is not None:
        if not (opts.limit.isascii() and opts.limit.isdigit()) or int(opts.limit) < 1:
            print(
                f"エラー: --limit には1以上の整数を指定してください: {opts.limit}",
                file=sys.stderr,
            )
            return 2
        limit = int(opts.limit)
    max_chars: int | None = None
    if opts.max_chars is not None:
        if not (opts.max_chars.isascii() and opts.max_chars.isdigit()) or int(opts.max_chars) < 1:
            print(
                f"エラー: --max-chars には1以上の整数を指定してください: {opts.max_chars}",
                file=sys.stderr,
            )
            return 2
        max_chars = int(opts.max_chars)
    since: datetime | None = None
    if opts.since is not None:
        since = _parse_since(opts.since)
        if since is None:
            print(
                f"エラー: --since には YYYY-MM-DD の形の日付を指定してください: {opts.since}",
                file=sys.stderr,
            )
            return 2
    if group_by is not None and group_by != "assignee":
        print(
            f"エラー: --group-by に指定できる値は assignee です: {group_by}",
            file=sys.stderr,
        )
        return 2
    headings: dict[str, str] | None = config.get("headings")
    title: str | None = opts.title if opts.title is not None else config.get("title")
    if title == "":
        print("エラー: --title には1文字以上を指定してください", file=sys.stderr)
        return 2
    paths: list[str] = opts.paths
    if len(paths) != 1:
        print(USAGE, file=sys.stderr)
        return 2
    if as_json and as_csv:
        print("エラー: --json と --csv は同時に指定できません", file=sys.stderr)
        return 2
    if group_by is not None and (as_json or as_csv):
        print(
            f"エラー: --group-by と {'--json' if as_json else '--csv'} は同時に指定できません"
            "（--group-by は Markdown だけで使えます）",
            file=sys.stderr,
        )
        return 2
    if max_chars is not None and (as_json or as_csv):
        print(
            "エラー: --max-chars は --json、--csv と同時に指定できません"
            "（Markdown だけで使えます）",
            file=sys.stderr,
        )
        return 2
    if only and exclude:
        print("エラー: --only と --exclude は同時に指定できません", file=sys.stderr)
        return 2
    fail_if_any: list[str] = opts.fail_if_any
    for option, labels in (
        ("--only", only),
        ("--exclude", exclude),
        ("--fail-if-any", fail_if_any),
    ):
        for label in labels:
            if label not in CATEGORIES:
                print(
                    f"エラー: {option} に指定できないラベルです: {label}\n"
                    f"指定できるラベル: {', '.join(CATEGORIES)}",
                    file=sys.stderr,
                )
                return 2
    only_filter = only or None
    exclude_filter = exclude or None
    path = paths[0]
    if path == "-":
        try:
            issues = parse_issues(sys.stdin.read())
        except InvalidUpdatedAtError as e:
            print(f"エラー: {e}", file=sys.stderr)
            return 1
        except (OSError, ValueError, KeyError, TypeError) as e:
            print(f"エラー: 標準入力を読み込めません ({type(e).__name__})", file=sys.stderr)
            return 1
    else:
        try:
            issues = load_issues(path)
        except FileNotFoundError:
            print(f"エラー: ファイルが見つかりません: {path}", file=sys.stderr)
            return 1
        except InvalidUpdatedAtError as e:
            print(f"エラー: {e}", file=sys.stderr)
            return 1
        except (OSError, ValueError, KeyError, TypeError) as e:
            print(f"エラー: ファイルを読み込めません: {path} ({type(e).__name__})", file=sys.stderr)
            return 1
    all_classified = classify_issues(issues)
    classified = all_classified
    if since is not None:
        classified = classify_issues(
            [i for i in issues if i.updated_at is not None and i.updated_at >= since]
        )
    diff: Diff | None = None
    if opts.diff is not None and not as_csv:
        try:
            # 今回の --only や --since などに関係なく、全分類の全件で比べる
            diff = compute_diff(load_previous(opts.diff), all_classified)
        except FileNotFoundError:
            print(f"エラー: 前回の JSON が見つかりません: {opts.diff}", file=sys.stderr)
            return 1
        except InvalidPreviousError:
            print(
                f"エラー: 前回の JSON が --json の出力の形ではありません: {opts.diff}",
                file=sys.stderr,
            )
            return 1
        except (OSError, ValueError) as e:
            print(
                f"エラー: 前回の JSON を読み込めません: {opts.diff} ({type(e).__name__})",
                file=sys.stderr,
            )
            return 1
    if as_csv:
        # CSV に列のない --stale、--age、--show-assignees、--show-labels、--show-milestone、
        # --summary、--title、--diff は無視する
        digest = format_csv(
            classified, hide_empty, only_filter, sort, exclude_filter, limit, opts.reverse
        )
    elif as_json:
        # JSON には分類ごとの count があるので、--summary は Markdown のときだけ効く
        digest = format_json(
            classified,
            hide_empty,
            only_filter,
            stale_days,
            now,
            sort,
            show_assignees,
            exclude_filter,
            limit,
            show_labels,
            title,
            diff,
            headings,
            opts.age,
            opts.show_milestone,
            opts.reverse,
        )
    elif group_by == "assignee":
        # 0件の担当者の見出しは出さないので、--hide-empty は効果がない
        digest = format_digest_by_assignee(
            classified,
            only_filter,
            stale_days,
            now,
            sort,
            summary,
            show_assignees,
            exclude_filter,
            limit,
            show_labels,
            title,
            diff,
            headings,
            opts.age,
            opts.reverse,
            max_chars,
            opts.show_milestone,
        )
    else:
        digest = format_digest(
            classified,
            hide_empty,
            only_filter,
            stale_days,
            now,
            sort,
            summary,
            show_assignees,
            exclude_filter,
            limit,
            show_labels,
            title,
            diff,
            headings,
            opts.age,
            max_chars,
            opts.show_milestone,
            opts.reverse,
        )
    if max_chars is not None and len(digest) > max_chars:
        print(
            f"警告: Issue の行をすべて削っても --max-chars の {max_chars} 文字に収まりません"
            f"（{len(digest)} 文字）",
            file=sys.stderr,
        )
    # 判定は --since で絞った後の件数で行い、--only などの出力の絞り込みには左右されない
    exit_code = 3 if any(classified[label] for label in fail_if_any) else 0
    if output is None:
        print(digest, end="")
        return exit_code
    try:
        with open(output, "w", encoding="utf-8", newline="") as f:
            f.write(digest)
    except OSError as e:
        print(f"エラー: ファイルに書き出せません: {output} ({type(e).__name__})", file=sys.stderr)
        return 1
    return exit_code
