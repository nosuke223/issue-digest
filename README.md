# issue-digest

GitHub Issue の状況をラベル別にまとめ、Markdown のダイジェストを出力する CLI です。

AI エージェントによる自律開発の練習用プロジェクトでもあります。
タスクは GitHub Issue で管理し、Claude Code が実装、Codex がレビューします。
ルールは [CLAUDE.md](CLAUDE.md)（実装担当向け）と [AGENTS.md](AGENTS.md)（レビュー担当向け）にあります。

これまでの変更は [CHANGELOG.md](CHANGELOG.md) にまとめています。

## 使い方

`gh issue list --json number,title,labels,url` の出力を渡します。

### オプション一覧

| オプション | 何をするか | 例 |
| --- | --- | --- |
| `-` | 標準入力から読む | `gh issue list --json number,title,labels,url \| uv run issue-digest -` |
| `-h` / `--help` | 使い方を出力する | `uv run issue-digest --help` |
| `--version` | バージョンだけを出力する | `uv run issue-digest --version` |
| `--hide-empty` | 0件の分類を出力しない | `uv run issue-digest --hide-empty issues.json` |
| `--only <ラベル>` | 指定したラベルの分類だけを出力する（複数回指定できる） | `uv run issue-digest --only agent:needs-decision issues.json` |
| `--exclude <ラベル>` | 指定したラベルの分類を出力しない（複数回指定できる。`--only` とは同時に使えない） | `uv run issue-digest --exclude unclassified issues.json` |
| `--stale <日数>` | 最終更新から指定日数以上たった Issue に `（N日更新なし）` を付ける | `uv run issue-digest --stale 7 issues.json` |
| `--since <日付>` | 最終更新が指定日（`YYYY-MM-DD`、UTC の0時）以降の Issue だけを出力する | `uv run issue-digest --since 2026-10-01 issues.json` |
| `--sort updated` | 各分類の中を最終更新の古い順に並べる | `uv run issue-digest --sort updated issues.json` |
| `--sort created` | 各分類の中を作成日時の古い順に並べる | `uv run issue-digest --sort created issues.json` |
| `--reverse` | 各分類の中の並びを逆にする（`--sort` がなければ番号の大きい順、あれば新しい順） | `uv run issue-digest --reverse issues.json` |
| `--limit <件数>` | 各分類で、先頭から指定件数だけ Issue を出力する | `uv run issue-digest --limit 5 issues.json` |
| `--max-chars <文字数>` | Markdown の出力全体を指定文字数以内に収める（収まらない分の Issue の行を `- ほか N 件` にする） | `uv run issue-digest --max-chars 2000 issues.json` |
| `--summary` | 総件数の次に、分類ごとの件数を1行で出力する | `uv run issue-digest --summary issues.json` |
| `--show-assignees` | 担当者がいる Issue に `（担当: @alice）` を付ける | `uv run issue-digest --show-assignees issues.json` |
| `--show-labels` | `agent:` で始まらないラベルがある Issue に `（ラベル: bug, docs）` を付ける | `uv run issue-digest --show-labels issues.json` |
| `--age` | 作成日時（`createdAt`）がある Issue に `（作成から12日）` を付ける | `uv run issue-digest --age issues.json` |
| `--show-milestone` | マイルストーンがある Issue に `（マイルストーン: v1.0）` を付ける | `uv run issue-digest --show-milestone issues.json` |
| `--json` | Markdown の代わりに JSON を出力する | `uv run issue-digest --json issues.json` |
| `--csv` | Markdown の代わりに CSV を出力する | `uv run issue-digest --csv issues.json` |
| `--title <文字列>` | 見出しの `Issue ダイジェスト` を指定した文字列に置き換える | `uv run issue-digest --title issue-digest issues.json` |
| `--output <パス>` | 標準出力ではなく、指定したファイルに書き出す | `uv run issue-digest --output digest.md issues.json` |
| `--diff <前回のJSONのパス>` | 前回の `--json` の出力と比べ、変化した Issue を末尾に出す | `uv run issue-digest --diff last.json issues.json` |
| `--fail-if-any <ラベル>` | 指定したラベルの分類に Issue が1件以上あるとき、終了コード 3 で終わる（複数回指定できる） | `uv run issue-digest --fail-if-any agent:blocked issues.json` |
| `--config <パス>` | 読む設定ファイルを指定する（省略時はカレントディレクトリの `.issue-digest.toml`） | `uv run issue-digest --config my.toml issues.json` |
| `--group-by assignee` | 分類ごとの代わりに、担当者ごとの見出しで並べる（Markdown だけ） | `uv run issue-digest --group-by assignee issues.json` |

### 入力

ファイルを指定する場合:

```
uv run issue-digest issues.json
```

パイプで渡す場合（引数に `-` を指定すると標準入力から読みます）:

```
gh issue list --json number,title,labels,url | uv run issue-digest -
```

### タイトルの長さ

Markdown では、Issue のタイトルが40文字を超えるとき、40文字までにして末尾に `…` を付けます（行が折り返されて読みにくくなるのを避けるため）。
Markdown の記号のエスケープは、省略した後のタイトルに対して行います。`--json` のタイトルは省略しません。

### `--hide-empty`

