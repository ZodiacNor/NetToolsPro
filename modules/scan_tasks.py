"""Bounded, cancellable submission for network scan workers."""
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait


def scan_results(worker, items, max_workers, stop_event):
    """Yield (input, future) while keeping at most two tasks per worker queued.

    Cancellation discards queued work and waits only for in-flight probes.
    Callers must give each probe its own I/O timeout.
    """
    if max_workers < 1:
        raise ValueError("Worker count must be positive")
    items = iter(items)
    pending = {}
    executor = ThreadPoolExecutor(max_workers=max_workers)
    exhausted = False
    try:
        while not stop_event.is_set():
            while not exhausted and len(pending) < max_workers * 2 and not stop_event.is_set():
                try:
                    item = next(items)
                except StopIteration:
                    exhausted = True
                    break
                pending[executor.submit(worker, item)] = item
            if not pending or stop_event.is_set():
                break
            completed, _ = wait(pending, timeout=0.1, return_when=FIRST_COMPLETED)
            for future in completed:
                item = pending.pop(future)
                if stop_event.is_set():
                    return
                yield item, future
    finally:
        for future in pending:
            future.cancel()
        executor.shutdown(wait=True, cancel_futures=True)
