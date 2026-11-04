# オプションの詳しい説明

[README に戻る](../README.md)

## タイトルの長さ

Markdown では、Issue のタイトルが40文字を超えるとき、40文字までにして末尾に `…` を付けます（行が折り返されて読みにくくなるのを避けるため）。
Markdown の記号のエスケープは、省略した後のタイトルに対して行います。`--json` のタイトルは省略しません。

## `--hide-empty`

`--hide-empty` を付けると、0件の分類の見出しと「なし」を出力しません。対応が必要な分類だけを見たいときに使います。
付けない場合は、0件の分類も見出しと「なし」を出力します。

```
uv run issue-digest --hide-empty issues.json
```

## `--only <ラベル>`

`--only <ラベル>` を付けると、指定したラベルの分類だけを出力します。見たい分類だけを素早く確認したいときに使います。
複数回指定すると、指定したすべての分類を出力します。`--hide-empty` と同時に使えます。
指定できるのは `agent:needs-decision`、`agent:blocked`、`agent:review`、`agent:working`、`agent:ready`、`unclassified`（未分類）の6つです。
これは分類の名前で、設定ファイルの `[category_labels]` で分類に使う GitHub ラベルを変えても、指定する名前は変わりません（例: `"agent:ready" = ["status:todo"]` と書いたときも `--only agent:ready` で、`status:todo` で分類した Issue を出します）。
それ以外を指定すると、エラーを標準エラーに出して終了コード 2 で終わります。
見出しの総件数は、`--only` に関係なく全件の数のままです。

```
uv run issue-digest --only agent:needs-decision issues.json
uv run issue-digest --only agent:needs-decision --only agent:blocked --hide-empty issues.json
```

## `--exclude <ラベル>`

