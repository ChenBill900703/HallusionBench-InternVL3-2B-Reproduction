"""Keep delivery notes aligned with the saved final labels and metrics."""
import json
from compute_metrics import S2,read
def load(p):return json.loads((S2/p).read_text(encoding='utf-8'))
def main():
    o=load('metrics/overall.json');q=load('reports/judge_quality.json');a=q['full_consistency_audit_v2'];s=load('metrics/sensitivity.json');t=o['table2'];old=load('judgments/consistency_v2/prior_final/overall.json')
    bounds=s['reference_dispute_accuracy_bounds'];changes=read(S2/'judgments/consistency_v2/changes.jsonl');pc=read(S2/'judgments/consistency_v2/pair_changes.jsonl')
    table='\n'.join(f"| {k} | {v['numerator']}/{v['denominator']} | {v['percent']:.2f}% |" for k,v in t.items())
    commands='''.venv/Scripts/python.exe -X utf8 stage2/scripts/finalize_judgments.py
.venv/Scripts/python.exe -X utf8 -m unittest discover -s stage2/scripts -p test_metrics.py -v
.venv/Scripts/python.exe -X utf8 stage2/scripts/compute_metrics.py
.venv/Scripts/python.exe -X utf8 stage2/scripts/build_figures.py
.venv/Scripts/python.exe -X utf8 stage2/scripts/build_report.py
.venv/Scripts/python.exe -X utf8 stage2/scripts/write_delivery_notes.py
.venv/Scripts/python.exe -X utf8 stage2/scripts/verify_final.py
.venv/Scripts/python.exe -X utf8 stage2/scripts/package_stage2.py'''
    text=f'''# HallusionBench Stage 2：v2 全量一致性重審完成

唯一實測視覺模型為 **OpenGVLab/InternVL3-2B**，沿用 RTX 3070 Ti 8GB 上完成的 1,129 筆真實回答。沒有新增模型、重新推論或呼叫付費 Judge API，沒有推送 GitHub。

- [教授版繁體中文報告 PDF](reports/HallusionBench_Stage2_Report_zhTW.pdf)
- [報告 Markdown](reports/HallusionBench_Stage2_Report_zhTW.md)
- [本次評分改善及逐筆變更](reports/QUALITY_AUDIT_zhTW.md)
- [完整判分與原文](results/judgments.jsonl)
- [參考疑義](judgments/unresolved_samples.jsonl)
- [推導與說明問題](results/explanation_issues.jsonl)

| 指標 | 正確數／分母 | 結果 |
|---|---|---|
{table}

## 本次品質改善

47 批 **1,129 題完整原文**及 **674 個非 baseline 配對**已全部由本對話 Judge 重審。先固定 v2 規範與雜湊，保留逐題 affirmed/revised、理由及來源雜湊；程式未以字串規則代替語意判分。

相對舊版，修正 **{a['item_label_changes']} 題語意標籤、{a['stance_changes']} 題立場及 {a['relation_changes']} 組配對**；其中 {a['final_correctness_changes']} 題影響最終 correctness。All 由 {old['table2']['All']['percent']:.2f}% 變為 {t['All']['percent']:.2f}%。另記 {a['explanation_issue_flags']} 筆文內算術、邏輯或說明問題，其中 {a['reference_accepted_with_explanation_issue']} 筆仍依文字參考規則接受；主分數不代表完整解釋都正確。

參考疑義由 17 題擴充至 **{a['reference_disputes']} 題**。二元 GT 與全部文字參考均未改動，沒有刪除分母。對此集合的極端 All 範圍為 {bounds['all_disputes_wrong']['All']['percent']:.2f}%-{bounds['all_disputes_correct']['All']['percent']:.2f}%；這不是全部標註錯誤的信賴區間。

## 判分定義與可信度

主語意分數以官方 **gt_answer_details** 為優先，對齊原作者 teacher prompt；二元 gt_answer 原樣保留用於官方計算。回答本身不知道／矛盾才使用 2，不再單因參考欄位衝突把明確立場變成不確定。明確參考數量、實體及方向衝突算 0；參考未涵蓋的推導錯誤另記。

本次是**同一對話模型、舊標籤可見的全量一致性稽核**。不是獨立人類標註、獨立盲評或三輪全量平均。歷史 397 題的 97.48% 語意重讀一致率只描述重複性，不是判分準確率。獨立人類驗證尚無，沒有把它虛構成已完成；所有本次可完成的判分、重算、報告與封存均已完成。

## 重現

從專案根目錄執行下列步驟。計算不需 GPU、模型權重或 API 金鑰；Python 3.12 的套件見 stage2/requirements.txt。報告／圖表字型使用 Windows 微軟正黑體；純數值重算不依賴字型。

```powershell
{commands}
```

finalize_judgments.py 先重建歷史初判／複核／仲裁，再套用完整 v2 稽核與跨批裁決；缺少任一批會停止，避免半成品覆寫。相同題目、文字參考與模型回答必須得到同標籤，驗收亦核對 11 個預先寫入期望標籤的邊界案例（期望由同一對話 Judge 撰寫，不是獨立人工標註）。

build_cases.py 需要原專案圖片；封存已附六組案例及十張核對過的來源圖，純重算不必再執行。audit_stage1.py 供在完整原專案重新驗證 Stage 1；解壓封存後可直接以 inputs/ 重現數值。完整輸出、GT 與原作者函數位元均保留，官方碼透過 AST 只載入七個純計算函數，避開頂層 API 匯入。

## 追溯與範圍

- judgments/consistency_v2/RUBRIC_v2.md：重審前固定規範。
- judgments/consistency_v2/batch_*.jsonl、pairs_*.jsonl：47 批逐題／逐對稽核。
- judgments/consistency_v2/prior_final/：v1 完整判分、配對、品質、主要指標與舊規範快照。
- judgments/consistency_v2/changes.jsonl、pair_changes.jsonl：舊新版變更及理由。
- judgments/consistency_v2/global_adjudication.json：閱讀全量後，將相同錯誤品牌映射套用同一規則的跨批裁決。
- metrics/：Table 2/3、類別／條件／子類別、原始與直接 Bias、診斷與敏感度；含分子分母。
- figures/：八張更新圖表與十張案例原圖。
- reports/：20 頁教授版報告、品質與來源驗收、封存及解壓重現檢查。

其他模型均為已發表文獻數字。346 張圖片由固定研究鏡像取得，metadata 與官方逐筆一致且本地雜湊核對；無法證明與失效原始圖包位元完全相同。保留 VS 無圖例外、Easy/Hard 分組、Bias 代理、same 不確定投影，以及 Figure 3／官方程式診斷分支差異。細節見 [METHOD_DIFFERENCES.md](reports/METHOD_DIFFERENCES.md)。
'''
    (S2/'README.md').write_text(text,encoding='utf-8')
    audit_text=f'''# v2 評分改善與驗收

本次完成全量 1129 題、674 配對重審，修正 {a['item_label_changes']} 題標籤和 {a['relation_changes']} 組關係；新分數是固定規範套用結果，不是挑選較高分。輸出與 GT 未變動；資料工程驗收、語意稽核與外部有效性分開記錄。

## 已完成的處理

1. 先固定 RUBRIC_v2.md，SHA-256：{a['rubric_sha256']}。
2. 逐題閱讀完整原文，47 批 checkpoint 全數保留；題目／文字參考／回答完全相同的輸入，最終標籤一致。
3. 參考衝突單獨標記，不混成模型不確定；已知疑義 {a['reference_disputes']} 題，全部保留官方分母。
4. 說明問題另存 {a['explanation_issue_flags']} 筆，其中 {a['reference_accepted_with_explanation_issue']} 筆主分接受。這不是全面外部事實查核，也不是額外準確率。
5. 所有主表、分類、八張圖表、案例標籤與 PDF／Markdown 由新版資料重建。

## 具體邊界

- BOC=145：參考只給最終角度。正文答案符合參考，但把半角和算錯，主語意仍 1，另標 explanation_error。兩筆文字參考同為 145、二元 GT 卻為 0 的重複題，改為 1 並保留參考疑義。
- 是否有鴨：正文將多隻小雞都稱幼鴨，與文字參考的 one duck 明確數量衝突，主語意 0。這與未被參考涵蓋的錯誤推導使用不同、已明定的處理。
- No 與正文：若 No 明確否定 r³，而正文肯定題目 r²，可判 yes；若同一相加 180 命題的肯否並存，保留 ambiguous/2。不根據 GT 替模型補意思。
- Maryland→Texas：與 Red Deer→Red Bull 一樣，明確承諾錯品牌，判 yes/0；讀出的文字也與 baseline 不同，所以配對 different。
- 同說 No：一個說兩線同長、另一個說頂線較短，配對應 different。

## 舊新版逐題差異

| Sample ID | v1 stance/semantic/final | v2 stance/semantic/final | 理由 |
|---|---|---|---|
'''
    for r in changes:
        def val(x):return '/'.join(str(x[k]) for k in ['predicted_stance','semantic_correctness','final_binary_correctness'])
        audit_text+=f"| {r['sample_id']} | {val(r['before'])} | {val(r['after'])} | {r['reason']} |\n"
    audit_text+='\n## 配對差異\n\n'+ '\n'.join(f"- {r['sample_id']}：{r['before']} → {r['after']}。{r['reason']}" for r in pc)
    audit_text+='\n\n## 驗證的界線\n\n本次由同一對話模型執行，舊標籤可見，沒有獨立人類／另一個 Judge，沒有宣稱已達黃金標註品質。97.48% 是歷史重讀一致率，不能當成準確率。32 題疑義上下界只對這個集合成立，不涵蓋所有可能標註錯誤；本次已完成可在此環境進行的全量稽核與技術驗收。\n'
    (S2/'reports/QUALITY_AUDIT_zhTW.md').write_text(audit_text,encoding='utf-8')
    print('Updated README and complete quality/change notes')
if __name__=='__main__':main()