`--hide-empty` を付けると、0件の分類の見出しと「なし」を出力しません。対応が必要な分類だけを見たいときに使います。
付けない場合は、0件の分類も見出しと「なし」を出力します。

```
uv run issue-digest --hide-empty issues.json
```

### `--only <ラベル>`

`--only <ラベル>` を付けると、指定したラベルの分類だけを出力します。見たい分類だけを素早く確認したいときに使います。
複数回指定すると、指定したすべての分類を出力します。`--hide-empty` と同時に使えます。
指定できるのは `agent:needs-decision`、`agent:blocked`、`agent:review`、`agent:working`、`agent:ready`、`unclassified`（未分類）の6つです。
それ以外を指定すると、エラーを標準エラーに出して終了コード 2 で終わります。
見出しの総件数は、`--only` に関係なく全件の数のままです。

```
uv run issue-digest --only agent:needs-decision issues.json
uv run issue-digest --only agent:needs-decision --only agent:blocked --hide-empty issues.json
```

### `--exclude <ラベル>`

`--exclude <ラベル>` を付けると、指定したラベルの分類を出力しません。未分類など、あまり見ない分類を除きたいときに使います。
複数回指定すると、指定したすべての分類を除きます。指定できるラベルとエラーの出し方は `--only` と同じです。
`--hide-empty`、`--sort`、`--stale`、`--json` と同時に使えます。
`--only` と同時に指定すると、`エラー: --only と --exclude は同時に指定できません` を標準エラーに出して終了コード 2 で終わります。
見出しの総件数と `--summary` の行は、`--exclude` に関係なく全件・全分類のままです。

```
uv run issue-digest --exclude unclassified issues.json
uv run issue-digest --exclude unclassified --exclude agent:working --hide-empty issues.json
```

### `--stale <日数>`

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

### `--since <日付>`

`--since <日付>` を付けると、最終更新（`updatedAt`）が指定日以降の Issue だけを出力します。最近動いた Issue だけを見たいときに使います。

- 日付は `YYYY-MM-DD` の形で、UTC のその日の0時（`T00:00:00Z`）以降を対象にします。0時ちょうどに更新された Issue も出ます。時刻やタイムゾーンは指定できません。
- `updatedAt` がない Issue は出ません。
- 絞った後の Issue が、見出しの総件数、分類ごとの件数、`--summary` の対象になります。
- 日付の形が不正なとき、または `2026-02-30` のようなない日付のときは、エラーを標準エラーに出して終了コード 2 で終わります。
- Markdown、`--json`、`--csv` のどれでも効きます。設定ファイルには `since` キーはありません。

`--since` を付けない場合の出力は変わりません。

```
gh issue list --json number,title,labels,url,updatedAt | uv run issue-digest --since 2026-10-01 -
```

### `--show-assignees`

`--show-assignees` を付けると、担当者がいる Issue の行の末尾に `（担当: @alice, @bob）` を付けます。誰が対応しているかを知りたいときに使います。
担当者は入力の `assignees` の順に、カンマと空白で区切って並べます。担当者がいない Issue には何も付けません。
`assignees` がない入力でもエラーにはならず、担当者なしとして扱います。
`--show-assignees` を付けない場合の出力は変わりません。

```
gh issue list --json number,title,labels,url,assignees | uv run issue-digest --show-assignees -
```

### `--show-labels`

`--show-labels` を付けると、`agent:` で始まらないラベルがある Issue の行の末尾に `（ラベル: bug, docs）` を付けます。`bug` や `docs` などのラベルも一緒に見たいときに使います。
ラベルは入力の順に、カンマと空白で区切って並べます。対象のラベルがない Issue には何も付けません。
各ラベルの名前の Markdown の記号（`\` `` ` `` `*` `_` `[` `]` `<` `>`）は、タイトルと同じようにエスケープします（例: `x_y*z` は `x\_y\*z`）。`--json` の `labels` はエスケープしません。
`--show-labels` を付けない場合の出力は変わりません。

```
gh issue list --json number,title,labels,url | uv run issue-digest --show-labels -
```

### `--age`

`--age` を付けると、作成日時（`createdAt`）がある Issue の行の末尾に `（作成から12日）` を付けます。古くから残っている Issue に気づきたいときに使います。
日数は `--stale` と同じ基準時刻からの経過日数で、1日未満は切り捨てます（作成から1日たっていなければ `（作成から0日）`）。`createdAt` がない Issue には何も付けません。
`--age` を付けない場合の出力は変わりません。設定ファイルの `age = true` でも指定できます。

```
gh issue list --json number,title,labels,url,createdAt | uv run issue-digest --age -
```

### `--show-milestone`

`--show-milestone` を付けると、マイルストーンがある Issue の行の末尾に `（マイルストーン: v1.0）` を付けます。どのマイルストーンの Issue かを見たいときに使います。
入力は `gh issue list --json ...,milestone` の `milestone`（`{"title": "v1.0", ...}` の形）で、`title` を表示します。`milestone` がない、または `null` の Issue には何も付けません。
マイルストーンの名前の Markdown の記号（`\` `` ` `` `*` `_` `[` `]` `<` `>`）は、タイトルと同じようにエスケープします（例: `Sprint *2*` は `Sprint \*2\*`）。`--json` の `milestone` はエスケープしません。
`--show-milestone` を付けない場合の出力は変わりません。設定ファイルの `show_milestone = true` でも指定できます。

