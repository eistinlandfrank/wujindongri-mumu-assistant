import sys,unittest,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from chapter_local_batch import allowed,decision,BASE
from PIL import Image,ImageDraw
class Tests(unittest.TestCase):
    def test_intent(self):
        self.assertIsNone(decision(None,{}));self.assertEqual(decision('city_chapter',{}),'city_chapter')
        self.assertIsNone(decision('city_chapter',{'consumed':['city_chapter']}))
        self.assertIsNone(decision('wall_menu',{'pending':'wall_menu'}))
    def test_assets_and_missing(self):
        for n in json.loads((BASE/'nodes.json').read_text()):
            ref=Image.open(BASE/n['asset']).convert('RGB');f=ref.copy()
            for x,y in n.get('green',[]):ImageDraw.Draw(f).rectangle((x-12,y-12,x+12,y+12),fill=(30,200,30))
            self.assertTrue(allowed(n,f,ref),n['id'])
            for box in n['boxes']:
                bad=f.copy();ImageDraw.Draw(bad).rectangle(box,fill='black');self.assertFalse(allowed(n,bad,ref),n['id'])
    def test_resources_insufficient(self):
        n=next(n for n in json.loads((BASE/'nodes.json').read_text()) if n['id']=='wall_confirm');ref=Image.open(BASE/n['asset']).convert('RGB')
        self.assertFalse(allowed(n,ref,ref))
if __name__=='__main__':unittest.main()
