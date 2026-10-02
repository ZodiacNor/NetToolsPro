"""Read-only dashboard samples. Call on one background thread, never Tk's thread."""
import os
from pathlib import Path
import time


def _read(callback):
    """An unavailable metric must not suppress the rest of the dashboard."""
    try:
        return callback()
    except Exception:
        return None


class SystemSampler:
    def __init__(self, psutil_module, local_ip, gateway, clock=time.monotonic):
        self.ps = psutil_module
        self.local_ip = local_ip
        self.gateway = gateway
        self.clock = clock
        self._previous_io = None
        self._slow_at = None
        self._slow = {}

    def sample(self):
        now = self.clock()
        result = dict(cpu=None, cores=None, memory=None, disk=None,
                      download=None, upload=None, received=None, sent=None)
        if self.ps is not None:
            result["cpu"] = _read(self.ps.cpu_percent)
            result["cores"] = _read(self.ps.cpu_count)
            result["memory"] = _read(self.ps.virtual_memory)
            result["disk"] = _read(lambda: self.ps.disk_usage(Path.home().anchor if os.name == "nt" else "/"))
            io = _read(self.ps.net_io_counters)
            if io is not None:
                result.update(received=io.bytes_recv, sent=io.bytes_sent)
                if self._previous_io is not None:
                    before, received, sent = self._previous_io
                    elapsed = now - before
                    if elapsed > 0 and io.bytes_recv >= received and io.bytes_sent >= sent:
                        result["download"] = (io.bytes_recv - received) / elapsed
                        result["upload"] = (io.bytes_sent - sent) / elapsed
                self._previous_io = (now, io.bytes_recv, io.bytes_sent)
            else:
                self._previous_io = None
        if self._slow_at is None or now - self._slow_at >= 10:
            self._slow = {
                "connections": _read(lambda: len(self.ps.net_connections(kind="inet"))) if self.ps else None,
                "local_ip": _read(self.local_ip),
                "gateway": _read(self.gateway),
            }
            self._slow_at = now
        result.update(self._slow)
        return result
