"""Mede latência p50/p95/p99 e cache hit de buscas REAIS pela API.

Uso: python -m scripts.benchmark_search --url http://localhost:8000 \\
  --query etica --requests 100 --output data/output/benchmark.json

Este programa não gera métricas fictícias: só salva valores de requisições
efetivamente executadas. Para comparar cache, use --cache-bust.
"""
import argparse
import json
import math
import statistics
import time
from pathlib import Path

import httpx


def percentile(values: list[float], percent: int) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * percent / 100
    low, high = math.floor(index), math.ceil(index)
    return round(ordered[low] + (ordered[high] - ordered[low]) * (index - low), 3)


def benchmark(url: str, query: str, requests: int, cache_bust: bool = False) -> dict:
    durations_ms = []
    errors = []
    cache_hits = 0
    start = time.perf_counter()
    with httpx.Client(timeout=30.0) as client:
        for i in range(requests):
            params = {"q": query}
            if cache_bust:
                # Modificar termo de busca evita reuso da mesma chave Redis.
                params["q"] = query + " " + str(i)
            before = time.perf_counter()
            try:
                response = client.get(url.rstrip("/") + "/api/questions", params=params)
                response.raise_for_status()
                data = response.json()
                durations_ms.append((time.perf_counter() - before) * 1000)
                cache_hits += int(bool(data.get("cache_hit")))
            except (httpx.HTTPError, ValueError) as exc:
                errors.append({"request": i + 1, "error": str(exc)})
    elapsed = time.perf_counter() - start
    successful = len(durations_ms)
    return {
        "query": query,
        "requests_attempted": requests,
        "requests_successful": successful,
        "requests_failed": len(errors),
        "elapsed_seconds": round(elapsed, 3),
        "requests_per_second": round(successful / elapsed, 3) if elapsed else None,
        "latency_ms": {
            "mean": round(statistics.mean(durations_ms), 3) if durations_ms else None,
            "p50": percentile(durations_ms, 50),
            "p95": percentile(durations_ms, 95),
            "p99": percentile(durations_ms, 99),
        },
        "observed_cache_hits": cache_hits,
        "observed_cache_hit_rate": round(cache_hits / successful, 4) if successful else None,
        "errors": errors[:20],
        "method": "sequential HTTP calls, wall-clock client-side, single process",
        "cache_bust": cache_bust,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--query", default="etica")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--cache-bust", action="store_true")
    parser.add_argument("--output", default="data/output/benchmark.json")
    args = parser.parse_args()
    if not 1 <= args.requests <= 10000:
        parser.error("--requests precisa estar entre 1 e 10000")
    data = benchmark(args.url, args.query, args.requests, args.cache_bust)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
