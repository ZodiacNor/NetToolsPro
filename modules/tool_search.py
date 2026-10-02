"""Search the existing navigation catalog without importing GUI or backends."""
ALIASES = {
    "ping": "latency packet loss reachability",
    "portscan": "tcp ports services",
    "traceroute": "route hops path tracert",
    "dns": "lookup resolve hostname records",
    "netscan": "network hosts devices discovery",
    "netdiscover": "arp scan layer 2 ethernet",
    "wol": "wake on lan magic packet",
    "camfinder": "camera onvif ssdp discovery",
    "camview": "camera rtsp mjpeg jpeg playback stream wall",
    "cam_analysis": "camera analysis ports fingerprint",
    "bluetooth": "bluez ble wireless devices",
    "bandwidth": "traffic speed throughput monitor",
    "livecapture": "packets sniff capture",
    "subnet": "cidr calculate mask ip network",
    "mdns": "bonjour zeroconf discovery",
    "system_tools": "diagnostics maintenance",
    "script_lab": "scripts python bash powershell editor",
}


def search_tools(query, structure):
    """All query words must match label, category, or common tool terminology."""
    words = query.casefold().split()
    categories = {key: label for kind, label, key, _ in structure if kind == "category"}
    results = []
    for kind, label, key, category in structure:
        if kind not in ("tool", "standalone"):
            continue
        category_label = categories.get(category, "Workspace")
        haystack = f"{label} {category_label} {ALIASES.get(key, '')}".casefold()
        if all(word in haystack for word in words):
            results.append((key, label, category_label))
    return results