```
gh issue list --json number,title,labels,url,milestone | uv run issue-digest --show-milestone -
```

### `--summary`

`--summary` を付けると、総件数の見出しの次に、空行をはさんで分類ごとの件数を1行で出力します。全体の概要をひと目で知りたいときに使います。
分類の名前と順は見出しと同じです。この行は `--only` や `--hide-empty` に関係なく、常に6つの分類すべての件数を出します。
`--summary` を付けない場合の出力は変わりません。

```
判断待ち 1 / 中断 0 / レビュー待ち 2 / 作業中 0 / 着手可能 3 / 未分類 1
```

```
uv run issue-digest --summary issues.json
```

### `--sort updated`

`--sort updated` を付けると、各分類の中の Issue を `updatedAt`（最終更新）の古い順に並べます。止まっている Issue を見つけやすくするために使います。
`updatedAt` が同じ Issue は番号の小さい順、`updatedAt` がない Issue は分類の末尾に番号の小さい順で並べます。分類の順番は変わりません。
`--sort` に指定できる値は `updated` と `created` です。それ以外の値や値がない場合は、エラーを標準エラーに出して終了コード 2 で終わります。
`--sort` を付けない場合の並び順（Issue 番号の小さい順）は変わりません。

```
gh issue list --json number,title,labels,url,updatedAt | uv run issue-digest --sort updated --stale 7 -
```

### `--sort created`

`--sort created` を付けると、各分類の中の Issue を `createdAt`（作成日時）の古い順に並べます。古くからある Issue を優先して片付けたいときに使います。
並べ方の決まりは `--sort updated` と同じです。`createdAt` が同じ Issue は番号の小さい順、`createdAt` がない Issue は分類の末尾に番号の小さい順で並べます。分類の順番は変わりません。
入力の各 Issue の `createdAt`（ISO 8601 形式。例: `2026-10-20T12:34:56Z`）は省略できます。日時として読めない値のときは、エラーを標準エラーに出して終了コード 1 で終わります。
`--sort updated` と `--sort` なしの動作は変わりません。`--sort` は1つの値しか指定できないため、`updated` と `created` は同時に使えません。

```
gh issue list --json number,title,labels,url,createdAt | uv run issue-digest --sort created -
```

### `--reverse`

`--reverse` を付けると、各分類の中の Issue の並びを逆にします。新しい Issue から順に見たいときに使います。`--group-by assignee` のときは、各担当者の中の並びを逆にします。分類や担当者の順番は変わりません。

- `--sort` がなければ、番号の大きい順になります。
- `--sort updated` / `--sort created` と一緒なら、`--sort` で並べた結果をそのまま逆にするので、新しい順になります（同じ日時の Issue は番号の大きい順。`updatedAt`・`createdAt` がない Issue は、逆にするので分類の先頭に番号の大きい順で並びます）。
- `--limit` は逆にした後の先頭から数えます（`--reverse --limit 5` で、新しい5件）。
- `--max-chars` で削るのは、逆にした後の末尾の行です。
- `--json`、`--csv` でも同じように並びが変わります。
- `--diff` の `## 前回からの変化` の節の並び（番号の小さい順）は変わりません。
- 設定ファイルに `reverse` キーはありません。

`--reverse` を付けない場合の出力は変わりません。

```
uv run issue-digest --reverse --limit 5 issues.json
```

### `--limit <件数>`

`--limit <件数>` を付けると、各分類で先頭から指定件数だけ Issue を出力します。件数の多い分類があっても、ほかの分類が見づらくならないようにするために使います。
`--sort` を同時に指定した場合は、並べ替えた後の先頭から数えます。見出しの件数と総件数は全件のままです。

- Markdown: 出力しなかった Issue があれば、その分類の最後に `- ほか N 件` を出します。
- JSON: 各分類の `issues` を先頭の指定件数だけにします（`count` は全件のまま）。各分類に `omitted`（出力しなかった件数。0 も含む）を加えます。
- 件数は1以上の整数です。それ以外の値や値がない場合は、エラーを標準エラーに出して終了コード 2 で終わります。

`--limit` を付けない場合の出力は変わりません（`omitted` も出しません）。

```
uv run issue-digest --limit 5 --sort updated issues.json
```

### `--max-chars <文字数>`

`--max-chars <文字数>` を付けると、Markdown の出力全体（末尾の改行を含む）を指定した文字数以内に収めます。Discord（1つのメッセージは2000文字まで）など、長さに上限がある場所に送るときに使います。
文字数は Python の `len()` で数えます（絵文字や日本語も1文字は1と数えます）。

