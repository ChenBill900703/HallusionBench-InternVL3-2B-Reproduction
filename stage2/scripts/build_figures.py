import json,csv,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];S2=ROOT/'stage2'
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'tmp/matplotlib'))
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from compute_metrics import dump,csvout
font='C:/Windows/Fonts/msjh.ttc'
font_manager.fontManager.addfont(font)
plt.rcParams.update({'font.family':font_manager.FontProperties(fname=font).get_name(),'axes.unicode_minus':False,'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','savefig.facecolor':'white'})
BLUE='#1674a9';TEAL='#13887f';ORANGE='#d78825';RED='#b44850';GRAY='#8393a1'
def load(name):return json.loads((S2/name).read_text(encoding='utf-8'))
def csvload(name):
    with (S2/name).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def save(fig,name):
    fig.savefig(S2/f'figures/{name}.png',dpi=200,bbox_inches='tight');plt.close(fig)
def bars(ax,labels,values,counts=None,colors=BLUE):
    b=ax.bar(labels,values,color=colors,width=.62);ax.set_ylim(0,108);ax.set_ylabel('正確率（%）');ax.grid(axis='y',alpha=.16);ax.set_axisbelow(True)
    for i,(bar,v) in enumerate(zip(b,values)):
        ax.text(bar.get_x()+bar.get_width()/2,v+2,f'{v:.2f}%'+('\n'+counts[i] if counts else ''),ha='center',va='bottom',fontsize=10)
