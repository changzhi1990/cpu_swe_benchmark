from cpu_swe_benchmark.validation import classify_run


def test_classify_run_requires_submitted_and_validation_marker():
    assert classify_run("Submitted", ["setup", "VALIDATION_PASSED\nok"], None) == "success"
    assert classify_run("Submitted", ["no marker"], None) == "validation_failed"
    assert classify_run("LimitsExceeded", ["VALIDATION_PASSED"], None) == "not_submitted"
    assert classify_run("Submitted", ["VALIDATION_PASSED"], "boom") == "exception"
