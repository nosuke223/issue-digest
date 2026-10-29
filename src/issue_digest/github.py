import re
import subprocess
from collections.abc import Callable

# --stale などの指定に関係なく、ダイジェストに使うすべての項目を毎回取得する
FIELDS = "number,title,labels,url,updatedAt,createdAt,assignees,milestone"
LIMIT = 1000
TIMEOUT_SECONDS = 60

# OWNER/REPO または HOST/OWNER/REPO。各部分は英数字、.、_、- だけ
_REPO = re.compile(r"[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+){1,2}")

# gh の引数のリストを受け取って実行する関数（テストで差し替える）
Runner = Callable[[list[str]], subprocess.CompletedProcess]


class FetchError(Exception):
    """gh issue list で Issue を取得できなかったときのエラー。"""


def is_valid_repo(value: str) -> bool:
    """--repo の値が OWNER/REPO か HOST/OWNER/REPO の形か。- で始まる値は gh のオプションと
    見なされるため使えない。"""
    return not value.startswith("-") and _REPO.fullmatch(value) is not None


def gh_args(repo: str) -> list[str]:
    return [
        "gh",
        "issue",
        "list",
        "-R",
        repo,
        "--state",
        "open",
        "-L",
        str(LIMIT),
        "--json",
        FIELDS,
    ]


def run_gh(args: list[str]) -> subprocess.CompletedProcess:
    """シェルを通さずに実行する。出力はバイト列のまま返す（読めないときのエラーは呼び出し側で出す）。"""
    return subprocess.run(
        args,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )


def fetch_issue_list(repo: str, run: Runner = run_gh) -> bytes:
    """gh issue list で開いている Issue を取得し、その出力（JSON のバイト列）を返す。"""
    try:
        result = run(gh_args(repo))
    except FileNotFoundError as e:
        raise FetchError("gh コマンドが見つかりません") from e
    except subprocess.TimeoutExpired as e:
        raise FetchError(f"gh issue list が{TIMEOUT_SECONDS}秒で終わりませんでした: {repo}") from e
    except OSError as e:
        raise FetchError(f"gh issue list に失敗しました: {repo}（{type(e).__name__}）") from e
    if result.returncode != 0:
        reason = _first_line(result.stderr, result.returncode)
        raise FetchError(f"gh issue list に失敗しました: {repo}（{reason}）")
    return result.stdout


def _first_line(stderr: bytes | None, returncode: int) -> str:
    """gh の標準エラーの最初の（空でない）1行。標準エラーが空なら終了コードを示す。"""
    text = (stderr or b"").decode("utf-8", errors="replace")
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return f"終了コード {returncode}"