- 収まらないときは、最後の分類から順に、分類の末尾の Issue の行を1行ずつ削ります。最後の分類の Issue の行がなくなったら、1つ前の分類を削ります。
- 削った分類の最後に `- ほか N 件` を出します。`--limit` で省いた件数とまとめて1行にします。
- 削るのは分類の Issue の行だけです。見出し、件数、`--summary` の行、`--diff` の節（`## 前回からの変化`）は削りません。
- `--stale`、`--show-assignees`、`--show-labels`、`--age`、`--show-milestone` の印を付けたときは、印を含めた行で数えます。
- すべての Issue の行を削っても収まらないときは、そのまま出力し、標準エラーに `警告: Issue の行をすべて削っても --max-chars の N 文字に収まりません（M 文字）` を出します（終了コードは 0）。
- 文字数は1以上の整数です。それ以外の値や値がない場合は、エラーを標準エラーに出して終了コード 2 で終わります。
- Markdown だけで使えます。コマンドラインの `--json` または `--csv` と同時に指定すると、エラーを標準エラーに出して終了コード 2 で終わります。設定ファイルの `json = true` は、`--max-chars` を指定したら使いません（Markdown を出します）。設定ファイルの `max_chars` でも指定できます（設定の `json = true` と一緒に書くとエラーです）。
- `--group-by assignee` と同時に指定すると、分類の代わりに担当者の見出しを単位にして、最後の担当者（`## 担当者なし` があればそれ）から順に、各担当者の末尾の Issue の行を削ります。行末の分類の名前も含めた行で数えます。

`--max-chars` を付けない場合の出力は変わりません。

```
uv run issue-digest --max-chars 2000 --sort updated issues.json
```

### `--json`

`--json` を付けると、Markdown の代わりに JSON を標準出力に出します。通知のスクリプトなど、ほかのツールから使いたいときに使います。
UTF-8 で日本語はエスケープせず、インデントは2です。`--json` を付けない場合の出力は変わりません。

- `total`: Markdown の見出しと同じ総件数（重複を除いた全件数。`--only` に関係なく全件）
- `categories`: 分類の配列。順と `label`、`title` は Markdown の見出しと同じ（未分類の `label` は `unclassified`）

```
uv run issue-digest --json issues.json
```

出力例（`--only agent:needs-decision`）:

```json
{
  "total": 3,
  "categories": [
    {
      "label": "agent:needs-decision",
      "title": "判断待ち",
      "count": 1,
      "issues": [
        {
          "number": 12,
          "title": "仕様を決めたい",
          "url": "https://github.com/example/repo/issues/12"
        }
      ]
    }
  ]
}
```

`--stale 7` を同時に指定し、その Issue が13日更新されていない場合は、Issue に `"stale_days": 13` が加わります。

### `--csv`

`--csv` を付けると、Markdown の代わりに CSV を標準出力に出します。ダイジェストを表計算ソフトに読み込んで集計したいときに使います。
文字コードは UTF-8 で、クオートと改行（行末は `\r\n`）の扱いは Python の `csv` モジュールの既定に従います。カンマ、ダブルクオート、改行を含むタイトルも正しくクオートされます。
`--csv` を付けない場合の出力は変わりません。

- 1行目は見出し行 `label,number,title,url` です。
- 2行目からは、分類の順、各分類の中の Issue の順で1行ずつ出力します。複数の分類に入る Issue は、分類ごとに1行出力します。
- `label` は分類のラベル（未分類は `unclassified`）です。Markdown と違い、タイトルは省略しません。
- 出力する分類がなければ、見出し行だけを出力します。

```
uv run issue-digest --csv issues.json
```

出力例:

```
label,number,title,url
agent:ready,1,サンプルの Issue A,https://github.com/example/repo/issues/1
unclassified,2,ラベルなしの Issue B,https://github.com/example/repo/issues/2
```

### `--title <文字列>`

`--title <文字列>` を付けると、Markdown の1行目の `Issue ダイジェスト` を指定した文字列に置き換えます。複数のリポジトリのダイジェストを並べて読むときに、どのリポジトリのものか区別するために使います。

- Markdown: `--title issue-digest` なら、1行目は `# issue-digest（全 5 件）` になります。
- JSON: `--json` と同時に指定すると、JSON の先頭に `"title": "issue-digest"` を加えます。
- 空の文字列は、エラーを標準エラーに出して終了コード 2 で終わります。

`--title` を付けない場合の出力は変わりません（JSON に `title` も出しません）。

```
uv run issue-digest --title issue-digest issues.json
```

### `--output <パス>`

`--output <パス>` を付けると、ダイジェストを標準出力ではなく、指定したファイルに書き出します。シェルのリダイレクトを使わずに、定期的にファイルへ保存したいときに使います。
文字コードは UTF-8 で、ファイルが既にあれば上書きします。書き出したときは、標準出力には何も出しません。
フォルダは作らないので、フォルダがないなど書き出せない場合は、エラーを標準エラーに出して終了コード 1 で終わります。
`--output` の後にパスがない場合は、エラーを標準エラーに出して終了コード 2 で終わります。
`--output` を付けない場合の動作は変わりません。`--version` の出力先も変わりません（標準出力に出します）。

```
uv run issue-digest --output digest.md issues.json
```

### `--diff <前回のJSONのパス>`

`--diff <前回のJSONのパス>` を付けると、前回の `--json` の出力と今回の入力を比べ、Markdown の末尾に `## 前回からの変化` の節を加えます。前回のダイジェストから何が変わったかをひと目で知りたいときに使います。

