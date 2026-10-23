import sys
from datetime import datetime
from importlib.metadata import version

from issue_digest.classifier import CATEGORIES, classify_issues
from issue_digest.formatter import format_digest, format_json
from issue_digest.loader import load_issues, parse_issues

USAGE = (
    "使い方: issue-digest [--hide-empty] [--only <ラベル>]... [--stale <日数>] [--json]"
    " [--output <パス>] <JSONファイルのパス | ->\n"
    "       issue-digest --version\n"
    "  - で標準入力から読む / --hide-empty で0件の分類を出力しない\n"
    "  --only で指定した分類だけを出力する（複数回指定できる）\n"
    "  --stale で最終更新から指定日数以上たった Issue に印を付ける\n"
    "  --json で Markdown の代わりに JSON を出力する\n"
    "  --output でダイジェストを標準出力ではなく指定したファイルに書き出す（上書きする）\n"
    "  --version でバージョンだけを出力する（ほかの指定は無視する）"
)


def main(argv: list[str] | None = None, now: datetime | None = None) -> int:
    """now は --stale の経過日数の基準時刻。省略時は現在時刻（テストで固定できる）。"""
    args = sys.argv[1:] if argv is None else argv
    if "--version" in args:
        print(f"issue-digest {version('issue-digest')}")
        return 0
    hide_empty = False
    as_json = False
    only: list[str] = []
    stale_days: int | None = None
    output: str | None = None
    paths: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--hide-empty":
            hide_empty = True
        elif arg == "--json":
            as_json = True
        elif arg == "--only":
            i += 1
            if i >= len(args):
                print(USAGE, file=sys.stderr)
                return 2
            only.append(args[i])
        elif arg == "--stale":
            i += 1
            if i >= len(args):
                print(USAGE, file=sys.stderr)
                return 2
            if not (args[i].isascii() and args[i].isdigit()):
                print(
                    f"エラー: --stale には0以上の整数を指定してください: {args[i]}",
                    file=sys.stderr,
                )
                return 2
            stale_days = int(args[i])
        elif arg == "--output":
            i += 1
            if i >= len(args):
                print(USAGE, file=sys.stderr)
                return 2
            output = args[i]
        else:
            paths.append(arg)
        i += 1
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
    render = format_json if as_json else format_digest
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
    digest = render(classify_issues(issues), hide_empty, only_filter, stale_days, now)
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
