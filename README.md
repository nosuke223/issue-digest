# issue-digest

GitHub Issue の状況をラベル別にまとめ、Markdown のダイジェストを出力する CLI です。

AI エージェントによる自律開発の練習用プロジェクトでもあります。
タスクは GitHub Issue で管理し、Claude Code が実装、Codex がレビューします。
ルールは [CLAUDE.md](CLAUDE.md)（実装担当向け）と [AGENTS.md](AGENTS.md)（レビュー担当向け）にあります。

これまでの変更は [CHANGELOG.md](CHANGELOG.md) にまとめています。

## インストールと実行する場所

### プロジェクトのフォルダの中で実行する

このリポジトリのフォルダの中では、`uv run issue-digest ...` で実行できます。この README の例はすべてこの形です。

### 別のフォルダから実行する

cron や、ほかのリポジトリの作業フォルダから使うときは、`--project` にこのリポジトリのパスを渡します。

```
uv run --project <プロジェクトのパス> issue-digest issues.json
```

`issues.json` などの入力ファイルは、実行したフォルダからの相対パスで指定します。

### 設定ファイルの探し方

設定ファイル `.issue-digest.toml` は、プロジェクトのフォルダではなく、実行したときのカレントディレクトリから探します。
別のフォルダで実行するときは、次のどちらかにします。

- `--config <パス>` で設定ファイルを指定する
- 実行するフォルダに `.issue-digest.toml` を置く

```
uv run --project <プロジェクトのパス> issue-digest --config <設定ファイルのパス> issues.json
```

## 使い方

