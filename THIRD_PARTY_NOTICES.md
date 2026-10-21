# 第三方來源與發布界線

本專案整合多種來源，不能用一個授權名稱概括全部。研究結果保留，但第三方圖片的公開再散布權限仍未明確，因此先以 **Private Repository** 發布。改為公開前，仍需確認相關資料條款。

## HallusionBench：題目、官方函數及論文

- 官方來源：[tianyi-lab/HallusionBench](https://github.com/tianyi-lab/HallusionBench)。
- 參考程式版本：744007c232c292942c7f80eb61edb2465482da31。
- 題目 JSON 版本：c226ce45c95eec2935b09789099409c682a6c05d。
- 題目 JSON SHA-256：ca6e0fb677dd56e5fb0e2700d06c58d01f8a6ae66e0f1773b2ac48c0a095d051。
- 官方程式採 BSD-3-Clause，Copyright 2023 Fuxiao；完整條款保留於 [原始授權](handoff/upstream_reference/LICENSE.md)。本次透過 AST 載入七個純計算函數，不執行頂層 API 呼叫。
- [CVPR 2024 論文](https://openaccess.thecvf.com/content/CVPR2024/html/Guan_HallusionBench_An_Advanced_Diagnostic_Suite_for_Entangled_Language_Hallucination_and_CVPR_2024_paper.html)僅提供來源連結；原論文 PDF 未放入本發布庫。

## 圖片：只發布來源與核對資訊

程式的 BSD 授權不能直接證明每張來源圖片都可重新散布。固定研究鏡像的資料卡也不足以釐清所有圖片權利。因此本庫排除 data/VD/、data/VS/、案例原圖，以及含這些原圖的本地 20 頁 PDF。八張自行產生的統計圖及不含第三方原圖的新 PDF 已保留。

- 固定鏡像：lmms-lab-encoder/HallusionBench，revision cd417161857aefb23d878d42cf1bb53aa9dd646f。
- 取得方式：[下載程式](scripts/download_assets.py)。
- 圖片路徑、來源與 SHA-256：[images.jsonl](data/manifests/images.jsonl)。
- 六組案例的 ID、回答及來源 metadata：[案例說明](docs/DATA_GUIDE_zhTW.md#六組案例)。

原始 ZIP 沒有直接上傳，因為包含第三方圖片或含圖報告。所有可發布的研究紀錄已展開整合；來源 ZIP 的雜湊及逐檔檢查保留於 [來源驗收](reports/stage3/source_audit.json)。

## InternVL3-2B

模型來源：[OpenGVLab/InternVL3-2B](https://huggingface.co/OpenGVLab/InternVL3-2B/tree/899155015275a9b7338c7f4677e19c784e0e5a21)。

本次固定 revision 為 899155015275a9b7338c7f4677e19c784e0e5a21。模型卡 YAML 標為 Apache-2.0，正文另說 InternVL 程式採 MIT，Qwen 元件採 Apache-2.0；不可據此把所有元件簡化成同一授權。保留的官方模型執行程式帶 MIT 標頭及原授權，位於 [model_runtime_source](reports/model_runtime_source)。權重沒有上傳，下載及使用者仍需自行閱讀固定版本條款。

## 本次生成內容與歷史紀錄

原始模型輸出、GPT-6.1 Judge 判定、複核與仲裁紀錄屬本次研究資料，不代表外部事實資料庫，也不因專案新程式採 MIT 就使所有上游文字一併成為 MIT。官方 GT、模型原文與最終標籤未改寫。

部分 Stage 1／Stage 2 歷史文件描述當時本地封存狀態，例如「20 頁」或「十張案例原圖」。它們是來源憑證；本發布版的實際檔案請看 [發布清單](reports/publication_manifest.json)，閱讀入口則以根目錄 README 為準。

唯一隱私清理為 logs/smoke_internvl.log 中四處本機 Windows 使用者目錄名稱，替換為 USER；GPU、錯誤與推論數值均保留。所有排除與清理均有逐檔來源雜湊，未改動原始封存。
