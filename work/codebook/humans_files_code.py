"""outputs/github/humans_files/ 186件の種類分け + 本研究の意味の HUMANS.md の中身を v1 カテゴリで数える。
種類と中身のコードは私(Opus)がファイルを読んで付けた(下の辞書)。uv run python work/codebook/humans_files_code.py"""
import collections, csv, json, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
W = os.path.join(ROOT, "work/codebook")
ex = json.load(open(os.path.join(ROOT, "outputs/github/humans_exact.json")))
PFX = {
 "A": ["EdmundLimBoEn__", "MarkStokes-outlook__", "Stoked-Builds__", "hehamalainen__", "thegoodcompany-sst__", "danja__jigdaw",
       "tomtev__termlings", "aibozo__gok", "TeamLith__lith", "Aurora-Viewer__", "thewebartisan7__riservo", "TimeLordRaps__verifier"],
 "G": ["Digital-Grinnell__", "Jiaxu-Li__", "PerceptronV__", "mmoerz__", "nyejames__", "fielding__", "xingrz__", "oaknational__",
       "cristianbica__", "attogram__", "benthomasson__", "dollspace-gay__", "iotaledger__", "lukelee-sl__", "C-Kennelly__",
       "nakamura196__", "atisharma__", "octave-commons__", "google__myvibe", "Inna949Festchuk__"],
 "M": ["Citadel-Inc__", "recisio__", "halfaipg__", "mdhender__", "Rethunk-Tech__", "prdoyle__", "getsentry__", "La-Volpe__",
       "emb715__", "seismicgear__", "danparshall__", "jerpint__", "day50-dev__", "NikolaySus__", "FloareDor__", "joseph__mud",
       "therealadam__", "1clawAI__", "xenotaur__", "tambetvali__", "humanlayer__", "AnatolyUA__"],
 "T": ["BioJulia__", "civiform__", "fablestudio__", "jdiaz5513__", "kalisjoshua__", "rasmushenningsson__", "mashhype__",
       "sfeir-open-source__", "untracked-tx__", "ieee-webmaster__", "mrktps__", "tkshill__", "justinhartman__", "gtcode-dot-com__",
       "HacktheHill__", "dojo4__", "nlr-ai__", "littlematch0123__", "alphagov__", "sandialabs__"],
}
NAME = {"A": "責任分担型(人間が決める・行う事項)", "G": "協働ガイド型(人間がAIとどう働くか・AI方針)", "M": "人間向け説明書型(運用・構成の解説)",
        "T": "クレジット型(humans.txt 系)", "N": "無関係(架空世界の種族・記事・その他)"}
def typ(f):
    for t, ps in PFX.items():
        if any(f.startswith(p) for p in ps): return t
    return "N"
# A 型の中身(ファイル単位で、そのカテゴリの記述があるか)。O = 資格情報・アカウント・物理/実機の操作(v1 外の新カテゴリ)
CONTENT = {
 "EdmundLimBoEn__ipad-webbooth": ["O", "R-gov", "R-tech"],   # 遠隔の変更は明示の許可なしに行わない / 本番バケットを流用しない
 "EdmundLimBoEn__s2-05-timetable": ["O", "D-risk"],          # テストが良ければ PR をマージ
 "EdmundLimBoEn__stage-wand": ["O", "D-dir", "D-risk"],      # 配布経路・ライセンスを決める / リリース受け入れ
 "EdmundLimBoEn__trakr": ["O"],                              # 漏れた API キーの制限・ローテーション
 "MarkStokes-outlook__product-finder": ["R-gov"],            # Primary Owner / Allowed Delegations / Sensitive Areas(空の雛形)
 "MarkStokes-outlook__uk-policy-simulator": ["R-gov"],
 "Stoked-Builds__daemon-core-public": ["R-gov"],
 "hehamalainen__Humans.md__examples__monorepo__HUMANS.md": ["R-gov", "D-risk"],            # リスク段階ごとに STOP for approval
 "hehamalainen__Humans.md__examples__monorepo__packages": ["R-gov", "D-risk"],             # fintech-lead / security-auditor の承認
 "thegoodcompany-sst__TAVAttendance": ["O", "R-gov", "D-dir", "D-risk"],  # DPO 任命・法務承認・DPA 署名・フラグを入れる判断
 "danja__jigdaw": ["O", "K-priv", "D-dir"],                  # 実際に耳で聴く・診断を確かめる・どれが悪い音か言う
 "tomtev__termlings": ["O", "R-gov", "D-dir", "D-risk"],     # 資格情報・権限付与・戦略判断・大きな変更の承認
 "aibozo__gok": ["O"],                                       # API キー等を用意する
 "TeamLith__lith": ["O", "R-gov", "D-risk"],                 # 署名・最終リリース承認・法務/ライセンス判断
 "Aurora-Viewer__Aurora-Viewer": ["O", "R-gov", "D-dir", "D-risk"],  # 役割分担表・製品上の選択・⚠️ 時の判断・実環境ログイン
 "thewebartisan7__riservo": ["R-gov", "D-dir", "D-risk"],    # INTENT は人間・計画承認とコミットの2ゲート
 "TimeLordRaps__verifier": ["R-gov", "D-risk"],              # 人間が結論してよい範囲・リスク判断は人間が別に記録
}
rows = []
for x in ex:
    t = typ(x["file"]); c = next((v for k, v in CONTENT.items() if x["file"].startswith(k)), []) if t == "A" else []
    rows.append(dict(file=x["file"], repo=x["repo"], chars=x["chars"], ai_hits=x["ai_hits"], type=t, content=";".join(c)))
with open(os.path.join(W, "humans_files_types.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
ct = collections.Counter(r["type"] for r in rows)
for t in "AGMTN": print(t, NAME[t], ct[t], "(ai_hits>0:", sum(1 for r in rows if r["type"] == t and r["ai_hits"] > 0), ")")
A = [r for r in rows if r["type"] == "A"]
assert all(r["content"] for r in A), [r["file"] for r in A if not r["content"]]
cc = collections.Counter(c for r in A for c in r["content"].split(";"))
print("A 型", len(A), "件(うち空の雛形 daemoncore 3件)。カテゴリを含むファイル数:", dict(cc.most_common()))
A2 = [r for r in A if not r["file"].startswith(("MarkStokes", "Stoked"))]
print("雛形3件を1件に数えた場合 n=", len(A2) + 1, dict(collections.Counter(c for r in A2 for c in r["content"].split(";")) + collections.Counter(["R-gov"])))
