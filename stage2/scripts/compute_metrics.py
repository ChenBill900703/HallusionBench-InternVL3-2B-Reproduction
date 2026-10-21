"""Deterministic local evaluation. Load ONLY audited pure upstream functions by AST."""
import ast,collections,copy,csv,json,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]; S2=ROOT/'stage2'
NAMES={'assign_correctness','get_eval_all','get_eval_fig','get_eval_pair_all','get_eval_pair_easy','get_eval_pair_hard','yes_ratio_stats'}
def official():
    path=S2/'inputs/utils.py'; tree=ast.parse(path.read_text(encoding='utf-8'))
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in NAMES]
    assert {n.name for n in nodes}==NAMES
    ns={'np':np};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns)
    return ns
def read(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x]
def dump(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2,default=lambda x:x.item() if isinstance(x,np.generic) else str(x)),encoding='utf-8')
def jl(p,rows):p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
def csvout(p,rows):
    if not rows:return
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def ratio(c,n,formula):return {'numerator':int(c),'denominator':int(n),'fraction':c/n if n else None,'percent':100*c/n if n else None,'formula':formula}
def adapt(rows,pairs,uncertain_same=0):
    relation={r['sample_id']:r for r in pairs};out=[]
    for r in rows:
        rel=relation.get(r['sample_id'],{}).get('relation','baseline_self')
        same=1 if rel in ['same','baseline_self'] else 0 if rel=='different' else uncertain_same
        out.append({**r,'judge_raw':str(r['semantic_correctness']),'same':str(same)})
    return official()['assign_correctness'](out,'judge_raw')
def flags(r,base,figure3=False):
    c=int(r['judge_raw']);b=int(base['judge_raw']);same=int(r['same']);v=int(r['visual_input'])
    if str(r['figure_id'])=='0':
        return ((0,1) if c in [0,2] else (0,0)) if r['category']=='VD' else ((1,0) if c==0 else (0,0))
    if r['category']=='VD':
        if b==1 and c==0 and same:return (1,0) if figure3 else (1,1)
        return (0,1) if c in [0,2] else (0,0)
    if b==0:
        return (1,0) if c==0 and same else (1,1) if c in [0,2] else (0,0)
    if b==2:return (0,1) if c in [0,2] else (0,0)
    if c==2:return (0,1)
    if c==0:return (1,0) if v==2 and same else (0,1)
    return (0,0)
def diagnostic_trace(data,figure3=False):
    base={r['question_pair_id']:r for r in data if str(r['figure_id'])=='0'};rows=[]
    labels={(0,0):'none',(1,0):'LH',(0,1):'VI',(1,1):'Mixed'}
    for r in data:
        b=base[r['question_pair_id']];a=flags(r,b,figure3)
        rows.append({'sample_id':r['sample_id'],'question_pair_id':r['question_pair_id'],'baseline_sample_id':b['sample_id'],
                     'baseline_semantic':int(b['judge_raw']),'current_semantic':int(r['judge_raw']),
                     'category':r['category'],'visual_input':int(r['visual_input']),'same_projected':int(r['same']),
                     'LH_flag':a[0],'VI_flag':a[1],'diagnostic':labels[a],
                     'baseline_response_raw':b['model_response_raw'],'current_response_raw':r['model_response_raw']})
    return rows
