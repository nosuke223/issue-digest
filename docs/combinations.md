# オプションの組み合わせ

[README に戻る](../README.md)

## 組み合わせ

- 入力を複数指定したときも、すべてのオプションは入力が1つのときと同じように効きます。まとめた後の Issue（URL が同じものは最初の1件だけ）が、件数、`--since`、`--until`、`--only`、`--exclude`、`--sort`、`--reverse`、`--limit`、`--max-chars`、`--summary`、`--group-by`、`--diff`、`--fail-if-any` の対象です。設定ファイルに入力を書くキーはありません。
- `--repo` は、ほかのオプションすべてと同時に使えます。取得した Issue は、ファイルから読んだ Issue と同じように、件数、`--since`、`--until`、`--only`、`--exclude`、`--sort`、`--reverse`、`--limit`、`--max-chars`、`--summary`、`--group-by`、`--diff`、`--fail-if-any`、`--json`、`--csv` の対象です。`--repo` での取得に失敗したとき（終了コード 1）は、`--output` のファイルを書き出さず、`--fail-if-any` の判定もしません。
- `--hide-empty`、`--only`、`--stale`、`--since`、`--until`、`--sort`、`--reverse`、`--limit`、`--title`、`--output`、`--diff` は、どれも同時に使えます（`--csv` との併用は下の項目を参照）。
- `--reverse` は `--sort` の後に並びを逆にし、そのあとで `--limit` と `--max-chars` が効きます（`--limit` は逆にした後の先頭から、`--max-chars` は逆にした後の末尾の行から）。
- `--since`、`--until` で絞るのは出力する Issue です。件数（総件数、分類ごとの件数、`--summary`）は絞った後の Issue で数えます。`--json`、`--csv` でも同じです。両方を指定すると、両方の条件に合う Issue だけを出します。`--since` の日付が `--until` の日付より後ならエラー（終了コード 2）です。`--since` を指定せず設定ファイルの `since` を使うときも、その日付が `--until` の日付より後ならエラー（終了コード 2）です。
- `--diff` の比較は、`--only`、`--exclude`、`--hide-empty`、`--limit`、`--since`、`--until` に関係なく全分類の全件で行います。`## 前回からの変化` の節の行には、`--stale`、`--show-assignees`、`--show-author`、`--show-labels`、`--age`、`--show-milestone` の印を付けません。
- `--max-chars` は、Markdown を出すほかのオプションと同時に使えます。`--limit` と同時に指定すると、`--limit` で省いた後の出力をさらに削り、`- ほか N 件` の件数は両方で省いた件数の合計になります。`--output` と同時に指定すると、削った後の出力をファイルに書き出します（`--json`、`--csv`、`--group-by` との併用は下の項目を参照）。
- `--exclude` は `--only` 以外と同時に使えます。`--only` と同時に指定するとエラーです。
- `--json` と同時に指定した場合
  - `--hide-empty`、`--only`、`--exclude` は Markdown と同じように効き、出力する分類が変わります。
  - `--stale` を同時に指定すると、印が付く Issue にだけ `stale_days`（経過日数）を加えます。
  - `--sort updated`、`--sort created`、`--sort number` のどれかを同時に指定すると、各分類の `issues` の順が変わります。`--reverse` を同時に指定すると、`issues` の順が逆になります。
  - `--summary` は無視します（JSON には分類ごとの `count` があるため）。
  - `--show-assignees` を同時に指定すると、各 Issue に `"assignees": ["alice", "bob"]`（login の配列。担当者がいなければ空の配列）を加えます。`--show-assignees` を付けない JSON には `assignees` を出しません。
  - `--show-author` を同時に指定すると、各 Issue に `"author": "bob"`（作成者の `login` の文字列。なければ `null`）を加えます。`--show-author` を付けない JSON には `author` を出しません。
  - `--show-labels` を同時に指定すると、各 Issue に `"labels": ["bug"]`（`agent:` で始まらず、設定ファイルの `[category_labels]` にも書いていないラベルの配列。なければ空の配列）を加えます。`--show-labels` を付けない JSON には `labels` を出しません。
  - `--age` を同時に指定すると、各 Issue に `"age_days": 12`（作成からの経過日数の整数。`createdAt` がなければ `null`）を加えます。`--age` を付けない JSON には `age_days` を出しません。
  - `--show-milestone` を同時に指定すると、各 Issue に `"milestone": "v1.0"`（マイルストーンの名前の文字列。なければ `null`）を加えます。`--show-milestone` を付けない JSON には `milestone` を出しません。
  - `--diff` を同時に指定すると、末尾に `diff`（`added`、`removed`、`moved`）を加えます。`--diff` を付けない JSON には `diff` を出しません。
