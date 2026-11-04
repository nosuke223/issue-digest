# 終了コードの一覧

[README に戻る](../README.md)

## 終了コード

cron や CI で終了コードによって処理を分けたいときの一覧です。

| 終了コード | 意味 | 起きる例 |
| --- | --- | --- |
| 0 | 正常 | ダイジェストを出力した。`--fail-if-any`（または設定の `fail_if_any`）で分類を指定したときは、指定した分類のどれにも Issue がなかった |
| 1 | 実行時のエラー | 入力のファイルが読めない（`エラー: ファイルが見つかりません: <パス>`）、設定ファイルが見つからない・読めない（`エラー: 設定ファイルが見つかりません: <パス>`）、`--diff` の前回の JSON が見つからない・形が違う、`--output` のファイルを書き出せない、`gh` が失敗した、`updatedAt` や `createdAt` が日時として読めない |
| 2 | オプションの指定のエラー | `--fail-if-any` や `--only` に知らない値を指定した、`--only` と `--exclude` のように同時に使えないものを指定した、`--repo` の形の誤り、設定ファイルの中身の誤り（TOML として読めない、知らないキー、値の型や形の誤り） |
| 3 | `--fail-if-any`（または設定の `fail_if_any`）で指定した分類に Issue がある | `--fail-if-any agent:ready` を付けて（または設定に `fail_if_any = ["agent:ready"]` と書いて）、着手可能の分類に Issue が1件以上あった |

- エラー（1 か 2）のときは、3 より 1 か 2 を優先します。`--fail-if-any` の分類に Issue があっても、エラーなら 3 にはなりません。
- 終了コード 3 のときも、ダイジェストはいつもどおり出力します。`--output` があるときは、ファイルに書き出してから終了コード 3 で終わります。

cron でダイジェストを保存しながら、終了コード 3 のときだけ通知する例です（`notify` は通知するコマンドに置き換えてください）。

```
uv run issue-digest --fail-if-any agent:needs-decision --fail-if-any agent:blocked --output digest.md issues.json
status=$?
if [ "$status" -eq 3 ]; then notify "判断待ちか中断の Issue があります"; fi
```
