#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NetTools Pro v1.8.1 - Network Engineering Toolkit
A comprehensive, portable network diagnostic and utility toolkit for Windows.

Author:      Bengt Simon Røch Dragseth
License:     MIT License
Copyright:   Copyright (c) 2026 Bengt Simon Røch Dragseth
Repository:  https://github.com/ZodiacNor/NetToolsPro
"""

__version__   = "1.8.1"
__author__    = "Bengt Simon Røch Dragseth"
__license__   = "MIT"
__copyright__ = "Copyright (c) 2026 Bengt Simon Røch Dragseth"

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import subprocess
import socket
import threading
import queue
import time
import ipaddress
import os
import sys
import struct
import re
import json
import pathlib
import ctypes
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import xml.etree.ElementTree as ET
import uuid
import urllib.request
import urllib.error
from urllib.parse import unquote
from collections import deque
import system_backend

# Cross-platform abstraction layer (see platform_utils/)
from platform_utils import (
    detect as _pu_detect,
    net as _pu_net,
    shell as _pu_shell,
    scripting as _pu_scripting,
    capabilities as _pu_caps,
)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False

try:
    from PIL import Image, ImageTk
    import io as _io
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import pystray
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False

# Hide console window on Windows when frozen — sourced from platform_utils
SUBPROCESS_FLAGS = _pu_detect.SUBPROCESS_FLAGS

# ==================== Application Metadata ====================
APP_NAME        = "NetTools Pro"
APP_VERSION     = "1.8.1"
APP_AUTHOR      = "Bengt Simon Røch Dragseth"
APP_LICENSE     = "MIT"
APP_COPYRIGHT   = "Copyright (c) 2026 Bengt Simon Røch Dragseth"
APP_DESCRIPTION = "Network diagnostics and utility toolkit"
APP_COMPANY     = "Bengt Simon Røch Dragseth"

UNSTABLE_UI_GLYPHS = {
    "🏓": "PING",
    "🔍": "Find",
    "🔎": "Find",
    "⚡": "Load",
    "🗺": "Route",
    "🌐": "Web",
    "📡": "Net",
    "🧮": "Subnet",
    "💡": "WOL",
    "➕": "Add",
    "🖧": "Iface",
    "📊": "Stats",
    "🔗": "Conn",
    "🔄": "Refresh",
    "📋": "Copy",
    "📷": "Cam",
    "📺": "Stream",
    "⚙️": "Cfg",
    "⚙": "Cfg",
    "📂": "Folder",
    "📁": "Folder",
    "📄": "New",
    "📝": "Script",
    "💾": "Save",
    "🗑": "Clear",
    "⭐": "Save",
    "🔬": "Cam",
    "🕐": "History",
    "📣": "mDNS",
    "💻": "CPU",
    "🧠": "RAM",
    "📥": "Net In",
    "📤": "Net Out",
    "🚪": "Gateway",
    "⚠": "WARN",
    "✓": "OK",
    "✔": "OK",
    "✗": "ERR",
    "✘": "NO",
    "▶": "",
    "⏹": "",
    "○": "",
    "●": "",
    "↓": "Down",
    "↑": "Up",
    "→": "->",
    "›": ">",
}


def _safe_ui_text(text):
    """Replace unstable emoji/glyphs before CustomTkinter renders text."""
    if not isinstance(text, str):
        return text
    for glyph, replacement in UNSTABLE_UI_GLYPHS.items():
        text = text.replace(glyph, replacement)

    cleaned_lines = []
    for line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        words = line.split(" ")
        if len(words) >= 2 and words[0].casefold() == words[1].casefold():
            words = words[1:]
        cleaned_lines.append(" ".join(words))
    return "\n".join(cleaned_lines)


def _install_safe_ctk_text_wrappers():
    """Wrap CustomTkinter text widgets so visible labels stay font-safe."""
    def wrap_class(original):
        class SafeTextWidget(original):
            def __init__(self, *args, **kwargs):
                if "text" in kwargs:
                    kwargs["text"] = _safe_ui_text(kwargs["text"])
                super().__init__(*args, **kwargs)

            def configure(self, require_redraw=False, **kwargs):
                if "text" in kwargs:
                    kwargs["text"] = _safe_ui_text(kwargs["text"])
                return super().configure(require_redraw=require_redraw, **kwargs)

            config = configure

        SafeTextWidget.__name__ = original.__name__
        return SafeTextWidget

    ctk.CTkLabel = wrap_class(ctk.CTkLabel)
    ctk.CTkButton = wrap_class(ctk.CTkButton)
    ctk.CTkCheckBox = wrap_class(ctk.CTkCheckBox)


_install_safe_ctk_text_wrappers()

COMMON_PORTS = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB",
    3389: "RDP", 3306: "MySQL", 5432: "PostgreSQL", 5900: "VNC",
    6379: "Redis", 8080: "HTTP-Alt", 8443: "HTTPS-Alt", 27017: "MongoDB",
    1433: "MSSQL", 161: "SNMP", 389: "LDAP", 636: "LDAPS",
    2049: "NFS", 111: "RPC", 873: "rsync", 993: "IMAPS", 995: "POP3S",
    587: "SMTP-Sub", 465: "SMTPS", 5060: "SIP", 5061: "SIPS",
    9200: "Elasticsearch", 6443: "k8s-API", 179: "BGP", 500: "IKE",
    514: "Syslog", 623: "IPMI", 1194: "OpenVPN", 1723: "PPTP",
    4500: "IPSec-NAT", 8888: "Jupyter", 9090: "Prometheus", 9100: "Grafana",
}

CAMERA_PORTS = [80, 81, 443, 554, 8080, 8081, 8443, 8554, 8000, 8001, 9000]

# MAC OUI prefix → vendor (first 6 hex digits, uppercase, no separators)
CAMERA_OUI = {
    # Hikvision
    "ACCC8E": "Hikvision", "BCAD28": "Hikvision", "C056E3": "Hikvision",
    "D46A35": "Hikvision", "E8D3F8": "Hikvision", "4419B6": "Hikvision",
    "A41437": "Hikvision", "B4A382": "Hikvision", "54C415": "Hikvision",
    "34EAE7": "Hikvision", "9CF6DD": "Hikvision", "4C7BE8": "Hikvision",
    "30E282": "Hikvision", "1CE624": "Hikvision", "485443": "Hikvision",
    # Dahua
    "3CEF8C": "Dahua",     "A0F3E4": "Dahua",     "4C11BF": "Dahua",
    "705DCC": "Dahua",     "E0508B": "Dahua",      "90C7AA": "Dahua",
    "40A3CC": "Dahua",     "F40228": "Dahua",      "70B3D5": "Dahua",
    # Axis
    "001A07": "Axis",      "00408C": "Axis",        "00B802": "Axis",
    # Hanwha / Samsung Techwin
    "001168": "Hanwha",    "104938": "Hanwha",      "000BE4": "Hanwha",
    "1C6758": "Hanwha",
    # Bosch / Pelco / FLIR / Mobotix / Vivotek
    "0050DC": "Bosch",     "000709": "Pelco",       "0003C5": "FLIR",
    "000AF7": "FLIR",      "001C8F": "Mobotix",     "000AD1": "Vivotek",
    "00022D": "Vivotek",   "005011": "Vivotek",     "002328": "Vivotek",
    # Sony / Panasonic
    "000963": "Sony",      "00601D": "Panasonic",   "00E091": "Panasonic",
    # Reolink
    "BC387A": "Reolink",   "E848B8": "Reolink",     "EC71DB": "Reolink",
    "DC8B28": "Reolink",
    # Amcrest / Foscam / Uniview / Milesight
    "001E47": "Amcrest",   "804B50": "Foscam",      "A47AF9": "Foscam",
    "C4E984": "TP-Link",   "000B6B": "Uniview",     "582D34": "Milesight",
    # Generic NVR/DVR chipsets
    "001122": "Hisilicon", "7801B8": "Hisilicon",
}

CAMERA_HTTP_KEYWORDS = [
    ("hikvision",       "Hikvision"),   ("dahua",       "Dahua"),
    ("axis",            "Axis"),        ("hanwha",      "Hanwha"),
    ("samsung techwin", "Hanwha"),      ("bosch",       "Bosch"),
    ("pelco",           "Pelco"),       ("flir",        "FLIR"),
    ("mobotix",         "Mobotix"),     ("vivotek",     "Vivotek"),
    ("reolink",         "Reolink"),     ("amcrest",     "Amcrest"),
    ("foscam",          "Foscam"),      ("uniview",     "Uniview"),
    ("milesight",       "Milesight"),   ("tiandy",      "Tiandy"),
    ("sony snc",        "Sony"),        ("panasonic bb","Panasonic"),
    ("network camera",  "IP Camera"),   ("ipcamera",    "IP Camera"),
    ("ip camera",       "IP Camera"),   ("nvr",         "NVR"),
    ("dvr",             "DVR"),         ("cctv",        "CCTV"),
    ("onvif",           "ONVIF Device"),("webcam",      "Webcam"),
]

# HTTP paths to probe on a camera IP for live streams or snapshots
# Each entry: (path, stream_type)
CAMERA_STREAM_PATHS = [
    # ── MJPEG live streams ────────────────────────────────────────────────
    ("/video",                                    "MJPEG"),
    ("/video.mjpg",                               "MJPEG"),
    ("/video.cgi",                                "MJPEG"),
    ("/mjpeg",                                    "MJPEG"),
    ("/mjpeg.cgi",                                "MJPEG"),
    ("/stream",                                   "MJPEG"),
    ("/stream.mjpeg",                             "MJPEG"),
    ("/live",                                     "MJPEG"),
    ("/live.mjpeg",                               "MJPEG"),
    ("/live/ch00_0",                              "MJPEG"),
    ("/livevideo.cgi",                            "MJPEG"),
    ("/axis-cgi/mjpg/video.cgi",                  "MJPEG"),   # Axis
    ("/cam/realmonitor?channel=1&subtype=0",      "MJPEG"),   # Dahua
    ("/videostream.cgi?rate=0",                   "MJPEG"),   # Foscam
    ("/cgi-bin/mjpeg",                            "MJPEG"),
    ("/cgi-bin/video.cgi",                        "MJPEG"),
    # ── Single-frame JPEG snapshots ───────────────────────────────────────
    ("/snapshot.jpg",                             "JPEG"),
    ("/snapshot",                                 "JPEG"),
    ("/image.jpg",                                "JPEG"),
    ("/img/snapshot.cgi",                         "JPEG"),
    ("/cgi-bin/snapshot.cgi",                     "JPEG"),
    ("/Streaming/channels/1/picture",             "JPEG"),    # Hikvision HTTP
    ("/ISAPI/Streaming/channels/1/picture",       "JPEG"),    # Hikvision ISAPI
    ("/onvif/snapshot",                           "JPEG"),
    ("/tmpfs/snap.jpg",                           "JPEG"),    # Reolink
    ("/cgi-bin/api.cgi?cmd=Snap&channel=0&rs=x", "JPEG"),    # Reolink API
    ("/cgi-bin/viewer/video.jpg",                 "JPEG"),
    ("/webcapture.jpg",                           "JPEG"),
    ("/control/faststream.jpg",                   "JPEG"),    # Mobotix
    ("/cgi-bin/mjpg/video.cgi",                   "MJPEG"),   # Axis alt
    ("/mjpg/video.mjpg",                          "MJPEG"),
    ("/ipcam/mjpeg.cgi",                          "MJPEG"),
    ("/live/mjpeg",                               "MJPEG"),
]

# RTSP URL templates — filled with {ip} at probe time
CAMERA_RTSP_TEMPLATES = [
    "rtsp://{ip}:554/Streaming/Channels/1",               # Hikvision main
    "rtsp://{ip}:554/Streaming/Channels/101",              # Hikvision sub-stream
    "rtsp://{ip}:554/cam/realmonitor?channel=1&subtype=0", # Dahua
    "rtsp://{ip}:554/axis-media/media.amp",                # Axis
    "rtsp://{ip}:554/live.sdp",
    "rtsp://{ip}:554/stream1",
    "rtsp://{ip}:554/video1",
    "rtsp://{ip}:554/h264",
    "rtsp://{ip}:554/live",
    "rtsp://{ip}:8554/live",
]

# Structured RTSP candidates for Camera Analysis: (path, port, vendor_style, score_bonus)
# score_bonus 2 = vendor-specific path, 1 = generic
CAMERA_RTSP_PATHS = [
    # Vendor-specific paths (score_bonus=2)
    ("/Streaming/Channels/1",                    554,  "Hikvision", 2),
    ("/Streaming/Channels/101",                  554,  "Hikvision", 2),
    ("/Streaming/Channels/102",                  554,  "Hikvision", 2),
    ("/MediaInput/h264",                         554,  "Hikvision", 2),
    ("/cam/realmonitor?channel=1&subtype=0",     554,  "Dahua",     2),
    ("/cam/realmonitor?channel=1&subtype=1",     554,  "Dahua",     2),
    ("/live/ch00_0",                             554,  "Dahua",     2),
    ("/axis-media/media.amp",                    554,  "Axis",      2),
    ("/live/0/MAIN",                             554,  "Samsung",   2),
    ("/Profile1/media.smp",                      554,  "Hanwha",    2),
    # Generic paths (score_bonus=1)
    ("/live.sdp",                                554,  "Generic",   1),
    ("/stream1",                                 554,  "Generic",   1),
    ("/video1",                                  554,  "Generic",   1),
    ("/h264",                                    554,  "Generic",   1),
    ("/live",                                    554,  "Generic",   1),
    ("/stream",                                  554,  "Generic",   1),
    ("/video.mp4",                               554,  "Generic",   1),
    ("/ch1/main",                                554,  "Generic",   1),
    ("/1",                                       554,  "Generic",   1),
    # Alt port 8554
    ("/live",                                   8554,  "Generic",   1),
    ("/Streaming/Channels/1",                   8554,  "Hikvision", 1),
]


# ==================== Camera Analysis — shared helpers ====================

_LINUX_ETH_P_IP = 0x0800
_LINUX_ETH_P_VLAN = 0x8100

def _cam_tcp_open(ip, port, timeout_ms=1000):
    """TCP connect probe. Returns True if port accepts connection."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_ms / 1000)
            s.connect((ip, port))
            return True
    except Exception:
        return False


def _cam_rtsp_alive(ip, port=554, timeout_s=2.0):
    """Send RTSP OPTIONS and check for RTSP/1 in response."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_s)
            s.connect((ip, port))
            s.sendall(b"OPTIONS rtsp://localhost RTSP/1.0\r\nCSeq: 1\r\n\r\n")
            banner = s.recv(256)
            return b"RTSP/1" in banner
    except Exception:
        return False


def _cam_oui_lookup(mac):
    """Look up vendor in CAMERA_OUI by MAC prefix."""
    prefix = mac.upper().replace(":", "").replace("-", "")[:6]
    return CAMERA_OUI.get(prefix, "")


def _parse_arp_cache():
    """Return list of (ip, mac) tuples from the system ARP cache."""
    return _pu_net.arp_table()


def _parse_dhcp_from_raw(data):
    """
    Parse IP + UDP + DHCP from raw socket bytes (IP_HDRINCL mode).
    Returns dict with msg_type, mac, client_ip, offered_ip — or None.
    """
    if len(data) < 248:          # IP(20) + UDP(8) + DHCP(240) minimum
        return None
    ihl = (data[0] & 0x0F) * 4
    if data[9] != 17:            # protocol must be UDP
        return None
    if len(data) < ihl + 8:
        return None
    udp_dst = (data[ihl + 2] << 8) | data[ihl + 3]
    if udp_dst not in (67, 68):
        return None
    dhcp = data[ihl + 8:]
    if len(dhcp) < 240:
        return None
    chaddr  = dhcp[28:34]
    mac     = ":".join(f"{b:02X}" for b in chaddr)
    ciaddr  = ".".join(str(b) for b in dhcp[12:16])
    yiaddr  = ".".join(str(b) for b in dhcp[16:20])
    if dhcp[236:240] != b"\x63\x82\x53\x63":   # magic cookie
        return None
    msg_type = None
    i = 240
    while i < len(dhcp):
        opt = dhcp[i]
        if opt == 255:
            break
        if opt == 0:
            i += 1
            continue
        if i + 1 >= len(dhcp):
            break
        length = dhcp[i + 1]
        if opt == 53 and length >= 1 and i + 2 < len(dhcp):
            msg_type = dhcp[i + 2]
        i += 2 + length
    type_names = {1: "Discover", 2: "Offer", 3: "Request", 5: "ACK", 6: "NAK"}
    return {
        "msg_type":   type_names.get(msg_type, str(msg_type)),
        "mac":        mac,
        "client_ip":  ciaddr if ciaddr != "0.0.0.0" else None,
        "offered_ip": yiaddr if yiaddr != "0.0.0.0" else None,
    }


def _capture_ipv4_packet(data):
    """Normalize Windows/Linux raw capture bytes to an IPv4 packet buffer."""
    if not _pu_detect.IS_LINUX:
        return data
    if len(data) < 14:
        return None
    ether_type = struct.unpack("!H", data[12:14])[0]
    offset = 14
    if ether_type == _LINUX_ETH_P_VLAN:
        if len(data) < 18:
            return None
        ether_type = struct.unpack("!H", data[16:18])[0]
        offset = 18
    if ether_type != _LINUX_ETH_P_IP or len(data) <= offset:
        return None
    return data[offset:]


def build_candidate_rtsp_urls(ip):
    """Return ranked list of candidate RTSP URL dicts for a given IP."""
    return [
        {"url": f"rtsp://{ip}:{port}{path}", "vendor": vendor, "score_bonus": bonus}
        for path, port, vendor, bonus in CAMERA_RTSP_PATHS
    ]


def _is_rfc1918(addr):
    """Return True if addr is in an RFC 1918 private range."""
    try:
        a = ipaddress.ip_address(addr)
        return a.is_private and not a.is_loopback
    except Exception:
        return False


def _rfc1918_class(addr):
    """Return the RFC 1918 class string for a private IP, or None."""
    try:
        a = ipaddress.ip_address(addr)
        if not a.is_private or a.is_loopback:
            return None
        first = a.packed[0]
        if first == 10:
            return "10.0.0.0/8"
        if first == 172 and 16 <= a.packed[1] <= 31:
            return "172.16.0.0/12"
        if first == 192 and a.packed[1] == 168:
            return "192.168.0.0/16"
        return None
    except Exception:
        return None


def _check_route_exists(candidate_ip):
    """Quick ping to test if a route to candidate_ip exists (even across subnets)."""
    return _pu_net.ping_once(str(candidate_ip), timeout_ms=500)


def _get_default_gateway(adapter_ip):
    """Return the default gateway IP for a given adapter, or ''."""
    return _pu_net.default_gateway(adapter_ip)


def _classify_mac(mac, target_ip, adapter_ip, adapter_mask, gateway_ip=""):
    """Determine whether a MAC address likely belongs to the target device or
    to a next-hop gateway.  Returns a dict with classification info.

    mac_class values:
      'direct'   — same L2 segment, MAC likely belongs to target device
      'gateway'  — target is routed, MAC likely belongs to next-hop gateway
      'unknown'  — cannot determine
      'none'     — no MAC available
    """
    if not mac or mac == "—":
        return {
            "mac_class": "none",
            "mac_label": "MAC unavailable from current network position",
            "resolved_mac": "",
            "gateway_mac": "",
        }
    try:
        net = ipaddress.ip_network(f"{adapter_ip}/{adapter_mask}", strict=False)
        cam = ipaddress.ip_address(target_ip)
        same_subnet = cam in net
    except Exception:
        same_subnet = None

    if same_subnet is True:
        return {
            "mac_class": "direct",
            "mac_label": "Direct MAC — camera on same L2 segment",
            "resolved_mac": mac,
            "gateway_mac": "",
        }

    # Target on different subnet — MAC from ARP is the next-hop, not the camera
    gw_mac = ""
    if gateway_ip:
        try:
            arp = _parse_arp_cache()
            for a_ip, a_mac in arp:
                if a_ip == gateway_ip:
                    gw_mac = a_mac
                    break
        except Exception:
            pass

    if gw_mac and mac.upper().replace("-", ":") == gw_mac.upper().replace("-", ":"):
        return {
            "mac_class": "gateway",
            "mac_label": f"Next-hop MAC (gateway {gateway_ip}) — not the camera itself",
            "resolved_mac": "",
            "gateway_mac": mac,
        }

    if same_subnet is False:
        return {
            "mac_class": "gateway",
            "mac_label": "Next-hop MAC only — camera is behind a router",
            "resolved_mac": "",
            "gateway_mac": mac,
        }

    return {
        "mac_class": "unknown",
        "mac_label": "MAC detected but ownership uncertain",
        "resolved_mac": mac,
        "gateway_mac": "",
    }


def compare_adapter_to_candidate(adapter_ip, adapter_mask, candidate_ip):
    """Compare adapter subnet to candidate IP.  Returns an expanded result dict
    with reachability analysis and human-readable explanation."""
    try:
        net = ipaddress.ip_network(f"{adapter_ip}/{adapter_mask}", strict=False)
        cam = ipaddress.ip_address(candidate_ip)
        same = cam in net

        cam_net = ipaddress.ip_network(f"{candidate_ip}/{net.prefixlen}", strict=False)
        a_class = _rfc1918_class(adapter_ip)
        c_class = _rfc1918_class(candidate_ip)
        same_class = (a_class is not None and a_class == c_class)

        if same:
            reach = "direct"
            expl = "Same subnet — adapter can reach this IP directly."
        elif same_class:
            reach = "possibly_routed"
            expl = (
                f"Different subnet ({net} vs {cam_net}) but same private range "
                f"({a_class}).  A gateway/router may provide a route.  "
                "Try accessing the camera before changing adapter config."
            )
        elif _is_rfc1918(adapter_ip) and _is_rfc1918(candidate_ip):
            reach = "likely_unreachable"
            expl = (
                f"Different private ranges ({a_class or '?'} vs {c_class or '?'}).  "
                "Direct access is very unlikely without a temporary adapter change, "
                "routing through a gateway, or connecting via an NVR/relay."
            )
        elif _is_rfc1918(adapter_ip) != _is_rfc1918(candidate_ip):
            reach = "likely_unreachable"
            expl = (
                "One address is private and the other is public.  "
                "Direct access requires NAT/routing or a VPN."
            )
        else:
            reach = "unknown"
            expl = "Could not determine the network relationship."

        return {
            "same_subnet": same,
            "adapter_net": str(net),
            "adapter_prefix": net.prefixlen,
            "candidate_net": str(cam_net),
            "same_rfc1918_class": same_class,
            "reachability": reach,
            "explanation": expl,
        }
    except Exception as exc:
        return {"same_subnet": None, "error": str(exc),
                "reachability": "unknown", "explanation": str(exc)}


def suggest_static_ip_for_candidate(candidate_ip):
    """
    Suggest a safe temporary static IP in the same subnet as candidate_ip.
    Returns dict with ip, mask, gateway.
    """
    try:
        octets = candidate_ip.split(".")
        first, second = int(octets[0]), int(octets[1]) if len(octets) > 1 else 0
        if first == 10:
            mask, prefix = "255.0.0.0", 8
        elif first == 172 and 16 <= second <= 31:
            mask, prefix = "255.255.0.0", 16
        else:
            mask, prefix = "255.255.255.0", 24
        last      = "100" if octets[-1] != "100" else "200"
        suggested = ".".join(octets[:-1] + [last])
        net       = ipaddress.ip_network(f"{candidate_ip}/{prefix}", strict=False)
        if ipaddress.ip_address(suggested) not in net:
            hosts     = list(net.hosts())
            suggested = str(hosts[99]) if len(hosts) > 99 else str(hosts[0])
        return {"ip": suggested, "mask": mask, "gateway": ""}
    except Exception:
        return {"ip": "", "mask": "", "gateway": ""}


CANDIDATE_SCORE_WEIGHTS = {
    "dhcp_request":         ("DHCP packet observed",          40),
    "onvif_found":          ("ONVIF discovery response",      35),
    "rtsp_open":            ("RTSP port open",                30),
    "camera_oui":           ("Camera vendor OUI match",       25),
    "camera_http_keywords": ("Camera keywords in HTTP",       20),
    "ssdp_found":           ("SSDP/UPnP response",           20),
    "http_open":            ("HTTP port open",                15),
    "arp_entry":            ("ARP cache entry",               10),
    "multicast_only":       ("Multicast-only address",       -20),
    "local_pc_mac":         ("Local PC MAC (not a camera)",  -50),
}


def score_camera_candidate(evidence):
    """
    Score a camera evidence dict. Returns (score: int, label: str).
    Labels: High (>=70), Medium (>=40), Low (>=20), Very Low (<20).
    """
    score = sum(w for k, (_, w) in CANDIDATE_SCORE_WEIGHTS.items() if evidence.get(k))
    score = max(0, min(score, 100))
    if score >= 70:   label = "High"
    elif score >= 40: label = "Medium"
    elif score >= 20: label = "Low"
    else:             label = "Very Low"
    return score, label


def score_camera_breakdown(evidence, reach="unknown", mac_class="unknown"):
    """Return a list of (label, points) tuples showing what contributed to the
    score, plus network-context modifiers.  Also returns the final clamped score."""
    items = []
    raw = 0
    for key, (label, pts) in CANDIDATE_SCORE_WEIGHTS.items():
        if evidence.get(key):
            items.append((label, pts))
            raw += pts
    # Network-context modifiers (informational, affect display not stored score)
    if reach == "likely_unreachable":
        items.append(("Different subnet, no confirmed route", -10))
        raw -= 10
    elif reach == "possibly_routed":
        items.append(("Different subnet (possibly routed)",   -5))
        raw -= 5
    if mac_class == "gateway":
        items.append(("MAC is next-hop only (not camera)",    -5))
        raw -= 5
    elif mac_class == "none":
        items.append(("MAC unavailable",                      -3))
        raw -= 3
    if evidence.get("ping_ok") is True:
        items.append(("Ping reachable",                       +5))
        raw += 5
    elif evidence.get("ping_ok") is False:
        items.append(("Ping failed",                          -5))
        raw -= 5
    final = max(0, min(raw, 100))
    return items, final


SIDEBAR_STRUCTURE = [
    # (type, display_label, key, category_key)
    ("standalone", "Dashboard",      "dashboard",    None),

    ("category",   "Diagnostics",    "cat_diag",     None),
    ("tool",       "Ping",           "ping",         "cat_diag"),
    ("tool",       "Port Scanner",   "portscan",     "cat_diag"),
    ("tool",       "Stress Test",    "stress",       "cat_diag"),
    ("tool",       "Traceroute",     "traceroute",   "cat_diag"),
    ("tool",       "DNS Lookup",     "dns",          "cat_diag"),

    ("category",   "Discovery",      "cat_disc",     None),
    ("tool",       "Net Scanner",    "netscan",      "cat_disc"),
    ("tool",       "Netdiscover",    "netdiscover",  "cat_disc"),
    ("tool",       "Subnet Calc",    "subnet",       "cat_disc"),
    ("tool",       "Wake-on-LAN",    "wol",          "cat_disc"),
    ("tool",       "ARP Table",      "arp",          "cat_disc"),
    ("tool",       "WHOIS",          "whois",        "cat_disc"),
    ("tool",       "mDNS Scan",      "mdns",         "cat_disc"),

    ("category",   "Camera",         "cat_cam",      None),
    ("tool",       "Camera Finder",  "camfinder",    "cat_cam"),
    ("tool",       "Stream Viewer",  "camview",      "cat_cam"),
    ("tool",       "Cam Analysis",   "cam_analysis", "cat_cam"),

    ("category",   "Monitoring",     "cat_mon",      None),
    ("tool",       "Interfaces",     "interfaces",   "cat_mon"),
    ("tool",       "Bandwidth",      "bandwidth",    "cat_mon"),
    ("tool",       "Connections",    "connections",  "cat_mon"),
    ("tool",       "Live Capture",   "livecapture",  "cat_mon"),

    ("category",   "System",         "cat_sys",      None),
    ("tool",       "System Tools",   "system_tools", "cat_sys"),
    ("tool",       "Script Lab",     "script_lab",   "cat_sys"),

    ("category",   "My Tools",       "cat_mine",     None),
    ("tool",       "History",        "history",      "cat_mine"),
    ("tool",       "Favorites",      "favorites",    "cat_mine"),
]

# Flat list for backward compat (cls_map, select_default, etc.)
SIDEBAR_TOOLS = [
    (label, key)
    for type_, label, key, _ in SIDEBAR_STRUCTURE
    if type_ in ("tool", "standalone")
]


# ==================== Utilities ====================
def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def get_local_network():
    local_ip = get_local_ip()
    try:
        if PSUTIL_AVAILABLE:
            for iface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET and addr.address == local_ip:
                        net = ipaddress.IPv4Network(f"{local_ip}/{addr.netmask}", strict=False)
                        return str(net)
    except Exception:
        pass
    return f"{'.'.join(local_ip.split('.')[:3])}.0/24"


def format_bytes_rate(b):
    if b < 1024:
        return f"{b:.0f} B/s"
    elif b < 1024 ** 2:
        return f"{b / 1024:.1f} KB/s"
    elif b < 1024 ** 3:
        return f"{b / 1024 ** 2:.1f} MB/s"
    return f"{b / 1024 ** 3:.2f} GB/s"


def format_bytes_total(b):
    if b < 1024:
        return f"{b} B"
    elif b < 1024 ** 2:
        return f"{b / 1024:.1f} KB"
    elif b < 1024 ** 3:
        return f"{b / 1024 ** 2:.1f} MB"
    return f"{b / 1024 ** 3:.2f} GB"


# ==================== Session History ====================
class SessionHistory:
    """In-memory session log of tool actions. Singleton via class methods."""
    _entries = []
    _listeners = []

    @classmethod
    def log(cls, tool, action, summary):
        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "tool": tool,
            "action": action,
            "summary": summary,
        }
        cls._entries.append(entry)
        for cb in cls._listeners:
            try: cb()
            except Exception: pass

    @classmethod
    def get_all(cls):
        return list(cls._entries)

    @classmethod
    def clear(cls):
        cls._entries.clear()

    @classmethod
    def subscribe(cls, callback):
        cls._listeners.append(callback)

    @classmethod
    def export_to_file(cls, filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            for e in cls._entries:
                f.write(f"[{e['timestamp']}] {e['tool']} \u2014 {e['action']}\n")
                f.write(f"  Result: {e['summary']}\n\n")


# ==================== Favorites Manager ====================
FAVORITES_FILE = pathlib.Path(__file__).parent / "favorites.json"


class FavoritesManager:
    """Persistent favorites store backed by JSON file."""
    _favorites = []

    @classmethod
    def load(cls):
        try:
            if FAVORITES_FILE.exists():
                cls._favorites = json.loads(FAVORITES_FILE.read_text(encoding="utf-8"))
        except Exception:
            cls._favorites = []

    @classmethod
    def save(cls):
        try:
            FAVORITES_FILE.write_text(
                json.dumps(cls._favorites, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    @classmethod
    def add(cls, name, fav_type, value, notes=""):
        entry = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "type": fav_type,
            "value": value,
            "notes": notes,
        }
        cls._favorites.append(entry)
        cls.save()
        return entry

    @classmethod
    def remove(cls, fav_id):
        cls._favorites = [f for f in cls._favorites if f["id"] != fav_id]
        cls.save()

    @classmethod
    def get_all(cls):
        return list(cls._favorites)

    @classmethod
    def get_by_type(cls, fav_type):
        return [f for f in cls._favorites if f["type"] == fav_type]


# ==================== Settings Manager ====================
SETTINGS_FILE = pathlib.Path(__file__).parent / "settings.json"


class SettingsManager:
    """Persistent app settings backed by JSON file. Singleton via class methods."""
    _defaults = {
        "theme": "dark",
        "minimize_to_tray": True,
    }
    _settings = {}

    @classmethod
    def load(cls):
        cls._settings = dict(cls._defaults)
        try:
            if SETTINGS_FILE.exists():
                cls._settings.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass

    @classmethod
    def save(cls):
        try:
            SETTINGS_FILE.write_text(
                json.dumps(cls._settings, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    @classmethod
    def get(cls, key, default=None):
        return cls._settings.get(key, cls._defaults.get(key, default))

    @classmethod
    def set(cls, key, value):
        cls._settings[key] = value
        cls.save()


# ==================== Tray Manager ====================
class TrayManager:
    """System tray icon manager using pystray. Windows only."""

    def __init__(self, app):
        self._app = app
        self._icon = None

    def setup(self):
        if not PYSTRAY_AVAILABLE:
            return
        img = self._create_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("Show", self._on_show, default=True),
            pystray.MenuItem("Exit", self._on_exit),
        )
        self._icon = pystray.Icon(APP_NAME, img, APP_NAME, menu)
        threading.Thread(target=self._icon.run, daemon=True).start()

    def _create_icon_image(self):
        """Generate a simple 64x64 tray icon programmatically."""
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (64, 64), "#1f6feb")
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), "N", font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((64 - tw) / 2, (64 - th) / 2 - bbox[1]), "N", fill="white", font=font)
        return img

    def minimize_to_tray(self):
        if self._icon:
            self._app.withdraw()

    def _on_show(self, icon=None, item=None):
        self._app.after(0, self._app.deiconify)
        self._app.after(50, self._app.lift)

    def _on_exit(self, icon=None, item=None):
        if self._icon:
            self._icon.stop()
        self._app.after(0, self._app.destroy)

    def stop(self):
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass


# ==================== Custom Output Widget ====================
class OutputText(tk.Text):
    """Colored, scrollable text output widget."""

    def __init__(self, parent, **kwargs):
        defaults = {
            "bg": "#0d1117", "fg": "#c9d1d9",
            "font": ("Consolas", 10), "relief": "flat",
            "padx": 10, "pady": 8, "wrap": "word",
            "state": "disabled", "insertbackground": "#ffffff",
            "selectbackground": "#264f78", "borderwidth": 0,
        }
        defaults.update(kwargs)
        super().__init__(parent, **defaults)
        self.tag_configure("success",   foreground="#3fb950")
        self.tag_configure("error",     foreground="#f85149")
        self.tag_configure("warning",   foreground="#d29922")
        self.tag_configure("info",      foreground="#58a6ff")
        self.tag_configure("header",    foreground="#79c0ff", font=("Consolas", 10, "bold"))
        self.tag_configure("dim",       foreground="#8b949e")
        self.tag_configure("highlight", foreground="#f0883e")
        self.tag_configure("normal",    foreground="#c9d1d9")
        self.tag_configure("cyan",      foreground="#39d3d3")
        self.tag_configure("green",     foreground="#56d364")

    def append(self, text, tag="normal", newline=True):
        self.configure(state="normal")
        if newline and self.get("1.0", "end-1c"):
            self.insert("end", "\n")
        self.insert("end", text, tag)
        self.see("end")
        self.configure(state="disabled")

    def clear(self):
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")


# ==================== Base Tool Frame ====================
class BaseToolFrame(ctk.CTkFrame):
    """Base class for all tool frames with shared utilities."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="#0d1117", **kwargs)
        self.running = False
        self.stop_event = threading.Event()
        self.output_queue = queue.Queue()

    def make_header(self, title, description):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(18, 8))
        ctk.CTkLabel(hdr, text=title, font=ctk.CTkFont(size=20, weight="bold"),
                     text_color="#79c0ff").pack(anchor="w")
        ctk.CTkLabel(hdr, text=description, font=ctk.CTkFont(size=11),
                     text_color="#8b949e").pack(anchor="w")

    def make_card(self, parent, title=None, **kwargs):
        card = ctk.CTkFrame(parent, fg_color="#161b22", corner_radius=8, **kwargs)
        if title:
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12, weight="bold"),
                         text_color="#79c0ff").pack(anchor="w", padx=14, pady=(12, 4))
        return card

    def make_output(self, parent, height=None):
        wrap = ctk.CTkFrame(parent, fg_color="#161b22", corner_radius=8)
        wrap.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        sb = ctk.CTkScrollbar(wrap)
        sb.pack(side="right", fill="y", padx=(0, 2), pady=2)
        out = OutputText(wrap, yscrollcommand=sb.set)
        out.pack(fill="both", expand=True, padx=2, pady=2)
        sb.configure(command=out.yview)
        return out

    def make_stat_bar(self, parent, metrics):
        bar = ctk.CTkFrame(parent, fg_color="#161b22", corner_radius=8)
        bar.pack(fill="x", padx=20, pady=(0, 8))
        for label, attr in metrics:
            sf = ctk.CTkFrame(bar, fg_color="transparent")
            sf.pack(side="left", expand=True, padx=6, pady=8)
            ctk.CTkLabel(sf, text=label, text_color="#8b949e",
                         font=ctk.CTkFont(size=10)).pack()
            v = ctk.CTkLabel(sf, text="—", text_color="#f0883e",
                             font=ctk.CTkFont(size=13, weight="bold"))
            v.pack()
            setattr(self, attr, v)
        return bar

    def make_btn_row(self, parent, start_cmd, stop_cmd, clear_cmd=None,
                     start_text="▶  Start", fill=False):
        """Create Start / Stop / Clear button row.
        fill=True: buttons stretch to fill the parent (use inside fixed-width panels).
        fill=False: buttons use fixed widths packed left (use in wide control rows).
        """
        row = ctk.CTkFrame(parent, fg_color="transparent")
        if fill:
            # Responsive grid: [Start][Stop] on row 0, [Clear] full-width on row 1
            row.grid_columnconfigure(0, weight=1)
            row.grid_columnconfigure(1, weight=1)
            self.start_btn = ctk.CTkButton(row, text=start_text, command=start_cmd,
                                           fg_color="#238636", hover_color="#2ea043", width=0)
            self.start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 3), pady=(0, 4))
            self.stop_btn = ctk.CTkButton(row, text="⏹  Stop", command=stop_cmd,
                                          fg_color="#da3633", hover_color="#f85149",
                                          width=0, state="disabled")
            self.stop_btn.grid(row=0, column=1, sticky="ew", padx=(3, 0), pady=(0, 4))
            if clear_cmd:
                ctk.CTkButton(row, text="🗑  Clear", command=clear_cmd,
                              fg_color="#21262d", hover_color="#30363d",
                              width=0).grid(row=1, column=0, columnspan=2, sticky="ew")
        else:
            self.start_btn = ctk.CTkButton(row, text=start_text, command=start_cmd,
                                           fg_color="#238636", hover_color="#2ea043", width=120)
            self.start_btn.pack(side="left", padx=(0, 6))
            self.stop_btn = ctk.CTkButton(row, text="⏹  Stop", command=stop_cmd,
                                          fg_color="#da3633", hover_color="#f85149",
                                          width=100, state="disabled")
            self.stop_btn.pack(side="left", padx=(0, 6))
            if clear_cmd:
                ctk.CTkButton(row, text="🗑  Clear", command=clear_cmd,
                              fg_color="#21262d", hover_color="#30363d",
                              width=90).pack(side="left")
        return row

    def q(self, text, tag="normal"):
        self.output_queue.put((text, tag))

    def drain_queue(self):
        try:
            while True:
                item = self.output_queue.get_nowait()
                if item and hasattr(self, "output"):
                    self.output.append(item[0], item[1])
        except queue.Empty:
            pass

    def poll(self):
        self.drain_queue()
        if self.running:
            self.after(60, self.poll)
        else:
            self.after(300, self.drain_queue)

    def start_poll(self):
        self.after(60, self.poll)

    def stop_op(self):
        self.running = False
        self.stop_event.set()

    def ui_done(self):
        self.running = False
        if hasattr(self, "start_btn"):
            self.start_btn.configure(state="normal")
        if hasattr(self, "stop_btn"):
            self.stop_btn.configure(state="disabled")

    def ui_started(self):
        self.running = True
        self.stop_event.clear()
        if hasattr(self, "start_btn"):
            self.start_btn.configure(state="disabled")
        if hasattr(self, "stop_btn"):
            self.stop_btn.configure(state="normal")

    def export_output(self, tool_name="output"):
        """Export current output text to a file via save dialog."""
        content = self.output.get("1.0", "end-1c")
        if not content.strip():
            messagebox.showinfo("Export", "Nothing to export.")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text file", "*.txt"), ("All files", "*.*")],
            initialfile=f"{tool_name}_{ts}",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.output.append(f"\n\u2714 Exported to {path}", "success")
        except Exception as e:
            self.output.append(f"\n\u2716 Export failed: {e}", "error")

    def _save_favorite_dialog(self, fav_type, value):
        """Open a small dialog to name and save a favorite."""
        if not value.strip():
            messagebox.showinfo("Favorite", "No value to save.")
            return
        dlg = ctk.CTkToplevel(self)
        dlg.title("Save Favorite")
        dlg.geometry("350x180")
        dlg.resizable(False, False)
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        ctk.CTkLabel(dlg, text=f"Save as {fav_type}",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#79c0ff").pack(pady=(16, 4))
        ctk.CTkLabel(dlg, text=value, text_color="#8b949e",
                     wraplength=300).pack(pady=(0, 8))

        name_var = tk.StringVar(value=value[:40])
        ctk.CTkEntry(dlg, textvariable=name_var,
                     placeholder_text="Name this favorite",
                     width=280).pack(pady=(0, 12))

        def do_save():
            n = name_var.get().strip() or value[:40]
            FavoritesManager.add(n, fav_type, value)
            dlg.destroy()
            if hasattr(self, "output"):
                self.output.append(f"\u2b50 Saved favorite: {n}", "success")

        ctk.CTkButton(dlg, text="\u2b50  Save", command=do_save,
                      fg_color="#238636", hover_color="#2ea043",
                      width=120).pack()

    def _attach_entry_context_menu(self, widget):
        """Attach a dark-themed edit context menu to a Tk/CustomTkinter entry widget."""
        target = getattr(widget, "_entry", widget)
        menu = tk.Menu(
            target,
            tearoff=0,
            bg="#1e1e1e",
            fg="#e6edf3",
            activebackground="#30363d",
            activeforeground="#ffffff",
            bd=1,
            relief="solid",
            font=("Consolas", 10),
        )

        def action(sequence):
            try:
                target.event_generate(sequence)
            except tk.TclError:
                pass

        def select_all():
            try:
                target.select_range(0, "end")
                target.icursor("end")
            except tk.TclError:
                pass

        menu.add_command(label="Cut", command=lambda: action("<<Cut>>"))
        menu.add_command(label="Copy", command=lambda: action("<<Copy>>"))
        menu.add_command(label="Paste", command=lambda: action("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Select All", command=select_all)

        def popup(event):
            try:
                target.focus_set()
                menu.unpost()
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                try:
                    menu.grab_release()
                except tk.TclError:
                    pass
            return "break"

        def close_menu(_event=None):
            try:
                menu.unpost()
            except tk.TclError:
                pass

        menu.bind("<FocusOut>", close_menu, add="+")
        target.winfo_toplevel().bind_all("<Button-1>", close_menu, add="+")
        target.winfo_toplevel().bind_all("<Escape>", close_menu, add="+")

        for bind_target in {widget, target}:
            bind_target.bind("<Button-3>", popup, add="+")
            bind_target.bind("<Control-Button-1>", popup, add="+")
        return widget

    def _safe_after(self, ms, func):
        """Schedule func on the main thread; silently drop if widget is gone or loop not running."""
        try:
            self.after(ms, func)
        except (RuntimeError, tk.TclError):
            pass


# ==================== Ping Tool ====================
class PingFrame(BaseToolFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()

    def _build(self):
        self.make_header("🏓  Ping Tool",
                         "Send ICMP echo requests with fully customizable parameters")

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True)

        # ── Left controls ──────────────────────────────────────────────────────
        left = self.make_card(content, title="Configuration", width=290)
        left.pack(side="left", fill="y", padx=(20, 8), pady=(0, 20))
        left.pack_propagate(False)

        def lbl(txt): ctk.CTkLabel(left, text=txt, text_color="#8b949e",
                                   font=ctk.CTkFont(size=11)).pack(anchor="w", padx=14, pady=(6, 0))

        lbl("Target Host / IP")
        self.target_var = tk.StringVar(value="8.8.8.8")
        ctk.CTkEntry(left, textvariable=self.target_var,
                     placeholder_text="hostname or IP").pack(fill="x", padx=14, pady=(2, 0))

        lbl("Packet Count  (0 = continuous)")
        self.count_var = tk.IntVar(value=4)
        ctk.CTkEntry(left, textvariable=self.count_var).pack(fill="x", padx=14, pady=(2, 0))

        lbl("Packet Size (bytes)")
        self.size_var = tk.IntVar(value=32)
        self._size_lbl = ctk.CTkLabel(left, text="32 B", text_color="#f0883e",
                                      font=ctk.CTkFont(size=11))
        self._size_lbl.pack(anchor="w", padx=14)
        sz_sl = ctk.CTkSlider(left, from_=1, to=65500, variable=self.size_var,
                              command=lambda v: self._size_lbl.configure(text=f"{int(v)} B"))
        sz_sl.pack(fill="x", padx=14)
        ctk.CTkEntry(left, textvariable=self.size_var).pack(fill="x", padx=14, pady=(2, 0))

        lbl("TTL")
        self.ttl_var = tk.IntVar(value=128)
        ctk.CTkEntry(left, textvariable=self.ttl_var).pack(fill="x", padx=14, pady=(2, 0))

        lbl("Timeout (ms)")
        self.timeout_var = tk.IntVar(value=1000)
        ctk.CTkEntry(left, textvariable=self.timeout_var).pack(fill="x", padx=14, pady=(2, 0))

        lbl("Interval (ms)")
        self.interval_var = tk.IntVar(value=1000)
        ctk.CTkEntry(left, textvariable=self.interval_var).pack(fill="x", padx=14, pady=(2, 0))

        self.df_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(left, text="Don't Fragment (DF bit)", variable=self.df_var,
                        text_color="#c9d1d9").pack(anchor="w", padx=14, pady=(8, 0))

        row = self.make_btn_row(left, self._start, self.stop_op,
                                clear_cmd=lambda: self.output.clear(), fill=True)
        row.pack(fill="x", padx=14, pady=(14, 14))
        ctk.CTkButton(row, text="\U0001f4be  Export",
                      command=lambda: self.export_output("Ping"),
                      fg_color="#21262d", hover_color="#30363d",
                      width=0).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        ctk.CTkButton(row, text="\u2b50  Save Target",
                      command=lambda: self._save_favorite_dialog("Host", self.target_var.get().strip()),
                      fg_color="#21262d", hover_color="#30363d",
                      width=0).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        # ── Right panel ────────────────────────────────────────────────────────
        right = ctk.CTkFrame(content, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True, padx=(0, 20), pady=(0, 20))

        self.make_stat_bar(right, [
            ("Sent", "s_sent"), ("Received", "s_recv"), ("Lost", "s_lost"),
            ("Loss %", "s_loss"), ("Min ms", "s_min"), ("Avg ms", "s_avg"), ("Max ms", "s_max"),
        ])

        self.output = self.make_output(right)
        self._stats = {}

    def _start(self):
        if self.running:
            return
        t = self.target_var.get().strip()
        if not t:
            messagebox.showwarning("Input", "Enter a target host.")
            return
        self.ui_started()
        self._stats = {"sent": 0, "recv": 0, "rtts": []}
        self._stats_lock = threading.Lock()
        self.output.clear()
        self.output.append(f"Pinging {t}  size={self.size_var.get()}B  TTL={self.ttl_var.get()}  "
                           f"timeout={self.timeout_var.get()}ms  interval={self.interval_var.get()}ms", "header")
        self.output.append(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", "dim")
        self.start_poll()
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        target = self.target_var.get().strip()
        count = self.count_var.get()
        size = self.size_var.get()
        ttl = self.ttl_var.get()
        timeout = self.timeout_var.get()
        interval = self.interval_var.get()
        df = self.df_var.get()
        continuous = (count == 0)
        sent = 0

        while self.running and (continuous or sent < count):
            if self.stop_event.is_set():
                break
            cmd = _pu_net.ping_once_command(target, timeout_ms=timeout,
                                            size=size, ttl=ttl, df=df)
            sent += 1
            with self._stats_lock:
                self._stats["sent"] = sent
            try:
                res = subprocess.run(cmd, capture_output=True, text=True,
                                     timeout=timeout / 1000 + 2,
                                     creationflags=SUBPROCESS_FLAGS)
                out = res.stdout
                if "TTL=" in out or "ttl=" in out.lower():
                    m = re.search(r"time[=<](\d+)", out, re.IGNORECASE)
                    rtt = int(m.group(1)) if m else 0
                    with self._stats_lock:
                        self._stats["rtts"].append(rtt)
                        self._stats["recv"] = self._stats.get("recv", 0) + 1
                    tag = "success" if rtt < 50 else "warning" if rtt < 200 else "error"
                    self.q(f"Reply from {target}: bytes={size}  time={rtt}ms  TTL={ttl}", tag)
                else:
                    self.q(f"Request timed out  (seq {sent})", "error")
            except Exception as e:
                self.q(f"Error: {e}", "error")

            self.after(0, self._update_stats)
            if self.running and not self.stop_event.is_set():
                time.sleep(max(0, interval / 1000))

        self._print_summary(target)
        with self._stats_lock:
            _sent = self._stats["sent"]
            _recv = self._stats.get("recv", 0)
        _loss = f"{(_sent - _recv) / _sent * 100:.0f}%" if _sent else "0%"
        SessionHistory.log("Ping", f"Ping {target}", f"Sent: {_sent}, Recv: {_recv}, Loss: {_loss}")
        self.after(0, self.ui_done)

    def _update_stats(self):
        with self._stats_lock:
            sent = self._stats["sent"]
            recv = self._stats.get("recv", 0)
            rtts = list(self._stats.get("rtts", []))
        lost = sent - recv
        pct = f"{lost / sent * 100:.1f}%" if sent else "0%"
        self.s_sent.configure(text=str(sent))
        self.s_recv.configure(text=str(recv), text_color="#3fb950" if recv else "#8b949e")
        self.s_lost.configure(text=str(lost), text_color="#f85149" if lost else "#3fb950")
        self.s_loss.configure(text=pct, text_color="#f85149" if lost else "#3fb950")
        if rtts:
            self.s_min.configure(text=str(min(rtts)))
            self.s_avg.configure(text=str(sum(rtts) // len(rtts)))
            self.s_max.configure(text=str(max(rtts)))

    def _print_summary(self, target):
        with self._stats_lock:
            sent = self._stats["sent"]
            recv = self._stats.get("recv", 0)
            rtts = list(self._stats.get("rtts", []))
        lost = sent - recv
        self.q(f"\n{'─'*55}", "dim")
        self.q(f"Ping statistics for {target}", "header")
        self.q(f"  Packets: Sent={sent}  Received={recv}  Lost={lost}  "
               f"({lost / sent * 100:.1f}% loss)" if sent else "  No packets sent.", "info")
        if rtts:
            self.q(f"  RTT: Min={min(rtts)}ms  Avg={sum(rtts)//len(rtts)}ms  Max={max(rtts)}ms", "info")


# ==================== Port Scanner ====================
class PortScanFrame(BaseToolFrame):
    # ── Scan profiles ──
    _PROFILES = {
        "Quick Scan":    [22, 80, 443, 445, 554, 3389],
        "Web Scan":      [80, 443, 8080, 8443],
        "Camera Scan":   [80, 554, 8080, 8554],
        "Common Ports":  None,   # uses COMMON_PORTS keys
        "Full (1-1024)": None,   # range 1-1024
        "Custom":        None,   # user-defined
    }

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._results = []    # list of dicts for copy/export
        self._build()

    def _build(self):
        self.make_header("🔍  Port Scanner", "Scan TCP/UDP ports with service fingerprinting")

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True)

        # ── Left controls ──────────────────────────────────────────────────────
        left = self.make_card(content, title="Configuration", width=290)
        left.pack(side="left", fill="y", padx=(20, 8), pady=(0, 20))
        left.pack_propagate(False)

        def lbl(t): ctk.CTkLabel(left, text=t, text_color="#8b949e",
                                  font=ctk.CTkFont(size=11)).pack(anchor="w", padx=14, pady=(6, 0))

        lbl("Target Host / IP")
        self.target_var = tk.StringVar(value="192.168.1.1")
        ctk.CTkEntry(left, textvariable=self.target_var).pack(fill="x", padx=14, pady=(2, 0))

        # ── Profile selector ──
        lbl("Scan Profile")
        self._profile_var = tk.StringVar(value="Quick Scan")
        ctk.CTkOptionMenu(
            left, variable=self._profile_var,
            values=list(self._PROFILES.keys()),
            command=self._on_profile_change,
            fg_color="#21262d", button_color="#30363d", button_hover_color="#484f58",
        ).pack(fill="x", padx=14, pady=(2, 0))

        self._profile_desc = ctk.CTkLabel(left, text="Ports: 22, 80, 443, 445, 554, 3389",
                                          text_color="#58a6ff", font=ctk.CTkFont(size=10),
                                          wraplength=250)
        self._profile_desc.pack(anchor="w", padx=14, pady=(2, 0))

        # ── Custom options (hidden by default, shown for Custom/Full) ──
        self._custom_frm = ctk.CTkFrame(left, fg_color="transparent")

        lbl_c = ctk.CTkLabel(self._custom_frm, text="Scan Mode", text_color="#8b949e",
                              font=ctk.CTkFont(size=11))
        lbl_c.pack(anchor="w", padx=0, pady=(4, 0))
        self.mode_var = tk.StringVar(value="common")
        for ltext, val in [("Common Ports (top 40)", "common"),
                           ("Port Range", "range"),
                           ("Single Port", "single"),
                           ("All Ports  1–65535  (slow)", "all")]:
            ctk.CTkRadioButton(self._custom_frm, text=ltext, variable=self.mode_var,
                               value=val, command=self._update_mode).pack(anchor="w", padx=10, pady=1)

        self._range_frm = ctk.CTkFrame(self._custom_frm, fg_color="transparent")
        ctk.CTkLabel(self._range_frm, text="Start Port", text_color="#8b949e",
                     font=ctk.CTkFont(size=11)).pack(anchor="w")
        self.start_port = tk.IntVar(value=1)
        ctk.CTkEntry(self._range_frm, textvariable=self.start_port).pack(fill="x", pady=(2, 4))
        ctk.CTkLabel(self._range_frm, text="End Port", text_color="#8b949e",
                     font=ctk.CTkFont(size=11)).pack(anchor="w")
        self.end_port = tk.IntVar(value=1024)
        ctk.CTkEntry(self._range_frm, textvariable=self.end_port).pack(fill="x", pady=(2, 0))

        self._single_frm = ctk.CTkFrame(self._custom_frm, fg_color="transparent")
        ctk.CTkLabel(self._single_frm, text="Port", text_color="#8b949e",
                     font=ctk.CTkFont(size=11)).pack(anchor="w")
        self.single_port = tk.IntVar(value=80)
        ctk.CTkEntry(self._single_frm, textvariable=self.single_port).pack(fill="x", pady=(2, 0))

        lbl("Protocol")
        self.proto_var = tk.StringVar(value="TCP")
        pf = ctk.CTkFrame(left, fg_color="transparent")
        pf.pack(anchor="w", padx=14)
        for p in ["TCP", "UDP", "Both"]:
            ctk.CTkRadioButton(pf, text=p, variable=self.proto_var, value=p).pack(side="left", padx=4)

        lbl("Timeout (ms)")
        self.timeout_var = tk.IntVar(value=500)
        ctk.CTkEntry(left, textvariable=self.timeout_var).pack(fill="x", padx=14, pady=(2, 0))

        lbl("Threads")
        self.threads_var = tk.IntVar(value=150)
        ctk.CTkEntry(left, textvariable=self.threads_var).pack(fill="x", padx=14, pady=(2, 0))

        self.open_only_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(left, text="Show open ports only", variable=self.open_only_var,
                        text_color="#c9d1d9").pack(anchor="w", padx=14, pady=(8, 0))

        self.fingerprint_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(left, text="Service fingerprinting", variable=self.fingerprint_var,
                        text_color="#c9d1d9").pack(anchor="w", padx=14, pady=(4, 0))

        row = self.make_btn_row(left, self._start, self.stop_op,
                                clear_cmd=self._clear_results,
                                start_text="▶  Scan", fill=True)
        row.pack(fill="x", padx=14, pady=(10, 4))

        ctk.CTkButton(left, text="\U0001f4cb  Copy Results", command=self._copy_results,
                      fg_color="#21262d", hover_color="#30363d",
                      width=0).pack(fill="x", padx=14, pady=(2, 0))
        ctk.CTkButton(left, text="\U0001f4be  Export", command=lambda: self.export_output("PortScan"),
                      fg_color="#21262d", hover_color="#30363d",
                      width=0).pack(fill="x", padx=14, pady=(2, 0))
        ctk.CTkButton(left, text="\u2b50  Save Target",
                      command=lambda: self._save_favorite_dialog("Host", self.target_var.get().strip()),
                      fg_color="#21262d", hover_color="#30363d",
                      width=0).pack(fill="x", padx=14, pady=(2, 14))

        # ── Right ──────────────────────────────────────────────────────────────
        right = ctk.CTkFrame(content, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True, padx=(0, 20), pady=(0, 20))

        pf2 = ctk.CTkFrame(right, fg_color="transparent")
        pf2.pack(fill="x", pady=(0, 6))
        self._prog_lbl = ctk.CTkLabel(pf2, text="Ready", text_color="#8b949e")
        self._prog_lbl.pack(anchor="w")
        self._prog_bar = ctk.CTkProgressBar(pf2)
        self._prog_bar.set(0)
        self._prog_bar.pack(fill="x")

        self.make_stat_bar(right, [("Scanned", "s_scanned"), ("Open", "s_open"),
                                   ("Closed", "s_closed"), ("Filtered", "s_filtered")])
        self.output = self.make_output(right)

    # ── Profile handling ──

    def _on_profile_change(self, choice):
        profile = self._profile_var.get()
        ports = self._PROFILES.get(profile)
        self._custom_frm.pack_forget()
        if profile == "Custom":
            self._custom_frm.pack(fill="x", padx=14, pady=(4, 0))
            self._profile_desc.configure(text="Custom scan — configure below")
        elif profile == "Full (1-1024)":
            self._profile_desc.configure(text="Ports: 1–1024 (well-known range)")
        elif profile == "Common Ports":
            self._profile_desc.configure(text=f"Top {len(COMMON_PORTS)} common service ports")
        elif ports:
            self._profile_desc.configure(text=f"Ports: {', '.join(str(p) for p in ports)}")

    def _update_mode(self):
        mode = self.mode_var.get()
        self._range_frm.pack_forget()
        self._single_frm.pack_forget()
        if mode == "range":
            self._range_frm.pack(fill="x", padx=0, pady=(4, 0))
        elif mode == "single":
            self._single_frm.pack(fill="x", padx=0, pady=(4, 0))

    def _get_ports(self):
        profile = self._profile_var.get()
        fixed = self._PROFILES.get(profile)
        if fixed is not None:
            return list(fixed)
        if profile == "Common Ports":
            return list(COMMON_PORTS.keys())
        if profile == "Full (1-1024)":
            return list(range(1, 1025))
        # Custom
        m = self.mode_var.get()
        if m == "common":   return list(COMMON_PORTS.keys())
        if m == "range":    return list(range(self.start_port.get(), self.end_port.get() + 1))
        if m == "single":   return [self.single_port.get()]
        return list(range(1, 65536))

    # ── Service fingerprinting ──

    @staticmethod
    def _fingerprint(host, port, timeout_s=1.5):
        """Lightweight service fingerprint for an open port. Returns (service, detail)."""
        svc_name = COMMON_PORTS.get(port, "")
        detail = ""
        try:
            if port in (80, 8080, 8000, 8888, 81):
                return PortScanFrame._fp_http(host, port, timeout_s)
            if port in (443, 8443):
                return PortScanFrame._fp_https(host, port, timeout_s)
            if port == 554 or port == 8554:
                return PortScanFrame._fp_rtsp(host, port, timeout_s)
            if port == 22:
                return PortScanFrame._fp_banner(host, port, timeout_s, "SSH")
            if port == 21:
                return PortScanFrame._fp_banner(host, port, timeout_s, "FTP")
            if port == 25 or port == 587:
                return PortScanFrame._fp_banner(host, port, timeout_s, "SMTP")
            if port == 445:
                return "SMB", "Windows file sharing"
            if port == 3389:
                return "RDP", "Remote Desktop"
            if port == 3306:
                return PortScanFrame._fp_banner(host, port, timeout_s, "MySQL")
            if port == 5432:
                return "PostgreSQL", ""
            if port == 5900:
                return PortScanFrame._fp_banner(host, port, timeout_s, "VNC")
        except Exception:
            pass
        return svc_name or "Open", detail

    @staticmethod
    def _fp_http(host, port, timeout_s):
        """Probe HTTP and extract Server header + page title."""
        try:
            import urllib.request as _ur
            req = _ur.Request(f"http://{host}:{port}/",
                              headers={"User-Agent": "Mozilla/5.0"})
            with _ur.urlopen(req, timeout=timeout_s) as resp:
                server = resp.headers.get("Server", "").strip()
                body = resp.read(4096).decode("utf-8", errors="replace")
                title = ""
                m = re.search(r"<title[^>]*>([^<]{1,80})</title>", body, re.I)
                if m:
                    title = m.group(1).strip()
                parts = []
                if server:
                    parts.append(server)
                if title:
                    parts.append(f'"{title}"')
                return "HTTP", " — ".join(parts) if parts else ""
        except Exception:
            return "HTTP", ""

    @staticmethod
    def _fp_https(host, port, timeout_s):
        """Probe HTTPS and extract Server header."""
        try:
            import urllib.request as _ur
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = _ur.Request(f"https://{host}:{port}/",
                              headers={"User-Agent": "Mozilla/5.0"})
            with _ur.urlopen(req, timeout=timeout_s, context=ctx) as resp:
                server = resp.headers.get("Server", "").strip()
                return "HTTPS", server
        except Exception:
            return "HTTPS", ""

    @staticmethod
    def _fp_rtsp(host, port, timeout_s):
        """Send RTSP OPTIONS and extract server header."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout_s)
                s.connect((host, port))
                s.sendall(f"OPTIONS rtsp://{host}:{port}/ RTSP/1.0\r\nCSeq: 1\r\n\r\n".encode())
                banner = s.recv(512).decode("utf-8", errors="replace")
                if "RTSP/1" in banner:
                    server = ""
                    for line in banner.splitlines():
                        if line.lower().startswith("server:"):
                            server = line.split(":", 1)[1].strip()
                            break
                    return "RTSP", server
                return "RTSP?", "port open but no RTSP response"
        except Exception:
            return "RTSP?", ""

    @staticmethod
    def _fp_banner(host, port, timeout_s, label):
        """Generic: connect and read first banner line."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout_s)
                s.connect((host, port))
                banner = s.recv(256).decode("utf-8", errors="replace").strip()
                # Take first non-empty line, truncate
                for line in banner.splitlines():
                    line = line.strip()
                    if line:
                        return label, line[:120]
                return label, ""
        except Exception:
            return label, ""

    # ── Scan logic ──

    def _clear_results(self):
        self.output.clear()
        self._results.clear()

    def _start(self):
        if self.running:
            return
        t = self.target_var.get().strip()
        if not t:
            messagebox.showwarning("Input", "Enter a target.")
            return
        ports = self._get_ports()
        if len(ports) > 10000 and not messagebox.askyesno(
                "Large Scan", f"Scanning {len(ports):,} ports. Continue?"):
            return
        self.ui_started()
        self._clear_results()
        self._prog_bar.set(0)
        self._scan_stats = {"scanned": 0, "open": 0, "closed": 0, "filtered": 0}
        self._total = len(ports)
        profile = self._profile_var.get()
        fp_on = self.fingerprint_var.get()
        self.output.append(
            f"Scanning {t}  —  {len(ports):,} ports  |  "
            f"{self.proto_var.get()}  |  Profile: {profile}  |  "
            f"Fingerprint: {'on' if fp_on else 'off'}",
            "header",
        )
        self.output.append(
            f"{'PORT':<8} {'STATE':<11} {'SERVICE':<14} DETAILS", "header",
        )
        self.output.append("─" * 65, "dim")
        self.start_poll()
        threading.Thread(target=self._worker, args=(t, ports), daemon=True).start()

    def _tcp_scan(self, host, port, to_ms):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(to_ms / 1000)
                r = s.connect_ex((host, port))
                return "open" if r == 0 else "closed"
        except socket.timeout:
            return "filtered"
        except Exception:
            return "filtered"

    def _udp_scan(self, host, port, to_ms):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(to_ms / 1000)
                s.sendto(b"\x00", (host, port))
                s.recvfrom(1024)
            return "open"
        except socket.timeout:
            return "open|filtered"
        except ConnectionRefusedError:
            return "closed"
        except Exception:
            return "filtered"

    def _scan_one(self, host, port, proto, to_ms, do_fp):
        if self.stop_event.is_set():
            return port, "cancelled", proto, "", ""
        if proto == "TCP":
            state = self._tcp_scan(host, port, to_ms)
        elif proto == "UDP":
            state = self._udp_scan(host, port, to_ms)
        else:
            tcp = self._tcp_scan(host, port, to_ms)
            udp = self._udp_scan(host, port, to_ms)
            state = "open" if "open" in tcp or "open" in udp else tcp
            proto = f"TCP:{tcp}/UDP:{udp}"

        svc, detail = "", ""
        is_open = "open" in str(state).lower()
        if is_open and do_fp:
            try:
                svc, detail = self._fingerprint(host, port, timeout_s=min(to_ms / 1000, 2.0))
            except Exception:
                svc = COMMON_PORTS.get(port, "")
        elif is_open:
            svc = COMMON_PORTS.get(port, "")
        return port, state, proto, svc, detail

    def _worker(self, host, ports):
        to_ms = self.timeout_var.get()
        proto = self.proto_var.get()
        n_threads = min(self.threads_var.get(), 500)
        open_only = self.open_only_var.get()
        do_fp = self.fingerprint_var.get()
        done = 0

        with ThreadPoolExecutor(max_workers=n_threads) as ex:
            futs = {ex.submit(self._scan_one, host, p, proto, to_ms, do_fp): p for p in ports}
            for fut in as_completed(futs):
                if self.stop_event.is_set():
                    break
                try:
                    port, state, p_label, svc, detail = fut.result()
                    done += 1
                    self._scan_stats["scanned"] = done
                    is_open = "open" in str(state).lower()
                    if is_open:
                        self._scan_stats["open"] += 1
                        svc_display = svc or COMMON_PORTS.get(port, "—")
                        detail_short = detail[:60] if detail else ""
                        self.q(
                            f"{port:<8} {'OPEN':<11} {svc_display:<14} {detail_short}",
                            "success",
                        )
                        self._results.append({
                            "port": port, "proto": p_label, "state": "OPEN",
                            "service": svc_display, "detail": detail,
                        })
                    elif "filter" in str(state).lower():
                        self._scan_stats["filtered"] += 1
                        if not open_only:
                            self.q(f"{port:<8} {'FILTERED':<11}", "warning")
                    else:
                        self._scan_stats["closed"] += 1
                        if not open_only:
                            self.q(f"{port:<8} {'CLOSED':<11}", "dim")
                    pct = done / self._total
                    self.after(0, lambda p=pct, d=done: (
                        self._prog_bar.set(p),
                        self._prog_lbl.configure(text=f"Scanning {d}/{self._total}"),
                        self.s_scanned.configure(text=str(self._scan_stats["scanned"])),
                        self.s_open.configure(text=str(self._scan_stats["open"]), text_color="#3fb950"),
                        self.s_closed.configure(text=str(self._scan_stats["closed"])),
                        self.s_filtered.configure(text=str(self._scan_stats["filtered"]), text_color="#d29922"),
                    ))
                except Exception:
                    done += 1

        # Summary
        ss = self._scan_stats
        self.q(f"\n{'─'*65}", "dim")
        self.q(f"Scan complete — Open: {ss['open']}  Closed: {ss['closed']}  Filtered: {ss['filtered']}", "header")

        # Show fingerprint detail for open ports
        if self._results and do_fp:
            self.q(f"\n{'─'*65}", "dim")
            self.q("Service Details:", "header")
            for r in sorted(self._results, key=lambda x: x["port"]):
                if r["detail"]:
                    self.q(f"  {r['port']:<6} {r['service']:<14} {r['detail']}", "info")

        SessionHistory.log("Port Scanner", f"Scan {host}",
                          f"Open: {ss['open']}, Closed: {ss['closed']}, Filtered: {ss['filtered']}")
        self.after(0, lambda: (self.ui_done(), self._prog_bar.set(1),
                               self._prog_lbl.configure(text="Scan complete")))

    def _copy_results(self):
        if not self._results:
            return
        lines = [f"Port Scan Results — {self.target_var.get()}",
                 f"{'PORT':<8} {'STATE':<11} {'SERVICE':<14} DETAILS", "─" * 65]
        for r in sorted(self._results, key=lambda x: x["port"]):
            lines.append(f"{r['port']:<8} {r['state']:<11} {r['service']:<14} {r['detail']}")
        self.clipboard_clear()
        self.clipboard_append("\n".join(lines))
        self.q("Results copied to clipboard.", "success")


# ==================== Stress Test ====================
class StressTestFrame(BaseToolFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()

    def _build(self):
        self.make_header("⚡  Stress Test", "Network stress & load testing tool")

        warn = ctk.CTkFrame(self, fg_color="#3d1f00", corner_radius=8)
        warn.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(warn,
                     text="⚠  WARNING: Only use on networks you own or have explicit written permission to test.",
                     text_color="#d29922", font=ctk.CTkFont(size=11)).pack(padx=12, pady=8)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True)

        left = self.make_card(content, title="Configuration", width=290)
        left.pack(side="left", fill="y", padx=(20, 8), pady=(0, 20))
        left.pack_propagate(False)

        def lbl(t): ctk.CTkLabel(left, text=t, text_color="#8b949e",
                                  font=ctk.CTkFont(size=11)).pack(anchor="w", padx=14, pady=(6, 0))

        lbl("Target Host / IP")
        self.target_var = tk.StringVar(value="192.168.1.1")
        ctk.CTkEntry(left, textvariable=self.target_var).pack(fill="x", padx=14, pady=(2, 0))

        lbl("Test Type")
        self.type_var = tk.StringVar(value="ping_flood")
        for lt, val in [("Ping Flood (ICMP)", "ping_flood"),
                        ("TCP SYN Connect", "tcp_connect"),
                        ("UDP Flood", "udp_flood")]:
            ctk.CTkRadioButton(left, text=lt, variable=self.type_var, value=val,
                               command=self._update_type).pack(anchor="w", padx=24, pady=1)

        self._tcp_frm = ctk.CTkFrame(left, fg_color="transparent")
        ctk.CTkLabel(self._tcp_frm, text="Target Port", text_color="#8b949e",
                     font=ctk.CTkFont(size=11)).pack(anchor="w")
        self.tcp_port_var = tk.IntVar(value=80)
        ctk.CTkEntry(self._tcp_frm, textvariable=self.tcp_port_var).pack(fill="x")

        lbl("Packet Size (bytes)")
        self.size_var = tk.IntVar(value=64)
        self._size_lbl = ctk.CTkLabel(left, text="64 B", text_color="#f0883e", font=ctk.CTkFont(size=11))
        self._size_lbl.pack(anchor="w", padx=14)
        ctk.CTkSlider(left, from_=1, to=65500, variable=self.size_var,
                      command=lambda v: self._size_lbl.configure(text=f"{int(v)} B")
                      ).pack(fill="x", padx=14)

        lbl("Concurrent Threads")
        self.threads_var = tk.IntVar(value=10)
        self._thr_lbl = ctk.CTkLabel(left, text="10", text_color="#f0883e", font=ctk.CTkFont(size=11))
        self._thr_lbl.pack(anchor="w", padx=14)
        ctk.CTkSlider(left, from_=1, to=200, variable=self.threads_var,
                      command=lambda v: self._thr_lbl.configure(text=str(int(v)))
                      ).pack(fill="x", padx=14)

        lbl("Duration (s)  — 0 = unlimited")
        self.dur_var = tk.IntVar(value=30)
        ctk.CTkEntry(left, textvariable=self.dur_var).pack(fill="x", padx=14, pady=(2, 0))

        lbl("Rate Limit (pkt/s per thread, 0 = max)")
        self.rate_var = tk.IntVar(value=100)
        ctk.CTkEntry(left, textvariable=self.rate_var).pack(fill="x", padx=14, pady=(2, 0))

        row = self.make_btn_row(left, self._start, self.stop_op,
                                clear_cmd=lambda: self.output.clear(),
                                start_text="⚡  Launch Test", fill=True)
        self.start_btn.configure(fg_color="#da3633", hover_color="#f85149")
        row.pack(fill="x", padx=14, pady=(14, 14))

        right = ctk.CTkFrame(content, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True, padx=(0, 20), pady=(0, 20))

        self.make_stat_bar(right, [("Sent", "s_sent"), ("Success", "s_succ"),
                                   ("Failed", "s_fail"), ("Pkt/s", "s_rate"),
                                   ("Elapsed", "s_time"), ("MB Sent", "s_mb")])
        self.output = self.make_output(right)

    def _update_type(self):
        if self.type_var.get() == "tcp_connect":
            self._tcp_frm.pack(fill="x", padx=14, pady=(4, 0))
        else:
            self._tcp_frm.pack_forget()

    def _start(self):
        if self.running:
            return
        t = self.target_var.get().strip()
        if not t:
            messagebox.showwarning("Input", "Enter a target.")
            return
        if not messagebox.askyesno("Confirm",
                                   f"Start stress test against {t}?\n\n"
                                   "You must have permission to test this target."):
            return
        self.ui_started()
        self.output.clear()
        self._ss = {"sent": 0, "succ": 0, "fail": 0, "bytes": 0, "t0": time.time()}
        self.output.append(f"Stress test  →  {t}", "header")
        nthreads = int(self.threads_var.get())
        self.output.append(f"Type: {self.type_var.get()}  "
                           f"Threads: {nthreads}  "
                           f"Size: {self.size_var.get()}B  "
                           f"Duration: {self.dur_var.get()}s", "dim")
        self._active_workers = nthreads
        self._worker_lock = threading.Lock()
        self._ss_lock = threading.Lock()
        self.start_poll()
        for _ in range(nthreads):
            threading.Thread(target=self._stress_worker, daemon=True).start()
        threading.Thread(target=self._monitor, daemon=True).start()

    def _stress_worker(self):
        target = self.target_var.get().strip()
        ttype = self.type_var.get()
        size = self.size_var.get()
        rate = self.rate_var.get()
        dur = self.dur_var.get()
        t0 = time.time()

        while self.running and not self.stop_event.is_set():
            if dur > 0 and (time.time() - t0) >= dur:
                break
            if rate > 0:
                time.sleep(1.0 / rate)
            try:
                ok = False
                if ttype == "ping_flood":
                    r = subprocess.run(
                        _pu_net.ping_once_command(target, timeout_ms=200, size=size),
                        capture_output=True, timeout=2,
                        creationflags=SUBPROCESS_FLAGS)
                    ok = r.returncode == 0
                elif ttype == "tcp_connect":
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(0.5)
                        ok = s.connect_ex((target, self.tcp_port_var.get())) == 0
                elif ttype == "udp_flood":
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                        s.sendto(bytes(size), (target, 9))
                    ok = True
                with self._ss_lock:
                    self._ss["sent"] += 1
                    self._ss["bytes"] += size
                    if ok:
                        self._ss["succ"] += 1
                    else:
                        self._ss["fail"] += 1
            except Exception:
                with self._ss_lock:
                    self._ss["sent"] += 1
                    self._ss["fail"] += 1

        with self._worker_lock:
            self._active_workers -= 1
            if self._active_workers == 0:
                self.running = False
                self.after(0, self._finish)

    def _monitor(self):
        last_sent, last_t = 0, time.time()
        while self.running:
            time.sleep(1)
            now = time.time()
            with self._ss_lock:
                cur = self._ss["sent"]
                elapsed = now - self._ss["t0"]
                mb = self._ss["bytes"] / (1024 * 1024)
                succ = self._ss["succ"]
                fail = self._ss["fail"]
            rate = (cur - last_sent) / max(now - last_t, 0.001)
            last_sent, last_t = cur, now
            self.after(0, lambda r=rate, e=elapsed, m=mb, sn=cur, sk=succ, fl=fail: (
                self.s_rate.configure(text=f"{r:.0f}"),
                self.s_time.configure(text=f"{e:.0f}s"),
                self.s_mb.configure(text=f"{m:.1f}"),
                self.s_sent.configure(text=str(sn)),
                self.s_succ.configure(text=str(sk), text_color="#3fb950"),
                self.s_fail.configure(text=str(fl),
                                      text_color="#f85149" if fl else "#c9d1d9"),
            ))
            elapsed_int = int(elapsed)
            self.q(f"[{elapsed_int:>4}s]  Sent: {cur:>8,}  Rate: {rate:>7.0f} pkt/s  "
                   f"Data: {mb:>6.1f} MB", "info")

    def _finish(self):
        self.ui_done()
        s = self._ss
        elapsed = time.time() - s["t0"]
        self.q(f"\n{'─'*55}", "dim")
        self.q(f"Stress test complete  —  {elapsed:.1f}s", "header")
        self.q(f"Sent: {s['sent']:,}  Success: {s['succ']:,}  Failed: {s['fail']:,}  "
               f"Data: {s['bytes']/(1024*1024):.2f} MB", "info")


# ==================== Traceroute ====================
class TracerouteFrame(BaseToolFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()

    def _build(self):
        self.make_header("🗺   Traceroute", "Trace the network path to any destination")

        top = self.make_card(self)
        top.pack(fill="x", padx=20, pady=(0, 10))

        row = ctk.CTkFrame(top, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=12)

        def lbl(t): return ctk.CTkLabel(row, text=t, text_color="#8b949e")

        lbl("Target").pack(side="left", padx=(0, 4))
        self.target_var = tk.StringVar(value="google.com")
        ctk.CTkEntry(row, textvariable=self.target_var).pack(side="left", padx=(0, 14), fill="x", expand=True)

        lbl("Max Hops").pack(side="left", padx=(0, 4))
        self.hops_var = tk.IntVar(value=30)
        ctk.CTkEntry(row, textvariable=self.hops_var, width=55).pack(side="left", padx=(0, 14))

        lbl("Timeout ms").pack(side="left", padx=(0, 4))
        self.timeout_var = tk.IntVar(value=1000)
        ctk.CTkEntry(row, textvariable=self.timeout_var, width=70).pack(side="left", padx=(0, 14))

        self.resolve_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(row, text="Resolve names", variable=self.resolve_var).pack(side="left", padx=(0, 14))

        r = self.make_btn_row(row, self._start, self.stop_op, start_text="▶  Trace")
        r.pack(side="left", padx=(0, 6))
        ctk.CTkButton(row, text="\U0001f5d1", command=lambda: self.output.clear(),
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="left")
        ctk.CTkButton(row, text="\U0001f4be", command=lambda: self.export_output("Traceroute"),
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="left", padx=(6, 0))
        ctk.CTkButton(row, text="\u2b50", command=lambda: self._save_favorite_dialog("Host", self.target_var.get().strip()),
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="left", padx=(6, 0))

        self.output = self.make_output(self)

    def _start(self):
        if self.running:
            return
        t = self.target_var.get().strip()
        if not t:
            messagebox.showwarning("Input", "Enter a target.")
            return
        self.ui_started()
        self.output.clear()
        self.output.append(f"Traceroute to {t}  (max {self.hops_var.get()} hops, "
                           f"{self.timeout_var.get()}ms timeout)", "header")
        self.output.append("─" * 65, "dim")
        self.start_poll()
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        t = self.target_var.get().strip()
        proc = None
        status = "Trace complete"
        try:
            cmd = _pu_net.traceroute_command(
                t, max_hops=self.hops_var.get(),
                timeout_ms=self.timeout_var.get(),
                resolve=self.resolve_var.get(),
            )
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, creationflags=SUBPROCESS_FLAGS)
            for line in proc.stdout:
                if self.stop_event.is_set():
                    proc.terminate()
                    break
                line = line.rstrip()
                if not line:
                    continue
                if "*" in line and "ms" not in line:
                    self.q(line, "warning")
                elif "Trace complete" in line:
                    self.q(line, "header")
                elif "Tracing" in line or "over a maximum" in line:
                    self.q(line, "info")
                elif re.match(r"^\s*\d+", line):
                    self.q(line, "success")
                else:
                    self.q(line, "normal")
        except FileNotFoundError as e:
            self.q(str(e), "error")
            self.q("Install it with: sudo apt install traceroute", "warning")
            status = "Traceroute unavailable"
        except OSError as e:
            self.q(f"Traceroute failed to start: {e}", "error")
            status = "Traceroute failed to start"
        except Exception as e:
            self.q(f"Error: {e}", "error")
            status = "Traceroute error"
        finally:
            if proc is not None:
                try:
                    proc.terminate()
                except Exception:
                    pass
                proc.wait()
            SessionHistory.log("Traceroute", f"Trace {t}", status)
            self.after(0, self.ui_done)


# ==================== DNS Lookup ====================
class DNSFrame(BaseToolFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()

    def _build(self):
        self.make_header("🌐  DNS Lookup", "Query all DNS record types for any domain")

        top = self.make_card(self)
        top.pack(fill="x", padx=20, pady=(0, 8))
        row = ctk.CTkFrame(top, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=12)

        ctk.CTkLabel(row, text="Domain", text_color="#8b949e").pack(side="left", padx=(0, 4))
        self.domain_var = tk.StringVar(value="google.com")
        ctk.CTkEntry(row, textvariable=self.domain_var).pack(side="left", padx=(0, 14), fill="x", expand=True)

        ctk.CTkLabel(row, text="Type", text_color="#8b949e").pack(side="left", padx=(0, 4))
        self.rtype_var = tk.StringVar(value="ALL")
        ctk.CTkOptionMenu(row, values=["ALL", "A", "AAAA", "MX", "NS", "TXT",
                                       "CNAME", "SOA", "PTR", "SRV"],
                          variable=self.rtype_var, width=90).pack(side="left", padx=(0, 14))

        ctk.CTkLabel(row, text="DNS Server", text_color="#8b949e").pack(side="left", padx=(0, 4))
        self.dns_srv_var = tk.StringVar()
        ctk.CTkEntry(row, textvariable=self.dns_srv_var,
                     placeholder_text="system default", width=130).pack(side="left", padx=(0, 14))

        ctk.CTkButton(row, text="\U0001f50d  Lookup", command=self._lookup,
                      fg_color="#238636", hover_color="#2ea043", width=110).pack(side="left", padx=(0, 6))
        ctk.CTkButton(row, text="\U0001f5d1", command=lambda: self.output.clear(),
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="left")
        ctk.CTkButton(row, text="\U0001f4be", command=lambda: self.export_output("DNS"),
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="left", padx=(6, 0))

        # Quick shortcuts
        qrow = ctk.CTkFrame(self, fg_color="transparent")
        qrow.pack(fill="x", padx=20, pady=(0, 8))
        ctk.CTkLabel(qrow, text="Quick:", text_color="#8b949e",
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 8))
        for label, d in [("google.com", "google.com"), ("cloudflare.com", "cloudflare.com"),
                         ("github.com", "github.com"), ("Reverse IP", None)]:
            def cb(dom=d):
                if dom:
                    self.domain_var.set(dom)
                self._lookup()
            ctk.CTkButton(qrow, text=label, command=cb,
                          width=110, fg_color="#21262d", hover_color="#30363d",
                          font=ctk.CTkFont(size=11)).pack(side="left", padx=3)

        self.output = self.make_output(self)

    def _lookup(self):
        domain = self.domain_var.get().strip()
        if not domain:
            return
        self.output.clear()
        self.output.append(f"DNS Lookup: {domain}  [{self.rtype_var.get()}]  "
                           f"@ {datetime.now().strftime('%H:%M:%S')}", "header")
        srv = self.dns_srv_var.get().strip()
        if srv:
            self.output.append(f"Using DNS server: {srv}", "dim")
        self.output.append("─" * 55, "dim")
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        domain = self.domain_var.get().strip()
        rtype = self.rtype_var.get()
        srv = self.dns_srv_var.get().strip()

        if DNS_AVAILABLE:
            resolver = dns.resolver.Resolver()
            if srv:
                resolver.nameservers = [srv]
            types = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"] if rtype == "ALL" else [rtype]
            for t in types:
                try:
                    ans = resolver.resolve(domain, t, lifetime=5)
                    self.after(0, lambda t=t: self.output.append(f"\n[{t} Records]", "info"))
                    for rd in ans:
                        self.after(0, lambda r=str(rd): self.output.append(f"  {r}", "success"))
                except dns.resolver.NoAnswer:
                    if rtype != "ALL":
                        self.after(0, lambda t=t: self.output.append(f"No {t} records found", "warning"))
                except dns.resolver.NXDOMAIN:
                    self.after(0, lambda: self.output.append(f"NXDOMAIN — domain not found", "error"))
                    break
                except Exception as e:
                    if rtype != "ALL":
                        self.after(0, lambda e=str(e), t=t: self.output.append(f"Error [{t}]: {e}", "error"))
        else:
            # Fallback to nslookup
            cmd = ["nslookup"]
            if rtype not in ("ALL", "A"):
                cmd.append(f"-type={rtype}")
            if srv:
                cmd += [domain, srv]
            else:
                cmd.append(domain)
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=10,
                                     creationflags=SUBPROCESS_FLAGS)
                for line in (res.stdout + res.stderr).split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    if "***" in line or "can't find" in line.lower():
                        tag = "error"
                    elif "Address:" in line or "addresses:" in line.lower():
                        tag = "success"
                    elif "Server:" in line or "Name:" in line:
                        tag = "info"
                    else:
                        tag = "normal"
                    self.after(0, lambda l=line, tg=tag: self.output.append(l, tg))
            except Exception as e:
                self.after(0, lambda err=str(e): self.output.append(f"Error: {err}", "error"))

        SessionHistory.log("DNS Lookup", f"Lookup {domain}", f"Query type: {rtype}")
        self.after(0, lambda: self.output.append("\nDone.", "dim"))


# ==================== Network Scanner ====================
class NetworkScanFrame(BaseToolFrame):
    # Ports to probe for device fingerprinting (label, port)
    _PROBE_PORTS = [
        ("HTTP",   80),  ("HTTPS",  443), ("RTSP",  554),
        ("SSH",    22),  ("SMB",    445), ("RDP",   3389),
        ("HTTP-Alt", 8080), ("HTTPS-Alt", 8443),
    ]

    # Device-type classification rules: (test_func, type_label, confidence)
    # Each test_func receives the enrichment dict and returns True/False.
    _DEVICE_RULES = [
        (lambda d: d["rtsp"] and d["cam_oui"],                "Camera",  "Confirmed"),
        (lambda d: d["rtsp"] and d["cam_http"],               "Camera",  "Confirmed"),
        (lambda d: d["rtsp"] and not d["smb"] and not d["rdp"], "Camera", "Likely"),
        (lambda d: d["cam_oui"],                              "Camera",  "Possible"),
        (lambda d: d["cam_http"],                             "Camera",  "Possible"),
        (lambda d: d["is_gw"],                                "Router / Gateway", "Confirmed"),
        (lambda d: d["smb"] and d["rdp"],                     "Windows PC", "Likely"),
        (lambda d: d["rdp"] and not d["ssh"],                 "Windows PC", "Possible"),
        (lambda d: d["ssh"] and not d["smb"] and not d["rdp"], "Linux / Unix", "Likely"),
        (lambda d: d["ssh"] and d["http"],                    "Server",  "Possible"),
        (lambda d: d["http"] or d["https"],                   "Web Device", "Possible"),
    ]

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._hosts_data = []      # list of enrichment dicts
        self._selected_host = None
        self._build()

    def _build(self):
        self.make_header("📡  Network Scanner", "Discover and identify hosts on the local network")

        # ── Controls ──
        top = self.make_card(self)
        top.pack(fill="x", padx=20, pady=(0, 8))
        row = ctk.CTkFrame(top, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=12)

        ctk.CTkLabel(row, text="Network (CIDR)", text_color="#8b949e").pack(side="left", padx=(0, 4))
        default_net = get_local_network() if PSUTIL_AVAILABLE else "192.168.1.0/24"
        self.net_var = tk.StringVar(value=default_net)
        ctk.CTkEntry(row, textvariable=self.net_var).pack(side="left", padx=(0, 14), fill="x", expand=True)

        ctk.CTkLabel(row, text="Threads", text_color="#8b949e").pack(side="left", padx=(0, 4))
        self.threads_var = tk.IntVar(value=80)
        ctk.CTkEntry(row, textvariable=self.threads_var, width=60).pack(side="left", padx=(0, 14))

        ctk.CTkLabel(row, text="Timeout ms", text_color="#8b949e").pack(side="left", padx=(0, 4))
        self.timeout_var = tk.IntVar(value=500)
        ctk.CTkEntry(row, textvariable=self.timeout_var, width=65).pack(side="left", padx=(0, 14))

        self.resolve_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(row, text="Resolve hostnames", variable=self.resolve_var).pack(side="left", padx=(0, 14))

        r = self.make_btn_row(row, self._start, self.stop_op, start_text="\u25b6  Scan")
        r.pack(side="left", padx=(0, 6))
        ctk.CTkButton(row, text="\U0001f5d1", command=self._clear_all,
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="left")
        ctk.CTkButton(row, text="\U0001f4be", command=lambda: self.export_output("NetScanner"),
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="left", padx=(6, 0))
        ctk.CTkButton(row, text="\u2b50", command=lambda: self._save_favorite_dialog("Host", self.net_var.get().strip()),
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="left", padx=(6, 0))

        # ── Progress ──
        pf = ctk.CTkFrame(self, fg_color="transparent")
        pf.pack(fill="x", padx=20, pady=(0, 6))
        self._prog_lbl = ctk.CTkLabel(pf, text="Ready", text_color="#8b949e")
        self._prog_lbl.pack(anchor="w")
        self._prog_bar = ctk.CTkProgressBar(pf)
        self._prog_bar.set(0)
        self._prog_bar.pack(fill="x")

        self._found_lbl = ctk.CTkLabel(self, text="Hosts discovered: 0",
                                       font=ctk.CTkFont(size=12, weight="bold"),
                                       text_color="#3fb950")
        self._found_lbl.pack(anchor="w", padx=20, pady=(4, 0))

        # ── Split pane: Treeview (left) + Detail (right) ──
        split = ctk.CTkFrame(self, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=20, pady=(4, 20))
        split.grid_columnconfigure(0, weight=3)
        split.grid_columnconfigure(1, weight=2)
        split.grid_rowconfigure(0, weight=1)

        # Left: Treeview
        tree_frame = ctk.CTkFrame(split, fg_color="#161b22", corner_radius=8)
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        style = tk.ttk.Style()
        style.theme_use("default")
        style.configure("Netscan.Treeview",
                        background="#0d1117", foreground="#c9d1d9",
                        fieldbackground="#0d1117", rowheight=24,
                        font=("Consolas", 10), borderwidth=0)
        style.configure("Netscan.Treeview.Heading",
                        background="#21262d", foreground="#79c0ff",
                        font=("Segoe UI", 10, "bold"), relief="flat")
        style.map("Netscan.Treeview",
                  background=[("selected", "#1f6feb")],
                  foreground=[("selected", "#ffffff")])

        cols = ("ip", "hostname", "mac", "vendor", "device", "ports")
        self._tree = tk.ttk.Treeview(tree_frame, columns=cols, show="headings",
                                     style="Netscan.Treeview", selectmode="browse")
        for cid, hdr, w in [
            ("ip", "IP Address", 120), ("hostname", "Hostname", 140),
            ("mac", "MAC", 130), ("vendor", "Vendor", 100),
            ("device", "Device Type", 130), ("ports", "Open Ports", 140),
        ]:
            self._tree.heading(cid, text=hdr)
            self._tree.column(cid, width=w, minwidth=60)

        self._tree.tag_configure("camera",  foreground="#3fb950")
        self._tree.tag_configure("server",  foreground="#58a6ff")
        self._tree.tag_configure("router",  foreground="#d29922")
        self._tree.tag_configure("windows", foreground="#bc8cff")
        self._tree.tag_configure("linux",   foreground="#58a6ff")
        self._tree.tag_configure("web",     foreground="#79c0ff")
        self._tree.tag_configure("unknown", foreground="#8b949e")

        tsb = ctk.CTkScrollbar(tree_frame, command=self._tree.yview)
        self._tree.configure(yscrollcommand=tsb.set)
        tsb.pack(side="right", fill="y", padx=(0, 2), pady=2)
        self._tree.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)
        self._tree.bind("<<TreeviewSelect>>", self._on_host_select)

        # Right: Detail panel
        detail_wrap = ctk.CTkFrame(split, fg_color="#161b22", corner_radius=8)
        detail_wrap.grid(row=0, column=1, sticky="nsew")
        dsb = ctk.CTkScrollbar(detail_wrap)
        dsb.pack(side="right", fill="y", padx=(0, 2), pady=2)
        self.output = OutputText(detail_wrap, yscrollcommand=dsb.set)
        self.output.pack(fill="both", expand=True, padx=2, pady=2)
        dsb.configure(command=self.output.yview)

    def _clear_all(self):
        self._tree.delete(*self._tree.get_children())
        self._hosts_data.clear()
        self._selected_host = None
        self.output.clear()
        self._found_lbl.configure(text="Hosts discovered: 0")
        self._prog_bar.set(0)
        self._prog_lbl.configure(text="Ready")

    # ── Scan start ──

    def _start(self):
        if self.running:
            return
        try:
            net = ipaddress.IPv4Network(self.net_var.get().strip(), strict=False)
        except ValueError as e:
            messagebox.showwarning("Input", f"Invalid network: {e}")
            return
        hosts = list(net.hosts())
        if len(hosts) > 1024 and not messagebox.askyesno(
                "Large Scan", f"Scanning {len(hosts):,} hosts — continue?"):
            return
        self.ui_started()
        self._clear_all()
        self._found = 0
        self._total = len(hosts)
        self.start_poll()
        threading.Thread(target=self._worker, args=(hosts,), daemon=True).start()

    # ── Ping ──

    def _ping_host(self, ip, to_ms):
        cmd = _pu_net.ping_once_command(str(ip), timeout_ms=to_ms)
        t0 = time.time()
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=to_ms / 1000 + 1,
                               creationflags=SUBPROCESS_FLAGS)
            rtt = (time.time() - t0) * 1000
            return r.returncode == 0, rtt
        except Exception:
            return False, -1

    # ── Port probe ──

    @staticmethod
    def _probe_ports(ip, timeout_ms=400):
        """Quick TCP connect probe on common ports. Returns dict of label->bool."""
        result = {}
        for label, port in NetworkScanFrame._PROBE_PORTS:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(timeout_ms / 1000)
                    s.connect((str(ip), port))
                    result[label] = True
            except Exception:
                result[label] = False
        return result

    # ── Enrich a single host ──

    @staticmethod
    def _enrich_host(ip_str, rtt, hostname, arp_map, gateway_ip, port_result):
        """Build enrichment dict for one host."""
        mac = arp_map.get(ip_str, "")
        cam_vendor = _cam_oui_lookup(mac) if mac else ""

        # HTTP camera keyword check (lightweight: only if HTTP open)
        cam_http_vendor = ""
        if port_result.get("HTTP") or port_result.get("HTTP-Alt"):
            http_port = 80 if port_result.get("HTTP") else 8080
            try:
                import urllib.request as _ur
                req = _ur.Request(f"http://{ip_str}:{http_port}/",
                                  headers={"User-Agent": "Mozilla/5.0"})
                with _ur.urlopen(req, timeout=1.5) as resp:
                    text = resp.read(2048).decode("utf-8", errors="replace").lower()
                    server = resp.headers.get("Server", "").lower()
                    combined = text + server
                    for kw, vendor in CAMERA_HTTP_KEYWORDS:
                        if kw.lower() in combined:
                            cam_http_vendor = vendor
                            break
            except Exception:
                pass

        open_ports = [lbl for lbl, ok in port_result.items() if ok]
        is_gw = (ip_str == gateway_ip)

        evidence = {
            "ip": ip_str, "rtt": rtt, "hostname": hostname,
            "mac": mac, "cam_oui": cam_vendor, "cam_http": cam_http_vendor,
            "vendor": cam_vendor or cam_http_vendor,
            "ports": port_result, "open_ports": open_ports,
            "rtsp":  port_result.get("RTSP", False),
            "http":  port_result.get("HTTP", False),
            "https": port_result.get("HTTPS", False),
            "ssh":   port_result.get("SSH", False),
            "smb":   port_result.get("SMB", False),
            "rdp":   port_result.get("RDP", False),
            "is_gw": is_gw,
        }

        # Device classification
        dev_type, dev_conf = "Unknown", ""
        for test, dtype, dconf in NetworkScanFrame._DEVICE_RULES:
            try:
                if test(evidence):
                    dev_type, dev_conf = dtype, dconf
                    break
            except Exception:
                continue

        evidence["device_type"] = dev_type
        evidence["device_conf"] = dev_conf
        return evidence

    # ── Worker ──

    def _worker(self, hosts):
        to_ms = self.timeout_var.get()
        n_thr = min(self.threads_var.get(), 256)
        resolve = self.resolve_var.get()

        # Phase 1: Discovery (ping sweep)
        self.after(0, lambda: self._prog_lbl.configure(text="Phase 1: Discovering hosts…"))
        alive_hosts = []
        done = 0

        with ThreadPoolExecutor(max_workers=n_thr) as ex:
            futs = {ex.submit(self._ping_host, ip, to_ms): ip for ip in hosts}
            for fut in as_completed(futs):
                if self.stop_event.is_set():
                    return
                ip = futs[fut]
                done += 1
                try:
                    ok, rtt = fut.result()
                    if ok:
                        alive_hosts.append((str(ip), rtt))
                except Exception:
                    pass
                pct = done / self._total * 0.5  # first 50% of progress
                self.after(0, lambda p=pct, d=done: (
                    self._prog_bar.set(p),
                    self._prog_lbl.configure(text=f"Phase 1: Ping {d}/{self._total}"),
                ))

        if self.stop_event.is_set():
            return

        self._found = len(alive_hosts)
        fc = self._found
        self.after(0, lambda c=fc: self._found_lbl.configure(text=f"Hosts discovered: {c}"))

        if not alive_hosts:
            self.q("No hosts responded.", "warning")
            self.after(0, lambda: (self.ui_done(), self._prog_bar.set(1),
                                   self._prog_lbl.configure(text="Done — 0 hosts")))
            return

        # Build ARP map
        arp_map = {}
        try:
            for a_ip, a_mac in _parse_arp_cache():
                arp_map[a_ip] = a_mac
        except Exception:
            pass

        # Detect gateway
        gateway_ip = ""
        try:
            gateway_ip = _get_default_gateway(
                get_local_ip() if not PSUTIL_AVAILABLE else get_local_ip()
            )
        except Exception:
            pass

        # Phase 2: Enrichment (port probes + classification)
        self.after(0, lambda: self._prog_lbl.configure(text="Phase 2: Enriching hosts…"))
        enrich_thr = min(n_thr, len(alive_hosts), 64)

        def _enrich_one(ip_rtt):
            ip_str, rtt = ip_rtt
            hostname = "—"
            if resolve:
                try:
                    hostname = socket.gethostbyaddr(ip_str)[0]
                except Exception:
                    pass
            port_result = self._probe_ports(ip_str, timeout_ms=min(to_ms, 600))
            return self._enrich_host(ip_str, rtt, hostname, arp_map, gateway_ip, port_result)

        enriched = []
        edone = 0
        with ThreadPoolExecutor(max_workers=enrich_thr) as ex:
            futs = {ex.submit(_enrich_one, ipr): ipr for ipr in alive_hosts}
            for fut in as_completed(futs):
                if self.stop_event.is_set():
                    return
                edone += 1
                try:
                    data = fut.result()
                    enriched.append(data)
                    # Update tree incrementally
                    self.after(0, lambda d=data: self._add_tree_row(d))
                except Exception:
                    pass
                pct = 0.5 + (edone / len(alive_hosts)) * 0.5
                self.after(0, lambda p=pct, d=edone, t=len(alive_hosts): (
                    self._prog_bar.set(p),
                    self._prog_lbl.configure(text=f"Phase 2: Enriching {d}/{t}"),
                ))

        # Sort by IP
        enriched.sort(key=lambda d: tuple(int(o) for o in d["ip"].split(".")))
        self._hosts_data = enriched

        # Rebuild tree sorted
        self.after(0, self._rebuild_tree_sorted)
        fc2 = len(enriched)
        SessionHistory.log("Net Scanner", "Network scan", f"{fc2} hosts found")
        self.after(0, lambda: (self.ui_done(), self._prog_bar.set(1),
                               self._prog_lbl.configure(text=f"Done — {fc2} hosts enriched")))

    # ── Tree management ──

    def _device_tag(self, dev_type):
        t = dev_type.lower()
        if "camera" in t:   return "camera"
        if "router" in t or "gateway" in t: return "router"
        if "windows" in t:  return "windows"
        if "linux" in t or "unix" in t:    return "linux"
        if "server" in t:   return "server"
        if "web" in t:      return "web"
        return "unknown"

    def _add_tree_row(self, data):
        dev_label = data["device_type"]
        if data["device_conf"]:
            dev_label = f"{data['device_conf']}: {data['device_type']}"
        tag = self._device_tag(data["device_type"])
        ports_str = ", ".join(data["open_ports"]) if data["open_ports"] else "—"
        self._tree.insert("", "end", values=(
            data["ip"], data["hostname"],
            data["mac"] or "—", data["vendor"] or "—",
            dev_label, ports_str,
        ), tags=(tag,))

    def _rebuild_tree_sorted(self):
        self._tree.delete(*self._tree.get_children())
        for data in self._hosts_data:
            self._add_tree_row(data)
        # Select first
        children = self._tree.get_children()
        if children:
            self._tree.selection_set(children[0])
            self._tree.focus(children[0])
            self._on_host_select(None)

    # ── Detail panel ──

    def _on_host_select(self, event):
        sel = self._tree.selection()
        if not sel:
            return
        idx = self._tree.index(sel[0])
        if idx < len(self._hosts_data):
            self._selected_host = self._hosts_data[idx]
            self._show_host_detail(self._selected_host)

    def _show_host_detail(self, d):
        self.output.clear()
        ip = d["ip"]
        div = "─" * 50

        # Header
        dev_label = d["device_type"]
        if d["device_conf"]:
            dev_label = f"{d['device_type']}  ({d['device_conf']})"
        tag = self._device_tag(d["device_type"])
        header_tag = {
            "camera": "success", "router": "warning", "server": "info",
            "windows": "info", "linux": "info", "web": "info",
        }.get(tag, "normal")

        self.output.append(f"\n{div}", "dim")
        self.output.append(f" {ip}  —  {dev_label}\n{div}", "header")

        # Basic Info
        self.output.append(f"\n── Basic Info {'─'*37}", "dim")
        self.output.append(f"\n  IP:        {ip}", "normal")
        self.output.append(f"\n  Hostname:  {d['hostname']}", "normal")
        rtt_str = f"< 1 ms" if d["rtt"] < 1 else f"{d['rtt']:.0f} ms"
        self.output.append(f"\n  RTT:       {rtt_str}", "normal")
        self.output.append(f"\n  Status:    Alive", "success")

        # MAC / Vendor
        self.output.append(f"\n\n── MAC / Vendor {'─'*35}", "dim")
        if d["mac"]:
            self.output.append(f"\n  MAC:       {d['mac']}", "normal")
            if d["cam_oui"]:
                self.output.append(f"\n  Vendor:    {d['cam_oui']}  (camera OUI)", "success")
            elif d["vendor"]:
                self.output.append(f"\n  Vendor:    {d['vendor']}", "normal")
            else:
                self.output.append(f"\n  Vendor:    Unknown OUI", "dim")
        else:
            self.output.append(f"\n  MAC:       — (not in ARP cache)", "dim")

        # Open Ports & Services
        self.output.append(f"\n\n── Ports & Services {'─'*31}", "dim")
        if d["open_ports"]:
            for label in d["open_ports"]:
                port_num = dict(self._PROBE_PORTS).get(label, "?")
                svc_note = ""
                if label == "RTSP":
                    svc_note = "  → camera streaming likely"
                elif label == "SMB":
                    svc_note = "  → file sharing / Windows"
                elif label == "RDP":
                    svc_note = "  → remote desktop"
                elif label == "SSH":
                    svc_note = "  → secure shell"
                self.output.append(f"\n  ✔ {label:<10} (port {port_num}){svc_note}", "success")
        else:
            self.output.append(f"\n  No common ports responded", "dim")

        # Device Type
        self.output.append(f"\n\n── Device Classification {'─'*26}", "dim")
        self.output.append(f"\n  Type:       {d['device_type']}", header_tag)
        if d["device_conf"]:
            self.output.append(f"\n  Confidence: {d['device_conf']}", "normal")
        else:
            self.output.append(f"\n  Confidence: —", "dim")

        # Reasoning
        self.output.append(f"\n\n  Reasoning:", "dim")
        reasons = self._classification_reasons(d)
        if reasons:
            for r in reasons:
                self.output.append(f"\n    • {r}", "dim")
        else:
            self.output.append(f"\n    • No strong classification evidence", "dim")

        # Camera-specific extras
        if "camera" in d["device_type"].lower():
            self.output.append(f"\n\n── Camera Info {'─'*36}", "dim")
            if d["cam_oui"]:
                self.output.append(f"\n  OUI Vendor:  {d['cam_oui']}", "success")
            if d["cam_http"]:
                self.output.append(f"\n  HTTP Banner: {d['cam_http']}", "success")
            if d["rtsp"]:
                self.output.append(f"\n  RTSP:        Port 554 open", "success")
                rtsp_urls = build_candidate_rtsp_urls(ip)
                v = d["cam_oui"] or d["cam_http"] or ""
                if v:
                    rtsp_urls.sort(key=lambda u: (
                        0 if u["vendor"].lower() == v.lower() else 1,
                        -u["score_bonus"],
                    ))
                self.output.append(f"\n\n  Top RTSP candidates:", "dim")
                for i, entry in enumerate(rtsp_urls[:5], 1):
                    stars = "★★" if entry["score_bonus"] == 2 else "★ "
                    self.output.append(
                        f"\n    {i}. {entry['vendor'] + ' ' + stars:<14} {entry['url']}", "normal",
                    )

        self.output.append("\n", "normal")

    @staticmethod
    def _classification_reasons(d):
        reasons = []
        if d["is_gw"]:
            reasons.append("IP matches the default gateway")
        if d["cam_oui"]:
            reasons.append(f"Camera vendor OUI: {d['cam_oui']}")
        if d["cam_http"]:
            reasons.append(f"Camera keywords in HTTP response: {d['cam_http']}")
        if d["rtsp"]:
            reasons.append("RTSP port 554 open (streaming service)")
        if d["smb"] and d["rdp"]:
            reasons.append("SMB + RDP open → likely Windows PC")
        elif d["rdp"]:
            reasons.append("RDP open → likely Windows")
        if d["ssh"] and not d["smb"]:
            reasons.append("SSH open without SMB → likely Linux/Unix")
        elif d["ssh"]:
            reasons.append("SSH open")
        if d["http"] and not d["rtsp"] and not d["cam_oui"] and not d["cam_http"]:
            reasons.append("HTTP open (generic web service)")
        if d["https"]:
            reasons.append("HTTPS open")
        if not d["open_ports"]:
            reasons.append("No common ports responded — device type unclear")
        return reasons


# ==================== Netdiscover Scanner (Linux) ====================
class NetdiscoverFrame(BaseToolFrame):
    """Linux netdiscover frontend backed by SystemBackend."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._backend = system_backend.get_backend()
        self._supported = "netdiscover" in self._backend.available_tools()
        self._seen_macs = set()
        self._hosts_data = []
        self._tree_items = {}
        self._build()

    def _build(self):
        (self._build_full if self._supported else self._build_unsupported)()

    def _build_unsupported(self):
        self.make_header("📡  Netdiscover", "Advanced network discovery — ikke tilgjengelig på denne plattformen")
        card = self.make_card(self)
        card.pack(fill="x", padx=20, pady=20)
        msg_lines = [
            "Netdiscover er en Linux-funksjon som krever at pakken er installert.", "",
            "På Ubuntu/Debian:", "    sudo apt install netdiscover", "",
            "Standard Network Scanner-fanen fungerer på alle plattformer",
            "og gir lignende enhets-deteksjon via ping + port-probing.",
        ]
        ctk.CTkLabel(
            card, text="\n".join(msg_lines), text_color="#8b949e",
            justify="left", font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=16, pady=16)

    def _build_full(self):
        self.make_header(
            "📡  Netdiscover",
            "Advanced network discovery (Linux) — deeper device visibility than standard ARP scanning",
        )
        top = self.make_card(self)
        top.pack(fill="x", padx=20, pady=(0, 8))
        row = ctk.CTkFrame(top, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(row, text="Interface", text_color="#8b949e").pack(side="left", padx=(0, 4))
        iface_options = self._detect_interfaces()
        self.iface_var = tk.StringVar(value=iface_options[0] if iface_options else "auto")
        self.iface_menu = ctk.CTkOptionMenu(row, variable=self.iface_var, values=iface_options or ["auto"], width=130)
        self.iface_menu.pack(side="left", padx=(0, 14))
        ctk.CTkLabel(row, text="CIDR", text_color="#8b949e").pack(side="left", padx=(0, 4))
        default_net = get_local_network() if PSUTIL_AVAILABLE else "192.168.1.0/24"
        self.cidr_var = tk.StringVar(value=default_net)
        ctk.CTkEntry(row, textvariable=self.cidr_var, width=140).pack(side="left", padx=(0, 14))
        self.passive_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(row, text="Passive mode", variable=self.passive_var).pack(side="left", padx=(0, 14))
        r = self.make_btn_row(row, self._start, self.stop_op, start_text="▶  Scan")
        r.pack(side="left", padx=(0, 6))
        ctk.CTkButton(row, text="🗑", command=self._clear_all, width=40,
                      fg_color="#21262d", hover_color="#30363d").pack(side="left")
        ctk.CTkButton(row, text="💾", command=lambda: self.export_output("Netdiscover"), width=40,
                      fg_color="#21262d", hover_color="#30363d").pack(side="left", padx=(6, 0))
        pf = ctk.CTkFrame(self, fg_color="transparent")
        pf.pack(fill="x", padx=20, pady=(0, 6))
        self._prog_lbl = ctk.CTkLabel(pf, text="Ready", text_color="#8b949e")
        self._prog_lbl.pack(anchor="w")
        self._prog_bar = ctk.CTkProgressBar(pf, mode="indeterminate")
        self._prog_bar.pack(fill="x")
        self._prog_bar.set(0)
        self._found_lbl = ctk.CTkLabel(self, text="Hosts discovered: 0", text_color="#79c0ff",
                                       font=ctk.CTkFont(size=11, weight="bold"))
        self._found_lbl.pack(anchor="w", padx=24, pady=(0, 6))
        split = ctk.CTkFrame(self, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        split.grid_columnconfigure(0, weight=3)
        split.grid_columnconfigure(1, weight=2)
        split.grid_rowconfigure(0, weight=1)
        tree_frame = ctk.CTkFrame(split, fg_color="#161b22", corner_radius=8)
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        style = tk.ttk.Style()
        style.theme_use("default")
        style.configure("Netdisc.Treeview", background="#0d1117", foreground="#c9d1d9",
                        fieldbackground="#0d1117", rowheight=24, font=("Consolas", 10), borderwidth=0)
        style.configure("Netdisc.Treeview.Heading", background="#21262d", foreground="#79c0ff",
                        font=("Segoe UI", 10, "bold"), relief="flat")
        style.map("Netdisc.Treeview", background=[("selected", "#1f6feb")],
                  foreground=[("selected", "#ffffff")])
        cols = ("ip", "mac", "vendor", "count", "length")
        self._tree = tk.ttk.Treeview(tree_frame, columns=cols, show="headings",
                                     style="Netdisc.Treeview", selectmode="browse")
        for cid, hdr, w in [
            ("ip", "IP Address", 120),
            ("mac", "MAC", 140),
            ("vendor", "Vendor", 220),
            ("count", "Count", 60),
            ("length", "Length", 70),
        ]:
            self._tree.heading(cid, text=hdr)
            self._tree.column(cid, width=w, minwidth=50)

        tsb = ctk.CTkScrollbar(tree_frame, command=self._tree.yview)
        self._tree.configure(yscrollcommand=tsb.set)
        tsb.pack(side="right", fill="y", padx=(0, 2), pady=2)
        self._tree.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)
        self._tree.bind("<<TreeviewSelect>>", self._on_host_select)
        detail_wrap = ctk.CTkFrame(split, fg_color="#161b22", corner_radius=8)
        detail_wrap.grid(row=0, column=1, sticky="nsew")
        dsb = ctk.CTkScrollbar(detail_wrap)
        dsb.pack(side="right", fill="y", padx=(0, 2), pady=2)
        self.output = OutputText(detail_wrap, yscrollcommand=dsb.set)
        self.output.pack(fill="both", expand=True, padx=2, pady=2)
        dsb.configure(command=self.output.yview)
        self.output.append("Ready for netdiscover scan.", "info")

    def _detect_interfaces(self) -> list:
        if not PSUTIL_AVAILABLE:
            return ["auto"]
        try:
            names = [name for name in psutil.net_if_addrs().keys() if name not in ("lo", "lo0")]
            return ["auto"] + sorted(names) if names else ["auto"]
        except Exception:
            return ["auto"]

    def _clear_all(self):
        if hasattr(self, "_tree"):
            self._tree.delete(*self._tree.get_children())
        self._hosts_data.clear()
        self._seen_macs.clear()
        self._tree_items.clear()
        if hasattr(self, "output"):
            self.output.clear()
        if hasattr(self, "_found_lbl"):
            self._found_lbl.configure(text="Hosts discovered: 0")
        if hasattr(self, "_prog_lbl"):
            self._prog_lbl.configure(text="Ready")
        if hasattr(self, "_prog_bar"):
            try:
                self._prog_bar.stop()
            except Exception:
                pass
            self._prog_bar.set(0)

    def _on_host_select(self, event):
        sel = self._tree.selection()
        if not sel:
            return
        item = self._tree.item(sel[0])
        values = item["values"]
        if len(values) < 5:
            return
        ip, mac, vendor, count, length = values
        self.output.clear()
        self.output.append(f"Host: {ip}", "header")
        self.output.append(f"\nMAC:      {mac}", "info")
        self.output.append(f"\nVendor:   {vendor}", "info")
        self.output.append(f"\nSeen:     {count} time(s)", "info")
        self.output.append(f"\nLength:   {length} bytes", "info")

    def _start(self):
        if self.running:
            return

        iface = self.iface_var.get()
        if iface == "auto":
            iface = None
        cidr = self.cidr_var.get().strip() or None
        passive = self.passive_var.get()
        if not messagebox.askyesno(
            "Netdiscover krever privilegier",
            "Netdiscover krever root eller CAP_NET_RAW + CAP_NET_ADMIN capabilities.\n\n"
            "Hvis appen ikke har dette, vil scan feile med en melding.\n\n"
            "Fortsett?",
        ):
            return
        self._clear_all()
        self.ui_started()
        self._prog_lbl.configure(text=f"Scanning {'(passive)' if passive else '(active)'}...")
        try:
            self._prog_bar.start()
        except Exception:
            self._prog_bar.set(0.2)
        self.start_poll()
        threading.Thread(target=self._worker, args=(iface, cidr, passive), daemon=True).start()

    def _worker(self, iface, cidr, passive):
        try:
            for line, tag in self._backend.run_netdiscover(
                self.stop_event,
                interface=iface,
                cidr=cidr,
                passive=passive,
            ):
                if self.stop_event.is_set():
                    break
                if tag == "data":
                    try:
                        record = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        self.q(f"[parse error] {line}", "error")
                        continue
                    self._safe_after(0, lambda r=record: self._add_host(r))
                else:
                    self.q(line, tag)
        except NotImplementedError as e:
            self.q(f"Ikke støttet: {e}", "error")
        except Exception as e:
            self.q(f"Uventet feil: {e}", "error")
        finally:
            self._safe_after(0, self._scan_done)

    def _add_host(self, record: dict):
        mac = (record.get("mac") or "").strip()
        key = mac or (record.get("ip") or "").strip()
        if not key:
            return
        values = (
            record.get("ip", "?"),
            mac or "—",
            record.get("vendor", "") or "Unknown vendor",
            record.get("count", 0),
            record.get("length", 0),
        )
        if key in self._seen_macs:
            item_id = self._tree_items.get(key)
            if item_id:
                self._tree.item(item_id, values=values)
            for idx, existing in enumerate(self._hosts_data):
                existing_key = (existing.get("mac") or "").strip() or (existing.get("ip") or "").strip()
                if existing_key == key:
                    self._hosts_data[idx] = record
                    break
            return

        self._seen_macs.add(key)
        self._hosts_data.append(record)
        item_id = self._tree.insert("", "end", values=values)
        self._tree_items[key] = item_id
        self._found_lbl.configure(text=f"Hosts discovered: {len(self._seen_macs)}")

    def _scan_done(self):
        stopped = self.stop_event.is_set()
        self.ui_done()
        try:
            self._prog_bar.stop()
        except Exception:
            pass
        self._prog_bar.set(0 if stopped else 1)
        status = "Stopped" if stopped else "Done"
        self._prog_lbl.configure(text=f"{status} — {len(self._seen_macs)} hosts")


# ==================== Subnet Calculator ====================
class SubnetFrame(BaseToolFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()

    def _build(self):
        self.make_header("🧮  Subnet Calculator", "Calculate all subnet information offline — no network needed")

        top = self.make_card(self)
        top.pack(fill="x", padx=20, pady=(0, 10))
        row = ctk.CTkFrame(top, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=12)

        ctk.CTkLabel(row, text="IP / CIDR", text_color="#8b949e").pack(side="left", padx=(0, 4))
        self.cidr_var = tk.StringVar(value="192.168.1.0/24")
        ctk.CTkEntry(row, textvariable=self.cidr_var).pack(side="left", padx=(0, 14), fill="x", expand=True)

        ctk.CTkLabel(row, text="— or —", text_color="#8b949e",
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 14))
        ctk.CTkLabel(row, text="Subnet Mask", text_color="#8b949e").pack(side="left", padx=(0, 4))
        self.mask_var = tk.StringVar(value="255.255.255.0")
        ctk.CTkEntry(row, textvariable=self.mask_var, width=140).pack(side="left", padx=(0, 14))

        ctk.CTkButton(row, text="Calculate", command=self._calc,
                      fg_color="#238636", hover_color="#2ea043", width=100).pack(side="left", padx=(0, 6))
        ctk.CTkButton(row, text="🗑  Clear", command=lambda: self.output.clear(),
                      fg_color="#21262d", hover_color="#30363d", width=90).pack(side="left")

        # Quick presets
        qrow = ctk.CTkFrame(self, fg_color="transparent")
        qrow.pack(fill="x", padx=20, pady=(0, 8))
        ctk.CTkLabel(qrow, text="Presets:", text_color="#8b949e",
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 8))
        for label, cidr in [("/8 Class A", "10.0.0.0/8"), ("/16 Class B", "172.16.0.0/16"),
                             ("/24 Class C", "192.168.1.0/24"), ("/30 P2P", "10.0.0.0/30"),
                             ("/32 Host", "10.0.0.1/32")]:
            def cb(c=cidr):
                self.cidr_var.set(c)
                self.mask_var.set("")
                self._calc()
            ctk.CTkButton(qrow, text=label, command=cb, width=105,
                          fg_color="#21262d", hover_color="#30363d",
                          font=ctk.CTkFont(size=11)).pack(side="left", padx=3)

        self.output = self.make_output(self)
        self._calc()  # Show default result

    def _calc(self):
        cidr_str = self.cidr_var.get().strip()
        mask_str = self.mask_var.get().strip()

        # Build input
        if "/" not in cidr_str and mask_str:
            cidr_str = f"{cidr_str}/{mask_str}"

        try:
            net = ipaddress.IPv4Network(cidr_str, strict=False)
            ip = ipaddress.IPv4Address(cidr_str.split("/")[0])
        except ValueError as e:
            messagebox.showwarning("Input", f"Invalid address: {e}")
            return

        prefix = net.prefixlen
        hosts = net.num_addresses - 2 if prefix < 31 else net.num_addresses
        bcast = net.broadcast_address
        first = net.network_address + (0 if prefix >= 31 else 1)
        last  = net.broadcast_address - (0 if prefix >= 31 else 1)
        wildcard = ipaddress.IPv4Address(int(net.hostmask))
        ip_type = "Private" if ip.is_private else ("Loopback" if ip.is_loopback else "Public")

        # Classify
        if ip in ipaddress.IPv4Network("10.0.0.0/8"):
            cls = "Class A (RFC 1918)"
        elif ip in ipaddress.IPv4Network("172.16.0.0/12"):
            cls = "Class B (RFC 1918)"
        elif ip in ipaddress.IPv4Network("192.168.0.0/16"):
            cls = "Class C (RFC 1918)"
        elif ip in ipaddress.IPv4Network("169.254.0.0/16"):
            cls = "APIPA (Link-local)"
        elif ip in ipaddress.IPv4Network("127.0.0.0/8"):
            cls = "Loopback"
        else:
            cls = "Public / Global"

        self.output.clear()
        rows = [
            ("Input IP",         str(ip)),
            ("Network Address",  str(net.network_address)),
            ("Broadcast",        str(bcast)),
            ("First Host",       str(first)),
            ("Last Host",        str(last)),
            ("Usable Hosts",     f"{hosts:,}"),
            ("Subnet Mask",      str(net.netmask)),
            ("CIDR Prefix",      f"/{prefix}"),
            ("Wildcard Mask",    str(wildcard)),
            ("IP Type",          ip_type),
            ("Address Class",    cls),
            ("Total Addresses",  f"{net.num_addresses:,}"),
        ]
        self.output.append(f"Subnet Calculator — {cidr_str}", "header")
        self.output.append("─" * 55, "dim")
        for k, v in rows:
            self.output.append(f"  {k:<22} {v}", "normal" if k != "CIDR Prefix" else "highlight")

        # Binary representation
        self.output.append("\nBinary Breakdown:", "info")
        ip_bin = ".".join(f"{int(o):08b}" for o in str(ip).split("."))
        mk_bin = ".".join(f"{int(o):08b}" for o in str(net.netmask).split("."))
        self.output.append(f"  IP:   {ip_bin}", "dim")
        self.output.append(f"  Mask: {mk_bin}", "dim")


# ==================== Wake-on-LAN ====================
class WoLFrame(BaseToolFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()

    def _build(self):
        self.make_header("💡  Wake-on-LAN",
                         "Send magic packets to wake remote machines on the local network")

        card = self.make_card(self, title="Send Magic Packet")
        card.pack(fill="x", padx=20, pady=(0, 10))

        def lbl(t): ctk.CTkLabel(card, text=t, text_color="#8b949e",
                                  font=ctk.CTkFont(size=11)).pack(anchor="w", padx=14, pady=(6, 0))

        lbl("MAC Address  (formats: AA:BB:CC:DD:EE:FF  or  AA-BB-CC-DD-EE-FF)")
        self.mac_var = tk.StringVar()
        ctk.CTkEntry(card, textvariable=self.mac_var, placeholder_text="AA:BB:CC:DD:EE:FF",
                     ).pack(fill="x", padx=14, pady=(2, 0))

        lbl("Broadcast Address")
        self.bcast_var = tk.StringVar(value="255.255.255.255")
        ctk.CTkEntry(card, textvariable=self.bcast_var).pack(fill="x", padx=14, pady=(2, 0))

        lbl("Port")
        self.port_var = tk.IntVar(value=9)
        ctk.CTkEntry(card, textvariable=self.port_var).pack(fill="x", padx=14, pady=(2, 0))

        lbl("Number of Packets (1–10)")
        self.count_var = tk.IntVar(value=3)
        ctk.CTkEntry(card, textvariable=self.count_var).pack(fill="x", padx=14, pady=(2, 0))

        ctk.CTkButton(card, text="💡  Send Wake-on-LAN Packet", command=self._send,
                      fg_color="#9933cc", hover_color="#7a29a3"
                      ).pack(fill="x", padx=14, pady=(14, 14))

        # Saved devices
        dev_card = self.make_card(self, title="Quick-Access Devices")
        dev_card.pack(fill="x", padx=20, pady=(0, 10))

        self._dev_frame = ctk.CTkFrame(dev_card, fg_color="transparent")
        self._dev_frame.pack(fill="x", padx=14, pady=(0, 6))
        ctk.CTkLabel(self._dev_frame, text="(No saved devices — type a MAC and click Add below)",
                     text_color="#8b949e", font=ctk.CTkFont(size=11)).pack(anchor="w")

        add_row = ctk.CTkFrame(dev_card, fg_color="transparent")
        add_row.pack(fill="x", padx=14, pady=(0, 10))
        add_row.columnconfigure(0, weight=1)
        self._dev_name = tk.StringVar(value="My Server")
        ctk.CTkEntry(add_row, textvariable=self._dev_name, placeholder_text="Device name",
                     ).pack(side="left", padx=(0, 6), fill="x", expand=True)
        ctk.CTkButton(add_row, text="➕  Add Device", command=self._add_device,
                      fg_color="#21262d", hover_color="#30363d", width=120).pack(side="left")

        self._devices = []

        self.output = self.make_output(self)

    def _add_device(self):
        mac = self.mac_var.get().strip()
        name = self._dev_name.get().strip() or "Device"
        if not mac:
            messagebox.showwarning("Input", "Enter a MAC address first.")
            return
        self._devices.append({"name": name, "mac": mac,
                               "bcast": self.bcast_var.get(), "port": self.port_var.get()})
        # Rebuild list
        for w in self._dev_frame.winfo_children():
            w.destroy()
        for dev in self._devices:
            df = ctk.CTkFrame(self._dev_frame, fg_color="transparent")
            df.pack(fill="x", pady=1)
            ctk.CTkLabel(df, text=f"{dev['name']}  ({dev['mac']})",
                         text_color="#c9d1d9", font=ctk.CTkFont(size=11)).pack(side="left")
            ctk.CTkButton(df, text="Wake", command=lambda d=dev: self._send_dev(d),
                          width=60, fg_color="#9933cc", hover_color="#7a29a3",
                          font=ctk.CTkFont(size=11)).pack(side="right", padx=4)

    def _send_dev(self, dev):
        self.mac_var.set(dev["mac"])
        self.bcast_var.set(dev["bcast"])
        self.port_var.set(dev["port"])
        self._send()

    def _send(self):
        mac_raw = self.mac_var.get().strip()
        if not mac_raw:
            messagebox.showwarning("Input", "Enter a MAC address.")
            return
        mac_clean = re.sub(r"[:\-\.]", "", mac_raw).upper()
        if len(mac_clean) != 12 or not re.fullmatch(r"[0-9A-F]{12}", mac_clean):
            messagebox.showerror("Input", f"Invalid MAC address: {mac_raw}")
            return
        try:
            mac_bytes = bytes.fromhex(mac_clean)
            magic = b"\xff" * 6 + mac_bytes * 16
            bcast = self.bcast_var.get().strip()
            port = self.port_var.get()
            count = max(1, min(10, self.count_var.get()))
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                for i in range(count):
                    s.sendto(magic, (bcast, port))
                    time.sleep(0.05)
            self.output.append(
                f"✓  Wake-on-LAN sent  ({count}x)  →  {mac_raw}  "
                f"via {bcast}:{port}  at {datetime.now().strftime('%H:%M:%S')}", "success")
        except Exception as e:
            self.output.append(f"✗  Failed: {e}", "error")


# ==================== Network Interfaces ====================
class InterfacesFrame(BaseToolFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()

    def _build(self):
        self.make_header("🖧   Network Interfaces", "All local network adapters and their current configuration")

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(0, 8))
        ctk.CTkButton(top, text="\U0001f504  Refresh", command=self._refresh,
                      fg_color="#238636", hover_color="#2ea043", width=110).pack(side="left")
        ctk.CTkButton(top, text="\U0001f5d1  Clear", command=lambda: self.output.clear(),
                      fg_color="#21262d", hover_color="#30363d", width=90).pack(side="left", padx=8)
        ctk.CTkButton(top, text="\U0001f4be", command=lambda: self.export_output("Interfaces"),
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="left")
        self._auto_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(top, text="Auto-refresh every 5s", variable=self._auto_var,
                        command=self._toggle_auto).pack(side="left", padx=8)

        self.output = self.make_output(self)
        self._auto_job = None
        self._refresh()

    def _toggle_auto(self):
        if self._auto_var.get():
            self._auto_refresh()
        else:
            if self._auto_job:
                self.after_cancel(self._auto_job)

    def _auto_refresh(self):
        if self._auto_var.get():
            self._refresh()
            self._auto_job = self.after(5000, self._auto_refresh)

    def _refresh(self):
        self.output.clear()
        self.output.append(f"Network Interfaces — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "header")
        self.output.append("─" * 75, "dim")
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        if PSUTIL_AVAILABLE:
            self._with_psutil()
        else:
            self._with_ipconfig()

    def _with_psutil(self):
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()

        for iface, addr_list in addrs.items():
            st = stats.get(iface)
            status = "UP" if (st and st.isup) else "DOWN"
            speed = f"{st.speed} Mbps" if st and st.speed else "—"
            mtu = st.mtu if st else "—"

            tag = "success" if status == "UP" else "dim"
            self._safe_after(0, lambda i=iface, s=status, sp=speed, m=mtu, t=tag:
                             self.output.append(f"\n[{i}]  Status: {s}  Speed: {sp}  MTU: {m}", t))

            for addr in addr_list:
                if addr.family == socket.AF_INET:
                    self._safe_after(0, lambda a=addr: self.output.append(
                        f"  IPv4:    {a.address}  /  {a.netmask}", "info"))
                elif addr.family == socket.AF_INET6:
                    self._safe_after(0, lambda a=addr: self.output.append(
                        f"  IPv6:    {a.address}", "dim"))
                elif addr.family == psutil.AF_LINK:
                    self._safe_after(0, lambda a=addr: self.output.append(
                        f"  MAC:     {a.address}", "dim"))

        self._safe_after(0, lambda: self.output.append(
            f"\n{'─'*55}\nTotal interfaces: {len(addrs)}", "dim"))

    def _with_ipconfig(self):
        try:
            details = _pu_net.interface_details()
            if details is not None:
                for iface in details:
                    status = iface.get("status", "—")
                    mtu = iface.get("mtu") or "—"
                    tag = "success" if status == "UP" else ("dim" if status == "DOWN" else "normal")
                    self._safe_after(0, lambda i=iface["name"], s=status, m=mtu, t=tag:
                                     self.output.append(f"\n[{i}]  Status: {s}  Speed: —  MTU: {m}", t))
                    if iface.get("ipv4"):
                        self._safe_after(0, lambda a=iface["ipv4"], n=iface.get("netmask") or iface.get("prefix", ""):
                                         self.output.append(f"  IPv4:    {a}  /  {n}", "info"))
                    if iface.get("mac"):
                        self._safe_after(0, lambda a=iface["mac"]:
                                         self.output.append(f"  MAC:     {a}", "dim"))
                self._safe_after(0, lambda: self.output.append(
                    f"\n{'─'*55}\nTotal interfaces: {len(details)}", "dim"))
                return
            res = subprocess.run(_pu_net.ipconfig_command(),
                                 capture_output=True, text=True,
                                 creationflags=SUBPROCESS_FLAGS)
            for line in res.stdout.split("\n"):
                line = line.rstrip()
                if not line:
                    continue
                if line and line[0] not in (" ", "\t"):
                    tag = "header"
                elif "IPv4" in line or "IP Address" in line:
                    tag = "info"
                elif "MAC" in line or "Physical" in line:
                    tag = "dim"
                else:
                    tag = "normal"
                self._safe_after(0, lambda l=line, t=tag: self.output.append(l, t))
        except Exception as e:
            self._safe_after(0, lambda err=str(e): self.output.append(f"Error: {err}", "error"))


# ==================== Bandwidth Monitor ====================
class BandwidthFrame(BaseToolFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._monitor_running = False
        self._t0_io = None
        self._history_rx = [0] * 60
        self._history_tx = [0] * 60
        self._prev_io = None
        self._build()

    def _build(self):
        self.make_header("📊  Bandwidth Monitor", "Real-time network throughput per interface")

        if not PSUTIL_AVAILABLE:
            ctk.CTkLabel(self, text="psutil not installed — bandwidth monitoring unavailable.\n"
                                    "Run:  pip install psutil",
                         text_color="#f85149").pack(pady=40)
            return

        # Controls
        top = self.make_card(self)
        top.pack(fill="x", padx=20, pady=(0, 10))
        row = ctk.CTkFrame(top, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(row, text="Interface:", text_color="#8b949e").pack(side="left", padx=(0, 6))
        ifaces = ["All"] + list(psutil.net_if_stats().keys())
        self.iface_var = tk.StringVar(value="All")
        ctk.CTkOptionMenu(row, values=ifaces, variable=self.iface_var,
                          width=200).pack(side="left", padx=(0, 14))

        ctk.CTkButton(row, text="▶  Start", command=self._start_monitor,
                      fg_color="#238636", hover_color="#2ea043", width=90).pack(side="left", padx=(0, 6))
        ctk.CTkButton(row, text="⏹  Stop", command=self._stop_monitor,
                      fg_color="#da3633", hover_color="#f85149", width=80).pack(side="left")

        # Live stats
        self.make_stat_bar(self, [("↓ RX Rate", "bw_rx"), ("↑ TX Rate", "bw_tx"),
                                  ("Total ↓ RX", "bw_total_rx"), ("Total ↑ TX", "bw_total_tx"),
                                  ("Pkts RX", "bw_pkts_rx"), ("Pkts TX", "bw_pkts_tx")])

        # Canvas graph
        graph_card = self.make_card(self, title="Throughput History (60s)")
        graph_card.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self._canvas = tk.Canvas(graph_card, bg="#0d1117", highlightthickness=0)
        self._canvas.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self._canvas.bind("<Configure>", lambda e: self._draw_graph())

    def _start_monitor(self):
        if self._monitor_running:
            return
        self._monitor_running = True
        self._history_rx = [0] * 60
        self._history_tx = [0] * 60
        self._prev_io = None
        self._t0_io = None
        self._monitor_loop()

    def _stop_monitor(self):
        self._monitor_running = False

    def _monitor_loop(self):
        if not self._monitor_running:
            return
        iface = self.iface_var.get()
        try:
            if iface == "All":
                io = psutil.net_io_counters()
                rx_b, tx_b = io.bytes_recv, io.bytes_sent
                pkts_rx, pkts_tx = io.packets_recv, io.packets_sent
            else:
                ios = psutil.net_io_counters(pernic=True)
                io = ios.get(iface)
                if io:
                    rx_b, tx_b = io.bytes_recv, io.bytes_sent
                    pkts_rx, pkts_tx = io.packets_recv, io.packets_sent
                else:
                    rx_b = tx_b = pkts_rx = pkts_tx = 0

            now = time.time()
            if self._prev_io and self._t0_io:
                dt = now - self._t0_io
                if dt > 0:
                    rx_rate = (rx_b - self._prev_io[0]) / dt
                    tx_rate = (tx_b - self._prev_io[1]) / dt
                    self._history_rx = self._history_rx[1:] + [rx_rate]
                    self._history_tx = self._history_tx[1:] + [tx_rate]

                    self.bw_rx.configure(text=format_bytes_rate(rx_rate))
                    self.bw_tx.configure(text=format_bytes_rate(tx_rate))
                    self.bw_total_rx.configure(text=format_bytes_total(rx_b))
                    self.bw_total_tx.configure(text=format_bytes_total(tx_b))
                    self.bw_pkts_rx.configure(text=f"{pkts_rx:,}")
                    self.bw_pkts_tx.configure(text=f"{pkts_tx:,}")
                    self._draw_graph()

            self._prev_io = (rx_b, tx_b)
            self._t0_io = now

        except Exception:
            pass

        self.after(1000, self._monitor_loop)

    def _draw_graph(self):
        c = self._canvas
        c.delete("all")
        W = c.winfo_width()
        H = c.winfo_height()
        if W < 10 or H < 10:
            return

        pad_l, pad_r, pad_t, pad_b = 65, 14, 14, 30
        gw = W - pad_l - pad_r
        gh = H - pad_t - pad_b
        if gw < 10 or gh < 10:
            return

        # Background grid
        c.create_rectangle(pad_l, pad_t, pad_l + gw, pad_t + gh, fill="#0d1117", outline="#30363d")
        for i in range(1, 4):
            y = pad_t + gh * i // 4
            c.create_line(pad_l, y, pad_l + gw, y, fill="#21262d", dash=(3, 4))

        all_vals = self._history_rx + self._history_tx
        max_val = max(max(all_vals), 1)

        def draw_line(history, color):
            pts = []
            n = len(history)
            for i, v in enumerate(history):
                x = pad_l + gw * i / max(n - 1, 1)
                y = pad_t + gh - (gh * v / max_val)
                pts.extend([x, y])
            if len(pts) >= 4:
                c.create_line(*pts, fill=color, width=2, smooth=True)

        draw_line(self._history_rx, "#3fb950")   # green = download
        draw_line(self._history_tx, "#58a6ff")   # blue  = upload

        # Y-axis labels
        for i in range(5):
            val = max_val * (4 - i) / 4
            y = pad_t + gh * i / 4
            c.create_text(pad_l - 4, y, text=format_bytes_rate(val),
                          anchor="e", fill="#8b949e", font=("Consolas", 8))

        # X labels
        c.create_text(pad_l, pad_t + gh + 14, text="60s ago", anchor="w",
                      fill="#8b949e", font=("Consolas", 8))
        c.create_text(pad_l + gw, pad_t + gh + 14, text="now", anchor="e",
                      fill="#8b949e", font=("Consolas", 8))

        # Legend
        c.create_rectangle(pad_l + 4, pad_t + 4, pad_l + 14, pad_t + 14, fill="#3fb950", outline="")
        c.create_text(pad_l + 18, pad_t + 9, text="↓ Download", anchor="w",
                      fill="#3fb950", font=("Consolas", 9))
        c.create_rectangle(pad_l + 110, pad_t + 4, pad_l + 120, pad_t + 14, fill="#58a6ff", outline="")
        c.create_text(pad_l + 124, pad_t + 9, text="↑ Upload", anchor="w",
                      fill="#58a6ff", font=("Consolas", 9))


# ==================== Active Connections ====================
class ConnectionsFrame(BaseToolFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()

    def _build(self):
        self.make_header("🔗  Active Connections", "View active TCP/UDP connections (netstat)")

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(0, 8))

        ctk.CTkButton(top, text="🔄  Refresh", command=self._refresh,
                      fg_color="#238636", hover_color="#2ea043", width=110).pack(side="left")

        ctk.CTkLabel(top, text="Filter:", text_color="#8b949e").pack(side="left", padx=(12, 4))
        self.filter_var = tk.StringVar(value="All")
        ctk.CTkOptionMenu(top, values=["All", "ESTABLISHED", "LISTEN", "TIME_WAIT",
                                       "CLOSE_WAIT", "UDP"],
                          variable=self.filter_var, width=130).pack(side="left", padx=(0, 12))

        self._auto_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(top, text="Auto-refresh 3s", variable=self._auto_var,
                        command=self._toggle_auto).pack(side="left")

        ctk.CTkButton(top, text="\U0001f5d1", command=lambda: self.output.clear(),
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="right")
        ctk.CTkButton(top, text="\U0001f4be", command=lambda: self.export_output("Connections"),
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="right", padx=(0, 6))

        self.output = self.make_output(self)
        self._job = None
        self._refresh()

    def _toggle_auto(self):
        if self._auto_var.get():
            self._auto_refresh()
        elif self._job:
            self.after_cancel(self._job)

    def _auto_refresh(self):
        if self._auto_var.get():
            self._refresh()
            self._job = self.after(3000, self._auto_refresh)

    def _refresh(self):
        self.output.clear()
        filt = self.filter_var.get()
        threading.Thread(target=self._worker, args=(filt,), daemon=True).start()

    def _worker(self, filt):
        self._safe_after(0, lambda: self.output.append(
            f"Active connections — {datetime.now().strftime('%H:%M:%S')}  "
            f"[filter: {filt}]", "header"))
        self._safe_after(0, lambda: self.output.append(
            f"{'Proto':<7} {'Local Address':<28} {'Remote Address':<28} {'State':<16} {'PID'}", "header"))
        self._safe_after(0, lambda: self.output.append("─" * 90, "dim"))

        if PSUTIL_AVAILABLE:
            conns = psutil.net_connections(kind="inet")
            count = 0
            for c in sorted(conns, key=lambda x: str(x.status)):
                proto = "TCP" if c.type == socket.SOCK_STREAM else "UDP"
                state = c.status if c.status else "—"
                if filt not in ("All", proto) and filt != state:
                    continue
                la = f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "—"
                ra = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "—"
                pid = str(c.pid) if c.pid else "—"
                count += 1

                if state == "ESTABLISHED":
                    tag = "success"
                elif state == "LISTEN":
                    tag = "info"
                elif state in ("TIME_WAIT", "CLOSE_WAIT"):
                    tag = "warning"
                else:
                    tag = "normal"

                line = f"{proto:<7} {la:<28} {ra:<28} {state:<16} {pid}"
                self._safe_after(0, lambda l=line, t=tag: self.output.append(l, t))

            self._safe_after(0, lambda: self.output.append(
                f"\n{count} connection(s) shown", "dim"))
        else:
            try:
                rows = _pu_net.connection_details()
                if rows is not None:
                    count = 0
                    for c in rows:
                        proto = c.get("proto", "").upper()
                        state = c.get("state") or "—"
                        if filt not in ("All", proto) and filt != state:
                            continue
                        la = f"{c.get('local_address') or '—'}:{c.get('local_port') or '—'}"
                        ra = f"{c.get('remote_address') or '—'}:{c.get('remote_port') or '—'}"
                        pid = str(c.get("pid")) if c.get("pid") is not None else "—"
                        count += 1

                        if state == "ESTABLISHED":
                            tag = "success"
                        elif state == "LISTEN":
                            tag = "info"
                        elif state in ("TIME_WAIT", "CLOSE_WAIT"):
                            tag = "warning"
                        else:
                            tag = "normal"

                        line = f"{proto:<7} {la:<28} {ra:<28} {state:<16} {pid}"
                        self._safe_after(0, lambda l=line, t=tag: self.output.append(l, t))
                    self._safe_after(0, lambda: self.output.append(
                        f"\n{count} connection(s) shown", "dim"))
                    return
                res = subprocess.run(_pu_net.netstat_command(),
                                     capture_output=True, text=True,
                                     timeout=10, creationflags=SUBPROCESS_FLAGS)
                for line in res.stdout.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("Active") or line.startswith("Proto"):
                        continue
                    if filt != "All" and filt not in line:
                        continue
                    if "ESTABLISHED" in line:
                        tag = "success"
                    elif "LISTENING" in line:
                        tag = "info"
                    elif "TIME_WAIT" in line or "CLOSE_WAIT" in line:
                        tag = "warning"
                    else:
                        tag = "normal"
                    self._safe_after(0, lambda l=line, t=tag: self.output.append(l, t))
            except Exception as e:
                self._safe_after(0, lambda err=str(e): self.output.append(f"Error: {err}", "error"))


# ==================== ARP Table ====================
class ARPFrame(BaseToolFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()

    def _build(self):
        self.make_header("📋  ARP Table", "View and manage the local ARP cache")

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(0, 8))

        ctk.CTkButton(top, text="🔄  Refresh", command=self._refresh,
                      fg_color="#238636", hover_color="#2ea043", width=110).pack(side="left")
        ctk.CTkButton(top, text="🗑  Clear Output", command=lambda: self.output.clear(),
                      fg_color="#21262d", hover_color="#30363d", width=120).pack(side="left", padx=8)

        # Lookup
        ctk.CTkLabel(top, text="Lookup IP:", text_color="#8b949e").pack(side="left", padx=(12, 4))
        self.lookup_var = tk.StringVar()
        ctk.CTkEntry(top, textvariable=self.lookup_var,
                     placeholder_text="192.168.1.1", width=140).pack(side="left", padx=(0, 6))
        ctk.CTkButton(top, text="Find", command=self._lookup,
                      fg_color="#21262d", hover_color="#30363d", width=60).pack(side="left")
        ctk.CTkButton(top, text="\U0001f4be", command=lambda: self.export_output("ARP"),
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="left", padx=(8, 0))

        self.output = self.make_output(self)
        self._refresh()

    def _lookup(self):
        ip = self.lookup_var.get().strip()
        if not ip:
            return
        self.output.clear()
        threading.Thread(target=self._run_arp, args=["-a", ip], daemon=True).start()

    def _refresh(self):
        self.output.clear()
        threading.Thread(target=self._run_arp, args=["-a"], daemon=True).start()

    def _run_arp(self, *args):
        self._safe_after(0, lambda: self.output.append(
            f"ARP Table — {datetime.now().strftime('%H:%M:%S')}", "header"))
        self._safe_after(0, lambda: self.output.append("─" * 70, "dim"))
        try:
            res = subprocess.run(_pu_net.arp_command(*args),
                                 capture_output=True, text=True,
                                 timeout=8, creationflags=SUBPROCESS_FLAGS)
            for line in (res.stdout + res.stderr).split("\n"):
                line = line.rstrip()
                if not line:
                    continue
                if "Interface:" in line or "interface" in line.lower():
                    tag = "header"
                elif "Internet Address" in line or "Address" in line and "Type" in line:
                    tag = "info"
                elif "static" in line.lower():
                    tag = "warning"
                elif re.search(r"\d+\.\d+\.\d+\.\d+", line):
                    tag = "success"
                else:
                    tag = "dim"
                self._safe_after(0, lambda l=line, t=tag: self.output.append(l, t))
        except Exception as e:
            self._safe_after(0, lambda err=str(e): self.output.append(f"Error: {err}", "error"))


# ==================== IP Camera Finder ====================
class CameraFinderFrame(BaseToolFrame):
    """Discover IP cameras on the local network using multiple protocols."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._cameras = {}          # ip -> info dict
        self._cam_lock = threading.Lock()
        self._stats_lock = threading.Lock()   # protects _scan_stats counters
        self._conflict_ips = set()
        self._tree_ids = {}         # ip -> treeview item id
        self._build()

    # ── UI ────────────────────────────────────────────────────────────────
    def _build(self):
        self.make_header("📷  IP Camera Finder",
                         "Discover cameras using ONVIF, SSDP, ping sweep, HTTP banner and RTSP probing")

        # Controls card
        ctrl = self.make_card(self)
        ctrl.pack(fill="x", padx=20, pady=(0, 8))

        row1 = ctk.CTkFrame(ctrl, fg_color="transparent")
        row1.pack(fill="x", padx=14, pady=(10, 4))

        ctk.CTkLabel(row1, text="Network (CIDR):", text_color="#8b949e").pack(side="left", padx=(0, 6))
        default_net = get_local_network() if PSUTIL_AVAILABLE else "192.168.1.0/24"
        self.net_var = tk.StringVar(value=default_net)
        ctk.CTkEntry(row1, textvariable=self.net_var).pack(side="left", padx=(0, 8), fill="x", expand=True)
        ctk.CTkButton(row1, text="Auto-detect", command=self._autodetect,
                      fg_color="#21262d", hover_color="#30363d", width=100).pack(side="left", padx=(0, 14))

        ctk.CTkLabel(row1, text="Timeout (ms):", text_color="#8b949e").pack(side="left", padx=(0, 4))
        self.timeout_var = tk.IntVar(value=1500)
        ctk.CTkEntry(row1, textvariable=self.timeout_var, width=70).pack(side="left", padx=(0, 14))

        ctk.CTkLabel(row1, text="Threads:", text_color="#8b949e").pack(side="left", padx=(0, 4))
        self.threads_var = tk.IntVar(value=60)
        ctk.CTkEntry(row1, textvariable=self.threads_var, width=55).pack(side="left")

        # Method checkboxes
        row2 = ctk.CTkFrame(ctrl, fg_color="transparent")
        row2.pack(fill="x", padx=14, pady=(0, 4))
        ctk.CTkLabel(row2, text="Methods:", text_color="#8b949e").pack(side="left", padx=(0, 8))
        self.use_onvif = tk.BooleanVar(value=True)
        self.use_ssdp  = tk.BooleanVar(value=True)
        self.use_ping  = tk.BooleanVar(value=True)
        self.use_http  = tk.BooleanVar(value=True)
        self.use_rtsp  = tk.BooleanVar(value=True)
        for lbl, var in [("ONVIF", self.use_onvif), ("SSDP/UPnP", self.use_ssdp),
                          ("Ping Sweep", self.use_ping), ("HTTP Banner", self.use_http),
                          ("RTSP Probe", self.use_rtsp)]:
            ctk.CTkCheckBox(row2, text=lbl, variable=var,
                            text_color="#c9d1d9", font=ctk.CTkFont(size=11)).pack(side="left", padx=8)

        # Button row
        row3 = ctk.CTkFrame(ctrl, fg_color="transparent")
        row3.pack(fill="x", padx=14, pady=(4, 12))
        r = self.make_btn_row(row3, self._start, self.stop_op, start_text="▶  Start Discovery")
        r.pack(side="left")
        ctk.CTkButton(row3, text="🗑  Clear", command=self._clear_all,
                      fg_color="#21262d", hover_color="#30363d", width=90).pack(side="left", padx=8)
        ctk.CTkButton(row3, text="\U0001f4be  Export CSV", command=self._export_csv,
                      fg_color="#21262d", hover_color="#30363d", width=110).pack(side="left")
        ctk.CTkButton(row3, text="\U0001f4be  Export Log", command=lambda: self.export_output("CameraFinder"),
                      fg_color="#21262d", hover_color="#30363d", width=110).pack(side="left", padx=(6, 0))

        # Stat bar
        self.make_stat_bar(self, [
            ("Cameras", "cf_total"), ("⚠ Conflicts", "cf_conflicts"),
            ("Scanned", "cf_scanned"), ("ONVIF", "cf_onvif"),
            ("SSDP", "cf_ssdp"), ("HTTP Match", "cf_http"),
        ])

        # Split: treeview top, detail+log bottom
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=(0, 4))

        # ── Treeview ───────────────────────────────────────────────────
        tv_card = ctk.CTkFrame(body, fg_color="#161b22", corner_radius=8)
        tv_card.pack(fill="both", expand=True, pady=(0, 6))

        style = tk.ttk.Style()
        style.theme_use("default")
        style.configure("Cam.Treeview",
                        background="#161b22", foreground="#c9d1d9",
                        fieldbackground="#161b22", rowheight=26,
                        font=("Consolas", 10), borderwidth=0)
        style.configure("Cam.Treeview.Heading",
                        background="#21262d", foreground="#79c0ff",
                        font=("Consolas", 10, "bold"), relief="flat")
        style.map("Cam.Treeview",
                  background=[("selected", "#264f78")],
                  foreground=[("selected", "#ffffff")])

        cols = ("status", "ip", "mac", "vendor", "model", "method", "ports", "url")
        self._tv = tk.ttk.Treeview(tv_card, columns=cols, show="headings",
                                    style="Cam.Treeview", selectmode="browse")
        col_cfg = [
            ("status",  "Status",       70,  False),
            ("ip",      "IP Address",   130, False),
            ("mac",     "MAC Address",  150, False),
            ("vendor",  "Vendor",       120, False),
            ("model",   "Model",        160, True),
            ("method",  "Methods",      110, False),
            ("ports",   "Open Ports",   120, False),
            ("url",     "Web / RTSP",   200, True),
        ]
        for cid, hdr, w, stretch in col_cfg:
            self._tv.heading(cid, text=hdr)
            self._tv.column(cid, width=w, stretch=stretch, anchor="w")

        vsb = ctk.CTkScrollbar(tv_card, command=self._tv.yview)
        vsb.pack(side="right", fill="y", pady=2, padx=(0, 2))
        hsb = ctk.CTkScrollbar(tv_card, command=self._tv.xview,
                               orientation="horizontal")
        hsb.pack(side="bottom", fill="x", padx=2, pady=(0, 2))
        self._tv.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tv.pack(fill="both", expand=True, padx=2, pady=(2, 0))
        self._tv.bind("<<TreeviewSelect>>", self._on_select)

        # Tag colors for conflict rows
        self._tv.tag_configure("conflict", foreground="#f85149")
        self._tv.tag_configure("camera",   foreground="#3fb950")
        self._tv.tag_configure("scanning", foreground="#d29922")

        # ── Detail panel ────────────────────────────────────────────────
        det_card = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=8)
        det_card.pack(fill="x", padx=20, pady=(0, 8))

        det_top = ctk.CTkFrame(det_card, fg_color="transparent")
        det_top.pack(fill="x", padx=8, pady=(6, 2))
        ctk.CTkLabel(det_top, text="Camera Details",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#79c0ff").pack(side="left")

        self._btn_web  = ctk.CTkButton(det_top, text="🌐 Open Web", command=self._open_web,
                                       fg_color="#21262d", hover_color="#30363d",
                                       width=110, state="disabled")
        self._btn_web.pack(side="right", padx=4)
        self._btn_copy = ctk.CTkButton(det_top, text="📋 Copy RTSP", command=self._copy_rtsp,
                                       fg_color="#21262d", hover_color="#30363d",
                                       width=110, state="disabled")
        self._btn_copy.pack(side="right", padx=4)
        self._btn_view = ctk.CTkButton(det_top, text="📺 View Stream",
                                       command=self._view_stream,
                                       fg_color="#0f3460", hover_color="#1a4a80",
                                       width=120, state="disabled")
        self._btn_view.pack(side="right", padx=4)

        det_wrap = ctk.CTkFrame(det_card, fg_color="#0d1117", corner_radius=6)
        det_wrap.pack(fill="x", padx=6, pady=(0, 6))
        det_sb = ctk.CTkScrollbar(det_wrap)
        det_sb.pack(side="right", fill="y", padx=(0, 2), pady=2)
        self._detail = OutputText(det_wrap, height=7, yscrollcommand=det_sb.set)
        self._detail.pack(fill="x", padx=2, pady=2)
        det_sb.configure(command=self._detail.yview)
        self._detail.append("Select a camera row above to see full details.", "dim")

        self._selected_ip = None

    def _autodetect(self):
        self.net_var.set(get_local_network() if PSUTIL_AVAILABLE else
                         f"{'.'.join(get_local_ip().split('.')[:3])}.0/24")

    def _clear_all(self):
        self._cameras.clear()
        self._conflict_ips.clear()
        self._tree_ids.clear()
        self._selected_ip = None
        for item in self._tv.get_children():
            self._tv.delete(item)
        self._detail.clear()
        self._detail.append("Select a camera row above to see full details.", "dim")
        for attr in ("cf_total", "cf_conflicts", "cf_scanned", "cf_onvif", "cf_ssdp", "cf_http"):
            getattr(self, attr).configure(text="—")

    # ── Discovery ─────────────────────────────────────────────────────────
    def _start(self):
        if self.running:
            return
        try:
            net = ipaddress.IPv4Network(self.net_var.get().strip(), strict=False)
        except ValueError as e:
            messagebox.showwarning("Input", f"Invalid network: {e}")
            return
        if net.num_addresses > 65536:
            messagebox.showwarning("Input", "Network too large (max /16).")
            return
        self.ui_started()
        self._clear_all()
        self._scan_stats = {"scanned": 0, "total": 0, "onvif": 0, "ssdp": 0, "http": 0}
        threading.Thread(target=self._coordinator, args=(net,), daemon=True).start()

    def _coordinator(self, net):
        hosts = list(net.hosts())
        self._scan_stats["total"] = len(hosts)
        self.after(0, lambda: self.cf_scanned.configure(text=f"0/{len(hosts)}"))

        threads_list = []

        # Fast passive discovery (multicast, fire immediately)
        if self.use_onvif.get():
            t = threading.Thread(target=self._run_onvif, daemon=True)
            t.start(); threads_list.append(t)
        if self.use_ssdp.get():
            t = threading.Thread(target=self._run_ssdp, daemon=True)
            t.start(); threads_list.append(t)

        # Active ping sweep + probing
        if self.use_ping.get() and self.running:
            self._run_ping_sweep(hosts)

        # Wait for passive threads
        for t in threads_list:
            t.join(timeout=8)

        with self._cam_lock:
            _cam_count = len(self._cameras)
        SessionHistory.log("Camera Finder", "Discovery scan", f"{_cam_count} cameras found")
        self.after(0, self.ui_done)
        self.after(0, self._finalize_conflicts)

    def _finalize_conflicts(self):
        # After all discovery, check if multiple cameras share an IP
        ip_count = {}
        with self._cam_lock:
            for ip, info in self._cameras.items():
                ip_count[ip] = ip_count.get(ip, 0) + 1

        for ip, info in list(self._cameras.items()):
            macs = info.get("all_macs", [info.get("mac", "")])
            if len(set(m for m in macs if m)) > 1:
                info["conflict"] = True
                self._conflict_ips.add(ip)

        n_conflicts = len(self._conflict_ips)
        self.after(0, lambda: (
            self.cf_conflicts.configure(
                text=str(n_conflicts),
                text_color="#f85149" if n_conflicts else "#3fb950"),
            [self._update_treeview_row(ip) for ip in self._conflict_ips],
        ))

    # ── ONVIF WS-Discovery ────────────────────────────────────────────────
    def _run_onvif(self):
        PROBE = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"'
            ' xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"'
            ' xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"'
            ' xmlns:dn="http://www.onvif.org/ver10/network/wsdl">'
            '<e:Header>'
            f'<w:MessageID>uuid:{uuid.uuid4()}</w:MessageID>'
            '<w:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>'
            '<w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>'
            '</e:Header>'
            '<e:Body><d:Probe>'
            '<d:Types>dn:NetworkVideoTransmitter</d:Types>'
            '</d:Probe></e:Body></e:Envelope>'
        )
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 4)
                sock.settimeout(4)
                sock.sendto(PROBE.encode(), ("239.255.255.250", 3702))

                end = time.time() + 4
                while time.time() < end and self.running:
                    try:
                        data, addr = sock.recvfrom(8192)
                        ip = addr[0]
                        self._parse_onvif_response(ip, data.decode("utf-8", errors="ignore"))
                    except socket.timeout:
                        break
                    except Exception:
                        continue
            finally:
                sock.close()
        except Exception:
            pass

    def _parse_onvif_response(self, ip, xml_text):
        vendor, model, onvif_url, scopes = "", "", "", []
        try:
            root = ET.fromstring(xml_text)
            ns = {
                "d": "http://schemas.xmlsoap.org/ws/2005/04/discovery",
                "dn": "http://www.onvif.org/ver10/network/wsdl",
            }
            # XAddrs = service URL
            for xa in root.iter("{http://schemas.xmlsoap.org/ws/2005/04/discovery}XAddrs"):
                if xa.text:
                    onvif_url = xa.text.split()[0] if xa.text else ""

            # Scopes contain onvif://www.onvif.org/hardware/ModelName etc.
            for sc in root.iter("{http://schemas.xmlsoap.org/ws/2005/04/discovery}Scopes"):
                if sc.text:
                    scopes = sc.text.split()
            for scope in scopes:
                if "/hardware/" in scope:
                    model = scope.split("/hardware/")[-1]
                elif "/name/" in scope:
                    vendor = scope.split("/name/")[-1]
                elif "/mfr/" in scope or "/manufacturer/" in scope:
                    for part in ["/mfr/", "/manufacturer/"]:
                        if part in scope:
                            vendor = scope.split(part)[-1]
        except Exception:
            pass

        # Clean up URL-encoded names
        try:
            vendor = unquote(vendor).strip()
            model = unquote(model).strip()
        except Exception:
            pass

        # Vendor fallback via HTTP keywords
        if not vendor:
            vendor = self._guess_vendor_from_text(xml_text)

        self._merge_result({
            "ip": ip, "vendor": vendor or "ONVIF Device", "model": model,
            "onvif_url": onvif_url, "method": "ONVIF", "conflict": False,
        })
        with self._stats_lock:
            self._scan_stats["onvif"] += 1
        self.after(0, lambda: self.cf_onvif.configure(text=str(self._scan_stats["onvif"])))

    # ── SSDP / UPnP ───────────────────────────────────────────────────────
    def _run_ssdp(self):
        MSEARCH = (
            "M-SEARCH * HTTP/1.1\r\n"
            "HOST: 239.255.255.250:1900\r\n"
            'MAN: "ssdp:discover"\r\n'
            "MX: 3\r\n"
            "ST: ssdp:all\r\n\r\n"
        )
        seen = set()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.settimeout(4)
                sock.sendto(MSEARCH.encode(), ("239.255.255.250", 1900))

                end = time.time() + 4
                while time.time() < end and self.running:
                    try:
                        data, addr = sock.recvfrom(4096)
                        ip = addr[0]
                        if ip in seen:
                            continue
                        seen.add(ip)
                        text = data.decode("utf-8", errors="ignore")
                        self._parse_ssdp_response(ip, text)
                    except socket.timeout:
                        break
                    except Exception:
                        continue
            finally:
                sock.close()
        except Exception:
            pass

    def _parse_ssdp_response(self, ip, text):
        # Parse header-like key:value pairs
        headers = {}
        for line in text.split("\r\n"):
            if ":" in line:
                k, _, v = line.partition(":")
                headers[k.strip().lower()] = v.strip()

        server = headers.get("server", "")
        st = headers.get("st", "")
        location = headers.get("location", "")
        vendor = self._guess_vendor_from_text(server + " " + st + " " + location)

        # Only report if it looks like a camera or video device
        cam_indicators = ["camera", "nvr", "dvr", "video", "hikvision", "dahua",
                          "axis", "onvif", "reolink", "foscam"]
        text_lower = (server + st + location).lower()
        if not any(k in text_lower for k in cam_indicators):
            return

        self._merge_result({
            "ip": ip, "vendor": vendor or "UPnP Device",
            "model": "", "method": "SSDP",
            "http_url": location if location.startswith("http") else f"http://{ip}",
            "conflict": False,
        })
        with self._stats_lock:
            self._scan_stats["ssdp"] += 1
        self.after(0, lambda: self.cf_ssdp.configure(text=str(self._scan_stats["ssdp"])))

    # ── Ping sweep + host probing ──────────────────────────────────────────
    def _run_ping_sweep(self, hosts):
        to_ms = self.timeout_var.get()
        n_thr = min(self.threads_var.get(), 256)
        done = 0
        total = len(hosts)

        with ThreadPoolExecutor(max_workers=n_thr) as ex:
            futs = {ex.submit(self._ping_alive, ip, to_ms): ip for ip in hosts}
            probe_futs = []
            for fut in as_completed(futs):
                if self.stop_event.is_set():
                    break
                ip = futs[fut]
                try:
                    alive = fut.result()
                    done += 1
                    with self._stats_lock:
                        self._scan_stats["scanned"] = done
                    pct = done / total
                    self.after(0, lambda d=done, t=total, p=pct: (
                        self.cf_scanned.configure(text=f"{d}/{t}"),
                    ))
                    if alive and (self.use_http.get() or self.use_rtsp.get()):
                        pf = ex.submit(self._probe_host, str(ip))
                        probe_futs.append(pf)
                except Exception:
                    done += 1

            # Wait for probes
            for pf in as_completed(probe_futs):
                try:
                    pf.result()
                except Exception:
                    pass

    def _ping_alive(self, ip, to_ms):
        try:
            r = subprocess.run(
                _pu_net.ping_once_command(str(ip), timeout_ms=to_ms),
                capture_output=True, timeout=to_ms / 1000 + 1,
                creationflags=SUBPROCESS_FLAGS)
            return r.returncode == 0
        except Exception:
            return False

    def _probe_host(self, ip):
        """Port-probe, HTTP banner, RTSP check, ARP MAC for a live host."""
        if self.stop_event.is_set():
            return

        to_ms = self.timeout_var.get()
        open_ports = []
        http_url = ""
        rtsp_url = ""
        vendor = ""
        model = ""
        server_hdr = ""
        http_title = ""

        # Port probe
        for port in CAMERA_PORTS:
            if self.stop_event.is_set():
                break
            if self._tcp_open(ip, port, to_ms):
                open_ports.append(port)

        if not open_ports:
            return  # nothing interesting on this host

        # HTTP banner on first HTTP port found
        if self.use_http.get():
            for port in [p for p in open_ports if p in (80, 81, 8080, 8081, 8000, 8001, 443, 8443)]:
                server_hdr, http_title, v = self._http_banner(ip, port, to_ms)
                if v:
                    vendor = v
                if not model and http_title:
                    model = http_title[:60]
                scheme = "https" if port in (443, 8443) else "http"
                http_url = f"{scheme}://{ip}" + (f":{port}" if port not in (80, 443) else "")
                break

        # RTSP probe
        if self.use_rtsp.get():
            for rport in [p for p in open_ports if p in (554, 8554)]:
                if self._rtsp_alive(ip, rport, to_ms):
                    rtsp_url = f"rtsp://{ip}:{rport}/stream"
                    break

        # Only record if looks like a camera
        is_cam = (
            vendor or
            any(p in open_ports for p in (554, 8554)) or
            any(kw in (server_hdr + http_title).lower() for kw, _ in CAMERA_HTTP_KEYWORDS)
        )
        if not is_cam:
            return

        # MAC from ARP
        mac = self._get_arp_mac(ip)
        if not vendor and mac:
            vendor = self._oui_lookup(mac)
        if not vendor:
            vendor = self._guess_vendor_from_text(server_hdr + " " + http_title)

        if vendor:
            with self._stats_lock:
                self._scan_stats["http"] += 1
            self.after(0, lambda: self.cf_http.configure(text=str(self._scan_stats["http"])))

        self._merge_result({
            "ip": ip, "mac": mac, "vendor": vendor or "IP Camera",
            "model": model, "method": "Ping+HTTP",
            "ports": open_ports, "http_url": http_url, "rtsp_url": rtsp_url,
            "server": server_hdr, "conflict": False,
        })

    # ── Low-level probe helpers ────────────────────────────────────────────
    def _tcp_open(self, ip, port, to_ms):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(to_ms / 1000)
                return s.connect_ex((ip, port)) == 0
        except Exception:
            return False

    def _http_banner(self, ip, port, to_ms):
        """Returns (server_header, page_title, vendor_guess)."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(to_ms / 1000)
                s.connect((ip, port))
                req = f"GET / HTTP/1.1\r\nHost: {ip}\r\nConnection: close\r\n\r\n"
                s.sendall(req.encode())
                data = b""
                while len(data) < 8192:
                    chunk = s.recv(2048)
                    if not chunk:
                        break
                    data += chunk
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            return "", "", ""

        server = ""
        title = ""
        for line in text.split("\r\n"):
            if line.lower().startswith("server:"):
                server = line.split(":", 1)[1].strip()
            elif not server and line.lower().startswith("www-authenticate:"):
                server = line  # auth challenge often reveals device type
        m = re.search(r"<title[^>]*>([^<]{1,80})</title>", text, re.IGNORECASE)
        if m:
            title = m.group(1).strip()

        vendor = self._guess_vendor_from_text(server + " " + title + " " + text[:2000])
        return server, title, vendor

    def _rtsp_alive(self, ip, port, to_ms):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(to_ms / 1000)
                s.connect((ip, port))
                s.sendall(f"OPTIONS rtsp://{ip}:{port}/ RTSP/1.0\r\nCSeq: 1\r\n\r\n".encode())
                data = s.recv(512).decode("utf-8", errors="ignore")
            return "RTSP/1" in data
        except Exception:
            return False

    def _get_arp_mac(self, ip):
        """Return MAC address string for IP from ARP cache, or empty string."""
        try:
            mac = _pu_net.arp_lookup(str(ip))
            if mac:
                return mac
            # Fallback: if lookup returned nothing, scan the full table (some
            # systems don't accept `arp -a <ip>` / `ip neigh show <ip>`).
            res = subprocess.run(_pu_net.arp_command("-a", str(ip)),
                                 capture_output=True, text=True,
                                 timeout=4, creationflags=SUBPROCESS_FLAGS)
            for line in res.stdout.split("\n"):
                if str(ip) in line:
                    # Windows: "  192.168.1.50         ac-cc-8e-xx-xx-xx     dynamic"
                    m = re.search(r"([0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}"
                                  r"[:\-][0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2})", line)
                    if m:
                        return m.group(1).replace("-", ":").upper()
        except Exception:
            pass
        return ""

    def _oui_lookup(self, mac):
        oui = re.sub(r"[:\-\.]", "", mac).upper()[:6]
        return CAMERA_OUI.get(oui, "")

    def _guess_vendor_from_text(self, text):
        text_lower = text.lower()
        for kw, vendor in CAMERA_HTTP_KEYWORDS:
            if kw in text_lower:
                return vendor
        return ""

    # ── Result merge & treeview update ────────────────────────────────────
    def _merge_result(self, info):
        ip = info.get("ip", "")
        if not ip:
            return
        with self._cam_lock:
            existing = self._cameras.get(ip, {})
            # Merge: keep best data from all methods
            merged = dict(existing)
            for k, v in info.items():
                if v and (not merged.get(k)):
                    merged[k] = v
            # Accumulate methods
            methods = set(merged.get("_methods", []))
            methods.add(info.get("method", ""))
            merged["_methods"] = list(methods)
            merged["method"] = " + ".join(sorted(m for m in methods if m))
            # Accumulate MACs (for conflict detection)
            macs = list(merged.get("all_macs", []))
            new_mac = info.get("mac", "")
            if new_mac and new_mac not in macs:
                macs.append(new_mac)
            merged["all_macs"] = macs
            if not merged.get("mac") and macs:
                merged["mac"] = macs[0]
            self._cameras[ip] = merged

        total = len(self._cameras)
        self.after(0, lambda: (
            self.cf_total.configure(text=str(total)),
            self._update_treeview_row(ip),
        ))

    def _update_treeview_row(self, ip):
        with self._cam_lock:
            info = self._cameras.get(ip)
        if not info:
            return
        conflict = ip in self._conflict_ips or len(info.get("all_macs", [])) > 1
        if conflict:
            status = "⚠ CONFLICT"
            tag = "conflict"
        else:
            status = "✓ Camera"
            tag = "camera"

        mac = info.get("mac", "—")
        vendor = info.get("vendor", "—")
        model = info.get("model", "—")[:50]
        method = info.get("method", "—")
        ports = ", ".join(str(p) for p in info.get("ports", []))
        url = info.get("http_url") or info.get("rtsp_url") or info.get("onvif_url") or "—"

        vals = (status, ip, mac, vendor, model, method, ports, url)
        if ip in self._tree_ids:
            try:
                self._tv.item(self._tree_ids[ip], values=vals, tags=(tag,))
            except tk.TclError:
                pass
        else:
            iid = self._tv.insert("", "end", values=vals, tags=(tag,))
            self._tree_ids[ip] = iid

    # ── Selection & detail panel ──────────────────────────────────────────
    def _on_select(self, _event=None):
        sel = self._tv.selection()
        if not sel:
            return
        row = self._tv.item(sel[0], "values")
        if not row:
            return
        ip = row[1]
        self._selected_ip = ip
        with self._cam_lock:
            info = dict(self._cameras.get(ip, {}))
        self._show_details(ip, info)
        has_web = bool(info.get("http_url"))
        has_rtsp = bool(info.get("rtsp_url"))
        self._btn_web.configure(state="normal" if has_web else "disabled")
        self._btn_copy.configure(state="normal" if has_rtsp else "disabled")
        self._btn_view.configure(state="normal")   # always enabled once a camera is selected

    def _view_stream(self):
        """Open the Stream Viewer tab pre-filled with the selected camera's IP."""
        if not self._selected_ip:
            return
        with self._cam_lock:
            info = self._cameras.get(self._selected_ip, {})
        ports = info.get("ports", [80])
        http_port = next((p for p in ports if p in (80, 81, 8080, 8081, 8000)), 80)
        vendor = info.get("vendor", "")
        # Walk up to the App root and call _open_viewer
        root = self.winfo_toplevel()
        if hasattr(root, "_open_viewer"):
            root._open_viewer(self._selected_ip, http_port, vendor_hint=vendor)

    def _show_details(self, ip, info):
        d = self._detail
        d.clear()
        conflict = ip in self._conflict_ips or len(info.get("all_macs", [])) > 1
        if conflict:
            d.append("⚠  IP ADDRESS CONFLICT DETECTED — multiple devices may share this IP!", "error")
            d.append("", "dim")
        d.append(f"IP Address:      {ip}", "info")
        d.append(f"MAC Address(es): {', '.join(info.get('all_macs', ['—'])) or '—'}", "normal")
        d.append(f"Vendor:          {info.get('vendor', '—')}", "success" if info.get("vendor") else "dim")
        d.append(f"Model / Title:   {info.get('model', '—')}", "normal")
        d.append(f"Discovery:       {info.get('method', '—')}", "info")
        d.append(f"Open Ports:      {', '.join(str(p) for p in info.get('ports', [])) or '—'}", "normal")
        if info.get("http_url"):
            d.append(f"Web Interface:   {info['http_url']}", "highlight")
        if info.get("rtsp_url"):
            d.append(f"RTSP Stream:     {info['rtsp_url']}", "highlight")
        if info.get("onvif_url"):
            d.append(f"ONVIF Service:   {info['onvif_url']}", "highlight")
        if info.get("server"):
            d.append(f"HTTP Server:     {info['server']}", "dim")

        # Subnet reachability check — compare camera IP to local adapters
        if PSUTIL_AVAILABLE:
            try:
                reachable_from = []
                for _n, addrs in psutil.net_if_addrs().items():
                    for a in addrs:
                        if a.family == socket.AF_INET and a.address and a.netmask:
                            sub = compare_adapter_to_candidate(a.address, a.netmask, ip)
                            if sub.get("same_subnet"):
                                reachable_from.append(a.address)
                if reachable_from:
                    d.append(f"Reachability:    ✔ Directly reachable from {reachable_from[0]}", "success")
                else:
                    # Check best reachability state
                    for _n, addrs in psutil.net_if_addrs().items():
                        for a in addrs:
                            if a.family == socket.AF_INET and a.address and a.netmask:
                                sub = compare_adapter_to_candidate(a.address, a.netmask, ip)
                                r = sub.get("reachability", "unknown")
                                if r == "possibly_routed":
                                    d.append(
                                        f"Reachability:    ~ Different subnet, possibly routable via gateway",
                                        "info",
                                    )
                                    break
                    else:
                        d.append(
                            f"Reachability:    ⚠ Different subnet — may need adapter change or gateway",
                            "warning",
                        )
            except Exception:
                pass

        if conflict:
            d.append("", "dim")
            d.append("CONFLICT DETAIL:", "error")
            d.append("  Two or more devices responded to this IP address during scanning.", "warning")
            d.append("  Known MACs at this IP:", "warning")
            for mac in info.get("all_macs", []):
                oui_vendor = self._oui_lookup(mac) if mac else ""
                d.append(f"    {mac}  →  {oui_vendor or 'Unknown vendor'}", "error")
            d.append("  Recommendation: assign a static IP to each camera to resolve the conflict.", "info")

    def _open_web(self):
        if not self._selected_ip:
            return
        with self._cam_lock:
            info = self._cameras.get(self._selected_ip, {})
        url = info.get("http_url", f"http://{self._selected_ip}")
        try:
            _pu_shell.open_url(url)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _copy_rtsp(self):
        if not self._selected_ip:
            return
        with self._cam_lock:
            info = self._cameras.get(self._selected_ip, {})
        url = info.get("rtsp_url", "")
        if url:
            self.clipboard_clear()
            self.clipboard_append(url)
            messagebox.showinfo("Copied", f"RTSP URL copied:\n{url}")

    def _export_csv(self):
        if not self._cameras:
            messagebox.showinfo("Export", "No cameras to export.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="cameras.csv")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("IP,MAC,Vendor,Model,Methods,Ports,Web URL,RTSP URL,ONVIF URL,Conflict\n")
                for ip, info in sorted(self._cameras.items()):
                    conflict = "YES" if ip in self._conflict_ips else "NO"
                    ports = " ".join(str(p) for p in info.get("ports", []))
                    line = ",".join([
                        ip,
                        info.get("mac", ""),
                        info.get("vendor", ""),
                        (info.get("model", "") or "").replace(",", " "),
                        info.get("method", ""),
                        ports,
                        info.get("http_url", ""),
                        info.get("rtsp_url", ""),
                        info.get("onvif_url", ""),
                        conflict,
                    ])
                    f.write(line + "\n")
            messagebox.showinfo("Export", f"Saved {len(self._cameras)} cameras to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))


# ==================== Camera Stream Viewer ====================
class _CameraStreamSlot:
    """Per-camera state container for CameraViewerFrame."""

    def __init__(self, idx):
        self.idx = idx
        self.url = ""
        self.user = ""
        self.password = ""
        self.running = False
        self.stop_event = threading.Event()
        self.frame_lock = threading.Lock()
        self.pending_frame = None
        self.frame_count = 0
        self.lost_count = 0
        self.fps_times = deque(maxlen=30)
        self.last_image = None
        self.current_photo = None
        self.canvas = None
        self.poll_after_id = None
        self.card = None
        self.title_label = None
        self.url_label = None
        self.lbl_fps = None
        self.lbl_res = None
        self.lbl_frm = None
        self.lbl_lost = None


class CameraViewerFrame(BaseToolFrame):
    """
    Live HTTP/MJPEG stream viewer for IP cameras.
    Probes a camera IP for known stream URLs and displays the feed in-app.
    Requires Pillow for JPEG decoding; falls back gracefully if not installed.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._slots = [_CameraStreamSlot(i) for i in range(4)]
        self._active_slot_idx = 0
        self._fullscreen_slot_idx = None
        self._probe_results = []       # list of (url, stream_type, label, confidence)
        self._all_probe_results = []   # unfiltered copy (includes "failed")
        self._lb_index_map  = []       # listbox row → _probe_results index
        self._vendor_hint   = ""       # vendor from CameraFinder for RTSP ranking
        self._show_all_var  = None     # BooleanVar for "Show all candidates" checkbox
        self._slot_buttons = []
        self._build()

    # ── UI ─────────────────────────────────────────────────────────────────
    def _build(self):
        self.make_header("📺  Camera Stream Viewer",
                         "Connect to HTTP/MJPEG/JPEG and RTSP camera streams — no external software needed")

        if not PILLOW_AVAILABLE:
            warn = self.make_card(self)
            warn.pack(fill="x", padx=20, pady=20)
            ctk.CTkLabel(warn,
                         text="⚠  Pillow library not found — required for JPEG frame decoding.\n\n"
                              "Run:  pip install Pillow\n"
                              "Then restart the application.",
                         text_color="#f85149", font=ctk.CTkFont(size=13),
                         justify="left").pack(padx=20, pady=20)
            return

        # ── Controls card ─────────────────────────────────────────────────
        ctrl = self.make_card(self)
        ctrl.pack(fill="x", padx=20, pady=(0, 8))

        row1 = ctk.CTkFrame(ctrl, fg_color="transparent")
        row1.pack(fill="x", padx=14, pady=(10, 4))

        ctk.CTkLabel(row1, text="Camera IP:", text_color="#8b949e").pack(side="left", padx=(0, 5))
        self._ip_var = tk.StringVar(value="192.168.1.")
        ip_entry = ctk.CTkEntry(row1, textvariable=self._ip_var)
        self._attach_entry_context_menu(ip_entry)
        ip_entry.pack(side="left", padx=(0, 8), fill="x", expand=True)

        ctk.CTkLabel(row1, text="Port:", text_color="#8b949e").pack(side="left", padx=(0, 4))
        self._port_var = tk.IntVar(value=80)
        port_entry = ctk.CTkEntry(row1, textvariable=self._port_var, width=65)
        self._attach_entry_context_menu(port_entry)
        port_entry.pack(side="left", padx=(0, 8))

        ctk.CTkButton(row1, text="🔍  Probe Streams", command=self._probe_streams,
                      fg_color="#0f3460", hover_color="#1a4a80", width=140).pack(side="left")

        row1b = ctk.CTkFrame(ctrl, fg_color="transparent")
        row1b.pack(fill="x", padx=14, pady=(0, 4))
        ctk.CTkLabel(row1b, text="User:", text_color="#8b949e").pack(side="left", padx=(0, 4))
        self._user_var = tk.StringVar(value="admin")
        user_entry = ctk.CTkEntry(row1b, textvariable=self._user_var)
        self._attach_entry_context_menu(user_entry)
        user_entry.pack(side="left", padx=(0, 12), fill="x", expand=True)

        ctk.CTkLabel(row1b, text="Pass:", text_color="#8b949e").pack(side="left", padx=(0, 4))
        self._pass_var = tk.StringVar(value="")
        pass_entry = ctk.CTkEntry(row1b, textvariable=self._pass_var, show="*")
        self._attach_entry_context_menu(pass_entry)
        pass_entry.pack(side="left", fill="x", expand=True)

        # Manual URL row
        row2 = ctk.CTkFrame(ctrl, fg_color="transparent")
        row2.pack(fill="x", padx=14, pady=(0, 10))
        ctk.CTkLabel(row2, text="Direct URL:", text_color="#8b949e").pack(side="left", padx=(0, 5))
        self._url_var = tk.StringVar()
        url_entry = ctk.CTkEntry(
            row2,
            textvariable=self._url_var,
            placeholder_text="http://... or rtsp://... — paste any stream URL",
        )
        self._attach_entry_context_menu(url_entry)
        url_entry.pack(side="left", padx=(0, 8), fill="x", expand=True)
        ctk.CTkButton(row2, text="\u25b6  Connect", command=self._connect_manual,
                      fg_color="#238636", hover_color="#2ea043", width=110).pack(side="left")
        ctk.CTkButton(row2, text="\u2b50  Save URL",
                      command=lambda: self._save_favorite_dialog("RTSP URL", self._active_slot().url or self._url_var.get().strip()),
                      fg_color="#21262d", hover_color="#30363d", width=90).pack(side="left", padx=(8, 0))

        slot_row = ctk.CTkFrame(ctrl, fg_color="transparent")
        slot_row.pack(fill="x", padx=14, pady=(0, 10))
        ctk.CTkLabel(slot_row, text="Target slot:", text_color="#8b949e").pack(side="left", padx=(0, 6))
        for idx in range(4):
            btn = ctk.CTkButton(
                slot_row,
                text=f"Slot {idx + 1}",
                width=72,
                height=26,
                command=lambda i=idx: self._set_active_slot(i),
            )
            btn.pack(side="left", padx=(0, 6))
            self._slot_buttons.append(btn)

        # ── Main split: probe list (left) + canvas (right) ─────────────────
        split = ctk.CTkFrame(self, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=20, pady=(0, 0))

        # Left: stream list
        left = self.make_card(split, title="Discovered Streams", width=260)
        left.pack(side="left", fill="y", padx=(0, 8), pady=(0, 8))
        left.pack_propagate(False)

        list_wrap = ctk.CTkFrame(left, fg_color="#0d1117", corner_radius=6)
        list_wrap.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        list_sb = ctk.CTkScrollbar(list_wrap)
        list_sb.pack(side="right", fill="y", padx=(0, 2), pady=2)

        self._listbox = tk.Listbox(list_wrap,
                                   bg="#0d1117", fg="#c9d1d9",
                                   selectbackground="#264f78",
                                   selectforeground="#ffffff",
                                   font=("Consolas", 9),
                                   relief="flat", borderwidth=0,
                                   highlightthickness=0,
                                   yscrollcommand=list_sb.set,
                                   activestyle="none")
        self._listbox.pack(fill="both", expand=True, padx=2, pady=2)
        list_sb.configure(command=self._listbox.yview)
        self._listbox.bind("<<ListboxSelect>>", self._on_list_select)

        # "Show all candidates" toggle
        self._show_all_var = tk.BooleanVar(value=False)
        self._show_all_chk = ctk.CTkCheckBox(
            left, text="Show all candidates",
            variable=self._show_all_var, command=self._toggle_show_all,
            font=ctk.CTkFont(size=10), text_color="#8b949e",
            fg_color="#21262d", hover_color="#30363d", height=24,
        )
        self._show_all_chk.pack(fill="x", padx=10, pady=(2, 4))

        # Action buttons (left panel)
        btn_frame = ctk.CTkFrame(left, fg_color="transparent")
        btn_frame.pack(fill="x", padx=8, pady=(0, 10))

        self._connect_btn = ctk.CTkButton(btn_frame, text="▶  Connect Selected",
                                          command=self._connect_selected,
                                          fg_color="#238636", hover_color="#2ea043",
                                          state="disabled", height=30)
        self._connect_btn.pack(fill="x", pady=(0, 4))

        self._stop_stream_btn = ctk.CTkButton(btn_frame, text="⏹  Stop Stream",
                                              command=self._stop_stream,
                                              fg_color="#da3633", hover_color="#f85149",
                                              state="disabled", height=30)
        self._stop_stream_btn.pack(fill="x", pady=(0, 4))

        ctk.CTkButton(btn_frame, text="📷  Snapshot",
                      command=self._snapshot,
                      fg_color="#21262d", hover_color="#30363d", height=30
                      ).pack(fill="x", pady=(0, 4))

        ctk.CTkButton(btn_frame, text="📋  Copy RTSP URLs",
                      command=self._copy_rtsp_urls,
                      fg_color="#21262d", hover_color="#30363d", height=30
                      ).pack(fill="x", pady=(0, 4))

        ctk.CTkButton(btn_frame, text="🌐  Open Web UI",
                      command=self._open_web,
                      fg_color="#21262d", hover_color="#30363d", height=30
                      ).pack(fill="x")

        # Right: 4-slot stream wall. Canvases are never destroyed during
        # fullscreen toggles; they are only re-gridded to preserve stream state.
        self._wall = ctk.CTkFrame(split, fg_color="transparent")
        self._wall.pack(side="left", fill="both", expand=True, pady=(0, 8))
        self._wall.grid_columnconfigure(0, weight=1, uniform="camwall")
        self._wall.grid_columnconfigure(1, weight=1, uniform="camwall")
        self._wall.grid_rowconfigure(0, weight=1, uniform="camwall")
        self._wall.grid_rowconfigure(1, weight=1, uniform="camwall")
        self._build_stream_slots()

        # ── Status bar ────────────────────────────────────────────────────
        status = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=8)
        status.pack(fill="x", padx=20, pady=(0, 12))

        srow = ctk.CTkFrame(status, fg_color="transparent")
        srow.pack(fill="x", padx=12, pady=6)

        for label, attr, init in [
            ("FPS",        "_lbl_fps",  "—"),
            ("Resolution", "_lbl_res",  "—"),
            ("Frames",     "_lbl_frm",  "0"),
            ("Lost",       "_lbl_lost", "0"),
        ]:
            sf = ctk.CTkFrame(srow, fg_color="transparent")
            sf.pack(side="left", padx=(0, 20))
            ctk.CTkLabel(sf, text=label, text_color="#8b949e",
                         font=ctk.CTkFont(size=10)).pack(anchor="w")
            v = ctk.CTkLabel(sf, text=init, text_color="#f0883e",
                             font=ctk.CTkFont(size=12, weight="bold"))
            v.pack(anchor="w")
            setattr(self, attr, v)

        self._lbl_url = ctk.CTkLabel(srow, text="Not connected",
                                     text_color="#8b949e", font=ctk.CTkFont(size=10))
        self._lbl_url.pack(side="left", padx=(10, 0))
        self._set_active_slot(0)

    def _build_stream_slots(self):
        for slot in self._slots:
            row, col = divmod(slot.idx, 2)
            card = ctk.CTkFrame(self._wall, fg_color="#161b22", corner_radius=8)
            card.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
            slot.card = card

            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=8, pady=(6, 2))
            slot.title_label = ctk.CTkLabel(
                top,
                text=f"Slot {slot.idx + 1}",
                text_color="#79c0ff",
                font=ctk.CTkFont(size=12, weight="bold"),
            )
            slot.title_label.pack(side="left")
            slot.url_label = ctk.CTkLabel(
                top,
                text="Idle",
                text_color="#8b949e",
                font=ctk.CTkFont(size=10),
            )
            slot.url_label.pack(side="left", padx=(10, 0), fill="x", expand=True)

            canvas = tk.Canvas(card, bg="#0d1117", highlightthickness=0, relief="flat")
            canvas.pack(fill="both", expand=True, padx=4, pady=4)
            canvas.bind("<Button-1>", lambda _event, i=slot.idx: self._toggle_fullscreen_slot(i))
            slot.canvas = canvas

            stats = ctk.CTkFrame(card, fg_color="transparent")
            stats.pack(fill="x", padx=8, pady=(0, 6))
            for label, attr, init in [
                ("FPS", "lbl_fps", "—"),
                ("RES", "lbl_res", "—"),
                ("FRM", "lbl_frm", "0"),
                ("LOST", "lbl_lost", "0"),
            ]:
                cell = ctk.CTkFrame(stats, fg_color="transparent")
                cell.pack(side="left", expand=True, fill="x")
                ctk.CTkLabel(cell, text=label, text_color="#8b949e",
                             font=ctk.CTkFont(size=9)).pack(anchor="w")
                val = ctk.CTkLabel(cell, text=init, text_color="#f0883e",
                                   font=ctk.CTkFont(size=11, weight="bold"))
                val.pack(anchor="w")
                setattr(slot, attr, val)

            self._draw_idle_screen(slot)

    def _active_slot(self):
        return self._slots[self._active_slot_idx]

    def _set_active_slot(self, idx):
        self._active_slot_idx = idx
        for i, btn in enumerate(self._slot_buttons):
            if i == idx:
                btn.configure(fg_color="#238636", hover_color="#2ea043")
            else:
                btn.configure(fg_color="#21262d", hover_color="#30363d")
        self._refresh_active_status()

    def _refresh_active_status(self):
        slot = self._active_slot()
        if hasattr(self, "_lbl_fps"):
            self._lbl_fps.configure(text=slot.lbl_fps.cget("text") if slot.lbl_fps else "—")
            self._lbl_res.configure(text=slot.lbl_res.cget("text") if slot.lbl_res else "—")
            self._lbl_frm.configure(text=slot.lbl_frm.cget("text") if slot.lbl_frm else "0")
            self._lbl_lost.configure(text=slot.lbl_lost.cget("text") if slot.lbl_lost else "0")
            self._lbl_url.configure(text=slot.url_label.cget("text") if slot.url_label else "Not connected")
        if hasattr(self, "_stop_stream_btn"):
            self._stop_stream_btn.configure(state="normal" if slot.running else "disabled")
        if hasattr(self, "_connect_btn"):
            self._connect_btn.configure(
                state="normal" if self._probe_results and not slot.running else "disabled")

    def _toggle_fullscreen_slot(self, idx):
        self._set_active_slot(idx)
        if self._fullscreen_slot_idx == idx:
            self._restore_stream_wall()
            return

        self._show_fullscreen_slot(idx)

    def _restore_stream_wall(self):
        self._fullscreen_slot_idx = None
        for slot in self._slots:
            slot.card.grid_forget()
        for slot in self._slots:
            row, col = divmod(slot.idx, 2)
            slot.card.grid(
                row=row,
                column=col,
                rowspan=1,
                columnspan=1,
                sticky="nsew",
                padx=4,
                pady=4,
            )
            slot.card.lift()
        self._wall.update_idletasks()
        self._refresh_active_status()

    def _show_fullscreen_slot(self, idx):
        self._fullscreen_slot_idx = idx
        for slot in self._slots:
            slot.card.grid_forget()
        slot = self._slots[idx]
        slot.card.grid(
            row=0,
            column=0,
            rowspan=2,
            columnspan=2,
            sticky="nsew",
            padx=4,
            pady=4,
        )
        slot.card.lift()
        self._wall.update_idletasks()
        self._refresh_active_status()

    # ── Idle screen ────────────────────────────────────────────────────────
    def _draw_idle_screen(self, slot):
        slot.canvas.update_idletasks()
        w = max(slot.canvas.winfo_width(), 300)
        h = max(slot.canvas.winfo_height(), 200)
        cx, cy = w // 2, h // 2
        slot.canvas.delete("all")
        slot.canvas.create_text(cx, cy - 20, text="CAM", font=("Consolas", 24, "bold"),
                                fill="#21262d")
        slot.canvas.create_text(cx, cy + 34,
                                text=f"Slot {slot.idx + 1}",
                                font=("Consolas", 11), fill="#8b949e", justify="center")

    # ── set_target: called from CameraFinderFrame ──────────────────────────
    def set_target(self, ip, port=80, vendor_hint=""):
        """Pre-fill IP/port and automatically start probing."""
        self._set_active_slot(0)
        self._ip_var.set(ip)
        self._port_var.set(port)
        self._vendor_hint = vendor_hint
        self._probe_streams()

    # ── Probe all known stream paths ───────────────────────────────────────
    def _probe_streams(self):
        ip = self._ip_var.get().strip()
        if not ip:
            messagebox.showwarning("Input", "Enter a camera IP address.")
            return
        try:
            port = self._port_var.get()
        except Exception:
            port = 80

        self._listbox.delete(0, "end")
        self._listbox.insert("end", "  Probing streams …")
        self._probe_results = []
        self._connect_btn.configure(state="disabled")

        user = self._user_var.get().strip()
        pw   = self._pass_var.get()
        threading.Thread(target=self._probe_worker,
                         args=(ip, port, user, pw), daemon=True).start()

    def _rtsp_options_check(self, url, user, pw, timeout=3):
        """Send RTSP OPTIONS to verify an RTSP endpoint responds.
        Returns (alive: bool, server_header: str)."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            host = parsed.hostname
            rport = parsed.port or 554
            # Build auth URL if credentials provided
            if user:
                auth_url = f"rtsp://{user}:{pw}@{host}:{rport}{parsed.path}"
                if parsed.query:
                    auth_url += f"?{parsed.query}"
            else:
                auth_url = url
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((host, rport))
            req_str = f"OPTIONS {auth_url} RTSP/1.0\r\nCSeq: 1\r\n\r\n"
            s.sendall(req_str.encode())
            resp = s.recv(1024).decode(errors="ignore")
            s.close()
            alive = "RTSP/1" in resp
            server = ""
            for line in resp.splitlines():
                if line.lower().startswith("server:"):
                    server = line.split(":", 1)[1].strip()
                    break
            return alive, server
        except Exception:
            return False, ""

    def _probe_worker(self, ip, port, user, pw):
        found = []       # (url, type, label, confidence)
        failed = []      # same shape, for hidden-by-default entries
        base  = f"http://{ip}:{port}"
        vendor_hint = self._vendor_hint.lower() if self._vendor_hint else ""

        # Check subnet reachability and build a warning if needed
        subnet_warning = ""
        if PSUTIL_AVAILABLE:
            try:
                for _name, addrs in psutil.net_if_addrs().items():
                    for a in addrs:
                        if a.family == socket.AF_INET and a.address and a.netmask:
                            sub = compare_adapter_to_candidate(a.address, a.netmask, ip)
                            if sub.get("same_subnet"):
                                subnet_warning = ""
                                break
                    if not subnet_warning and subnet_warning != "":
                        break
                else:
                    subnet_warning = (
                        f"Camera {ip} is on a different subnet from all local adapters — "
                        "streams may be unreachable without routing or an adapter change."
                    )
            except Exception:
                pass

        # Phase 1: probe HTTP stream paths
        for path, stype in CAMERA_STREAM_PATHS:
            if self.stop_event.is_set():
                break
            url = base + path
            try:
                opener = self._make_opener(user, pw, url)
                req = urllib.request.Request(url, method="GET")
                req.add_header("User-Agent", "NetToolsPro/1.0")
                with opener.open(req, timeout=2) as resp:
                    ct   = resp.headers.get("Content-Type", "").lower()
                    code = resp.status
                if code == 200:
                    if "multipart" in ct or "mjpeg" in ct or "octet-stream" in ct:
                        actual_type = "MJPEG"
                    elif "jpeg" in ct or "jpg" in ct or "image" in ct:
                        actual_type = "JPEG"
                    else:
                        actual_type = stype
                    label = f"OK {path}  [{actual_type}]"
                    found.append((url, actual_type, label, "verified"))
            except Exception:
                pass

        # Phase 2: probe RTSP ports — validate with OPTIONS handshake
        rtsp_candidates = []
        for rtsp_port in (554, 8554):
            if self.stop_event.is_set():
                break
            if not _cam_tcp_open(ip, rtsp_port, 1500):
                continue
            # Sort RTSP paths: vendor-matching first if hint is set
            paths = list(CAMERA_RTSP_PATHS)
            if vendor_hint:
                paths.sort(key=lambda p: (0 if vendor_hint in p[2].lower() else 1))
            for rpath, rport, vendor, bonus in paths:
                if rport != rtsp_port:
                    continue
                if self.stop_event.is_set():
                    break
                url = f"rtsp://{ip}:{rtsp_port}{rpath}"
                alive, server_hdr = self._rtsp_options_check(url, user, pw, timeout=2)
                if alive:
                    conf = "verified"
                    tag = "OK Verified"
                elif vendor_hint and vendor_hint in vendor.lower():
                    conf = "likely"
                    tag = "Likely"
                elif bonus == 2:
                    conf = "likely"
                    tag = "Likely"
                else:
                    conf = "guess"
                    tag = "? Guess"
                label = f"{tag}  {rpath}  [RTSP {vendor}]"
                if alive:
                    if server_hdr:
                        label += f"  srv:{server_hdr[:30]}"
                    rtsp_candidates.append((url, "RTSP", label, conf))
                else:
                    # Port is open but this specific path didn't respond
                    rtsp_candidates.append((url, "RTSP", label, conf))

        # Sort RTSP: verified > likely > guess
        conf_order = {"verified": 0, "likely": 1, "guess": 2, "failed": 3}
        rtsp_candidates.sort(key=lambda c: conf_order.get(c[3], 9))

        self._safe_after(0, lambda: self._show_probe_results(
            ip, port, found, rtsp_candidates, subnet_warning))

    def _make_opener(self, user, pw, url):
        if user:
            pm = urllib.request.HTTPPasswordMgrWithDefaultRealm()
            pm.add_password(None, url, user, pw)
            return urllib.request.build_opener(
                urllib.request.HTTPBasicAuthHandler(pm),
                urllib.request.HTTPDigestAuthHandler(pm),
            )
        return urllib.request.build_opener()

    def _show_probe_results(self, ip, port, found, rtsp_candidates=None,
                            subnet_warning=""):
        """Display probe results grouped by confidence level.
        Each result is (url, type, label, confidence) where confidence is
        'verified', 'likely', 'guess', or 'failed'."""
        self._listbox.delete(0, "end")
        rtsp_candidates = rtsp_candidates or []

        all_results = list(found) + list(rtsp_candidates)
        self._all_probe_results = list(all_results)   # keep unfiltered copy
        self._subnet_warning = subnet_warning
        self._last_probe_ip   = ip
        self._last_probe_port = port
        self._render_probe_list()

    def _render_probe_list(self):
        """Render the probe results listbox, filtering by 'Show all' toggle."""
        self._listbox.delete(0, "end")
        self._lb_index_map = []
        show_all = self._show_all_var.get() if self._show_all_var else False

        # Filter: hide "guess" confidence unless show_all is checked
        if show_all:
            results = list(self._all_probe_results)
        else:
            results = [r for r in self._all_probe_results
                       if len(r) < 4 or r[3] in ("verified", "likely")]
        self._probe_results = results

        if not self._all_probe_results:
            for line in [
                "  No streams found on this IP/port.", "",
                "  Try:", "  - Different port (81, 8080, 8081)",
                "  - Adding credentials", "  - Pasting URL directly below",
            ]:
                self._listbox.insert("end", line)
                self._lb_index_map.append(-1)
            if not CV2_AVAILABLE:
                self._listbox.insert("end", "")
                self._lb_index_map.append(-1)
                self._listbox.insert("end", "  RTSP needs: pip install opencv-python")
                self._lb_index_map.append(-1)
            self._connect_btn.configure(state="disabled")
            return

        # Show subnet warning if applicable
        if getattr(self, "_subnet_warning", "") and self._subnet_warning:
            self._listbox.insert("end", f"WARN {self._subnet_warning}")
            self._lb_index_map.append(-1)
            self._listbox.insert("end", "")
            self._lb_index_map.append(-1)

        ri = 0
        # Group by confidence
        http_results = [r for r in results if r[1] != "RTSP"]
        rtsp_results = [r for r in results if r[1] == "RTSP"]

        if http_results:
            self._listbox.insert("end", "── HTTP Streams (verified) ──")
            self._lb_index_map.append(-1)
            for r in http_results:
                self._listbox.insert("end", f"  {r[2]}")
                self._lb_index_map.append(ri)
                ri += 1

        if rtsp_results:
            if http_results:
                self._listbox.insert("end", "")
                self._lb_index_map.append(-1)
            # Sub-group RTSP by confidence
            verified = [r for r in rtsp_results if len(r) >= 4 and r[3] == "verified"]
            likely   = [r for r in rtsp_results if len(r) >= 4 and r[3] == "likely"]
            guess    = [r for r in rtsp_results if len(r) < 4 or r[3] == "guess"]

            if verified:
                hdr = "── RTSP Verified"
                hdr += " (click to connect) ──" if CV2_AVAILABLE else " ──"
                self._listbox.insert("end", hdr)
                self._lb_index_map.append(-1)
                for r in verified:
                    self._listbox.insert("end", f"  {r[2]}")
                    self._lb_index_map.append(ri)
                    ri += 1

            if likely:
                hdr = "── RTSP Likely"
                hdr += " (click to connect) ──" if CV2_AVAILABLE else " ──"
                self._listbox.insert("end", hdr)
                self._lb_index_map.append(-1)
                for r in likely:
                    self._listbox.insert("end", f"  {r[2]}")
                    self._lb_index_map.append(ri)
                    ri += 1

            if guess:
                hdr = "── RTSP Candidates (unverified) ──"
                self._listbox.insert("end", hdr)
                self._lb_index_map.append(-1)
                for r in guess:
                    self._listbox.insert("end", f"  {r[2]}")
                    self._lb_index_map.append(ri)
                    ri += 1

            if not CV2_AVAILABLE and not verified and not likely:
                self._listbox.insert("end", "")
                self._lb_index_map.append(-1)
                self._listbox.insert("end", "  RTSP needs: pip install opencv-python")
                self._lb_index_map.append(-1)

        # Show how many hidden if not showing all
        if not show_all:
            hidden = len(self._all_probe_results) - len(results)
            if hidden > 0:
                self._listbox.insert("end", "")
                self._lb_index_map.append(-1)
                self._listbox.insert("end", f"  ({hidden} more candidates — check 'Show all')")
                self._lb_index_map.append(-1)

        # Select first actual result row
        for idx, mapped in enumerate(self._lb_index_map):
            if mapped != -1:
                self._listbox.selection_set(idx)
                break
        self._connect_btn.configure(
            state="normal" if results and not self._active_slot().running else "disabled")

    def _lb_selected_result(self):
        """Return the probe result for the current listbox selection, or None."""
        sel = self._listbox.curselection()
        if not sel:
            return None
        lb_idx = sel[0]
        if lb_idx >= len(self._lb_index_map):
            return None
        ri = self._lb_index_map[lb_idx]
        if ri < 0 or ri >= len(self._probe_results):
            return None
        return self._probe_results[ri]

    def _on_list_select(self, _event):
        result = self._lb_selected_result()
        self._connect_btn.configure(
            state="normal" if result and not self._active_slot().running else "disabled")

    def _toggle_show_all(self):
        """Re-render probe results when the 'Show all candidates' checkbox changes."""
        if self._all_probe_results:
            self._render_probe_list()

    # ── Connect ────────────────────────────────────────────────────────────
    def _connect_selected(self):
        result = self._lb_selected_result()
        if not result:
            return
        url, stype = result[0], result[1]
        self._start_stream(url, stype)

    def _connect_manual(self):
        url = self._url_var.get().strip()
        if not url:
            messagebox.showwarning("Input", "Enter a stream URL.")
            return
        low = url.lower()
        if low.startswith("rtsp://"):
            stype = "RTSP"
        elif any(x in low for x in ("snapshot", "image", "picture", "shot", ".jpg")):
            stype = "JPEG"
        else:
            stype = "MJPEG"
        self._start_stream(url, stype)

    def _start_stream(self, url, stype):
        slot = self._active_slot()
        self._stop_stream(slot)          # stop any running stream in this slot
        slot.running = True
        slot.stop_event.clear()
        slot.url = url
        slot.user = self._user_var.get().strip()
        slot.password = self._pass_var.get()
        slot.frame_count = 0
        slot.lost_count = 0
        slot.fps_times.clear()
        slot.last_image = None
        slot.current_photo = None
        with slot.frame_lock:
            slot.pending_frame = None
        slot.poll_after_id = self.after(33, lambda i=slot.idx: self._poll_slot(i))
        label = f"Connecting [{stype}] → {url[:70]}"
        slot.url_label.configure(text=label)
        slot.lbl_frm.configure(text="0")
        slot.lbl_lost.configure(text="0", text_color="#f0883e")
        slot.lbl_fps.configure(text="—")
        slot.lbl_res.configure(text="—")
        self._refresh_active_status()
        self._stop_stream_btn.configure(state="normal")
        self._connect_btn.configure(state="disabled")
        if stype == "RTSP":
            threading.Thread(target=self._stream_worker_rtsp,
                             args=(slot, url, slot.user, slot.password), daemon=True).start()
        else:
            threading.Thread(target=self._stream_worker,
                             args=(slot, url, stype, slot.user, slot.password), daemon=True).start()

    def _stop_stream(self, slot=None):
        slot = slot or self._active_slot()
        slot.running = False
        slot.stop_event.set()
        if slot.poll_after_id is not None:
            try:
                self.after_cancel(slot.poll_after_id)
            except Exception:
                pass
            slot.poll_after_id = None
        with slot.frame_lock:
            slot.pending_frame = None
        slot.current_photo = None
        if slot.canvas is not None:
            slot.canvas.image = None
        if slot.url_label is not None:
            slot.url_label.configure(text="Stopped")
        if slot.idx == self._active_slot_idx:
            self._refresh_active_status()

    # ── Stream worker (background thread) ─────────────────────────────────
    def _stream_worker(self, slot, url, stype, user, pw):
        resp = None
        try:
            opener = self._make_opener(user, pw, url)
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "NetToolsPro/1.0")
            resp = opener.open(req, timeout=10)
            ct   = resp.headers.get("Content-Type", "").lower()
            self._safe_after(0, lambda: self._set_slot_url(slot, f"▶  {url}"))

            if "multipart" in ct or "mjpeg" in ct:
                self._read_mjpeg(slot, resp)
            else:
                # Treat as single-JPEG / refreshing snapshot
                self._read_jpeg_loop(slot, resp, opener, url)

        except Exception as e:
            self._safe_after(0, lambda err=str(e): (
                self._set_slot_url(slot, f"✗  Error: {err}"),
                self._draw_error(slot, err),
            ))
        finally:
            # Always close the connection to release socket resources
            try:
                if resp is not None:
                    resp.close()
            except Exception:
                pass
            slot.running = False
            self._safe_after(0, self._refresh_active_status)

    # ── RTSP stream worker (cv2) ──────────────────────────────────────────
    def _stream_worker_rtsp(self, slot, url, user, pw):
        """Stream RTSP via OpenCV VideoCapture. Requires opencv-python."""
        if not CV2_AVAILABLE:
            self._safe_after(0, lambda: (
                self._set_slot_url(slot, "✗  opencv-python not installed — required for RTSP"),
                self._draw_error(slot,
                    "RTSP playback requires the opencv-python package.\n\n"
                    "Install it with:\n  pip install opencv-python\n\n"
                    "Then restart NetTools Pro."),
            ))
            slot.running = False
            self._safe_after(0, self._refresh_active_status)
            return

        cap = None
        try:
            # Build URL with embedded credentials if provided
            if user:
                from urllib.parse import urlparse, urlunparse
                p    = urlparse(url)
                host = p.hostname or ""
                port = f":{p.port}" if p.port else ""
                auth_url = urlunparse(p._replace(
                    netloc=f"{user}:{pw}@{host}{port}"))
            else:
                auth_url = url

            # Open with a short timeout — cv2 uses ffmpeg backend on most installs
            cap = cv2.VideoCapture(auth_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)

            if not cap.isOpened():
                self._safe_after(0, lambda: (
                    self._set_slot_url(slot, "✗  RTSP stream failed to open"),
                    self._draw_error(slot,
                        "Could not open RTSP stream.\n\n"
                        "Check URL, credentials, and camera status.\n"
                        "Ensure the camera is reachable on this subnet."),
                ))
                return

            self._safe_after(0, lambda: self._set_slot_url(
                slot, f"▶ RTSP  {url[:75]}"))

            consecutive_fail = 0
            while slot.running and not slot.stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    consecutive_fail += 1
                    if consecutive_fail > 60:
                        self._safe_after(0, lambda: self._set_slot_url(
                            slot, "✗  RTSP: too many consecutive read failures"))
                        break
                    self._safe_after(0, lambda s=slot: self._inc_lost(s))
                    time.sleep(0.03)
                    continue
                consecutive_fail = 0
                # BGR → RGB → PIL Image
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                # Deposit frame in shared slot; UI poller picks up only the latest.
                with slot.frame_lock:
                    slot.pending_frame = (img, "pil")
                time.sleep(0.016)

        except Exception as e:
            self._safe_after(0, lambda err=str(e): (
                self._set_slot_url(slot, f"✗  RTSP Error: {err}"),
                self._draw_error(slot, f"RTSP Error:\n{err}"),
            ))
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
            slot.running = False
            self._safe_after(0, self._refresh_active_status)

    # ── Display PIL image directly (avoids re-encode) ─────────────────────
    def _display_pil_image(self, slot, img):
        """Display a PIL Image on the canvas. Main-thread only."""
        try:
            cw = slot.canvas.winfo_width()
            ch = slot.canvas.winfo_height()
            if cw < 10 or ch < 10:
                return
            img.thumbnail((cw, ch), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            slot.canvas.delete("all")
            slot.canvas.create_image(cw // 2, ch // 2,
                                     image=photo, anchor="center")
            slot.canvas.image = photo
            slot.current_photo = photo
            slot.last_image = img

            slot.frame_count += 1
            now = time.time()
            slot.fps_times.append(now)
            slot.lbl_frm.configure(text=f"{slot.frame_count:,}")
            slot.lbl_res.configure(text=f"{img.width}×{img.height}")
            if slot.frame_count % 10 == 0 and len(slot.fps_times) >= 2:
                span = slot.fps_times[-1] - slot.fps_times[0]
                fps  = len(slot.fps_times) / span if span > 0 else 0
                slot.lbl_fps.configure(text=f"{fps:.1f}")
            if slot.idx == self._active_slot_idx:
                self._refresh_active_status()
        except Exception:
            slot.lost_count += 1
            slot.lbl_lost.configure(text=str(slot.lost_count),
                                    text_color="#f85149")
            if slot.idx == self._active_slot_idx:
                self._refresh_active_status()

    def _poll_slot(self, idx):
        """UI-thread poller: grabs the latest frame from the shared slot.
        Only one frame is ever pending — prevents callback queue buildup
        that would otherwise hold MB-sized PIL Images in lambda closures."""
        slot = self._slots[idx]
        if not slot.running:
            slot.poll_after_id = None
            return
        with slot.frame_lock:
            pending = slot.pending_frame
            slot.pending_frame = None
        if pending is not None:
            data, kind = pending
            if kind == "pil":
                self._display_pil_image(slot, data)
            else:
                self._display_frame(slot, data)
        slot.poll_after_id = self.after(33, lambda i=idx: self._poll_slot(i))

    def _read_mjpeg(self, slot, resp):
        """Parse multipart MJPEG stream using raw JPEG SOI/EOI markers."""
        buf = b""
        while slot.running and not slot.stop_event.is_set():
            try:
                chunk = resp.read(32768)
            except Exception:
                break
            if not chunk:
                break
            buf += chunk
            # Extract all complete JPEG frames from buffer
            while True:
                soi = buf.find(b"\xff\xd8")          # Start Of Image
                if soi == -1:
                    # Preserve a trailing \xff — it could be the first byte of an SOI marker
                    buf = buf[-1:] if buf and buf[-1:] == b"\xff" else b""
                    break
                eoi = buf.find(b"\xff\xd9", soi + 2) # End Of Image
                if eoi == -1:
                    buf = buf[soi:]                  # Keep partial frame
                    break
                jpeg = buf[soi: eoi + 2]
                buf  = buf[eoi + 2:]
                with slot.frame_lock:
                    slot.pending_frame = (jpeg, "jpeg")

    def _read_jpeg_loop(self, slot, first_resp, opener, url):
        """Continuously refresh a single-frame JPEG (snapshot polling)."""
        # Display the first response
        try:
            data = first_resp.read()
            if data:
                with slot.frame_lock:
                    slot.pending_frame = (data, "jpeg")
        except Exception:
            pass

        # Poll every second
        while slot.running and not slot.stop_event.is_set():
            time.sleep(1)
            if slot.stop_event.is_set():
                break
            try:
                req = urllib.request.Request(url)
                req.add_header("Cache-Control", "no-cache")
                req.add_header("User-Agent", "NetToolsPro/1.0")
                with opener.open(req, timeout=5) as resp:
                    data = resp.read()
                if data:
                    with slot.frame_lock:
                        slot.pending_frame = (data, "jpeg")
            except Exception:
                self._safe_after(0, lambda s=slot: self._inc_lost(s))

    # ── Frame display (main thread) ────────────────────────────────────────
    def _inc_lost(self, slot):
        """Increment lost-frame counter — must be called on the main thread."""
        slot.lost_count += 1
        slot.lbl_lost.configure(text=str(slot.lost_count), text_color="#f85149")
        if slot.idx == self._active_slot_idx:
            self._refresh_active_status()

    def _display_frame(self, slot, jpeg_bytes):
        try:
            img = Image.open(_io.BytesIO(jpeg_bytes))
            img.load()

            cw = slot.canvas.winfo_width()
            ch = slot.canvas.winfo_height()
            if cw < 10 or ch < 10:
                return

            # Fit-to-canvas while preserving aspect ratio
            img.thumbnail((cw, ch), Image.LANCZOS)

            photo = ImageTk.PhotoImage(img)
            slot.canvas.delete("all")
            slot.canvas.create_image(cw // 2, ch // 2,
                                     image=photo, anchor="center")
            slot.canvas.image = photo       # Prevent garbage collection
            slot.current_photo = photo
            slot.last_image = img           # Keep for saving

            # Stats
            slot.frame_count += 1
            now = time.time()
            slot.fps_times.append(now)
            slot.lbl_frm.configure(text=f"{slot.frame_count:,}")
            slot.lbl_res.configure(text=f"{img.width}×{img.height}")

            if slot.frame_count % 10 == 0 and len(slot.fps_times) >= 2:
                span = slot.fps_times[-1] - slot.fps_times[0]
                fps  = len(slot.fps_times) / span if span > 0 else 0
                slot.lbl_fps.configure(text=f"{fps:.1f}")
            if slot.idx == self._active_slot_idx:
                self._refresh_active_status()

        except Exception:
            slot.lost_count += 1
            slot.lbl_lost.configure(text=str(slot.lost_count),
                                    text_color="#f85149")
            if slot.idx == self._active_slot_idx:
                self._refresh_active_status()

    def _set_slot_url(self, slot, text):
        slot.url_label.configure(text=text)
        if slot.idx == self._active_slot_idx:
            self._lbl_url.configure(text=text)

    def _draw_error(self, slot, msg):
        slot.canvas.delete("all")
        w = max(slot.canvas.winfo_width(), 400)
        h = max(slot.canvas.winfo_height(), 200)
        slot.canvas.create_text(w // 2, h // 2,
                                text=f"✗  Connection failed\n\n{msg}\n\n"
                                     "Check IP, port, credentials and camera stream URL.",
                                font=("Consolas", 11), fill="#f85149",
                                justify="center", width=w - 40)

    # ── Snapshot ───────────────────────────────────────────────────────────
    def _snapshot(self):
        if not PILLOW_AVAILABLE:
            return
        slot = self._active_slot()
        img = slot.last_image
        if img is None:
            messagebox.showinfo("Snapshot", "No frame captured yet.")
            return
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        ip_source = slot.url or self._ip_var.get().strip()
        ip  = re.sub(r"[^\d.]", "_", ip_source)[:60] or f"slot_{slot.idx + 1}"
        fn  = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            initialfile=f"snapshot_{ip}_{ts}.jpg",
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png"), ("All files", "*.*")],
            title="Save Snapshot",
        )
        if fn:
            try:
                fmt = "PNG" if fn.lower().endswith(".png") else "JPEG"
                img.save(fn, fmt, quality=95)
                messagebox.showinfo("Saved", f"Snapshot saved:\n{fn}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    # ── Copy RTSP URLs ─────────────────────────────────────────────────────
    def _copy_rtsp_urls(self):
        ip = self._ip_var.get().strip()
        if not ip:
            messagebox.showwarning("Input", "Enter a camera IP first.")
            return
        lines = [t.format(ip=ip) for t in CAMERA_RTSP_TEMPLATES]
        text  = "\n".join(lines)
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copied",
                            f"{len(lines)} RTSP template URLs copied to clipboard.\n\n"
                            "Paste into VLC →  Media › Open Network Stream")

    # ── Open web UI ────────────────────────────────────────────────────────
    def _open_web(self):
        ip   = self._ip_var.get().strip()
        port = self._port_var.get()
        if not ip:
            messagebox.showwarning("Input", "Enter a camera IP first.")
            return
        url = f"http://{ip}:{port}" if port != 80 else f"http://{ip}"
        try:
            _pu_shell.open_url(url)
        except Exception as e:
            messagebox.showerror("Error", str(e))


# ==================== Sidebar ====================
class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, on_select, **kwargs):
        super().__init__(parent, fg_color="#010409", corner_radius=0, **kwargs)
        self._on_select = on_select
        self._btns = {}            # tool key → CTkButton
        self._cat_frames = {}      # cat_key → CTkFrame (collapsible)
        self._cat_btns = {}        # cat_key → CTkButton (header)
        self._cat_labels = {}      # cat_key → display label (without arrow)
        self._expanded_cat = None  # currently expanded category key
        self._tool_to_cat = {}     # tool key → category key
        self._build()

    def _build(self):
        # Logo / title — fixed at top
        logo = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=0, height=64)
        logo.pack(fill="x")
        logo.pack_propagate(False)
        ctk.CTkLabel(logo, text=APP_NAME,
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color="#79c0ff").pack(side="left", padx=16, pady=10)
        ctk.CTkLabel(logo, text=f"v{APP_VERSION}",
                     font=ctk.CTkFont(size=10),
                     text_color="#8b949e").pack(side="left", pady=10)

        ctk.CTkFrame(self, fg_color="#21262d", height=1).pack(fill="x")

        # Scrollable navigation area
        nav = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                     scrollbar_button_color="#21262d",
                                     scrollbar_button_hover_color="#30363d")
        nav.pack(fill="both", expand=True, pady=(4, 0))

        # Build accordion from SIDEBAR_STRUCTURE
        current_cat_frame = None
        for type_, label, key, cat_key in SIDEBAR_STRUCTURE:
            if type_ == "standalone":
                btn = ctk.CTkButton(
                    nav, text=label, anchor="w",
                    font=ctk.CTkFont(size=12),
                    fg_color="transparent", hover_color="#21262d",
                    text_color="#c9d1d9", height=34, corner_radius=6,
                    command=lambda k=key: self._select(k),
                )
                btn.pack(fill="x", padx=8, pady=(2, 6))
                self._btns[key] = btn

            elif type_ == "category":
                self._cat_labels[key] = label
                cat_btn = ctk.CTkButton(
                    nav, text=f"> {label}", anchor="w",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    fg_color="transparent", hover_color="#21262d",
                    text_color="#8b949e", height=36, corner_radius=6,
                    command=lambda k=key: self._toggle_category(k),
                )
                cat_btn.pack(fill="x", padx=8, pady=(4, 0))
                self._cat_btns[key] = cat_btn

                # Collapsible frame for tools — hidden by default
                cat_frame = ctk.CTkFrame(nav, fg_color="transparent")
                self._cat_frames[key] = cat_frame
                current_cat_frame = None  # don't pack yet

            elif type_ == "tool":
                self._tool_to_cat[key] = cat_key
                parent_frame = self._cat_frames[cat_key]
                btn = ctk.CTkButton(
                    parent_frame, text=label, anchor="w",
                    font=ctk.CTkFont(size=12),
                    fg_color="transparent", hover_color="#21262d",
                    text_color="#c9d1d9", height=30, corner_radius=6,
                    command=lambda k=key: self._select(k),
                )
                btn.pack(fill="x", padx=(24, 8), pady=1)
                self._btns[key] = btn

        # Footer — fixed at bottom
        info = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=0)
        info.pack(fill="x", side="bottom")
        local_ip = get_local_ip()
        ctk.CTkLabel(info, text=f"Local IP: {local_ip}",
                     font=ctk.CTkFont(size=10), text_color="#8b949e").pack(anchor="w", padx=12, pady=4)

        # Theme toggle uses plain ASCII to avoid font fallback artifacts.
        self._theme = SettingsManager.get("theme", "dark")
        ctk.CTkButton(info, text="Toggle Theme", command=self._toggle_theme,
                      fg_color="transparent", hover_color="#21262d",
                      text_color="#8b949e", height=28, font=ctk.CTkFont(size=10)
                      ).pack(fill="x", padx=4, pady=(0, 2))

        # About button
        ctk.CTkButton(info, text="i  About", command=self._show_about,
                      fg_color="transparent", hover_color="#21262d",
                      text_color="#8b949e", height=26, font=ctk.CTkFont(size=10)
                      ).pack(fill="x", padx=4, pady=(0, 6))

    # ---- Accordion logic ----

    def _toggle_category(self, cat_key):
        if self._expanded_cat == cat_key:
            self._collapse_category(cat_key)
            self._expanded_cat = None
        else:
            if self._expanded_cat:
                self._collapse_category(self._expanded_cat)
            self._expand_category(cat_key)
            self._expanded_cat = cat_key

    def _expand_category(self, cat_key):
        self._cat_frames[cat_key].pack(fill="x", after=self._cat_btns[cat_key])
        lbl = self._cat_labels[cat_key]
        self._cat_btns[cat_key].configure(
            text=f"v {lbl}",
            text_color="#c9d1d9",
            fg_color="#161b22",
        )

    def _collapse_category(self, cat_key):
        self._cat_frames[cat_key].pack_forget()
        lbl = self._cat_labels[cat_key]
        self._cat_btns[cat_key].configure(
            text=f"> {lbl}",
            text_color="#8b949e",
            fg_color="transparent",
        )

    # ---- Selection & highlighting ----

    def _highlight(self, key):
        for k, b in self._btns.items():
            if k == key:
                b.configure(fg_color="#21262d", text_color="#79c0ff")
            else:
                b.configure(fg_color="transparent", text_color="#c9d1d9")

    def _ensure_category_expanded(self, key):
        """Auto-expand the category containing key, if any."""
        cat = self._tool_to_cat.get(key)
        if cat and self._expanded_cat != cat:
            if self._expanded_cat:
                self._collapse_category(self._expanded_cat)
            self._expand_category(cat)
            self._expanded_cat = cat

    def _select(self, key):
        self._highlight(key)
        self._ensure_category_expanded(key)
        self._on_select(key)

    def select_no_callback(self, key):
        """Update sidebar button styling without triggering frame switch.
        Used by programmatic navigation (e.g. 'View Stream' from Camera Finder)
        where the frame is already being raised separately."""
        self._highlight(key)
        self._ensure_category_expanded(key)

    def _toggle_theme(self):
        self._theme = "light" if self._theme == "dark" else "dark"
        ctk.set_appearance_mode(self._theme)
        SettingsManager.set("theme", self._theme)

    def _show_about(self):
        win = ctk.CTkToplevel(self)
        win.title(f"About {APP_NAME}")
        win.geometry("460x360")
        win.resizable(False, False)
        win.grab_set()   # Modal

        ctk.CTkLabel(win, text=APP_NAME,
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#79c0ff").pack(pady=(28, 4))
        ctk.CTkLabel(win, text=f"Version {APP_VERSION}",
                     font=ctk.CTkFont(size=12),
                     text_color="#8b949e").pack(pady=(0, 2))
        ctk.CTkLabel(win, text=APP_DESCRIPTION,
                     font=ctk.CTkFont(size=12),
                     text_color="#c9d1d9").pack(pady=(0, 18))

        sep = ctk.CTkFrame(win, fg_color="#21262d", height=1)
        sep.pack(fill="x", padx=30)

        info_rows = [
            ("Author",    APP_AUTHOR),
            ("License",   APP_LICENSE),
            ("Copyright", APP_COPYRIGHT),
        ]
        for label, value in info_rows:
            row = ctk.CTkFrame(win, fg_color="transparent")
            row.pack(fill="x", padx=36, pady=4)
            ctk.CTkLabel(row, text=f"{label}:",
                         width=90, anchor="w",
                         font=ctk.CTkFont(size=11),
                         text_color="#8b949e").pack(side="left")
            ctk.CTkLabel(row, text=value,
                         anchor="w",
                         font=ctk.CTkFont(size=11),
                         text_color="#c9d1d9").pack(side="left")

        sep2 = ctk.CTkFrame(win, fg_color="#21262d", height=1)
        sep2.pack(fill="x", padx=30, pady=(12, 0))

        deps_txt = (
            f"Python {sys.version.split()[0]}  \u00b7  customtkinter  \u00b7  psutil  \u00b7  "
            f"dnspython  \u00b7  Pillow"
        )
        ctk.CTkLabel(win, text=deps_txt,
                     font=ctk.CTkFont(size=10),
                     text_color="#8b949e").pack(pady=(10, 0))

        mit_text = (
            "Permission is hereby granted, free of charge, to any person obtaining\n"
            "a copy of this software to use, copy, modify, merge, publish, distribute,\n"
            "sublicense, and/or sell copies, subject to the MIT License conditions."
        )
        ctk.CTkLabel(win, text=mit_text,
                     font=ctk.CTkFont(size=9),
                     text_color="#6e7681",
                     justify="center").pack(pady=(6, 16))

        ctk.CTkButton(win, text="Close", command=win.destroy,
                      fg_color="#21262d", hover_color="#30363d",
                      width=100).pack()

    def select_default(self):
        self._select(SIDEBAR_TOOLS[0][1])


# ==================== System Tools ====================

# Log file location (created on first use)
SYSTOOLS_LOG_PATH = pathlib.Path.home() / "Documents" / "NetTools Pro" / "systools.log"

# ==================== Script Lab ====================

# Default folder where the script browser looks for scripts
SCRIPT_LAB_DEFAULT_DIR = pathlib.Path.home() / "Documents" / "NetTools Pro" / "Scripts"

# File extensions that can be executed via subprocess (platform-specific)
_RUNNABLE_EXTS  = _pu_scripting.script_extensions()
# File extensions that can be opened in the editor but not executed
_VIEW_ONLY_EXTS = {".txt", ".json", ".yaml", ".yml", ".ini"}
# All extensions shown in the script browser and open-file dialog
_ALL_SCRIPT_EXTS = _RUNNABLE_EXTS | _VIEW_ONLY_EXTS

# Runnable script glob used in filedialog filters (platform-specific)
_RUNNABLE_GLOB = " ".join(f"*{ext}" for ext in sorted(_RUNNABLE_EXTS))

SCRIPT_LAB_FILETYPES = [
    ("Script files", _RUNNABLE_GLOB),
    ("Text / Config", "*.txt *.json *.yaml *.yml *.ini"),
    ("All files", "*.*"),
]

# ---------------------------------------------------------------------------
# Service lists — taken verbatim from SkipperToolkit.ps1 ($Script:SafeDisableServices,
# $Script:AggressiveExtraDisableServices, $Script:ManualServices).
#
# SAFE profile (29 services → set Disabled):
#   ASUS/OEM bloat, Xbox services, telemetry, and home-network services
#   that are rarely needed. Does NOT touch DPS, WdiServiceHost, WdiSystemHost,
#   WerSvc, Hyper-V, WSL, Defender, Firewall, or Security Center.
#
# MANUAL services (2 services → set Manual, not Disabled):
#   UsoSvc (Windows Update Orchestrator) and WSearch (Windows Search)
#   are set to Manual so they can still be started on demand.
#
# AGGRESSIVE additions (16 extra services → set Disabled):
#   Includes diagnostic helpers (DPS, WdiServiceHost, WdiSystemHost, WerSvc),
#   developer/IT services (WinRM, lmhosts), and Hyper-V / WSL / container
#   networking services. Only present in AGGRESSIVE profile.
#   Windows Defender, Firewall, and Security Center are NOT included.
# ---------------------------------------------------------------------------

# Developer note — SAFE is *performance-oriented*, not zero-risk:
#   RemoteRegistry  → may be needed by some remote-admin tools
#   WebClient       → required by some mapped-drive / SharePoint workflows
#   SSDPSRV / upnphost → disables network device discovery (UPnP)
#   SharedAccess    → disables Internet Connection Sharing
#   DiagTrack       → Windows telemetry (intentional)
# Review this list before running on a production or developer machine.

# SAFE — disable these (29 total)
_SAFE_SERVICES = [
    # ASUS / OEM bloat
    "AsusAppService", "ASUSSoftwareManager", "ASUSSwitch", "AsusCertService",
    "ASUSOptimization", "ASUSSystemAnalysis", "ASUSSystemDiagnosis", "AsusPTPService",
    # Telemetry / misc
    "DiagTrack", "whesvc", "wisvc", "InventorySvc", "RetailDemo", "MapsBroker",
    "Fax", "RemoteRegistry", "PushToInstall", "WbioSrvc", "wcncsvc", "lfsvc",
    # Xbox
    "XboxGipSvc", "XblAuthManager", "XboxNetApiSvc", "XblGameSave",
    # Rarely-needed home network services
    "SharedAccess", "SSDPSRV", "upnphost", "WwanSvc", "WebClient",
]

# MANUAL — set startup type to Manual (not Disabled) — both profiles
_MANUAL_SERVICES = ["UsoSvc", "WSearch"]

# AGGRESSIVE additions — disable these on top of SAFE (16 additional)
# WARNING: affects diagnostics, WinRM, Hyper-V, WSL, and container networking
_AGGRESSIVE_ADDITIONS = [
    "DPS", "WdiServiceHost", "WdiSystemHost", "WerSvc",
    "lmhosts", "dot3svc", "WinRM",
    "hns", "WSLService", "HvHost",
    "wmiApSrv", "PcaSvc", "StiSvc", "TapiSrv", "WManSvc",
    "perceptionsimulation",
]

# Combined list for aggressive debloat (29 + 16 = 45 to disable)
_ALL_DEBLOAT_SERVICES = _SAFE_SERVICES + [
    s for s in _AGGRESSIVE_ADDITIONS if s not in _SAFE_SERVICES
]


class SystemToolsFrame(BaseToolFrame):
    """Windows maintenance, repair, and service management tools."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.dry_run_var = tk.BooleanVar(value=False)
        self._log_dir_ready = False  # lazy-init: create log dir on first write
        self._backend = system_backend.get_backend()
        self._build()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(self):
        self.make_header("⚙️  System Tools",
                         "Windows maintenance, repair, and service management")

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True)

        # ── Left controls card ────────────────────────────────────────────────
        left = self.make_card(content, title="Controls", width=264)
        left.pack(side="left", fill="y", padx=(20, 8), pady=(0, 20))
        left.pack_propagate(False)

        # Admin status badge
        self.admin_label = ctk.CTkLabel(left, text="● Checking...",
                                        text_color="#8b949e", anchor="w",
                                        font=ctk.CTkFont(size=11))
        self.admin_label.pack(fill="x", padx=12, pady=(10, 0))
        ctk.CTkButton(left, text="Recheck", height=22,
                      command=self._update_admin_badge,
                      fg_color="#21262d", hover_color="#30363d",
                      font=ctk.CTkFont(size=11)).pack(fill="x", padx=12, pady=(4, 6))

        # Dry-run toggle
        ctk.CTkFrame(left, height=1, fg_color="#30363d").pack(fill="x", padx=8, pady=(0, 6))
        ctk.CTkCheckBox(left, text="Dry Run (preview only)",
                        variable=self.dry_run_var).pack(fill="x", padx=12, pady=(0, 6))
        ctk.CTkFrame(left, height=1, fg_color="#30363d").pack(fill="x", padx=8, pady=(0, 4))

        def section(title):
            ctk.CTkLabel(left, text=title, text_color="#79c0ff",
                         font=ctk.CTkFont(size=11, weight="bold")).pack(
                             anchor="w", padx=12, pady=(8, 2))

        def btn(label, cmd, fg=None, hov=None):
            kw = {}
            if fg:
                kw["fg_color"] = fg
            if hov:
                kw["hover_color"] = hov
            ctk.CTkButton(left, text=label, command=cmd, **kw).pack(
                fill="x", padx=10, pady=(2, 0))

        TOOLS = self._backend.available_tools()

        if not TOOLS:
            ctk.CTkLabel(
                left,
                text="Ingen verktøy støttet\npå denne plattformen\n(Linux-støtte: Fase 8)",
                text_color="#8b949e", justify="left",
                font=ctk.CTkFont(size=11)
            ).pack(padx=12, pady=(10, 6))
        else:
            # Diagnostics
            if "diagnostics" in TOOLS:
                section("Diagnostics")
                btn("Run System Diagnostics", self._run_diagnostics)

            # System Repair
            if "sfc" in TOOLS or "dism" in TOOLS:
                section("System Repair")
                if "sfc" in TOOLS:
                    btn("SFC Scan", self._run_sfc)
                if "dism" in TOOLS:
                    btn("DISM Repair", self._run_dism)

            # Service Debloat
            if "debloat" in TOOLS:
                section("Service Debloat")
                btn(f"Safe Debloat  ({len(_SAFE_SERVICES)} off, {len(_MANUAL_SERVICES)} manual)",
                    self._run_safe_debloat, "#E65100", "#BF360C")
                btn(f"Aggressive  ({len(_ALL_DEBLOAT_SERVICES)} off, {len(_MANUAL_SERVICES)} manual)",
                    self._run_aggressive_debloat, "#B71C1C", "#7F0000")

            # Backup / Restore
            if "backup" in TOOLS or "restore" in TOOLS:
                section("Backup / Restore")
                if "backup" in TOOLS:
                    btn("Backup Services", self._run_backup)
                if "restore" in TOOLS:
                    btn("Restore Services", self._run_restore)

        # Log folder button at bottom
        ctk.CTkFrame(left, height=1, fg_color="#30363d").pack(fill="x", padx=8, pady=(10, 4))
        ctk.CTkButton(left, text="📂  Open Log Folder",
                      command=self._open_log_folder,
                      fg_color="#21262d", hover_color="#30363d",
                      font=ctk.CTkFont(size=11)).pack(fill="x", padx=10, pady=(2, 10))

        # ── Right output area ─────────────────────────────────────────────────
        right = ctk.CTkFrame(content, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)
        self.output = self.make_output(right)

        # Set admin badge on load (start_poll is called per-operation in each _run_X)
        self._update_admin_badge()

    # ── Admin detection ───────────────────────────────────────────────────────

    def _is_admin(self) -> bool:
        return _pu_detect.is_admin()

    def _update_admin_badge(self):
        if self._is_admin():
            self.admin_label.configure(
                text="● Running as Administrator", text_color="#3fb950")
        else:
            self.admin_label.configure(
                text="● Not Admin — SFC/DISM/debloat may fail",
                text_color="#d29922")

    # ── Logging ───────────────────────────────────────────────────────────────

    def _log(self, message: str):
        """Append a timestamped line to the system tools log file."""
        try:
            # Create parent dir once, not on every write
            if not self._log_dir_ready:
                SYSTOOLS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
                self._log_dir_ready = True
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(SYSTOOLS_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] {message}\n")
        except OSError:
            pass  # Never crash the UI over a logging failure

    def _open_log_folder(self):
        folder = SYSTOOLS_LOG_PATH.parent
        folder.mkdir(parents=True, exist_ok=True)
        _pu_shell.open_folder(folder)

    # ── Guard helpers ─────────────────────────────────────────────────────────

    def _abort_if_running(self) -> bool:
        if self.running:
            self.output.append("An operation is already running. Please wait.", "warning")
            return True
        return False

    def _finish(self, summary: str, tag: str = "success"):
        """Post summary line, log it, and reset UI state (must be called from worker thread)."""
        self.q(f"\n{'─' * 55}", "dim")
        self.q(summary, tag)
        self._log(f"FINISH: {summary}")
        self._safe_after(0, self.ui_done)  # ui_done() resets self.running + button states

    # ── Pre-debloat auto-backup (synchronous) ────────────────────────────────

    def _do_backup(self, path: str):
        """Wrap backend export with frame-level logging and user feedback.
        Replaces the old _do_quick_backup — backend does the work, frame handles UX."""
        try:
            self._backend.export_services(path)
            self.q(f"Auto-backup saved: {path}", "info")
            self._log(f"Auto-backup: {path}")
        except Exception as e:
            self.q(f"Backup failed: {e}", "error")
            self._log(f"Auto-backup FAILED: {e}")
            raise

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def _run_diagnostics(self):
        if self._abort_if_running():
            return
        self.ui_started()
        self.output.clear()
        self._log("START: System Diagnostics")
        self.output.append("Running system diagnostics — please wait...", "header")
        self.start_poll()
        threading.Thread(target=self._worker_diagnostics, daemon=True).start()

    def _worker_diagnostics(self):
        try:
            for line, tag in self._backend.run_diagnostics(self.stop_event):
                if self.stop_event.is_set():
                    break
                self.q(line, tag)
        except NotImplementedError as e:
            self.q(str(e), "error")
            self._finish("Not supported on this platform.", "error")
            return
        except Exception as e:
            self.q(f"Error: {e}", "error")
            self._finish(f"Diagnostics failed: {e}", "error")
            return
        if self.stop_event.is_set():
            self._finish("Diagnostics aborted.", "warning")
        else:
            self._finish("Diagnostics complete.", "success")

    # ── SFC Scan ──────────────────────────────────────────────────────────────

    def _run_sfc(self):
        if self._abort_if_running():
            return
        self.ui_started()
        self.output.clear()
        self._log("START: SFC Scan")
        self.output.append("Running sfc /scannow — this may take several minutes...", "header")
        if not self._is_admin():
            self.output.append(
                "Warning: SFC requires Administrator privileges — output may show an error.",
                "warning")
        self.start_poll()
        threading.Thread(target=self._worker_sfc, daemon=True).start()

    def _worker_sfc(self):
        last_tag = "success"
        last_msg = "SFC scan complete."
        try:
            for line, tag in self._backend.run_sfc(self.stop_event):
                if self.stop_event.is_set():
                    break
                self.q(line, tag)
                # Backend yielder siste linje med final tag — fang det
                if tag in ("success", "warning", "error"):
                    last_tag, last_msg = tag, line
        except NotImplementedError as e:
            self.q(str(e), "error")
            self._finish("Not supported on this platform.", "error")
            return
        except Exception as e:
            self.q(f"Error: {e}", "error")
            self._finish(f"SFC failed: {e}", "error")
            return
        if self.stop_event.is_set():
            self._finish("SFC aborted.", "warning")
        else:
            self._finish(last_msg, last_tag)

    # ── DISM Repair ───────────────────────────────────────────────────────────

    def _run_dism(self):
        if self._abort_if_running():
            return
        self.ui_started()
        self.output.clear()
        self._log("START: DISM Repair")
        self.output.append(
            "Running DISM /RestoreHealth — this can take 15–45 minutes...", "header")
        if not self._is_admin():
            self.output.append(
                "Warning: DISM requires Administrator privileges — output may show an error.",
                "warning")
        self.start_poll()
        threading.Thread(target=self._worker_dism, daemon=True).start()

    def _worker_dism(self):
        try:
            for line, tag in self._backend.run_dism(self.stop_event):
                if self.stop_event.is_set():
                    break
                self.q(line, tag)
        except NotImplementedError as e:
            self.q(str(e), "error")
            self._finish("Not supported on this platform.", "error")
            return
        except Exception as e:
            self.q(f"Error: {e}", "error")
            self._finish(f"DISM failed: {e}", "error")
            return
        if self.stop_event.is_set():
            self._finish("DISM aborted.", "warning")
        else:
            self._finish("DISM repair complete.", "success")

    # ── Service Backup ────────────────────────────────────────────────────────

    def _run_backup(self):
        if self._abort_if_running():
            return
        path = filedialog.asksaveasfilename(
            title="Save Service Backup",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="services_backup.json",
            initialdir=str(pathlib.Path.home() / "Documents"))
        if not path:
            return
        self._log(f"Backup requested to: {path}")
        self.ui_started()
        self.output.clear()
        self.output.append(f"Exporting service states to:\n  {path}", "header")
        self.start_poll()
        threading.Thread(target=self._worker_backup, args=(path,), daemon=True).start()

    def _worker_backup(self, path: str):
        self._do_backup(path)
        self._finish(f"Backup complete: {pathlib.Path(path).name}", "success")

    # ── Service Restore ───────────────────────────────────────────────────────

    def _run_restore(self):
        if self._abort_if_running():
            return
        path = filedialog.askopenfilename(
            title="Select Service Backup",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=str(pathlib.Path.home() / "Documents"))
        if not path:
            return
        # Validate the JSON file before spawning the thread
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list) or not data:
                raise ValueError("File is empty or not a list")
            if not {"Name", "StartType"}.issubset(data[0].keys()):
                raise ValueError("Missing required fields: Name, StartType")
        except Exception as e:
            messagebox.showerror("Invalid Backup File", str(e))
            return
        if not messagebox.askyesno(
                "Restore Services",
                f"Restore startup types for {len(data)} services from:\n{path}\n\n"
                "This will modify system service settings. Continue?",
                icon="warning"):
            return
        dry = self.dry_run_var.get()
        self._log(f"Restore requested from: {path}")
        self.ui_started()
        self.output.clear()
        self.output.append(
            f"{'[DRY RUN] ' if dry else ''}Restoring {len(data)} services "
            f"from {pathlib.Path(path).name}...", "header")
        self.start_poll()
        # Pass parsed data and dry flag — avoids re-reading the file from the thread
        threading.Thread(target=self._worker_restore, args=(data, path, dry),
                         daemon=True).start()

    def _worker_restore(self, data: list, path: str, dry: bool):
        """data and dry are pre-captured on the main thread to avoid thread-unsafe reads."""
        ok = fail = 0
        for record in data:
            if self.stop_event.is_set():
                break
            name = record.get("Name", "").strip()
            start_type = record.get("StartType", "").strip()
            if not name or not start_type:
                continue
            success, line = self._backend.set_service_startup(name, start_type, dry)
            tag = "warning" if dry else ("success" if success else "error")
            self.q(line, tag)
            if success:
                ok += 1
            else:
                fail += 1
            if not dry:
                self._log(line)
        self._finish(
            f"Restore complete — OK: {ok}  Failed: {fail}",
            "success" if fail == 0 else "warning")

    # ── Safe Debloat ──────────────────────────────────────────────────────────

    def _run_safe_debloat(self):
        if self._abort_if_running():
            return
        dry = self.dry_run_var.get()
        if not messagebox.askyesno(
                "Safe Debloat",
                f"Disable {len(_SAFE_SERVICES)} non-essential services and set "
                f"{len(_MANUAL_SERVICES)} to Manual startup.\n\n"
                f"{'DRY RUN — no changes will be applied.' if dry else 'A timestamped backup will be saved to Documents/NetTools Pro first.'}\n\n"
                "Continue?",
                icon="warning"):
            return
        # Pre-compute backup path on main thread (mkdir is fast); actual backup runs in worker
        backup_path = None
        if not dry:
            p = (pathlib.Path.home() / "Documents" / "NetTools Pro" /
                 f"svc_pre_debloat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            p.parent.mkdir(parents=True, exist_ok=True)
            backup_path = str(p)
        self.ui_started()
        self.output.clear()
        self._log("START: Safe Debloat")
        self.start_poll()
        threading.Thread(target=self._worker_debloat,
                         args=(_SAFE_SERVICES, "Safe Debloat", dry, backup_path),
                         daemon=True).start()

    # ── Aggressive Debloat ────────────────────────────────────────────────────

    def _run_aggressive_debloat(self):
        if self._abort_if_running():
            return
        # Stage 1 — strong warning with accurate service description
        if not messagebox.askyesno(
                "Aggressive Debloat — WARNING",
                f"AGGRESSIVE mode disables {len(_ALL_DEBLOAT_SERVICES)} services and sets "
                f"{len(_MANUAL_SERVICES)} to Manual.\n\n"
                "In addition to Safe-mode services, this disables:\n"
                "  • Diagnostic helpers: DPS, WdiServiceHost, WdiSystemHost, WerSvc\n"
                "  • Remote management: WinRM, lmhosts, dot3svc\n"
                "  • Hyper-V / WSL: HvHost, WSLService, hns\n"
                "  • Misc: wmiApSrv, PcaSvc, StiSvc, TapiSrv, WManSvc, perceptionsimulation\n\n"
                "This can affect WSL, Hyper-V, remote desktop, and dev/IT tooling.\n"
                "Do you want to continue?",
                icon="warning"):
            return
        # Stage 2 — final confirmation
        if not messagebox.askyesno(
                "Final Confirmation",
                "Are you absolutely sure?\n\nThis is difficult to reverse without a backup.",
                icon="warning"):
            return
        dry = self.dry_run_var.get()
        # Pre-compute backup path on main thread; actual backup runs in worker
        backup_path = None
        if not dry:
            p = (pathlib.Path.home() / "Documents" / "NetTools Pro" /
                 f"svc_pre_aggressive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            p.parent.mkdir(parents=True, exist_ok=True)
            backup_path = str(p)
        self.ui_started()
        self.output.clear()
        self._log("START: Aggressive Debloat")
        self.start_poll()
        threading.Thread(target=self._worker_debloat,
                         args=(_ALL_DEBLOAT_SERVICES, "Aggressive Debloat", dry, backup_path),
                         daemon=True).start()

    # ── Debloat worker (shared by safe + aggressive) ──────────────────────────

    def _worker_debloat(self, service_list, label, dry, backup_path):
        """Disable each service then set _MANUAL_SERVICES to Manual.
        dry and backup_path are pre-captured on the main thread.
        backup_path: if set, save auto-backup JSON before touching any service."""
        # Backup first so it exists before any service is changed
        if backup_path:
            self._do_backup(backup_path)

        self.q(f"{'─' * 55}", "dim")
        self.q(f"{label}  {'[DRY RUN]' if dry else ''}  "
               f"({len(service_list)} off, {len(_MANUAL_SERVICES)} manual)", "header")
        ok = fail = 0

        # Phase 1 — disable services
        for svc in service_list:
            if self.stop_event.is_set():
                self.q("Stopped by user.", "warning")
                self._finish(f"{label} stopped — OK: {ok}  Failed: {fail}", "warning")
                return
            success, line = self._backend.set_service_startup(svc, "Disabled", dry)
            self.q(line, "warning" if dry else ("success" if success else "error"))
            if success:
                ok += 1
            else:
                fail += 1
            if not dry:
                self._log(line)

        # Phase 2 — set manual services to Manual startup (both profiles)
        if _MANUAL_SERVICES:
            self.q(f"{'─' * 30}", "dim")
            self.q("Setting to Manual startup:", "dim")
        for svc in _MANUAL_SERVICES:
            if self.stop_event.is_set():
                break
            success, line = self._backend.set_service_startup(svc, "Manual", dry)
            self.q(line, "warning" if dry else ("success" if success else "error"))
            if success:
                ok += 1
            else:
                fail += 1
            if not dry:
                self._log(line)

        self._finish(
            f"{label} complete — OK: {ok}  Failed: {fail}",
            "success" if fail == 0 else "warning")


# ==================== Script Lab ====================
class ScriptLabFrame(BaseToolFrame):
    """Browse, edit, and run scripts (.ps1 .py .bat .cmd) from inside the GUI."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        # ── File / editor state ───────────────────────────────────────────────
        self._current_path = ""      # absolute path of the loaded file; "" = none
        self._dirty = False          # True when editor has unsaved changes
        self._proc = None            # active subprocess.Popen or None
        self._script_paths = []      # parallel list to _listbox — full absolute paths
        self._path_var  = tk.StringVar(value="No file loaded")
        self._dirty_var = tk.StringVar(value="")
        self._build()
        self._refresh_script_list()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(self):
        self.make_header("📝  Script Lab",
                         "Browse, edit and run scripts (.ps1, .py, .bat, .cmd)")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # ── Left panel ────────────────────────────────────────────────────────
        left = ctk.CTkFrame(body, fg_color="#161b22", corner_radius=8, width=220)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        def _sec(title):
            ctk.CTkLabel(left, text=title, text_color="#79c0ff",
                         font=ctk.CTkFont(size=11, weight="bold")
                         ).pack(anchor="w", padx=12, pady=(10, 2))

        def _btn(label, cmd, fg=None, hov=None, **kw):
            b = ctk.CTkButton(left, text=label, command=cmd, height=28,
                              fg_color=fg or "#21262d",
                              hover_color=hov or "#30363d", **kw)
            b.pack(fill="x", padx=8, pady=(2, 0))
            return b

        # Script library section
        _sec("Script Library")

        list_wrap = ctk.CTkFrame(left, fg_color="#0d1117", corner_radius=6)
        list_wrap.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        list_sb = ctk.CTkScrollbar(list_wrap)
        list_sb.pack(side="right", fill="y", padx=(0, 2), pady=2)

        self._listbox = tk.Listbox(
            list_wrap,
            bg="#0d1117", fg="#c9d1d9",
            selectbackground="#264f78", selectforeground="#ffffff",
            font=("Consolas", 9),
            relief="flat", borderwidth=0,
            highlightthickness=0,
            yscrollcommand=list_sb.set,
            activestyle="none",
        )
        self._listbox.pack(fill="both", expand=True, padx=2, pady=2)
        list_sb.configure(command=self._listbox.yview)
        self._listbox.bind("<Double-Button-1>", lambda e: self._load_selected())

        _btn("📂  Open Script",  self._open_script)
        _btn("🔄  Refresh",      self._refresh_script_list)
        _btn("📄  New Script",   self._new_script)
        _btn("📁  Open Folder",  self._open_script_folder)

        # Separator
        ctk.CTkFrame(left, height=1, fg_color="#30363d").pack(
            fill="x", padx=8, pady=(6, 4))

        # Actions section
        _sec("Actions")
        _btn("💾  Save",        self._save_script)
        _btn("💾  Save As…",    self._save_script_as)

        ctk.CTkFrame(left, height=1, fg_color="#30363d").pack(
            fill="x", padx=8, pady=(6, 4))

        # Run / Stop — named start_btn / stop_btn for BaseToolFrame auto-management
        self.start_btn = ctk.CTkButton(
            left, text="▶  Run Script", command=self._run_script,
            fg_color="#238636", hover_color="#2ea043",
            height=32, state="disabled")
        self.start_btn.pack(fill="x", padx=8, pady=(0, 4))

        self.stop_btn = ctk.CTkButton(
            left, text="⏹  Stop", command=self._stop_script,
            fg_color="#da3633", hover_color="#f85149",
            height=32, state="disabled")
        self.stop_btn.pack(fill="x", padx=8, pady=(0, 10))

        # ── Right pane ────────────────────────────────────────────────────────
        right = ctk.CTkFrame(body, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)

        # Path bar
        path_bar = ctk.CTkFrame(right, fg_color="#161b22", corner_radius=8, height=32)
        path_bar.pack(fill="x", pady=(0, 6))
        path_bar.pack_propagate(False)

        ctk.CTkLabel(path_bar, textvariable=self._path_var,
                     font=ctk.CTkFont(size=10, family="Consolas"),
                     text_color="#8b949e", anchor="w"
                     ).pack(side="left", padx=12)

        self._dirty_label = ctk.CTkLabel(
            path_bar, textvariable=self._dirty_var,
            font=ctk.CTkFont(size=10), text_color="#8b949e", anchor="e")
        self._dirty_label.pack(side="right", padx=10)

        # Editor (fills vertically, expands with window)
        editor_wrap = ctk.CTkFrame(right, fg_color="#161b22", corner_radius=8)
        editor_wrap.pack(fill="both", expand=True, pady=(0, 6))

        self.editor = self._make_editor(editor_wrap)

        # Output area (fixed height, does not expand)
        output_wrap = ctk.CTkFrame(right, fg_color="#161b22", corner_radius=8, height=220)
        output_wrap.pack(fill="x")
        output_wrap.pack_propagate(False)

        out_hdr = ctk.CTkFrame(output_wrap, fg_color="transparent")
        out_hdr.pack(fill="x", padx=10, pady=(6, 0))

        ctk.CTkLabel(out_hdr, text="Output",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#79c0ff").pack(side="left")

        self._admin_note = ctk.CTkLabel(
            out_hdr, text="", font=ctk.CTkFont(size=10), text_color="#d29922")
        self._admin_note.pack(side="left", padx=10)
        self._update_admin_note()

        ctk.CTkButton(out_hdr, text="🗑  Clear", command=self._clear_output,
                      fg_color="#21262d", hover_color="#30363d",
                      height=22, font=ctk.CTkFont(size=10)).pack(side="right")

        # OutputText — self.output is required by BaseToolFrame.drain_queue()
        out_sb = ctk.CTkScrollbar(output_wrap)
        out_sb.pack(side="right", fill="y", padx=(0, 2), pady=(2, 4))
        self.output = OutputText(output_wrap, yscrollcommand=out_sb.set)
        self.output.pack(fill="both", expand=True, padx=(4, 0), pady=(2, 4))
        out_sb.configure(command=self.output.yview)

    # ── Editor widget factory ─────────────────────────────────────────────────

    def _make_editor(self, parent):
        """Build a tk.Text editor with vertical + horizontal scrollbars.
        Packing order: sb_y (right) → sb_x (bottom) → editor (fill=both).
        This order is required for the horizontal scrollbar to appear correctly."""
        sb_y = ctk.CTkScrollbar(parent)
        sb_y.pack(side="right", fill="y", padx=(0, 2), pady=2)

        sb_x = ctk.CTkScrollbar(parent, orientation="horizontal")
        sb_x.pack(side="bottom", fill="x", padx=2, pady=(0, 2))

        editor = tk.Text(
            parent,
            bg="#0d1117", fg="#c9d1d9",
            font=("Consolas", 11),
            relief="flat", borderwidth=0,
            wrap="none",                  # wrap=none enables horizontal scrolling
            padx=10, pady=8,
            insertbackground="#ffffff",
            selectbackground="#264f78",
            highlightthickness=0,
            undo=True,                    # enables Ctrl+Z / Ctrl+Y
            yscrollcommand=sb_y.set,
            xscrollcommand=sb_x.set,
        )
        editor.pack(fill="both", expand=True, padx=(2, 0), pady=2)
        sb_y.configure(command=editor.yview)
        sb_x.configure(command=editor.xview)

        # <<Modified>> fires once after each edit burst; reset with edit_modified(False)
        editor.bind("<<Modified>>", self._on_editor_modified)
        return editor

    # ── File browser ──────────────────────────────────────────────────────────

    def _refresh_script_list(self):
        """Populate the listbox from SCRIPT_LAB_DEFAULT_DIR."""
        SCRIPT_LAB_DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
        self._listbox.delete(0, "end")
        self._script_paths = []
        try:
            entries = sorted(
                p for p in SCRIPT_LAB_DEFAULT_DIR.iterdir()
                if p.is_file() and p.suffix.lower() in _ALL_SCRIPT_EXTS
            )
        except OSError:
            entries = []
        for p in entries:
            self._listbox.insert("end", p.name)
            self._script_paths.append(str(p))

    def _load_selected(self):
        """Double-click handler for the listbox."""
        sel = self._listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if 0 <= idx < len(self._script_paths):
            self._load_script_file(self._script_paths[idx])

    def _open_script(self):
        path = filedialog.askopenfilename(
            title="Open Script", filetypes=SCRIPT_LAB_FILETYPES)
        if path:
            self._load_script_file(path)

    def _open_script_folder(self):
        SCRIPT_LAB_DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
        _pu_shell.open_folder(SCRIPT_LAB_DEFAULT_DIR)

    # ── Editor lifecycle ──────────────────────────────────────────────────────

    def _load_script_file(self, path):
        """Read file into editor. Guards against unsaved changes first."""
        if not self._confirm_discard_changes():
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError as exc:
            messagebox.showerror("Open Error", str(exc))
            return
        # Replace editor content atomically
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", content)
        # Clear modified flag AFTER insert (insert sets it, which would trigger <<Modified>>)
        self.editor.edit_modified(False)
        self._current_path = path
        self._path_var.set(path)
        self._set_editor_dirty(False)
        self._refresh_run_btn()

    def _confirm_discard_changes(self):
        """Return True if it is safe to discard current editor content."""
        if not self._dirty:
            return True
        return messagebox.askyesno(
            "Unsaved Changes",
            "You have unsaved changes.\nDiscard and continue?",
            icon="warning")

    def _on_editor_modified(self, event=None):
        """Called by the <<Modified>> virtual event — fires once per edit burst."""
        if self.editor.edit_modified():
            self._set_editor_dirty(True)
            self.editor.edit_modified(False)   # reset so next edit fires again

    def _set_editor_dirty(self, dirty):
        self._dirty = dirty
        if dirty:
            self._dirty_var.set("  ● Modified")
            self._dirty_label.configure(text_color="#d29922")
        else:
            if self._current_path:
                self._dirty_var.set("  ● Saved")
                self._dirty_label.configure(text_color="#8b949e")
            else:
                self._dirty_var.set("")

    def _refresh_run_btn(self):
        """Enable Run only when a runnable file is loaded and no process is active."""
        ext = pathlib.Path(self._current_path).suffix.lower() if self._current_path else ""
        runnable = bool(self._current_path) and ext in _RUNNABLE_EXTS
        # Never re-enable while a script is already running
        if not self.running:
            self.start_btn.configure(state="normal" if runnable else "disabled")

    # ── Save ──────────────────────────────────────────────────────────────────

    def _new_script(self):
        if not self._confirm_discard_changes():
            return
        self.editor.delete("1.0", "end")
        self.editor.edit_modified(False)
        self._current_path = ""
        self._path_var.set("New script — not saved")
        self._set_editor_dirty(False)
        self._refresh_run_btn()

    def _save_script(self):
        if not self._current_path:
            self._save_script_as()
            return
        try:
            text = self.editor.get("1.0", "end-1c")
            with open(self._current_path, "w", encoding="utf-8") as fh:
                fh.write(text)
            self._set_editor_dirty(False)
        except OSError as exc:
            messagebox.showerror("Save Error", str(exc))

    def _save_script_as(self):
        path = filedialog.asksaveasfilename(
            title="Save Script As",
            filetypes=SCRIPT_LAB_FILETYPES,
            defaultextension=_pu_scripting.default_script_extension(),
            initialdir=str(SCRIPT_LAB_DEFAULT_DIR))
        if not path:
            return
        self._current_path = path
        self._path_var.set(path)
        self._save_script()                # writes content + clears dirty flag
        self._refresh_script_list()        # show the new file in the listbox
        self._refresh_run_btn()            # update run button state

    # ── Run / Stop ────────────────────────────────────────────────────────────

    def _run_script(self):
        if self.running:
            self.output.append("A script is already running. Stop it first.", "warning")
            return
        if not self._current_path:
            self.output.append("No script loaded. Open or create a script first.", "warning")
            return
        ext = pathlib.Path(self._current_path).suffix.lower()
        if ext not in _RUNNABLE_EXTS:
            self.output.append(
                f"Files with extension '{ext}' cannot be executed (view/edit only).", "warning")
            return
        # Handle unsaved changes
        if self._dirty:
            choice = messagebox.askyesnocancel(
                "Unsaved Changes",
                "The script has unsaved changes.\n\n"
                "Yes    = Save and run\n"
                "No     = Run without saving\n"
                "Cancel = Abort")
            if choice is None:       # Cancel
                return
            if choice:               # Yes → save first
                self._save_script()
                if self._dirty:      # save failed (e.g. OSError) → abort run
                    return
        cmd = self._build_run_command(self._current_path)
        if not cmd:
            self.output.append("Cannot build run command for this file type.", "error")
            return
        self.output.clear()
        self.start_poll()
        self.ui_started()
        threading.Thread(target=self._worker_run,
                         args=(cmd, self._current_path),
                         daemon=True).start()

    def _stop_script(self):
        self.stop_event.set()
        if self._proc is not None:
            try:
                self._proc.terminate()
            except OSError:
                pass

    def _build_run_command(self, path):
        """Return the subprocess command list for the given file path."""
        return _pu_scripting.build_run_command(path)

    def _worker_run(self, cmd, path):
        """Worker thread: spawn subprocess, stream output, call ui_done() when done."""
        start_ts = time.time()
        name = pathlib.Path(path).name
        self.q(f"Running: {name}", "header")
        self.q(f"Command: {' '.join(cmd)}", "dim")
        self.q("─" * 55, "dim")
        try:
            self._proc = subprocess.Popen(
                cmd,
                cwd=str(pathlib.Path(path).parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=SUBPROCESS_FLAGS)
            for line in self._proc.stdout:
                if self.stop_event.is_set():
                    self._proc.terminate()
                    break
                self.q(line.rstrip(), "normal")
            rc = self._proc.wait()
            elapsed = time.time() - start_ts
            self.q("─" * 55, "dim")
            if self.stop_event.is_set():
                self.q("Script stopped by user.", "warning")
            elif rc == 0:
                self.q(f"Finished in {elapsed:.1f}s — exit code 0", "success")
            else:
                self.q(f"Finished in {elapsed:.1f}s — exit code {rc}", "error")
        except Exception as exc:
            self.q(f"Error launching script: {exc}", "error")
        finally:
            self._proc = None
            self._safe_after(0, self.ui_done)

    # ── Output + admin helpers ────────────────────────────────────────────────

    def _clear_output(self):
        self.output.clear()

    def _is_admin(self):
        return _pu_detect.is_admin()

    def _update_admin_note(self):
        """Show a note in the output header if the app is not running as admin."""
        if not self._is_admin():
            self._admin_note.configure(
                text="● Not Admin — .ps1 elevation may be needed")


# ==================== Camera Analysis ====================
class CameraAnalysisFrame(BaseToolFrame):
    """
    Detect camera candidates from the ARP cache or live UDP traffic,
    score evidence, check subnet compatibility, and suggest RTSP URLs.
    """

    _MULTICAST_PREFIXES = ("01:00:5E", "33:33:", "FF:FF:FF")

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._candidates    = []    # list of scored candidate dicts
        self._selected_cand = None  # currently displayed
        self._adapters      = []    # [(label, ip, mask), ...]
        self._build()

    # ── UI ─────────────────────────────────────────────────────────────────
    def _build(self):
        self.make_header(
            "🔬  Camera Analysis",
            "Identify camera candidates from ARP cache or live traffic • subnet mismatch detection • RTSP URL candidates",
        )

        # Controls card
        ctrl = self.make_card(self)
        ctrl.pack(fill="x", padx=20, pady=(0, 8))

        row1 = ctk.CTkFrame(ctrl, fg_color="transparent")
        row1.pack(fill="x", padx=14, pady=(10, 4))

        ctk.CTkLabel(row1, text="Adapter:", text_color="#8b949e").pack(side="left", padx=(0, 6))
        self._adapters = self._get_adapter_list()
        adapter_names  = [a[0] for a in self._adapters] if self._adapters else ["(no adapters found)"]
        self._adapter_var = tk.StringVar(value=adapter_names[0])
        ctk.CTkOptionMenu(
            row1, values=adapter_names, variable=self._adapter_var, width=260,
        ).pack(side="left", padx=(0, 18))

        ctk.CTkLabel(row1, text="Mode:", text_color="#8b949e").pack(side="left", padx=(0, 6))
        self._mode_var = tk.StringVar(value="arp_scan")
        ctk.CTkRadioButton(
            row1, text="ARP + Scan", variable=self._mode_var, value="arp_scan",
            text_color="#c9d1d9", font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=(0, 10))
        ctk.CTkRadioButton(
            row1, text="Live Capture", variable=self._mode_var, value="live",
            text_color="#c9d1d9", font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=(0, 18))

        ctk.CTkLabel(row1, text="Duration:", text_color="#8b949e").pack(side="left", padx=(0, 4))
        self._duration_var = tk.IntVar(value=30)
        ctk.CTkEntry(row1, textvariable=self._duration_var, width=55).pack(side="left", padx=(0, 4))
        ctk.CTkLabel(row1, text="s", text_color="#8b949e").pack(side="left")

        # Row 1b: optional direct target IP
        row1b = ctk.CTkFrame(ctrl, fg_color="transparent")
        row1b.pack(fill="x", padx=14, pady=(2, 4))
        ctk.CTkLabel(
            row1b, text="Target Camera IP:", text_color="#8b949e",
        ).pack(side="left", padx=(0, 6))
        self._target_ip_var = tk.StringVar(value="")
        ctk.CTkEntry(
            row1b, textvariable=self._target_ip_var, width=170,
            placeholder_text="(optional — leave blank for adapter discovery)",
        ).pack(side="left", padx=(0, 12))
        ctk.CTkLabel(
            row1b, text="Leave blank to scan all candidates from the adapter.",
            text_color="#6e7681", font=ctk.CTkFont(size=10),
        ).pack(side="left")

        row2 = ctk.CTkFrame(ctrl, fg_color="transparent")
        row2.pack(fill="x", padx=14, pady=(4, 10))

        r = self.make_btn_row(row2, self._start, self.stop_op, start_text="▶  Run Analysis")
        r.pack(side="left")
        ctk.CTkButton(
            row2, text="\U0001f5d1  Clear", command=self._clear,
            fg_color="#21262d", hover_color="#30363d", width=90,
        ).pack(side="left", padx=(10, 0))
        ctk.CTkButton(row2, text="\U0001f4be", command=lambda: self.export_output("CamAnalysis"),
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="left", padx=(6, 0))
        ctk.CTkButton(row2, text="\u2b50",
                      command=lambda: self._save_favorite_dialog("Host", self._target_var.get().strip()),
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="left", padx=(6, 0))
        self._admin_lbl = ctk.CTkLabel(
            row2,
            text=("⚠  Live Capture requires CAP_NET_RAW or root"
                  if _pu_detect.IS_LINUX
                  else "⚠  Live Capture requires administrator privileges"),
            text_color="#d29922", font=ctk.CTkFont(size=11),
        )  # hidden by default — shown on capture permission error
        self._mode_lbl = ctk.CTkLabel(
            row2, text="", text_color="#58a6ff", font=ctk.CTkFont(size=11),
        )  # shows active analysis mode during run

        # Body: left candidate list + right detail panel
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # ── Left: candidates treeview ──────────────────────────────────────
        left = self.make_card(body, title="Camera Candidates")
        left.configure(width=270)
        left.pack_propagate(False)
        left.pack(side="left", fill="y", padx=(0, 8))

        tree_wrap = ctk.CTkFrame(left, fg_color="#0d1117")
        tree_wrap.pack(fill="both", expand=True, padx=8, pady=(4, 4))

        style = tk.ttk.Style()
        style.theme_use("default")
        style.configure("CamA.Treeview",
                        background="#0d1117", foreground="#c9d1d9",
                        fieldbackground="#0d1117", rowheight=22,
                        font=("Consolas", 10), borderwidth=0,
                        relief="flat")
        style.configure("CamA.Treeview.Heading",
                        background="#161b22", foreground="#8b949e",
                        font=("Consolas", 10, "bold"), relief="flat",
                        borderwidth=0)
        style.map("CamA.Treeview",
                  background=[("selected", "#1f3452")],
                  foreground=[("selected", "#ffffff")])

        sb = ctk.CTkScrollbar(tree_wrap)
        sb.pack(side="right", fill="y", padx=(0, 2), pady=2)
        self._tree = tk.ttk.Treeview(
            tree_wrap, style="CamA.Treeview",
            columns=("ip", "conf", "status"), show="headings",
            yscrollcommand=sb.set, selectmode="browse",
        )
        sb.configure(command=self._tree.yview)
        self._tree.heading("ip",     text="IP Address")
        self._tree.heading("conf",   text="Confidence")
        self._tree.heading("status", text="Reach")
        self._tree.column("ip",     width=112, anchor="w")
        self._tree.column("conf",   width=75,  anchor="center")
        self._tree.column("status", width=65,  anchor="center")
        self._tree.tag_configure("high",   foreground="#3fb950")
        self._tree.tag_configure("medium", foreground="#d29922")
        self._tree.tag_configure("low",    foreground="#8b949e")
        self._tree.bind("<<TreeviewSelect>>", self._on_candidate_select)
        self._tree.pack(fill="both", expand=True, padx=2, pady=(2, 0))

        act = ctk.CTkFrame(left, fg_color="transparent")
        act.pack(fill="x", padx=8, pady=(4, 8))
        self._copy_rtsp_btn = ctk.CTkButton(
            act, text="Copy RTSP", command=self._copy_rtsp,
            fg_color="#21262d", hover_color="#30363d", width=115, state="disabled",
        )
        self._copy_rtsp_btn.pack(side="left", padx=(0, 4))
        self._copy_netsh_btn = ctk.CTkButton(
            act, text="Copy netsh", command=self._copy_netsh,
            fg_color="#21262d", hover_color="#30363d", width=115, state="disabled",
        )
        self._copy_netsh_btn.pack(side="left")

        # ── Right: summary bar + scrollable detail ─────────────────────────
        right = self.make_card(body)
        right.pack(side="left", fill="both", expand=True)

        sum_bar = ctk.CTkFrame(right, fg_color="#0d1117", height=34)
        sum_bar.pack_propagate(False)
        sum_bar.pack(fill="x", padx=8, pady=(8, 0))
        self._summary_var = tk.StringVar(value="Run analysis to detect camera candidates.")
        ctk.CTkLabel(
            sum_bar, textvariable=self._summary_var,
            text_color="#8b949e", font=ctk.CTkFont(size=11), anchor="w",
        ).pack(side="left", padx=10, pady=6)

        self.output = self.make_output(right)

    # ── Adapter enumeration ─────────────────────────────────────────────────
    def _get_adapter_list(self):
        """Return [(label, ip, mask)] for adapters with a non-loopback IPv4."""
        result = []
        if not PSUTIL_AVAILABLE:
            return result
        try:
            addrs = psutil.net_if_addrs()
            for name, addr_list in addrs.items():
                for addr in addr_list:
                    if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                        mask  = addr.netmask or "255.255.255.0"
                        label = f"{name}  [{addr.address}]"
                        result.append((label, addr.address, mask))
        except Exception:
            pass
        return result

    def _resolve_adapter(self):
        """Return (ip, mask, label) for selected adapter, or None."""
        sel = self._adapter_var.get()
        for label, ip, mask in self._adapters:
            if label == sel:
                return ip, mask, label
        return None

    # ── Start / Stop ────────────────────────────────────────────────────────
    def _start(self):
        # Resolve adapter (always needed for subnet context)
        adapter = self._resolve_adapter()
        if adapter is None:
            self.output.clear()
            self.output.append("No adapter selected or no IPv4 adapters found.", "error")
            return
        adapter_ip, adapter_mask, adapter_label = adapter
        adapter_name = adapter_label.split("[", 1)[0].strip()
        mode     = self._mode_var.get()
        duration = self._duration_var.get()

        # Resolve optional direct target IP
        target_ip = self._target_ip_var.get().strip()
        if target_ip:
            try:
                ipaddress.ip_address(target_ip)
            except ValueError:
                self.output.clear()
                self.output.append(
                    f"Invalid target IP: '{target_ip}'. Enter a valid IPv4 address or leave blank.",
                    "error",
                )
                return

        # Determine analysis mode label
        if target_ip:
            mode_desc = f"Direct target: {target_ip}  (adapter context: {adapter_label})"
        elif mode == "live":
            mode_desc = f"Live Capture — {adapter_label}"
        else:
            mode_desc = f"ARP + Active Scan — {adapter_label}"

        # Clear previous results
        self.output.clear()
        self._tree.delete(*self._tree.get_children())
        self._candidates.clear()
        self._selected_cand = None
        self._copy_rtsp_btn.configure(state="disabled")
        self._copy_netsh_btn.configure(state="disabled")
        self._summary_var.set("Analysis running…")
        self._admin_lbl.pack_forget()
        self._mode_lbl.configure(text=f"  [{mode_desc.split('—')[0].strip()}]")
        self._mode_lbl.pack(side="left", padx=(10, 0))

        self.q(f"Adapter:  {adapter_label}", "info")
        if target_ip:
            self.q(f"Target:   {target_ip}  (direct camera analysis)", "info")
        self.q(f"Mode:     {mode_desc}", "info")
        if mode == "live" and not target_ip:
            self.q(f"Duration: {duration}s", "info")
        self.q("", "normal")

        self.running = True
        self.stop_event.clear()
        self.start_poll()
        self.ui_started()

        if target_ip:
            # Direct target mode — probe a specific camera IP
            threading.Thread(
                target=self._worker_direct_target,
                args=(target_ip, adapter_ip, adapter_mask),
                daemon=True,
            ).start()
        elif mode == "live":
            threading.Thread(
                target=self._worker_live_capture,
                args=(adapter_name, adapter_ip, adapter_mask, duration),
                daemon=True,
            ).start()
        else:
            threading.Thread(
                target=self._worker_arp_scan,
                args=(adapter_ip, adapter_mask),
                daemon=True,
            ).start()

    # ── ARP + Scan worker ────────────────────────────────────────────────────
    def _worker_arp_scan(self, adapter_ip, adapter_mask):
        try:
            self.q("Reading ARP cache…", "dim")
            arp_entries = _parse_arp_cache()
            self.q(f"  {len(arp_entries)} ARP entries found.", "dim")
            active = {}
            for ip, mac in arp_entries:
                if self.stop_event.is_set():
                    break
                if ip == adapter_ip:
                    continue
                ev = self._active_probe(ip)
                active[ip] = ev
                hits = [k for k, v in ev.items() if v and k not in ("vendor_http",)]
                if hits:
                    self.q(f"  {ip}  {mac}  → {hits}", "dim")
            self._analyze_and_score(arp_entries, {}, active, adapter_ip, adapter_mask)
        except Exception as exc:
            self.q(f"Error: {exc}", "error")
        finally:
            SessionHistory.log("Cam Analysis", "ARP scan analysis", "Analysis complete")
            self.after(0, self.ui_done)
            self.after(0, lambda: self._mode_lbl.pack_forget())

    # ── Direct target worker ──────────────────────────────────────────────
    def _worker_direct_target(self, target_ip, adapter_ip, adapter_mask):
        """Analyze a single camera IP directly.  Uses the adapter for subnet
        context but focuses all probing on the one target."""
        try:
            self.q(f"Direct target analysis: {target_ip}", "info")
            self.q("", "normal")

            # Step 1: Subnet relationship (needed early for MAC classification)
            sub = compare_adapter_to_candidate(adapter_ip, adapter_mask, target_ip)
            reach = sub.get("reachability", "unknown")
            gateway_ip = _get_default_gateway(adapter_ip)

            # Step 2: Reachability check
            self.q("Checking reachability…", "dim")
            reachable = _check_route_exists(target_ip)
            if reachable:
                self.q(f"  ✔ {target_ip} responded to ping — route exists.", "success")
            else:
                self.q(f"  ⚠ {target_ip} did not respond to ping (may still be reachable).", "warning")

            # Step 3: Get MAC from ARP cache and classify it
            mac = ""
            try:
                arp_entries = _parse_arp_cache()
                for a_ip, a_mac in arp_entries:
                    if a_ip == target_ip:
                        mac = a_mac
                        break
            except Exception:
                pass

            mac_info = _classify_mac(mac, target_ip, adapter_ip, adapter_mask, gateway_ip)
            mac_class = mac_info["mac_class"]
            if mac:
                self.q(f"  MAC: {mac}  ({mac_info['mac_label']})", "dim")
            else:
                self.q(f"  MAC: {mac_info['mac_label']}", "dim")
            if gateway_ip:
                self.q(f"  Gateway: {gateway_ip}", "dim")

            # Step 4: Active probe — RTSP, HTTP, vendor detection
            self.q("Probing camera ports and services…", "dim")
            ev = self._active_probe(target_ip)
            hits = [k for k, v in ev.items() if v and k not in ("vendor_http",)]
            if hits:
                self.q(f"  Evidence: {hits}", "info")
            else:
                self.q("  No open camera ports detected.", "warning")
            if ev.get("vendor_http"):
                self.q(f"  Vendor (HTTP): {ev['vendor_http']}", "info")

            # Step 5: Build evidence and score through the standard pipeline
            arp_entries_for_target = [(target_ip, mac)] if mac else [(target_ip, "")]
            active = {target_ip: ev}
            # Inject extra evidence into active probe results
            active[target_ip]["_ping_ok"] = reachable
            active[target_ip]["_mac_info"] = mac_info
            active[target_ip]["_gateway_ip"] = gateway_ip
            self._analyze_and_score(
                arp_entries_for_target, {}, active, adapter_ip, adapter_mask,
            )

            # Step 6: If no candidates met the score threshold, still show results
            if not self._candidates:
                self.q("", "normal")
                self.q("Camera did not meet the confidence threshold for automatic listing.", "warning")
                self.q("Showing manual analysis results below.", "info")
                self.q("", "normal")

                sugg = suggest_static_ip_for_candidate(target_ip) if sub.get("same_subnet") is False else {}
                rtsp = build_candidate_rtsp_urls(target_ip)
                vendor = ev.get("vendor_http", "")
                oui_vendor = _cam_oui_lookup(mac) if mac and mac_class == "direct" else ""
                if oui_vendor:
                    vendor = oui_vendor
                if vendor:
                    rtsp.sort(key=lambda u: (0 if u["vendor"].lower() == vendor.lower() else 1, -u["score_bonus"]))

                # Determine confidence label based on evidence strength
                if reachable and (ev.get("rtsp_open") or ev.get("http_open")):
                    conf_label = "Likely Camera"
                elif reachable:
                    conf_label = "Manual Target"
                else:
                    conf_label = "Not Reachable"

                forced = {
                    "ip": target_ip, "mac": mac or "—",
                    "arp_entry": bool(mac), "dhcp_request": False, "dhcp_info": None,
                    "rtsp_open": ev.get("rtsp_open", False),
                    "rtsp_8554": ev.get("rtsp_8554", False),
                    "http_open": ev.get("http_open", False),
                    "onvif_found": ev.get("onvif_found", False),
                    "ssdp_found": ev.get("ssdp_found", False),
                    "camera_oui": bool(oui_vendor), "vendor": vendor,
                    "camera_http_keywords": bool(ev.get("vendor_http")),
                    "vendor_http": ev.get("vendor_http", ""),
                    "multicast_only": False, "local_pc_mac": False,
                    "score": 5, "confidence": conf_label,
                    "subnet": sub, "suggestion": sugg, "rtsp_urls": rtsp,
                    "adapter_ip": adapter_ip, "adapter_mask": adapter_mask,
                    "mac_info": mac_info, "ping_ok": reachable,
                    "gateway_ip": gateway_ip,
                }
                self._candidates = [forced]
                self.after(0, self._refresh_candidates_ui)

        except Exception as exc:
            self.q(f"Error: {exc}", "error")
        finally:
            SessionHistory.log("Cam Analysis", f"Direct target {target_ip}", "Analysis complete")
            self.after(0, self.ui_done)
            self.after(0, lambda: self._mode_lbl.pack_forget())

    def _active_probe(self, ip):
        """Quick probe for RTSP, HTTP, ONVIF presence. Returns evidence dict."""
        ev = {
            "rtsp_open":   False,
            "rtsp_8554":   False,
            "http_open":   False,
            "onvif_found": False,
            "ssdp_found":  False,
            "vendor_http": "",
        }
        if _cam_rtsp_alive(ip, 554, 1.5) or _cam_tcp_open(ip, 554, 1500):
            ev["rtsp_open"] = True
        if _cam_tcp_open(ip, 8554, 1000):
            ev["rtsp_8554"] = True
        for port in (80, 8080, 8000, 81):
            if _cam_tcp_open(ip, port, 800):
                ev["http_open"] = True
                try:
                    import urllib.request as _ur
                    req = _ur.Request(
                        f"http://{ip}:{port}/",
                        headers={"User-Agent": "Mozilla/5.0"},
                    )
                    with _ur.urlopen(req, timeout=2) as resp:
                        text   = resp.read(2048).decode("utf-8", errors="replace").lower()
                        server = resp.headers.get("Server", "").lower()
                        combined = text + server
                        for kw, vendor in CAMERA_HTTP_KEYWORDS:
                            if kw.lower() in combined:
                                ev["vendor_http"] = vendor
                                break
                except Exception:
                    pass
                break
        return ev

    # ── Live Capture worker ────────────────────────────────────────────────
    def _worker_live_capture(self, adapter_name, adapter_ip, adapter_mask, duration):
        dhcp_seen = {}   # mac -> latest DHCP dict
        raw = None
        try:
            if _pu_detect.IS_LINUX:
                if not _pu_caps.has_net_raw():
                    raise PermissionError("CAP_NET_RAW or root privileges are required")
                raw = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(_LINUX_ETH_P_IP))
                raw.bind((adapter_name, 0))
            else:
                raw = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_UDP)
                raw.bind((adapter_ip, 0))
                raw.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
                raw.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
            raw.settimeout(1.0)
            self.q(f"Live capture started on {adapter_ip} for {duration}s…", "info")
            deadline   = time.time() + duration
            pkt_count  = 0
            while time.time() < deadline and not self.stop_event.is_set():
                try:
                    data, _ = raw.recvfrom(65535)
                    pkt_count += 1
                    packet = _capture_ipv4_packet(data)
                    if packet is None:
                        continue
                    parsed = _parse_dhcp_from_raw(packet)
                    if parsed and parsed.get("mac"):
                        mac = parsed["mac"]
                        dhcp_seen[mac] = parsed
                        suffix = f"  client={parsed['client_ip']}" if parsed.get("client_ip") else ""
                        self.q(f"  DHCP {parsed['msg_type']} from {mac}{suffix}", "cyan")
                except socket.timeout:
                    pass
            self.q(
                f"Capture done. {pkt_count} UDP packets, {len(dhcp_seen)} DHCP device(s).", "dim",
            )
        except PermissionError:
            if _pu_detect.IS_LINUX:
                self.q("Raw socket access unavailable on Linux. Run with CAP_NET_RAW or as root.", "error")
            else:
                self.q("Live Capture requires administrator privileges.", "error")
            self.q("Falling back to ARP + Scan…", "warning")
            self.after(0, lambda: self._admin_lbl.pack(side="left", padx=(16, 0)))
        except Exception as exc:
            self.q(f"Capture error: {exc}", "error")
        finally:
            if raw is not None:
                try:
                    if not _pu_detect.IS_LINUX:
                        raw.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
                    raw.close()
                except Exception:
                    pass

        # Always follow up with ARP + active probing
        try:
            self.q("Reading ARP cache…", "dim")
            arp_entries = _parse_arp_cache()
            known_ips   = {ip for ip, _ in arp_entries}
            for mac, info in dhcp_seen.items():
                ip_c = info.get("client_ip") or info.get("offered_ip")
                if ip_c and ip_c not in known_ips:
                    arp_entries.append((ip_c, mac))
                    known_ips.add(ip_c)
            self.q("Probing candidates…", "dim")
            active = {}
            for ip, mac in arp_entries:
                if self.stop_event.is_set():
                    break
                if ip == adapter_ip:
                    continue
                active[ip] = self._active_probe(ip)
            self._analyze_and_score(arp_entries, dhcp_seen, active, adapter_ip, adapter_mask)
        except Exception as exc:
            self.q(f"Analysis error: {exc}", "error")
        finally:
            SessionHistory.log("Cam Analysis", "Live capture analysis", "Analysis complete")
            self.after(0, self.ui_done)
            self.after(0, lambda: self._mode_lbl.pack_forget())

    # ── Analysis & scoring ──────────────────────────────────────────────────
    def _analyze_and_score(self, arp_entries, dhcp_seen, active, adapter_ip, adapter_mask):
        """Merge all evidence, score candidates, schedule UI refresh."""
        adapter_mac = ""
        if PSUTIL_AVAILABLE:
            try:
                for name, addr_list in psutil.net_if_addrs().items():
                    for addr in addr_list:
                        if addr.family == socket.AF_INET and addr.address == adapter_ip:
                            for a2 in addr_list:
                                if a2.family == psutil.AF_LINK:
                                    adapter_mac = a2.address.upper().replace("-", ":")
            except Exception:
                pass

        per_ip = {}

        def _blank(ip, mac):
            return {
                "ip": ip, "mac": mac,
                "arp_entry": False, "dhcp_request": False, "dhcp_info": None,
                "rtsp_open": False, "rtsp_8554": False, "http_open": False,
                "onvif_found": False, "ssdp_found": False,
                "camera_oui": False, "vendor": "",
                "camera_http_keywords": False, "vendor_http": "",
                "multicast_only": False, "local_pc_mac": False,
            }

        # ARP cache entries
        for ip, mac in arp_entries:
            if ip == adapter_ip:
                continue
            if any(mac.upper().startswith(p) for p in self._MULTICAST_PREFIXES):
                continue
            if ip not in per_ip:
                per_ip[ip] = _blank(ip, mac)
            e = per_ip[ip]
            e["arp_entry"] = True
            vendor = _cam_oui_lookup(mac)
            if vendor:
                e["camera_oui"] = True
                e["vendor"]     = vendor
            if adapter_mac and mac == adapter_mac:
                e["local_pc_mac"] = True

        # DHCP evidence
        for mac, info in dhcp_seen.items():
            if any(mac.upper().startswith(p) for p in self._MULTICAST_PREFIXES):
                continue
            ip_c = info.get("client_ip") or info.get("offered_ip")
            if not ip_c:
                continue
            if ip_c not in per_ip:
                per_ip[ip_c] = _blank(ip_c, mac)
            e = per_ip[ip_c]
            e["dhcp_request"] = True
            e["dhcp_info"]    = info
            if not e["vendor"]:
                v = _cam_oui_lookup(mac)
                if v:
                    e["camera_oui"] = True
                    e["vendor"]     = v

        # Active probe results
        for ip, ev in active.items():
            if ip not in per_ip:
                continue
            e = per_ip[ip]
            e["rtsp_open"]   = ev.get("rtsp_open",   False)
            e["rtsp_8554"]   = ev.get("rtsp_8554",   False)
            e["http_open"]   = ev.get("http_open",   False)
            e["onvif_found"] = ev.get("onvif_found", False)
            e["ssdp_found"]  = ev.get("ssdp_found",  False)
            # Propagate extra evidence from direct target worker
            if ev.get("_ping_ok") is not None:
                e["ping_ok"]    = ev["_ping_ok"]
            if ev.get("_mac_info"):
                e["mac_info"]   = ev["_mac_info"]
            if ev.get("_gateway_ip"):
                e["gateway_ip"] = ev["_gateway_ip"]
            if ev.get("vendor_http"):
                e["vendor_http"]         = ev["vendor_http"]
                e["camera_http_keywords"] = True
                if not e["vendor"]:
                    e["vendor"] = ev["vendor_http"]

        # Score and build candidate list
        gateway_ip = ""
        try:
            gateway_ip = _get_default_gateway(adapter_ip)
        except Exception:
            pass

        candidates = []
        for ip, e in per_ip.items():
            score, label = score_camera_candidate(e)
            if score < 10:
                continue
            sub  = compare_adapter_to_candidate(adapter_ip, adapter_mask, ip)
            sugg = suggest_static_ip_for_candidate(ip) if sub.get("same_subnet") is False else {}
            rtsp = build_candidate_rtsp_urls(ip)
            # Re-rank RTSP URLs: known vendor paths first
            vendor = e.get("vendor") or e.get("vendor_http", "")
            if vendor:
                rtsp.sort(key=lambda u: (0 if u["vendor"] == vendor else 1, -u["score_bonus"]))

            # MAC classification if not already set by direct target worker
            if "mac_info" not in e:
                e["mac_info"] = _classify_mac(
                    e.get("mac", ""), ip, adapter_ip, adapter_mask, gateway_ip,
                )
            if "gateway_ip" not in e:
                e["gateway_ip"] = gateway_ip

            # Upgrade confidence label based on evidence strength
            if label == "High" and (e.get("camera_oui") or e.get("onvif_found")):
                label = "Confirmed Camera"
            elif label == "High":
                label = "Likely Camera"

            candidates.append({
                **e,
                "score":        score,
                "confidence":   label,
                "subnet":       sub,
                "suggestion":   sugg,
                "rtsp_urls":    rtsp,
                "adapter_ip":   adapter_ip,
                "adapter_mask": adapter_mask,
            })

        candidates.sort(key=lambda c: -c["score"])
        self._candidates = candidates
        self.after(0, lambda: self._refresh_candidates_ui())

    def _refresh_candidates_ui(self):
        self._tree.delete(*self._tree.get_children())
        if not self._candidates:
            self._summary_var.set("No camera candidates detected.")
            self.q("No candidates found with sufficient confidence.", "warning")
            return
        for cand in self._candidates:
            conf      = cand["confidence"]
            tag       = "high" if conf == "High" else "medium" if conf == "Medium" else "low"
            r_state   = cand["subnet"].get("reachability", "unknown")
            if r_state == "direct":
                reach = "✔ direct"
            elif r_state == "possibly_routed":
                reach = "~ routable?"
            elif r_state == "likely_unreachable":
                reach = "⚠ mismatch"
            else:
                reach = "?"
            self._tree.insert("", "end",
                              values=(cand["ip"], conf, reach),
                              tags=(tag,))
        first = self._tree.get_children()[0]
        self._tree.selection_set(first)
        self._tree.focus(first)
        self._on_candidate_select(None)
        self._summary_var.set(
            f"{len(self._candidates)} candidate(s) found — select one for details."
        )

    # ── Detail display ──────────────────────────────────────────────────────
    def _on_candidate_select(self, event):
        sel = self._tree.selection()
        if not sel:
            return
        idx = self._tree.index(sel[0])
        if idx < len(self._candidates):
            self._selected_cand = self._candidates[idx]
            self._show_candidate_detail(self._selected_cand)
            self._copy_rtsp_btn.configure(state="normal")
            has_sugg = bool(self._selected_cand.get("suggestion", {}).get("ip"))
            self._copy_netsh_btn.configure(state="normal" if has_sugg else "disabled")

    # ── Auto-Conclusion & Smart Action Engine ────────────────────────────

    @staticmethod
    def _build_auto_conclusion(cand, reach, mac_class, ping_ok, vendor):
        """Produce a concise plain-language technical conclusion from evidence."""
        ip = cand["ip"]
        has_rtsp = cand.get("rtsp_open")
        has_http = cand.get("http_open")
        has_cam_kw = cand.get("camera_http_keywords")
        has_onvif = cand.get("onvif_found")
        has_oui = cand.get("camera_oui") and mac_class == "direct"

        parts = []

        # Identity assessment
        if has_onvif or (has_oui and (has_rtsp or has_cam_kw)):
            parts.append(f"Strong camera evidence at {ip}.")
        elif has_rtsp and has_cam_kw:
            parts.append(f"The target at {ip} shows camera-specific behavior (RTSP + HTTP camera keywords).")
        elif has_rtsp or has_cam_kw:
            parts.append(f"The target at {ip} has some camera indicators but identity is not fully confirmed.")
        elif has_http:
            parts.append(f"The target at {ip} has an HTTP service but no strong camera-specific evidence.")
        elif ping_ok:
            parts.append(f"The target at {ip} responds to ping but no camera-specific services were found.")
        else:
            parts.append(f"No confirmed services or camera evidence at {ip}.")

        # Reachability assessment
        if reach == "direct":
            if ping_ok:
                parts.append("Directly reachable on the local subnet.")
            elif ping_ok is False:
                parts.append("Same subnet but not responding to ping — may be firewalled or powered off.")
            else:
                parts.append("Same subnet — direct access expected.")
            if has_rtsp:
                parts.append("RTSP is likely available.")
        elif reach == "possibly_routed":
            if ping_ok:
                parts.append("Reachable through a gateway despite being on a different subnet.")
            else:
                parts.append("Different subnet — a route may exist but is not confirmed.")
            if mac_class == "gateway":
                parts.append("Direct MAC confirmation is not possible from the current network position.")
        elif reach == "likely_unreachable":
            parts.append("Different subnet with no confirmed route. Direct access is unlikely without adapter change or routing.")
        else:
            parts.append("Network relationship could not be fully determined.")

        return " ".join(parts)

    @staticmethod
    def _pick_smart_action(cand, reach, mac_class, ping_ok, vendor, sugg):
        """Choose ONE primary next action based on evidence. Returns
        (action, reason, secondary_action_or_empty)."""
        ip = cand["ip"]
        has_rtsp = cand.get("rtsp_open")
        has_http = cand.get("http_open")
        rtsp_urls = cand.get("rtsp_urls") or []
        no_ports = not has_rtsp and not has_http

        # Unreachable — must fix network first
        if reach == "likely_unreachable":
            if sugg.get("ip"):
                return (
                    f"Change adapter IP to {sugg['ip']} / {sugg['mask']} (no gateway)",
                    "different subnet with no confirmed route",
                    "Or connect through a gateway/NVR that bridges both networks",
                )
            return (
                "Re-run analysis from the same subnet as the camera",
                "different subnet with no confirmed route",
                "",
            )

        # Routed but not confirmed reachable
        if reach == "possibly_routed" and not ping_ok:
            if has_rtsp and rtsp_urls:
                return (
                    f"Try RTSP connection: {rtsp_urls[0]['url']}",
                    "RTSP port responded despite different subnet — route likely exists",
                    f"If unreachable, change adapter to {sugg['ip']} / {sugg.get('mask','')}" if sugg.get("ip") else "",
                )
            if has_http:
                return (
                    f"Try browser access: http://{ip}",
                    "HTTP port open — test if a route exists",
                    f"If unreachable, change adapter to {sugg['ip']} / {sugg.get('mask','')}" if sugg.get("ip") else "",
                )
            return (
                "Test connectivity with ping or browser before changing adapter",
                "different subnet, route not confirmed",
                f"If unreachable, change adapter to {sugg['ip']} / {sugg.get('mask','')}" if sugg.get("ip") else "",
            )

        # Reachable (direct or confirmed routed)
        if has_rtsp and rtsp_urls:
            reason = "RTSP port responded" + (" on same subnet" if reach == "direct" else " and ping confirmed route")
            if vendor and vendor != "Unknown":
                reason += f", vendor-matched paths available ({vendor})"
            return (
                f"Try RTSP stream: {rtsp_urls[0]['url']}",
                reason,
                f"Or try browser: http://{ip}" if has_http else "",
            )

        if has_http:
            reason = "HTTP port open"
            if cand.get("camera_http_keywords"):
                reason += f" with camera banner ({cand.get('vendor_http', '')})"
            return (
                f"Try browser access: http://{ip}",
                reason,
                "Check for RTSP on non-standard ports if web UI confirms camera",
            )

        if ping_ok and no_ports:
            return (
                f"Try browser access: http://{ip}",
                "target is reachable but no open ports were confirmed — may use non-standard ports",
                "Check credentials or firewall rules if connection refused",
            )

        if no_ports and not ping_ok:
            return (
                "Verify camera is powered on and connected to the network",
                "no ports responded and ping failed",
                "Re-run analysis after confirming physical connectivity",
            )

        return (
            f"Try browser access: http://{ip}",
            "limited evidence available",
            "",
        )

    @staticmethod
    def _pick_best_stream(cand, vendor):
        """Choose the single best stream candidate. Returns a dict with
        url, confidence ('Verified'/'Likely'/'Guess'), and reason, or None."""
        rtsp_urls = cand.get("rtsp_urls") or []
        has_rtsp = cand.get("rtsp_open")
        has_http = cand.get("http_open")
        has_cam_kw = cand.get("camera_http_keywords")
        reach = cand.get("subnet", {}).get("reachability", "unknown")

        if not rtsp_urls and not has_http:
            return None

        # If RTSP port is open and we have vendor-matched paths
        if has_rtsp and rtsp_urls:
            best = rtsp_urls[0]
            url = best["url"]
            v = best.get("vendor", "")

            if vendor and v.lower() == vendor.lower() and best.get("score_bonus", 0) >= 2:
                confidence = "Verified" if cand.get("onvif_found") else "Likely"
                reason = f"RTSP port open + vendor match ({v})"
                if cand.get("onvif_found"):
                    reason += " + ONVIF confirmed"
                return {"url": url, "confidence": confidence, "reason": reason}

            if best.get("score_bonus", 0) >= 2:
                return {
                    "url": url,
                    "confidence": "Likely",
                    "reason": f"RTSP port open + high-priority path ({v})",
                }

            return {
                "url": url,
                "confidence": "Guess",
                "reason": "RTSP port open but path is a generic template",
            }

        # HTTP-only camera
        if has_http and has_cam_kw:
            ip = cand["ip"]
            return {
                "url": f"http://{ip}/",
                "confidence": "Likely",
                "reason": "HTTP camera banner detected — web UI likely available",
            }

        if has_http:
            ip = cand["ip"]
            return {
                "url": f"http://{ip}/",
                "confidence": "Guess",
                "reason": "HTTP port open but no camera-specific banner confirmed",
            }

        return None

    @staticmethod
    def _build_failure_reasons(cand, reach, mac_class, ping_ok):
        """Return a list of (reason, detail) tuples explaining why access may fail."""
        reasons = []
        has_rtsp = cand.get("rtsp_open")
        has_http = cand.get("http_open")

        if reach == "likely_unreachable":
            reasons.append((
                "Different subnet with no confirmed route",
                "The camera and adapter are on different network ranges. "
                "Traffic cannot reach the camera without routing or an adapter change.",
            ))
        elif reach == "possibly_routed" and not ping_ok:
            reasons.append((
                "Different subnet — route not confirmed",
                "A route may exist through a gateway but has not been verified. "
                "Access might work or might time out.",
            ))

        if mac_class == "gateway":
            reasons.append((
                "MAC is next-hop gateway only",
                "The ARP MAC belongs to the gateway router, not the camera itself. "
                "Camera identity cannot be confirmed via OUI from this position.",
            ))
        elif mac_class == "none":
            reasons.append((
                "No MAC address available",
                "Could not resolve a MAC for this target. The device may be offline "
                "or on a non-adjacent network.",
            ))

        if not has_rtsp and not has_http:
            reasons.append((
                "No open ports confirmed",
                "Neither RTSP nor HTTP ports responded. Camera may be offline, "
                "firewalled, or using non-standard ports.",
            ))
        elif not has_rtsp:
            reasons.append((
                "RTSP port not responding",
                "Standard RTSP ports (554, 8554) did not respond. "
                "Camera may not support RTSP, or uses a non-standard port.",
            ))

        if ping_ok is False:
            reasons.append((
                "Ping failed",
                "The target did not respond to ICMP ping. It may be offline, "
                "firewalled, or ICMP-blocked.",
            ))

        if has_http and not cand.get("camera_http_keywords"):
            reasons.append((
                "No camera keywords in HTTP response",
                "HTTP port is open but the response did not contain known camera "
                "vendor strings. The device may not be a camera.",
            ))

        if has_rtsp and cand.get("rtsp_urls"):
            # All RTSP paths are guesses (no vendor match)
            v = cand.get("vendor") or cand.get("vendor_http") or ""
            urls = cand["rtsp_urls"]
            if v and not any(u["vendor"].lower() == v.lower() for u in urls[:3]):
                reasons.append((
                    "Stream paths are generic guesses",
                    f"Vendor '{v}' was detected but top RTSP path candidates "
                    "are generic templates. Credentials or exact path may be needed.",
                ))

        return reasons

    def _show_candidate_detail(self, cand):
        self.output.clear()
        ip     = cand["ip"]
        mac    = cand["mac"]
        vendor = cand.get("vendor") or cand.get("vendor_http") or "Unknown"
        score  = cand["score"]
        conf   = cand["confidence"]
        sub    = cand["subnet"]
        sugg   = cand.get("suggestion", {})
        rtsp   = cand["rtsp_urls"]
        a_ip   = cand["adapter_ip"]
        a_mask = cand["adapter_mask"]
        a_net  = sub.get("adapter_net", "?")
        cam_net = sub.get("candidate_net", "?")
        reach  = sub.get("reachability", "unknown")
        expl   = sub.get("explanation", "")
        mac_info   = cand.get("mac_info") or {}
        mac_class  = mac_info.get("mac_class", "unknown")
        mac_label  = mac_info.get("mac_label", "")
        ping_ok    = cand.get("ping_ok")
        gateway_ip = cand.get("gateway_ip", "")
        div    = "─" * 60

        # ── Camera Candidate header ──
        self.output.append(f"\n{div}", "dim")
        self.output.append(f" Camera Candidate: {ip}  ({conf})\n{div}", "header")
        self.output.append(f"\n  IP:          {ip}", "normal")
        self.output.append(f"\n  Confidence:  {conf}  (score {score}/100)", "normal")

        # ── MAC / Vendor ──
        self.output.append(f"\n\n── MAC / Vendor {'─'*45}", "dim")
        if mac_class == "direct":
            self.output.append(f"\n  MAC:     {mac}", "normal")
            self.output.append(f"\n  Type:    Direct — camera MAC (same L2 segment)", "success")
        elif mac_class == "gateway":
            self.output.append(f"\n  MAC:     {mac}", "normal")
            self.output.append(f"\n  Type:    Gateway MAC — not the camera itself", "warning")
            if gateway_ip:
                self.output.append(f"\n           Next-hop gateway: {gateway_ip}", "dim")
            self.output.append(
                "\n           The real camera MAC is not visible from this network position.", "dim",
            )
        elif mac_class == "none":
            self.output.append(f"\n  MAC:     —", "dim")
            self.output.append(f"\n  Type:    MAC unavailable from current network position", "dim")
        else:
            self.output.append(f"\n  MAC:     {mac}", "normal")
            self.output.append(f"\n  Type:    {mac_label or 'Cannot determine MAC ownership'}", "dim")

        if vendor and vendor != "Unknown":
            oui_note = ""
            if mac_class == "gateway":
                oui_note = "  (from HTTP banner, not OUI — MAC belongs to gateway)"
            self.output.append(f"\n  Vendor:  {vendor}{oui_note}", "normal")
        else:
            self.output.append(f"\n  Vendor:  Unknown", "dim")

        # ── Network Position ──
        self.output.append(f"\n\n── Network Position {'─'*41}", "dim")
        self.output.append(f"\n  Adapter:   {a_ip} / {a_mask}  (net {a_net})", "normal")
        self.output.append(f"\n  Camera:    {ip}  (inferred net {cam_net})", "normal")

        if reach == "direct":
            self.output.append(f"\n  Status:    ✔ {expl}", "success")
        elif reach == "possibly_routed":
            self.output.append(f"\n  Status:    ~ Different subnet — possibly routable", "info")
            self.output.append(f"\n             {expl}", "info")
        elif reach == "likely_unreachable":
            self.output.append(f"\n  Status:    ⚠ Likely unreachable from current config", "warning")
            self.output.append(f"\n             {expl}", "warning")
        else:
            self.output.append(f"\n  Status:    ? Could not determine subnet relationship", "warning")

        if ping_ok is not None:
            if ping_ok:
                self.output.append(f"\n  Ping:      ✔ Reachable (ICMP reply received)", "success")
            else:
                self.output.append(f"\n  Ping:      ✘ No ICMP reply (blocked or offline)", "warning")

        # ── Path / Route ──
        self.output.append(f"\n\n── Path / Route {'─'*45}", "dim")
        if reach == "direct":
            self.output.append(f"\n  {a_ip}  ──  {ip}", "success")
            self.output.append(f"\n  (Direct connection, same subnet)", "dim")
        elif gateway_ip and mac_class == "gateway":
            self.output.append(f"\n  {a_ip}  →  [{gateway_ip}]  →  {ip}", "info")
            self.output.append(f"\n  (Routed via gateway)", "dim")
            if ping_ok:
                self.output.append(f"\n  Route confirmed — camera responded to ping", "success")
            elif ping_ok is False:
                self.output.append(f"\n  Route exists but camera did not respond to ping", "warning")
        elif reach == "possibly_routed":
            self.output.append(f"\n  {a_ip}  →  [Router?]  →  {ip}", "info")
            self.output.append(f"\n  (No gateway confirmed — route may exist)", "dim")
        elif reach == "likely_unreachable":
            self.output.append(f"\n  {a_ip}  ✘ ─ ─ ─  {ip}", "warning")
            self.output.append(f"\n  (No route — different network range)", "dim")
        else:
            self.output.append(f"\n  {a_ip}  ? ─ ─ ─  {ip}", "dim")
            self.output.append(f"\n  (Unknown route)", "dim")

        # ── Confidence Breakdown ──
        breakdown, adj_score = score_camera_breakdown(cand, reach, mac_class)
        self.output.append(f"\n\n── Confidence Breakdown {'─'*37}", "dim")
        self.output.append(f"\n  {conf}  (adjusted {adj_score}/100)", "normal")
        for label, pts in breakdown:
            sign = "+" if pts > 0 else ""
            tag = "success" if pts > 0 else "warning" if pts < 0 else "dim"
            self.output.append(f"\n    {sign}{pts:>3}  {label}", tag)

        # ── Final Assessment ──
        conclusion = self._build_auto_conclusion(cand, reach, mac_class, ping_ok, vendor)
        self.output.append(f"\n\n── Final Assessment {'─'*41}", "dim")
        # Pick tag based on overall outlook
        if reach == "direct" and (cand.get("rtsp_open") or cand.get("http_open")):
            c_tag = "success"
        elif reach == "likely_unreachable":
            c_tag = "warning"
        else:
            c_tag = "info"
        self.output.append(f"\n  {conclusion}", c_tag)

        # ── Recommended Next Action ──
        action, reason, secondary = self._pick_smart_action(
            cand, reach, mac_class, ping_ok, vendor, sugg,
        )
        self.output.append(f"\n\n── Recommended Next Action {'─'*34}", "dim")
        self.output.append(f"\n  → {action}", "info")
        self.output.append(f"\n    Why: {reason}", "dim")
        if secondary:
            self.output.append(f"\n    Alt: {secondary}", "dim")

        # ── Best Stream Match ──
        best = self._pick_best_stream(cand, vendor)
        self.output.append(f"\n\n── Best Stream Match {'─'*40}", "dim")
        if best:
            conf_tag = "success" if best["confidence"] == "Verified" else \
                       "info" if best["confidence"] == "Likely" else "dim"
            self.output.append(
                f"\n  {best['url']}  ({best['confidence']})", conf_tag,
            )
            self.output.append(f"\n  {best['reason']}", "dim")
        else:
            self.output.append(
                "\n  No verified stream match found — only template guesses available.", "warning",
            )

        # ── Why Access May Fail ──
        failures = self._build_failure_reasons(cand, reach, mac_class, ping_ok)
        if failures:
            self.output.append(f"\n\n── Why Access May Fail {'─'*38}", "dim")
            for reason_title, detail in failures:
                self.output.append(f"\n  • {reason_title}", "warning")
                self.output.append(f"\n    {detail}", "dim")

        # ── Suggested Adapter Config (if different subnet) ──
        if reach in ("possibly_routed", "likely_unreachable") and sugg.get("ip"):
            self.output.append(f"\n\n── Suggested Adapter Config {'─'*33}", "dim")
            self.output.append(f"\n  IP address:  {sugg['ip']}", "cyan")
            self.output.append(f"\n  Subnet mask: {sugg['mask']}", "cyan")
            self.output.append(f"\n  Gateway:     (leave empty)", "cyan")
            adapter_name = self._adapter_var.get().split("[")[0].strip()
            cmd = (
                f'netsh interface ip set address name="{adapter_name}" '
                f"static {sugg['ip']} {sugg['mask']}"
            )
            self.output.append(f"\n\n  netsh command (click 'Copy netsh'):", "dim")
            self.output.append(f"\n    {cmd}", "dim")
            self.output.append(
                "\n\n  This app will NOT auto-change your network config.",
                "dim",
            )

        # ── Candidate RTSP URLs ──
        self.output.append(f"\n\n── Candidate RTSP URLs {'─'*37}", "dim")
        self.output.append(f"\n  {'#':<4} {'Vendor':<12} {'URL'}", "dim")
        for i, entry in enumerate(rtsp[:10], 1):
            stars = "★★" if entry["score_bonus"] == 2 else "★ "
            self.output.append(
                f"\n  {i:<4} {entry['vendor'] + ' ' + stars:<14} {entry['url']}", "normal",
            )

        self.output.append("\n", "normal")

    # ── Clipboard actions ───────────────────────────────────────────────────
    def _copy_rtsp(self):
        cand = self._selected_cand
        if not cand or not cand.get("rtsp_urls"):
            return
        url = cand["rtsp_urls"][0]["url"]
        self.clipboard_clear()
        self.clipboard_append(url)
        self.q(f"Copied to clipboard: {url}", "success")

    def _copy_netsh(self):
        cand = self._selected_cand
        if not cand:
            return
        sugg = cand.get("suggestion", {})
        if not sugg.get("ip"):
            return
        adapter_name = self._adapter_var.get().split("[")[0].strip()
        cmd = (
            f'netsh interface ip set address name="{adapter_name}" '
            f"static {sugg['ip']} {sugg['mask']}"
        )
        self.clipboard_clear()
        self.clipboard_append(cmd)
        self.q("Copied netsh command to clipboard.", "success")

    def _clear(self):
        self.output.clear()
        self._tree.delete(*self._tree.get_children())
        self._candidates.clear()
        self._selected_cand = None
        self._summary_var.set("Run analysis to detect camera candidates.")
        self._copy_rtsp_btn.configure(state="disabled")
        self._copy_netsh_btn.configure(state="disabled")
        self._mode_lbl.pack_forget()


# ==================== History ====================
class HistoryFrame(BaseToolFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()
        SessionHistory.subscribe(lambda: self.after(0, self._refresh))

    def _build(self):
        self.make_header("\U0001f550  Session History", "Actions performed this session")

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(0, 8))
        ctk.CTkButton(top, text="\U0001f5d1  Clear History", command=self._clear,
                      fg_color="#21262d", hover_color="#30363d", width=130).pack(side="left")
        ctk.CTkButton(top, text="\U0001f4be  Export Log", command=self._export,
                      fg_color="#21262d", hover_color="#30363d", width=120).pack(side="left", padx=8)

        self.output = self.make_output(self)

    def _refresh(self):
        self.output.clear()
        entries = SessionHistory.get_all()
        if not entries:
            self.output.append("No actions recorded yet.", "dim")
            return
        self.output.append(f"{len(entries)} actions this session\n", "dim")
        for e in reversed(entries):
            self.output.append(
                f"[{e['timestamp']}]  {e['tool']}  \u2014  {e['action']}", "info")
            self.output.append(f"  {e['summary']}", "normal")
            self.output.append("", "normal")

    def _clear(self):
        SessionHistory.clear()
        self._refresh()

    def _export(self):
        entries = SessionHistory.get_all()
        if not entries:
            messagebox.showinfo("Export", "No history to export.")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text file", "*.txt"), ("All files", "*.*")],
            initialfile=f"session_log_{ts}",
        )
        if not path:
            return
        try:
            SessionHistory.export_to_file(path)
            self.output.append(f"\u2714 Log exported to {path}", "success")
        except Exception as e:
            self.output.append(f"\u2716 Export failed: {e}", "error")


# ==================== Favorites ====================
class FavoritesFrame(BaseToolFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._filter = "All"
        self._build()

    def _build(self):
        self.make_header("\u2b50  Favorites", "Saved targets, URLs and profiles")

        # Filter row
        frow = ctk.CTkFrame(self, fg_color="transparent")
        frow.pack(fill="x", padx=20, pady=(0, 8))
        self._seg = ctk.CTkSegmentedButton(
            frow,
            values=["All", "Host", "RTSP URL", "Scan Profile", "Script Path"],
            command=self._on_filter,
        )
        self._seg.set("All")
        self._seg.pack(side="left")

        # Scrollable list
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="#0d1117")
        self._scroll.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        self._refresh_list()

    def _on_filter(self, value):
        self._filter = value
        self._refresh_list()

    def _refresh_list(self):
        for w in self._scroll.winfo_children():
            w.destroy()
        if self._filter == "All":
            favs = FavoritesManager.get_all()
        else:
            favs = FavoritesManager.get_by_type(self._filter)
        if not favs:
            ctk.CTkLabel(self._scroll, text="No favorites saved yet.",
                         text_color="#8b949e").pack(pady=20)
            return
        for fav in favs:
            self._make_fav_row(fav)

    def _make_fav_row(self, fav):
        row = ctk.CTkFrame(self._scroll, fg_color="#161b22", corner_radius=6)
        row.pack(fill="x", pady=3)

        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=10, pady=6)
        ctk.CTkLabel(left, text=fav["name"], text_color="#c9d1d9",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(left, text=f"{fav['type']}  \u2022  {fav['value']}",
                     text_color="#8b949e", font=ctk.CTkFont(size=10),
                     wraplength=500).pack(anchor="w")

        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.pack(side="right", padx=8, pady=6)
        ctk.CTkButton(btn_frame, text="\U0001f4cb Use", width=70,
                      fg_color="#21262d", hover_color="#30363d",
                      command=lambda v=fav["value"]: self._use(v)).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="\U0001f5d1", width=35,
                      fg_color="#da3633", hover_color="#f85149",
                      command=lambda fid=fav["id"]: self._delete(fid)).pack(side="left", padx=2)

    def _use(self, value):
        self.clipboard_clear()
        self.clipboard_append(value)
        messagebox.showinfo("Favorite", f"Copied to clipboard:\n{value}")

    def _delete(self, fav_id):
        FavoritesManager.remove(fav_id)
        self._refresh_list()


# ==================== WHOIS Lookup ====================
class WHOISFrame(BaseToolFrame):
    _WHOIS_SERVERS = {
        "com": "whois.verisign-grs.com",
        "net": "whois.verisign-grs.com",
        "org": "whois.pir.org",
        "io":  "whois.nic.io",
        "no":  "whois.norid.no",
        "de":  "whois.denic.de",
        "uk":  "whois.nic.uk",
        "co":  "whois.nic.co",
        "se":  "whois.iis.se",
        "dk":  "whois.dk-hostmaster.dk",
        "fi":  "whois.fi",
        "eu":  "whois.eu",
        "info": "whois.afilias.net",
        "biz": "whois.biz",
    }
    _KEY_FIELDS = re.compile(
        r"^(netname|netrange|cidr|orgname|org-name|organisation|organization|"
        r"org|country|registrar|registrant|creation date|created|"
        r"updated date|last-modified|expir|expires|name\s*server|nserver|"
        r"abuse|tech-c|admin-c|status|descr|role|person|address|phone)",
        re.IGNORECASE,
    )

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()

    def _build(self):
        self.make_header("\U0001f50e  WHOIS Lookup",
                         "Query registration and ownership data for IPs and domains")

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 8))

        ctk.CTkLabel(row, text="Target", text_color="#8b949e").pack(side="left", padx=(0, 4))
        self._target_var = tk.StringVar()
        ctk.CTkEntry(row, textvariable=self._target_var,
                     placeholder_text="example.com or 8.8.8.8",
                     width=260).pack(side="left", padx=(0, 14), fill="x", expand=True)

        ctk.CTkButton(row, text="\U0001f50d  Lookup", command=self._lookup,
                      fg_color="#238636", hover_color="#2ea043", width=110).pack(side="left", padx=(0, 6))
        ctk.CTkButton(row, text="\U0001f5d1", command=lambda: self.output.clear(),
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="left")
        ctk.CTkButton(row, text="\U0001f4be", command=lambda: self.export_output("WHOIS"),
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="left", padx=(6, 0))
        ctk.CTkButton(row, text="\u2b50",
                      command=lambda: self._save_favorite_dialog("Host", self._target_var.get().strip()),
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="left", padx=(6, 0))

        self.output = self.make_output(self)

    # ── Actions ──

    def _lookup(self):
        target = self._target_var.get().strip()
        if not target:
            messagebox.showwarning("Input", "Enter an IP address or domain name.")
            return
        self.output.clear()
        self.output.append(f"WHOIS query: {target}  @  {datetime.now().strftime('%H:%M:%S')}", "header")
        self.output.append("\u2500" * 60, "dim")
        threading.Thread(target=self._worker, args=(target,), daemon=True).start()

    def _worker(self, target):
        try:
            is_ip = self._is_ip(target)
            server = "whois.iana.org"
            if not is_ip:
                tld = target.rsplit(".", 1)[-1].lower() if "." in target else ""
                server = self._WHOIS_SERVERS.get(tld, "whois.iana.org")

            self.q(f"Querying {server} ...", "dim")
            resp = self._whois_query(target, server)
            self._format_response(resp, server)

            # Follow referral (max 1 hop)
            referral = self._detect_referral(resp)
            if referral and referral.lower() != server.lower():
                self.q(f"\n\u2500" * 60, "dim")
                self.q(f"Following referral \u2192 {referral}", "info")
                try:
                    resp2 = self._whois_query(target, referral)
                    self._format_response(resp2, referral)
                    resp = resp2  # use authoritative response for history
                except Exception as e:
                    self.q(f"Referral query failed: {e}", "warning")

            # History
            summary = ""
            for line in resp.splitlines():
                line = line.strip()
                if line and not line.startswith("%") and not line.startswith("#"):
                    summary = line[:80]
                    break
            SessionHistory.log("WHOIS", f"Query: {target}", summary or "Query complete")

        except socket.timeout:
            self.q("\u26a0 Query timed out. The WHOIS server may be unreachable.", "error")
        except ConnectionRefusedError:
            self.q("\u26a0 Connection refused. The server may be rate-limiting requests.", "error")
        except Exception as e:
            self.q(f"\u26a0 Error: {e}", "error")
        finally:
            self.after(0, self.ui_done)

    # ── Helpers ──

    @staticmethod
    def _is_ip(target):
        try:
            ipaddress.ip_address(target)
            return True
        except ValueError:
            return False

    @staticmethod
    def _whois_query(target, server, timeout=10.0):
        with socket.create_connection((server, 43), timeout=timeout) as s:
            s.sendall((target + "\r\n").encode("utf-8"))
            chunks = []
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
        return b"".join(chunks).decode("utf-8", errors="replace")

    @staticmethod
    def _detect_referral(response):
        for line in response.splitlines():
            low = line.lower().strip()
            if low.startswith("refer:") or low.startswith("whois:"):
                val = line.split(":", 1)[1].strip()
                if val and " " not in val:
                    return val
            if low.startswith("referralserver:"):
                val = line.split(":", 1)[1].strip()
                # Strip whois:// prefix if present
                val = re.sub(r"^whois://", "", val, flags=re.I).strip()
                if val and " " not in val:
                    return val
        return None

    def _format_response(self, text, server):
        self.q(f"\n--- Response from {server} ---", "header")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                self.q("", "normal")
            elif stripped.startswith("%") or stripped.startswith("#"):
                self.q(line, "dim")
            elif self._KEY_FIELDS.match(stripped):
                self.q(line, "info")
            else:
                self.q(line, "normal")


# ==================== mDNS / Bonjour Discovery ====================
class MDNSFrame(BaseToolFrame):
    _MDNS_ADDR = "224.0.0.251"
    _MDNS_PORT = 5353
    _SERVICE_LABELS = {
        "_http._tcp":           "Web Server",
        "_https._tcp":          "HTTPS Server",
        "_rtsp._tcp":           "RTSP Stream",
        "_ipp._tcp":            "Printer (IPP)",
        "_printer._tcp":        "Printer",
        "_ssh._tcp":            "SSH",
        "_smb._tcp":            "File Share (SMB)",
        "_afpovertcp._tcp":     "File Share (AFP)",
        "_airplay._tcp":        "AirPlay",
        "_raop._tcp":           "AirPlay Audio",
        "_homekit._tcp":        "HomeKit",
        "_onvif._tcp":          "ONVIF Camera",
        "_axis-video._tcp":     "Axis Camera",
        "_googlecast._tcp":     "Chromecast",
        "_spotify-connect._tcp": "Spotify",
        "_daap._tcp":           "iTunes/Music",
        "_nfs._tcp":            "NFS",
        "_ftp._tcp":            "FTP",
    }

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._devices = {}
        self._cnt_pkts = 0
        self._cnt_devices = 0
        self._cnt_services = 0
        self._build()

    def _build(self):
        self.make_header("\U0001f4e3  mDNS / Bonjour Discovery",
                         "Discover .local devices on the local network")

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 8))

        ctk.CTkLabel(row, text="Duration (s)", text_color="#8b949e").pack(side="left", padx=(0, 4))
        self._dur_var = tk.IntVar(value=15)
        ctk.CTkEntry(row, textvariable=self._dur_var, width=55).pack(side="left", padx=(0, 14))

        r = self.make_btn_row(row, self._start, self.stop_op, start_text="\u25b6  Discover")
        r.pack(side="left", padx=(0, 6))
        ctk.CTkButton(row, text="\U0001f5d1", command=self._clear_all,
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="left")
        ctk.CTkButton(row, text="\U0001f4be", command=lambda: self.export_output("mDNS_Discovery"),
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="left", padx=(6, 0))

        self.make_stat_bar(self, [("Devices", "s_devices"), ("Services", "s_services"),
                                  ("Packets", "s_pkts")])
        self.output = self.make_output(self)

    def _clear_all(self):
        self.output.clear()
        self._devices.clear()
        self._cnt_pkts = self._cnt_devices = self._cnt_services = 0
        self._refresh_stats()

    def _start(self):
        if self.running:
            return
        dur = max(5, min(60, self._dur_var.get()))
        self.ui_started()
        self._clear_all()
        self.output.append(f"mDNS discovery for {dur}s  @  {datetime.now().strftime('%H:%M:%S')}", "header")
        self.output.append("Listening on 224.0.0.251:5353 ...", "dim")
        self.start_poll()
        threading.Thread(target=self._mdns_worker, args=(dur,), daemon=True).start()

    def _refresh_stats(self):
        if hasattr(self, "s_devices"):
            self.s_devices.configure(text=str(self._cnt_devices))
        if hasattr(self, "s_services"):
            self.s_services.configure(text=str(self._cnt_services))
        if hasattr(self, "s_pkts"):
            self.s_pkts.configure(text=str(self._cnt_pkts))

    # ── Worker ──

    def _mdns_worker(self, duration):
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("", self._MDNS_PORT))
            except Exception as e:
                self.q(f"\u26a0 Cannot bind to port 5353: {e}", "error")
                self.q("  Try closing other mDNS/Bonjour services or run as Administrator.", "dim")
                return

            # Join multicast group
            mreq = struct.pack("4sL", socket.inet_aton(self._MDNS_ADDR), socket.INADDR_ANY)
            try:
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            except Exception:
                pass

            sock.settimeout(1.0)
            devices = {}
            end_time = time.time() + duration

            # Send initial query to stimulate responses
            self._send_mdns_query(sock)

            while not self.stop_event.is_set() and time.time() < end_time:
                try:
                    data, addr = sock.recvfrom(4096)
                except socket.timeout:
                    continue
                self._cnt_pkts += 1
                parsed = self._parse_mdns_packet(data, addr[0])
                if parsed:
                    changed = self._merge_result(devices, parsed)
                    if changed:
                        self._cnt_devices = len(devices)
                        self._cnt_services = sum(len(d["services"]) for d in devices.values())
                        snapshot = {k: {"ips": set(v["ips"]), "services": set(v["services"])}
                                    for k, v in devices.items()}
                        self.after(0, lambda s=snapshot: self._display_devices(s))
                self.after(0, self._refresh_stats)

            self._devices = devices
            n_dev = len(devices)
            n_svc = sum(len(d["services"]) for d in devices.values())
            SessionHistory.log("mDNS Scan", f"{duration}s scan",
                               f"{n_dev} devices, {n_svc} services found")
        except Exception as e:
            self.q(f"\u26a0 mDNS error: {e}", "error")
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass
            self.after(0, self.ui_done)

    # ── DNS wire format parser ──

    @staticmethod
    def _read_dns_name(data, offset):
        """Read a DNS-compressed name from data starting at offset.
        Returns (name_string, new_offset)."""
        parts = []
        jumped = False
        orig_offset = offset
        max_jumps = 20
        jumps = 0
        while offset < len(data):
            length = data[offset]
            if length == 0:
                offset += 1
                break
            if (length & 0xC0) == 0xC0:
                # Pointer
                if offset + 1 >= len(data):
                    break
                ptr = ((length & 0x3F) << 8) | data[offset + 1]
                if not jumped:
                    orig_offset = offset + 2
                jumped = True
                offset = ptr
                jumps += 1
                if jumps > max_jumps:
                    break
                continue
            offset += 1
            if offset + length > len(data):
                break
            parts.append(data[offset:offset + length].decode("utf-8", errors="replace"))
            offset += length
        name = ".".join(parts)
        return (name, orig_offset if jumped else offset)

    def _parse_mdns_packet(self, data, src_ip):
        """Parse mDNS DNS packet. Returns dict or None."""
        if len(data) < 12:
            return None
        try:
            # Header
            _id, flags, qd_count, an_count, ns_count, ar_count = struct.unpack("!HHHHHH", data[:12])
            offset = 12
            total_rr = an_count + ns_count + ar_count

            # Skip questions
            for _ in range(qd_count):
                if offset >= len(data):
                    return None
                _, offset = self._read_dns_name(data, offset)
                offset += 4  # QTYPE + QCLASS

            names = []
            ips = []
            services = []

            # Parse resource records
            for _ in range(total_rr):
                if offset >= len(data):
                    break
                rr_name, offset = self._read_dns_name(data, offset)
                if offset + 10 > len(data):
                    break
                rr_type, rr_class, _ttl, rdlength = struct.unpack("!HHiH", data[offset:offset + 10])
                offset += 10
                rd_end = offset + rdlength
                if rd_end > len(data):
                    break

                if rr_type == 1 and rdlength == 4:  # A record
                    ip = socket.inet_ntoa(data[offset:offset + 4])
                    ips.append(ip)
                    if rr_name:
                        names.append(rr_name)
                elif rr_type == 12:  # PTR
                    ptr_name, _ = self._read_dns_name(data, offset)
                    if ptr_name:
                        names.append(ptr_name)
                    # Extract service type from rr_name
                    if rr_name and rr_name.startswith("_"):
                        svc_parts = rr_name.split(".")
                        if len(svc_parts) >= 2:
                            svc_key = ".".join(svc_parts[:2])
                            services.append(svc_key)
                elif rr_type == 33:  # SRV
                    if rdlength >= 6:
                        srv_target, _ = self._read_dns_name(data, offset + 6)
                        if srv_target:
                            names.append(srv_target)
                elif rr_type == 28 and rdlength == 16:  # AAAA
                    pass  # skip IPv6 for now

                offset = rd_end

            if not names and not ips and not services:
                return None
            return {"src_ip": src_ip, "names": names, "ips": ips, "services": services}
        except Exception:
            return None

    @staticmethod
    def _merge_result(devices, parsed):
        """Merge parsed packet into devices dict. Returns True if anything changed."""
        changed = False
        hostnames = set()
        for name in parsed["names"]:
            # Extract hostname (strip .local and service prefixes)
            parts = name.rstrip(".").split(".")
            # Look for .local suffix
            if parts and parts[-1].lower() == "local" and len(parts) >= 2:
                host = parts[-2]
            elif len(parts) >= 1 and not parts[0].startswith("_"):
                host = parts[0]
            else:
                continue
            hostnames.add(host.lower())

        if not hostnames:
            # Use source IP as hostname
            hostnames.add(parsed["src_ip"])

        for host in hostnames:
            if host not in devices:
                devices[host] = {"ips": set(), "services": set()}
                changed = True
            d = devices[host]
            for ip in parsed["ips"]:
                if ip not in d["ips"]:
                    d["ips"].add(ip)
                    changed = True
            d["ips"].add(parsed["src_ip"])
            for svc in parsed["services"]:
                if svc not in d["services"]:
                    d["services"].add(svc)
                    changed = True
        return changed

    def _display_devices(self, devices):
        """Rebuild output showing all discovered devices."""
        self.output.clear()
        self.output.append(f"mDNS Discovery \u2014 {len(devices)} device(s) found", "header")
        self.output.append("\u2500" * 60, "dim")
        for host in sorted(devices.keys()):
            d = devices[host]
            self.output.append(f"\n\u2500\u2500 {host} \u2500" * 30, "header")
            ips = sorted(d["ips"])
            self.output.append(f"  IP Address:  {', '.join(ips) if ips else 'unknown'}", "info")
            if d["services"]:
                svc_labels = []
                for svc in sorted(d["services"]):
                    label = self._SERVICE_LABELS.get(svc, svc)
                    svc_labels.append(label)
                self.output.append(f"  Services:    {', '.join(svc_labels)}", "success")
                # Also show raw service types
                self.output.append(f"  Raw types:   {', '.join(sorted(d['services']))}", "dim")
            else:
                self.output.append("  Services:    (none detected)", "dim")
        self._refresh_stats()

    @staticmethod
    def _send_mdns_query(sock):
        """Send PTR query for _services._dns-sd._udp.local to stimulate mDNS responses."""
        try:
            # Build DNS query for _services._dns-sd._udp.local PTR
            query = b"\x00\x00"  # Transaction ID
            query += b"\x00\x00"  # Flags (standard query)
            query += b"\x00\x01"  # Questions: 1
            query += b"\x00\x00\x00\x00\x00\x00"  # AN, NS, AR = 0
            # QNAME: _services._dns-sd._udp.local
            for part in ["_services", "_dns-sd", "_udp", "local"]:
                query += bytes([len(part)]) + part.encode()
            query += b"\x00"      # End of name
            query += b"\x00\x0c"  # QTYPE = PTR
            query += b"\x00\x01"  # QCLASS = IN
            sock.sendto(query, ("224.0.0.251", 5353))
        except Exception:
            pass


# ==================== Live Packet Capture ====================
class LiveCaptureFrame(BaseToolFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._adapter_map = {}
        self._cnt_total = self._cnt_tcp = self._cnt_udp = 0
        self._cnt_icmp = self._cnt_other = 0
        self._build()

    def _build(self):
        self.make_header(
            "\U0001f4e6  Live Packet Capture",
            ("Capture live network traffic (requires CAP_NET_RAW or root on Linux)"
             if _pu_detect.IS_LINUX
             else "Capture live network traffic (requires Administrator)"),
        )

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True)

        # ── Left controls ──
        left = self.make_card(content, title="Configuration", width=290)
        left.pack(side="left", fill="y", padx=(20, 8), pady=(0, 20))
        left.pack_propagate(False)

        def lbl(t):
            ctk.CTkLabel(left, text=t, text_color="#8b949e",
                         font=ctk.CTkFont(size=11)).pack(anchor="w", padx=14, pady=(6, 0))

        lbl("Adapter")
        af = ctk.CTkFrame(left, fg_color="transparent")
        af.pack(fill="x", padx=14, pady=(2, 0))
        self._adapter_var = tk.StringVar(value="(select)")
        self._adapter_menu = ctk.CTkOptionMenu(
            af, variable=self._adapter_var, values=["(select)"],
            fg_color="#21262d", button_color="#30363d", button_hover_color="#484f58",
            width=0,
        )
        self._adapter_menu.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(af, text="\U0001f504", command=self._populate_adapters,
                      width=35, fg_color="#21262d", hover_color="#30363d").pack(side="left", padx=(4, 0))

        lbl("Protocol Filters")
        self._f_tcp = tk.BooleanVar(value=True)
        self._f_udp = tk.BooleanVar(value=True)
        self._f_icmp = tk.BooleanVar(value=True)
        self._f_other = tk.BooleanVar(value=True)
        for text, var in [("TCP", self._f_tcp), ("UDP", self._f_udp),
                          ("ICMP", self._f_icmp), ("Other", self._f_other)]:
            ctk.CTkCheckBox(left, text=text, variable=var,
                            text_color="#c9d1d9").pack(anchor="w", padx=24, pady=1)

        lbl("Max Packets")
        self._max_var = tk.IntVar(value=500)
        ctk.CTkEntry(left, textvariable=self._max_var).pack(fill="x", padx=14, pady=(2, 0))

        row = self.make_btn_row(left, self._start, self.stop_op,
                                clear_cmd=self._clear_all,
                                start_text="\u25b6  Capture", fill=True)
        row.pack(fill="x", padx=14, pady=(14, 4))
        ctk.CTkButton(row, text="\U0001f4be  Export",
                      command=lambda: self.export_output("LiveCapture"),
                      fg_color="#21262d", hover_color="#30363d",
                      width=0).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        # Admin warning
        ctk.CTkLabel(
            left,
            text=("\u26a0 Requires CAP_NET_RAW or root"
                  if _pu_detect.IS_LINUX
                  else "\u26a0 Requires Administrator"),
            text_color="#d29922", font=ctk.CTkFont(size=10),
        ).pack(padx=14, pady=(8, 14))

        # ── Right panel ──
        right = ctk.CTkFrame(content, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True, padx=(0, 20), pady=(0, 20))

        self.make_stat_bar(right, [("Captured", "s_total"), ("TCP", "s_tcp"),
                                   ("UDP", "s_udp"), ("ICMP", "s_icmp"),
                                   ("Other", "s_other")])
        self.output = self.make_output(right)

        # Populate adapters on init
        self._populate_adapters()

    def _populate_adapters(self):
        self._adapter_map.clear()
        entries = []
        if PSUTIL_AVAILABLE:
            for iface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET and addr.address != "127.0.0.1":
                        label = f"{iface} [{addr.address}]"
                        self._adapter_map[label] = {"name": iface, "ip": addr.address}
                        entries.append(label)
        if not entries:
            entries = ["(no adapters found)"]
        self._adapter_menu.configure(values=entries)
        if entries:
            self._adapter_var.set(entries[0])

    def _clear_all(self):
        self.output.clear()
        self._cnt_total = self._cnt_tcp = self._cnt_udp = 0
        self._cnt_icmp = self._cnt_other = 0
        self._refresh_stats()

    def _refresh_stats(self):
        if hasattr(self, "s_total"):
            self.s_total.configure(text=str(self._cnt_total))
        if hasattr(self, "s_tcp"):
            self.s_tcp.configure(text=str(self._cnt_tcp), text_color="#58a6ff")
        if hasattr(self, "s_udp"):
            self.s_udp.configure(text=str(self._cnt_udp), text_color="#39d3d3")
        if hasattr(self, "s_icmp"):
            self.s_icmp.configure(text=str(self._cnt_icmp), text_color="#d29922")
        if hasattr(self, "s_other"):
            self.s_other.configure(text=str(self._cnt_other))

    def _start(self):
        if self.running:
            return
        adapter_label = self._adapter_var.get()
        adapter = self._adapter_map.get(adapter_label)
        if not adapter:
            messagebox.showwarning("Input", "Select a valid network adapter.")
            return
        adapter_name = adapter["name"]
        adapter_ip = adapter["ip"]
        max_pkts = max(50, min(5000, self._max_var.get()))
        filters = {
            "tcp": self._f_tcp.get(),
            "udp": self._f_udp.get(),
            "icmp": self._f_icmp.get(),
            "other": self._f_other.get(),
        }
        self.ui_started()
        self._clear_all()
        self.output.append(f"Capturing on {adapter_label}  \u2014  max {max_pkts} packets", "header")
        self.output.append(f"{'TIME':<16} {'PROTO':<6} {'SOURCE':<24} {'DEST':<24} {'FLAGS':<14} LEN", "header")
        self.output.append("\u2500" * 90, "dim")
        self.start_poll()
        threading.Thread(target=self._capture_worker,
                         args=(adapter_name, adapter_ip, filters, max_pkts),
                         daemon=True).start()

    # ── Capture worker ──

    def _capture_worker(self, adapter_name, adapter_ip, filters, max_pkts):
        sock = None
        try:
            if _pu_detect.IS_LINUX:
                if not _pu_caps.has_net_raw():
                    self.q("Raw socket access unavailable on Linux. Run with CAP_NET_RAW or as root.", "error")
                    self.after(0, self.ui_done)
                    return
                sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(_LINUX_ETH_P_IP))
                sock.bind((adapter_name, 0))
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
                sock.bind((adapter_ip, 0))
                sock.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
        except (PermissionError, OSError) as e:
            self.q(f"\u26a0 Cannot open raw socket: {e}", "error")
            if _pu_detect.IS_LINUX:
                self.q("  Raw socket access unavailable on Linux. Run with CAP_NET_RAW or as root.", "warning")
            else:
                self.q("  Run NetTools Pro as Administrator to use Live Capture.", "warning")
            self.after(0, self.ui_done)
            return

        count = 0
        try:
            while not self.stop_event.is_set() and count < max_pkts:
                sock.settimeout(1.0)
                try:
                    data, addr = sock.recvfrom(65535)
                except socket.timeout:
                    continue
                except OSError:
                    break
                packet = _capture_ipv4_packet(data)
                if packet is None:
                    continue
                pkt = self._parse_ip_packet(packet)
                if pkt and self._passes_filter(pkt, filters):
                    self._cnt_total += 1
                    proto = pkt["proto"]
                    if proto == "TCP":
                        self._cnt_tcp += 1
                    elif proto == "UDP":
                        self._cnt_udp += 1
                    elif proto == "ICMP":
                        self._cnt_icmp += 1
                    else:
                        self._cnt_other += 1
                    self.q(self._format_packet(pkt), self._proto_tag(proto))
                    count += 1
                    if count % 10 == 0:
                        self.after(0, self._refresh_stats)
        finally:
            try:
                if sock:
                    if not _pu_detect.IS_LINUX:
                        sock.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
                    sock.close()
            except Exception:
                pass
            SessionHistory.log("Live Capture", f"Adapter: {adapter_ip}",
                               f"{self._cnt_total} packets (TCP:{self._cnt_tcp} UDP:{self._cnt_udp} ICMP:{self._cnt_icmp})")
            self.after(0, self._refresh_stats)
            self.after(0, self.ui_done)

    # ── Packet parsing ──

    @staticmethod
    def _parse_ip_packet(data):
        """Parse raw IP packet. Returns summary dict or None."""
        if len(data) < 20:
            return None
        try:
            ver_ihl = data[0]
            ihl = (ver_ihl & 0x0F) * 4
            if ihl < 20 or len(data) < ihl:
                return None
            total_len = struct.unpack("!H", data[2:4])[0]
            proto_num = data[9]
            src_ip = socket.inet_ntoa(data[12:16])
            dst_ip = socket.inet_ntoa(data[16:20])

            pkt = {
                "proto": "OTHER",
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "src_port": 0,
                "dst_port": 0,
                "flags": "",
                "length": total_len,
                "timestamp": datetime.now().strftime("%H:%M:%S.") + f"{datetime.now().microsecond // 1000:03d}",
            }

            if proto_num == 6 and len(data) >= ihl + 14:  # TCP
                pkt["proto"] = "TCP"
                pkt["src_port"] = struct.unpack("!H", data[ihl:ihl + 2])[0]
                pkt["dst_port"] = struct.unpack("!H", data[ihl + 2:ihl + 4])[0]
                flags_byte = data[ihl + 13]
                flag_names = []
                if flags_byte & 0x02:
                    flag_names.append("SYN")
                if flags_byte & 0x10:
                    flag_names.append("ACK")
                if flags_byte & 0x01:
                    flag_names.append("FIN")
                if flags_byte & 0x04:
                    flag_names.append("RST")
                if flags_byte & 0x08:
                    flag_names.append("PSH")
                pkt["flags"] = ",".join(flag_names)

            elif proto_num == 17 and len(data) >= ihl + 4:  # UDP
                pkt["proto"] = "UDP"
                pkt["src_port"] = struct.unpack("!H", data[ihl:ihl + 2])[0]
                pkt["dst_port"] = struct.unpack("!H", data[ihl + 2:ihl + 4])[0]

            elif proto_num == 1 and len(data) >= ihl + 2:  # ICMP
                pkt["proto"] = "ICMP"
                icmp_type = data[ihl]
                icmp_code = data[ihl + 1]
                pkt["flags"] = f"type={icmp_type} code={icmp_code}"

            return pkt
        except Exception:
            return None

    @staticmethod
    def _passes_filter(pkt, filters):
        proto = pkt["proto"]
        if proto == "TCP":
            return filters["tcp"]
        if proto == "UDP":
            return filters["udp"]
        if proto == "ICMP":
            return filters["icmp"]
        return filters["other"]

    @staticmethod
    def _format_packet(pkt):
        src = f"{pkt['src_ip']}:{pkt['src_port']}" if pkt["src_port"] else pkt["src_ip"]
        dst = f"{pkt['dst_ip']}:{pkt['dst_port']}" if pkt["dst_port"] else pkt["dst_ip"]
        flags = f"[{pkt['flags']}]" if pkt["flags"] else ""
        return f"{pkt['timestamp']:<16} {pkt['proto']:<6} {src:<24} {dst:<24} {flags:<14} {pkt['length']}"

    @staticmethod
    def _proto_tag(proto):
        return {"TCP": "info", "UDP": "cyan", "ICMP": "warning"}.get(proto, "dim")


# ==================== Dashboard ====================
class DashboardFrame(ctk.CTkFrame):
    """Live system stats dashboard — default start page."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="#0d1117", corner_radius=0, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        self._stat_labels = {}
        self._gateway_cache = None
        self._build()
        self.after(500, self._refresh)

    # ---- layout ----
    def _build(self):
        # Row 0: Header
        hdr = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=8)
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        ctk.CTkLabel(hdr, text=f"{APP_NAME}",
                     font=ctk.CTkFont(size=24, weight="bold"),
                     text_color="#79c0ff").pack(side="left", padx=20, pady=14)
        ctk.CTkLabel(hdr, text=f"v{APP_VERSION}",
                     font=ctk.CTkFont(size=12),
                     text_color="#8b949e").pack(side="left", padx=(0, 12), pady=14)
        ctk.CTkLabel(hdr, text="Network Engineering Toolkit",
                     font=ctk.CTkFont(size=13),
                     text_color="#8b949e").pack(side="left", pady=14)

        # Row 1: Stat cards grid
        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="nsew", padx=20, pady=5)
        for c in range(4):
            cards.grid_columnconfigure(c, weight=1)
        cards.grid_rowconfigure(0, weight=1)
        cards.grid_rowconfigure(1, weight=1)

        card_defs = [
            ("💻  CPU Usage",        0, 0),
            ("🧠  RAM Usage",        0, 1),
            ("💾  Disk Usage",       0, 2),
            ("📥  Network In",       0, 3),
            ("📤  Network Out",      1, 0),
            ("🔗  Active Conns",     1, 1),
            ("🌐  Local IP",         1, 2),
            ("🚪  Gateway",          1, 3),
        ]
        for title, row, col in card_defs:
            val_lbl, sub_lbl = self._build_card(cards, title, row, col)
            key = title.split("  ", 1)[1].strip()
            self._stat_labels[key] = (val_lbl, sub_lbl)

        # Row 2: Recent activity
        act_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=8)
        act_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(5, 20))
        ctk.CTkLabel(act_frame, text="📋  Recent Activity",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#c9d1d9").pack(anchor="w", padx=16, pady=(10, 4))
        self._activity_label = ctk.CTkLabel(
            act_frame, text="No activity yet.",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#8b949e", justify="left", anchor="w",
        )
        self._activity_label.pack(fill="x", padx=16, pady=(0, 12))

    def _build_card(self, parent, title, row, col):
        card = ctk.CTkFrame(parent, fg_color="#161b22", corner_radius=8,
                            border_width=1, border_color="#21262d")
        card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text=title,
                     font=ctk.CTkFont(size=11),
                     text_color="#8b949e").grid(row=0, column=0, sticky="w", padx=14, pady=(12, 2))
        val_lbl = ctk.CTkLabel(card, text="—",
                               font=ctk.CTkFont(size=22, weight="bold"),
                               text_color="#79c0ff")
        val_lbl.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 0))
        sub_lbl = ctk.CTkLabel(card, text="",
                               font=ctk.CTkFont(size=10),
                               text_color="#8b949e")
        sub_lbl.grid(row=2, column=0, sticky="w", padx=14, pady=(0, 12))
        return val_lbl, sub_lbl

    # ---- refresh loop ----
    def _refresh(self):
        if not self.winfo_ismapped():
            self.after(2000, self._refresh)
            return
        try:
            self._update_stats()
            self._update_activity()
        except Exception:
            pass
        self.after(2000, self._refresh)

    def _color_for_pct(self, pct):
        if pct >= 90:
            return "#f85149"
        if pct >= 80:
            return "#f0883e"
        return "#79c0ff"

    def _update_stats(self):
        # CPU
        if PSUTIL_AVAILABLE:
            cpu = psutil.cpu_percent()
            vl, sl = self._stat_labels["CPU Usage"]
            vl.configure(text=f"{cpu:.1f}%", text_color=self._color_for_pct(cpu))
            sl.configure(text=f"{psutil.cpu_count()} cores")

            # RAM
            mem = psutil.virtual_memory()
            vl, sl = self._stat_labels["RAM Usage"]
            vl.configure(text=f"{mem.percent:.1f}%", text_color=self._color_for_pct(mem.percent))
            sl.configure(text=f"{format_bytes_total(mem.used)} / {format_bytes_total(mem.total)}")

            # Disk
            try:
                disk = psutil.disk_usage("C:\\")
            except Exception:
                disk = psutil.disk_usage("/")
            vl, sl = self._stat_labels["Disk Usage"]
            vl.configure(text=f"{disk.percent:.1f}%", text_color=self._color_for_pct(disk.percent))
            sl.configure(text=f"{format_bytes_total(disk.used)} / {format_bytes_total(disk.total)}")

            # Network I/O
            nio = psutil.net_io_counters()
            vl, sl = self._stat_labels["Network In"]
            vl.configure(text=format_bytes_total(nio.bytes_recv))
            sl.configure(text=f"{nio.packets_recv:,} packets")

            vl, sl = self._stat_labels["Network Out"]
            vl.configure(text=format_bytes_total(nio.bytes_sent))
            sl.configure(text=f"{nio.packets_sent:,} packets")

            # Active connections
            try:
                conns = len(psutil.net_connections())
            except Exception:
                conns = 0
            vl, sl = self._stat_labels["Active Conns"]
            vl.configure(text=str(conns))
            sl.configure(text="TCP + UDP")
        else:
            for key in ("CPU Usage", "RAM Usage", "Disk Usage", "Network In",
                        "Network Out", "Active Conns"):
                vl, sl = self._stat_labels[key]
                vl.configure(text="N/A")
                sl.configure(text="psutil not available")

        # Local IP (no psutil needed)
        vl, sl = self._stat_labels["Local IP"]
        lip = get_local_ip()
        vl.configure(text=lip, font=ctk.CTkFont(size=16, weight="bold"))
        sl.configure(text="Primary adapter")

        # Gateway
        vl, sl = self._stat_labels["Gateway"]
        if self._gateway_cache is None:
            self._gateway_cache = self._get_gateway()
        vl.configure(text=self._gateway_cache, font=ctk.CTkFont(size=16, weight="bold"))
        sl.configure(text="Default route")

    def _update_activity(self):
        entries = SessionHistory.get_all()
        if not entries:
            self._activity_label.configure(text="No activity yet.")
            return
        lines = []
        for e in entries[-10:]:
            lines.append(f"[{e['timestamp']}]  {e['tool']} \u2014 {e['action']}")
        lines.reverse()
        self._activity_label.configure(text="\n".join(lines))

    def _get_gateway(self):
        try:
            gw = _pu_net.default_gateway()
            if gw:
                return gw
        except Exception:
            pass
        return "N/A"


# ==================== Main App ====================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        # Load persistent data
        FavoritesManager.load()
        SettingsManager.load()

        ctk.set_appearance_mode(SettingsManager.get("theme", "dark"))
        ctk.set_default_color_theme("blue")

        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1340x820")
        self.minsize(980, 640)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar — stored on self so programmatic navigation can update it
        sidebar = Sidebar(self, on_select=self._show, width=210)
        sidebar.grid(row=0, column=0, sticky="nsew")
        self._sidebar = sidebar

        # Content area
        content = ctk.CTkFrame(self, fg_color="#0d1117", corner_radius=0)
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)

        # Build all frames
        cls_map = {
            "dashboard":    DashboardFrame,
            "ping":         PingFrame,
            "portscan":     PortScanFrame,
            "stress":       StressTestFrame,
            "traceroute":   TracerouteFrame,
            "dns":          DNSFrame,
            "netscan":      NetworkScanFrame,
            "netdiscover":  NetdiscoverFrame,
            "subnet":       SubnetFrame,
            "wol":          WoLFrame,
            "interfaces":   InterfacesFrame,
            "bandwidth":    BandwidthFrame,
            "connections":  ConnectionsFrame,
            "arp":          ARPFrame,
            "camfinder":    CameraFinderFrame,
            "camview":      CameraViewerFrame,
            "system_tools": SystemToolsFrame,
            "cam_analysis": CameraAnalysisFrame,
            "script_lab":   ScriptLabFrame,
            "history":      HistoryFrame,
            "favorites":    FavoritesFrame,
            "livecapture":  LiveCaptureFrame,
            "whois":        WHOISFrame,
            "mdns":         MDNSFrame,
        }
        self._frames = {}
        for key, cls in cls_map.items():
            frm = cls(content)
            frm.grid(row=0, column=0, sticky="nsew")
            self._frames[key] = frm

        sidebar.select_default()

        # System tray
        self._tray = TrayManager(self)
        self._tray.setup()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after_idle(self._finish_startup)

    def _finish_startup(self):
        self.update_idletasks()
        self.deiconify()
        self.lift()

    def _on_close(self):
        if PYSTRAY_AVAILABLE and SettingsManager.get("minimize_to_tray", True):
            self._tray.minimize_to_tray()
        else:
            self._tray.stop()
            self.destroy()

    def _show(self, key):
        self._frames[key].tkraise()

    def _open_viewer(self, ip, port=80, vendor_hint=""):
        """Switch to Stream Viewer and pre-fill the target camera IP.
        Also syncs sidebar selection so it visually matches the active frame."""
        self._sidebar.select_no_callback("camview")
        self._show("camview")
        self._frames["camview"].set_target(ip, port, vendor_hint=vendor_hint)


# ==================== Entry Point ====================
def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
