from scripts.benchmark_search import percentile, benchmark


def test_percentiles():
    values = [10, 20, 30, 40, 50]
    assert percentile(values, 50) == 30
    assert percentile(values, 95) == 48
    assert percentile(values, 99) == 49.6
    assert percentile([], 95) is None


def test_benchmark_counts_real_responses(monkeypatch):
    import httpx

    class Response:
        def raise_for_status(self):
            return None
        def json(self):
            return {"cache_hit": True}

    class Client:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def get(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr(httpx, "Client", Client)
    result = benchmark("http://localhost:8000", "ética", 3)
    assert result["requests_successful"] == 3
    assert result["observed_cache_hits"] == 3
    assert result["observed_cache_hit_rate"] == 1.0
    assert result["latency_ms"]["p95"] is not None