- 新しい Issue: 前回になく、今回ある Issue
- なくなった Issue: 前回あり、今回ない Issue（タイトルと URL は前回の JSON のもの）
- 分類が変わった Issue: `- [#12](url) タイトル: 着手可能 → レビュー待ち` の形で出します。複数の分類に入る Issue は、分類の集合が変わったときだけ出し、`作業中, 着手可能 → レビュー待ち` のように分類を見出しの順にカンマで区切って並べます。タイトルだけが変わった Issue は出しません。

どれかに変化があるときは3つの小見出し（`### 新しい Issue - 1件` など）をすべて出し、0件の小見出しには「なし」を出します。各小見出しの中は Issue 番号の小さい順です。
どれも変化がなければ、節の中に「変化なし」だけを出します。

前回の JSON は、`--only`、`--exclude`、`--hide-empty`、`--limit`、`--since` を付けず、設定ファイル（`.issue-digest.toml` や `--config`）の `hide_empty`、`only`、`limit` も使わずに出力したものを前提とします。付けて出力した JSON を使うと、その JSON に入っていなかった Issue は「新しい Issue」として出ます。複数の分類に入る Issue で、前回は一部の分類にしか出ていなかったものは「分類が変わった Issue」として出ます。
今回の比較は、`--only`、`--exclude`、`--hide-empty`、`--limit` に関係なく、全分類の全件で行います。
`--title`、`--stale`、`--show-assignees`、`--show-labels`、`--age`、`--show-milestone`、`--summary`、`--sort`、`--reverse`、`--diff` を付けて出力した JSON も、前回の JSON として使えます（増えた項目は読みません。`--sort` と `--reverse` は並びだけが変わります）。

前回の JSON が見つからない、JSON として読めない、または `--json` の出力の形でない（`total` と `categories` がない、分類の `label` が見出しのラベルでない、Issue に `number`、`title`、`url` がないなど）ときは、エラーを標準エラーに出して終了コード 1 で終わります。
`--diff` の後にパスがない場合は、エラーを標準エラーに出して終了コード 2 で終わります。
`--diff` を付けない場合の出力は変わりません。前回の JSON の自動保存はしないので、次回のために `--json --output` で保存しておきます。

```
# 前回: JSON を保存しておく
gh issue list --json number,title,labels,url | uv run issue-digest --json --output last.json -

# 次回: 前回の JSON と比べる
gh issue list --json number,title,labels,url | uv run issue-digest --diff last.json -
```

出力例:

```
## 前回からの変化

### 新しい Issue - 1件

- [#5](https://github.com/example/repo/issues/5) 新しい Issue E

### なくなった Issue - 0件

なし

### 分類が変わった Issue - 1件

- [#12](https://github.com/example/repo/issues/12) 仕様を決めたい: 着手可能 → レビュー待ち
```

`--json` と同時に指定すると、JSON の末尾に `diff` を加えます。`added`、`removed`、`moved` の配列で、それぞれ Issue 番号の小さい順です。変化がなければ3つとも空の配列です。

- `added`、`removed` の各要素: `number`、`title`、`url`、`categories`（`added` は今回の、`removed` は前回の分類のラベルの配列）
- `moved` の各要素: `number`、`title`（今回のもの）、`url`、`from`（前回の分類のラベルの配列）、`to`（今回の分類のラベルの配列）

```json
"diff": {
  "added": [
    {"number": 5, "title": "新しい Issue E", "url": "https://github.com/example/repo/issues/5", "categories": ["agent:ready"]}
  ],
  "removed": [],
  "moved": [
    {"number": 12, "title": "仕様を決めたい", "url": "https://github.com/example/repo/issues/12", "from": ["agent:ready"], "to": ["agent:review"]}
  ]
}
```

`--diff` を付けた JSON も、次回の前回の JSON として使えます。

```
gh issue list --json number,title,labels,url | uv run issue-digest --json --diff last.json --output next.json -
```

### 設定ファイルと `--config <パス>`

毎回同じオプションを指定する手間を省くため、カレントディレクトリの `.issue-digest.toml` をオプションの既定値として読みます。ファイルがなければ、何も読まず今までどおり動きます。
`--config <パス>` で読むファイルを指定できます（このとき `.issue-digest.toml` は読みません）。指定したファイルがなければ、`エラー: 設定ファイルが見つかりません: <パス>` を標準エラーに出して終了コード 1 で終わります。
ホームディレクトリなど、ほかの場所の設定ファイルは探しません。

書けるキーは次の15個です。

| キー | 型 | 対応するオプション |
| --- | --- | --- |
| `hide_empty` | 真偽値 | `--hide-empty` |
| `summary` | 真偽値 | `--summary` |
| `only` | 文字列の配列（`--only` と同じ6つのラベル） | `--only` |
| `stale` | 0以上の整数 | `--stale` |
| `sort` | `"updated"` か `"created"` | `--sort updated` / `--sort created` |
| `show_assignees` | 真偽値 | `--show-assignees` |
| `show_labels` | 真偽値 | `--show-labels` |
| `show_milestone` | 真偽値 | `--show-milestone` |
| `age` | 真偽値 | `--age` |
| `title` | 1文字以上の文字列 | `--title` |
| `limit` | 1以上の整数 | `--limit` |
| `max_chars` | 1以上の整数 | `--max-chars` |
| `group_by` | `"assignee"` だけ | `--group-by assignee` |
| `json` | 真偽値 | `--json` |
| `headings` | テーブル（`[headings]`）。キーは `--only` と同じ6つのラベル、値は1文字以上の文字列 | なし（下の「分類の見出しを変える」を参照） |

