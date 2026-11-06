# プロジェクトのルール（AIエージェント向け）

実装エージェントの共通のルールは、agent ユーザーの `~/.claude/CLAUDE.md` にある（agent-env の `agent-user/CLAUDE.md`。直すときは agent-env で直す）。このファイルには、このプロジェクトに固有のことだけを書く。共通のルールと食い違うときは、このファイルを優先する。

## プロジェクト固有

- 概要: GitHub Issue の状況（`gh issue list --json` の出力）をラベル別にまとめ、Markdown のダイジェストを出力する CLI
- 言語・フレームワーク: Python 3.12、uv（パッケージ管理）、pytest、ruff。コードは `src/issue_digest/`、テストは `tests/`
- テストコマンド: `uv run pytest`（失敗したテストだけ再実行: `uv run pytest --lf`）
- lint / format コマンド: `uv run ruff check .` / `uv run ruff format .`
- 読まなくてよいディレクトリ: `.venv/`、`.pytest_cache/`、`.ruff_cache/`、`uv.lock`
- その他の注意:
  - テストで GitHub に接続しない。入力は JSON ファイル（`tests/` 以下に置くサンプル）で与える
  - 依存パッケージの追加（`uv add`）は「止まって聞く」に当たる
  - オプションを追加・変更・削除したら、README の「オプション一覧」の表、`docs/options.md` のそのオプションの節、`docs/combinations.md`（ほかのオプションとの併用の決まりがあるとき）、`docs/config.md` の表（設定ファイルに書けるとき）、`--help`（`USAGE`）をそろえて更新する