`--exclude <ラベル>` を付けると、指定したラベルの分類を出力しません。未分類など、あまり見ない分類を除きたいときに使います。
複数回指定すると、指定したすべての分類を除きます。指定できるラベルとエラーの出し方は `--only` と同じです。
`--hide-empty`、`--sort`、`--stale`、`--json` と同時に使えます。
`--only` と同時に指定すると、`エラー: --only と --exclude は同時に指定できません` を標準エラーに出して終了コード 2 で終わります。
見出しの総件数と `--summary` の行は、`--exclude` に関係なく全件・全分類のままです。
設定ファイルの `exclude` キーにも同じラベルを書けます（`--only`、`--exclude` との優先順位は「[設定ファイルと `--config <パス>`](config.md#設定ファイルと---config-パス)」を参照）。

```
uv run issue-digest --exclude unclassified issues.json
uv run issue-digest --exclude unclassified --exclude agent:working --hide-empty issues.json
```

## `--stale <日数>`

`--stale <日数>` を付けると、最終更新から指定日数以上たった Issue の行の末尾に `（N日更新なし）` を付けます。止まっている Issue に気づきたいときに使います。
N は経過日数を切り捨てた整数です。`--hide-empty`、`--only` と同時に使えます。
この印を付けるには、入力の各 Issue に `updatedAt`（ISO 8601 形式。例: `2026-10-20T12:34:56Z`）が必要です。
`gh issue list -L 1000 --json number,title,labels,url,updatedAt` の出力をそのまま渡せます。
`updatedAt` がない Issue には印を付けません。
日数は0以上の整数で指定します。それ以外を指定すると、エラーを標準エラーに出して終了コード 2 で終わります。
`--stale` を付けない場合の出力は変わりません。

```
gh issue list -L 1000 --json number,title,labels,url,updatedAt | uv run issue-digest --stale 7 -
```

## `--since <日付>`

`--since <日付>` を付けると、最終更新（`updatedAt`）が指定日以降の Issue だけを出力します。最近動いた Issue だけを見たいときに使います。

- 日付は `YYYY-MM-DD` の形で、UTC のその日の0時（`T00:00:00Z`）以降を対象にします。0時ちょうどに更新された Issue も出ます。時刻やタイムゾーンは指定できません。
- `7d` のように `<整数>d` の形で日数も指定できます。基準時刻の N 日前以降に更新された Issue を出し、ちょうど N 日前に更新された Issue も出ます。cron などで日付を書き換えずに使えます。
  - `N` は0以上の整数（半角数字のみ）で、`0d` も使えます。`d` は小文字だけです。`7D`、`7days`、`-1d`、`1.5d`、`d`、`1w` はエラーです。`h`（時間）や `w`（週）の単位はありません。
  - 基準時刻は `--stale`、`--age` と同じです。実行の最初に現在時刻を1回だけ決め、`--since`、`--stale`、`--age` のすべてがそれを使います。
  - `--since` は1つの値しか使えません。`--since 2026-10-01 --since 7d` のように複数回指定しても、エラーにはならず、最後の指定（この例では `7d`）だけを使います。
- `updatedAt` がない Issue は出ません。
- 絞った後の Issue が、見出しの総件数、分類ごとの件数、`--summary` の対象になります。
- 日付としても `<整数>d` としても読めない値（`2026-02-30` のようなない日付を含む）のときは、`エラー: --since には YYYY-MM-DD の形の日付か、7d のような日数を指定してください: <値>` を標準エラーに出して終了コード 2 で終わります。
- Markdown、`--json`、`--csv` のどれでも効きます。設定ファイルには `since = "7d"` の形で書けます（日数の形だけ。日付の形は書けません。意味と基準時刻はコマンドラインの `--since 7d` と同じです）。コマンドラインで `--since` を指定したら、設定の `since` は使いません。詳しくは「[設定ファイルと `--config <パス>`](config.md#設定ファイルと---config-パス)」を参照してください。

`--since` を付けない場合の出力は変わりません。

```
gh issue list -L 1000 --json number,title,labels,url,updatedAt | uv run issue-digest --since 2026-10-01 -
gh issue list -L 1000 --json number,title,labels,url,updatedAt | uv run issue-digest --since 7d -
```

## `--until <日付>`

`--until <日付>` を付けると、最終更新（`updatedAt`）が指定日の終わりまでの Issue だけを出力します。`--since` と一緒に使うと、「先月に動いた Issue」のように期間を区切って見られます。

- 日付は `YYYY-MM-DD` の形で、UTC のその日の終わりまで（翌日の `T00:00:00Z` より前）を対象にします。指定した日に更新された Issue も出ます。時刻やタイムゾーンは指定できません。`7d` のような日数の形は使えません。
- `--until` だけでも使えます。このときは指定日の終わりまでに更新された Issue をすべて出します。
- `--since` と一緒に指定すると、両方の条件に合う Issue だけを出します。`--since 2026-10-01 --until 2026-10-31` なら、10月1日0時から10月31日の終わりまで（10月31日に更新された Issue も含む）に更新された Issue です。同じ日を指定すると、その日1日分です。
- `--since` の日付が `--until` の日付より後のときは、`エラー: --since は --until より前の日付にしてください` を標準エラーに出して終了コード 2 で終わります。`--since` が `7d` の形のときは、基準時刻の N 日前を UTC の日付に直して比べます（例: 基準時刻が 2026-11-02 12時なら、`--since 1d` は11月1日なので `--until 2026-10-31` とはエラー、`--since 2d` は10月31日なのでエラーにならない）。コマンドラインで `--since` を指定しないときは、設定ファイルの `since` から求めた日付も同じように比べ、`--until` の日付より後なら `エラー: 設定ファイルの since（<値>）は --until より前の日付にしてください` を標準エラーに出して終了コード 2 で終わります（例: 基準時刻が 2026-11-02 12時で設定が `since = "1d"` なら、`--until 2026-10-31` はエラー、`--until 2026-11-01` 以降はエラーにならず両方の条件で絞る）。コマンドラインで `--since` を指定したときは、設定の `since` を使わないので、設定の `since` とは比べません。
- `updatedAt` がない Issue は出ません（`--since` と同じ）。
- 日付として読めない値（`2026-02-30` のようなない日付を含む）のときは、`エラー: --until には YYYY-MM-DD の形の日付を指定してください: <値>` を標準エラーに出して終了コード 2 で終わります。日付の順の検査より先に行います。
- `--until` は1つの値しか使えません。複数回指定しても、エラーにはならず、最後の指定だけを使います（`--since` と同じ）。
- 絞った後の Issue が、見出しの総件数、分類ごとの件数、`--summary`、`--fail-if-any` の判定の対象になります。`--diff` の比較は、絞り込みに関係なく全件で行います。
- Markdown、`--json`、`--csv`、`--group-by assignee` のどれでも効きます。
- 設定ファイルには書けません（日付が固定されて古くなるため。設定の `since` が日付の形を受け付けないのと同じ理由です）。`until` を書くと、`エラー: 設定ファイルに知らないキーがあります: until` を標準エラーに出して終了コード 2 で終わります。

`--until` を付けない場合の出力は変わりません。

```
gh issue list -L 1000 --json number,title,labels,url,updatedAt | uv run issue-digest --since 2026-10-01 --until 2026-10-31 -
gh issue list -L 1000 --json number,title,labels,url,updatedAt | uv run issue-digest --until 2026-10-31 -
```

## `--show-assignees`

`--show-assignees` を付けると、担当者がいる Issue の行の末尾に `（担当: @alice, @bob）` を付けます。誰が対応しているかを知りたいときに使います。
担当者は入力の `assignees` の順に、カンマと空白で区切って並べます。担当者がいない Issue には何も付けません。
`assignees` がない入力でもエラーにはならず、担当者なしとして扱います。
`--show-assignees` を付けない場合の出力は変わりません。

```
gh issue list -L 1000 --json number,title,labels,url,assignees | uv run issue-digest --show-assignees -
```

## `--show-author`

`--show-author` を付けると、作成者がある Issue の行の末尾に `（作成者: @alice）` を付けます。外部から来た Issue や、特定の人が作った Issue を見分けたいときに使います。
作成者は入力の `author`（`{"login": "alice", ...}` の形）の `login` を、そのまま表示します（`app/dependabot` のようなボットの名前も変えません）。`author` がない、または `null` の Issue には何も付けません（エラーにしません）。
`--show-author` を付けない場合の出力は変わりません。作成者での絞り込みや、作成者ごとの見出しはありません。

```
gh issue list -L 1000 --json number,title,labels,url,author | uv run issue-digest --show-author -
```

## `--show-labels`

`--show-labels` を付けると、`agent:` で始まらないラベルがある Issue の行の末尾に `（ラベル: bug, docs）` を付けます。`bug` や `docs` などのラベルも一緒に見たいときに使います。
設定ファイルの `[category_labels]` に書いたラベル（分類に使っているラベル）は、`agent:` で始まらなくても出しません。`agent:` で始まるラベルは、分類に使っていなくても出しません。`--json` の `labels` も同じです。
ラベルは入力の順に、カンマと空白で区切って並べます。対象のラベルがない Issue には何も付けません。
各ラベルの名前の Markdown の記号（`\` `` ` `` `*` `_` `[` `]` `<` `>`）は、タイトルと同じようにエスケープします（例: `x_y*z` は `x\_y\*z`）。`--json` の `labels` はエスケープしません。
`--show-labels` を付けない場合の出力は変わりません。

```
gh issue list -L 1000 --json number,title,labels,url | uv run issue-digest --show-labels -
```

## `--age`

`--age` を付けると、作成日時（`createdAt`）がある Issue の行の末尾に `（作成から12日）` を付けます。古くから残っている Issue に気づきたいときに使います。
日数は `--stale` と同じ基準時刻からの経過日数で、1日未満は切り捨てます（作成から1日たっていなければ `（作成から0日）`）。`createdAt` がない Issue には何も付けません。
`--age` を付けない場合の出力は変わりません。設定ファイルの `age = true` でも指定できます。

```
gh issue list -L 1000 --json number,title,labels,url,createdAt | uv run issue-digest --age -
```

## `--show-milestone`

`--show-milestone` を付けると、マイルストーンがある Issue の行の末尾に `（マイルストーン: v1.0）` を付けます。どのマイルストーンの Issue かを見たいときに使います。
入力は `gh issue list -L 1000 --json ...,milestone` の `milestone`（`{"title": "v1.0", ...}` の形）で、`title` を表示します。`milestone` がない、または `null` の Issue には何も付けません。
マイルストーンの名前の Markdown の記号（`\` `` ` `` `*` `_` `[` `]` `<` `>`）は、タイトルと同じようにエスケープします（例: `Sprint *2*` は `Sprint \*2\*`）。`--json` の `milestone` はエスケープしません。
`--show-milestone` を付けない場合の出力は変わりません。設定ファイルの `show_milestone = true` でも指定できます。

```
gh issue list -L 1000 --json number,title,labels,url,milestone | uv run issue-digest --show-milestone -
```

## `--summary`

`--summary` を付けると、総件数の見出しの次に、空行をはさんで分類ごとの件数を1行で出力します。全体の概要をひと目で知りたいときに使います。
分類の名前と順は見出しと同じです。この行は `--only` や `--hide-empty` に関係なく、常に6つの分類すべての件数を出します。
`--summary` を付けない場合の出力は変わりません。

```
判断待ち 1 / 中断 0 / レビュー待ち 2 / 作業中 0 / 着手可能 3 / 未分類 1
```

```
uv run issue-digest --summary issues.json
```

## `--sort updated`

`--sort updated` を付けると、各分類の中の Issue を `updatedAt`（最終更新）の古い順に並べます。止まっている Issue を見つけやすくするために使います。
`updatedAt` が同じ Issue は既定の並び（リポジトリ名の順、同じリポジトリの中は番号の小さい順。「[リポジトリ名の表示](input.md#リポジトリ名の表示)」を参照）、`updatedAt` がない Issue は分類の末尾に既定の並びで並べます。分類の順番は変わりません。
`--sort` に指定できる値は `updated`、`created`、`number` の3つです。それ以外の値や値がない場合は、エラーを標準エラーに出して終了コード 2 で終わります。
`--sort` を付けない場合の並び順（既定の並び）は変わりません。

```
gh issue list -L 1000 --json number,title,labels,url,updatedAt | uv run issue-digest --sort updated --stale 7 -
```

## `--sort created`

`--sort created` を付けると、各分類の中の Issue を `createdAt`（作成日時）の古い順に並べます。古くからある Issue を優先して片付けたいときに使います。
並べ方の決まりは `--sort updated` と同じです。`createdAt` が同じ Issue は既定の並び（リポジトリ名の順、同じリポジトリの中は番号の小さい順）、`createdAt` がない Issue は分類の末尾に既定の並びで並べます。分類の順番は変わりません。
入力の各 Issue の `createdAt`（ISO 8601 形式。例: `2026-10-20T12:34:56Z`）は省略できます。日時として読めない値のときは、その入力のパス（標準入力は `-（標準入力）`）を付けたエラー（例: `エラー: bad.json: Issue #4 の createdAt を日時として読めません: xx`）を標準エラーに出して終了コード 1 で終わります。
`--sort updated` と `--sort` なしの動作は変わりません。`--sort` は1つの値しか使えません。`--sort updated --sort created` のように複数回指定しても、エラーにはならず、最後の指定（この例では `created`）だけを使います。

```
gh issue list -L 1000 --json number,title,labels,url,createdAt | uv run issue-digest --sort created -
```

## `--sort number`

`--sort number` を付けると、各分類の中の Issue を番号の小さい順に並べます。複数のリポジトリの Issue をまとめたとき（既定はリポジトリ名の順）に、番号の順で見たいときに使います。
番号が同じ Issue（別のリポジトリの同じ番号）は既定の並び（リポジトリ名の順）で並べます。分類の順番は変わりません。日時は使わないので、入力に `updatedAt` や `createdAt` がなくても同じように並びます。
`--reverse` と一緒なら番号の大きい順になります（番号が同じ Issue は既定の並びの逆）。`--limit`、`--max-chars`、`--json`、`--csv`、`--group-by assignee` との関係は、`--sort updated` / `--sort created` と同じです。
`--sort` は1つの値しか使えず、複数回指定したときは最後の指定だけを使います。設定ファイルの `sort = "number"` でも指定でき、`--sort` を指定したら設定の値は使いません。

```
uv run issue-digest --sort number alpha.json beta.json
```

## `--reverse`

`--reverse` を付けると、各分類の中の Issue の並びを逆にします。新しい Issue から順に見たいときに使います。`--group-by assignee` のときは、各担当者の中の並びを逆にします。分類や担当者の順番は変わりません。

- `--sort` がなければ、既定の並び（リポジトリ名の順、同じリポジトリの中は番号の小さい順）を逆にします。入力が1つのリポジトリだけなら、番号の大きい順になります。
- `--sort updated` / `--sort created` と一緒なら、`--sort` で並べた結果をそのまま逆にするので、新しい順になります（同じ日時の Issue は既定の並びの逆。`updatedAt`・`createdAt` がない Issue は、逆にするので分類の先頭に既定の並びの逆で並びます）。
- `--sort number` と一緒なら、番号の大きい順になります（番号が同じ Issue は既定の並びの逆）。
- `--limit` は逆にした後の先頭から数えます（`--reverse --limit 5` で、新しい5件）。
- `--max-chars` で削るのは、逆にした後の末尾の行です。
- `--json`、`--csv` でも同じように並びが変わります。
- `--diff` の `## 前回からの変化` の節の並び（リポジトリ名の順、同じリポジトリの中は番号の小さい順）は変わりません。
- 設定ファイルに `reverse = true` と書くと、`--reverse` を付けたときと同じになります。コマンドラインで打ち消す方法はありません（ほかの真偽値のキーと同じ）。

`--reverse` を付けない場合の出力は変わりません。

```
uv run issue-digest --reverse --limit 5 issues.json
```

## `--limit <件数>`

`--limit <件数>` を付けると、各分類で先頭から指定件数だけ Issue を出力します。件数の多い分類があっても、ほかの分類が見づらくならないようにするために使います。
`--sort` を同時に指定した場合は、並べ替えた後の先頭から数えます。見出しの件数と総件数は全件のままです。

- Markdown: 出力しなかった Issue があれば、その分類の最後に `- ほか N 件` を出します。
- JSON: 各分類の `issues` を先頭の指定件数だけにします（`count` は全件のまま）。各分類に `omitted`（出力しなかった件数。0 も含む）を加えます。
- 件数は1以上の整数です。それ以外の値や値がない場合は、エラーを標準エラーに出して終了コード 2 で終わります。

`--limit` を付けない場合の出力は変わりません（`omitted` も出しません）。

```
uv run issue-digest --limit 5 --sort updated issues.json
```

## `--max-chars <文字数>`

`--max-chars <文字数>` を付けると、Markdown の出力全体（末尾の改行を含む）を指定した文字数以内に収めます。Discord（1つのメッセージは2000文字まで）など、長さに上限がある場所に送るときに使います。
文字数は Python の `len()` で数えます（絵文字や日本語も1文字は1と数えます）。

- 収まらないときは、最後の分類から順に、分類の末尾の Issue の行を1行ずつ削ります。最後の分類の Issue の行がなくなったら、1つ前の分類を削ります。
- 削った分類の最後に `- ほか N 件` を出します。`--limit` で省いた件数とまとめて1行にします。
- 削るのは分類の Issue の行だけです。見出し、件数、`--summary` の行、`--diff` の節（`## 前回からの変化`）は削りません。
- `--stale`、`--show-assignees`、`--show-author`、`--show-labels`、`--age`、`--show-milestone` の印を付けたときは、印を含めた行で数えます。リポジトリ名（`[owner/repo#12]`）も含めた行で数えます。
- すべての Issue の行を削っても収まらないときは、そのまま出力し、標準エラーに `警告: Issue の行をすべて削っても --max-chars の N 文字に収まりません（M 文字）` を出します（終了コードは 0）。
- 文字数は1以上の整数です。それ以外の値や値がない場合は、エラーを標準エラーに出して終了コード 2 で終わります。
- Markdown だけで使えます。コマンドラインの `--json` または `--csv` と同時に指定すると、エラーを標準エラーに出して終了コード 2 で終わります。設定ファイルの `json = true` は、`--max-chars` を指定したら使いません（Markdown を出します）。設定ファイルの `max_chars` でも指定できます（設定の `json = true` と一緒に書くとエラーです）。
- `--group-by assignee` と同時に指定すると、分類の代わりに担当者の見出しを単位にして、最後の担当者（`## 担当者なし` があればそれ）から順に、各担当者の末尾の Issue の行を削ります。行末の分類の名前も含めた行で数えます。

`--max-chars` を付けない場合の出力は変わりません。

```
uv run issue-digest --max-chars 2000 --sort updated issues.json
```

## `--json`

`--json` を付けると、Markdown の代わりに JSON を標準出力に出します。通知のスクリプトなど、ほかのツールから使いたいときに使います。
UTF-8 で日本語はエスケープせず、インデントは2です。`--json` を付けない場合の出力は変わりません。

- `total`: Markdown の見出しと同じ総件数（重複を除いた全件数。`--only` に関係なく全件）
- `categories`: 分類の配列。順と `label`、`title` は Markdown の見出しと同じ（未分類の `label` は `unclassified`）
- 各 Issue の `number`、`title`、`url`、`repository`（URL から読み取ったリポジトリ名。読み取れなければ `null`）

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
          "url": "https://github.com/example/repo/issues/12",
          "repository": "example/repo"
        }
      ]
    }
  ]
}
```

`--stale 7` を同時に指定し、その Issue が13日更新されていない場合は、Issue に `"stale_days": 13` が加わります。

## `--csv`

`--csv` を付けると、Markdown の代わりに CSV を標準出力に出します。ダイジェストを表計算ソフトに読み込んで集計したいときに使います。
文字コードは UTF-8 で、クオートと改行（行末は `\r\n`）の扱いは Python の `csv` モジュールの既定に従います。カンマ、ダブルクオート、改行を含むタイトルも正しくクオートされます。
`--csv` を付けない場合の出力は変わりません。

- 1行目は見出し行 `label,number,title,url,repository` です。
- `repository` は URL から読み取ったリポジトリ名です。読み取れなければ空にします。
- 2行目からは、分類の順、各分類の中の Issue の順で1行ずつ出力します。複数の分類に入る Issue は、分類ごとに1行出力します。
- `label` は分類のラベル（未分類は `unclassified`）です。Markdown と違い、タイトルは省略しません。
- 出力する分類がなければ、見出し行だけを出力します。

```
uv run issue-digest --csv issues.json
```

出力例:

```
label,number,title,url,repository
agent:ready,1,サンプルの Issue A,https://github.com/example/repo/issues/1,example/repo
unclassified,2,ラベルなしの Issue B,https://github.com/example/repo/issues/2,example/repo
```

## `--title <文字列>`

`--title <文字列>` を付けると、Markdown の1行目の `Issue ダイジェスト` を指定した文字列に置き換えます。複数のリポジトリのダイジェストを並べて読むときに、どのリポジトリのものか区別するために使います。

- Markdown: `--title issue-digest` なら、1行目は `# issue-digest（全 5 件）` になります。
- JSON: `--json` と同時に指定すると、JSON の先頭に `"title": "issue-digest"` を加えます。
- 空の文字列は、エラーを標準エラーに出して終了コード 2 で終わります。

