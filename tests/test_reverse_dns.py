"""Bounded PTR lookup and scan cancellation with synthetic loopback DNS."""
import socket
import threading
import time
import unittest
from unittest.mock import Mock, patch

import dns.message
import dns.resolver
import dns.rrset
import nettools
from test_network_regressions import frame_stub


class ReverseDnsTests(unittest.TestCase):
    def test_silent_dns_server_has_a_deadline(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
            server.bind(("127.0.0.1", 0))
            resolver = dns.resolver.Resolver(configure=False)
            resolver.nameservers = ["127.0.0.1"]
            resolver.port = server.getsockname()[1]
            started = time.monotonic()
            with patch.object(dns.resolver, "get_default_resolver", return_value=resolver):
                name = nettools.NetworkScanFrame._resolve_hostname("192.0.2.1", timeout=0.2)
            self.assertEqual(name, "—")
            self.assertLess(time.monotonic() - started, 0.8)

    def test_real_ptr_reply_is_used_without_trailing_dot(self):
        errors = []
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
            server.bind(("127.0.0.1", 0))
            server.settimeout(2)
            resolver = dns.resolver.Resolver(configure=False)
            resolver.nameservers = ["127.0.0.1"]
            resolver.port = server.getsockname()[1]

            def respond():
                try:
                    data, address = server.recvfrom(4096)
                    query = dns.message.from_wire(data)
                    reply = dns.message.make_response(query)
                    reply.answer.append(dns.rrset.from_text(
                        query.question[0].name, 60, "IN", "PTR", "fixture.example."))
                    server.sendto(reply.to_wire(), address)
                except Exception as exc:
                    errors.append(exc)

            worker = threading.Thread(target=respond)
            worker.start()
            try:
                with patch.object(dns.resolver, "get_default_resolver", return_value=resolver):
                    self.assertEqual(nettools.NetworkScanFrame._resolve_hostname("192.0.2.1"),
                                     "fixture.example")
            finally:
                worker.join(3)
            self.assertFalse(worker.is_alive())
            self.assertEqual(errors, [])

    def test_missing_dns_support_leaves_address_usable(self):
        with patch.object(nettools, "DNS_AVAILABLE", False):
            self.assertEqual(nettools.NetworkScanFrame._resolve_hostname("192.0.2.1"), "—")

    def test_stop_during_lookup_does_not_start_port_or_http_probes(self):
        stop = threading.Event()

        def cancelled_lookup(*args, **kwargs):
            stop.set()
            return "fixture.example"

        frame = frame_stub(nettools.NetworkScanFrame,
                           stop_event=stop, _total=1, _ping_host=Mock(return_value=(True, 1)),
                           _resolve_hostname=Mock(side_effect=cancelled_lookup),
                           _probe_ports=Mock(), _enrich_host=Mock(), _prog_lbl=Mock(),
                           _prog_bar=Mock(), _found_lbl=Mock(), _rebuild_tree_sorted=Mock(),
                           q=Mock(), after=Mock())
        with patch.object(nettools.socket, "gethostbyaddr", side_effect=cancelled_lookup), \
                patch.object(nettools, "_parse_arp_cache", return_value=[]), \
                patch.object(nettools, "get_local_ip", return_value="192.0.2.2"), \
                patch.object(nettools, "_get_default_gateway", return_value=""), \
                patch.object(nettools.SessionHistory, "log"):
            nettools.NetworkScanFrame._scan_hosts(frame, ["192.0.2.1"], (100, 1, True))
        frame._probe_ports.assert_not_called()
        frame._enrich_host.assert_not_called()

    def test_stop_during_port_probe_skips_remaining_ports(self):
        stop = threading.Event()
        with patch.object(nettools.socket, "socket") as factory:
            connection = factory.return_value.__enter__.return_value
            connection.connect.side_effect = lambda *args: stop.set()
            result = nettools.NetworkScanFrame._probe_ports("192.0.2.1", stop_event=stop)
        self.assertEqual(factory.call_count, 1)
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
