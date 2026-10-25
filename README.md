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
| `--sort updated` | 各分類の中を最終更新の古い順に並べる | `uv run issue-digest --sort updated issues.json` |
| `--sort created` | 各分類の中を作成日時の古い順に並べる | `uv run issue-digest --sort created issues.json` |
| `--limit <件数>` | 各分類で、先頭から指定件数だけ Issue を出力する | `uv run issue-digest --limit 5 issues.json` |
| `--summary` | 総件数の次に、分類ごとの件数を1行で出力する | `uv run issue-digest --summary issues.json` |
| `--show-assignees` | 担当者がいる Issue に `（担当: @alice）` を付ける | `uv run issue-digest --show-assignees issues.json` |
| `--show-labels` | `agent:` で始まらないラベルがある Issue に `（ラベル: bug, docs）` を付ける | `uv run issue-digest --show-labels issues.json` |
| `--json` | Markdown の代わりに JSON を出力する | `uv run issue-digest --json issues.json` |
| `--csv` | Markdown の代わりに CSV を出力する | `uv run issue-digest --csv issues.json` |
| `--title <文字列>` | 見出しの `Issue ダイジェスト` を指定した文字列に置き換える | `uv run issue-digest --title issue-digest issues.json` |
| `--output <パス>` | 標準出力ではなく、指定したファイルに書き出す | `uv run issue-digest --output digest.md issues.json` |

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
`--show-labels` を付けない場合の出力は変わりません。

```
gh issue list --json number,title,labels,url | uv run issue-digest --show-labels -
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

### `--version`

`--version` を付けると、`issue-digest 0.1.0` のようにバージョンを1行で出力し、終了コード 0 で終わります。
バージョンは `pyproject.toml` の値です。ほかのオプションやファイルが指定されていても、バージョンだけを出力します（ファイルは読みません）。
`--version` を付けない場合の動作は変わりません。

```
uv run issue-digest --version
```

### 組み合わせ

- `--hide-empty`、`--only`、`--stale`、`--sort`、`--limit`、`--title`、`--output` は、どれも同時に使えます（`--csv` との併用は下の項目を参照）。
- `--exclude` は `--only` 以外と同時に使えます。`--only` と同時に指定するとエラーです。
- `--json` と同時に指定した場合
  - `--hide-empty`、`--only`、`--exclude` は Markdown と同じように効き、出力する分類が変わります。
  - `--stale` を同時に指定すると、印が付く Issue にだけ `stale_days`（経過日数）を加えます。
  - `--sort updated` または `--sort created` を同時に指定すると、各分類の `issues` の順が変わります。
  - `--summary` は無視します（JSON には分類ごとの `count` があるため）。
  - `--show-assignees` を同時に指定すると、各 Issue に `"assignees": ["alice", "bob"]`（login の配列。担当者がいなければ空の配列）を加えます。`--show-assignees` を付けない JSON には `assignees` を出しません。
  - `--show-labels` を同時に指定すると、各 Issue に `"labels": ["bug"]`（`agent:` で始まらないラベルの配列。なければ空の配列）を加えます。`--show-labels` を付けない JSON には `labels` を出しません。
- `--json` と `--output <パス>` を同時に指定すると、JSON をファイルに書き出します。
- `--csv` と同時に指定した場合
  - `--hide-empty`、`--only`、`--exclude`、`--sort`、`--limit`、`--output` は Markdown と同じように効きます（`--limit` は各分類の先頭から指定件数の行にします）。
  - `--stale`、`--show-assignees`、`--show-labels`、`--summary`、`--title` は、CSV に対応する列や行がないので無視します（エラーにしません）。
  - `--json` と同時に指定すると、`エラー: --json と --csv は同時に指定できません` を標準エラーに出して終了コード 2 で終わります。
- `--stale`、`--show-assignees`、`--show-labels` の印が付くときは、`（N日更新なし）（担当: @alice）（ラベル: bug）` の順です。
- `--summary` の件数の行は、`--only` や `--hide-empty` に関係なく、常に6つの分類すべての件数を出します。
- `--version` は、ほかのオプションやファイルの指定があっても、バージョンだけを出力します。
