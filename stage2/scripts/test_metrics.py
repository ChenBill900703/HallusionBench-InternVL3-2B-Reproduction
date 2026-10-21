import unittest,copy,collections
from compute_metrics import official,flags
def row(cat='VS',fig='0',visual='0',q='0',raw='1',gt='1',same='1'):
    return dict(category=cat,subcategory='test',set_id='0',figure_id=fig,visual_input=visual,question_id=q,judge_raw=raw,gt_answer=gt,same=same)
class MetricsTests(unittest.TestCase):
    def setUp(self):self.o=official()
    def assign(self,rows):return self.o['assign_correctness'](rows,'judge_raw')
    def test_uncertainty_exception_is_only_VS_no_visual(self):
        d=self.assign([row(raw='2'),row(fig='1',visual='1',raw='2'),row('VD',raw='2')])
        self.assertEqual([r['correct'] for r in d],[1,0,0])
    def test_control_all_correct_not_item_average(self):
        d=self.assign([row(raw='2'),row(fig='1',visual='1'),row(fig='2',visual='2',raw='0')])
        p=self.o['get_eval_pair_all'](d,'judge_raw');self.assertEqual((p['correct'],p['total'],p['total_q']),(0,1,3))
        self.assertEqual(self.o['get_eval_all'](d,'judge_raw')['correct'],2)
    def test_hard_groups_require_all_edited_variants(self):
        d=self.assign([row(),row(fig='1',visual='1'),row(fig='2',visual='2'),row(fig='3',visual='2',raw='0'),row(q='1'),row(fig='1',visual='1',q='1')])
        self.assertEqual((self.o['get_eval_pair_easy'](d)['correct'],self.o['get_eval_pair_easy'](d)['total']),(2,2))
        self.assertEqual((self.o['get_eval_pair_hard'](d)['correct'],self.o['get_eval_pair_hard'](d)['total']),(0,1))
        self.assertEqual(self.o['get_eval_pair_hard'](d)['total_q'],2)
    def test_figure_excludes_no_image_and_separates_partial(self):
        d=self.assign([row(raw='2'),row(fig='1',visual='1'),row(fig='1',visual='1',q='1',raw='0'),row(fig='2',visual='2')])
        f=self.o['get_eval_fig'](d);self.assertEqual((f['total'],f['correct'],f['inconsistent'],f['wrong']),(2,1,1,0))
        self.assertEqual(f['score'],.75);self.assertNotEqual(f['score'],f['correct']/f['total'])
    def test_bias_proxy_is_not_actual_stance(self):
        d=self.assign([row(raw='0',gt='0')]);d[0]['predicted_stance']='no'
        b=self.o['yes_ratio_stats'](d);self.assertEqual(b,dict(diff=1.,fp=1.))
    def test_VD_code_and_figure3_disagree_on_same_wrong(self):
        b=row('VD',raw='1');r=row('VD',fig='1',visual='2',raw='0')
        self.assertEqual(flags(r,b),(1,1));self.assertEqual(flags(r,b,True),(1,0))
    def test_diagnostic_branches(self):
        self.assertEqual(flags(row(raw='0'),row(raw='0')),(1,0))
        self.assertEqual(flags(row(fig='1',visual='1',raw='0'),row(raw='2')),(0,1))
        self.assertEqual(flags(row(fig='2',visual='2',raw='0',same='1'),row(raw='1')),(1,0))
        self.assertEqual(flags(row(fig='2',visual='2',raw='0',same='0'),row(raw='1')),(0,1))
        self.assertEqual(flags(row(fig='1',visual='1',raw='0',same='0'),row(raw='0')),(1,1))
    def test_AST_loads_only_pure_functions(self):
        self.assertNotIn('evaluate_by_chatgpt',self.o);self.assertNotIn('check_same_by_chatgpt',self.o);self.assertNotIn('openai',self.o)
if __name__=='__main__':unittest.main(verbosity=2)
