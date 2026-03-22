#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NetTools Pro v1.0.0 - Network Engineering Toolkit
A comprehensive, portable network diagnostic and utility toolkit for Windows.

Author:      Bengt Simon Røch Dragseth
License:     MIT License
Copyright:   Copyright (c) 2026 Bengt Simon Røch Dragseth
Repository:  https://github.com/ZodiacNor/NetToolsPro
"""

__version__   = "1.0.0"
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

# Hide console window on Windows when frozen
SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

# ==================== Application Metadata ====================
APP_NAME        = "NetTools Pro"
APP_VERSION     = "1.0.0"
APP_AUTHOR      = "Bengt Simon Røch Dragseth"
APP_LICENSE     = "MIT"
APP_COPYRIGHT   = "Copyright (c) 2026 Bengt Simon Røch Dragseth"
APP_DESCRIPTION = "Network diagnostics and utility toolkit"
APP_COMPANY     = "Bengt Simon Røch Dragseth"

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
    ("/Streaming/Channels/1",                    554,  "Hikvision", 2),
    ("/Streaming/Channels/101",                  554,  "Hikvision", 2),
    ("/cam/realmonitor?channel=1&subtype=0",      554,  "Dahua",     2),
    ("/axis-media/media.amp",                    554,  "Axis",      2),
    ("/live.sdp",                                554,  "Generic",   1),
    ("/stream1",                                 554,  "Generic",   1),
    ("/video1",                                  554,  "Generic",   1),
    ("/h264",                                    554,  "Generic",   1),
    ("/live",                                    554,  "Generic",   1),
    ("/live",                                   8554,  "Generic",   1),
]


# ==================== Camera Analysis — shared helpers ====================

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
    """Parse Windows `arp -a` output. Returns list of (ip, mac) tuples."""
    try:
        out = subprocess.check_output(
            ["arp", "-a"], text=True, stderr=subprocess.DEVNULL,
            creationflags=SUBPROCESS_FLAGS, timeout=5,
        )
        results = []
        for line in out.splitlines():
            m = re.match(
                r"\s+(\d+\.\d+\.\d+\.\d+)\s+"
                r"([0-9a-f]{2}[:-](?:[0-9a-f]{2}[:-]){4}[0-9a-f]{2})\s+(\w+)",
                line, re.I,
            )
            if m:
                ip, mac, type_ = m.groups()
                if type_.lower() != "invalid":
                    results.append((ip, mac.upper().replace("-", ":")))
        return results
    except Exception:
        return []


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


def build_candidate_rtsp_urls(ip):
    """Return ranked list of candidate RTSP URL dicts for a given IP."""
    return [
        {"url": f"rtsp://{ip}:{port}{path}", "vendor": vendor, "score_bonus": bonus}
        for path, port, vendor, bonus in CAMERA_RTSP_PATHS
    ]


def compare_adapter_to_candidate(adapter_ip, adapter_mask, candidate_ip):
    """Compare adapter subnet to candidate IP. Returns result dict."""
    try:
        net  = ipaddress.ip_network(f"{adapter_ip}/{adapter_mask}", strict=False)
        cam  = ipaddress.ip_address(candidate_ip)
        return {"same_subnet": cam in net, "adapter_net": str(net),
                "adapter_prefix": net.prefixlen}
    except Exception as exc:
        return {"same_subnet": None, "error": str(exc)}


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


def score_camera_candidate(evidence):
    """
    Score a camera evidence dict. Returns (score: int, label: str).
    Labels: High (>=70), Medium (>=40), Low (>=20), Very Low (<20).
    """
    weights = {
        "dhcp_request":         40,
        "onvif_found":          35,
        "rtsp_open":            30,
        "camera_oui":           25,
        "camera_http_keywords": 20,
        "ssdp_found":           20,
        "http_open":            15,
        "arp_entry":            10,
        "multicast_only":      -20,
        "local_pc_mac":        -50,
    }
    score = sum(w for k, w in weights.items() if evidence.get(k))
    score = max(0, min(score, 100))
    if score >= 70:   label = "High"
    elif score >= 40: label = "Medium"
    elif score >= 20: label = "Low"
    else:             label = "Very Low"
    return score, label


SIDEBAR_TOOLS = [
    ("🏓  Ping", "ping"),
    ("🔍  Port Scanner", "portscan"),
    ("⚡  Stress Test", "stress"),
    ("🗺   Traceroute", "traceroute"),
    ("🌐  DNS Lookup", "dns"),
    ("📡  Net Scanner", "netscan"),
    ("🧮  Subnet Calc", "subnet"),
    ("💡  Wake-on-LAN", "wol"),
    ("🖧   Interfaces", "interfaces"),
    ("📊  Bandwidth", "bandwidth"),
    ("🔗  Connections", "connections"),
    ("📋  ARP Table", "arp"),
    ("📷  Camera Finder", "camfinder"),
    ("📺  Stream Viewer", "camview"),
    ("🔬  Cam Analysis",  "cam_analysis"),
    ("⚙️  System Tools", "system_tools"),
    ("📝  Script Lab",   "script_lab"),
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
            cmd = ["ping", "-n", "1", "-l", str(size), "-i", str(ttl), "-w", str(timeout), target]
            if df:
                cmd.insert(1, "-f")
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
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()

    def _build(self):
        self.make_header("🔍  Port Scanner", "Scan TCP/UDP ports on any host")

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

        lbl("Scan Mode")
        self.mode_var = tk.StringVar(value="common")
        for ltext, val in [("Common Ports (top 40)", "common"),
                           ("Port Range", "range"),
                           ("Single Port", "single"),
                           ("All Ports  1–65535  (slow)", "all")]:
            ctk.CTkRadioButton(left, text=ltext, variable=self.mode_var,
                               value=val, command=self._update_mode).pack(anchor="w", padx=24, pady=1)

        self._range_frm = ctk.CTkFrame(left, fg_color="transparent")
        ctk.CTkLabel(self._range_frm, text="Start Port", text_color="#8b949e",
                     font=ctk.CTkFont(size=11)).pack(anchor="w")
        self.start_port = tk.IntVar(value=1)
        ctk.CTkEntry(self._range_frm, textvariable=self.start_port).pack(fill="x", pady=(2, 4))
        ctk.CTkLabel(self._range_frm, text="End Port", text_color="#8b949e",
                     font=ctk.CTkFont(size=11)).pack(anchor="w")
        self.end_port = tk.IntVar(value=1024)
        ctk.CTkEntry(self._range_frm, textvariable=self.end_port).pack(fill="x", pady=(2, 0))

        self._single_frm = ctk.CTkFrame(left, fg_color="transparent")
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

        row = self.make_btn_row(left, self._start, self.stop_op,
                                clear_cmd=lambda: self.output.clear(),
                                start_text="▶  Scan", fill=True)
        row.pack(fill="x", padx=14, pady=(14, 14))

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

    def _update_mode(self):
        mode = self.mode_var.get()
        self._range_frm.pack_forget()
        self._single_frm.pack_forget()
        if mode == "range":
            self._range_frm.pack(fill="x", padx=14, pady=(4, 0))
        elif mode == "single":
            self._single_frm.pack(fill="x", padx=14, pady=(4, 0))

    def _get_ports(self):
        m = self.mode_var.get()
        if m == "common":   return list(COMMON_PORTS.keys())
        if m == "range":    return list(range(self.start_port.get(), self.end_port.get() + 1))
        if m == "single":   return [self.single_port.get()]
        return list(range(1, 65536))

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
        self.output.clear()
        self._prog_bar.set(0)
        self._scan_stats = {"scanned": 0, "open": 0, "closed": 0, "filtered": 0}
        self._total = len(ports)
        self.output.append(f"Scanning {t}  —  {len(ports):,} ports  |  "
                           f"{self.proto_var.get()}  |  {self.threads_var.get()} threads  |  "
                           f"{self.timeout_var.get()}ms timeout", "header")
        self.output.append(f"{'PORT':<10} {'PROTO':<6} {'STATE':<12} SERVICE", "header")
        self.output.append("─" * 55, "dim")
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

    def _scan_one(self, host, port, proto, to_ms):
        if self.stop_event.is_set():
            return port, "cancelled", proto
        if proto == "TCP":
            return port, self._tcp_scan(host, port, to_ms), "TCP"
        elif proto == "UDP":
            return port, self._udp_scan(host, port, to_ms), "UDP"
        else:
            tcp = self._tcp_scan(host, port, to_ms)
            udp = self._udp_scan(host, port, to_ms)
            combined = "open" if "open" in tcp or "open" in udp else "closed"
            return port, combined, f"TCP:{tcp}/UDP:{udp}"

    def _worker(self, host, ports):
        to_ms = self.timeout_var.get()
        proto = self.proto_var.get()
        n_threads = min(self.threads_var.get(), 500)
        open_only = self.open_only_var.get()
        done = 0

        with ThreadPoolExecutor(max_workers=n_threads) as ex:
            futs = {ex.submit(self._scan_one, host, p, proto, to_ms): p for p in ports}
            for fut in as_completed(futs):
                if self.stop_event.is_set():
                    break
                try:
                    port, state, p_label = fut.result()
                    done += 1
                    self._scan_stats["scanned"] = done
                    is_open = "open" in str(state).lower()
                    if is_open:
                        self._scan_stats["open"] += 1
                        svc = COMMON_PORTS.get(port, "—")
                        self.q(f"{port:<10} {p_label:<6} {'OPEN':<12} {svc}", "success")
                    elif "filter" in str(state).lower():
                        self._scan_stats["filtered"] += 1
                        if not open_only:
                            self.q(f"{port:<10} {p_label:<6} {'FILTERED':<12}", "warning")
                    else:
                        self._scan_stats["closed"] += 1
                        if not open_only:
                            self.q(f"{port:<10} {p_label:<6} {'CLOSED':<12}", "dim")
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

        ss = self._scan_stats
        self.q(f"\n{'─'*55}", "dim")
        self.q(f"Scan complete — Open: {ss['open']}  Closed: {ss['closed']}  Filtered: {ss['filtered']}", "header")
        self.after(0, lambda: (self.ui_done(), self._prog_bar.set(1),
                               self._prog_lbl.configure(text="Scan complete")))


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
                    r = subprocess.run(["ping", "-n", "1", "-l", str(size), "-w", "200", target],
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
        ctk.CTkButton(row, text="🗑", command=lambda: self.output.clear(),
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="left")

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
        cmd = ["tracert"]
        if not self.resolve_var.get():
            cmd.append("-d")
        cmd += ["-h", str(self.hops_var.get()), "-w", str(self.timeout_var.get()), t]
        proc = None
        try:
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
        except Exception as e:
            self.q(f"Error: {e}", "error")
        finally:
            if proc is not None:
                try:
                    proc.terminate()
                except Exception:
                    pass
                proc.wait()
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

        ctk.CTkButton(row, text="🔍  Lookup", command=self._lookup,
                      fg_color="#238636", hover_color="#2ea043", width=110).pack(side="left", padx=(0, 6))
        ctk.CTkButton(row, text="🗑", command=lambda: self.output.clear(),
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="left")

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
                self.after(0, lambda: self.output.append(f"Error: {e}", "error"))

        self.after(0, lambda: self.output.append("\nDone.", "dim"))


# ==================== Network Scanner ====================
class NetworkScanFrame(BaseToolFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()

    def _build(self):
        self.make_header("📡  Network Scanner", "Discover active hosts on the local network via ping sweep")

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

        r = self.make_btn_row(row, self._start, self.stop_op, start_text="▶  Scan")
        r.pack(side="left", padx=(0, 6))
        ctk.CTkButton(row, text="🗑", command=lambda: self.output.clear(),
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="left")

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
        self.output = self.make_output(self)

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
        self.output.clear()
        self._prog_bar.set(0)
        self._found = 0
        self._total = len(hosts)
        self.output.append(f"Scanning {self.net_var.get()}  ({len(hosts):,} hosts)", "header")
        self.output.append(f"{'IP Address':<18} {'Hostname':<38} {'RTT':>8}", "header")
        self.output.append("─" * 68, "dim")
        self.start_poll()
        threading.Thread(target=self._worker, args=(hosts,), daemon=True).start()

    def _ping_host(self, ip, to_ms):
        cmd = ["ping", "-n", "1", "-w", str(to_ms), str(ip)]
        t0 = time.time()
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=to_ms / 1000 + 1,
                               creationflags=SUBPROCESS_FLAGS)
            rtt = (time.time() - t0) * 1000
            return r.returncode == 0, rtt
        except Exception:
            return False, -1

    def _worker(self, hosts):
        to_ms = self.timeout_var.get()
        n_thr = min(self.threads_var.get(), 256)
        resolve = self.resolve_var.get()
        done = 0

        with ThreadPoolExecutor(max_workers=n_thr) as ex:
            futs = {ex.submit(self._ping_host, ip, to_ms): ip for ip in hosts}
            for fut in as_completed(futs):
                if self.stop_event.is_set():
                    break
                ip = futs[fut]
                try:
                    alive, rtt = fut.result()
                    done += 1
                    if alive:
                        self._found += 1
                        hostname = "—"
                        if resolve:
                            try:
                                hostname = socket.gethostbyaddr(str(ip))[0]
                            except Exception:
                                pass
                        rtt_str = f"< 1ms" if rtt < 1 else f"{rtt:.0f}ms"
                        fc = self._found
                        self.q(f"{str(ip):<18} {hostname:<38} {rtt_str:>8}", "success")
                        self.after(0, lambda c=fc: self._found_lbl.configure(
                            text=f"Hosts discovered: {c}"))
                    pct = done / self._total
                    self.after(0, lambda p=pct, d=done: (
                        self._prog_bar.set(p),
                        self._prog_lbl.configure(text=f"Scanning {d}/{self._total}"),
                    ))
                except Exception:
                    done += 1

        self.q(f"\n{'─'*55}", "dim")
        self.q(f"Scan complete — {self._found} hosts discovered", "header")
        self.after(0, lambda: (self.ui_done(), self._prog_bar.set(1),
                               self._prog_lbl.configure(text=f"Done — {self._found} hosts")))


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
        ctk.CTkButton(top, text="🔄  Refresh", command=self._refresh,
                      fg_color="#238636", hover_color="#2ea043", width=110).pack(side="left")
        ctk.CTkButton(top, text="🗑  Clear", command=lambda: self.output.clear(),
                      fg_color="#21262d", hover_color="#30363d", width=90).pack(side="left", padx=8)
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
            self.after(0, lambda i=iface, s=status, sp=speed, m=mtu, t=tag:
                       self.output.append(f"\n[{i}]  Status: {s}  Speed: {sp}  MTU: {m}", t))

            for addr in addr_list:
                if addr.family == socket.AF_INET:
                    self.after(0, lambda a=addr: self.output.append(
                        f"  IPv4:    {a.address}  /  {a.netmask}", "info"))
                elif addr.family == socket.AF_INET6:
                    self.after(0, lambda a=addr: self.output.append(
                        f"  IPv6:    {a.address}", "dim"))
                elif addr.family == psutil.AF_LINK:
                    self.after(0, lambda a=addr: self.output.append(
                        f"  MAC:     {a.address}", "dim"))

        self.after(0, lambda: self.output.append(
            f"\n{'─'*55}\nTotal interfaces: {len(addrs)}", "dim"))

    def _with_ipconfig(self):
        try:
            res = subprocess.run(["ipconfig", "/all"], capture_output=True, text=True,
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
                self.after(0, lambda l=line, t=tag: self.output.append(l, t))
        except Exception as e:
            self.after(0, lambda: self.output.append(f"Error: {e}", "error"))


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

        ctk.CTkButton(top, text="🗑", command=lambda: self.output.clear(),
                      width=40, fg_color="#21262d", hover_color="#30363d").pack(side="right")

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
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        filt = self.filter_var.get()
        self.after(0, lambda: self.output.append(
            f"Active connections — {datetime.now().strftime('%H:%M:%S')}  "
            f"[filter: {filt}]", "header"))
        self.after(0, lambda: self.output.append(
            f"{'Proto':<7} {'Local Address':<28} {'Remote Address':<28} {'State':<16} {'PID'}", "header"))
        self.after(0, lambda: self.output.append("─" * 90, "dim"))

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
                self.after(0, lambda l=line, t=tag: self.output.append(l, t))

            self.after(0, lambda: self.output.append(
                f"\n{count} connection(s) shown", "dim"))
        else:
            try:
                res = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
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
                    self.after(0, lambda l=line, t=tag: self.output.append(l, t))
            except Exception as e:
                self.after(0, lambda: self.output.append(f"Error: {e}", "error"))


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
        self.after(0, lambda: self.output.append(
            f"ARP Table — {datetime.now().strftime('%H:%M:%S')}", "header"))
        self.after(0, lambda: self.output.append("─" * 70, "dim"))
        try:
            res = subprocess.run(["arp"] + list(args), capture_output=True, text=True,
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
                self.after(0, lambda l=line, t=tag: self.output.append(l, t))
        except Exception as e:
            self.after(0, lambda: self.output.append(f"Error: {e}", "error"))


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
        ctk.CTkButton(row3, text="💾  Export CSV", command=self._export_csv,
                      fg_color="#21262d", hover_color="#30363d", width=110).pack(side="left")

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
                ["ping", "-n", "1", "-w", str(to_ms), str(ip)],
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
            res = subprocess.run(["arp", "-a", str(ip)], capture_output=True, text=True,
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
        # Walk up to the App root and call _open_viewer
        root = self.winfo_toplevel()
        if hasattr(root, "_open_viewer"):
            root._open_viewer(self._selected_ip, http_port)

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
            subprocess.Popen(["cmd", "/c", "start", "", url],
                             creationflags=SUBPROCESS_FLAGS)
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
class CameraViewerFrame(BaseToolFrame):
    """
    Live HTTP/MJPEG stream viewer for IP cameras.
    Probes a camera IP for known stream URLs and displays the feed in-app.
    Requires Pillow for JPEG decoding; falls back gracefully if not installed.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._current_photo = None     # Keep PhotoImage reference (prevents GC)
        self._frame_count   = 0
        self._lost_count    = 0
        self._stream_url    = ""
        self._snapshot_img  = None     # Last PIL Image for saving
        self._probe_results = []       # list of (url, stream_type, label)
        self._lb_index_map  = []       # listbox row → _probe_results index
        self._fps_times = deque(maxlen=30)
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
        ctk.CTkEntry(row1, textvariable=self._ip_var).pack(side="left", padx=(0, 8), fill="x", expand=True)

        ctk.CTkLabel(row1, text="Port:", text_color="#8b949e").pack(side="left", padx=(0, 4))
        self._port_var = tk.IntVar(value=80)
        ctk.CTkEntry(row1, textvariable=self._port_var, width=65).pack(side="left", padx=(0, 8))

        ctk.CTkButton(row1, text="🔍  Probe Streams", command=self._probe_streams,
                      fg_color="#0f3460", hover_color="#1a4a80", width=140).pack(side="left")

        row1b = ctk.CTkFrame(ctrl, fg_color="transparent")
        row1b.pack(fill="x", padx=14, pady=(0, 4))
        ctk.CTkLabel(row1b, text="User:", text_color="#8b949e").pack(side="left", padx=(0, 4))
        self._user_var = tk.StringVar(value="admin")
        ctk.CTkEntry(row1b, textvariable=self._user_var).pack(side="left", padx=(0, 12), fill="x", expand=True)

        ctk.CTkLabel(row1b, text="Pass:", text_color="#8b949e").pack(side="left", padx=(0, 4))
        self._pass_var = tk.StringVar(value="")
        ctk.CTkEntry(row1b, textvariable=self._pass_var, show="●").pack(side="left", fill="x", expand=True)

        # Manual URL row
        row2 = ctk.CTkFrame(ctrl, fg_color="transparent")
        row2.pack(fill="x", padx=14, pady=(0, 10))
        ctk.CTkLabel(row2, text="Direct URL:", text_color="#8b949e").pack(side="left", padx=(0, 5))
        self._url_var = tk.StringVar()
        ctk.CTkEntry(row2, textvariable=self._url_var,
                     placeholder_text="http://... or rtsp://... — paste any stream URL",
                     ).pack(side="left", padx=(0, 8), fill="x", expand=True)
        ctk.CTkButton(row2, text="▶  Connect", command=self._connect_manual,
                      fg_color="#238636", hover_color="#2ea043", width=110).pack(side="left")

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

        # Right: live canvas
        right = ctk.CTkFrame(split, fg_color="#161b22", corner_radius=8)
        right.pack(side="left", fill="both", expand=True, pady=(0, 8))

        self._canvas = tk.Canvas(right, bg="#0d1117",
                                 highlightthickness=0, relief="flat")
        self._canvas.pack(fill="both", expand=True, padx=4, pady=4)
        self._draw_idle_screen()

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

    # ── Idle screen ────────────────────────────────────────────────────────
    def _draw_idle_screen(self):
        self._canvas.update_idletasks()
        w = max(self._canvas.winfo_width(), 400)
        h = max(self._canvas.winfo_height(), 300)
        cx, cy = w // 2, h // 2
        self._canvas.delete("all")
        self._canvas.create_text(cx, cy - 20, text="📷", font=("Segoe UI Emoji", 48),
                                 fill="#21262d")
        self._canvas.create_text(cx, cy + 40,
                                 text="Enter camera IP and click  🔍 Probe Streams\n"
                                      "or paste a direct URL and click  ▶ Connect",
                                 font=("Consolas", 11), fill="#8b949e", justify="center")

    # ── set_target: called from CameraFinderFrame ──────────────────────────
    def set_target(self, ip, port=80):
        """Pre-fill IP/port and automatically start probing."""
        self._ip_var.set(ip)
        self._port_var.set(port)
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

    def _probe_worker(self, ip, port, user, pw):
        found = []
        base  = f"http://{ip}:{port}"

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
                    found.append((url, actual_type, f"{path}  [{actual_type}]  ✓"))
            except Exception:
                pass

        # Phase 2: probe RTSP ports and add candidates
        rtsp_candidates = []
        for rtsp_port in (554, 8554):
            if self.stop_event.is_set():
                break
            if _cam_tcp_open(ip, rtsp_port, 1500):
                for rpath, rport, vendor, _bonus in CAMERA_RTSP_PATHS:
                    if rport == rtsp_port:
                        url = f"rtsp://{ip}:{rtsp_port}{rpath}"
                        label = f"{rpath}  [RTSP {vendor}]  port {rtsp_port} open"
                        rtsp_candidates.append((url, "RTSP", label))

        self.after(0, lambda: self._show_probe_results(ip, port, found, rtsp_candidates))

    def _make_opener(self, user, pw, url):
        if user:
            pm = urllib.request.HTTPPasswordMgrWithDefaultRealm()
            pm.add_password(None, url, user, pw)
            return urllib.request.build_opener(
                urllib.request.HTTPBasicAuthHandler(pm),
                urllib.request.HTTPDigestAuthHandler(pm),
            )
        return urllib.request.build_opener()

    def _show_probe_results(self, ip, port, found, rtsp_candidates=None):
        self._listbox.delete(0, "end")
        rtsp_candidates = rtsp_candidates or []

        all_results      = list(found) + list(rtsp_candidates)
        self._probe_results  = all_results
        self._lb_index_map   = []  # listbox row → index into _probe_results (or -1)

        if not all_results:
            for line in [
                "  No streams found on this IP/port.", "",
                "  Try:", f"  • Different port (81, 8080, 8081)",
                f"  • Adding credentials", f"  • Pasting URL directly below",
            ]:
                self._listbox.insert("end", line)
                self._lb_index_map.append(-1)
            if not CV2_AVAILABLE:
                self._listbox.insert("end", "")
                self._lb_index_map.append(-1)
                self._listbox.insert("end", "  RTSP needs: pip install opencv-python")
                self._lb_index_map.append(-1)
        else:
            ri = 0   # running index into all_results
            if found:
                self._listbox.insert("end", "── HTTP Streams ──")
                self._lb_index_map.append(-1)
                for _, _, label in found:
                    self._listbox.insert("end", f"  {label}")
                    self._lb_index_map.append(ri)
                    ri += 1
            if rtsp_candidates:
                if found:
                    self._listbox.insert("end", "")
                    self._lb_index_map.append(-1)
                rtsp_hdr = "── RTSP Streams"
                if CV2_AVAILABLE:
                    rtsp_hdr += " (click to connect) ──"
                else:
                    rtsp_hdr += " (need opencv-python) ──"
                self._listbox.insert("end", rtsp_hdr)
                self._lb_index_map.append(-1)
                for _, _, label in rtsp_candidates:
                    self._listbox.insert("end", f"  {label}")
                    self._lb_index_map.append(ri)
                    ri += 1
            # Select first actual result row
            for idx, mapped in enumerate(self._lb_index_map):
                if mapped != -1:
                    self._listbox.selection_set(idx)
                    break
            self._connect_btn.configure(state="normal")

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
        self._connect_btn.configure(state="normal" if result else "disabled")

    # ── Connect ────────────────────────────────────────────────────────────
    def _connect_selected(self):
        result = self._lb_selected_result()
        if not result:
            return
        url, stype, _ = result
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
        self._stop_stream()          # stop any running stream
        self.running = True
        self.stop_event.clear()
        self._stream_url = url
        self._frame_count = 0
        self._lost_count  = 0
        self._fps_times.clear()
        label = f"Connecting [{stype}] → {url[:70]}"
        self._lbl_url.configure(text=label)
        self._lbl_frm.configure(text="0")
        self._lbl_lost.configure(text="0")
        self._lbl_fps.configure(text="—")
        self._lbl_res.configure(text="—")
        self._stop_stream_btn.configure(state="normal")
        self._connect_btn.configure(state="disabled")
        user = self._user_var.get().strip()
        pw   = self._pass_var.get()
        if stype == "RTSP":
            threading.Thread(target=self._stream_worker_rtsp,
                             args=(url, user, pw), daemon=True).start()
        else:
            threading.Thread(target=self._stream_worker,
                             args=(url, stype, user, pw), daemon=True).start()

    def _stop_stream(self):
        self.running = False
        self.stop_event.set()
        if hasattr(self, "_stop_stream_btn"):
            self._stop_stream_btn.configure(state="disabled")
        if hasattr(self, "_connect_btn"):
            self._connect_btn.configure(state="normal" if self._probe_results else "disabled")
        if hasattr(self, "_lbl_url"):
            self._lbl_url.configure(text="Stopped")

    # ── Stream worker (background thread) ─────────────────────────────────
    def _stream_worker(self, url, stype, user, pw):
        resp = None
        try:
            opener = self._make_opener(user, pw, url)
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "NetToolsPro/1.0")
            resp = opener.open(req, timeout=10)
            ct   = resp.headers.get("Content-Type", "").lower()
            self.after(0, lambda: self._lbl_url.configure(text=f"▶  {url}"))

            if "multipart" in ct or "mjpeg" in ct:
                self._read_mjpeg(resp)
            else:
                # Treat as single-JPEG / refreshing snapshot
                self._read_jpeg_loop(resp, opener, url)

        except Exception as e:
            self.after(0, lambda err=str(e): (
                self._lbl_url.configure(text=f"✗  Error: {err}"),
                self._draw_error(err),
            ))
        finally:
            # Always close the connection to release socket resources
            try:
                if resp is not None:
                    resp.close()
            except Exception:
                pass
            self.running = False
            self.after(0, lambda: (
                self._stop_stream_btn.configure(state="disabled"),
                self._connect_btn.configure(state="normal" if self._probe_results else "disabled"),
            ))

    # ── RTSP stream worker (cv2) ──────────────────────────────────────────
    def _stream_worker_rtsp(self, url, user, pw):
        """Stream RTSP via OpenCV VideoCapture. Requires opencv-python."""
        if not CV2_AVAILABLE:
            self.after(0, lambda: (
                self._lbl_url.configure(
                    text="✗  opencv-python not installed — required for RTSP"),
                self._draw_error(
                    "RTSP playback requires the opencv-python package.\n\n"
                    "Install it with:\n  pip install opencv-python\n\n"
                    "Then restart NetTools Pro."),
            ))
            self.running = False
            self.after(0, lambda: (
                self._stop_stream_btn.configure(state="disabled"),
                self._connect_btn.configure(
                    state="normal" if self._probe_results else "disabled"),
            ))
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
                self.after(0, lambda: (
                    self._lbl_url.configure(text="✗  RTSP stream failed to open"),
                    self._draw_error(
                        "Could not open RTSP stream.\n\n"
                        "Check URL, credentials, and camera status.\n"
                        "Ensure the camera is reachable on this subnet."),
                ))
                return

            self.after(0, lambda: self._lbl_url.configure(
                text=f"▶ RTSP  {url[:75]}"))

            consecutive_fail = 0
            while self.running and not self.stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    consecutive_fail += 1
                    if consecutive_fail > 60:
                        self.after(0, lambda: self._lbl_url.configure(
                            text="✗  RTSP: too many consecutive read failures"))
                        break
                    self.after(0, self._inc_lost)
                    time.sleep(0.03)
                    continue
                consecutive_fail = 0
                # BGR → RGB → PIL Image
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                self.after(0, lambda i=img: self._display_pil_image(i))
                # ~30 fps cap to avoid flooding the UI
                time.sleep(0.016)

        except Exception as e:
            self.after(0, lambda err=str(e): (
                self._lbl_url.configure(text=f"✗  RTSP Error: {err}"),
                self._draw_error(f"RTSP Error:\n{err}"),
            ))
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
            self.running = False
            self.after(0, lambda: (
                self._stop_stream_btn.configure(state="disabled"),
                self._connect_btn.configure(
                    state="normal" if self._probe_results else "disabled"),
            ))

    # ── Display PIL image directly (avoids re-encode) ─────────────────────
    def _display_pil_image(self, img):
        """Display a PIL Image on the canvas. Main-thread only."""
        try:
            cw = self._canvas.winfo_width()
            ch = self._canvas.winfo_height()
            if cw < 10 or ch < 10:
                return
            img.thumbnail((cw, ch), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._canvas.delete("all")
            self._canvas.create_image(cw // 2, ch // 2,
                                      image=photo, anchor="center")
            self._canvas.image = photo
            self._current_photo = photo
            self._snapshot_img  = img

            self._frame_count += 1
            now = time.time()
            self._fps_times.append(now)
            self._lbl_frm.configure(text=f"{self._frame_count:,}")
            self._lbl_res.configure(text=f"{img.width}×{img.height}")
            if self._frame_count % 10 == 0 and len(self._fps_times) >= 2:
                span = self._fps_times[-1] - self._fps_times[0]
                fps  = len(self._fps_times) / span if span > 0 else 0
                self._lbl_fps.configure(text=f"{fps:.1f}")
        except Exception:
            self._lost_count += 1
            self._lbl_lost.configure(text=str(self._lost_count),
                                     text_color="#f85149")

    def _read_mjpeg(self, resp):
        """Parse multipart MJPEG stream using raw JPEG SOI/EOI markers."""
        buf = b""
        while self.running and not self.stop_event.is_set():
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
                self.after(0, lambda j=jpeg: self._display_frame(j))

    def _read_jpeg_loop(self, first_resp, opener, url):
        """Continuously refresh a single-frame JPEG (snapshot polling)."""
        # Display the first response
        try:
            data = first_resp.read()
            if data:
                self.after(0, lambda d=data: self._display_frame(d))
        except Exception:
            pass

        # Poll every second
        while self.running and not self.stop_event.is_set():
            time.sleep(1)
            if self.stop_event.is_set():
                break
            try:
                req = urllib.request.Request(url)
                req.add_header("Cache-Control", "no-cache")
                req.add_header("User-Agent", "NetToolsPro/1.0")
                with opener.open(req, timeout=5) as resp:
                    data = resp.read()
                if data:
                    self.after(0, lambda d=data: self._display_frame(d))
            except Exception:
                self.after(0, self._inc_lost)

    # ── Frame display (main thread) ────────────────────────────────────────
    def _inc_lost(self):
        """Increment lost-frame counter — must be called on the main thread."""
        self._lost_count += 1
        self._lbl_lost.configure(text=str(self._lost_count), text_color="#f85149")

    def _display_frame(self, jpeg_bytes):
        try:
            img = Image.open(_io.BytesIO(jpeg_bytes))
            img.load()

            cw = self._canvas.winfo_width()
            ch = self._canvas.winfo_height()
            if cw < 10 or ch < 10:
                return

            # Fit-to-canvas while preserving aspect ratio
            img.thumbnail((cw, ch), Image.LANCZOS)

            photo = ImageTk.PhotoImage(img)
            self._canvas.delete("all")
            self._canvas.create_image(cw // 2, ch // 2,
                                      image=photo, anchor="center")
            self._canvas.image = photo      # Prevent garbage collection
            self._current_photo = photo
            self._snapshot_img  = img       # Keep for saving

            # Stats
            self._frame_count += 1
            now = time.time()
            self._fps_times.append(now)
            self._lbl_frm.configure(text=f"{self._frame_count:,}")
            self._lbl_res.configure(text=f"{img.width}×{img.height}")

            if self._frame_count % 10 == 0 and len(self._fps_times) >= 2:
                span = self._fps_times[-1] - self._fps_times[0]
                fps  = len(self._fps_times) / span if span > 0 else 0
                self._lbl_fps.configure(text=f"{fps:.1f}")

        except Exception:
            self._lost_count += 1
            self._lbl_lost.configure(text=str(self._lost_count),
                                     text_color="#f85149")

    def _draw_error(self, msg):
        self._canvas.delete("all")
        w = max(self._canvas.winfo_width(), 400)
        h = max(self._canvas.winfo_height(), 200)
        self._canvas.create_text(w // 2, h // 2,
                                 text=f"✗  Connection failed\n\n{msg}\n\n"
                                      "Check IP, port, credentials and camera stream URL.",
                                 font=("Consolas", 11), fill="#f85149",
                                 justify="center", width=w - 40)

    # ── Snapshot ───────────────────────────────────────────────────────────
    def _snapshot(self):
        if not PILLOW_AVAILABLE:
            return
        img = self._snapshot_img
        if img is None:
            messagebox.showinfo("Snapshot", "No frame captured yet.")
            return
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        ip  = re.sub(r"[^\d.]", "_", self._ip_var.get().strip()) or "camera"
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
            subprocess.Popen(["cmd", "/c", "start", "", url],
                             creationflags=SUBPROCESS_FLAGS)
        except Exception as e:
            messagebox.showerror("Error", str(e))


# ==================== Sidebar ====================
class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, on_select, **kwargs):
        super().__init__(parent, fg_color="#010409", corner_radius=0, **kwargs)
        self._on_select = on_select
        self._btns = {}
        self._build()

    def _build(self):
        # Logo / title
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

        # Navigation buttons
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", pady=(8, 0))

        for label, key in SIDEBAR_TOOLS:
            btn = ctk.CTkButton(
                nav, text=label, anchor="w",
                font=ctk.CTkFont(size=12),
                fg_color="transparent",
                hover_color="#21262d",
                text_color="#c9d1d9",
                height=36,
                corner_radius=6,
                command=lambda k=key: self._select(k),
            )
            btn.pack(fill="x", padx=8, pady=1)
            self._btns[key] = btn

        # Bottom info
        ctk.CTkFrame(self, fg_color="transparent").pack(fill="both", expand=True)

        info = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=0)
        info.pack(fill="x", side="bottom")
        local_ip = get_local_ip()
        ctk.CTkLabel(info, text=f"Local IP: {local_ip}",
                     font=ctk.CTkFont(size=10), text_color="#8b949e").pack(anchor="w", padx=12, pady=4)

        # Theme toggle
        self._theme = "dark"
        ctk.CTkButton(info, text="☀ / ☾  Toggle Theme", command=self._toggle_theme,
                      fg_color="transparent", hover_color="#21262d",
                      text_color="#8b949e", height=28, font=ctk.CTkFont(size=10)
                      ).pack(fill="x", padx=4, pady=(0, 2))

        # About button
        ctk.CTkButton(info, text="ℹ  About", command=self._show_about,
                      fg_color="transparent", hover_color="#21262d",
                      text_color="#8b949e", height=26, font=ctk.CTkFont(size=10)
                      ).pack(fill="x", padx=4, pady=(0, 6))

    def _select(self, key):
        for k, b in self._btns.items():
            if k == key:
                b.configure(fg_color="#21262d", text_color="#79c0ff")
            else:
                b.configure(fg_color="transparent", text_color="#c9d1d9")
        self._on_select(key)

    def _toggle_theme(self):
        self._theme = "light" if self._theme == "dark" else "dark"
        ctk.set_appearance_mode(self._theme)

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
            f"Python {sys.version.split()[0]}  ·  customtkinter  ·  psutil  ·  "
            f"dnspython  ·  Pillow"
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

