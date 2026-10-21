# 評估定義與版本差異紀錄（持續補充）

主要實作依 ZIP 中 utils.py 與 evaluation.py 的固定副本，使用 AST 僅載入純計算函數，不匯入或呼叫付費 API。原始檔不修改。

1. Easy/Hard：evaluation.py 先按 visual_input !=2 / ==2 篩選，接著 get_eval_pair_easy/hard 以 category/subcategory/set_id/question_id 分組，組內全對才算對。雖表頭寫 easy aAcc/hard aAcc，並非直接逐題平均；另報逐題條件準確率以免混淆。
2. fAcc 是 get_eval_fig 的 correct/total；該函數的 score 是平均各圖內逐題比例，不是 fAcc。VS figure_id=0 被排除圖像分母。
3. assign_correctness 對 VS figure_id=0 接受所有原始語意標籤2；程式未區分誠實不知道與自相矛盾。兩者分開保存並報告此例外帶來的接受數。
4. yes_ratio_stats 以 int(correct == gt_answer) 反推 Yes/No，不直接讀取模型語意立場。未知、GT文字與二元不一致、開放式問題、極性對但重要解釋錯誤等都可能破壞此假設；官方代理結果與直接語意統計分列。
5. check_same_by_chatgpt 的二元parser：含same為1，含different為0，其他預設0。本次依使用者要求保存same/different/uncertain三值。若要送入未修改的官方計算，uncertain依原parser預設投影成0，並另外計算全部投影為1的敏感度；不將投影冒稱已解決的語意判定。
6. Figure 3 的 VD baseline正確、修改回答錯誤且回答相同路徑指向LH；utils.py 在同條件設analysis=(1,1)，即Mixed。主要表沿用官方程式，另報圖示路徑替代版本，不能默默互換。
7. evaluation.py 的Table 3診斷採用LH_cg/VI_cg/Mix_cg，即逐個VQ項目的分析計數；get_eval_pair_all另外回傳455組彙整後的LH/VI/Mix。兩套分母分開，不把所有診斷都除以455。
8. 來源包含which country/state/month等非二元問句，與README「全部Yes/No」的宣稱不完全一致。語意正確性依實體答案判定，直接Yes/No Bias另排除此類題，並保留數量與ID。
9. gt_answer_details若本身是No answer或明確要求無可回答，模型正確指出資訊不可用可判語意1，即使stance=uncertain；一般有圖卻不知道仍是語意2。此判準有別於單純把uncertain字串全部映成2。
10. 原論文GPT-4 judge重複三次取平均；本次先在現有gpt-6.1-sol對話內逐批判分、397題隱藏首標籤重讀，再完成全部1129題與674配對的v2一致性稽核。v2舊標籤可見，不是盲評，不呼叫API，不宣稱等價於原GPT-4、獨立人工驗證或三次全量judge。溫度等服務端抽樣參數未由本任務控制。
11. v2主語意採官方gt_answer_details，與原作者teacher prompt一致；原始二元gt_answer保留供官方函數及Bias計算。純參考衝突不當成模型不確定2；用reference_dispute獨立標記及上下界。文字參考本身肯否衝突時，具體實體／數量／位置敘述優先，疑義不消除。
12. 主分數衡量相對文字參考的不衝突性，未驗證的贅述不一概扣分；文內可判定的算術、邏輯與說明問題另存explanation_issue_flag。87筆旗標中20筆仍獲主分接受；這不是所有說明事實都正確或錯誤的全面標註率。
13. 固定RUBRIC_v2.md後完整閱讀47批，修正13題語意、3題立場（包含在該13題內）、7題final correctness及2組配對。舊版完整快照、逐筆差異、規範／輸入雜湊與跨批裁決保留；所有GT與模型輸出不變。完全相同的題目、文字參考及輸出，最終標籤一致。

全量初判1129題、歷史複核397題及v2全量1129題／674配對稽核均完成。正式分母與新版結果見metrics/overall.json，品質見reports/judge_quality.json、consistency_audit_v2.json。保留32題參考或定義疑義，All極端範圍604-636/1129=53.50%-56.33%；這是指定疑義集合的敏感度，不是全體標註準確率或信賴區間。沒有未處理批次，也沒有獨立人類驗證。
