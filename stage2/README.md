# Stage 2：已保存的語意判分與可重算指標

這裡保留 InternVL3-2B 的 1,129 題判分、47 批初判、397 題歷史複核、v2 全量一致性稽核及 674 個回答配對。原始回答、官方 GT 與既有最終判分均未因發布而改動。

| 指標 | 正確數／分母 | 結果 |
|---|---:|---:|
| qAcc | 102／455 | 22.42% |
| fAcc | 100／346 | 28.90% |
| Easy | 251／455 | 55.16% |
| Hard | 193／430 | 44.88% |
| All | 617／1,129 | 54.65% |

All 包含 63 筆 VS 無圖不確定回答的官方接受特例。Easy／Hard 是控制組全對比例。v2 是舊標籤可見的同一對話模型稽核，沒有獨立人工驗證。

- [完整研究入口](../README.md)
- [本發布版研究 PDF](../reports/HallusionBench_Research_Report_zhTW.pdf)
- [Stage 2 詳細文字報告](reports/HallusionBench_Stage2_Report_zhTW.md)
- [評分品質及逐筆變更](reports/QUALITY_AUDIT_zhTW.md)
- [最終判分與原文](results/judgments.jsonl)
- [32 題參考疑義](judgments/unresolved_samples.jsonl)
- [87 筆說明問題](results/explanation_issues.jsonl)
- [方法差異](reports/METHOD_DIFFERENCES.md)

## 不需 GPU 或 API 的數值重現

在專案根目錄安裝 stage2/requirements.txt，再執行：

```powershell
python -X utf8 -m unittest discover -s stage2/scripts -p test_metrics.py -v
python -X utf8 scripts/verify_publication.py
python -X utf8 stage2/scripts/compute_metrics.py
```

這些指令從已保存的標籤重算，不重新 Judge。原有 finalize_judgments.py 等歷史程式仍保留供研究追溯；發布階段不需要執行。重畫八張圖可用 build_figures.py；重建本發布版 PDF 請用根目錄 scripts/build_public_report.py。

## 圖片與封存

原本地報告為 20 頁，包含十張第三方案例原圖。本發布庫保留其文字、案例 metadata、八張自製圖表及來源驗收；另附不含第三方原圖的新 PDF。需要圖片的 build_cases.py 或歷史 build_report.py，須自行依固定來源下載圖片後才能使用。

stage2/PACKAGE_MANIFEST.json 是原始封存的來源清單，包含本發布庫省略的案例圖片；本發布庫實際清單見 [publication_manifest.json](../reports/publication_manifest.json)。
