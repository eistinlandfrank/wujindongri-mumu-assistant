"""Launch-only real gate: discard one positive frame; never invent a match.

Run explicitly with --device <current> --auto-beast-rally. The first actual
warning image is withheld from recognition only; following fresh frames use
the unmodified matcher. No injection is installed in the distributable app.
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import wjdr_beast_hunt as h
import wjdr_mumu_assistant_qt as ui

original = h.match_same_target_conflict
withheld = []
def first_frame_miss(image):
    found = original(image)
    if found and not withheld:
        withheld.append(image)
    return None if withheld and image is withheld[0] else found

assert '--auto-beast-rally' in sys.argv and '--device' in sys.argv
h.match_same_target_conflict = first_frame_miss
os.environ['WJDR_BEAST_MAX_CYCLES'] = '2'
os.environ.pop('WJDR_BEAST_SEARCH_RACE_PAUSE', None)
os.environ['WJDR_QA_PAGE'] = '4'
ui.main()
