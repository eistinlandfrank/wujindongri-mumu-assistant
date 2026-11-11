import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from chapter_guided_routes import wall_menu,WALL_BOXES
from PIL import Image,ImageDraw
class Tests(unittest.TestCase):
    def setUp(self):self.ref=Image.open('assets/chapter_tasks/guided/wall-menu.png').convert('RGB')
    def test_pair(self):self.assertTrue(wall_menu(self.ref,self.ref.copy()))
    def test_missing_each(self):
        for box in WALL_BOXES:
            f=self.ref.copy();ImageDraw.Draw(f).rectangle(box,fill='black');self.assertFalse(wall_menu(self.ref,f))
    def test_blank(self):self.assertFalse(wall_menu(self.ref,Image.new('RGB',self.ref.size)))
if __name__=='__main__':unittest.main()