def main():
    o=load('metrics/overall.json');q=load('reports/judge_quality.json');p=load('inputs/published_tables.json')['rows']
    keys=['qAcc','fAcc','Easy','Hard','All'];t=o['table2']
    measured={'model':'InternVL3-2B','parameters':'2B class','evaluation':'GPT-6.1 semantic + adjudication','result_type':'Our Measured Result',**{k:t[k]['percent'] for k in keys},
              'PctDiff':o['bias']['official_pct_diff']['fraction'],'FP':o['bias']['official_fp_ratio']['fraction'],
              **{k:o['consistency'][v]['percent'] for k,v in [('Correct','correct'),('Inconsistent','inconsistent'),('Wrong','wrong')]},
              **{k:o['diagnosis_items'][v]['percent'] for k,v in [('LH','LH'),('VI','VI'),('Mixed','Mix')]}}
    rows=p+[measured];dump(S2/'metrics/comparison_tables.json',rows)
    csvout(S2/'metrics/table2_comparison.csv',[{k:r[k] for k in ['model','qAcc','fAcc','Easy','Hard','All','evaluation','result_type']} for r in rows])
    csvout(S2/'metrics/table3_comparison.csv',[{k:r[k] for k in ['model','PctDiff','FP','Correct','Inconsistent','Wrong','LH','VI','Mixed','evaluation','result_type']} for r in rows])
    counts=[{'metric':'PctDiff','numerator':169,'denominator':1129,'value':o['bias']['official_pct_diff']['fraction'],'units':'fraction'},
            {'metric':'FP Ratio','numerator':o['bias']['official_fp_ratio']['numerator'],'denominator':o['bias']['official_fp_ratio']['denominator'],'value':o['bias']['official_fp_ratio']['fraction'],'units':'fraction'}]
    for scope in ['consistency','diagnosis_items']:
        counts += [{'metric':scope+'/'+k,'numerator':v['numerator'],'denominator':v['denominator'],'value':v['percent'],'units':'percent'} for k,v in o[scope].items()]
    counts[0]['numerator']=o['bias']['official_pct_diff']['difference_numerator']
    csvout(S2/'metrics/table3_measured_counts.csv',counts)
    fig,ax=plt.subplots(figsize=(8.7,4.6));bars(ax,keys,[t[k]['percent'] for k in keys],[f"{t[k]['numerator']}/{t[k]['denominator']}" for k in keys],[BLUE,TEAL,BLUE,ORANGE,TEAL]);ax.set_title('InternVL3-2B：主要評估結果',loc='left',fontweight='bold');fig.tight_layout();save(fig,'01_main_accuracy')
    fig,ax=plt.subplots(figsize=(7,4.5));bars(ax,['Easy：條件篩選後整組','Hard：修改圖整組'],[t[k]['percent'] for k in ['Easy','Hard']],[f"{t[k]['numerator']}/{t[k]['denominator']} 組" for k in ['Easy','Hard']],[BLUE,ORANGE]);ax.set_title('Easy / Hard：兩者皆採分組全對');fig.tight_layout();save(fig,'02_easy_hard')
    c=csvload('metrics/condition_accuracy.csv');fig,ax=plt.subplots(figsize=(7.5,4.5));bars(ax,['無圖','原圖','修改圖'],[float(r['percent']) for r in c],[r['numerator']+'/'+r['denominator']+' 題' for r in c],[GRAY,BLUE,ORANGE]);ax.set_title('按輸入條件的逐題準確率');fig.text(.1,.01,'無圖含 VS 不確定接受規則；三條件題目組成不同。',fontsize=9);fig.tight_layout(rect=[0,.05,1,1]);save(fig,'03_original_edited')
    b=o['bias'];d=b['direct_semantic'];fig,axs=plt.subplots(1,2,figsize=(9,4.2));axs[0].bar(['官方代理','直接語意'],[100*b['official_pct_diff']['fraction'],100*d['pct_diff']['fraction']],color=[BLUE,TEAL]);axs[0].set_ylabel('Yes 差異（百分點）');axs[0].set_title('Yes Percentage Difference');axs[0].axhline(0,color=GRAY,lw=.7)
    for i,v in enumerate([100*b['official_pct_diff']['fraction'],100*d['pct_diff']['fraction']]):axs[0].text(i,v+.5,f'{v:.2f}',ha='center')
    v=[b['official_fp_ratio']['percent'],d['false_positive_share_among_polarity_errors']['percent']];axs[1].bar([f"官方代理\n{b['official_fp_ratio']['numerator']}/{b['official_fp_ratio']['denominator']}",f"直接語意\n{d['false_positive_share_among_polarity_errors']['numerator']}/{d['false_positive_share_among_polarity_errors']['denominator']}"],v,color=[BLUE,TEAL]);axs[1].set_ylim(0,100);axs[1].axhline(50,ls='--',color=GRAY);axs[1].set_title('FP 錯誤占比（%）')
    for i,x in enumerate(v):axs[1].text(i,x+2,f'{x:.2f}%',ha='center')
    fig.text(.08,.01,f"官方：全 1129 題；直接：{d['determinate_items']} 筆明確二元回答。分母與定義不同。",fontsize=9);fig.tight_layout(rect=[0,.06,1,1]);save(fig,'04_yes_no_bias')
    fig,ax=plt.subplots(figsize=(7,4.5));bars(ax,['整圖全對','部分正確','整圖全錯'],[v['percent'] for v in o['consistency'].values()],[f"{v['numerator']}/{v['denominator']} 圖" for v in o['consistency'].values()],[TEAL,ORANGE,RED]);ax.set_ylabel('圖像占比（%）');ax.set_title('Consistency：同圖完整問題集合');fig.tight_layout();save(fig,'05_consistency')
    fig,ax=plt.subplots(figsize=(7.5,4.5));bars(ax,['Language Hallucination','Visual Illusion','Mixed'],[v['percent'] for v in o['diagnosis_items'].values()],[f"{v['numerator']}/{v['denominator']}" for v in o['diagnosis_items'].values()],[ORANGE,BLUE,RED]);ax.set_ylabel('已標記錯誤的占比（%）');ax.set_title('官方程式的操作性診斷（逐 VQ 項目）');fig.tight_layout();save(fig,'06_diagnostic_types')
    sc=csvload('metrics/subcategory_accuracy.csv');fig,ax=plt.subplots(figsize=(9,5.5));labels=[r['category']+'/'+r['paper_subcategory'] for r in sc];vals=[float(r['percent']) for r in sc];pos=range(len(sc));ax.barh(list(pos),vals,color=[BLUE if r['category']=='VD' else TEAL for r in sc]);ax.set_yticks(list(pos),labels);ax.invert_yaxis();ax.set_xlim(0,105);ax.set_xlabel('逐題正確率（%）');ax.set_title('子類別準確率（VD/ocr 對應論文 Poster）',loc='left')
    for i,(r,v) in enumerate(zip(sc,vals)):ax.text(v+1,i,f"{v:.2f}%  ({r['numerator']}/{r['denominator']})",va='center',fontsize=9)
    fig.tight_layout();save(fig,'07_subcategory_accuracy')
    comp=[r for r in rows if r['evaluation']!='Human'];fig,ax=plt.subplots(figsize=(9,4.8));names=[r['model'] for r in comp];ax.barh(names,[r['All'] for r in comp],color=[TEAL if r['result_type']=='Our Measured Result' else GRAY for r in comp]);ax.invert_yaxis();ax.set_xlim(0,100);ax.set_xlabel('All Accuracy（%）');ax.set_title('文獻結果與本次實測：設定及 Judge 不同',loc='left')
    for i,r in enumerate(comp):ax.text(r['All']+1,i,f"{r['All']:.2f}  "+('實測' if r['result_type']=='Our Measured Result' else 'Published'),va='center',fontsize=9)
    fig.tight_layout();save(fig,'08_published_comparison')
    print('Wrote 8 PNG figures and comparison/count tables')
if __name__=='__main__':main()