# File extensions that can be executed via subprocess
_RUNNABLE_EXTS  = {".ps1", ".py", ".bat", ".cmd"}
# File extensions that can be opened in the editor but not executed
_VIEW_ONLY_EXTS = {".txt", ".json", ".yaml", ".yml", ".ini"}
# All extensions shown in the script browser and open-file dialog
_ALL_SCRIPT_EXTS = _RUNNABLE_EXTS | _VIEW_ONLY_EXTS

SCRIPT_LAB_FILETYPES = [
    ("Script files", "*.ps1 *.py *.bat *.cmd"),
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

# Inline PowerShell script for system diagnostics.
# Mirrors the sections in SkipperToolkit.ps1 Invoke-PCDiagnostikk:
# System, CPU/RAM, Disk, GPU, Network, Running Services, Windows Update,
# Autostart, Installed Programs, and last 30 critical/error events (7 days).
PS_DIAGNOSTICS = r"""
$ErrorActionPreference = 'SilentlyContinue'
Write-Output ("Diagnostics started: {0}  Machine: {1}  User: {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $env:COMPUTERNAME, $env:USERNAME)
Write-Output ""

Write-Output "=== SYSTEM ==="
try {
    $cs   = Get-CimInstance Win32_ComputerSystem
    $os   = Get-CimInstance Win32_OperatingSystem
    $bios = Get-CimInstance Win32_BIOS
    Write-Output ("  Manufacturer : {0}" -f $cs.Manufacturer)
    Write-Output ("  Model        : {0}" -f $cs.Model)
    Write-Output ("  OS           : {0}" -f $os.Caption)
    Write-Output ("  Version      : {0}" -f $os.Version)
    Write-Output ("  Build        : {0}" -f $os.BuildNumber)
    Write-Output ("  BIOS         : {0}" -f $bios.SMBIOSBIOSVersion)
} catch { Write-Output "  (Error reading system info)" }

Write-Output ""
Write-Output "=== CPU / RAM ==="
try {
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    $ramGB = [math]::Round((Get-CimInstance Win32_PhysicalMemory | Measure-Object Capacity -Sum).Sum / 1GB, 2)
    Write-Output ("  CPU    : {0}" -f $cpu.Name)
    Write-Output ("  Cores  : {0}  Logical: {1}" -f $cpu.NumberOfCores, $cpu.NumberOfLogicalProcessors)
    Write-Output ("  RAM    : {0} GB installed" -f $ramGB)
} catch { Write-Output "  (Error reading CPU/RAM)" }

Write-Output ""
Write-Output "=== DISK ==="
try {
    foreach ($d in (Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -gt 0 })) {
        $tot  = [math]::Round(($d.Used + $d.Free) / 1GB, 2)
        $free = [math]::Round($d.Free / 1GB, 2)
        $used = [math]::Round($d.Used / 1GB, 2)
        $pct  = if ($tot -gt 0) { [math]::Round(($free / $tot) * 100, 1) } else { 0 }
        Write-Output ("  {0}: Total {1} GB | Used {2} GB | Free {3} GB ({4}% free)" -f $d.Name, $tot, $used, $free, $pct)
    }
} catch { Write-Output "  (Error reading disk)" }

Write-Output ""
Write-Output "=== GPU ==="
try {
    foreach ($g in (Get-CimInstance Win32_VideoController)) {
        Write-Output ("  GPU    : {0}" -f $g.Caption)
        Write-Output ("  Driver : {0}  Status: {1}" -f $g.DriverVersion, $g.Status)
    }
} catch { Write-Output "  (Error reading GPU)" }

Write-Output ""
Write-Output "=== NETWORK ADAPTERS ==="
try {
    foreach ($n in (Get-CimInstance Win32_NetworkAdapterConfiguration | Where-Object { $_.IPEnabled })) {
        Write-Output ("  Adapter : {0}" -f $n.Description)
        Write-Output ("  IP      : {0}" -f ($n.IPAddress -join ', '))
        Write-Output ("  Gateway : {0}" -f ($n.DefaultIPGateway -join ', '))
        Write-Output ("  DNS     : {0}" -f ($n.DNSServerSearchOrder -join ', '))
        Write-Output ""
    }
} catch { Write-Output "  (Error reading network)" }

Write-Output "=== RUNNING SERVICES ==="
try {
    Get-Service | Where-Object { $_.Status -eq 'Running' } | Sort-Object DisplayName |
        ForEach-Object { Write-Output ("  {0} ({1})" -f $_.DisplayName, $_.Name) }
} catch { Write-Output "  (Error reading services)" }

Write-Output ""
Write-Output "=== WINDOWS UPDATE — LAST 10 HOTFIXES ==="
try {
    Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 10 |
        ForEach-Object {
            $d = if ($_.InstalledOn) { $_.InstalledOn.ToString('yyyy-MM-dd') } else { 'Unknown' }
            Write-Output ("  {0} | {1} | {2}" -f $d, $_.HotFixID, $_.Description)
        }
} catch { Write-Output "  (Error reading hotfixes)" }

Write-Output ""
Write-Output "=== AUTOSTART ==="
try {
    foreach ($regPath in @('HKCU:\Software\Microsoft\Windows\CurrentVersion\Run',
                            'HKLM:\Software\Microsoft\Windows\CurrentVersion\Run')) {
        $props = Get-ItemProperty $regPath -ErrorAction SilentlyContinue
        if ($props) {
            $props.PSObject.Properties | Where-Object { $_.Name -notlike 'PS*' } |
                ForEach-Object { Write-Output ("  {0} | {1}" -f $_.Name, $regPath) }
        }
    }
} catch { Write-Output "  (Error reading autostart)" }

Write-Output ""
Write-Output "=== INSTALLED PROGRAMS (first 100, alphabetical) ==="
try {
    $regPaths = @('HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
                  'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
                  'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*')
    Get-ItemProperty $regPaths -ErrorAction SilentlyContinue |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_.DisplayName) } |
        Sort-Object DisplayName -Unique | Select-Object -First 100 |
        ForEach-Object { Write-Output ("  {0} | {1} | {2}" -f $_.DisplayName, $_.DisplayVersion, $_.Publisher) }
} catch { Write-Output "  (Error reading installed programs)" }

Write-Output ""
Write-Output "=== CRITICAL/ERROR EVENTS — LAST 7 DAYS (max 30) ==="
try {
    Get-WinEvent -FilterHashtable @{ LogName='System'; Level=1,2;
        StartTime=(Get-Date).AddDays(-7) } -MaxEvents 30 -ErrorAction Stop |
    ForEach-Object {
        Write-Output ("  [{0}] ID {1} | {2}" -f $_.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss'), $_.Id, $_.ProviderName)
        Write-Output ("        {0}" -f (($_.Message -replace '\r|\n',' ' -replace '\s+',' ').Substring(0, [math]::Min(120,$_.Message.Length))))
    }
} catch { Write-Output "  (No events found or access denied)" }

Write-Output ""
Write-Output "=== DONE ==="
"""

# Result keywords for SFC output parsing
_SFC_RESULTS = [
    ("did not find any integrity violations", "success",
     "No integrity violations found."),
    ("successfully repaired",                "success",
     "Violations found — repaired successfully."),
    ("found corrupt files and was unable",   "error",
     "Corrupt files found — repair FAILED. Run DISM first, then re-run SFC."),
]


class SystemToolsFrame(BaseToolFrame):
    """Windows maintenance, repair, and service management tools."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.dry_run_var = tk.BooleanVar(value=False)
        self._log_dir_ready = False  # lazy-init: create log dir on first write
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

        # Diagnostics
        section("Diagnostics")
        btn("Run System Diagnostics", self._run_diagnostics)

        # System Repair
        section("System Repair")
        btn("SFC Scan", self._run_sfc)
        btn("DISM Repair", self._run_dism)

        # Service Debloat
        section("Service Debloat")
        btn(f"Safe Debloat  ({len(_SAFE_SERVICES)} off, {len(_MANUAL_SERVICES)} manual)",
            self._run_safe_debloat, "#E65100", "#BF360C")
        btn(f"Aggressive  ({len(_ALL_DEBLOAT_SERVICES)} off, {len(_MANUAL_SERVICES)} manual)",
            self._run_aggressive_debloat, "#B71C1C", "#7F0000")

        # Backup / Restore
        section("Backup / Restore")
        btn("Backup Services", self._run_backup)
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
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

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
        subprocess.Popen(["explorer", str(folder)], creationflags=SUBPROCESS_FLAGS)

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
        self.after(0, self.ui_done)  # ui_done() resets self.running + button states

    # ── Pre-debloat auto-backup (synchronous) ────────────────────────────────

    def _do_quick_backup(self, path: str):
        """Export all service states to JSON before a destructive debloat operation.
        Runs synchronously before the debloat thread is spawned."""
        ps = (
            "Get-Service | ForEach-Object { [PSCustomObject]@{ "
            "Name=$_.Name; Status=$_.Status.ToString(); "
            "StartType=$_.StartType.ToString() } } "
            f"| ConvertTo-Json -Depth 2 "
            f"| Set-Content -Path '{path}' -Encoding UTF8"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        self.q(f"Auto-backup saved: {path}", "info")
        self._log(f"Auto-backup: {path}")

    # ── Low-level service helper ──────────────────────────────────────────────

    def _set_service_startup(self, svc, startup_type, dry):
        """Set a Windows service startup type via PowerShell.
        Returns (success: bool, display_line: str).
        dry=True returns a preview line without running anything."""
        if dry:
            return True, f"WOULD: Set-Service '{svc}' -StartupType {startup_type}"
        ps = (f"try {{ Set-Service -Name '{svc}' -StartupType {startup_type} "
              f"-ErrorAction Stop; Write-Output 'OK: {svc} -> {startup_type}' }} "
              f"catch {{ Write-Output ('FAIL: {svc}: ' + $_.Exception.Message) }}")
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        line = res.stdout.strip() or res.stderr.strip()
        return line.startswith("OK:"), line

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
        proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", PS_DIAGNOSTICS],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            creationflags=SUBPROCESS_FLAGS)
        for line in proc.stdout:
            if self.stop_event.is_set():
                proc.terminate()
                break
            line = line.rstrip()
            tag = "header" if line.startswith("===") else "normal"
            self.q(line, tag)
        proc.wait()
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
        proc = subprocess.Popen(
            ["sfc", "/scannow"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            creationflags=SUBPROCESS_FLAGS)
        lines = []
        for line in proc.stdout:
            if self.stop_event.is_set():
                proc.terminate()
                break
            stripped = line.rstrip()
            if stripped:
                self.q(stripped, "normal")
                lines.append(stripped.lower())
        proc.wait()
        # Parse result from the last 15 output lines
        result_tag, result_msg = "info", "SFC scan complete."
        for needle, tag, msg in _SFC_RESULTS:
            if any(needle in l for l in lines[-15:]):
                result_tag, result_msg = tag, msg
                break
        self._finish(result_msg, result_tag)

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
        proc = subprocess.Popen(
            ["DISM", "/Online", "/Cleanup-Image", "/RestoreHealth"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            creationflags=SUBPROCESS_FLAGS)
        for line in proc.stdout:
            if self.stop_event.is_set():
                proc.terminate()
                break
            stripped = line.rstrip()
            if stripped:
                # Highlight percentage progress lines
                tag = "info" if re.search(r'\d+\.\d+%', stripped) else "normal"
                self.q(stripped, tag)
        proc.wait()
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
        self._do_quick_backup(path)
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
            success, line = self._set_service_startup(name, start_type, dry)
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
            self._do_quick_backup(backup_path)

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
            success, line = self._set_service_startup(svc, "Disabled", dry)
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
            success, line = self._set_service_startup(svc, "Manual", dry)
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
        subprocess.Popen(["explorer", str(SCRIPT_LAB_DEFAULT_DIR)],
                         creationflags=SUBPROCESS_FLAGS)

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
            defaultextension=".ps1",
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
        suffix = pathlib.Path(path).suffix.lower()
        if suffix == ".ps1":
            return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", path]
        if suffix == ".py":
            return [sys.executable, path]
        if suffix in (".bat", ".cmd"):
            return ["cmd", "/c", path]
        return []

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
            self.after(0, self.ui_done)

    # ── Output + admin helpers ────────────────────────────────────────────────

    def _clear_output(self):
        self.output.clear()

    def _is_admin(self):
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

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

        row2 = ctk.CTkFrame(ctrl, fg_color="transparent")
        row2.pack(fill="x", padx=14, pady=(4, 10))

        r = self.make_btn_row(row2, self._start, self.stop_op, start_text="▶  Run Analysis")
        r.pack(side="left")
        ctk.CTkButton(
            row2, text="🗑  Clear", command=self._clear,
            fg_color="#21262d", hover_color="#30363d", width=90,
        ).pack(side="left", padx=(10, 0))
        self._admin_lbl = ctk.CTkLabel(
            row2, text="⚠  Live Capture requires administrator privileges",
            text_color="#d29922", font=ctk.CTkFont(size=11),
        )  # hidden by default — shown on PermissionError

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
        adapter = self._resolve_adapter()
        if adapter is None:
            self.output.clear()
            self.output.append("No adapter selected or no IPv4 adapters found.", "error")
            return
        adapter_ip, adapter_mask, adapter_label = adapter
        mode     = self._mode_var.get()
        duration = self._duration_var.get()

        self.output.clear()
        self._tree.delete(*self._tree.get_children())
        self._candidates.clear()
        self._selected_cand = None
        self._copy_rtsp_btn.configure(state="disabled")
        self._copy_netsh_btn.configure(state="disabled")
        self._summary_var.set("Analysis running…")
        self._admin_lbl.pack_forget()

        self.q(f"Adapter:  {adapter_label}", "info")
        self.q(f"Mode:     {'Live Capture' if mode == 'live' else 'ARP + Active Scan'}", "info")
        if mode == "live":
            self.q(f"Duration: {duration}s", "info")
        self.q("", "normal")

        self.running = True
        self.stop_event.clear()
        self.start_poll()
        self.ui_started()

        if mode == "live":
            threading.Thread(
                target=self._worker_live_capture,
                args=(adapter_ip, adapter_mask, duration),
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
            self.after(0, self.ui_done)

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
    def _worker_live_capture(self, adapter_ip, adapter_mask, duration):
        dhcp_seen = {}   # mac -> latest DHCP dict
        raw = None
        try:
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
                    parsed = _parse_dhcp_from_raw(data)
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
            self.q("Live Capture requires administrator privileges.", "error")
            self.q("Falling back to ARP + Scan…", "warning")
            self.after(0, lambda: self._admin_lbl.pack(side="left", padx=(16, 0)))
        except Exception as exc:
            self.q(f"Capture error: {exc}", "error")
        finally:
            if raw is not None:
                try:
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
            self.after(0, self.ui_done)

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
            if ev.get("vendor_http"):
                e["vendor_http"]         = ev["vendor_http"]
                e["camera_http_keywords"] = True
                if not e["vendor"]:
                    e["vendor"] = ev["vendor_http"]

        # Score and build candidate list
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
            same      = cand["subnet"].get("same_subnet")
            reach     = "✔" if same is True else ("⚠ mismatch" if same is False else "?")
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
        same   = sub.get("same_subnet")
        div    = "─" * 60

        self.output.append(f"\n{div}", "dim")
        self.output.append(f" Candidate: {ip}  (Confidence: {conf})\n{div}", "header")
        self.output.append(f"\nIP:          {ip}", "normal")
        self.output.append(f"\nMAC:         {mac}", "normal")
        self.output.append(f"\nVendor:      {vendor}", "normal")
        self.output.append(f"\nConfidence:  {conf}  (score {score}/100)\n", "normal")

        # Evidence
        self.output.append(f"\n── Evidence {'─'*49}", "dim")
        if cand.get("dhcp_request"):
            di     = cand.get("dhcp_info") or {}
            suffix = f"  type={di.get('msg_type','?')}  client={di.get('client_ip','?')}" if di else ""
            self.output.append(f"\n  ✔ DHCP packet observed from this MAC{suffix}", "success")
        if cand.get("camera_oui"):
            self.output.append(f"\n  ✔ Camera OUI match: {mac[:8]} → {vendor}", "success")
        if cand.get("rtsp_open"):
            self.output.append(f"\n  ✔ RTSP port 554 open", "success")
        if cand.get("rtsp_8554"):
            self.output.append(f"\n  ✔ RTSP port 8554 open (alternate)", "success")
        if cand.get("http_open"):
            self.output.append(f"\n  ✔ HTTP port open", "success")
        if cand.get("camera_http_keywords"):
            self.output.append(
                f"\n  ✔ Camera keywords in HTTP response → {cand.get('vendor_http')}", "success",
            )
        if cand.get("onvif_found"):
            self.output.append(f"\n  ✔ ONVIF WS-Discovery response received", "success")
        if cand.get("ssdp_found"):
            self.output.append(f"\n  ✔ SSDP/UPnP response received", "success")
        if cand.get("arp_entry"):
            self.output.append(f"\n  ✔ ARP cache entry present", "success")

        # Subnet analysis
        self.output.append(f"\n\n── Subnet Analysis {'─'*41}", "dim")
        self.output.append(f"\n  Adapter:    {a_ip} / {a_mask}  (net {a_net})", "normal")
        self.output.append(f"\n  Camera IP:  {ip}", "normal")
        if same is True:
            self.output.append(
                f"\n  ✔ Same subnet — adapter can reach camera directly.", "success",
            )
        elif same is False:
            self.output.append(
                f"\n  ⚠  SUBNET MISMATCH — direct browser/RTSP access will fail.", "warning",
            )
            if sugg.get("ip"):
                self.output.append(f"\n\n  Suggested temporary adapter config:", "info")
                self.output.append(f"\n    IP address:  {sugg['ip']}", "cyan")
                self.output.append(f"\n    Subnet mask: {sugg['mask']}", "cyan")
                self.output.append(f"\n    Gateway:     (leave empty)", "cyan")
                adapter_name = self._adapter_var.get().split("[")[0].strip()
                cmd = (
                    f'netsh interface ip set address name="{adapter_name}" '
                    f"static {sugg['ip']} {sugg['mask']}"
                )
                self.output.append(f"\n\n  netsh command (click 'Copy netsh'):", "dim")
                self.output.append(f"\n    {cmd}", "dim")
        else:
            self.output.append(f"\n  ? Could not determine subnet relationship.", "warning")

        # RTSP candidate URLs
        self.output.append(f"\n\n── Candidate RTSP URLs {'─'*37}", "dim")
        self.output.append(f"\n  {'#':<4} {'Vendor':<12} {'URL'}", "dim")
        for i, entry in enumerate(rtsp[:10], 1):
            stars = "★★" if entry["score_bonus"] == 2 else "★ "
            self.output.append(
                f"\n  {i:<4} {entry['vendor'] + ' ' + stars:<14} {entry['url']}", "normal",
            )

        # Recommendation
        self.output.append(f"\n\n── Recommendation {'─'*43}", "dim")
        step = 1
        if same is False and sugg.get("ip"):
            self.output.append(
                f"\n  {step}. Change adapter IP to {sugg['ip']} / {sugg['mask']} (no gateway).",
                "warning",
            )
            step += 1
        self.output.append(
            f"\n  {step}. Try browser:  http://{ip}  or  http://{ip}:80", "info",
        )
        step += 1
        if rtsp:
            self.output.append(
                f"\n  {step}. Try RTSP (e.g. VLC):  {rtsp[0]['url']}", "info",
            )
            step += 1
        if same is False:
            self.output.append(
                f"\n  {step}. Restore adapter to DHCP when done (netsh or adapter settings).", "dim",
            )
        no_ports = not cand.get("rtsp_open") and not cand.get("http_open")
        if no_ports:
            self.output.append(
                "\n\n  Note: No open ports confirmed — camera may be unreachable until "
                "adapter config is corrected (or camera is off).",
                "warning",
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


# ==================== Main App ====================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1340x820")
        self.minsize(980, 640)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        sidebar = Sidebar(self, on_select=self._show, width=210)
        sidebar.grid(row=0, column=0, sticky="nsew")

        # Content area
        content = ctk.CTkFrame(self, fg_color="#0d1117", corner_radius=0)
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)

        # Build all frames
        cls_map = {
            "ping":        PingFrame,
            "portscan":    PortScanFrame,
            "stress":      StressTestFrame,
            "traceroute":  TracerouteFrame,
            "dns":         DNSFrame,
            "netscan":     NetworkScanFrame,
            "subnet":      SubnetFrame,
            "wol":         WoLFrame,
            "interfaces":  InterfacesFrame,
            "bandwidth":   BandwidthFrame,
            "connections": ConnectionsFrame,
            "arp":         ARPFrame,
            "camfinder":   CameraFinderFrame,
            "camview":     CameraViewerFrame,
            "system_tools": SystemToolsFrame,
            "cam_analysis": CameraAnalysisFrame,
            "script_lab":   ScriptLabFrame,
        }
        self._frames = {}
        for key, cls in cls_map.items():
            frm = cls(content)
            frm.grid(row=0, column=0, sticky="nsew")
            self._frames[key] = frm

        sidebar.select_default()

    def _show(self, key):
        self._frames[key].tkraise()

    def _open_viewer(self, ip, port=80):
        """Switch to Stream Viewer and pre-fill the target camera IP."""
        self._show("camview")
        self._frames["camview"].set_target(ip, port)


# ==================== Entry Point ====================
def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
