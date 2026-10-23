import argparse
import sys
from datetime import datetime
from importlib.metadata import version

from issue_digest.classifier import CATEGORIES, classify_issues
from issue_digest.formatter import format_digest, format_json
from issue_digest.loader import load_issues, parse_issues

USAGE = (
    "使い方: issue-digest [--hide-empty] [--summary] [--only <ラベル>]... [--stale <日数>]"
    " [--json] [--sort updated] [--show-assignees] [--output <パス>]"
    " <JSONファイルのパス | ->\n"
    "       issue-digest --version\n"
    "  - で標準入力から読む / --hide-empty で0件の分類を出力しない\n"
    "  --only で指定した分類だけを出力する（複数回指定できる）\n"
    "  --summary で見出しの次に全分類の件数を1行で出力する\n"
    "  --stale で最終更新から指定日数以上たった Issue に印を付ける\n"
    "  --sort updated で各分類の中を最終更新の古い順に並べる\n"
    "  --json で Markdown の代わりに JSON を出力する\n"
    "  --show-assignees で担当者を表示する（Markdown は行末に（担当: @alice）、"
    "JSON は各 Issue に assignees の配列を加える）\n"
    "  --output でダイジェストを標準出力ではなく指定したファイルに書き出す（上書きする）\n"
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
    parser.add_argument("--show-assignees", action="store_true")
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--stale")
    parser.add_argument("--sort")
    parser.add_argument("--output")
    parser.add_argument("paths", nargs="*")
    return parser


def main(argv: list[str] | None = None, now: datetime | None = None) -> int:
    """now は --stale の経過日数の基準時刻。省略時は現在時刻（テストで固定できる）。"""
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
    hide_empty = opts.hide_empty
    summary = opts.summary
    as_json = opts.json
    only: list[str] = opts.only
    show_assignees = opts.show_assignees
    output: str | None = opts.output
    stale_days: int | None = None
    if opts.stale is not None:
        if not (opts.stale.isascii() and opts.stale.isdigit()):
            print(
                f"エラー: --stale には0以上の整数を指定してください: {opts.stale}",
                file=sys.stderr,
            )
            return 2
        stale_days = int(opts.stale)
    sort: str | None = opts.sort
    if sort is not None and sort != "updated":
        print(
            f"エラー: --sort に指定できるのは updated だけです: {sort}",
            file=sys.stderr,
        )
        return 2
    paths: list[str] = opts.paths
    if len(paths) != 1:
        print(USAGE, file=sys.stderr)
        return 2
    for label in only:
        if label not in CATEGORIES:
            print(
                f"エラー: --only に指定できないラベルです: {label}\n"
                f"指定できるラベル: {', '.join(CATEGORIES)}",
                file=sys.stderr,
            )
            return 2
    only_filter = only or None
    path = paths[0]
    if path == "-":
        try:
            issues = parse_issues(sys.stdin.read())
        except (OSError, ValueError, KeyError, TypeError) as e:
            print(f"エラー: 標準入力を読み込めません ({type(e).__name__})", file=sys.stderr)
            return 1
    else:
        try:
            issues = load_issues(path)
        except FileNotFoundError:
            print(f"エラー: ファイルが見つかりません: {path}", file=sys.stderr)
            return 1
        except (OSError, ValueError, KeyError, TypeError) as e:
            print(f"エラー: ファイルを読み込めません: {path} ({type(e).__name__})", file=sys.stderr)
            return 1
    classified = classify_issues(issues)
    if as_json:
        # JSON には分類ごとの count があるので、--summary は Markdown のときだけ効く
        digest = format_json(
            classified, hide_empty, only_filter, stale_days, now, sort, show_assignees
        )
    else:
        digest = format_digest(
            classified, hide_empty, only_filter, stale_days, now, sort, summary, show_assignees
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
