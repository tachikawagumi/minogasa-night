# 第15次：A+B候補統合・内部サブカテゴリー
Asia/Tokyo実行当日を含む7日間、東京/千葉の地上波・無料BS。docs/phase12/OPERATIONS.mdの開始記録/失敗保護とdocs/phase13/OPERATIONS.mdの定番追跡を継承する。

## 実行順
1. 実時刻と起動経路をrunsへ先に記録。予定09:00と実開始を混同しない。定刻無人成功は起動/実検索/書込/公開が揃うまで未検証。
2. config/discovery.jsonの20ジャンル・71内部カテゴリーでA検索。検索語は発見用で分類確定ではない。まず親ジャンルで幅広く探し、0件/少ない/期間後半空白の内部項目を追加追跡する。全71クエリを機械的な回数目標にしない。未検索項目と理由はログに残す。
3. config/regular-programs.jsonの元の50件を維持し、追加の車5件を含めた55件を追跡。指定6車番組を個別確認する。tvk/テレ玉を既存対象局へ読み替えない。
4. Bはconfig/collection.jsonの範囲で局・日付から補助的に実検索し、個別番組ページを通常参照。上限8は検索負荷の上限であり、8件で完了する規則ではない。全表の継続スクレイピングをしない。情報源条件を満たさなければ保留する。
5. A+Bを共通台帳recordで統合し、不足を追加検索。当該回の局/日時/内容/利用条件を個別照合する。既存の放送枠/シリーズIDを先に照合してから個別審査スナップショットを作成する。
6. 確認済みだけ既存ledger/autopublishへ渡し、GitHub/Actions/Pages/新IDを確認。正常な既存JSONを保護する。

## 入力形式と安全装置
ai-candidates.jsonのdiscoveryInputsに {route:"A" または "B",mode:"individual_reference",record:{既存ledger形式}} を追加/更新する。本文・出演者・画像は保存しない。discoveredAt/checkedAt、出典URL、分類根拠、個別factUseReviewを記録し、publicationApprovedを偽造しない。
従来のdiscoveries/recordsも引き続き利用可能。新入力はscripts/hybrid.py→ledger.prepare/project→既存source_rules/autopublishを通る。ここで規約審査・過去/対象期間・局ホワイトリスト・重複矛盾・大量消失防止を省略しない。
A+Bで同じID・同じ候補なら1枠に統合する。既存シリーズIDの変更や、同じ枠に別IDを勝手に割り当てる入力は保留。別局・別日時は別枠。同じ確認時刻で内容が矛盾する入力は更新全体を停止し、既存正常データを維持する。ジャンル配列を根拠なく自動和集合にしない。
車のeligible入力はclassification.vehicleEvidence={vehicleType,role:"central",basis} が必要。vehicleTypeはautomobile/motorcycle/truck/bus/special_vehicle/heavy_machinery/motorsport。当該回で紹介・運転・構造・整備・車両文化が主題と確認できること。単なる移動手段なら車を付けない。旅も該当する回はcar/travelの両根拠をgenreEvidenceへ記録する。
過去枠や不明な日時を未来へ動かさない。再放送は個別日時を確認した場合だけ。サブチャンネル142/152を通常局IDへ読み替えない。

## 許可範囲・ログ
既存有効2ポリシー・既存ホスト内のallowedUrls/individualFactReviewsを、実際に条件を確認できた個別URLの範囲で追加できる。enabled/mode/hosts/permissionsの変更、包括許諾の断定は禁止。新ホストや広域取得源はタスクが勝手に追加しない。
manual-approved.json/公開JSON/Android本体/処理コードは定期調査では変更しない。subcategoriesとcollection設定も変更しない。regularリストは同じIDの確認結果/日付/状態だけ更新可能。
data/hybrid-audit.jsonはActions生成。A/B入力数・重複・保留・経路を保存する。Workはruns/source-checksへA初発見/B初発見/以前の候補再確認/公開寄与を分け、実検索・対象内部項目・未調査範囲と理由を記録する。
アニメAPIはActions担当で重複照会しない。ActionsはAI検索を行わない。月木09:00を維持、次回11/2の定刻実行は未検証。通常成功はログのみ、取得/書込/検証/公開失敗・大量消失・重大矛盾・必要操作/起動欠落や遅延のみ通知する。有料API・新規契約・Cloudflare・他プロジェクト・日曜通知に触れない。