`gh issue list -L 1000 --json number,title,labels,url` の出力を渡します。
`gh issue list` は件数を指定しないと最初の30件で切られるので、パイプで渡すときは `-L` で件数を指定してください。
複数のリポジトリの出力を並べて渡すと、1つのダイジェストにまとめます（「[入力](docs/input.md#入力)」を参照）。
`--repo` を付けると、`gh` を自分で実行しなくても、GitHub から直接取得できます（「[`--repo <OWNER/REPO>`](docs/input.md#--repo-ownerrepo)」を参照）。

```
uv run issue-digest issues.json
uv run issue-digest repo-a.json repo-b.json
uv run issue-digest --repo owner/repo
```

### オプション一覧

| オプション | 何をするか | 例 |
| --- | --- | --- |
| [`-`](docs/input.md#入力) | 標準入力から読む（ほかの入力と混ぜられる。1回まで） | `gh issue list -L 1000 --json number,title,labels,url \| uv run issue-digest -` |
| [`--repo <OWNER/REPO>`](docs/input.md#--repo-ownerrepo) | `gh` を実行して、指定したリポジトリの開いている Issue を取得する（複数回指定できる。ファイル入力と混ぜられる） | `uv run issue-digest --repo nosuke223/issue-digest` |
| `-h` / `--help` | 使い方を出力する | `uv run issue-digest --help` |
| [`--version`](docs/options.md#--version) | バージョンだけを出力する | `uv run issue-digest --version` |
| [`--hide-empty`](docs/options.md#--hide-empty) | 0件の分類を出力しない | `uv run issue-digest --hide-empty issues.json` |
| [`--only <ラベル>`](docs/options.md#--only-ラベル) | 指定したラベルの分類だけを出力する（複数回指定できる） | `uv run issue-digest --only agent:needs-decision issues.json` |
| [`--exclude <ラベル>`](docs/options.md#--exclude-ラベル) | 指定したラベルの分類を出力しない（複数回指定できる。`--only` とは同時に使えない） | `uv run issue-digest --exclude unclassified issues.json` |
| [`--stale <日数>`](docs/options.md#--stale-日数) | 最終更新から指定日数以上たった Issue に `（N日更新なし）` を付ける | `uv run issue-digest --stale 7 issues.json` |
| [`--since <日付>`](docs/options.md#--since-日付) | 最終更新が指定日（`YYYY-MM-DD`、UTC の0時）以降、または `7d` のように基準時刻の N 日前以降の Issue だけを出力する | `uv run issue-digest --since 2026-10-01 issues.json` / `uv run issue-digest --since 7d issues.json` |
| [`--until <日付>`](docs/options.md#--until-日付) | 最終更新が指定日（`YYYY-MM-DD`）の UTC の終わりまで（翌日0時より前）の Issue だけを出力する（`--since` と一緒に使うと期間で絞れる） | `uv run issue-digest --since 2026-10-01 --until 2026-10-31 issues.json` |
| [`--sort updated`](docs/options.md#--sort-updated) | 各分類の中を最終更新の古い順に並べる | `uv run issue-digest --sort updated issues.json` |
| [`--sort created`](docs/options.md#--sort-created) | 各分類の中を作成日時の古い順に並べる | `uv run issue-digest --sort created issues.json` |
| [`--sort number`](docs/options.md#--sort-number) | 各分類の中を Issue の番号の小さい順に並べる | `uv run issue-digest --sort number issues.json` |
| [`--reverse`](docs/options.md#--reverse) | 各分類の中の並びを逆にする（`--sort` がなければリポジトリ名と番号の逆順、あれば新しい順） | `uv run issue-digest --reverse issues.json` |
| [`--limit <件数>`](docs/options.md#--limit-件数) | 各分類で、先頭から指定件数だけ Issue を出力する | `uv run issue-digest --limit 5 issues.json` |
| [`--max-chars <文字数>`](docs/options.md#--max-chars-文字数) | Markdown の出力全体を指定文字数以内に収める（収まらない分の Issue の行を `- ほか N 件` にする） | `uv run issue-digest --max-chars 2000 issues.json` |
| [`--summary`](docs/options.md#--summary) | 総件数の次に、分類ごとの件数を1行で出力する | `uv run issue-digest --summary issues.json` |
| [`--show-assignees`](docs/options.md#--show-assignees) | 担当者がいる Issue に `（担当: @alice）` を付ける | `uv run issue-digest --show-assignees issues.json` |
| [`--show-author`](docs/options.md#--show-author) | 作成者がある Issue に `（作成者: @alice）` を付ける | `uv run issue-digest --show-author issues.json` |
| [`--show-labels`](docs/options.md#--show-labels) | `agent:` で始まらないラベル（設定の `[category_labels]` に書いたラベルを除く）がある Issue に `（ラベル: bug, docs）` を付ける | `uv run issue-digest --show-labels issues.json` |
| [`--age`](docs/options.md#--age) | 作成日時（`createdAt`）がある Issue に `（作成から12日）` を付ける | `uv run issue-digest --age issues.json` |
| [`--show-milestone`](docs/options.md#--show-milestone) | マイルストーンがある Issue に `（マイルストーン: v1.0）` を付ける | `uv run issue-digest --show-milestone issues.json` |
| [`--json`](docs/options.md#--json) | Markdown の代わりに JSON を出力する | `uv run issue-digest --json issues.json` |
| [`--csv`](docs/options.md#--csv) | Markdown の代わりに CSV を出力する | `uv run issue-digest --csv issues.json` |
| [`--title <文字列>`](docs/options.md#--title-文字列) | 見出しの `Issue ダイジェスト` を指定した文字列に置き換える | `uv run issue-digest --title issue-digest issues.json` |
| [`--output <パス>`](docs/options.md#--output-パス) | 標準出力ではなく、指定したファイルに書き出す | `uv run issue-digest --output digest.md issues.json` |
| [`--diff <前回のJSONのパス>`](docs/options.md#--diff-前回のjsonのパス) | 前回の `--json` の出力と比べ、変化した Issue を末尾に出す | `uv run issue-digest --diff last.json issues.json` |
| [`--fail-if-any <ラベル>`](docs/options.md#--fail-if-any-ラベル) | 指定したラベルの分類に Issue が1件以上あるとき、終了コード 3 で終わる（複数回指定できる。設定ファイルの `fail_if_any` にも書ける） | `uv run issue-digest --fail-if-any agent:blocked issues.json` |
| [`--config <パス>`](docs/config.md#設定ファイルと---config-パス) | 読む設定ファイルを指定する（省略時はカレントディレクトリの `.issue-digest.toml`） | `uv run issue-digest --config my.toml issues.json` |
| [`--group-by assignee`](docs/options.md#--group-by-assignee) | 分類ごとの代わりに、担当者ごとの見出しで並べる（Markdown だけ） | `uv run issue-digest --group-by assignee issues.json` |

## 詳しい説明

- [docs/input.md](docs/input.md): 入力の渡し方（ファイル、標準入力、複数の入力）、読めない入力のエラー、`--repo` での取得、リポジトリ名の表示と既定の並び
- [docs/options.md](docs/options.md): オプションごとの詳しい説明（タイトルの長さ、`--hide-empty` から `--version` まで）
- [docs/config.md](docs/config.md): 設定ファイル（`.issue-digest.toml`）と `--config` で書けるキー、コマンドラインとの優先順位、`[headings]`、`[category_labels]`
- [docs/combinations.md](docs/combinations.md): オプションを同時に指定したときの決まり
- [docs/exit-codes.md](docs/exit-codes.md): 終了コードの一覧と、cron で使う例
