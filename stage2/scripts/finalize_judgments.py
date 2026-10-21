"""Materialize human-readable, manually authored in-session adjudications. No API."""
import json,re,collections,hashlib
from judge_io import ROOT,S2,read,atomic

def apply_v2(judgments, review):
    directory=S2/'judgments/consistency_v2'
    config_path=directory/'audit_config.json'
    if not config_path.exists():return judgments,review
    config=json.loads(config_path.read_text(encoding='utf-8'))
    assert hashlib.sha256((directory/'RUBRIC_v2.md').read_bytes()).hexdigest()==config['rubric_sha256']
    files=sorted(directory.glob('batch_*.jsonl'));pfiles=sorted(directory.glob('pairs_*.jsonl'))
    assert len(files)==len(pfiles)==47,'Do not materialize partial full-corpus audit'
    audited=[r for p in files for r in read(p)];pairs=[r for p in pfiles for r in read(p)]
    assert len(audited)==len({r['sample_id'] for r in audited})==1129
    assert len(pairs)==len({r['sample_id'] for r in pairs})==674
    decisions={r['sample_id']:dict(r) for r in audited}
    global_config=json.loads((directory/'global_adjudication.json').read_text(encoding='utf-8'))
    for i,(s,c,reason) in global_config['items'].items():
        decisions[i].update(predicted_stance={'y':'yes','n':'no','u':'uncertain','a':'ambiguous'}[s],semantic_correctness=c,short_explanation=reason,global_adjudication=True)
    for p in pairs:
        if p['sample_id'] in global_config['pairs']:
            code,reason=global_config['pairs'][p['sample_id']]
            p.update(relation={'s':'same','d':'different','u':'uncertain'}[code],reason=reason,global_adjudication=True)
        p['requires_review']=p['relation']=='uncertain'
    previous={r['sample_id']:r for r in read(directory/'prior_final/judgments.jsonl')}
    previous_pairs={r['sample_id']:r for r in read(directory/'prior_final/pair_relations.jsonl')}
    revised=[]
    for r in judgments:
        i=r['sample_id'];d=decisions[i];before=previous[i]
        digest=hashlib.sha256(json.dumps({k:r[k] for k in ['sample_id','question','gt_answer','gt_answer_details','model_response_raw']},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        assert digest==d['source_sha256']
        r['prior_v1_final']={k:before[k] for k in ['predicted_stance','semantic_correctness','final_binary_correctness','short_explanation']}
        for key in ['predicted_stance','semantic_correctness','short_explanation']:r[key]=d[key]
        r['consistency_audit_v2']=d
        r['audit_note']=d['audit_note']
        r['explanation_issue_flag']=any(tag in r['audit_note'] for tag in ['explanation_error:','explanation_degeneration:'])
        r['explanation_check_scope']='in-text arithmetic, logic, and reference conflicts only; not exhaustive external fact checking'
        note=r['audit_note']
        if 'reference_dispute:' in note:
            r['requires_review']=True
            r['review_reason']=(r['review_reason']+'; ' if r['review_reason'] else '')+note.split('reference_dispute:',1)[1].split(' explanation_error:')[0]
        r['reference_dispute']=r['requires_review']
        r['review_status']='full_consistency_audit_completed_reference_dispute' if r['requires_review'] else 'full_consistency_audit_completed'
        r['judge_prompt_version']='hb-semantic-v2'
        r['final_binary_correctness']=int(r['semantic_correctness']==1 or (r['category']=='VS' and str(r['figure_id'])=='0' and r['semantic_correctness']==2))
        changed=[key for key in ['predicted_stance','semantic_correctness','final_binary_correctness'] if r[key]!=before[key]]
        if changed:revised.append({'sample_id':i,'changed_fields':changed,'before':r['prior_v1_final'],'after':{k:r[k] for k in r['prior_v1_final']},'reason':d['short_explanation']})
    pd=[{'sample_id':p['sample_id'],'before':previous_pairs[p['sample_id']]['relation'],'after':p['relation'],'reason':p['reason']} for p in pairs if p['relation']!=previous_pairs[p['sample_id']]['relation']]
    summary={'completed_batches':47,'full_text_items_reviewed':1129,'full_response_relations_reviewed':674,'item_label_changes':len(revised),
             'semantic_label_changes':sum('semantic_correctness' in r['changed_fields'] for r in revised),
             'stance_changes':sum('predicted_stance' in r['changed_fields'] for r in revised),
             'final_correctness_changes':sum('final_binary_correctness' in r['changed_fields'] for r in revised),
             'relation_changes':len(pd),'explanation_issue_flags':sum(r['explanation_issue_flag'] for r in judgments),
             'reference_accepted_with_explanation_issue':sum(r['explanation_issue_flag'] and r['final_binary_correctness']==1 for r in judgments),
             'reference_disputes':sum(r['reference_dispute'] for r in judgments),'prior_labels_visible':True,
             'same_conversation_model':True,'independent_human_validation':False,'rubric_sha256':config['rubric_sha256'],
             'annotation_rule':'0/1/2 measure reference agreement; reference conflicts flagged separately; raw GT unchanged',
             'reliability_claim':'Full coverage consistency audit, not a measured grading accuracy or an independent validation.'}
    atomic(S2/'results/pair_relations.jsonl',pairs)
    atomic(directory/'changes.jsonl',revised);atomic(directory/'pair_changes.jsonl',pd)
    atomic(S2/'results/explanation_issues.jsonl',[r for r in judgments if r['explanation_issue_flag']])
    (S2/'reports/consistency_audit_v2.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    review.update(full_consistency_audit_v2=summary,unresolved_reference_disputes=summary['reference_disputes'],
                  final_semantic_counts=dict(collections.Counter(r['semantic_correctness'] for r in judgments)),
                  final_stance_counts=dict(collections.Counter(r['predicted_stance'] for r in judgments)))
    return judgments,review
def main():
    first=[r for p in sorted((S2/'judgments/batches').glob('batch_*.jsonl')) for r in read(p)]
    second=[r for p in sorted((S2/'judgments/second_pass').glob('chunk_*.jsonl')) for r in read(p)]
    assert len(first)==1129 and len(second)==397
    f={r['sample_id']:r for r in first}; q={r['sample_id']:r for r in second}
    config=json.loads((S2/'judgments/adjudication_decisions.json').read_text(encoding='utf-8'))
    choices={a:(b,c) for a,b,c in config['disagreement_decisions']}
    override={a:(s,c,t) for a,s,c,t in config['additional_overrides']}
    random_ids=set(json.loads((S2/'judgments/random_review_selection.json').read_text(encoding='utf-8'))['sample_ids'])
    fields=['predicted_stance','semantic_correctness']
    diffs=[i for i in q if any(f[i][k]!=q[i][k] for k in fields)]
    assert set(diffs)==set(choices)
    judgments=[]; adjud=[]
    for initial in first:
        i=initial['sample_id']; r=dict(initial); r['first_pass']={k:initial[k] for k in fields+['short_explanation']}
        r['question_pair_id']='_'.join(str(r[k]) for k in ['category','subcategory','set_id','question_id'])
        r['second_pass_reviewed']=i in q
        r['question_type']='open_ended' if re.search(r'\b(which (country|state|month)|what (country|state|month))\b',r['question'],re.I) else 'binary'
        if i in q:
            r['second_pass']={k:q[i][k] for k in fields+['short_explanation']}
            pick,why=choices.get(i,('second','兩輪一致。'))
            selected=q[i] if pick=='second' else initial
            for k in fields+['short_explanation']: r[k]=selected[k]
            r['review_notes']=q[i]['unresolved_issue']
            if i in choices: adjud.append({'sample_id':i,'first_pass':r['first_pass'],'second_pass':r['second_pass'],'selected':pick,'reason':why})
        if i in override:
            s,c,t=override[i];r.update(predicted_stance=s,semantic_correctness=c,short_explanation=t)
            adjud.append({'sample_id':i,'first_pass':r['first_pass'],'second_pass':r.get('second_pass'),'selected':'additional_adjudication','reason':t})
        r['final_binary_correctness']=int(r['semantic_correctness']==1 or (r['category']=='VS' and str(r['figure_id'])=='0' and r['semantic_correctness']==2))
        r['requires_review']=i in config['external_review']
        r['review_reason']=config['external_review'].get(i,'')
        r['review_status']='reviewed_reference_dispute' if r['requires_review'] else 'second_pass_completed' if i in q else 'first_pass_completed'
        r['judge_prompt_version']='hb-semantic-v1+edge-rules+adjudication-v1'
        judgments.append(r)
    atomic(S2/'judgments/adjudications.jsonl',adjud)
    atomic(S2/'judgments/disagreements.jsonl',[{'sample_id':i,'first_pass':f[i],'second_pass':q[i]} for i in diffs])
    def stats(ids):
        ids=list(ids);n=len(ids)
        joint=sum(all(f[i][k]==q[i][k] for k in fields) for i in ids)
        sem=sum(f[i]['semantic_correctness']==q[i]['semantic_correctness'] for i in ids)
        stance=sum(f[i]['predicted_stance']==q[i]['predicted_stance'] for i in ids)
        return {'n':n,'joint_agree':joint,'joint_disagree':n-joint,'semantic_agree':sem,'semantic_disagree':n-sem,'stance_agree':stance,'stance_disagree':n-stance,'joint_agreement_rate':joint/n,'semantic_agreement_rate':sem/n}
    review={'all_selected':stats(q),'preregistered_random':stats(random_ids),'all_token_caps_reviewed':all(r['sample_id'] in q for r in first if r['output_at_token_limit']),
            'all_initial_uncertain_ambiguous_reviewed':all(r['sample_id'] in q for r in first if r['predicted_stance'] in ['uncertain','ambiguous']),
            'adjudication_records':len(adjud),'additional_after_review_corrections':len(override),'unresolved_reference_disputes':len(config['external_review']),
            'final_semantic_counts':dict(collections.Counter(r['semantic_correctness'] for r in judgments)),
            'final_stance_counts':dict(collections.Counter(r['predicted_stance'] for r in judgments)),
            'same_model_re_read':True,'independent_human_validation':False,'full_triple_judgment':False}
    judgments,review=apply_v2(judgments,review)
    atomic(S2/'results/judgments.jsonl',judgments)
    atomic(S2/'judgments/unresolved_samples.jsonl',[r for r in judgments if r['requires_review']])
    (S2/'reports/judge_quality.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
    (S2/'judgments/progress.json').write_text(json.dumps({'completed_batches':47,'judged_samples':1129,'expected_samples':1129,'nonbaseline_pair_relations':674,'first_pass_complete':True,'quality_review_complete':True,'second_pass_reviewed':397,'unfinished_annotations':0,'external_reference_disputes':len(config['external_review'])},indent=2),encoding='utf-8')
    progress=json.loads((S2/'judgments/progress.json').read_text(encoding='utf-8'))
    if 'full_consistency_audit_v2' in review:progress.update(full_consistency_audit_v2_complete=True,full_consistency_audit_v2_items=1129,external_reference_disputes=review['unresolved_reference_disputes'])
    (S2/'judgments/progress.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(review,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
