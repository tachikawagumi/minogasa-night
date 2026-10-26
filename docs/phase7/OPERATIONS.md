# 第7次 発見・分類・公開

## 4方式
config/discovery.jsonを拡張し、全20ジャンルについてA:既知番組名、B:ジャンル・内容語、C:公式番組表入口、D:過去の取りこぼしの特徴を保持する。scripts/discovery.py --planは80項目を生成する。DのlearningHistoryとmissFeaturesは取りこぼし原因を反映した設定であり、モデルの再学習や自律的な権利判断を意味しない。
既存の20ジャンル、公開schemaVersion1、Android画面は変更しない。今回の調査は第6次の同一対象週の検索実績を再利用し、指定6番組に集中した。80項目の全検索が今回新たに実行されたという意味ではない。

## 候補台帳
AIは未確認候補を含めdata/ai-candidates.jsonのdiscoveriesへ記録する。公開用recordsと分離する。
scripts/ledger.pyが、API取得や公開判定に先立ちdata/discovered-candidates.jsonへupsertし、取得・公開失敗時も候補を保持する。
候補IDは繰り返し調査しても維持し、古い確認で新しい確認を上書きしない。48時間内の再調査目安はresearchDueで確認する。変更・中止の新しい証拠があるときは期限前でも確認する。
未確認の提示日時はclaimedStart/claimedEnd。公式確認前はstart/endへ移さない。番組本文・画像・出演者・秘密情報・未知項目は台帳に保存しない。

## 3段階分類
classification.level=clear（明確）、related（関連あり・追加確認）、excluded（対象外）。
related/excludedを公開候補へ投影しない。genreIdsは確認済み分類、candidateGenreIdsは調査観点でありアプリに配信しない。
タイトルにある単語だけで分類しない。幻魔大戦は映画とアニメ、SF・超能力のみを根拠にUFOへ追加しない。心霊ドラマは定義上対象になり得るが、作品や当該回の内容確認が必要。
公式作品紹介と今回の放送予定の照合は別の確認項目。

## 公開
eligibleかつclear、公式の番組名・局・日時・内容・出典が揃った台帳レコードだけを既存autopublish.pyへ渡す。ここでも出典ポリシー、7日間、重複・矛盾・大量消失等を再検証する。台帳の自己申告だけで全サイトを許諾済みにしない。
ほん怖は既存IDを維持しpublished扱い。再投影して二重登録しない。
何だコレは現在の次回予告の10/28(水)19時を、確認日の直近の将来の暦日2026/10/28と照合した。当該回の魔術・呪いによる治癒という超常的主張を扱う企画に基づきUFO・都市伝説に分類。終了20:54はユーザー提示値であって今回公式確認できなかったため公開値はnull。次回予告から別年や翌週の枠を生成することは禁止。
フジ公式ページの個別放送事実に限定した従来の運用判断を維持する。本文・番組表配列を転載せず、このURL・日時・番組だけに限定。サイト全体の取得・転載許諾を得たという意味ではない。
幻魔大戦はBS12自身の@Press発表で日時と分類を確認したが、@Pressの利用規約第11条(7)等の適用と公開利用条件に確認事項があるため保留。会員向け配信サービスの規約を公開記事の全事実へ当然に適用できるとも、当然に適用外とも断定しない。局サイトの503も回避取得しない。
NHK番組ページのrobots拒否を別ツールや回線で回避しない。VODの過去作品紹介から現在の再放送予定を生成しない。

## NHK BS
既存対応局定義にNHK BSが欠けていたため、nhk_bsを追加した。公開フィードのstationsは既存の配列形式のまま。
しょぼいカレンダーの局IDを推測して付けず、API収集対象とは分離する。coverageのanime=not_collected、animeCheckedAt=null。公式事実が確認できる別ソースの将来枠を扱える準備であり、NHKの番組データ取得成功を示さない。

## 品質集計
data/collection-quality.jsonを拡張。ジャンルごとにsearches/candidates/datetimeConfirmed/publicPrograms/held/excluded/omissionsを持つ。officialDatetimeConfirmedとclassificationLevel、公開状態、理由、出典、researchDueを候補ごとに追跡する。
confirmedOmissionsは日時まで公式確認済み・分類clear・未来枠で未公開のもの。未確認候補や対象外を確認済み取りこぼしとして水増ししない。
0件のzeroReasonCodeはsearch_insufficient、source_insufficient、decision_pending、no_broadcast_verifiedを区別する。最後は全対象局・当該7日間・確認日時・出典等の証跡が必要。今回、検索0件だけから放送予定なしを主張しない。
保留と公開は別軸であり、既存承認済みの同内容が公開中でも新規取得条件が未確認という場合がある。

## 定期実行・費用
既存の月曜・木曜09:00 JSTタスクとGitHub Actionsを維持する。AIタスクが候補ファイルをGitHub連携で更新するpushが接続点。GitHub ActionsにChatGPT Web検索があると仮定しない。
無人定期タスクでの検索・書込みが実測できるまでは、対話中の実行成功と分けて報告する。新規タスク、有料API、有料EPG、Cloudflareは導入しない。通常成功はログのみ、新しい取りこぼし・取得/公開失敗・矛盾・必要な対処がある場合だけ通知する。
