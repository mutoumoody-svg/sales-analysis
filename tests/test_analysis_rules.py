"""Pure analysis rule tests that do not require a live database."""

from app.services.analysis_service import detect_outlier_indices


def test_outlier_detection_marks_exceptional_month():
    values = [100.0, 102.0, 98.0, 101.0, 500.0, 99.0]
    assert detect_outlier_indices(values) == {4}


def test_outlier_detection_keeps_short_history():
    assert detect_outlier_indices([100.0, 200.0, 300.0]) == set()


def test_outlier_detection_keeps_stable_series():
    assert detect_outlier_indices([100.0, 100.0, 100.0, 100.0, 100.0]) == set()
