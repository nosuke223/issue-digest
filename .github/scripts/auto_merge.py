"""エージェントの PR が、自動マージの条件を満たしているかを判定する（GitHub Actions で動かす）。

条件は agent-env の PLAN.md「自動マージの方式」のとおり。判定に使うのは GitHub 上の記録だけで、
エージェントが書いた印（PR のラベルなど）は信じない。

環境変数:
    GH_TOKEN       GitHub Actions のトークン
    REPO           所有者/リポジトリ
    AGENT_ACCOUNT  エージェントの GitHub アカウント
    AUTO_MERGE     off: 何もしない / dry-run（未設定も同じ）: 判定の結果をコメントするだけ

標準ライブラリと gh だけで動く。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

CODEX_BOT = "chatgpt-codex-connector[bot]"
CODEX_STATE_RE = re.compile(r"<!-- codex-review-state:v1 (\{.*?\}) -->", re.DOTALL)
AUTO_LABEL = "merge:auto"
TEST_CHECK = "test"
MARKER = "<!-- auto-merge-check sha={sha} -->"
# 変えていたら人が見る（ルール、設定、CI、依存）
CAREFUL_PREFIXES = (".github/", ".claude/", ".env")
CAREFUL_NAMES = {"pyproject.toml", "uv.lock", "CLAUDE.md", "AGENTS.md"}


def gh_api(path: str, paginate: bool = False):
    cmd = ["gh", "api", path] + (["--paginate", "--slurp"] if paginate else [])
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    if paginate:
        return [item for page in data for item in page]
    return data


def gh_graphql(query: str, **variables) -> dict:
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        cmd += ["-F", f"{key}={value}"]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    return json.loads(out)["data"]


# 判定（GitHub に触れない部分）


def issue_number_of(branch: str, closing: list[int]) -> int | None:
    """ブランチ名 issue-<N>-... と、PR が閉じる Issue が同じ1件を指していれば、その番号。"""
    m = re.match(r"issue-(\d+)-", branch)
    if not m or closing != [int(m.group(1))]:
        return None
    return int(m.group(1))


def label_added_by(events: list, label: str) -> str | None:
    """ラベルを最後に付けたアカウント。今付いているかは呼び出し側で確かめる。"""
    actor = None
    for e in events:
        if e.get("event") == "labeled" and (e.get("label") or {}).get("name") == label:
            actor = (e.get("actor") or {}).get("login")
    return actor


def codex_state(comments: list) -> dict | None:
    """Codex のまとめのコメントに埋め込まれた状態のうち、最新のもの。"""
    latest = None
    for c in comments:
        if (c.get("user") or {}).get("login") != CODEX_BOT:
            continue
        m = CODEX_STATE_RE.search(c.get("body") or "")
        if not m:
            continue
        try:
            review = json.loads(m.group(1)).get("code_review") or {}
        except ValueError:
            continue
        if review.get("commit_sha"):
            latest = review
    return latest


def codex_clean(state: dict | None, head: str) -> bool | None:
    """True: 最新のコミットに指摘なし / False: 指摘あり / None: まだ（レビュー中など）。"""
    if not state or state.get("commit_sha") != head or state.get("status") != "completed":
        return None
    return not state.get("has_any_findings")


def test_result(check_runs: list) -> bool | None:
    """True: test が成功 / False: 失敗 / None: まだ（ないか、実行中）。"""
    runs = [r for r in check_runs if r.get("name") == TEST_CHECK]
    if not runs or any(r.get("status") != "completed" for r in runs):
        return None
    return all(r.get("conclusion") == "success" for r in runs)


def careful_files(files: list[str]) -> list[str]:
    return [f for f in files if f.startswith(CAREFUL_PREFIXES) or f in CAREFUL_NAMES]


def judge(facts: dict) -> tuple[str, list[str]]:
    """facts から、("wait" | "ok" | "ng", 満たしていない条件) を返す。

    wait は、まだ決められない（Codex のレビューかテストが終わっていない、Codex の指摘があり
    ランナーが直させる途中、衝突の判定中）。コメントせずに次の回を待つ。
    """
    if facts["codex"] is not True or facts["test"] is None or facts["mergeable"] is None:
        return "wait", []
    reasons = []
    if facts["label_actor"] != facts["owner"]:
        reasons.append(f"`{AUTO_LABEL}` を付けたのが所有者ではない（{facts['label_actor']}）")
    if facts["owner_comments"]:
        reasons.append(
            f"Issue に所有者のコメントが {facts['owner_comments']} 件ある"
            "（Codex はコメントの仕様を読めない）"
        )
    if facts["test"] is False:
        reasons.append("GitHub 上のテストか lint が失敗している")
    if facts["careful"]:
        reasons.append("ルールや設定のファイルを変えている: " + ", ".join(facts["careful"]))
    if facts["mergeable"] is False:
        reasons.append("main と衝突している")
    return ("ng" if reasons else "ok"), reasons


def comment_body(verdict: str, reasons: list[str], sha: str) -> str:
    if verdict == "ok":
        text = "🤖 自動マージの判定（試運転）: 条件を満たしています。本番ならマージします。"
    else:
        text = "🤖 自動マージの判定（試運転）: 条件を満たしていません。\n\n" + "\n".join(
            f"- {r}" for r in reasons
        )
    return f"{text}\n\n対象のコミット: `{sha[:7]}`\n{MARKER.format(sha=sha)}"


# GitHub から事実を集める

CLOSING_QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      closingIssuesReferences(first: 10) { nodes { number } }
    }
  }
}
"""


