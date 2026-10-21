"""One structured source -> Traditional Chinese Markdown and printable PDF."""
import json,csv,html,re,hashlib
from pathlib import Path
from compute_metrics import ROOT,S2,read,dump
def load(p):return json.loads((S2/p).read_text(encoding='utf-8'))
def csvread(p):
    with (S2/p).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def pct(v):return f"{v['percent']:.2f}%"
def frac(v):return f"{v['numerator']}/{v['denominator']} = {pct(v)}"
def blocks():
    o=load('metrics/overall.json');q=load('reports/judge_quality.json');se=load('metrics/sensitivity.json');je=load('metrics/judge_effects.json');comp=load('metrics/comparison_tables.json');cases=load('reports/case_studies.json')
    b=[]
    def h(t):b.append({'type':'heading','text':t})
    def p(t):b.append({'type':'paragraph','text':t})
    def table(title,head,rows,widths=None):b.append({'type':'table','title':title,'headers':head,'rows':rows,'widths':widths})
    def fig(name,caption):b.append({'type':'image','path':'figures/'+name+'.png','caption':caption,'max_height':270})
    def page():pass  # Continuous main text avoids artificial near-empty pages.
    p('資料版本：2026-10-21。唯一實測視覺模型：OpenGVLab/InternVL3-2B。完整初判 1,129 題；複核 397 題；未完成判分 0 題；保留參考或定義爭議 17 題。沒有重跑視覺模型，沒有呼叫付費 Judge API。')
    p('主要結果：qAcc 101/455 = 22.20%；fAcc 99/346 = 28.61%；Easy 250/455 = 54.95%；Hard 191/430 = 44.42%；All 616/1129 = 54.56%。分數包含作者的 VS 無圖特例，不能解讀為每題都具有可靠視覺理解。')
    h('一、論文摘要')
    p('HallusionBench 將視覺模型「看錯」與「依語言常識回答」交織的失誤放入控制實驗。資料包含 1,129 個視覺問答項目、455 個 Question Control Groups 與 346 張實體影像。Visual Dependent（VD）必須依賴影像；Visual Supplement（VS）可用無圖條件測試原有知識，再用原圖與修改圖檢驗視覺證據是否改變回答。')
    p('本報告依論文第 4、5 節、Table 2、Table 3 及 Figure 3、4、5，復用官方計算函數。重點是整組及整張圖是否都答對，而非只報一個逐題平均。Language Hallucination（LH）、Visual Illusion（VI）與 Mixed 是依控制條件得到的操作性分類，不是對模型內部機制的直接觀測。')
    h('二、研究目的')
    p('在單張 RTX 3070 Ti 8GB 的既定硬體內，評估一個可實際完成的本地視覺語言模型。使用者已將範圍明確縮為單模型，因此不重現原論文全部 15 種模型，也沒有將只下載的 Qwen 候選權重算作實驗。比較的其餘模型均是論文已發表結果。')
    p('本階段回答三個問題：單題答對能否代表跨條件與同圖一致；修改圖是否造成額外失誤；哪些失誤可由官方控制流程分類。研究結論限於此資料集、此推論設定與此 Judge，不外推為所有任務或模型年代的公平排名。')
    h('三、研究方法')
    p('先重新驗證 Stage 1 ZIP 的 CRC、PACKAGE_MANIFEST 127 筆檔案大小與 SHA-256，以及 summary、index、GT、control groups、正式 responses、integrity report。實際核對 1,129 個唯一 Sample ID、455 組、346 圖、47 批、40 筆達上限；排除 smoke test、失敗嘗試與其他模型。另逐張核對本地 346 張影像雜湊。原始回答不覆寫。')
    p('每題先產生原始語意標籤 s∈{0,1,2}，依序表示錯誤、正確、不確定；再以未修改的 assign_correctness 產生 c∈{0,1}：VS 且 figure_id=0 時，s=1 或 2 均令 c=1；其餘情況僅 s=1 令 c=1。這是依官方程式實作的 Eq. (2) 特例。原始語意與最終 correctness 分欄保留。')
    p('qAcc = Σg[組內所有 c=1]/控制組數。fAcc = Σf[該圖所有 c=1]/實體圖數，排除 VS 無圖。Easy 先取 visual_input≠2、Hard 先取 visual_input=2，再各自按控制組全對計算。All = Σi c_i / 1129。官方函數 get_eval_fig 的 score=各圖題內正確比例平均，不能拿來當 fAcc。')
    p('官方程式以 AST 僅載入七個純計算函數，沒有 import 原檔中的 OpenAI 或執行網路請求。以不同條件、非等量修改圖、部分正確圖、未知例外與診斷分支的 8 項單元測試驗證，另用獨立分組計數核對實際資料分母。')
    h('四、原論文實驗與成果')
    p('原文 Table 2 的 GPT-4V 人工評分 All 為 67.58%，GPT4-Assisted 為 65.28%；LLaVA-1.5 為 46.94%，Qwen-VL 為 39.15%，BLIP2 為 40.48%（後三者均 GPT4-Assisted）。原文 Fig. 4 分析九種子類別，Fig. 5 以數學、錯覺與反序影格說明模型可能忽略修改資訊。這些敘述是文獻結果，非本次重新推論。')
    p('原文模型涵蓋閉源與不同大小的開源系統，不能期待所有系統在 8GB 本機重跑。原文 GPT-4 輔助判分多次平均，本次為現有 GPT-6.1 對話判分；Table 2、3 的歷史數字已逐格對照 PDF 第 7 頁（印刷頁 14381），沒有由百分比逆推出不存在的整數分子。完整比較表見第七、八節。')
    page();h('五、本次復現環境及模型')
    table('本地實驗條件',['項目','實際設定'],[
        ['視覺模型','OpenGVLab/InternVL3-2B；唯一完整推論模型'],['硬體','NVIDIA RTX 3070 Ti 8GB；i7-11700K；約 32GB RAM；Windows 11'],
        ['推論環境','Python 3.12.14；PyTorch 2.7.1+cu128；Transformers 4.57.1'],['模型版本','899155015275a9b7338c7f4677e19c784e0e5a21'],
        ['精度及解碼','BF16，無量化／無 CPU offload；batch=1；greedy；seed=42；max_new_tokens=128'],['影像輸入','448 動態切塊，上限 12，加 thumbnail；eager attention；未用 FlashAttention'],
        ['推論成本','回答生成時間加總 50.64 分鐘；不含安裝、下載、載入及中斷間隔'],['輸出上限','40/1129 = 3.54%；完整原文與上限旗標保留']],[90,402])
    p('2B 級模型在此硬體確實完成全量推論，因此適合作為低顯存復現的可行基線。這不證明它是 8GB 條件的最佳模型。沒有同機比較其他候選，也沒有進行微調或為本測試調參。')
    p('Tensor allocated 峰值 5.471 GiB；前 204 題預設配置器的 reserved cache 曾記錄 9.576 GiB，故不能聲稱所有記憶體指標從未超過 8GB。第 205 題起限制每程序比例 90% 並逐題清快取；NVIDIA 每 20 秒取樣之實體顯存最高 7,987 MiB，取樣不保證捕捉所有瞬間峰值。此策略變更與程式版本均有逐題紀錄。')
    h('六、本次 GPT-6.1 Judge 方法')
    p('Judge 身分由本對話 turn_context 確認為 gpt-6.1-sol，非依使用者稱呼猜測。每批讀完整題目、二元 gt_answer、gt_answer_details 與全部 model_response_raw，逐筆以語意標注。程式只顯示、驗證及保存人工撰寫的判定，沒有以第一個 Yes/No、關鍵字規則或另一個視覺模型代判。')
    p('predicted_stance 為 yes／no／uncertain／ambiguous。No 後表示資訊不足時是 uncertain；明確相反文字並存則 ambiguous。數字推理錯誤但語言結論清楚時，依其核心承諾及參考判 0/1。開放式國名、州名、月份題共 18 題，Yes/No 不適用，stance 用 ambiguous 表示不適用；另有 question_type 區分，不能與真正矛盾混算。')
    p('參考明確是 No answer 或允許不知道時，正確指出不可判定可為語意 1；一般有圖卻不知道為 2。極性正確但關鍵解釋牴觸參考仍可為 0。未對參考未涵蓋的所有贅述作外部事實查核，因此語意 1 不保證每一個補充數字或歷史敘述都正確。達上限不自動算錯，依截斷前是否已形成完整意思判斷。')
    table('兩輪品質檢查（比對仲裁前標籤）',['檢查範圍','題數','stance+語意一致','語意 0/1/2 一致'],[
        ['全部複核','397','374/397 = 94.21%','387/397 = 97.48%'],['預先隨機抽樣','113','110/113 = 97.35%','113/113 = 100.00%']],[130,60,148,154])
    p('113 題以 seed=20261021 在初判前固定抽出，約占 10.01%。複核聯集另含所有初判未知／矛盾、全部 40 筆達上限及已標記問題；每次顯示隱藏首輪標籤。兩輪共 23 筆 stance 或語意分歧，其中 10 筆語意分歧；仲裁後另有 2 筆因參考回答對象錯置而改為 2。共保存 25 筆仲裁紀錄。')
    p('這是同一模型在同一對話的重讀，仍可能受先前記憶及規範調整影響，不是獨立人工驗證；抽樣 100% 語意一致也不代表零判分錯誤。沒有做全量三次判分，不宣稱達到原文三次平均的穩定性。最終語意為正確 551、錯誤 406、不確定 172；語言立場為 yes 507、no 434、uncertain 104、ambiguous 84（含 18 題開放式）。')
    p('僅接受語意 1 的逐題比例為 551/1129 = 48.80%。官方 VS 無圖特例額外接受 65 題語意 2，使 All 增至 54.56%。其中 stance uncertain 47、ambiguous 16、明確 yes/no 但 GT 矛盾各 1；這說明程式接受所有 2，範圍比「誠實不知道」的文字描述更廣。')
    page();h('七、主要實驗成果')
    table('本次 Table 2：分子與分母',['指標','正確數／分母','百分比','單位'],[[k,f"{v['numerator']}/{v['denominator']}",f"{v['percent']:.2f}%",'單題' if k=='All' else '實體圖' if k=='fAcc' else '控制組'] for k,v in o['table2'].items()],[70,140,90,192])
    p('Easy 分母為 455 組，包含 625 個非修改條件項目；Hard 分母為 430 組，包含 504 個修改條件項目。部分控制組沒有修改圖，故 Hard 不等於 455；一組多張修改圖時須全部正確。這兩個百分比不能以 625 與 504 直接加權還原 All。')
    fig('01_main_accuracy','圖 1。All 遠高於 qAcc，表示不少控制組只在部分條件答對。')
    table('對應原文 Table 2 的比較（%）',['Model','qAcc','fAcc','Easy','Hard','All','Evaluation','來源'],[[r['model'],*[f"{r[k]:.2f}" for k in ['qAcc','fAcc','Easy','Hard','All']],r['evaluation'],'Our Measured Result' if r['result_type'].startswith('Our') else 'Published Result'] for r in comp],[99,36,36,36,36,36,99,114])
    p('InternVL3-2B 的 All 54.56% 高於表中 LLaVA、Qwen-VL、BLIP2 的歷史發表值，但低於 GPT-4V 與 Claude 3。這只是不同年代、推論設定、資料來源及 Judge 下的並列觀察，不是受控優劣結論；小模型達到此數字也不代表超越較大模型的一般能力。')
    table('VD 與 VS：各欄列正確／分母及百分比',['類別／題數','qAcc','fAcc','Easy','Hard','All'],[[r['category']+'/'+r['N'],*[str(load('metrics/'+r['category']+'.json')['table2'][k]['numerator'])+'/'+str(load('metrics/'+r['category']+'.json')['table2'][k]['denominator'])+'\n'+f"{float(r[k]):.2f}%" for k in ['qAcc','fAcc','Easy','Hard','All']]] for r in csvread('metrics/category_accuracy.csv')],[112,76,76,76,76,76])
    fig('02_easy_hard','圖 2。Easy／Hard 為控制組指標，非單題條件平均。')
    fig('03_original_edited','圖 3。無圖 115/178；原圖 267/447；修改圖 234/504。')
    p('原圖逐題 59.73%，修改圖 46.43%，相差 -13.30 個百分點；兩條件數量及題目組成不同。另在同時有原圖與修改圖的 422 組，先對各組修改變體取平均，再等權比較：原圖 59.00%、修改 47.63%，差 -11.37 點。按組重抽 2,000 次的描述性 95% 百分位區間為 [-18.13, -4.26] 點；這不是獨立逐題的因果效果或跨資料集保證。')
    table('九個子類別逐題結果',['類別','正確／分母','百分比'],[[r['category']+'/'+r['paper_subcategory'],r['numerator']+'/'+r['denominator'],f"{float(r['percent']):.2f}%"] for r in csvread('metrics/subcategory_accuracy.csv')],[200,142,150])
    fig('07_subcategory_accuracy','圖 4。VD/ocr 在論文稱 Poster；VS/ocr 才是另一個 OCR 類別。')
    p('Math 為 35/108 = 32.41%，Video 為 75/170 = 44.12%；在本次設定中屬較弱項。Poster 為 65/89 = 73.03%，Figure 為 54/80 = 67.50%。子類別樣本數不同，VS 亦包含無圖例外，不能把這些數字當成純視覺感知能力排序。')
    page();h('八、Yes/No Bias 分析')
    p('官方 yes_ratio_stats 不直接讀回答：yes_proxy_i = 1[c_i = gt_i]，PctDiff = (Σyes_proxy - Σgt)/N = (653-484)/1129 = 0.14969，亦即 +14.97 個百分點。FP Ratio = 錯誤項目中 gt=0 的比例 = 341/513 = 0.66472。這不是傳統 FP/(FP+TN)，也不是對原文真正 Yes 的直接計數。')
    p('由語意立場另外統計：排除 18 個開放式題，在 1,111 個二元題中，yes 507、no 434、uncertain 104、ambiguous 66。只在 941 個明確 yes/no 中，Yes 比例 507/941=53.88%，同子集 GT Yes 為 400/941=42.51%；直接差異 107/941=0.11371。錯極性中，false yes=227、false no=120，FP 錯誤占比 227/347=0.65418；傳統條件式 FPR 為 227/541=41.96%。')
    p('官方與直接結果都呈 Yes 偏向，但分母與對未知的處理不同，不能互換。極性正確而關鍵解釋錯誤、VS 未知被接受、參考內部衝突，都可能使代理極性不等於實際立場。直接版本仍使用原始二元 GT，因此也受其錯置影響。')
    fig('04_yes_no_bias','圖 5。兩種 Bias 統計各保留自己的分母。')
    table('對應原文 Table 3 的比較',['Model','PctDiff','FP','Correct','Incons.','Wrong','LH','VI','Mixed','來源'],[[r['model']+('\n'+r['evaluation'] if r['model'].startswith('GPT-4V') else ''),f"{r['PctDiff']:.4f}",f"{r['FP']:.4f}",*[f"{r[k]:.2f}" for k in ['Correct','Inconsistent','Wrong','LH','VI','Mixed']],'Measured' if r['result_type'].startswith('Our') else 'Published'] for r in comp],[104,40,40,40,40,40,40,40,40,68])
    p('PctDiff 為 [-1,1] 的比例差；FP 為 [0,1] 比例；其餘欄為百分比。Published Result 取自原文 Table 3；Measured 是本次實測。發表值已經過四捨五入，多 Judge 平均也未提供各輪整數計數，故不虛構其分子。')
    h('九、Consistency Test')
    p('同一張實體圖的所有題目都正確為 Correct，部分正確為 Inconsistent，全部錯為 Wrong；這不是比較兩段回答是否同字。346 圖中：Correct 99/346=28.61%、Inconsistent 176/346=50.87%、Wrong 71/346=20.52%。三者互斥且完整相加為 346。')
    fig('05_consistency','圖 6。半數左右圖像只在部分提問答對，顯示單次問法不足以代表穩定理解。')
    p('官方 figure score 為 0.54010，即平均圖內逐題比例；它可高於 fAcc，但本報告主結果不以此替代整圖全對率。控制組正確 101/455 與整圖正確 99/346 的分母、成員均不同，不應比較整數大小判定哪個較容易。')
    h('十、Language Hallucination 與 Visual Illusion 分析')
    p('674 個非 baseline 比較已保存 same 288、different 230、uncertain 156 及逐對理由。VD baseline 為原圖 figure_id=0；VS baseline 為無圖 figure_id=0。為餵給官方二元 same 欄，主版本把 uncertain 投影為 0，依其原 parser 未識別時的預設值；這不是宣稱 uncertain 已被判定為 different。')
    table('官方 Table 3 診斷：逐錯誤 VQ 項目',['類型','數量／錯誤總數','百分比'],[[k, f"{v['numerator']}/{v['denominator']}",pct(v)] for k,v in o['diagnosis_items'].items()],[170,172,150])
    p('513 個最終錯誤分為 LH 106、VI 286、Mixed 121。若改以失敗控制組彙整，354 組為 LH 46/354=12.99%、VI 203/354=57.34%、Mixed 105/354=29.66%。主 Table 3 依 evaluation.py 採逐項版本；分組版本另列，不能把逐項數字除以 455。')
    fig('06_diagnostic_types','圖 7。VI 的操作性占比最高，但此分類不能證明內部機制。')
    p('將全部 156 個 uncertain same 投影為 1，逐項分類變為 LH 108、VI 284、Mixed 121；All、qAcc、fAcc 不變。另一個重要差異：Fig. 3 的 VD 原圖對、修改錯且 same 路徑為 LH，而官方程式設為 Mixed。若只改這條分支，得到 LH 185/513=36.06%、VI 286/513=55.75%、Mixed 42/513=8.19%，有 79 項轉類。因此幻覺占比的解讀對實作版本相當敏感。')
    p('以下案例的判分先依文字 GT 完成，再實際檢視來源圖片進行說明；沒有用看圖後的直覺回改已固定標籤。十張展示影像均重新核對 SHA-256，保留來源原位元、拼圖順序及 provenance。')
    for case in cases:
        if case['case_id']!='F':b.append({'type':'pagebreak'})
        b.append({'type':'subheading','text':'案例 '+case['case_id']+'：'+case['title']});p(case['observation']);p(case['interpretation'])
        p('共同題目：'+case['samples'][-1]['question'])
        table('判定依據（模型文字為節錄；完整原文見 case_studies.json）',['Sample ID／條件','GT／語意／最終／診斷','模型回答'],[
            [s['sample_id']+' / '+s['image_type'],str(s['gt_answer'])+' / '+str(s['semantic_correctness'])+' / '+str(s['final_binary_correctness'])+' / '+s['diagnostic_trace']['diagnostic'],
             s['model_response_raw'] if len(s['model_response_raw'])<=270 else s['model_response_raw'][:270].rsplit(' ',1)[0]+' [節錄至此]'] for s in case['samples']],[117,100,275])
        imgs=[{**im,'condition':sample['image_type']} for sample in case['samples'] for im in sample['verified_images']]
        if imgs:
            b.append({'type':'imagepair','images':imgs,'stacked':case['case_id']=='D','max_height':205 if case['case_id']!='A' else 265})
            p('展示圖維持來源位元；完整 SHA-256、來源路徑與檢視紀錄見 case_studies.json。原圖與修改圖順序如標籤。')
    page();h('十一、與原論文的差異')
    table('沿用與調整的明確區分',['項目','處理'],[
        ['忠實沿用','固定官方資料及程式版本；assign_correctness；qAcc/fAcc/Easy/Hard/All 分組；圖像一致性；官方 Bias 代理；官方診斷分支與逐項分母。'],
        ['Judge 替換','GPT-4 輔助評分改為現有 gpt-6.1-sol 語意判分；給定二元 GT 與文字 GT。官方 evaluate_by_chatgpt 提示只使用文字參考，故本次額外發現欄位矛盾是方法差異。'],
        ['重複判分','原文多次 GPT-4 平均；本次全量一輪、397 題隱藏首標籤重讀及仲裁。沒有全量三輪，也沒有新增人類 Judge。'],
        ['語意比較','保留 same/different/uncertain 三值；官方二元 parser 的預設 0 僅用於投影；比較時本次上下文可見題目與參考，原官方提示不提供題目，可能有錨定偏差。'],
        ['額外透明統計','直接 Yes/No 立場、開放式題排除、參考爭議上下界、配對組重抽、Fig.3 替代分支都作補充；不混入原官方主數字。'],
        ['圖片來源','官方 Drive 失效，使用 metadata 逐題一致且雜湊固定的研究鏡像；無法獨立證明與失效原壓縮檔位元完全一致。'],
        ['資料差異','18 題開放式題、17 題參考或定義爭議完整保留；不悄悄清理、改 GT、排除到分母之外。']],[98,394])
    p('爭議敏感度保持分母不動，將已標記 17 題最終 correctness 全設 0 或全設 1：All 範圍 612-629/1129=54.21%-55.71%；qAcc 100-107/455=21.98%-23.52%；fAcc 99-104/346=28.61%-30.06%；Easy 249-256/455=54.73%-56.26%；Hard 190-198/430=44.19%-46.05%。這是指定爭議集合的極端上下界，不是所有潛在標註錯誤的統計信賴區間。')
    h('十二、實驗限制')
    p('第一，單模型、單種解碼設定，沒有量化或更大模型對照；結論限於此實測。第二，語意 Judge 仍會犯錯；同一模型的重讀並不獨立，隨機抽樣一致不能排除共同偏差。第三，17 筆參考或定義爭議需資料作者或人工裁決；其餘資料也可能還有未發現錯誤。')
    p('第四，原始生成達 128-token 上限共 40 題，複核後最終接受 28/40=70.00%，含 VS 無圖特例；截斷可能影響理由，不能據此認為長度限制無害。第五，對完整回答的重要解釋一併判分，會比只看二元極性嚴格；同時未逐項外查所有贅述事實，這是可追溯但非完美的折衷。')
    p('第六，VI 可能含視覺辨識、推理、文字題意及拒答等因素；LH 與 Mixed 也取決於 baseline 及 same 判定。不能把 55.75% VI 解讀成有同樣比例的純感知故障。第七，影格拼圖測的是靜態多圖時序推理，非原生影片解碼。第八，原論文年代、模型參數、提示、Judge、影像取得與記憶體策略不同，不能直接公平排名。')
    h('十三、結論及未來研究方向')
    p('本次已完成單張 8GB GPU 的一個 InternVL3-2B 全量復現與後續語意評估。實驗支持：All 54.56% 仍伴隨 qAcc 22.20% 與 fAcc 28.61%，顯示回答在跨條件與同圖不同問法下不穩定；修改圖相對原圖較低；數學及時序是此設定的弱項；Yes 偏向在兩種定義下均可見。這些都是由保存的真實回答及程式計算得到。')
    p('「常識記憶壓過視覺證據」可由部分修改後仍不變的案例合理推測，但不能只由輸出完全證明。後續可讓 Vision Agent 每次結論附對應圖像區域、OCR 字串及影格順序，分開檢驗感知證據與文字推論；再加入同圖多問法、反事實改圖及不確定性處理，在執行動作前要求證據與結論相容。')
    p('若再做研究，優先由人類裁決爭議參考，固定 Judge 規範並進行真正獨立重評；之後再比較像素量測、OCR 校驗或角度計算等工具輔助是否提升整組與整圖可靠性。這些是建議的延伸工作，本階段沒有宣稱已實作或已驗證其效果。')
    page();h('附錄 A：可重現性與資料檔')
    p('以既有判分紀錄重算，不需 GPU、不需任何 API 金鑰。新的語意 Judge 重跑可能不同，因此「重現」指從保存的全量標籤、第二輪及仲裁檔重建相同統計，而非保證新對話再判一次完全相同。')
    b.append({'type':'quote','text':'.venv/Scripts/python.exe stage2/scripts/finalize_judgments.py\n.venv/Scripts/python.exe -m unittest discover -s stage2/scripts -p test_metrics.py -v\n.venv/Scripts/python.exe stage2/scripts/compute_metrics.py\n.venv/Scripts/python.exe stage2/scripts/build_figures.py\n.venv/Scripts/python.exe stage2/scripts/build_report.py'})
    table('追溯路徑（相對 stage2/）',['檔案／資料夾','用途'],[
        ['inputs/responses.jsonl、ground_truth.jsonl','Stage 1 位元相同的正式回答與 GT 副本'],['judgments/batches/','47 批不可覆寫初判及 674 組語意比較'],['judgments/second_pass/','397 題第二輪觀察，與原標籤分開'],['judgments/adjudications.jsonl','23 個分歧的裁決與另 2 個參考錯置修正'],['judgments/unresolved_samples.jsonl','17 個尚需外部裁決的參考／定義問題'],['results/judgments.jsonl','全量最終標籤及完整原文，保留 first/second pass'],['results/diagnostic_trace.jsonl','每項 baseline、原文、語意、same 投影及分類依據'],['results/control_group_scores.jsonl、figure_group_scores.jsonl','逐組成員及全對狀態'],['metrics/','JSON 與 CSV；每個實測數字的分子分母、比較及敏感度'],['figures/、reports/case_studies.json','八張圖與六組案例；十張來源圖雜湊及實際視覺檢視紀錄'],['reports/stage1_reaudit.json、judge_quality.json','輸入再驗證及品質統計']],[220,272])
    h('附錄 B：需資料作者或人工裁決的 17 題')
    disputes=read(S2/'judgments/unresolved_samples.jsonl')
    table('保留全部樣本與分母；不擅改 Ground Truth',['Sample ID','保留問題'],[[r['sample_id'],r['review_reason']] for r in disputes],[165,327])
    p('其中有些模型立場明確，但參考二元與文字欄位相反；有些是正方形與菱形定義或同修改圖近遠方向的跨題衝突。完整所有回答與原始 GT 可由以上 ID 查回，不以自行猜出的修正版取代。')
    h('參考文獻與固定版本')
    p('[1] Guan et al. (2024). HallusionBench: An Advanced Diagnostic Suite for Entangled Language Hallucination and Visual Illusion in Large Vision-Language Models. CVPR. 本地 PDF 第 4-8 頁（Section 4/5；Fig.3-5；Tables2/3），比較數字位於 PDF 第 7 頁。')
    p('[2] 官方程式：https://github.com/tianyi-lab/HallusionBench；固定 commit 744007c232c292942c7f80eb61edb2465482da31；逐題資料版本 c226ce45c95eec2935b09789099409c682a6c05d。')
    p('[3] 模型：https://huggingface.co/OpenGVLab/InternVL3-2B；revision 899155015275a9b7338c7f4677e19c784e0e5a21。')
    p('[4] 影像研究鏡像：https://huggingface.co/datasets/lmms-lab-encoder/HallusionBench；revision cd417161857aefb23d878d42cf1bb53aa9dd646f。346 圖均有 SHA-256；metadata 與官方 1,129 列逐筆一致，未聲稱失效官方影像位元已驗證。')
    p('[5] 第一階段封存 HallusionBench_Stage1_Results.zip：SHA-256 f415c03bc7a7e86c84a28f3e8c8b234fb40efd0b32924099aca9854a19d4c637。評分及圖表的來源雜湊見 metrics/provenance.json 與輸出封存 manifest。未公開、未推送 GitHub。')
    return v2_blocks(b,o,q,se,je)

