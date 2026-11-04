"""Compare scan scheduling memory with the previous eager submission pattern.

Run with Python -B tests/benchmark_scan_queue.py. No network I/O is performed.
The output measures Python allocations, not process RSS or network throughput.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import gc
import json
from pathlib import Path
import sys
import threading
import time
import tracemalloc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules.scan_tasks import scan_results


def probe(item):
    return item * 2


def eager(count, workers):
    # Submission pattern from the pre-review PortScanFrame._worker.
    with ThreadPoolExecutor(max_workers=workers) as executor:
        pending = {executor.submit(probe, item): item for item in range(count)}
        return sum(future.result() for future in as_completed(pending))


def bounded(count, workers):
    return sum(future.result() for _, future in
               scan_results(probe, range(count), workers, threading.Event()))


def measure(callback, count, workers):
    gc.collect()
    tracemalloc.start()
    started = time.perf_counter()
    checksum = callback(count, workers)
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert checksum == count * (count - 1)
    return {"peak_python_bytes": peak, "elapsed_seconds": round(elapsed, 4), "checksum": checksum}


if __name__ == "__main__":
    count, workers = 10000, 16
    print(json.dumps({"tasks": count, "workers": workers,
                      "eager": measure(eager, count, workers),
                      "bounded": measure(bounded, count, workers)}, indent=2))