- `--json` と `--output <パス>` を同時に指定すると、JSON をファイルに書き出します。
- `--csv` と同時に指定した場合
  - `--hide-empty`、`--only`、`--exclude`、`--since`、`--until`、`--sort`、`--reverse`、`--limit`、`--output` は Markdown と同じように効きます（`--limit` は各分類の先頭から指定件数の行にします）。
  - `--stale`、`--age`、`--show-assignees`、`--show-author`、`--show-labels`、`--show-milestone`、`--summary`、`--title`、`--diff` は、CSV に対応する列や行がないので無視します（エラーにしません。`--diff` の前回の JSON も読みません）。
  - `--json` と同時に指定すると、`エラー: --json と --csv は同時に指定できません` を標準エラーに出して終了コード 2 で終わります。
- コマンドラインの `--json` または `--csv` と `--max-chars` を同時に指定すると、`エラー: --max-chars は --json、--csv と同時に指定できません（Markdown だけで使えます）` を標準エラーに出して終了コード 2 で終わります。設定ファイルの `json = true` は `--max-chars` を指定したら使わないので、`--max-chars` と設定の `json = true` だけなら Markdown を出します（`--csv` を指定したときは、`--csv` との同時指定のエラーです）。
- `--stale`、`--show-assignees`、`--show-author`、`--show-labels`、`--age`、`--show-milestone` の印が付くときは、`（N日更新なし）（担当: @alice）（作成者: @bob）（ラベル: bug）（作成から12日）（マイルストーン: v1.0）` の順です。
- `--summary` の件数の行は、`--only` や `--hide-empty` に関係なく、常に6つの分類すべての件数を出します。
- `--group-by assignee` と同時に指定した場合
  - `--only`、`--exclude`、`--since`、`--until` は、出す Issue を絞ります。`--only`、`--exclude` では、選んだ分類のどれかに入る Issue だけを出し、行末の分類の名前も選んだ分類だけにします。
  - 見出しの総件数は、分類ごとのときと同じです（`--since`、`--until` で絞った後の全件。`--only`、`--exclude` に関係なし）。
  - `--sort`、`--reverse`、`--limit` は各担当者の中で効きます（`--limit` で出さなかった Issue があれば、その担当者の最後に `- ほか N 件`。見出しの件数は全件のまま）。
  - `--stale`、`--show-assignees`、`--show-author`、`--show-labels`、`--age`、`--show-milestone` の印は、分類の名前の後ろに付きます（例: `（作業中, 着手可能）（13日更新なし）（担当: @alice）（作成者: @bob）（ラベル: bug）（作成から12日）（マイルストーン: v1.0）`）。
  - `--summary` は、総件数の次に担当者ごとの件数を1行で出します（例: `@alice 2 / @bob 1 / 担当者なし 1`。順は見出しと同じ）。この行は `--only`、`--exclude` に関係なく、`--since`、`--until` で絞った後の全件で数えます。出す Issue がなければ「なし」です。
  - `--hide-empty` は効果がありません（0件の担当者は出さないため）。
  - `--diff` の `## 前回からの変化` の節は、分類ごとのときと同じです。
  - `--title`、`--output`、`--config` は分類ごとのときと同じように効きます。
  - `--json`、`--csv` と同時に指定するとエラーです。
  - `--max-chars` は、最後の担当者の見出し（`## 担当者なし` があればそれ）から順に、各担当者の末尾の Issue の行を1行ずつ削ります。最後の担当者の Issue の行がなくなったら、1つ前の担当者を削ります。削った担当者の最後に `- ほか N 件` を出し、`--limit` で省いた件数とまとめて1行にします。見出し、件数、`--summary` の行、`--diff` の節は削りません。行末の分類の名前と印を含めた行で数えます。すべて削っても収まらないときの警告は、分類ごとのときと同じです。
- `--fail-if-any` は、ほかのオプションすべてと同時に使えます。終了コードの判定は `--since`、`--until` で絞った後の件数で行い、`--only`、`--exclude`、`--hide-empty`、`--limit`、`--max-chars` には左右されません。`--json`、`--csv`、`--group-by`、`--output` のどれと同時でも、出力してから終了コード 3 で終わります。設定ファイルの `fail_if_any` も同じで、コマンドラインで `--fail-if-any` を指定したときは使いません。
- 終了コードは「[終了コード](exit-codes.md#終了コード)」の節を見てください。
- 設定ファイルの `group_by`、`max_chars` と `json = true` を一緒に書くと、コマンドラインで `--group-by`、`--max-chars` と `--json` を同時に指定したときと同じエラーで終了コード 2 です。コマンドラインで `--json` か `--csv` を指定したときは、設定の `group_by` と `max_chars` は使いません。
- `--config` は、ほかのオプションすべてと同時に使えます。設定ファイルの値は、コマンドラインで同じオプションを指定したときは使いません（詳しくは「[設定ファイルと `--config <パス>`](config.md#設定ファイルと---config-パス)」）。
- 設定ファイルの `[category_labels]` は、分類に使うラベルだけを変えます。`--only`、`--exclude`、`--fail-if-any`、`--diff`、`--group-by` などは、変えた後の分類に今までの名前（`agent:ready` など）で効きます。
- `--version` は、ほかのオプションやファイルの指定があっても、バージョンだけを出力します。