`--title` を付けない場合の出力は変わりません（JSON に `title` も出しません）。

```
uv run issue-digest --title issue-digest issues.json
```

## `--output <パス>`

`--output <パス>` を付けると、ダイジェストを標準出力ではなく、指定したファイルに書き出します。シェルのリダイレクトを使わずに、定期的にファイルへ保存したいときに使います。
文字コードは UTF-8 で、ファイルが既にあれば上書きします。書き出したときは、標準出力には何も出しません。
フォルダは作らないので、フォルダがないなど書き出せない場合は、エラーを標準エラーに出して終了コード 1 で終わります。
`--output` の後にパスがない場合は、エラーを標準エラーに出して終了コード 2 で終わります。
`--output` を付けない場合の動作は変わりません。`--version` の出力先も変わりません（標準出力に出します）。

```
uv run issue-digest --output digest.md issues.json
```

## `--diff <前回のJSONのパス>`

`--diff <前回のJSONのパス>` を付けると、前回の `--json` の出力と今回の入力を比べ、Markdown の末尾に `## 前回からの変化` の節を加えます。前回のダイジェストから何が変わったかをひと目で知りたいときに使います。

- 新しい Issue: 前回になく、今回ある Issue
- なくなった Issue: 前回あり、今回ない Issue（タイトルと URL は前回の JSON のもの）
- 分類が変わった Issue: `- [owner/repo#12](url) タイトル: 着手可能 → レビュー待ち` の形で出します。複数の分類に入る Issue は、分類の集合が変わったときだけ出し、`作業中, 着手可能 → レビュー待ち` のように分類を見出しの順にカンマで区切って並べます。タイトルだけが変わった Issue は出しません。

