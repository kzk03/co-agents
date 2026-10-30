# 共有コンテキスト(全エージェント必読)

## 研究の問い
HUMANS.md(人間が理解・判断・検証・責任を持つべき事項を書く文書)に何を書くべきかを、
「人間がコードレビューで変更を止めた理由」から実データで示す。AI エージェント時代に
人間に残る判断は何か。指導教員の指針:「スケールに殺されないテーマ」= モデルが強くなっても
無効化されない問い。

## これまでの結果(数値はすべて実出力から)
- Gerrit(OpenStack, 人間同士):-1/-2 100件。H系(人間の文脈・判断)は層補正後 39.6%(95%CI 28.1–51.6%)。
  -2 では 14/15 が H系。C/H 二分の κ(Opus–Sonnet)=0.83。
- GitHub(AIDev-pop, エージェント PR への人間の CHANGES_REQUESTED):4,681件(全件に理由テキストあり)、
  Copilot が 83%。100件サンプル、H系は層補正後 17.6%(95%CI 9.2–26.9%)。closed(強い拒否)では 27%、
  merged/open では 15%。C/H 二分 κ=0.64。理由を書かない拒否(Revert / Do not make this update)が目立つ。
  `@copilot` 等エージェント宛て指示は CR の 40%、だが指示か否かで H系の比率はほぼ同じ。
- 未解決:作者(人間/AI)の効果とプラットフォーム(Gerrit/GitHub)の効果が交絡している。
- 仮説(未検証):エージェント PR では、文脈・方針の判断はレビューより前(Issue・依頼文)に移っている。

## 分類(コードブック v0)
`outputs/gerrit/irr/codebook_v0.md`(Gerrit 用)、`outputs/aidev/irr/codebook_v0_github.md`(GitHub 用)。
C1 正しさ / C2 保守性 / C3 付随物不足 / M 機械的 / H1 人間の文脈 / H2 方針・設計判断 / H3 暗黙の前提 /
H4 プロセス・責任 / H5 セキュリティ・権限 / BOT / UNK。加えて inferable(yes/partial/no)。

## ディレクトリ(作業はすべて ~/projects/after_ses/humans_md/ の中)
- data/raw_json → Gerrit 生データ(読み取り専用)、data/aidev/ → AIDev-pop parquet
- scripts/:reproduce.py, irr.py(`irr.py code <set> <model>`, `irr.py stats <set>`), aidev_feasibility.py, aidev_sample.py, make_figs.py
- outputs/gerrit/, outputs/aidev/(sample100.json, dump.txt, coding_opus_v0.csv, irr/, human_blocks.parquet)
- GitHub 人間 PR の候補データ(読み取り専用):~/projects/after_ses/pilot/raw_full/<owner__repo>/
  (prs_full.jsonl: number, createdAt, mergedAt, closedAt, author, files, reviews, commits /
   review_bodies.jsonl: number, reviews[{author,state,submittedAt,body,comments}])。39 repo、41,969 PR、
  AI レビューが付いた PR だけを集めたもの(選び方の偏りあり)。CHANGES_REQUESTED 6,720件。
- Python は `uv run`(pandas, pyarrow, matplotlib 入り)。追加パッケージは `uv add`。
- LLM コーダー:`claude -p --model {sonnet|haiku} --max-turns 1 --disallowedTools "Bash,Read,Write,Edit,WebFetch,WebSearch,Agent,Glob,Grep,TodoWrite,ToolSearch,Skill,NotebookEdit"`
  を空ディレクトリで実行(irr.py 参照)。GitHub API は `gh api`(認証済み、レート制限に注意)。

## ルール(厳守)
- 書き込みは ~/projects/after_ses/humans_md/ の中だけ。自分の担当は work/<担当名>/ に置く。
  共有スクリプト(scripts/)を変えるときは既存の動作を壊さない(後方互換)。
- after_ses の他の場所・pilot/・Master_research・Obsidian Vault には書かない。git commit しない。
- サーバ(socsel 等)に ssh しない。
- 数値は実際の出力から転記。推測で書かない。確認できないものは「未確認」と書く。
- 最後に work/<担当名>/REPORT.md を書く:目的 / やったこと(実行コマンド)/ 結果(数値と出力ファイルのパス)/
  わかったこと / 限界 / 他の担当への質問・反論 / 次にやるべきこと。日本語、簡潔に。
