import json,hashlib,shutil
from pathlib import Path
from compute_metrics import ROOT,S2,read,dump
def main():
    rows={r['sample_id']:r for r in read(S2/'results/judgments.jsonl')};trace={r['sample_id']:r for r in read(S2/'results/diagnostic_trace.jsonl')}
    manifest={r['path']:r for r in read(S2/'inputs/images.jsonl')};out=[]
    cases=[
        ('A','修改地圖後仍沿用原答案',['VS/map/6/0/0','VS/map/6/1/0','VS/map/6/2/0'],
         '實際檢視兩張地鐵圖：原圖經 Pentagon 的路線為藍、黃；修改圖將紅藍對調，Pentagon 經過紅、黃線，藍線移到另一條路徑。模型在無圖、原圖、修改圖都回答藍線可到，沒有隨圖例與路線改變。',
         '修改題的 baseline 無圖正確、現答錯且 same，官方操作性分類為 LH。這支持答案未依修改視覺證據更新；是否由參數記憶主導仍屬推測。'),
        ('B','OCR 讀到新文字，品牌映射卻錯誤',['VD/ocr/13/0/0','VD/ocr/13/1/0'],
         '原圖字樣為 Red Bull；修改圖清楚改成 Red Deer，兩隻紅牛圖形保留。模型修改題原文已抄出 Red Deer，仍宣稱該文字表示 Red Bull。',
         '修改題語意 0；baseline 正確，但完整回答抄錄的名稱不同，same 判 different，官方歸 VI。不能僅憑品牌記憶的直覺改標 LH。這也揭示診斷依賴語意比較的尺度。'),
        ('C','視覺錯覺與相同 No 的不同事實',['VD/illusion/0/0/0','VD/illusion/0/1/0'],
         '實際檢視橙色圓圖：原圖兩中心圓等大，但周圍灰圓尺寸不同；修改圖右中心圓明顯加大。原答 No 並說右圓較小，修改答也為 No，但說右圓較大。',
         '原圖語意 0、修改圖語意 1；兩段 No 不能當 same，因較小與較大相反。原圖失敗按官方分類為 VI。等大判準由官方參考支持，本案例未另做像素量測。'),
        ('D','反轉時間順序仍說穿衣',['VD/video/5/0/0','VD/video/5/1/0'],
         '已檢視保留排列的三格拼圖。原序由衣物在頭頂到穿上；反序由穿著到衣物越過頭部。模型兩者都回答正在穿衣。這裡輸入是單張預先拼接 PNG，沒有另輸入影片或重新排序影格。',
         'baseline 正確、修改錯、same，官方程式歸 Mixed；論文 Figure 3 的 VD 同答案錯誤路徑則歸 LH。兩種版本分列，不以案例推定真正內部原因。'),
        ('E','圖表回答的肯否與正文互相矛盾',['VS/chart/7/0/0','VS/chart/7/1/0','VS/chart/7/2/0'],
         '已檢視政策利率圖：修改圖互換 US 與 UK 圖例。原圖回答先 No，後文明說美國 2019 年利率較高，因此是 ambiguous、語意 2；不能只取 No 算錯誤否定。原圖曲線的 2019 數值約 2.5，模型另稱約 5.0，也顯示年份讀取問題。',
         '修改題主要否定符合參考，語意 1；但它所列 1.0 與 0.0 無法支持「較低」。本評分追隨參考命題，不保證所有贅述數值正確；原文及數字推論旗標均保留。'),
        ('F','No 起頭實際是在說不知道',['VS/chart/0/0/0'],
         '無圖回答先 No，隨即說沒有進口資料，無法確認香港是否最大。這不是對香港排名作出明確否定，而是 uncertain、語意 2。此案例沒有圖片，也不聲稱看過視覺證據。',
         '官方 VS 無圖規則將語意 2 接受為最終 1。此特殊接受不表示模型知道正確答案，也不能套用到有圖問題。')]
    for cid,title,ids,obs,interpret in cases:
        samples=[]
        for i in ids:
            r=dict(rows[i]);imgs=[]
            for path in r['image_paths']:
                src=ROOT/path;sha=hashlib.sha256(src.read_bytes()).hexdigest();assert sha==manifest[path]['sha256']
                dest=S2/'figures/cases'/path.removeprefix('data/');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
                imgs.append({'source_path':path,'report_path':dest.relative_to(S2).as_posix(),'sha256':sha,'width':manifest[path]['width'],'height':manifest[path]['height']})
            r['verified_images']=imgs;r['diagnostic_trace']=trace[i];samples.append(r)
        out.append({'case_id':cid,'title':title,'observation':obs,'interpretation':interpret,'visual_inspection':'in-session actual image viewing; 2026-10-21' if any(r['verified_images'] for r in samples) else 'text only; no image supplied','samples':samples})
    dump(S2/'reports/case_studies.json',out)
    print('6 cases saved; 10 exact image copies rehashed, original collages unchanged.')
if __name__=='__main__':main()
