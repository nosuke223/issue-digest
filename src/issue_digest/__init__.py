import json
import sys

from issue_digest.classifier import CATEGORIES, classify_issues
from issue_digest.formatter import format_digest
from issue_digest.loader import load_issues, parse_issues

USAGE = (
    "使い方: issue-digest [--hide-empty] [--only <ラベル>]... <JSONファイルのパス | ->\n"
    "  - で標準入力から読む / --hide-empty で0件の分類を出力しない\n"
    "  --only で指定した分類だけを出力する（複数回指定できる）"
)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    hide_empty = False
    only: list[str] = []
    paths: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--hide-empty":
            hide_empty = True
        elif arg == "--only":
            i += 1
            if i >= len(args):
                print(USAGE, file=sys.stderr)
                return 2
            only.append(args[i])
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
    path = paths[0]
    if path == "-":
        try:
            issues = parse_issues(sys.stdin.read())
        except (OSError, ValueError, KeyError, TypeError) as e:
            print(f"エラー: 標準入力を読み込めません ({type(e).__name__})", file=sys.stderr)
            return 1
        print(format_digest(classify_issues(issues), hide_empty, only_filter), end="")
        return 0
    try:
        issues = load_issues(path)
    except FileNotFoundError:
        print(f"エラー: ファイルが見つかりません: {path}", file=sys.stderr)
        return 1
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"エラー: ファイルを読み込めません: {path} ({type(e).__name__})", file=sys.stderr)
        return 1
    print(format_digest(classify_issues(issues), hide_empty, only_filter), end="")
    return 0