def v2_blocks(blocks,o,q,se,je):
    """Replace legacy prose with live values; preserve historical QC as explicitly historical."""
    audit=q['full_consistency_audit_v2'];n=audit['reference_disputes'];t=o['table2'];bias=o['bias'];direct=bias['direct_semantic']
    st=q['final_stance_counts'];sc=q['final_semantic_counts'];rel=se['pair_relations'];cs=o['consistency'];dg=o['diagnosis_items'];cg=o['diagnosis_failed_groups']
    old=load('judgments/consistency_v2/prior_final/overall.json');paired=se['paired_condition_comparison'];bounds=se['reference_dispute_accuracy_bounds'];conditions={r['condition']:r for r in csvread('metrics/condition_accuracy.csv')}
    raw=je['semantic_correct_only'];accepted=sum(je['VS_no_visual_semantic2_accepted'].values());dcount=direct['binary_stance_counts']
    names=['qAcc','fAcc','Easy','Hard','All'];main='；'.join(k+' '+frac(t[k]) for k in names)
    pairs='、'.join(f"{key} {rel.get(key,0)}" for key in ['same','different','uncertain'])
    replacements={
      '資料版本：':f'資料版本：2026-10-21，v2 全量一致性重審版。唯一實測視覺模型：OpenGVLab/InternVL3-2B。初判 1,129 題，歷史複核 397 題；本次再逐題閱讀全部 1,129 筆完整回答並重審 674 個配對，47 批皆保存。未完成判分 0 題；已知參考疑義 {n} 題另列。沒有重跑視覺模型或呼叫付費 Judge API。',
      '主要結果：':f'主要結果：{main}。主分數表示相對官方文字參考的判定，再套用官方 VS 無圖例外；不是整段解釋都正確的比率。',
      'Judge 身分由': 'Judge 為本對話確認的 gpt-6.1-sol。每批閱讀完整題目、官方文字參考及全部 model_response_raw，程式只展示、驗證與保存對話 Judge 撰寫的判斷。v2 在全量重審前固定 RUBRIC_v2.md 及 SHA-256，舊標籤可見；屬同模型一致性稽核，不是獨立盲評或人工驗證。主語意採 gt_answer_details，對齊官方 teacher prompt；二元 gt_answer 不改動，欄位衝突另列。',
      '參考明確是': '主標籤 1 是清楚且不衝突文字參考；0 是核心承諾或明確事實牴觸參考；2 是模型回答本身棄答、矛盾或指涉不明。純參考矛盾不再自動轉成 2。參考明確 No answer 或允許不知道時，正確棄答可為 1。參考中的明確數量、方向、實體也算判準；參考未涵蓋的額外推導不一律扣主分，而以 explanation_issue_flag 和 audit_note 另記。',
      '這是同一模型在':f'以上是 v1 的歷史重讀一致率，97.48% 不代表判分準確率；兩輪可能重複同一偏差。v2 另完成全量一致性稽核，並保留每筆 affirmed/revised、原文摘要雜湊與跨批裁決。最終語意為正確 {sc.get("1",0)}、錯誤 {sc.get("0",0)}、不確定 {sc.get("2",0)}；立場 yes {st.get("yes",0)}、no {st.get("no",0)}、uncertain {st.get("uncertain",0)}、ambiguous {st.get("ambiguous",0)}（含 18 題開放式）。沒有獨立人類或全量三輪平均，不能據此估計真正標註準確率。',
      '僅接受語意 1':f'僅接受原始語意 1 為 {frac(raw)}。官方 VS 無圖特例再接受 {accepted} 題語意 2，使 All 成為 {pct(t["All"])}。接受的立場分布為 '+ '、'.join(f'{key} {value}' for key,value in je['VS_no_visual_semantic2_accepted'].items())+'；作者程式接受所有 2，包含矛盾回答，因此不等同模型知道答案。',
      'InternVL3-2B 的 All':f'InternVL3-2B 的 All {pct(t["All"])} 與文獻列並排。不同年代、推論設定、圖片來源與 Judge 下的差值，只是描述性比較，不能用作受控排名或小模型超越較大模型的一般性結論。',
      '原圖逐題':f'原圖逐題 {float(conditions["original"]["percent"]):.2f}%，修改圖 {float(conditions["edited"]["percent"]):.2f}%，差 {float(conditions["edited"]["percent"])-float(conditions["original"]["percent"]):.2f} 個百分點；題目組成不同。另在 {paired["groups"]} 個同時有原圖及修改圖的控制組，先平均各組修改變體再等權比較：原圖 {100*paired["mean_original"]:.2f}%、修改 {100*paired["mean_edited"]:.2f}%，差 {100*paired["delta_edited_minus_original"]:.2f} 點。按組重抽 2,000 次的描述性 95% 百分位區間為 [{100*paired["cluster_bootstrap_95_percentile"][0]:.2f}, {100*paired["cluster_bootstrap_95_percentile"][1]:.2f}] 點；不是獨立逐題或跨資料集的因果保證。',
      'Math 為':'九類別中，Math 與 Video 仍屬此設定的較弱項；完整分子、分母及百分比見上表。樣本數不同，VS 也含無圖特例，不能當作純視覺感知能力排序。',
      '官方 yes_ratio_stats':f'官方 yes_ratio_stats 不直接讀回答：yes_proxy_i=1[c_i=gt_i]。PctDiff=({bias["official_pct_diff"]["predicted_yes_proxy_numerator"]}-{bias["official_pct_diff"]["gt_yes_numerator"]})/1129={bias["official_pct_diff"]["fraction"]:.5f}，即 {100*bias["official_pct_diff"]["fraction"]:+.2f} 百分點。FP Ratio={frac(bias["official_fp_ratio"])}；此處是錯誤項目中 gt=0 的比例，並非傳統 FP/(FP+TN)。',
      '由語意立場另外':f'直接立場排除 {direct["excluded_open_ended"]} 題開放式題。在 {direct["binary_items"]} 個二元題中：'+ '、'.join(f'{k} {v}' for k,v in dcount.items())+f'。明確 yes/no 子集有 {direct["determinate_items"]} 題，Yes {frac(direct["yes_rate"])}，同子集 GT Yes {frac(direct["gt_yes_rate_on_same_subset"])}；直接比例差 {direct["pct_diff"]["numerator"]}/{direct["pct_diff"]["denominator"]}={direct["pct_diff"]["fraction"]:.5f}。錯極性中的 FP 占比 {frac(direct["false_positive_share_among_polarity_errors"])}；條件式 FPR {frac(direct["false_positive_rate"])}。',
      '同一張實體圖的': '同一實體圖全題正確為 Correct，部分正確為 Inconsistent，全錯為 Wrong。346 圖的結果：'+ '；'.join(f'{label} {frac(cs[key])}' for key,label in [('correct','Correct'),('inconsistent','Inconsistent'),('wrong','Wrong')])+'。三類互斥且完整，與兩段回答的 same/different 是不同指標。',
      '官方 figure score':f'官方 figure score 為 {o["official_raw"]["figure"]["score"]:.5f}，是平均圖內逐題比例，不能代替 fAcc。控制組全對 {t["qAcc"]["numerator"]}/{t["qAcc"]["denominator"]} 與整圖全對 {t["fAcc"]["numerator"]}/{t["fAcc"]["denominator"]} 的成員及分母不同。',
      '674 個非 baseline':f'674 個非 baseline 比較全部重審：{pairs}。VD baseline 為原圖 figure_id=0，VS baseline 為無圖 figure_id=0。主版本將 uncertain 投影為 0，依原 parser 無法辨識時的預設值；投影不表示語意已確定 different。另列投影為 1 的結果。',
      '513 個最終錯誤':f'{dg["LH"]["denominator"]} 個最終錯誤：LH {dg["LH"]["numerator"]}、VI {dg["VI"]["numerator"]}、Mixed {dg["Mix"]["numerator"]}。若彙整到失敗控制組，則為 '+ '；'.join(k+' '+frac(v) for k,v in cg.items())+'。主 Table 3 採 evaluation.py 的逐 VQ 版本，兩種分母不互換。',
      '將全部 156 個':f'將全部 {se["uncertain_pair_count"]} 個 uncertain 投影為 1，診斷為 '+ '、'.join(f'{k} {v["numerator"]}' for k,v in se['uncertain_same_projected_1'].items())+'；準確率不變。只將 VD「baseline 對、修改錯、same」分支按 Figure 3 改為 LH，得到 '+ '、'.join(f'{k} {se["figure3_VD_same_wrong_variant_counts"].get(k,0)}' for k in ['LH','VI','Mixed'])+'。主表仍沿用官方程式，圖示替代版本只列敏感度。',
      '爭議敏感度保持':f'將已標記 {n} 題的 final correctness 全設為 0 或全設為 1，保持全部分母不變。各指標極端範圍：'+ '；'.join(f'{k} {bounds["all_disputes_wrong"][k]["numerator"]}-{bounds["all_disputes_correct"][k]["numerator"]}/{bounds["all_disputes_correct"][k]["denominator"]}（{bounds["all_disputes_wrong"][k]["percent"]:.2f}%-{bounds["all_disputes_correct"][k]["percent"]:.2f}%）' for k in names)+'。這只是指定疑義集合的上下界，不是整體標註錯誤的統計信賴區間。',
      '第一，單模型':f'第一，只有一個視覺模型及一種解碼設定。第二，全量一致性重審仍由同一對話模型執行，舊標籤可見，可能有錨定與共同偏差。第三，{n} 筆參考或定義疑義已完整列出並做敏感度，但未擅改官方 GT；其餘資料也不保證沒有未發現問題。這些限制如實寫入交付版，沒有未完成的判分批次。',
      '第四，原始生成':f'第四，40 題達 128-token 上限，最終接受 {frac(je["token_cap_accuracy"])}，不能視截斷為無害。第五，另標記 {audit["explanation_issue_flags"]} 筆可由文內算術、邏輯或參考識別的說明問題，其中 {audit["reference_accepted_with_explanation_issue"]} 筆仍由主參考規則接受。此附加旗標不是完整事實正確率；未外查每項歷史、數字或角色來源。',
      '第六，VI 可能':f'第六，VI 包括感知、推理、題意、拒答等多種可能因素；{pct(dg["VI"])} 是依控制規則的操作性占比，不能解讀為純感知故障率。LH/Mixed 也依賴 baseline 與配對關係。第七，影片題輸入為保留順序的靜態拼圖。第八，與歷史模型比較存在年代、設定、Judge 及影像來源差異。',
      '本次已完成單張':f'本次已完成單張 8GB GPU 的 InternVL3-2B 全量推論，以及固定判準下的 1,129 題、674 配對重審。All {pct(t["All"])}，qAcc {pct(t["qAcc"])}，fAcc {pct(t["fAcc"])}，顯示單題成功不代表跨條件、同圖不同問法皆穩定。修改條件較低、數學及時序較弱，以及 Yes 偏向，是本資料與設定下的描述性結果。',
      '若再做研究': '現有交付已完成固定規範、全量重審、錯誤解釋分欄、參考疑義敏感度與重現驗證。若未來需要提升到經外部驗證的標註，仍需真正獨立的人類或其他 Judge 對照；本次沒有將這項不存在的驗證寫成已完成。此限制不要求重新推論或增加視覺模型。',
      '以既有判分紀錄': '從保存的初判、397 題歷史複核、47 批 v2 稽核與跨批裁決重建全部標籤，再重算結果，不需 GPU 或 API。原始輸出及官方 GT 維持原位元；舊版完整結果放在 judgments/consistency_v2/prior_final/。新對話再次判分仍可能不同，重現保證限於已保存標註的決定性重算。'
    }
    seen=set();out=[]
    for block in blocks:
        block=dict(block)
        if block['type']=='paragraph':
            for prefix,value in replacements.items():
                if block['text'].startswith(prefix):block['text']=value;seen.add(prefix);break
        if block['type']=='image' and block['path'].endswith('03_original_edited.png'):
            block['caption']='圖 3。'+ '；'.join(f'{label} {conditions[key]["numerator"]}/{conditions[key]["denominator"]}' for key,label in [('no_visual','無圖'),('original','原圖'),('edited','修改圖')])+'。'
        if block['type']=='heading' and block['text'].startswith('附錄 B：'):block['text']=f'附錄 B：保留分母的 {n} 題參考疑義'
        if block['type']=='table':
            if block['title'].startswith('兩輪品質'):block['title']='v1 歷史重讀一致率（不是判分準確率）'
            block['rows']=[[str(cell).replace('本次全量一輪、397 題隱藏首標籤重讀及仲裁。','本次初判、397 題歷史複核，再完成全部 1,129 題與 674 配對的一致性重審。').replace('18 題開放式題、17 題參考或定義爭議',f'18 題開放式題、{n} 題參考或定義爭議').replace('17 個尚需外部裁決的參考／定義問題',f'{n} 個參考／定義疑義；已有主分數及敏感度') for cell in row] for row in block['rows']]
            if block['title'].startswith('追溯路徑'):
                block['rows'].append(['judgments/consistency_v2/','固定規範、47 批全量稽核、舊版快照、逐筆改動及跨批裁決'])
        out.append(block)
        if block['type']=='paragraph' and block['text'].startswith('以上是 v1 的歷史'):
            out.append({'type':'table','title':'v2 全量重審與舊版差異','headers':['範圍／指標','v1','v2／處理'],'rows':[[k,frac(old['table2'][k]),frac(t[k])] for k in names]+[['重審範圍','397 題歷史複核','全部 1129 題及 674 配對'],['本次改動','保留原標註',f'{audit["item_label_changes"]} 題語意、{audit["relation_changes"]} 組關係'],['解釋問題','未統一分欄',f'{audit["explanation_issue_flags"]} 筆旗標；其中 {audit["reference_accepted_with_explanation_issue"]} 筆主分接受'],['參考疑義','17 題',f'{n} 題，全部保留分母']],'widths':[100,155,237]})
            out.append({'type':'paragraph','text':'邊界判例：BOC=145 的回答雖有錯誤半角推導，仍不牴觸只給最終角度的文字參考，主分 1、解釋另標錯；鴨子題明稱多隻而參考是一隻，屬明確參考衝突，主分 0。No 明確否定 r³、正文肯定 r² 時可辨識題目立場；No 與同一角度命題相反且未撤回時保留 2。這些規則及理由全部落盤，不以讓分數升高為目標。'})
    assert seen==set(replacements),set(replacements)-seen
    return out