`--output`、`--version` など、上に挙げていないオプションは設定できません。

- コマンドラインの指定が設定ファイルより優先されます。`--stale 3` は設定の `stale` を上書きします。
- 設定の `only` は、コマンドラインで `--only` を1つでも指定したら使いません（`--exclude` を指定したときも、`--only` と同時に使えないため使いません）。
- 設定の `title`、`limit`、`max_chars`、`group_by` も、コマンドラインで `--title`、`--limit`、`--max-chars`、`--group-by` を指定したら使いません。
- 設定の `group_by` と `max_chars` は、コマンドラインで `--json` または `--csv` を指定したら使いません（コマンドラインの出力形式が優先です）。
- 設定どうしが矛盾するとき（設定の `json = true` と `group_by` または `max_chars` を一緒に書いたときなど）は、コマンドラインで同じ指定をしたときと同じエラーを標準エラーに出して終了コード 2 で終わります。
- 設定の `json = true` は、コマンドラインで `--csv`、`--group-by`、`--max-chars` のどれかを指定したら使いません（コマンドラインが優先です）。
- 真偽値のキーは、`false` と書いても何も起きません（コマンドラインで打ち消すオプションはありません）。
- 知らないキー、型の違う値、TOML として読めない内容は、どのキーかを示すエラーを標準エラーに出して終了コード 2 で終わります。

例（`.issue-digest.toml`）:

```toml
hide_empty = true
stale = 7
limit = 5
title = "issue-digest"
show_labels = true
show_milestone = true
age = true
max_chars = 2000
group_by = "assignee"
only = ["agent:needs-decision", "agent:blocked", "agent:review"]
```

```
uv run issue-digest issues.json
uv run issue-digest --config my.toml --stale 3 issues.json
```

#### 分類の見出しを変える（`[headings]`）

設定ファイルに `[headings]` テーブルを書くと、分類の見出し（「判断待ち」など）をチームの呼び方に変えられます。キーは分類のラベル（`agent:needs-decision`、`agent:blocked`、`agent:review`、`agent:working`、`agent:ready`、`unclassified`）、値は見出しの文字列です。

```toml
[headings]
"agent:review" = "確認待ち"
unclassified = "その他"
```

- 書いた分類だけ、Markdown の見出し、`--summary` の行の名前、`--diff` の「分類が変わった Issue」の分類の名前、JSON の各分類の `title` を置き換えます。書かない分類の見出しは変わりません。
  - 例: `## 確認待ち (agent:review) - 2件`、`## その他 - 1件`
- `(agent:review)` のようなラベルの表示、JSON の `label`、CSV の `label` 列は変わりません。
- 知らないラベルや、1文字以上の文字列でない値は、どのキーかを示すエラーを標準エラーに出して終了コード 2 で終わります。
- コマンドラインに対応するオプションはありません。`--title` が置き換える1行目の `Issue ダイジェスト` には影響しません。

### `--group-by assignee`

`--group-by assignee` を付けると、分類ごとの見出しの代わりに、担当者ごとの見出しで Issue を並べます。誰が何を抱えているかを見たいときに使います。

- 見出しは `## @alice - 3件` の形です。担当者のログイン名の順（大文字と小文字は区別せずに比べます）に並べ、最後に `## 担当者なし - N件` を出します。
- 担当者が複数いる Issue は、それぞれの担当者の下に出します。
- 各担当者の中は Issue 番号の小さい順です。
- 各 Issue の行末に、その Issue が入る分類の名前を `（着手可能）` の形で付けます。複数の分類に入る Issue は `（作業中, 着手可能）` のように見出しの順にカンマで区切ります。設定ファイルの `[headings]` があれば、その名前を使います。
- 0件の担当者の見出しは出しません（担当者なしも同じです）。出す Issue が1件もなければ、見出しの代わりに「なし」を出します。
- `--group-by` に指定できる値は `assignee` だけです。それ以外の値は、エラーを標準エラーに出して終了コード 2 で終わります。`--group-by` の後に値がない場合も終了コード 2 で終わります。
- Markdown だけで使えます。`--json` または `--csv` と同時に指定すると、エラーを標準エラーに出して終了コード 2 で終わります。設定ファイルの `json = true` は、`--group-by` を指定したら使いません。設定ファイルの `group_by` と `json = true` を一緒に書くとエラーです。
- `--max-chars` と同時に指定すると、最後の担当者から順に、各担当者の末尾の Issue の行を削って指定文字数以内に収めます（削った担当者の最後に `- ほか N 件`）。
- 担当者は入力の `assignees` から読みます。`assignees` がない入力では、すべて担当者なしになります。

ほかのオプションとの組み合わせは「組み合わせ」の節を見てください。`--group-by` を付けない場合の出力は変わりません。設定ファイルの `group_by = "assignee"` でも指定できます（「設定ファイルと `--config <パス>`」を参照）。

```
gh issue list --json number,title,labels,url,assignees | uv run issue-digest --group-by assignee -
```

