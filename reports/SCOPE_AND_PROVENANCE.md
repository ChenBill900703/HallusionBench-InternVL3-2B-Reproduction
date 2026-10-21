# 第一階段範圍與來源紀錄

2026-10-21（Asia/Taipei），依使用者最新指示，僅執行 **OpenGVLab/InternVL3-2B**，在單張 RTX 3070 Ti 8GB 上完成第一階段推論。沒有執行 Qwen 模型推論，沒有判分。

最初依原始需求調查了三個候選模型，並下載候選權重。使用者縮減範圍後，停止其他模型的實驗準備；先前下載的檔案保留在本專案的 `models/`，未混入實驗結果或交接壓縮檔。`reports/model_catalog.json` 是候選調查紀錄，不能解讀為已測試三個模型。

## 論文與資料版本

- 原始 CVPR 2024 PDF 已完整擷取閱讀，另視覺檢查第 4 頁的統計表、定義與公式。
- 官方 repository：<https://github.com/tianyi-lab/HallusionBench>。
- 取得時 HEAD：`744007c232c292942c7f80eb61edb2465482da31`。
- 官方 JSON 最後修改版本：`c226ce45c95eec2935b09789099409c682a6c05d`，2023-11-15。
- JSON SHA-256：`ca6e0fb677dd56e5fb0e2700d06c58d01f8a6ae66e0f1773b2ac48c0a095d051`。
- 實際 JSON 與論文數量一致：1,129 題、346 個影像檔、455 個問題控制分組；無影像 178 題、原圖 447 題、修改圖 504 題；165 張原圖、181 張修改圖。
- 官方 README 的下載表仍列早期 254 題／69 圖，不適合作為最新資料統計。
- 官方 Google Drive 圖片連結實測 HTTP 404，gdown 下載也失敗，原始錯誤保存在 logs/。
- 圖片改由 LMMs-Lab 公開研究鏡像還原：<https://huggingface.co/datasets/lmms-lab-encoder/HallusionBench>，固定版本 `cd417161857aefb23d878d42cf1bb53aa9dd646f`。
- 已核對鏡像的所有 1,129 筆原始欄位（filename 的目錄前綴差異除外），與官方 JSON 一致；同一 filename 的重複圖像位元也一致。圖片全部解碼驗證，逐檔保存 SHA-256。
- 因原始 Drive 壓縮檔不可取得，無法獨立證明鏡像圖片與原始壓縮檔逐位元相同；此限制不可省略。

## 保留的結構與差異

`sample_id` 是由官方五個欄位 `category/subcategory/set_id/figure_id/question_id` 組合而成的本地鍵，不是假稱官方另有 sample_id。`question_pair_id` 的組合完全遵循官方 utils.py：category、subcategory、set_id、question_id。

官方 JSON 的 `VD/ocr` 對應論文 Poster；原始標記保留，另以 `paper_subcategory` 註記。VS/ocr 仍是論文 OCR。

Video 類題目在官方資料中以單張 PNG 呈現連續影格拼圖；輸入原始 PNG，保留既有位置與順序，沒有自行抽影格、重排或製作影片。

採用現代 InternVL3-2B 權重，並非重現原論文 2023 年模型輸出。採模型官方 `.chat()` 與影像預處理，以 BF16、batch 1、最多 12 個動態圖塊加縮圖、greedy decoding、最多 128 個新 token 執行。Windows 未使用 FlashAttention；完整設定逐題保存。

最初的冒煙測試曾因 CSV 新增欄位而中斷匯出；逐題 JSONL 均保留。修正匯出欄位聯集後接續完成，原始錯誤留在 logs/。完整資料集推論使用修正後程式；程式 SHA-256 逐題紀錄。

完整推論前 204 題採預設 CUDA allocator。tensor allocated 峰值約 5.47 GiB，但 unused reserved cache 曾達 9.58 GiB；Windows WDDM 可能因此使用共用記憶體。為避免快取超出實體顯存，保留 204 筆 checkpoint 後中止程序，改為 `torch.cuda.set_per_process_memory_fraction(0.90)` 並在每題後 `empty_cache()`；從尚未寫入的第 205 題接續。新策略在每筆 `runtime_memory_policy` 與新 run metadata 中明確記錄。模型／精度／圖片處理／Prompt／生成設定完全未變。`reports/inference_runtime_before_memory_policy.py` 與 `reports/inference_runtime.py` 保留兩版來源，逐題 `inference_code_sha256` 區分實際執行版本。沒有重新執行已保存成功的 204 題，沒有設定模型 CPU offload。
