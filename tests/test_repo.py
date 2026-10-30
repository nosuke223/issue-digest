import io
import json
import subprocess

import pytest
from conftest import DATA, json_out

from issue_digest import USAGE, github, main

REPO_A = str(DATA / "multi_repo_a.json")
REPO_B = str(DATA / "multi_repo_b.json")
OUTPUT_A = (DATA / "multi_repo_a.json").read_bytes()
OUTPUT_B = (DATA / "multi_repo_b.json").read_bytes()

GH_FIELDS = "number,title,labels,url,updatedAt,createdAt,assignees,milestone,author"


class FakeGh:
    """gh の代わりに、リポジトリごとに決めた出力を返す。呼ばれたときの引数を記録する。"""

    def __init__(self, outputs=None, returncode=0, stderr=b"", error=None):
        self.outputs = outputs or {}
        self.returncode = returncode
        self.stderr = stderr
        self.error = error
        self.calls: list[list[str]] = []

    def __call__(self, args):
        self.calls.append(args)
        if self.error is not None:
            raise self.error
        repo = args[args.index("-R") + 1]
        return subprocess.CompletedProcess(
            args, self.returncode, self.outputs.get(repo, b"[]"), self.stderr
        )


def gh_args(repo):
    return [
        "gh",
        "issue",
        "list",
        "-R",
        repo,
        "--state",
        "open",
        "-L",
        "1000",
        "--json",
        GH_FIELDS,
    ]


@pytest.fixture
def fake_gh():
    return FakeGh({"alpha/tools": OUTPUT_A, "Beta/app": OUTPUT_B})


def file_output(capsys, args):
    assert main(args) == 0
    return capsys.readouterr().out


def test_main_repo_makes_digest_from_gh(capsys, fake_gh):
    expected = file_output(capsys, [REPO_A])
    assert main(["--repo", "alpha/tools"], run=fake_gh) == 0
    captured = capsys.readouterr()
    assert captured.out == expected
    assert captured.err == ""
    assert fake_gh.calls == [gh_args("alpha/tools")]


def test_main_two_repos_are_merged_with_repository_names(capsys, fake_gh):
    expected = file_output(capsys, [REPO_A, REPO_B])
    assert main(["--repo", "alpha/tools", "--repo", "Beta/app"], run=fake_gh) == 0
    out = capsys.readouterr().out
    assert out == expected
    assert "- [alpha/tools#1](" in out
    assert "- [Beta/app#1](" in out
    assert fake_gh.calls == [gh_args("alpha/tools"), gh_args("Beta/app")]


def test_main_file_inputs_come_before_repos(capsys, fake_gh):
    # --repo を先に書いても、ファイル入力の後に読む（重複する #2 はファイルのものを使う）
    expected = file_output(capsys, [REPO_B, REPO_A])
    assert main(["--repo", "alpha/tools", REPO_B], run=fake_gh) == 0
    assert capsys.readouterr().out == expected


def test_main_stdin_and_repo_can_be_mixed(capsys, monkeypatch, fake_gh):
    expected = file_output(capsys, [REPO_A, REPO_B])
    monkeypatch.setattr("sys.stdin", io.StringIO(OUTPUT_A.decode("utf-8")))
    assert main(["-", "--repo", "Beta/app"], run=fake_gh) == 0
    assert capsys.readouterr().out == expected


def test_main_without_file_and_repo_prints_usage(capsys, fake_gh):
    assert main([], run=fake_gh) == 2
    captured = capsys.readouterr()
    assert captured.err == USAGE + "\n"
    assert captured.out == ""
    assert fake_gh.calls == []


def test_main_same_repo_twice_is_not_error(capsys, fake_gh):
    expected = file_output(capsys, [REPO_A])
    assert main(["--repo", "alpha/tools", "--repo", "alpha/tools"], run=fake_gh) == 0
    assert capsys.readouterr().out == expected
    assert fake_gh.calls == [gh_args("alpha/tools")]


def test_main_host_owner_repo_is_passed_to_gh(capsys):
    gh = FakeGh()
    assert main(["--repo", "ghe.example.com/Org/my_repo-1.x"], run=gh) == 0
    assert gh.calls == [gh_args("ghe.example.com/Org/my_repo-1.x")]