def markdown(bs):
    out=['# HallusionBench 第二階段實驗報告','## 單張 8GB GPU / InternVL3-2B / GPT-6.1 Judge','']
    for b in bs:
        typ=b['type']
        if typ=='pagebreak':continue
        if typ in ['heading','subheading']:out+=['## '+b['text'],'']
        elif typ=='paragraph':out += [b['text'],'']
        elif typ=='quote':out += ['> '+b['text'].replace('\n','\n> '),'']
        elif typ=='image':out += ['!['+b['caption']+'](../'+b['path']+')',b['caption'],'']
        elif typ=='imagepair':
            for im in b['images']:out+=['!['+im['condition']+'](../'+im['report_path']+')',im['condition']+' / SHA-256 '+im['sha256'],'']
        else:
            out += ['**'+b['title']+'**','', '| '+' | '.join(b['headers'])+' |','| '+' | '.join(['---']*len(b['headers']))+' |']
            out += ['| '+' | '.join(str(v).replace('\n','<br>') for v in row)+' |' for row in b['rows']];out+=['']
    return '\n'.join(out)
def pdf(bs):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak,KeepTogether
    pdfmetrics.registerFont(TTFont('JhengHei','C:/Windows/Fonts/msjh.ttc',subfontIndex=0))
    pdfmetrics.registerFont(TTFont('JhengHeiBold','C:/Windows/Fonts/msjhbd.ttc',subfontIndex=0))
    width=A4[0]-94
    normal=ParagraphStyle('Normal',fontName='JhengHei',fontSize=10,leading=16,wordWrap='CJK',spaceAfter=8,textColor=colors.HexColor('#22334b'))
    styles={'paragraph':normal,'heading':ParagraphStyle('H1',parent=normal,fontName='JhengHeiBold',fontSize=16,leading=23,spaceBefore=17,spaceAfter=9,keepWithNext=True,textColor=colors.HexColor('#125577')),
            'subheading':ParagraphStyle('H2',parent=normal,fontName='JhengHeiBold',fontSize=14,leading=20,spaceBefore=8,keepWithNext=True),
            'quote':ParagraphStyle('Quote',parent=normal,fontSize=8.6,leading=13,leftIndent=10,rightIndent=8,backColor=colors.HexColor('#f0f4f8'),borderPadding=7,spaceBefore=4,spaceAfter=12),
            'caption':ParagraphStyle('Caption',parent=normal,fontSize=8.2,leading=12,textColor=colors.HexColor('#506177'),spaceAfter=12),
            'cell':ParagraphStyle('Cell',parent=normal,fontSize=7.6,leading=11,spaceAfter=0),
            'cellhead':ParagraphStyle('CellHead',parent=normal,fontName='JhengHeiBold',fontSize=7.6,leading=11,spaceAfter=0,textColor=colors.white)}
    def para(text,style='paragraph'):
        text=str(text).replace('s∈{0,1,2}','s（0、1、2）').replace('c∈{0,1}','c（0、1）')
        return Paragraph(html.escape(text).replace('\n','<br/>'),styles[style])
    story=[Paragraph('HallusionBench',ParagraphStyle('Title',parent=normal,fontName='JhengHeiBold',fontSize=28,leading=36,textColor=colors.HexColor('#125577'))),
           Paragraph('第二階段實驗報告',ParagraphStyle('Subtitle',parent=normal,fontName='JhengHeiBold',fontSize=21,leading=30)),
           para('單張 8GB GPU / InternVL3-2B / GPT-6.1 Judge'),Spacer(1,8)]
    i=0
    while i<len(bs):
        b=bs[i];i+=1
        typ=b['type']
        if typ=='heading' and b['text']=='參考文獻與固定版本':
            story.append(KeepTogether([para(b['text'],'heading')]+[para(x['text']) for x in bs[i:] if x['type']=='paragraph']))
            break
        if typ=='pagebreak':story.append(PageBreak())
        elif typ in styles:story.append(para(b['text'],typ))
        elif typ=='table':
            story.append(para(b['title'],'subheading'))
            data=[[para(x,'cellhead') for x in b['headers']]]+[[para(x,'cell') for x in row] for row in b['rows']]
            widths=b.get('widths') or [width/len(b['headers'])]*len(b['headers']);widths=[w*width/sum(widths) for w in widths]
            t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#125577')),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f2f6f9')]),('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#125577')),('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#d5dfe7')),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6)]))
            story+=[t,Spacer(1,10)]
        elif typ=='imagepair':
            ims=[];captions=[];stacked=b['stacked'];cellwidth=width if stacked else (width-12)/2
            for src in b['images']:
                im=Image(str(S2/src['report_path']));scale=min(cellwidth/im.imageWidth,b['max_height']/im.imageHeight);im.drawWidth=im.imageWidth*scale;im.drawHeight=im.imageHeight*scale;im.hAlign='CENTER';ims.append(im);captions.append(para(src['condition'],'caption'))
            if stacked:data=[cell for pair in zip(ims,captions) for cell in ([pair[0]],[pair[1]])]
            else:data=[ims,captions]
            t=Table(data,colWidths=[width] if stacked else [width/2]*2,hAlign='CENTER');t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('ALIGN',(0,0),(-1,-1),'CENTER'),('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)]));story.append(KeepTogether([t,Spacer(1,6)]))
        elif typ=='image':
            im=Image(str(S2/b['path']));scale=min(width/im.imageWidth,b.get('max_height',270)/im.imageHeight);im.drawWidth=im.imageWidth*scale;im.drawHeight=im.imageHeight*scale;im.hAlign='CENTER'
            story.append(KeepTogether([im,Spacer(1,5),para(b['caption'],'caption')]))
    def page(c,doc):
        c.saveState();c.setFont('JhengHei',8);c.setFillColor(colors.HexColor('#63768a'));c.drawString(47,26,'HallusionBench | InternVL3-2B | 2026-10-21');c.drawRightString(A4[0]-47,26,str(doc.page));c.setStrokeColor(colors.HexColor('#d5dfe7'));c.line(47,A4[1]-30,A4[0]-47,A4[1]-30);c.restoreState()
    dest=S2/'reports/HallusionBench_Stage2_Report_zhTW.pdf'
    doc=SimpleDocTemplate(str(dest),pagesize=A4,rightMargin=47,leftMargin=47,topMargin=43,bottomMargin=43,title='HallusionBench 第二階段實驗報告',author='GPT-6.1 / Codex',pageCompression=1)
    doc.build(story,onFirstPage=page,onLaterPages=page)
def main():
    bs=blocks();dump(S2/'reports/report_content.json',bs)
    (S2/'reports/HallusionBench_Stage2_Report_zhTW.md').write_text(markdown(bs),encoding='utf-8');pdf(bs)
    print('Wrote Traditional Chinese Markdown and PDF reports')
if __name__=='__main__':main()