def summarize(data):
    o=official();a=o['get_eval_all'](data,'judge_raw');p=o['get_eval_pair_all'](data,'judge_raw');f=o['get_eval_fig'](data)
    e=o['get_eval_pair_easy'](data);h=o['get_eval_pair_hard'](data);b=o['yes_ratio_stats'](data)
    metrics={'qAcc':ratio(p['correct'],p['total'],'sum_g product_{i in g} c_i / N_control_groups'),
             'fAcc':ratio(f['correct'],f['total'],'sum_f product_{i in f} c_i / N_real_figures; exclude VS figure_id=0'),
             'Easy':ratio(e['correct'],e['total'],'filter visual_input!=2, group by question_pair_id, count groups all correct'),
             'Hard':ratio(h['correct'],h['total'],'filter visual_input==2, group by question_pair_id, count groups all correct'),
             'All':ratio(a['correct'],a['total'],'sum_i c_i / N_items')}
    consistency={k:ratio(f[k],f['total'],'figure groups with all / some / zero items correct') for k in ['correct','inconsistent','wrong']}
    ds=p['LH_cg']+p['VI_cg']+p['Mix_cg'];dg=p['LH']+p['VI']+p['Mix']
    diagnosis={k:ratio(p[k+'_cg'],ds,'operational flags per VQ item / all flagged VQ items; evaluation.py Table3') for k in ['LH','VI','Mix']}
    groupdiag={k:ratio(p[k],dg,'union flags within each failed question control group / failed groups') for k in ['LH','VI','Mix']}
    yp=sum(int(r['correct'])==int(r['gt_answer']) for r in data);yg=sum(int(r['gt_answer']) for r in data)
    failures=[r for r in data if not r['correct']];fp=sum(int(r['gt_answer'])==0 for r in failures)
    bias={'official_pct_diff':{'predicted_yes_proxy_numerator':yp,'gt_yes_numerator':yg,'denominator':len(data),'difference_numerator':yp-yg,'fraction':b['diff'],'formula':'mean(int(correct==gt_answer)) - mean(gt_answer)'},
          'official_fp_ratio':ratio(fp,len(failures),'count(final incorrect AND gt_answer=0) / count(final incorrect)'),
          'inferred_yes_proxy_note':'Not observed stance; official proxy only.'}
    binary=[r for r in data if r['question_type']=='binary'];determinate=[r for r in binary if r['predicted_stance'] in ['yes','no']]
    direct_yes=sum(r['predicted_stance']=='yes' for r in determinate);direct_gt=sum(int(r['gt_answer']) for r in determinate)
    false_yes=sum(r['predicted_stance']=='yes' and int(r['gt_answer'])==0 for r in determinate)
    false_no=sum(r['predicted_stance']=='no' and int(r['gt_answer'])==1 for r in determinate)
    bias['direct_semantic']={'binary_items':len(binary),'determinate_items':len(determinate),'excluded_open_ended':len(data)-len(binary),
        'binary_stance_counts':dict(collections.Counter(r['predicted_stance'] for r in binary)),
        'yes_rate':ratio(direct_yes,len(determinate),'semantic yes / determinate binary answers'),
        'gt_yes_rate_on_same_subset':ratio(direct_gt,len(determinate),'gt yes / same determinate subset'),
        'pct_diff':{'numerator':direct_yes-direct_gt,'denominator':len(determinate),'fraction':(direct_yes-direct_gt)/len(determinate)},
        'false_positive_share_among_polarity_errors':ratio(false_yes,false_yes+false_no,'semantic yes AND gt=0 / all wrong-polarity determinate answers'),
        'false_positive_rate':ratio(false_yes,sum(int(r['gt_answer'])==0 for r in determinate),'semantic yes AND gt=0 / gt-negative determinate answers'),
        'false_negative_count':false_no,
        'note':'Uses binary gt only; reference conflicts remain. Excludes abstention and nonbinary questions; not same denominator as official proxy.'}
    # Independent simple group calculations validate denominators and whole-group logic.
    for name,predicate in [('qAcc',lambda r:True),('Easy',lambda r:int(r['visual_input'])!=2),('Hard',lambda r:int(r['visual_input'])==2)]:
        groups=collections.defaultdict(list)
        for r in data:
            if predicate(r):groups[r['question_pair_id']].append(r['correct'])
        assert (sum(all(v) for v in groups.values()),len(groups))==(metrics[name]['numerator'],metrics[name]['denominator'])
    return {'table2':metrics,'consistency':consistency,'diagnosis_items':diagnosis,'diagnosis_failed_groups':groupdiag,'bias':bias,
            'official_raw':{'all':a,'pair':p,'figure':f,'easy':e,'hard':h,'bias':b}}
