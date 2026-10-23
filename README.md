# issue-digest

GitHub Issue の状況をラベル別にまとめ、Markdown のダイジェストを出力する CLI です。

AI エージェントによる自律開発の練習用プロジェクトでもあります。
タスクは GitHub Issue で管理し、Claude Code が実装、Codex がレビューします。
ルールは [CLAUDE.md](CLAUDE.md)（実装担当向け）と [AGENTS.md](AGENTS.md)（レビュー担当向け）にあります。

## 使い方

`gh issue list --json number,title,labels,url` の出力を渡します。

ファイルを指定する場合:

```
uv run issue-digest issues.json
```

パイプで渡す場合（引数に `-` を指定すると標準入力から読みます）:

```
gh issue list --json number,title,labels,url | uv run issue-digest -
```

`--hide-empty` を付けると、0件の分類の見出しと「なし」を出力しません。対応が必要な分類だけを見たいときに使います。
付けない場合は、0件の分類も見出しと「なし」を出力します。

```
uv run issue-digest --hide-empty issues.json
```

`--only <ラベル>` を付けると、指定したラベルの分類だけを出力します。見たい分類だけを素早く確認したいときに使います。
複数回指定すると、指定したすべての分類を出力します。`--hide-empty` と同時に使えます。
指定できるのは `agent:needs-decision`、`agent:blocked`、`agent:review`、`agent:working`、`agent:ready`、`unclassified`（未分類）の6つです。
それ以外を指定すると、エラーを標準エラーに出して終了コード 2 で終わります。
見出しの総件数は、`--only` に関係なく全件の数のままです。

```
uv run issue-digest --only agent:needs-decision issues.json
uv run issue-digest --only agent:needs-decision --only agent:blocked --hide-empty issues.json
```

`--stale <日数>` を付けると、最終更新から指定日数以上たった Issue の行の末尾に `（N日更新なし）` を付けます。止まっている Issue に気づきたいときに使います。
N は経過日数を切り捨てた整数です。`--hide-empty`、`--only` と同時に使えます。
この印を付けるには、入力の各 Issue に `updatedAt`（ISO 8601 形式。例: `2026-10-20T12:34:56Z`）が必要です。
`gh issue list --json number,title,labels,url,updatedAt` の出力をそのまま渡せます。
`updatedAt` がない Issue には印を付けません。
日数は0以上の整数で指定します。それ以外を指定すると、エラーを標準エラーに出して終了コード 2 で終わります。
`--stale` を付けない場合の出力は変わりません。

```
gh issue list --json number,title,labels,url,updatedAt | uv run issue-digest --stale 7 -
```

`--show-assignees` を付けると、担当者がいる Issue の行の末尾に `（担当: @alice, @bob）` を付けます。誰が対応しているかを知りたいときに使います。
担当者は入力の `assignees` の順に、カンマと空白で区切って並べます。担当者がいない Issue には何も付けません。
`assignees` がない入力でもエラーにはならず、担当者なしとして扱います。
`--stale` の印と両方付くときは、`（N日更新なし）（担当: @alice）` の順です。
`--show-assignees` を付けない場合の出力は変わりません。

```
gh issue list --json number,title,labels,url,assignees | uv run issue-digest --show-assignees -
```

`--version` を付けると、`issue-digest 0.1.0` のようにバージョンを1行で出力し、終了コード 0 で終わります。
バージョンは `pyproject.toml` の値です。ほかのオプションやファイルが指定されていても、バージョンだけを出力します（ファイルは読みません）。
`--version` を付けない場合の動作は変わりません。

```
uv run issue-digest --version
```
