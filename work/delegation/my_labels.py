"""My (main agent) upstream judgments. U1=(i) in request & repeated/elaborated in review, U2=(ii) explicit in request but agent/author did not follow & review points it out,
U3=(iii) not in request, first appears in review, U4=(iv) no request / linked issue unrelated / no substantive review point.
dec = request contains explicit design/policy/constraint/rationale beyond the bare task (Y/N; NA when no strict request).
conf = H/L. note = free text. rq = request quote for U1/U2."""
A = """G001 U2 NA H proxy本文が依頼文の体裁 | If some cannot, i.e. there is no model factory, the type does not have public ctor, or settable public properties, add a model factory method
G002 U3 Y H データの形を変えたいという依頼者自身の方針変更 |
G003 U3 Y H テスト/ベースライン更新 |
G004 U3 NA H |
G005 U4 NA H PR取得不可 |
G006 U3 NA H proxyにレビュー後の内容が混入 |
G007 U3 NA H どのopencodeかという文脈がレビューで初出 |
G008 U3 N H |
G009 U3 Y H |
G010 U1 NA L 依頼(タイトル)=consistent logging、レビューはqC*で統一 | Add consistent logging to CFAPI callbacks
G011 U3 Y H ロジックの置き場所(conf crate)が初出 |
G012 U3 N H |
G013 U4 Y H レビュー本文なし |
G014 U3 N H |
G015 U3 N H |
G016 U3 Y H |
G017 U3 Y H README/update.goの付随物 |
G018 U3 NA H |
G019 U4 N H 指摘内容が本文にない |
G020 U4 NA H PR取得不可 |
G021 U3 Y H |
G022 U3 NA H |
G023 U3 Y H 命名判断はIssueで決着済みでレビューは別件 |
G024 U3 N H |
G025 U1 Y L クラス名まで改名を拡張 | Rename `md` report to `markdown`
G026 U3 Y L |
G027 U3 Y H Issue作成者=レビュアーがcontribに留めると方針変更 |
G028 U3 NA H |
G029 U3 NA H |
G030 U3 Y H |
G031 U3 Y H |
G032 U2 Y L 複数指摘。VRCPhysBoneProviderBase活用は依頼文に明記、他(赤色、meta禁止等)は初出 | VRCPhysBoneProviderBaseを活用すること
G033 U3 Y H dev onlyでなくbuildも、は初出 |
G034 U3 NA H |
G035 U4 Y H 理由なしRevert |
G036 U3 NA L 依頼はSlack(proxy本文に記載)で不可視 |
G037 U4 NA H PR取得不可 |
G038 U4 N H 理由なし拒否 |
G039 U3 NA H proxyにcss-treeが混入(レビュー後の更新) |
G040 U1 N L 設定名をIssueの言い方(highlight markers)に合わせる | Option to remove Highlight Markers
G041 U3 N H |
G042 U3 Y H |
G043 U2 Y H 依頼文の要求をほぼそのまま繰り返し | Avoid hardcoding patterns such as function names, class names, field names ... each demo should become a tiny config plus a few calls
G044 U2 Y L Issueの出力例は揃っている | the resulting table should look something like the following
G045 U4 NA H レビュー取り下げ |
G046 U4 N H リンクIssueがPRの課題と不一致。レビュアーは「依頼された範囲を超えた」と不可視の依頼に言及 |
G047 U3 NA H |
G048 U3 NA H ドメイン知識。proxyにレビュー後の内容が混入 |
G049 U3 N H |
G050 U3 N H |
G051 U3 N H |
G052 U3 N H |
G053 U3 N H |
G054 U3 NA H |
G055 U3 N H ローカルブランチ削除は危険(初出) |
G056 U2 Y L 「Finish the work」=依頼範囲未完 | Update the codebase accordingly to what I want.
G057 U3 Y H |
G058 U3 NA H |
G059 U3 NA H |
G060 U3 Y L 簡潔に、が主。依存更新に絞る点はIssueコメントと一部重なる |
G061 U4 Y H 「Address comments.」のみ |
G062 U3 NA H |
G063 U3 Y H |
G064 U2 Y H 矢印キーで自然に動くことは依頼文に明記 | the element feels more natural to use when a user uses arrow keys for navigation
G065 U4 NA H PR取得不可 |
G066 U3 NA H |
G067 U3 Y L Issueコメントのヒントと関連するが具体策は初出 |
G068 U3 NA H |
G069 U3 N H |
G070 U3 N H 依頼(globalThis化)自体が成り立たない可能性をレビューで認識 |
G071 U3 Y H |
G072 U3 Y H |
G073 U3 NA H |
G074 U3 Y H |
G075 U3 Y H プラグインで実装すべき(Issueの提案方式を否定) |
G076 U4 Y H 本文「(see below)」のみ |
G077 U3 N H |
G078 U3 N H |
G079 U3 NA H 依頼の前提(CPUのみ)をレビューで疑問視 |
G080 U3 NA H |
G081 U3 N H |
G082 U3 NA H |
G083 U4 N H G046と同じPR・Issue不一致 |
G084 U1 Y L Issueが示した例に倣う形を具体化 | Replace the add-hoc code by high performance loggers ... Example: ...MsalDistributedTokenCacheAdapter.Logger.cs
G085 U3 NA H |
G086 U2 Y L Windows対応は依頼文に明記。複数ファイル対応は初出 | The changes must work for all platforms, including Windows.
G087 U3 N H フィーチャーフラグ・既存パラメータ拡張は初出 |
G088 U3 NA H |
G089 U3 NA H |
G090 U3 NA H proxyに混入 |
G091 U3 NA H |
G092 U3 NA H |
G093 U3 Y H |
G094 U3 NA L proxyに「maintainers noted」と混入 |
G095 U3 N H |
G096 U2 Y H 根本原因を直せという依頼の不遵守 | The purpose of this task is to find and fix the logic bug that causes the intended invariant
G097 U3 NA H |
G098 U2 Y H | The changes must work for all platforms, including Windows.
G099 U3 Y H |
G100 U4 NA H PR取得不可"""
H = """H004 U3 N H アーキテクチャ議論の承認が先 |
H007 U3 Y H standard schemaへ方針転換 |
H008 U3 Y H |
H015 U3 N H |
H016 U3 Y H |
H021 U4 NA H リンクIssue(#123)がPRと無関係(テンプレ由来とみられる) |
H026 U1 Y L 「元の報告の要点」に立ち返る。文言変更不要の判断は初出 | I'd prefer we move the 'arrow' to the position where the initializer is expected.
H027 U3 N H |
H028 U3 Y H IssueのTTL案そのものを否定 |
H029 U4 NA H リンクIssue不一致 |
H030 U4 NA H リンクIssue不一致(月次レポート) |
H032 U3 N H Issue本文が実質空 |
H039 U3 N H |
H050 U3 N H |
H055 U4 NA H リンクIssue不一致 |
H058 U3 N H |
H062 U3 Y H 既存翻訳を壊すという制約は初出 |
H068 U3 N H 方針はSlackスレッドにあり不可視 |
H070 U3 Y H |
H071 U2 Y H refactorのはずが新関数追加 | We need to refactor `sqrti` to be header-only, `constexpr` (if possible), shared math function.
H072 U4 NA H リンクIssue不一致(#123) |
H074 U3 N H |
H075 U3 N H |
H078 U3 N H |
H082 U3 N H |
H085 U1 Y H レビュアー自身がIssueで方針に疑問を出していた | Is there a reason you would not just reach for the actual Backstage Search feature
H086 U3 Y H |
H087 U4 NA H リンクIssue不一致(#1234) |
H088 U3 N H |
H089 U3 Y H |
H093 U3 Y H |
H095 U3 N H |
H097 U4 NA H リンクIssue不一致 |
H099 U3 Y H |
H100 U3 N H"""
def parse(s):
    out = {}
    for line in s.strip().splitlines():
        head, _, rq = line.partition("|")
        parts = head.split(None, 4)
        sid, lab, dec, conf = parts[:4]; note = parts[4].strip() if len(parts) > 4 else ""
        out[sid] = dict(me=lab, me_dec=dec, me_conf=conf, me_note=note, me_req_quote=rq.strip())
    return out
AGENT = parse(A); HUMAN = parse(H)
