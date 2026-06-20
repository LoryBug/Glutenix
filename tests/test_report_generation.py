from scripts.update_calibration_reports import update_bread_report


def test_bread_report_generated_block_is_current():
    assert update_bread_report(write=False) is False