前回と今回の Issue は URL で照合します（大文字と小文字は区別しません）。別のリポジトリの同じ番号の Issue を取り違えることはありません。前回の JSON の `repository` は読まず、URL から読み取るので、リポジトリ名を出す前の版の `--json` の出力も前回の JSON として使えます。

どれかに変化があるときは3つの小見出し（`### 新しい Issue - 1件` など）をすべて出し、0件の小見出しには「なし」を出します。各小見出しの中は、リポジトリ名の順、同じリポジトリの中は Issue 番号の小さい順です（リポジトリ名がない Issue は最後に番号の小さい順）。
どれも変化がなければ、節の中に「変化なし」だけを出します。

前回の JSON は、`--only`、`--exclude`、`--hide-empty`、`--limit`、`--since`、`--until` を付けず、設定ファイル（`.issue-digest.toml` や `--config`）の `hide_empty`、`only`、`exclude`、`limit`、`since` も使わずに出力したものを前提とします。付けて出力した JSON を使うと、その JSON に入っていなかった Issue は「新しい Issue」として出ます。複数の分類に入る Issue で、前回は一部の分類にしか出ていなかったものは「分類が変わった Issue」として出ます。
今回の比較は、`--only`、`--exclude`、`--hide-empty`、`--limit`、`--since`、`--until`（設定ファイルの `only`、`exclude`、`hide_empty`、`limit`、`since` も）に関係なく、全分類の全件で行います。
`--title`、`--stale`、`--show-assignees`、`--show-author`、`--show-labels`、`--age`、`--show-milestone`、`--summary`、`--sort`、`--reverse`、`--diff` を付けて出力した JSON も、前回の JSON として使えます（増えた項目は読みません。`--sort` と `--reverse` は並びだけが変わります）。

