# 入力の詳しい説明

[README に戻る](../README.md)

## 入力

ファイルを指定する場合:

```
uv run issue-digest issues.json
```

パイプで渡す場合（引数に `-` を指定すると標準入力から読みます）:

```
gh issue list -L 1000 --json number,title,labels,url | uv run issue-digest -
```

入力は複数指定できます。複数のリポジトリの Issue を1つのダイジェストで読みたいときに使います。

```
gh issue list -L 1000 --repo alpha/tools --json number,title,labels,url > alpha.json
gh issue list -L 1000 --repo beta/app --json number,title,labels,url | uv run issue-digest alpha.json -
```

`gh` を自分で実行する代わりに、`--repo` でリポジトリを指定して取得することもできます（「[`--repo <OWNER/REPO>`](#--repo-ownerrepo)」を参照）。ファイル入力と混ぜて指定できます。

```
uv run issue-digest --repo alpha/tools --repo beta/app
uv run issue-digest alpha.json --repo beta/app
```

- 項目の形や型が `gh` の出力と違う入力は読めません。`エラー: ファイルを読み込めません: <パス> (TypeError)` のように、読めなかった入力を示すエラーを出して終了コード 1 で終わります。出力の形（Markdown、`--json`、`--csv`）や `--show-*` の有無に関係なく、次のどれかに当たるとエラーになります。
  - `number` が整数でない（`"1"` のような文字列や `true` を含む）
  - `title`、`url` が文字列でない
  - `labels` が `[{"name": ...}]` の形の配列でない、または各 `name` が文字列でない（`null` を含む）
  - `assignees` が `[{"login": ...}]` の形の配列でない、または各 `login` が文字列でない（`null` を含む）
  - `milestone`、`author` が `{"title": ...}`、`{"login": ...}` の形のオブジェクトでない、または `title`、`login` が文字列でも `null` でもない
  - `milestone`、`author`、`assignees` が `null` または無いとき、`milestone` の `title`、`author` の `login` が `null` または無いときは、付けるものがないだけでエラーにはなりません。`number`、`title`、`labels`、`url` や、`labels` の `name`、`assignees` の `login` が無いときは、`(KeyError)` のエラーになります。
- 入力は指定した順に読み、すべての Issue を1つにまとめてから、分類・絞り込み・並べ替えをします。`--repo` で取得した Issue は、ファイル入力（`-` を含む）をすべて読んだ後に、`--repo` を指定した順に加えます（コマンドラインで `--repo` をファイルより前に書いても同じです）。
- `-`（標準入力）はほかのファイルと混ぜて指定できますが、1回までです。2回以上指定すると、`エラー: -（標準入力）は1回だけ指定できます` を標準エラーに出して終了コード 2 で終わります。
- ファイル入力も `--repo` も1つも指定しないときは、使い方を標準エラーに出して終了コード 2 で終わります。ファイル入力がなくても、`--repo` が1つ以上あれば動きます。
- 1つでも読めない入力があれば、そのファイルを示すエラー（`エラー: ファイルが見つかりません: <パス>` など）を標準エラーに出して終了コード 1 で終わります。`updatedAt` や `createdAt` が日時として読めないときも、入力を前に付けて示します（例: `エラー: bad.json: Issue #1 の updatedAt を日時として読めません: yesterday`。標準入力は `エラー: -（標準入力）: Issue #1 の ...`、`--repo` で取得した出力は `エラー: --repo alpha/bad: Issue #1 の ...`）。
- Issue は URL で見分けます（大文字と小文字は区別しません）。URL が同じ Issue が複数の入力（または1つの入力の中）にあるときは、最初に出てきた1件だけを使い、件数を二重に数えません。別のリポジトリの同じ番号の Issue は、別の Issue として数えます。

## `--repo <OWNER/REPO>`

`--repo <OWNER/REPO>` を付けると、`gh` コマンドを実行して、指定したリポジトリの開いている Issue を取得し、入力に加えます。必要な項目の付け忘れや、件数の切り捨てを避けたいときに使います。
`gh` をインストールし、`gh auth login` でログインしておく必要があります（issue-digest は認証情報を読みません）。

```
uv run issue-digest --repo nosuke223/issue-digest
uv run issue-digest --repo alpha/tools --repo beta/app --summary
```

- 1つのリポジトリにつき、`gh issue list -R <OWNER/REPO> --state open -L 1000 --json number,title,labels,url,updatedAt,createdAt,assignees,milestone,author` を実行します。ほかのオプション（`--stale` など）に関係なく、毎回すべての項目を取得します。シェルは通しません。
- 取得するのは開いている Issue だけです。閉じた Issue を取得するオプションや、取得件数の上限を変えるオプションはありません。
- 1つのリポジトリで1000件を取得したときは、`警告: <リポジトリ> の Issue を1000件取得しました。これ以上ある場合は、一部が含まれていません` を標準エラーに出します（ダイジェストはいつもどおり出力し、終了コードは変わりません）。
- 複数回指定でき、ファイル入力と混ぜて指定できます。取得した Issue は、ファイルから読んだ Issue と同じように1つにまとめます（URL が同じ Issue は最初の1件だけ。リポジトリ名の表示も同じ）。同じリポジトリ（大文字と小文字を区別しない）を2回指定してもエラーにせず、`gh` は1回だけ実行します。
- 値の形は `OWNER/REPO` か `HOST/OWNER/REPO`（GitHub Enterprise など）です。各部分に使えるのは英数字、`.`、`_`、`-` だけです。それ以外の値（`-` で始まる値、空、スラッシュの数が違うなど）は、`gh` を実行せずに `エラー: --repo には OWNER/REPO か HOST/OWNER/REPO の形を指定してください: <値>` を標準エラーに出して終了コード 2 で終わります。`--repo` の後に値がない場合も終了コード 2 です。
- 取得に失敗したときは、ダイジェストを出力せずに、標準エラーに次のどれかを出して終了コード 1 で終わります。
  - `gh` が見つからない: `エラー: gh コマンドが見つかりません`
  - `gh` が失敗した（ログインしていない、リポジトリが見つからないなど）: `エラー: gh issue list に失敗しました: <リポジトリ>（<gh の標準エラーの最初の1行>）`（`gh` の標準エラーが空のときは `（終了コード N）`）
  - 60秒で終わらない: `エラー: gh issue list が60秒で終わりませんでした: <リポジトリ>`（`gh` は中断します）
  - `gh` の出力が読めない: `エラー: gh issue list の出力を読み込めません: <リポジトリ> (JSONDecodeError)` など
  - `updatedAt` や `createdAt` が日時として読めない: `エラー: --repo <リポジトリ>: Issue #1 の updatedAt を日時として読めません: yesterday`（ファイル入力の `エラー: <パス>: ...` と区別するため `--repo` を付けます）
- 設定ファイルに取得先を書くキーはありません。

パイプで `gh issue list` の出力を渡す場合は、`-L` で件数を指定しないと、`gh` の既定の30件で切られます（例: `gh issue list -L 1000 --json number,title,labels,url | uv run issue-digest -`）。

## リポジトリ名の表示

入力が1つでも、各 Issue にリポジトリ名（`owner/repo`）を付けて出します。リポジトリ名は Issue の URL（`https://<ホスト>/<owner>/<repo>/issues/<番号>` または `.../pull/<番号>`）から読み取ります。ホストは `github.com` 以外でもかまいません。

- Markdown: Issue の行は `- [owner/repo#12](url) タイトル` の形です（`--group-by assignee`、`--diff` の節の行も同じ）。リポジトリ名の Markdown の記号（`\` `` ` `` `*` `_` `[` `]` `<` `>`）は、タイトルと同じようにエスケープします（例: `my_repo` は `my\_repo`）。
- JSON: 各 Issue に `"repository": "owner/repo"` を加えます（`diff` の `added`、`removed`、`moved` の各要素にも）。
- CSV: 末尾の `repository` 列に出します。
- URL から読み取れない Issue は、エラーにせず、Markdown は今までどおり `- [#12](url) タイトル`、JSON は `"repository": null`、CSV は空にします。

各分類の中の既定の並びは、リポジトリ名（大文字と小文字を区別しない）の順、同じリポジトリの中は番号の小さい順です。リポジトリ名がない Issue は最後に番号の小さい順で並べます。入力が1つで、すべて同じリポジトリのときは、番号の小さい順です。
