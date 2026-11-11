from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageEnhance
from wjdr_backend import match_arena_opponent_list, match_arena_reviewed_victory_exit, match_arena_list_close

ROOT = Path(__file__).resolve().parents[1]

def test_guard_list_reads_mixed_formats_and_only_fights_lower_power():
    frame = Image.open(ROOT/'tests/fixtures/daily_arena_list_guard.png').convert('RGB')
    state = match_arena_opponent_list(frame, .9)
    assert state is not None and state.remaining == 5 and state.my_power == 20624052
    assert [o.power for o in state.opponents] == [95600,60000,154000,154000,154000]
    assert state.safest().fight_point == (1250,972)
    assert match_arena_opponent_list(ImageEnhance.Brightness(frame).enhance(.7), .9) is None
    hidden = frame.copy(); hidden.paste((30,40,50), (1174,900,1324,1050))
    assert match_arena_opponent_list(hidden, .9) is None
    missing_unit = frame.copy(); missing_unit.paste((130,170,200), (462,1264,510,1315))
    assert match_arena_opponent_list(missing_unit, .9) is None

def test_player_list_handles_red_and_green_wan_without_names():
    frame = Image.open(ROOT/'tests/fixtures/daily_arena_list_players_sanitized.png').convert('RGB')
    state = match_arena_opponent_list(frame, .9)
    assert state is not None and state.remaining == 4 and state.my_power == 20624052
    assert [o.power for o in state.opponents] == [19000000,35261000,15572000,5953000,13380000]
    assert state.safest().fight_point == (1250,1489)
    assert match_arena_list_close(frame, .9) == (1330,380)
    assert match_arena_opponent_list(ImageEnhance.Brightness(frame).enhance(.7), .9) is None
    assert match_arena_list_close(ImageEnhance.Brightness(frame).enhance(.7), .9) is None
    missing = frame.copy(); missing.paste((70,95,130), (502,958,550,1003))
    assert match_arena_opponent_list(missing, .9) is None

def test_result_exit_requires_victory_rank_and_uncovered_exit_text():
    frame = Image.new('RGB', (1440,2560), (30,40,50))
    frame.paste(Image.open(ROOT/'assets/daily_arena_victory_banner.png'), (520,780))
    frame.paste(Image.open(ROOT/'assets/daily_arena_result_rank.png'), (440,1050))
    frame.paste(Image.open(ROOT/'assets/daily_arena_result_exit_alt.png'), (520,2410))
    assert match_arena_reviewed_victory_exit(frame) == (120,2200)
    assert match_arena_reviewed_victory_exit(ImageEnhance.Brightness(frame).enhance(.7)) is None
    missing = frame.copy(); missing.paste((30,40,50), (440,1050,600,1130))
    assert match_arena_reviewed_victory_exit(missing) is None

if __name__ == '__main__':
    test_guard_list_reads_mixed_formats_and_only_fights_lower_power()
    test_player_list_handles_red_and_green_wan_without_names()
    test_result_exit_requires_victory_rank_and_uncovered_exit_text()
    print('arena guard layout safety: PASS')