def many_issues(count):
    return json.dumps(
        [
            {
                "number": n,
                "title": f"Issue {n}",
                "labels": [],
                "url": f"https://github.com/o/r/issues/{n}",
            }
            for n in range(1, count + 1)
        ]
    ).encode("utf-8")


def test_main_warns_when_1000_issues_are_fetched(capsys):
    assert main(["--repo", "o/r"], run=FakeGh({"o/r": many_issues(1000)})) == 0
    captured = capsys.readouterr()
    assert captured.err == (
        "警告: o/r の Issue を1000件取得しました。これ以上ある場合は、一部が含まれていません\n"
    )
    assert captured.out.startswith("# Issue ダイジェスト（全 1000 件）\n")


def test_main_does_not_warn_when_999_issues_are_fetched(capsys):
    assert main(["--repo", "o/r"], run=FakeGh({"o/r": many_issues(999)})) == 0
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize("value", ["-x/y", "a", "a/b/c/d", "", "a/", "/b", "a b/c", "a/b;c", "-"])
def test_main_invalid_repo_is_error_without_gh(capsys, value):
    gh = FakeGh()
    assert main(["--repo", value, REPO_A], run=gh) == 2
    captured = capsys.readouterr()
    assert captured.err == (
        f"エラー: --repo には OWNER/REPO か HOST/OWNER/REPO の形を指定してください: {value}\n"
    )
    assert captured.out == ""
    assert gh.calls == []


def test_main_invalid_second_repo_is_error_without_gh(capsys):
    gh = FakeGh()
    assert main(["--repo", "o/r", "--repo", "a/b/c/d"], run=gh) == 2
    assert gh.calls == []


@pytest.mark.parametrize("args", [["--repo"], [REPO_A, "--repo"], ["--repo", "--json"]])
def test_main_repo_without_value_is_usage_error(capsys, args):
    gh = FakeGh()
    assert main(args, run=gh) == 2
    captured = capsys.readouterr()
    assert captured.err == USAGE + "\n"
    assert gh.calls == []


def test_main_gh_not_found(capsys):
    gh = FakeGh(error=FileNotFoundError("gh"))
    assert main(["--repo", "o/r"], run=gh) == 1
    captured = capsys.readouterr()
    assert captured.err == "エラー: gh コマンドが見つかりません\n"
    assert captured.out == ""


def test_main_gh_failed(capsys):
    gh = FakeGh(
        returncode=1,
        stderr=b"\nGraphQL: Could not resolve to a Repository with the name 'o/r'.\nmore\n",
    )
    assert main(["--repo", "o/r"], run=gh) == 1
    captured = capsys.readouterr()
    assert captured.err == (
        "エラー: gh issue list に失敗しました: o/r"
        "（GraphQL: Could not resolve to a Repository with the name 'o/r'.）\n"
    )
    assert captured.out == ""


def test_main_gh_failed_without_stderr(capsys):
    assert main(["--repo", "o/r"], run=FakeGh(returncode=4)) == 1
    assert capsys.readouterr().err == "エラー: gh issue list に失敗しました: o/r（終了コード 4）\n"


def test_main_gh_timeout(capsys):
    gh = FakeGh(error=subprocess.TimeoutExpired(gh_args("o/r"), 60))
    assert main(["--repo", "o/r"], run=gh) == 1
    captured = capsys.readouterr()
    assert captured.err == "エラー: gh issue list が60秒で終わりませんでした: o/r\n"
    assert captured.out == ""


def test_main_error_in_second_repo_prints_nothing(capsys, tmp_path):
    output = tmp_path / "digest.md"
    gh = FakeGh({"alpha/tools": OUTPUT_A})
    gh_fail = FakeGh(returncode=1, stderr=b"HTTP 404: Not Found\n")

    def run(args):
        return (gh if args[4] == "alpha/tools" else gh_fail)(args)

    args = ["--output", str(output), "--repo", "alpha/tools", "--repo", "x/y"]
    assert main(args, run=run) == 1
    captured = capsys.readouterr()
    assert captured.err == "エラー: gh issue list に失敗しました: x/y（HTTP 404: Not Found）\n"
    assert captured.out == ""
    assert not output.exists()


@pytest.mark.parametrize(
    ("output", "error"),
    [(b"{", "JSONDecodeError"), (b"\xff", "UnicodeDecodeError"), (b"[{}]", "KeyError")],
)
def test_main_unreadable_gh_output(capsys, output, error):
    assert main(["--repo", "o/r"], run=FakeGh({"o/r": output})) == 1
    captured = capsys.readouterr()
    assert captured.err == f"エラー: gh issue list の出力を読み込めません: o/r ({error})\n"
    assert captured.out == ""


