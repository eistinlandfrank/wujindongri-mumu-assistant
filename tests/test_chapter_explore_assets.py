import importlib.util,unittest
from pathlib import Path
from PIL import Image
spec=importlib.util.spec_from_file_location('chapter',Path(__file__).resolve().parents[1]/'scripts/chapter_explore_batch.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class TestAssets(unittest.TestCase):
    def canvas(self,names):
        import json
        f=Image.new('RGB',(1440,2560),'#183546')
        for n in names:
            box=json.loads((m.ASSETS/f'{n}.json').read_text())['box'];f.paste(Image.open(m.ASSETS/f'{n}.png'),box[:2])
        return f
    def test_pairs(self):
        self.assertEqual(m.classify(self.canvas(['battle','deploy'])),'setup')
        self.assertEqual(m.classify(self.canvas(['victory','continue'])),'victory')
    def test_missing_anchor(self):
        for n in ['battle','deploy','victory','continue']:
            self.assertEqual(m.classify(self.canvas([n])),'unknown')
    def test_blank(self):self.assertEqual(m.classify(self.canvas([])),'unknown')
    def test_target(self):self.assertEqual(m.decide('victory','await_victory',10,10),'done')
    def test_no_repeat_battle(self):self.assertIsNone(m.decide('setup','await_victory',3,10))
    def test_no_repeat_continue(self):self.assertIsNone(m.decide('victory','await_setup',4,10))
    def test_unknown(self):
        for phase in ('setup','await_setup','await_victory','done'):
            self.assertIsNone(m.decide('unknown',phase,4,10))
    def test_done_no_input(self):
        for kind in ('setup','victory','unknown'):self.assertIsNone(m.decide(kind,'done',10,10))
    def test_furniture(self):
        for heading in ('medical_title','residence5_title'):
            for kind in ('build','upgrade','next'):
                names=[heading,'furniture_'+kind]
                if kind!='next':names+=['furniture_wood']
                f=self.canvas(names);f.putpixel((1340,1295),(50,150,250))
                self.assertEqual(m.furniture_kind(f,heading),kind)
    def test_furniture_missing_wood(self):
        f=self.canvas(['medical_title','furniture_upgrade']);f.putpixel((1340,1295),(50,150,250))
        self.assertIsNone(m.furniture_kind(f,'medical_title'))
    def test_furniture_wrong_building(self):
        f=self.canvas(['medical_title','furniture_upgrade','furniture_wood']);f.putpixel((1340,1295),(50,150,250))
        self.assertIsNone(m.furniture_kind(f,'residence5_title'))
    def test_furniture_grey(self):
        f=self.canvas(['medical_title','furniture_upgrade','furniture_wood']);f.putpixel((1340,1295),(110,110,110))
        self.assertIsNone(m.furniture_kind(f,'medical_title'))
if __name__=='__main__':unittest.main()