出力例:

```
# Issue ダイジェスト（全 3 件）

## @alice - 2件

- [#1](https://github.com/example/repo/issues/1) 共同の Issue（作業中, 着手可能）
- [#2](https://github.com/example/repo/issues/2) レビュー中（レビュー待ち）

## @bob - 1件

- [#1](https://github.com/example/repo/issues/1) 共同の Issue（作業中, 着手可能）

## 担当者なし - 1件

- [#3](https://github.com/example/repo/issues/3) 担当者なしで着手可能（着手可能）
```

### `--fail-if-any <ラベル>`

`--fail-if-any <ラベル>` を付けると、指定した分類に Issue が1件以上あるとき、終了コード 3 で終わります。cron でダイジェストを保存しながら、判断待ち（`agent:needs-decision`）や中断（`agent:blocked`）があるときだけ通知したい、といった使い方を想定しています。
複数回指定でき、どれか1つの分類に1件以上あれば終了コード 3 です。どの分類にもなければ、終了コード 0 で終わります。

- ダイジェストはいつもどおり出力します。`--output` があるときは、ファイルに書き出してから終了コード 3 で終わります。
- 判定に使う件数は、`--since` で絞った後の件数です。`--only`、`--exclude`、`--hide-empty`、`--limit`、`--max-chars` には左右されないので、出力に出ていない分類でも判定します。
- 指定できるラベルは `--only` と同じ6つ（`agent:ready`、`agent:working`、`agent:review`、`agent:needs-decision`、`agent:blocked`、`unclassified`）です。それ以外を指定すると、エラーを標準エラーに出して終了コード 2 で終わります。`--fail-if-any` の後に値がない場合も終了コード 2 です。
- エラー（終了コード 1、2）になるときは、今までと同じ終了コードで終わります（3 にはなりません）。ファイルに書き出せないときも終了コード 1 です。
- Markdown、`--json`、`--csv`、`--group-by` のどれでも効きます。設定ファイルにキーはありません。

```
uv run issue-digest --fail-if-any agent:needs-decision --fail-if-any agent:blocked --output digest.md issues.json
```

### `--version`

`--version` を付けると、`issue-digest 0.1.0` のようにバージョンを1行で出力し、終了コード 0 で終わります。
バージョンは `pyproject.toml` の値です。ほかのオプションやファイルが指定されていても、バージョンだけを出力します（ファイルは読みません）。
`--version` を付けない場合の動作は変わりません。

```
uv run issue-digest --version
```

### 組み合わせ

- `--hide-empty`、`--only`、`--stale`、`--since`、`--sort`、`--reverse`、`--limit`、`--title`、`--output`、`--diff` は、どれも同時に使えます（`--csv` との併用は下の項目を参照）。
- `--reverse` は `--sort` の後に並びを逆にし、そのあとで `--limit` と `--max-chars` が効きます（`--limit` は逆にした後の先頭から、`--max-chars` は逆にした後の末尾の行から）。
- `--since` で絞るのは出力する Issue です。件数（総件数、分類ごとの件数、`--summary`）は絞った後の Issue で数えます。`--json`、`--csv` でも同じです。
- `--diff` の比較は、`--only`、`--exclude`、`--hide-empty`、`--limit`、`--since` に関係なく全分類の全件で行います。`## 前回からの変化` の節の行には、`--stale`、`--show-assignees`、`--show-labels`、`--age`、`--show-milestone` の印を付けません。
- `--max-chars` は、Markdown を出すほかのオプションと同時に使えます。`--limit` と同時に指定すると、`--limit` で省いた後の出力をさらに削り、`- ほか N 件` の件数は両方で省いた件数の合計になります。`--output` と同時に指定すると、削った後の出力をファイルに書き出します（`--json`、`--csv`、`--group-by` との併用は下の項目を参照）。
- `--exclude` は `--only` 以外と同時に使えます。`--only` と同時に指定するとエラーです。
- `--json` と同時に指定した場合
  - `--hide-empty`、`--only`、`--exclude` は Markdown と同じように効き、出力する分類が変わります。
  - `--stale` を同時に指定すると、印が付く Issue にだけ `stale_days`（経過日数）を加えます。
  - `--sort updated` または `--sort created` を同時に指定すると、各分類の `issues` の順が変わります。`--reverse` を同時に指定すると、`issues` の順が逆になります。
  - `--summary` は無視します（JSON には分類ごとの `count` があるため）。
  - `--show-assignees` を同時に指定すると、各 Issue に `"assignees": ["alice", "bob"]`（login の配列。担当者がいなければ空の配列）を加えます。`--show-assignees` を付けない JSON には `assignees` を出しません。
  - `--show-labels` を同時に指定すると、各 Issue に `"labels": ["bug"]`（`agent:` で始まらないラベルの配列。なければ空の配列）を加えます。`--show-labels` を付けない JSON には `labels` を出しません。
  - `--age` を同時に指定すると、各 Issue に `"age_days": 12`（作成からの経過日数の整数。`createdAt` がなければ `null`）を加えます。`--age` を付けない JSON には `age_days` を出しません。
  - `--show-milestone` を同時に指定すると、各 Issue に `"milestone": "v1.0"`（マイルストーンの名前の文字列。なければ `null`）を加えます。`--show-milestone` を付けない JSON には `milestone` を出しません。
  - `--diff` を同時に指定すると、末尾に `diff`（`added`、`removed`、`moved`）を加えます。`--diff` を付けない JSON には `diff` を出しません。