前回の JSON が見つからない、JSON として読めない、または `--json` の出力の形でない（`total` と `categories` がない、分類の `label` が見出しのラベルでない、Issue に `number`、`title`、`url` がないなど）ときは、エラーを標準エラーに出して終了コード 1 で終わります。
`--diff` の後にパスがない場合は、エラーを標準エラーに出して終了コード 2 で終わります。
`--diff` を付けない場合の出力は変わりません。前回の JSON の自動保存はしないので、次回のために `--json --output` で保存しておきます。

```
# 前回: JSON を保存しておく
gh issue list -L 1000 --json number,title,labels,url | uv run issue-digest --json --output last.json -

# 次回: 前回の JSON と比べる
gh issue list -L 1000 --json number,title,labels,url | uv run issue-digest --diff last.json -
```

出力例:

```
## 前回からの変化

### 新しい Issue - 1件

- [example/repo#5](https://github.com/example/repo/issues/5) 新しい Issue E

### なくなった Issue - 0件

なし

### 分類が変わった Issue - 1件

- [example/repo#12](https://github.com/example/repo/issues/12) 仕様を決めたい: 着手可能 → レビュー待ち
```

`--json` と同時に指定すると、JSON の末尾に `diff` を加えます。`added`、`removed`、`moved` の配列で、並びは Markdown の各小見出しの中と同じです。変化がなければ3つとも空の配列です。

