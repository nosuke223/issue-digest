import argparse
import sys
from datetime import UTC, datetime
from importlib.metadata import version

from issue_digest.classifier import CATEGORIES, classify_issues
from issue_digest.config import DEFAULT_CONFIG_PATH, ConfigError, load_config
from issue_digest.diff import Diff, InvalidPreviousError, compute_diff, load_previous
from issue_digest.formatter import format_csv, format_digest, format_json
from issue_digest.loader import InvalidUpdatedAtError, load_issues, parse_issues

USAGE = (
    "使い方: issue-digest [--hide-empty] [--summary] [--only <ラベル>]... [--exclude <ラベル>]..."
    " [--stale <日数>] [--age] [--since <YYYY-MM-DD>]"
    " [--json | --csv] [--sort updated|created] [--limit <件数>] [--show-assignees]"
    " [--show-labels] [--title <文字列>] [--output <パス>] [--diff <前回のJSONのパス>]"
    " [--config <パス>]"
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
    "  --limit で各分類の出力を先頭から指定件数までにする（Markdown は最後に「- ほか N 件」、"
    "JSON は各分類に omitted を加える。件数は全件のまま）\n"
    "  --json で Markdown の代わりに JSON を出力する\n"
    "  --csv で Markdown の代わりに CSV（見出し行 label,number,title,url）を出力する"
    "（--json とは同時に指定できない。--stale、--age、--show-assignees、--show-labels、--summary、"
    "--title は無視する）\n"
    "  --show-assignees で担当者を表示する（Markdown は行末に（担当: @alice）、"
    "JSON は各 Issue に assignees の配列を加える）\n"
    "  --show-labels で agent: で始まらないラベルを表示する"
    "（Markdown は行末に（ラベル: bug, docs）、JSON は各 Issue に labels の配列を加える）\n"
    "  --title で見出しの「Issue ダイジェスト」を指定した文字列に置き換える"
    "（JSON は先頭に title を加える）\n"
    "  --output でダイジェストを標準出力ではなく指定したファイルに書き出す（上書きする）\n"
    "  --diff で前回の --json の出力と比べ、新しい Issue、なくなった Issue、分類が変わった Issue を"
    "出す（Markdown は末尾に「## 前回からの変化」、JSON は diff を加える。--csv では無視する。"
    "前回の JSON は --only、--exclude、--hide-empty、--limit を付けず、"
    "設定ファイルの hide_empty、only も使わずに出力したもの）\n"
    "    例: issue-digest --json --output last.json issues.json で保存し、"
    "次回 issue-digest --diff last.json issues.json\n"
    "  --config で読む設定ファイルを指定する（省略時はカレントディレクトリの .issue-digest.toml。"
    "なければ使わない）。キーは hide_empty、summary、only、stale、sort、show_assignees、json、"
    "headings で、コマンドラインの指定を優先する（sort は updated か created）"
    "（only は --only か --exclude を指定したら使わない）\n"
    '    例: hide_empty = true / stale = 7 / only = ["agent:review", "agent:blocked"]\n'
    "    [headings] テーブルで分類の見出しを変えられる"
    '（例: [headings] の下に "agent:review" = "確認待ち"）\n'
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
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--stale")
    parser.add_argument("--sort")
    parser.add_argument("--limit")
    parser.add_argument("--since")
    parser.add_argument("--output")
    parser.add_argument("--title")
    parser.add_argument("--diff")
    parser.add_argument("--config")
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
    # 設定の json は、コマンドラインの --csv があれば使わない（--csv を優先する）
    as_json = opts.json or (config.get("json", False) and not as_csv)
    only: list[str] = opts.only
    exclude: list[str] = opts.exclude
    if not only and not exclude:
        # コマンドラインで --only も --exclude も指定しないときだけ、設定の only を使う
        only = config.get("only", [])
    show_assignees = opts.show_assignees or config.get("show_assignees", False)
    show_labels = opts.show_labels
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
    limit: int | None = None
    if opts.limit is not None:
        if not (opts.limit.isascii() and opts.limit.isdigit()) or int(opts.limit) < 1:
            print(
                f"エラー: --limit には1以上の整数を指定してください: {opts.limit}",
                file=sys.stderr,
            )
            return 2
        limit = int(opts.limit)
    since: datetime | None = None
    if opts.since is not None:
        since = _parse_since(opts.since)
        if since is None:
            print(
                f"エラー: --since には YYYY-MM-DD の形の日付を指定してください: {opts.since}",
                file=sys.stderr,
            )
            return 2
    headings: dict[str, str] | None = config.get("headings")
    title: str | None = opts.title
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
    if only and exclude:
        print("エラー: --only と --exclude は同時に指定できません", file=sys.stderr)
        return 2
    for option, labels in (("--only", only), ("--exclude", exclude)):
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
        # CSV に列のない --stale、--age、--show-assignees、--show-labels、--summary、--title、
        # --diff は無視する
        digest = format_csv(classified, hide_empty, only_filter, sort, exclude_filter, limit)
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
        )
    if output is None:
        print(digest, end="")
        return 0
    try:
        with open(output, "w", encoding="utf-8", newline="") as f:
            f.write(digest)
    except OSError as e:
        print(f"エラー: ファイルに書き出せません: {output} ({type(e).__name__})", file=sys.stderr)
        return 1
    return 0