- `--json` と `--output <パス>` を同時に指定すると、JSON をファイルに書き出します。
- `--csv` と同時に指定した場合
  - `--hide-empty`、`--only`、`--exclude`、`--since`、`--sort`、`--reverse`、`--limit`、`--output` は Markdown と同じように効きます（`--limit` は各分類の先頭から指定件数の行にします）。
  - `--stale`、`--age`、`--show-assignees`、`--show-labels`、`--show-milestone`、`--summary`、`--title`、`--diff` は、CSV に対応する列や行がないので無視します（エラーにしません。`--diff` の前回の JSON も読みません）。
  - `--json` と同時に指定すると、`エラー: --json と --csv は同時に指定できません` を標準エラーに出して終了コード 2 で終わります。
- コマンドラインの `--json` または `--csv` と `--max-chars` を同時に指定すると、`エラー: --max-chars は --json、--csv と同時に指定できません（Markdown だけで使えます）` を標準エラーに出して終了コード 2 で終わります。設定ファイルの `json = true` は `--max-chars` を指定したら使わないので、`--max-chars` と設定の `json = true` だけなら Markdown を出します（`--csv` を指定したときは、`--csv` との同時指定のエラーです）。
- `--stale`、`--show-assignees`、`--show-labels`、`--age`、`--show-milestone` の印が付くときは、`（N日更新なし）（担当: @alice）（ラベル: bug）（作成から12日）（マイルストーン: v1.0）` の順です。
- `--summary` の件数の行は、`--only` や `--hide-empty` に関係なく、常に6つの分類すべての件数を出します。
- `--group-by assignee` と同時に指定した場合
  - `--only`、`--exclude`、`--since` は、出す Issue を絞ります。`--only`、`--exclude` では、選んだ分類のどれかに入る Issue だけを出し、行末の分類の名前も選んだ分類だけにします。
  - 見出しの総件数は、分類ごとのときと同じです（`--since` で絞った後の全件。`--only`、`--exclude` に関係なし）。
  - `--sort`、`--reverse`、`--limit` は各担当者の中で効きます（`--limit` で出さなかった Issue があれば、その担当者の最後に `- ほか N 件`。見出しの件数は全件のまま）。
  - `--stale`、`--show-assignees`、`--show-labels`、`--age`、`--show-milestone` の印は、分類の名前の後ろに付きます（例: `（作業中, 着手可能）（13日更新なし）（担当: @alice）（ラベル: bug）（作成から12日）（マイルストーン: v1.0）`）。
  - `--summary` は、総件数の次に担当者ごとの件数を1行で出します（例: `@alice 2 / @bob 1 / 担当者なし 1`。順は見出しと同じ）。この行は `--only`、`--exclude` に関係なく、`--since` で絞った後の全件で数えます。出す Issue がなければ「なし」です。
  - `--hide-empty` は効果がありません（0件の担当者は出さないため）。
  - `--diff` の `## 前回からの変化` の節は、分類ごとのときと同じです。
  - `--title`、`--output`、`--config` は分類ごとのときと同じように効きます。
  - `--json`、`--csv` と同時に指定するとエラーです。
  - `--max-chars` は、最後の担当者の見出し（`## 担当者なし` があればそれ）から順に、各担当者の末尾の Issue の行を1行ずつ削ります。最後の担当者の Issue の行がなくなったら、1つ前の担当者を削ります。削った担当者の最後に `- ほか N 件` を出し、`--limit` で省いた件数とまとめて1行にします。見出し、件数、`--summary` の行、`--diff` の節は削りません。行末の分類の名前と印を含めた行で数えます。すべて削っても収まらないときの警告は、分類ごとのときと同じです。
- `--fail-if-any` は、ほかのオプションすべてと同時に使えます。終了コードの判定は `--since` で絞った後の件数で行い、`--only`、`--exclude`、`--hide-empty`、`--limit`、`--max-chars` には左右されません。`--json`、`--csv`、`--group-by`、`--output` のどれと同時でも、出力してから終了コード 3 で終わります。
- 終了コードは、正常が 0、実行時のエラー（ファイルが読めない、書き出せないなど）が 1、オプションの指定のエラーが 2、`--fail-if-any` で指定した分類に Issue があるときが 3 です。エラーのときは 1 か 2 を優先します。
- 設定ファイルの `group_by`、`max_chars` と `json = true` を一緒に書くと、コマンドラインで `--group-by`、`--max-chars` と `--json` を同時に指定したときと同じエラーで終了コード 2 です。コマンドラインで `--json` か `--csv` を指定したときは、設定の `group_by` と `max_chars` は使いません。
- `--config` は、ほかのオプションすべてと同時に使えます。設定ファイルの値は、コマンドラインで同じオプションを指定したときは使いません（詳しくは「設定ファイルと `--config <パス>`」）。
- `--version` は、ほかのオプションやファイルの指定があっても、バージョンだけを出力します。