- `added`、`removed` の各要素: `number`、`title`、`url`、`repository`（URL から読み取ったリポジトリ名。読み取れなければ `null`）、`categories`（`added` は今回の、`removed` は前回の分類のラベルの配列）
- `moved` の各要素: `number`、`title`（今回のもの）、`url`、`repository`、`from`（前回の分類のラベルの配列）、`to`（今回の分類のラベルの配列）

```json
"diff": {
  "added": [
    {"number": 5, "title": "新しい Issue E", "url": "https://github.com/example/repo/issues/5", "repository": "example/repo", "categories": ["agent:ready"]}
  ],
  "removed": [],
  "moved": [
    {"number": 12, "title": "仕様を決めたい", "url": "https://github.com/example/repo/issues/12", "repository": "example/repo", "from": ["agent:ready"], "to": ["agent:review"]}
  ]
}
```

`--diff` を付けた JSON も、次回の前回の JSON として使えます。

```
gh issue list -L 1000 --json number,title,labels,url | uv run issue-digest --json --diff last.json --output next.json -
```

## `--group-by assignee`

`--group-by assignee` を付けると、分類ごとの見出しの代わりに、担当者ごとの見出しで Issue を並べます。誰が何を抱えているかを見たいときに使います。

- 見出しは `## @alice - 3件` の形です。担当者のログイン名の順（大文字と小文字は区別せずに比べます）に並べ、最後に `## 担当者なし - N件` を出します。
- 担当者が複数いる Issue は、それぞれの担当者の下に出します。
- 各担当者の中は、リポジトリ名の順、同じリポジトリの中は Issue 番号の小さい順です（リポジトリ名がない Issue は最後に番号の小さい順）。
- 各 Issue の行末に、その Issue が入る分類の名前を `（着手可能）` の形で付けます。複数の分類に入る Issue は `（作業中, 着手可能）` のように見出しの順にカンマで区切ります。設定ファイルの `[headings]` があれば、その名前を使います。
- 0件の担当者の見出しは出しません（担当者なしも同じです）。出す Issue が1件もなければ、見出しの代わりに「なし」を出します。
- `--group-by` に指定できる値は `assignee` だけです。それ以外の値は、エラーを標準エラーに出して終了コード 2 で終わります。`--group-by` の後に値がない場合も終了コード 2 で終わります。
- Markdown だけで使えます。`--json` または `--csv` と同時に指定すると、エラーを標準エラーに出して終了コード 2 で終わります。設定ファイルの `json = true` は、`--group-by` を指定したら使いません。設定ファイルの `group_by` と `json = true` を一緒に書くとエラーです。
- `--max-chars` と同時に指定すると、最後の担当者から順に、各担当者の末尾の Issue の行を削って指定文字数以内に収めます（削った担当者の最後に `- ほか N 件`）。
- 担当者は入力の `assignees` から読みます。`assignees` がない入力では、すべて担当者なしになります。

