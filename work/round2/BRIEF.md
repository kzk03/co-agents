# Round 2 ブリーフ(2026-10-26、全エージェント必読。work/CONTEXT.md のルールも厳守)

## 研究の問い(当初)
HUMANS.md(人間が理解・判断・検証・責任を持つべき事項)に何を書くべきかを、人間がコードレビューで変更を止めた理由から実データで示す。
指導教員の指針:「スケールに殺されないテーマ」= モデルが強くなっても無効化されない問い。対象は SE のトップ会議(ICSE/FSE/ASE/MSR/TOSEM/TSE/EMSE)。

## これまでの結果(数値はすべて実出力から転記。出典ファイルつき)
1. 割合(コードブック v0、LLM 3コーダー多数決)
   - Gerrit(OpenStack 人間同士)-1/-2 100件: H系 39.6%(95%CI 28.1–51.6)、盲検ダンプで再コードしても 36.1%(25.6–46.9)。-2 では H 14/15。 work/blind/blind_stats.out
   - AIDev(エージェント PR への人間 CR)100件: H系 17.6%(9.2–26.9)。 outputs/aidev/
   - GitHub 人間 PR(pilot 39 repo)100件: 28.3%(結末層)。ただし CR の 70% が home-assistant/core。 work/baseline/repo_sensitivity.txt
2. **同じ repo 内でマッチした比較では、人間 PR とエージェント PR の H系比率に差がない**:HU−AG 差 0.049(repo クラスタ bootstrap 95%CI −0.168〜0.243)、MH OR 1.15(0.52–2.54)。 work/baseline/within/stats.txt
   → Gerrit/GitHub・人間/AI の差は、作者ではなく repo・プラットフォーム構成で説明される可能性が高い。
3. **再現実験(LLM に人間のコメントを見せずにレビューさせ、人間の主要な指摘が出るか)**:AIDev 30件(H15/C15)、条件 A 差分のみ / B +repo 文書 / C +Issue と先行議論。
   - sonnet 判定 yes 率: A H 53% vs C 60%、B 53% vs 60%、C 60% vs 73%。opus 判定では A H 67% vs C 53%。H と C に有意差なし。
   - **ただし PR 本文がレビュー後に編集されていたリーク**が 30件中12件(H 8, C 4)。リークのない18件に限ると A: H 2/7 (29%) vs C 7/11 (64%)。リークを除いた本文に差し替えた Cr では H 8件中 yes 3。n が小さすぎて結論は出ない。 work/reproduce/results/stats_v1.txt, work/reproduce/protocol.md
   - 主観の inferable ラベルと実測はほとんど対応しない。
4. 委任(上流)仮説:エージェント PR では判断がレビュー前(Issue・依頼文)に移っているか → H系では上流に書かれていたもの 0/10、C系 10/41。仮説は支持されない。レビュアー=依頼者が 79.6%(Copilot が大半)。 work/delegation/analysis.txt
5. コードブック v1(work/codebook/codebook_v1.md):H を K(情報不足:K-pub / K-priv)、R(書かれていない規則:R-tech / R-gov)、D(その場の決定:D-dir / D-risk)に分解。HUMANS.md 固有領域 = D + K-priv + R-gov。私(Opus) vs sonnet で 9値 κ 0.60。最大の不一致は C と D の境界。実在の文書確認で「書かれていたのに無視された」例あり(G027)。
6. 関連研究の精査:work/critic/literature.md(Peralta MSR'26、Duma EASE'26、Abujadallah、Khelifi、Takerngsaksiri、Farrag、Russo、Yu、Rahman、Park、Dhanorkar、Monperrus、Agent READMEs ほか)。critic の批判:work/critic/REPORT.md。

## 現在の弱点(自覚している)
- 「人間 vs AI 作者で判断の種類が違う」という当初の筋は within-repo で消えた。
- 「H系 = AI に再現できない」もデータでは支持されていない(リーク除去後に差の兆候はあるが n=18)。
- コーダーがすべて LLM(同社)。人間のラベルはまだない。
- 観測窓がレビューだけ。理由を書かない拒否・レビューなしのマージが多数派(Peralta: rejected の 33% は理由不明)。

## 利用できるデータ
- data/aidev/*.parquet(AIDev-pop: pull_request, pr_reviews, pr_review_comments, pr_comments, pr_commits, repository, user)
- data/raw_json → OpenStack Gerrit 232 repo(読み取り専用)
- ~/projects/after_ses/pilot/raw_full/<owner__repo>/(人間 PR を含む 39 repo、41,969 PR。読み取り専用)
- outputs/github/humans_files/(GitHub 上の実在 HUMANS.md 186件)
- gh api(認証済み、レート制限注意)、claude -p(**利用上限で過去に止まった。使う場合は事前に回数を宣言し、合計 100 回以内**)