def test_main_invalid_updated_at_in_gh_output(capsys):
    output = b'[{"number": 7, "title": "t", "labels": [], "url": "u", "updatedAt": "x"}]'
    assert main(["--repo", "o/r"], run=FakeGh({"o/r": output})) == 1
    assert capsys.readouterr().err == (
        "エラー: --repo o/r: Issue #7 の updatedAt を日時として読めません: x\n"
    )


@pytest.mark.parametrize("key", ["updatedAt", "createdAt"])
def test_main_invalid_date_names_the_second_repo(capsys, key):
    issue = {"number": 1, "title": "t", "labels": [], "updatedAt": "2026-10-20T00:00:00Z"}
    good = json.dumps([{**issue, "url": "https://github.com/beta/good/issues/1"}]).encode()
    bad_issue = {**issue, "url": "https://github.com/alpha/bad/issues/1", key: "yesterday"}
    bad = json.dumps([bad_issue]).encode()
    run = FakeGh({"beta/good": good, "alpha/bad": bad})
    assert main(["--repo", "beta/good", "--repo", "alpha/bad"], run=run) == 1
    assert capsys.readouterr().err == (
        f"エラー: --repo alpha/bad: Issue #1 の {key} を日時として読めません: yesterday\n"
    )


@pytest.mark.parametrize(
    "options",
    [
        ["--json"],
        ["--csv"],
        ["--group-by", "assignee"],
        ["--summary", "--only", "agent:ready", "--sort", "updated", "--reverse", "--limit", "1"],
        ["--json", "--show-assignees", "--stale", "3", "--since", "2026-10-02"],
    ],
)
def test_main_repo_works_like_files_with_options(capsys, fake_gh, options):
    expected = file_output(capsys, [*options, REPO_A, REPO_B])
    assert main([*options, "--repo", "alpha/tools", "--repo", "Beta/app"], run=fake_gh) == 0
    assert capsys.readouterr().out == expected


def test_main_repo_with_diff(capsys, tmp_path, fake_gh):
    previous = tmp_path / "previous.json"
    assert main(["--json", "--output", str(previous), "--repo", "Beta/app"], run=fake_gh) == 0
    expected = file_output(capsys, ["--diff", str(previous), REPO_A])
    assert main(["--diff", str(previous), "--repo", "alpha/tools"], run=fake_gh) == 0
    out = capsys.readouterr().out
    assert out == expected
    assert "## 前回からの変化" in out


def test_main_repo_with_fail_if_any(capsys, fake_gh):
    assert main(["--fail-if-any", "agent:needs-decision", "--repo", "Beta/app"], run=fake_gh) == 3
    assert "## 判断待ち (agent:needs-decision) - 1件" in capsys.readouterr().out
    assert main(["--fail-if-any", "agent:blocked", "--repo", "Beta/app"], run=fake_gh) == 0


def test_main_repo_json_has_repository(capsys, fake_gh):
    assert main(["--json", "--repo", "Beta/app"], run=fake_gh) == 0
    ready = next(c for c in json_out(capsys)["categories"] if c["label"] == "agent:ready")
    assert [i["repository"] for i in ready["issues"]] == ["Beta/app"]


def test_run_gh_uses_argument_list_without_shell(monkeypatch):
    # 本物の gh は呼ばず、subprocess.run に渡す値だけを確かめる
    recorded = {}

    def fake_run(args, **kwargs):
        recorded["args"] = args
        recorded["kwargs"] = kwargs
        return subprocess.CompletedProcess(args, 0, b"[]", b"")

    monkeypatch.setattr(github.subprocess, "run", fake_run)
    github.run_gh(gh_args("o/r"))
    assert recorded["args"] == gh_args("o/r")
    assert recorded["kwargs"]["timeout"] == 60
    assert recorded["kwargs"].get("shell", False) is False
    assert recorded["kwargs"]["capture_output"] is True


def test_main_usage_mentions_repo(capsys):
    assert main(["--help"]) == 0
    out = capsys.readouterr().out
    assert "[--repo <OWNER/REPO>]..." in out
    assert "--repo で gh issue list -R <OWNER/REPO> --state open -L 1000" in out