ほかのオプションとの組み合わせは「[組み合わせ](combinations.md#組み合わせ)」の節を見てください。`--group-by` を付けない場合の出力は変わりません。設定ファイルの `group_by = "assignee"` でも指定できます（「[設定ファイルと `--config <パス>`](config.md#設定ファイルと---config-パス)」を参照）。

```
gh issue list -L 1000 --json number,title,labels,url,assignees | uv run issue-digest --group-by assignee -
```

出力例:

```
# Issue ダイジェスト（全 3 件）

## @alice - 2件

- [example/repo#1](https://github.com/example/repo/issues/1) 共同の Issue（作業中, 着手可能）
- [example/repo#2](https://github.com/example/repo/issues/2) レビュー中（レビュー待ち）

## @bob - 1件

- [example/repo#1](https://github.com/example/repo/issues/1) 共同の Issue（作業中, 着手可能）

## 担当者なし - 1件

- [example/repo#3](https://github.com/example/repo/issues/3) 担当者なしで着手可能（着手可能）
```

## `--fail-if-any <ラベル>`

`--fail-if-any <ラベル>` を付けると、指定した分類に Issue が1件以上あるとき、終了コード 3 で終わります。cron でダイジェストを保存しながら、判断待ち（`agent:needs-decision`）や中断（`agent:blocked`）があるときだけ通知したい、といった使い方を想定しています。
複数回指定でき、どれか1つの分類に1件以上あれば終了コード 3 です。どの分類にもなければ、終了コード 0 で終わります。

- ダイジェストはいつもどおり出力します。`--output` があるときは、ファイルに書き出してから終了コード 3 で終わります。
- 判定に使う件数は、`--since`、`--until` で絞った後の件数です。`--only`、`--exclude`、`--hide-empty`、`--limit`、`--max-chars` には左右されないので、出力に出ていない分類でも判定します。
- 指定できるラベルは `--only` と同じ6つ（`agent:ready`、`agent:working`、`agent:review`、`agent:needs-decision`、`agent:blocked`、`unclassified`）です。これは分類の名前で、設定ファイルの `[category_labels]` で分類に使うラベルを変えても変わりません。それ以外を指定すると、エラーを標準エラーに出して終了コード 2 で終わります。`--fail-if-any` の後に値がない場合も終了コード 2 です。
- エラー（終了コード 1、2）になるときは、今までと同じ終了コードで終わります（3 にはなりません）。ファイルに書き出せないときも終了コード 1 です。
- Markdown、`--json`、`--csv`、`--group-by` のどれでも効きます。
- 設定ファイルの `fail_if_any`（例: `fail_if_any = ["agent:blocked"]`）にも書けます。意味は `--fail-if-any` と同じで、コマンドラインで `--fail-if-any` を1つでも指定したら設定の値は使いません。空の配列は、書かないのと同じです。知らないラベル、配列でない値、文字列でない要素は、`エラー: 設定ファイルの fail_if_any ...` を標準エラーに出して終了コード 2 で終わります。

```
uv run issue-digest --fail-if-any agent:needs-decision --fail-if-any agent:blocked --output digest.md issues.json
```

## `--version`

`--version` を付けると、`issue-digest 0.1.0` のようにバージョンを1行で出力し、終了コード 0 で終わります。
バージョンは `pyproject.toml` の値です。ほかのオプションやファイルが指定されていても、バージョンだけを出力します（ファイルは読みません）。
`--version` を付けない場合の動作は変わりません。

```
uv run issue-digest --version
```