def main():
    rows=read(S2/'results/judgments.jsonl');pairs=read(S2/'results/pair_relations.jsonl');assert len(rows)==1129 and len(pairs)==674
    data=adapt(rows,pairs);jl(S2/'results/official_scored_rows.jsonl',data)
    result=summarize(data);dump(S2/'metrics/overall.json',result)
    trace=diagnostic_trace(data);c=collections.Counter(r['diagnostic'] for r in trace)
    for key,label in [('LH','LH'),('VI','VI'),('Mix','Mixed')]:assert c[label]==result['diagnosis_items'][key]['numerator']
    jl(S2/'results/diagnostic_trace.jsonl',trace)
    groups=[]
    for category in ['VD','VS']:
        sub=[r for r in data if r['category']==category];s=summarize(sub);dump(S2/f'metrics/{category}.json',s)
        groups.append({'category':category,**{k:s['table2'][k]['percent'] for k in s['table2']},'N':len(sub)})
    csvout(S2/'metrics/category_accuracy.csv',groups)
    condition=[]
    for label in ['no_visual','original','edited']:
        sub=[r for r in data if r['image_type']==label];a=ratio(sum(r['correct'] for r in sub),len(sub),'sum final correctness / items in condition')
        condition.append({'condition':label,**{k:a[k] for k in ['numerator','denominator','percent']}})
    csvout(S2/'metrics/condition_accuracy.csv',condition)
    subcats=[]
    for cat,subcat in sorted({(r['category'],r['subcategory']) for r in data}):
        sub=[r for r in data if r['category']==cat and r['subcategory']==subcat];a=ratio(sum(r['correct'] for r in sub),len(sub),'sum correctness / subcategory items')
        subcats.append({'category':cat,'subcategory':subcat,'paper_subcategory':'Poster' if (cat,subcat)==('VD','ocr') else subcat.title(),**{k:a[k] for k in ['numerator','denominator','percent']}})
    csvout(S2/'metrics/subcategory_accuracy.csv',subcats)
    # Every control and figure group is exported with its member IDs.
    for mode in ['control','figure']:
        buckets=collections.defaultdict(list)
        for r in data:
            if mode=='figure' and r['category']=='VS' and str(r['figure_id'])=='0':continue
            k=r['question_pair_id'] if mode=='control' else '_'.join(str(r[x]) for x in ['category','subcategory','set_id','figure_id'])
            buckets[k].append(r)
        jl(S2/f'results/{mode}_group_scores.jsonl',[{'group_id':k,'correct_items':sum(r['correct'] for r in v),'total_items':len(v),'all_correct':int(all(r['correct'] for r in v)),'sample_ids':[r['sample_id'] for r in v]} for k,v in buckets.items()])
    same1=summarize(adapt(rows,pairs,1));fig3=diagnostic_trace(data,True);cf=collections.Counter(r['diagnostic'] for r in fig3)
    uncertain_pairs=[r for r in pairs if r['relation']=='uncertain']
    unresolved=[r for r in data if r['requires_review']];bound={}
    for tag,corr in [('all_disputes_wrong',0),('all_disputes_correct',1)]:
        altered=copy.deepcopy(data)
        for r in altered:
            if r['requires_review']:r['correct']=corr
        o=official();p=o['get_eval_pair_all']
        # Accuracy bounds do not need hallucination flags or raw labels.
        qb=collections.defaultdict(list)
        for r in altered:qb[r['question_pair_id']].append(r['correct'])
        fb=o['get_eval_fig'](altered);eb=o['get_eval_pair_easy'](altered);hb=o['get_eval_pair_hard'](altered)
        bound[tag]={'All':ratio(sum(r['correct'] for r in altered),len(altered),'all disputed final correctness set to 0 or 1'),
                    'qAcc':ratio(sum(all(v) for v in qb.values()),len(qb),'all disputed final correctness set to 0 or 1'),
                    'fAcc':ratio(fb['correct'],fb['total'],'all disputed final correctness set to 0 or 1'),
                    'Easy':ratio(eb['correct'],eb['total'],'same grouped easy definition'),
                    'Hard':ratio(hb['correct'],hb['total'],'same grouped hard definition')}
    # Matched control-group means: original versus mean of its edited variants.
    buckets=collections.defaultdict(list)
    for r in data:buckets[r['question_pair_id']].append(r)
    matched=[]
    for k,v in buckets.items():
        original=[r for r in v if r['image_type']=='original'];edited=[r for r in v if r['image_type']=='edited']
        if original and edited:matched.append({'group_id':k,'original':float(np.mean([r['correct'] for r in original])),'edited':float(np.mean([r['correct'] for r in edited]))})
    delta=np.array([r['edited']-r['original'] for r in matched]);rng=np.random.default_rng(20261021)
    boot=np.mean(rng.choice(delta,size=(2000,len(delta)),replace=True),axis=1)
    paired={'groups':len(delta),'mean_original':float(np.mean([r['original'] for r in matched])),'mean_edited':float(np.mean([r['edited'] for r in matched])),
            'delta_edited_minus_original':float(np.mean(delta)),'cluster_bootstrap_95_percentile':np.quantile(boot,[.025,.975]).tolist(),
            'bootstrap_seed':20261021,'replicates':2000,'caveat':'Descriptive resampling over benchmark groups; not an IID-question or causal model-effect confidence claim.'}
    jl(S2/'results/matched_condition_groups.jsonl',matched)
    sensitivity={'uncertain_pair_count':len(uncertain_pairs),'pair_relations':dict(collections.Counter(r['relation'] for r in pairs)),
                 'uncertain_same_projected_0':result['diagnosis_items'],'uncertain_same_projected_1':same1['diagnosis_items'],
                 'figure3_VD_same_wrong_variant_counts':dict(cf),'reference_dispute_accuracy_bounds':bound,'paired_condition_comparison':paired}
    dump(S2/'metrics/sensitivity.json',sensitivity)
    extra={'semantic_correct_only':ratio(sum(r['semantic_correctness']==1 for r in rows),len(rows),'sum(raw semantic==1)/1129'),
           'VS_no_visual_semantic2_accepted':dict(collections.Counter(r['predicted_stance'] for r in rows if r['category']=='VS' and str(r['figure_id'])=='0' and r['semantic_correctness']==2)),
           'nonbinary_ids':[r['sample_id'] for r in data if r['question_type']=='open_ended'],
           'raw_semantic2_ids':[r['sample_id'] for r in data if r['semantic_correctness']==2],
           'token_cap_accuracy':ratio(sum(r['correct'] for r in data if r['output_at_token_limit']),sum(r['output_at_token_limit'] for r in data),'correct final / 40 token-cap items')}
    dump(S2/'metrics/judge_effects.json',extra)
    csvout(S2/'metrics/table2_measured_counts.csv',[{'metric':k,**{x:v[x] for x in ['numerator','denominator','percent','formula']},'judge':'GPT-6.1 in-session semantic + adjudication','result_type':'Our Measured Result'} for k,v in result['table2'].items()])
    dump(S2/'metrics/provenance.json',{'judge':'gpt-6.1-sol','official_utils_sha256':hashlib.sha256((S2/'inputs/utils.py').read_bytes()).hexdigest(),'judgments_sha256':hashlib.sha256((S2/'results/judgments.jsonl').read_bytes()).hexdigest(),'pair_relations_sha256':hashlib.sha256((S2/'results/pair_relations.jsonl').read_bytes()).hexdigest(),'paid_api_calls':0,'primary_same_uncertain_projection':0,'version':'hb-stage2-v2'})
    print(json.dumps({'table2':result['table2'],'consistency':result['consistency'],'diagnosis':result['diagnosis_items'],'bias':result['bias'],'sensitivity':sensitivity,'judge_effects':extra},ensure_ascii=False,default=lambda x:int(x) if isinstance(x,np.integer) else str(x),indent=2))
if __name__=='__main__':main()
