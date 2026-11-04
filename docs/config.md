# 設定ファイルの詳しい説明

[README に戻る](../README.md)

## 設定ファイルと `--config <パス>`

毎回同じオプションを指定する手間を省くため、カレントディレクトリの `.issue-digest.toml` をオプションの既定値として読みます。ファイルがなければ、何も読まず今までどおり動きます。
`--config <パス>` で読むファイルを指定できます（このとき `.issue-digest.toml` は読みません）。指定したファイルがなければ、`エラー: 設定ファイルが見つかりません: <パス>` を標準エラーに出して終了コード 1 で終わります。
ホームディレクトリなど、ほかの場所の設定ファイルは探しません。

書けるキーは次の21個です。

| キー | 型 | 対応するオプション |
| --- | --- | --- |
| `hide_empty` | 真偽値 | `--hide-empty` |
| `summary` | 真偽値 | `--summary` |
| `only` | 文字列の配列（`--only` と同じ6つのラベル） | `--only` |
| `exclude` | 文字列の配列（`--exclude` と同じ6つのラベル） | `--exclude` |
| `stale` | 0以上の整数 | `--stale` |
| `since` | `"7d"` のような `<整数>d` の形の文字列（日付の形は書けない） | `--since 7d` |
| `sort` | `"updated"`、`"created"`、`"number"` のどれか | `--sort updated` / `--sort created` / `--sort number` |
| `reverse` | 真偽値 | `--reverse` |
| `show_assignees` | 真偽値 | `--show-assignees` |
| `show_author` | 真偽値 | `--show-author` |
| `show_labels` | 真偽値 | `--show-labels` |
| `show_milestone` | 真偽値 | `--show-milestone` |
| `age` | 真偽値 | `--age` |
| `title` | 1文字以上の文字列 | `--title` |
| `limit` | 1以上の整数 | `--limit` |
| `max_chars` | 1以上の整数 | `--max-chars` |
| `group_by` | `"assignee"` だけ | `--group-by assignee` |
| `json` | 真偽値 | `--json` |
| `fail_if_any` | 文字列の配列（`--fail-if-any` と同じ6つのラベル） | `--fail-if-any` |
| `headings` | テーブル（`[headings]`）。キーは `--only` と同じ6つのラベル、値は1文字以上の文字列 | なし（下の「[分類の見出しを変える](#分類の見出しを変えるheadings)」を参照） |
| `category_labels` | テーブル（`[category_labels]`）。キーは `unclassified` 以外の5つの分類の名前、値は1文字以上の文字列を1つ以上入れた配列 | なし（下の「[分類に使うラベルを変える](#分類に使うラベルを変えるcategory_labels)」を参照） |

`--output`、`--until`、`--version` など、上に挙げていないオプションは設定できません。

- コマンドラインの指定が設定ファイルより優先されます。`--stale 3` は設定の `stale` を上書きします。
- 設定の `only` と `exclude` は、コマンドラインで `--only` か `--exclude` を1つでも指定したら、どちらも使いません。指定しないときだけ使います。
- 設定に `only` と `exclude` を両方書く（どちらも空の配列でない）と、`エラー: --only と --exclude は同時に指定できません` を標準エラーに出して終了コード 2 で終わります。空の配列は、書かないのと同じです。コマンドラインで `--only` か `--exclude` を指定したときは、設定の `only` と `exclude` を使わないので、このエラーになりません。
- 設定の `since` は `"7d"` の形だけ書けます。日付の形（`"2026-10-01"`）は、書くと日付が固定になって古くなるので書けません。日付の形、`"7"`、`"7D"`、数値などは、`エラー: 設定ファイルの since には ...` を標準エラーに出して終了コード 2 で終わります。コマンドラインで `--since` を指定したら（日付の形でも日数の形でも）、設定の `since` は使いません。
- 設定の `since` を使うときにコマンドラインで `--until` を指定すると、`--since 7d` をコマンドラインで書いたときと同じように日付の順を検査します。設定の `since` から求めた日付が `--until` の日付より後なら、`エラー: 設定ファイルの since（<値>）は --until より前の日付にしてください` を標準エラーに出して終了コード 2 で終わります（同じ日ならエラーにならず、両方の条件で絞ります）。詳しくは「[`--until <日付>`](options.md#--until-日付)」を参照してください。
- 設定の `fail_if_any` は、コマンドラインで `--fail-if-any` を1つでも指定したら使いません。空の配列は、書かないのと同じです。
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
since = "7d"
limit = 5
title = "issue-digest"
show_labels = true
show_milestone = true
age = true
max_chars = 2000
group_by = "assignee"
exclude = ["unclassified"]
reverse = true
fail_if_any = ["agent:needs-decision", "agent:blocked"]
```

```
uv run issue-digest issues.json
uv run issue-digest --config my.toml --stale 3 issues.json
```

### 分類の見出しを変える（`[headings]`）

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

### 分類に使うラベルを変える（`[category_labels]`）

設定ファイルに `[category_labels]` テーブルを書くと、各分類にどの GitHub ラベルを割り当てるかを変えられます。`status:todo` など、`agent:*` 以外のラベルで運用しているリポジトリで使います。6つの分類（判断待ち、中断、レビュー待ち、作業中、着手可能、未分類）の意味と順番は変わりません。

```toml
[category_labels]
"agent:ready" = ["status:todo"]
"agent:working" = ["status:doing", "status:in-progress"]
```

- キーは分類の名前（`agent:needs-decision`、`agent:blocked`、`agent:review`、`agent:working`、`agent:ready` の5つ）です。`unclassified` は指定できません。
- 値は GitHub ラベル名の文字列の配列（1つ以上、各1文字以上）です。書いたラベルのどれかを持つ Issue が、その分類に入ります。
- 書いた分類は、その分類の既定のラベル（`agent:ready` など）を使わなくなります。上の例では、`agent:ready` だけを持つ Issue は未分類に入ります。
- 書かない分類は、今までどおり既定のラベル（分類の名前と同じラベル）で分類します。
- ラベル名の比較は、大文字と小文字を区別します。
- 複数の分類に当てはまる Issue は、今までどおりすべての分類に入ります。同じラベルを2つの分類に割り当ててもエラーにしません。どの分類のラベルも持たない Issue は未分類に入ります。
- 分類の名前は変わりません。`--only`、`--exclude`、`--fail-if-any` に指定する名前、設定の `only`、`exclude`、`headings` のキー、Markdown の見出しの `(agent:ready)`、JSON と CSV の `label` は、設定に関係なく今までの名前（`agent:ready` など）です。そのため、`[category_labels]` を書く前の `--json` の出力も `--diff` の前回の JSON として使えます。
- `--show-labels` と JSON の `labels` には、ここに書いたラベルを出しません（「[`--show-labels`](options.md#--show-labels)」を参照）。
- 知らない分類の名前や `unclassified` をキーに書いた、値が文字列の配列でない、空の配列、空の文字列を含む、`[category_labels]` がテーブルでない、のどれかのときは、どのキーかを示すエラーを標準エラーに出して終了コード 2 で終わります。
- コマンドラインに対応するオプションはありません。`[category_labels]` を書かない場合の動きは変わりません。

移行の例: 書いた分類は既定のラベルを使わなくなるので、`agent:ready` から `status:todo` へ切り替える間は、次のように両方を書くと、どちらのラベルの Issue も「着手可能」に入ります。

```toml
[category_labels]
"agent:ready" = ["status:todo", "agent:ready"]
```
