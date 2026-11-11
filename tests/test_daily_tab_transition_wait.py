from pathlib import Path

SOURCE = ((Path(__file__).resolve().parents[1] / 'wjdr_mumu_assistant_qt.py').read_text(encoding='utf-8') + (Path(__file__).resolve().parents[1] / "wjdr_daily_controller.py").read_text(encoding="utf-8") + (Path(__file__).resolve().parents[1] / "wjdr_runtime_config.py").read_text(encoding="utf-8"))

def test_both_tab_paths_wait_for_acknowledgement_without_second_click():
    needle = 'if daily_tab_tapped and time.monotonic() < transition_deadline:'
    assert SOURCE.count(needle) == 2
    for section in SOURCE.split(needle)[1:]:
        wait_branch = section.split('if daily_tab_tapped or not page.point:', 1)[0]
        assert 'continue' in wait_branch
        assert 'target.tap' not in wait_branch

if __name__ == '__main__':
    test_both_tab_paths_wait_for_acknowledgement_without_second_click()
    print('daily tab transition wait: PASS')
