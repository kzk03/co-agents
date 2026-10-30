# co-agents

HUMANS.md(人間が理解・判断・責任を持つべき事項)の研究の作業ディレクトリ。2026-10-30 に after_ses/humans_md から独立リポジトリ化(after_ses のコードには依存しない。生データは data/ に実体で置き git 管理外。data/README.md 参照)。
ノート(考察・結果の解釈)は Obsidian Vault の `Research/HUMANS-md/`(入口は HUMANS-md.md) に置く。

## 構成

```
co-agents/
├── data/raw_json/      # OpenStack Gerrit(232 repo)。読み取り専用(git 管理外)
├── data/pilot_raw_full/  # GitHub 39 repo(AIresearch パイロット、git 管理外)
├── data/aidev/        # AIDev v4 の AIDev-pop テーブル(HF hao-li/AIDev)
├── scripts/
│   ├── reproduce.py   # データ取得: github / gerrit_extract / gerrit_sample
│   ├── aidev_feasibility.py  # AIDev: 人間の CHANGES_REQUESTED の抽出と件数
│   ├── aidev_sample.py       # AIDev: 100件の層化抽出と分類用テキスト
│   ├── irr.py         # LLM コーダーでの分類(code)と一致率・全体推定(stats)。gerrit / aidev を引数で選ぶ
│   └── make_figs.py   # 図の生成(outputs/fig と Vault の fig に出力)
└── outputs/
    ├── github/        # HUMANS.md の検索結果と本文
    ├── aidev/         # 人間の CR 一覧、100件サンプル、分類(coding_opus_v0.csv、irr/)
    ├── gerrit/        # -1/-2 投票の全件、パイロット100件、手作業の分類(pilot_coding_v0.csv)
    │   └── irr/       # コードブック、Sonnet/Haiku の出力、irr_merged.csv
    └── fig/
```

## 実行(このディレクトリで)

```
uv run scripts/reproduce.py gerrit_extract
uv run scripts/reproduce.py gerrit_sample
uv run scripts/irr.py code gerrit sonnet
uv run scripts/irr.py stats gerrit
uv run scripts/aidev_feasibility.py
uv run scripts/aidev_sample.py
uv run scripts/irr.py code aidev sonnet
uv run scripts/irr.py stats aidev
uv run scripts/make_figs.py
```

- `github` は gh CLI(認証済み)、`gerrit_sample` は review.opendev.org(公開 API)、`irr.py code` は claude CLI を使う
- `gerrit_sample`、`irr.py code` を実行すると既存の出力が上書きされる(sample は seed=42 で決定的。LLM の出力は決定的ではない)
