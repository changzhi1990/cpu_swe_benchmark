from cpu_swe_benchmark.runner import endpoint_for_worker, parse_concurrency_levels


def test_endpoint_for_worker_uses_round_robin():
    endpoints = ["http://a/v1", "http://b/v1", "http://c/v1"]

    assert [endpoint_for_worker(i, endpoints) for i in range(7)] == [
        "http://a/v1",
        "http://b/v1",
        "http://c/v1",
        "http://a/v1",
        "http://b/v1",
        "http://c/v1",
        "http://a/v1",
    ]


def test_parse_concurrency_levels_rejects_zero_and_duplicates():
    assert parse_concurrency_levels("1,2,4,8") == [1, 2, 4, 8]

    for bad in ["0,1", "1,2,2", "abc"]:
        try:
            parse_concurrency_levels(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{bad!r} was accepted")
