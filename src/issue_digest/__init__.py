import json
import sys

from issue_digest.classifier import classify_issues
from issue_digest.formatter import format_digest
from issue_digest.loader import load_issues, parse_issues


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(
            "使い方: issue-digest <JSONファイルのパス | ->  (- で標準入力から読む)", file=sys.stderr
        )
        return 2
    path = args[0]
    if path == "-":
        try:
            issues = parse_issues(sys.stdin.read())
        except (OSError, ValueError, KeyError, TypeError) as e:
            print(f"エラー: 標準入力を読み込めません ({type(e).__name__})", file=sys.stderr)
            return 1
        print(format_digest(classify_issues(issues)), end="")
        return 0
    try:
        issues = load_issues(path)
    except FileNotFoundError:
        print(f"エラー: ファイルが見つかりません: {path}", file=sys.stderr)
        return 1
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"エラー: ファイルを読み込めません: {path} ({type(e).__name__})", file=sys.stderr)
        return 1
    print(format_digest(classify_issues(issues)), end="")
    return 0
