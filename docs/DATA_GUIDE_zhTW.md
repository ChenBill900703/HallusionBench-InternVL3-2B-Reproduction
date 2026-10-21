# 從一個回答追到最後分數

## 先認識 Sample ID

例如 VS/map/6/2/0，表示 VS、Map 子類別、第 6 組、figure_id=2、第 0 問。完整 ID 是跨階段核對的鍵，不靠列號猜測。

問題控制組依 category、subcategory、set_id、question_id 組成。VD 的 figure_id=0 是原圖 baseline；VS 的 figure_id=0 是無圖 baseline。不能把所有 figure_id=0 都說成沒有圖片。

## 每一層保存什麼？

| 檔案 | 最重要的欄位 | 用途 |
|---|---|---|
| results/internvl3_2b_bf16_tiles12/full/responses.jsonl | sample_id、model_response_raw、generation_details、inference_parameters | 未改寫的原始回答與推論設定 |
| data/manifests/ground_truth.jsonl | sample_id、official_row | 官方題目與 GT |
| stage2/results/judgments.jsonl | semantic_correctness、predicted_stance、final_binary_correctness | 最終判分，連同完整原文 |
| stage2/results/pair_relations.jsonl | baseline_sample_id、sample_id、relation、reason | 回答間的事實是否衝突 |
| stage2/results/official_scored_rows.jsonl | judge_raw、same、correct | 送入官方函數的資料 |
| stage2/results/diagnostic_trace.jsonl | baseline_semantic、current_semantic、same_projected、diagnostic | 每題為什麼分到 LH／VI／Mixed |
| stage2/results/control_group_scores.jsonl | sample_ids、correct_items、all_correct | qAcc 逐組的成員與結果 |
| stage2/results/figure_group_scores.jsonl | sample_ids、all_correct | fAcc 逐圖結果 |
| stage2/metrics/overall.json | numerator、denominator、percent | 最終數字與公式 |

原始語意 0/1/2 和最終 correct=0/1 是不同欄位。只看 correct，會漏掉 VS 無圖例外接受的不確定回答。

## 實例：修改地鐵圖仍沿用原答案

查 VS/map/6/2/0。問題問依這張圖，能不能搭藍線前往 Pentagon。模型原文：

> Yes. The Blue Line is one of the lines shown on the map, and it runs towards the Pentagon.

文字參考否定這個答案，所以 semantic_correctness=0，這題又是有圖條件，final_binary_correctness=0。其無圖 baseline VS/map/6/0/0 本來答對，修改題仍維持相同路線主張，relation=same，官方流程因此把修改題分到 LH。

這表示輸出沒有依修改路線更新，支持語言先驗影響的假說；它仍不能單獨證明模型內部只靠記憶。

## 六組案例

完整回答、標籤及圖像 metadata 見 [case_studies.json](../stage2/reports/case_studies.json)。下列英文都是保存的真實模型輸出節錄；省略不代表原文不存在。

| 案例 | 真實 Sample ID | 回答／判定與意義 |
|---|---|---|
| A：地鐵修改 | VS/map/6/0/0、6/1/0、6/2/0 | 三條件都說藍線可到；修改題錯且 same，官方歸 LH |
| B：Red Bull／Red Deer | VD/ocr/13/0/0、13/1/0 | 修改回答寫「The logo ... is for Red Bull, as indicated by the text Red Deer」；讀到新字卻映射錯，語意 0，完整文字與 baseline 不同，歸 VI |
| C：橙色圓 | VD/illusion/0/0/0、0/1/0 | 原答 No 且說右圓較小，修改答 No 卻說較大；不能只因都 No 判 same |
| D：反轉穿衣順序 | VD/video/5/0/0、5/1/0 | 兩者都說 baby attempting to put on the clothes；修改題錯且 same，官方程式歸 Mixed，Figure 3 替代分支則為 LH |
| E：利率圖 | VS/chart/7/0/0、7/1/0、7/2/0 | 原圖先 No，正文卻說 US rates were higher，保留 ambiguous/2；修改圖文字結論對但數值比較有錯，另標說明問題 |
| F：No 實際棄答 | VS/chart/0/0/0 | 原文 No, the information provided is insufficient...；是 uncertain/2，依 VS 無圖例外被接受 |

表內縮寫後續 ID 只為節省版面，完整 ID 皆保存在 JSON 中。圖片來源版本為 lmms-lab-encoder/HallusionBench 的 cd417161857aefb23d878d42cf1bb53aa9dd646f；各圖路徑、尺寸及 SHA-256 在 data/manifests/images.jsonl。發布版不含第三方像素，下載後再核對。

## 查一題的簡單方式

```python
import json
from pathlib import Path

sample_id = "VS/map/6/2/0"
path = Path("stage2/results/judgments.jsonl")
for line in path.read_text(encoding="utf-8").splitlines():
    row = json.loads(line)
    if row["sample_id"] == sample_id:
        print(row["question"])
        print(row["model_response_raw"])
        print(row["semantic_correctness"], row["final_binary_correctness"])
        print(row["short_explanation"])
```

## 歷史紀錄怎麼看？

judgments/batches 是初判，不可把它當成新版最終值；second_pass 是 397 題歷史複核；adjudication_decisions 是當時仲裁；consistency_v2 保存規範、全量重審、舊版快照及改動。正式數字統一以 results/judgments.jsonl 為準。

32 題 reference_dispute 表示參考或定義仍有疑義，不表示漏判。87 筆 explanation_issue_flag 是另記的文內說明問題，不可直接當成全部幻覺或錯誤解釋的總數。
