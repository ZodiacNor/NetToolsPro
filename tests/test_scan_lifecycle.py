"""Cancellation, bounded queues, and silent subprocess regression checks."""
import os
import subprocess
import sys
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import nettools
import system_backend
from modules.scan_tasks import scan_results
from platform_utils import net
from test_network_regressions import frame_stub, variable


class BoundedScanTests(unittest.TestCase):
    def test_all_results_and_worker_errors_are_delivered(self):
        def probe(item):
            if item == 3:
                raise ValueError("Test probe failure")
            return item * 2
        results = dict(scan_results(probe, range(10), 2, threading.Event()))
        self.assertEqual(set(results), set(range(10)))
        self.assertEqual(results[4].result(), 8)
        with self.assertRaises(ValueError):
            results[3].result()

    def test_cancellation_does_not_materialize_or_scan_entire_network(self):
        stop = threading.Event()
        consumed, probed = [], []
        def items():
            for item in range(1_000_000):
                consumed.append(item)
                yield item
        def probe(item):
            probed.append(item)
            stop.set()
            return item
        self.assertEqual(list(scan_results(probe, items(), 2, stop)), [])
        self.assertLessEqual(len(consumed), 4)
        self.assertLessEqual(len(probed), 4)

    def test_pre_cancelled_scan_does_not_consume_input(self):
        stop = threading.Event()
        stop.set()
        def items():
            raise AssertionError("Cancelled scan consumed input")
            yield
        self.assertEqual(list(scan_results(Mock(), items(), 2, stop)), [])

    def test_invalid_worker_count(self):
        with self.assertRaises(ValueError):
            list(scan_results(Mock(), [], 0, threading.Event()))


class FrameLifecycleTests(unittest.TestCase):
    def test_arp_backend_reports_stop_instead_of_no_devices(self):
        stop = threading.Event()
        def cancelled(**kwargs):
            self.assertIs(kwargs["stop_event"], stop)
            stop.set()
            return iter(())
        with patch.object(net, "arp_scan_available", return_value=True), \
                patch.object(net, "arp_scan_scan", side_effect=cancelled):
            output = list(system_backend.LinuxBackend().run_arp_scan(stop))
        self.assertEqual(output[-1], ("Scan aborted by user.", "warning"))

    def test_cancelled_network_scan_restores_start_button(self):
        frame = frame_stub(nettools.NetworkScanFrame, ("_scan_hosts",),
                           stop_event=threading.Event(), _prog_lbl=Mock(),
                           _prog_bar=Mock(), ui_done=Mock(), q=Mock())
        frame.stop_event.set()
        frame.after = lambda _ms, callback: callback()
        nettools.NetworkScanFrame._worker(frame, [], (100, 1, False))
        frame.ui_done.assert_called_once()
        frame._prog_lbl.configure.assert_called_with(text="Scan stopped")

    def test_network_worker_failure_restores_start_button(self):
        frame = SimpleNamespace(_scan_hosts=Mock(side_effect=RuntimeError("test error")),
                                stop_event=threading.Event(), _prog_lbl=Mock(), ui_done=Mock(), q=Mock(),
                                after=lambda _ms, callback: callback())
        nettools.NetworkScanFrame._worker(frame, [], (100, 1, False))
        frame.ui_done.assert_called_once()
        frame._prog_lbl.configure.assert_called_with(text="Scan failed")

    def test_stop_keeps_scan_busy_until_worker_finishes(self):
        for cls in (nettools.NetworkScanFrame, nettools.PortScanFrame):
            frame = SimpleNamespace(running=True, stop_event=threading.Event())
            cls.stop_op(frame)
            self.assertTrue(frame.running)
            self.assertTrue(frame.stop_event.is_set())


@unittest.skipUnless(os.name == "posix", "ARP scanner uses Linux pipes")
class ArpProcessTests(unittest.TestCase):
    def run_scan(self, script, **kwargs):
        popen = subprocess.Popen
        processes = []
        def launch(_command, **options):
            process = popen([sys.executable, "-c", script], **options)
            processes.append(process)
            return process
        def cleanup():
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)
                for pipe in (process.stdout, process.stderr):
                    if pipe:
                        pipe.close()
        self.addCleanup(cleanup)
        patches = [patch.object(net, "arp_scan_binary", return_value="arp-scan"),
                   patch.object(net.subprocess, "Popen", side_effect=launch)]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        return net.arp_scan_scan(**kwargs), processes

    def test_timeout_interrupts_silent_process(self):
        scan, processes = self.run_scan("import time; time.sleep(0.8)", timeout_s=0.1)
        started = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            list(scan)
        self.assertLess(time.monotonic() - started, 0.7)
        self.assertIsNotNone(processes[0].poll())
        self.assertTrue(processes[0].stdout.closed)
        self.assertTrue(processes[0].stderr.closed)

    def test_stop_interrupts_silent_process(self):
        stop = threading.Event()
        scan, processes = self.run_scan("import time; time.sleep(3)", timeout_s=10, stop_event=stop)
        timer = threading.Timer(0.1, stop.set)
        timer.start()
        self.addCleanup(timer.join)
        started = time.monotonic()
        self.assertEqual(list(scan), [])
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertIsNotNone(processes[0].poll())

    def test_stderr_cannot_fill_pipe_and_deadlock_scan(self):
        scan, processes = self.run_scan(
            "import sys; sys.stderr.write('x'*1000000); print('192.0.2.1\\taa:bb:cc:dd:ee:ff\\tTest')",
            timeout_s=2)
        self.assertEqual(list(scan), ["192.0.2.1\taa:bb:cc:dd:ee:ff\tTest"])
        self.assertEqual(processes[0].returncode, 0)

    def test_permission_error_is_preserved(self):
        scan, _ = self.run_scan("import sys; sys.stderr.write('Operation not permitted'); sys.exit(1)")
        with self.assertRaises(PermissionError):
            list(scan)


class BandwidthTests(unittest.TestCase):
    def setUp(self):
        self.frame = frame_stub(nettools.BandwidthFrame, ("_monitor_loop",),
                                _monitor_running=True, _monitor_job=None, _prev_iface="old",
                                _prev_io=(1000, 1000), _t0_io=1, iface_var=variable("new"),
                                _history_rx=[0]*60, _history_tx=[0]*60,
                                bw_rx=Mock(), bw_tx=Mock(), bw_total_rx=Mock(), bw_total_tx=Mock(),
                                bw_pkts_rx=Mock(), bw_pkts_tx=Mock(), _draw_graph=Mock(),
                                after=Mock(return_value="timer"), after_cancel=Mock())

    def test_switching_interface_does_not_create_negative_rates(self):
        counters = SimpleNamespace(bytes_recv=10, bytes_sent=20, packets_recv=1, packets_sent=2)
        with patch.object(nettools.psutil, "net_io_counters", return_value={"new": counters}), \
                patch.object(nettools.time, "monotonic", return_value=2):
            self.frame._monitor_loop()
        self.assertEqual(self.frame._history_rx[-1], 0)
        self.assertEqual(self.frame._history_tx[-1], 0)
        self.frame.bw_rx.configure.assert_called_with(text=nettools.format_bytes_rate(0))

    def test_stop_cancels_pending_callback_before_restart(self):
        self.frame._monitor_job = "old-timer"
        nettools.BandwidthFrame._stop_monitor(self.frame)
        self.frame.after_cancel.assert_called_once_with("old-timer")
        self.assertIsNone(self.frame._monitor_job)
        self.assertFalse(self.frame._monitor_running)


if __name__ == "__main__":
    unittest.main()