def collect(repo: str, owner: str, pr: dict) -> tuple[int | None, dict | None]:
    """PR の Issue 番号と、判定に使う事実。対象外なら (None, None)。"""
    name = repo.split("/", 1)[1]
    data = gh_graphql(CLOSING_QUERY, owner=owner, name=name, number=pr["number"])
    refs = data["repository"]["pullRequest"]["closingIssuesReferences"]["nodes"]
    closing = [n["number"] for n in refs]
    number = issue_number_of(pr["head"]["ref"], closing)
    if number is None:
        return None, None
    issue = gh_api(f"repos/{repo}/issues/{number}")
    if AUTO_LABEL not in {label["name"] for label in issue.get("labels", [])}:
        return number, None
    head = pr["head"]["sha"]
    detail = gh_api(f"repos/{repo}/pulls/{pr['number']}")
    events = gh_api(f"repos/{repo}/issues/{number}/events", paginate=True)
    issue_comments = gh_api(f"repos/{repo}/issues/{number}/comments", paginate=True)
    pr_comments = gh_api(f"repos/{repo}/issues/{pr['number']}/comments", paginate=True)
    checks = gh_api(f"repos/{repo}/commits/{head}/check-runs?per_page=100")
    files = gh_api(f"repos/{repo}/pulls/{pr['number']}/files", paginate=True)
    facts = {
        "owner": owner,
        "label_actor": label_added_by(events, AUTO_LABEL),
        "owner_comments": sum(1 for c in issue_comments if c["user"]["login"] == owner),
        "codex": codex_clean(codex_state(pr_comments), head),
        "test": test_result(checks.get("check_runs", [])),
        "careful": careful_files([f["filename"] for f in files]),
        "mergeable": detail.get("mergeable"),
        "pr_comments": pr_comments,
    }
    return number, facts


def already_commented(comments: list, sha: str) -> bool:
    marker = MARKER.format(sha=sha)
    return any(marker in (c.get("body") or "") for c in comments)


def main() -> int:
    mode = os.environ.get("AUTO_MERGE") or "dry-run"
    if mode == "off":
        print("AUTO_MERGE=off のため、何もしません")
        return 0
    repo = os.environ["REPO"]
    owner = repo.split("/", 1)[0]
    agent = os.environ["AGENT_ACCOUNT"]
    for pr in gh_api(f"repos/{repo}/pulls?state=open&per_page=100"):
        if pr["user"]["login"] != agent or pr.get("draft"):
            continue
        number, facts = collect(repo, owner, pr)
        if facts is None:
            continue
        verdict, reasons = judge(facts)
        sha = pr["head"]["sha"]
        print(f"PR #{pr['number']}（Issue #{number}）: {verdict} {reasons}")
        if verdict == "wait" or already_commented(facts["pr_comments"], sha):
            continue
        body = comment_body(verdict, reasons, sha)
        subprocess.run(
            ["gh", "pr", "comment", str(pr["number"]), "-R", repo, "--body", body], check=True
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
