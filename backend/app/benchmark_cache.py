"""
Controlled cold-vs-warm Redis cache benchmark for Orbit.

Methodology
-----------
This script isolates the cache variable by hitting the SAME endpoint with
the SAME workspace ID twice:

  COLD run  — Redis key evicted beforehand -> server must compute/fetch
  WARM run  — Redis key present            -> server returns cached value

Same endpoint + same workspace + same server = the only variable is cache state.
This is the correct way to measure Redis latency improvement.

Without this control, comparing /activity vs /workspaces latency conflates
cache effects with different DB query complexity -- an invalid comparison.

Usage
-----
    # 1. Set credentials + a workspace that already has some activity
    export ORBIT_EMAIL="you@example.com"
    export ORBIT_PASSWORD="your-password"
    export ORBIT_WORKSPACE_ID="<uuid>"

    # 2. Run
    python benchmark_cache.py

    # Optional: override defaults
    ORBIT_COLD_RUNS=5 ORBIT_WARM_RUNS=50 python benchmark_cache.py
"""

import os
import time
import statistics
import requests

# Config
BASE_URL     = os.environ.get("ORBIT_BASE_URL", "http://localhost:8000")
EMAIL        = os.environ.get("ORBIT_EMAIL", "you@example.com")
PASSWORD     = os.environ.get("ORBIT_PASSWORD", "your-password")
WORKSPACE_ID = os.environ.get("ORBIT_WORKSPACE_ID")   # REQUIRED
REDIS_URL    = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

COLD_RUNS    = int(os.environ.get("ORBIT_COLD_RUNS", 30))
WARM_RUNS    = int(os.environ.get("ORBIT_WARM_RUNS", 100))

ACTIVITY_URL = f"{BASE_URL}/api/workspaces/{{workspace_id}}/activity"


def login() -> requests.Session:
    """
    Login via cookie-based auth (server sets access_token as httponly cookie).
    Returns a session with the cookie stored automatically.
    """
    session = requests.Session()
    resp = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=30,
    )
    resp.raise_for_status()
    if "access_token" not in session.cookies:
        raise SystemExit(
            f"Login returned HTTP {resp.status_code} but no access_token cookie. "
            "Ensure PRODUCTION=False in your .env."
        )
    print(f"Logged in as {EMAIL}")
    return session


def evict_cache(workspace_id: str) -> None:
    """
    Delete the Redis cache key for this workspace so the next request is cold.
    Key patterns must match what WorkspaceDevelopmentCache uses.
    Uses SCAN instead of KEYS to avoid blocking Redis.
    """
    try:
        import redis as redis_lib
        r = redis_lib.from_url(REDIS_URL, socket_connect_timeout=2)
        deleted = r.delete(
            f"workspace_activity:{workspace_id}",
            f"activity:{workspace_id}",
            f"dev_cache:{workspace_id}",
        )
        pattern_keys = list(r.scan_iter(match=f"*{workspace_id}*", count=100))
        if pattern_keys:
            r.delete(*pattern_keys)
            deleted += len(pattern_keys)
        print(f"  evicted {deleted} Redis key(s)")
    except Exception as e:
        print(f"  WARNING: could not evict Redis key: {e}")
        print("  Cold runs may not be truly cold.")


def hit_activity(session: requests.Session, workspace_id: str):
    url = ACTIVITY_URL.format(workspace_id=workspace_id)
    start = time.perf_counter()
    try:
        resp = session.get(url, timeout=30)
        elapsed_ms = (time.perf_counter() - start) * 1000
        if resp.status_code == 200:
            return elapsed_ms
        print(f"    HTTP {resp.status_code}: {resp.text[:80]}")
        return None
    except requests.RequestException as e:
        print(f"    ERROR: {e}")
        return None


def percentile(data, p):
    idx = min(int(len(data) * p / 100), len(data) - 1)
    return sorted(data)[idx]


def print_stats(latencies):
    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    avg = statistics.mean(latencies)
    print(f"  p50: {p50:7.0f} ms   p95: {p95:7.0f} ms   avg: {avg:7.0f} ms")
    return {"p50": p50, "p95": p95, "avg": avg}


def run_benchmark():
    if not WORKSPACE_ID:
        raise SystemExit(
            "Set ORBIT_WORKSPACE_ID to a workspace with existing activity/documents."
        )

    session = login()

    # COLD runs
    print(f"\n=== COLD cache ({COLD_RUNS} runs -- Redis key evicted before each) ===")
    cold_latencies = []
    for i in range(1, COLD_RUNS + 1):
        evict_cache(WORKSPACE_ID)
        ms = hit_activity(session, WORKSPACE_ID)
        if ms is not None:
            cold_latencies.append(ms)
            print(f"  run {i:2d}: {ms:7.0f} ms  [COLD]")
        else:
            print(f"  run {i:2d}: FAILED")

    if not cold_latencies:
        raise SystemExit("All cold runs failed. Check server logs.")
    cold_stats = print_stats(cold_latencies)

    # WARM runs
    print(f"\n=== WARM cache ({WARM_RUNS} runs -- key kept alive) ===")
    priming = hit_activity(session, WORKSPACE_ID)
    print(f"  prime :  {priming:7.0f} ms  [priming -- not counted]")

    warm_latencies = []
    for i in range(1, WARM_RUNS + 1):
        ms = hit_activity(session, WORKSPACE_ID)
        if ms is not None:
            warm_latencies.append(ms)
            print(f"  run {i:2d}: {ms:7.0f} ms  [WARM]")
        else:
            print(f"  run {i:2d}: FAILED")

    if not warm_latencies:
        raise SystemExit("All warm runs failed.")
    warm_stats = print_stats(warm_latencies)

    # Summary
    def pct(cold, warm):
        return (cold - warm) / cold * 100

    p50_r = pct(cold_stats["p50"], warm_stats["p50"])
    p95_r = pct(cold_stats["p95"], warm_stats["p95"])

    print("\n" + "=" * 60)
    print("=== Cache improvement (COLD -> WARM) ===")
    print(f"  Median : {cold_stats['p50']:7.0f} ms -> {warm_stats['p50']:7.0f} ms  ({p50_r:+.1f}%)")
    print(f"  P95    : {cold_stats['p95']:7.0f} ms -> {warm_stats['p95']:7.0f} ms  ({p95_r:+.1f}%)")
    print(f"  Avg    : {cold_stats['avg']:7.0f} ms -> {warm_stats['avg']:7.0f} ms")
    print()
    print("  Resume bullet:")
    print(f'  "Redis caching reduced median latency by {p50_r:.0f}%')
    print(f'   ({cold_stats["p50"]:.0f} ms -> {warm_stats["p50"]:.0f} ms) and p95 by {p95_r:.0f}%')
    print(f'   ({cold_stats["p95"]:.0f} ms -> {warm_stats["p95"]:.0f} ms),')
    print(f'   measured in a controlled cold-vs-warm benchmark')
    print(f'   (cold N={len(cold_latencies)}, warm N={len(warm_latencies)})."')
    print("=" * 60)


if __name__ == "__main__":
    run_benchmark()
