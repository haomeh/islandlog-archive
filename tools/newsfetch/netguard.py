"""Network guards for the crawlers (T64: F-03 body cap, F-04 address check).

read_capped and gunzip_capped stop a huge body and a gzip bomb.
check_public_url refuses a non-HTTP scheme and any host that resolves to a private,
loopback or link-local address.
"""

import ipaddress
import socket
import urllib.parse
import zlib

MAX_BODY_BYTES = 10 * 1024 * 1024
MIN_HOST_GAP = 1.1  # R179, R324.4: seconds between two requests to one host. Every HTTP route uses this value.


class BodyTooLarge(OSError):
    """A response body or its decompressed form is larger than MAX_BODY_BYTES."""


class UnsafeUrl(OSError):
    """The URL scheme or the resolved address is not allowed."""


def read_capped(fp, cap=None):
    cap = MAX_BODY_BYTES if cap is None else cap
    data = fp.read(cap + 1)
    if len(data) > cap:
        raise BodyTooLarge(f"body is larger than {cap} bytes")
    return data


def gunzip_capped(data, cap=None):
    """Decompress gzip data. Raise BodyTooLarge when the result is larger than cap."""
    cap = MAX_BODY_BYTES if cap is None else cap
    inflater = zlib.decompressobj(16 + zlib.MAX_WBITS)
    out = inflater.decompress(data, cap + 1)
    if len(out) > cap or inflater.unconsumed_tail:
        raise BodyTooLarge(f"decompressed body is larger than {cap} bytes")
    return out


def address_is_public(text):
    try:
        ip = ipaddress.ip_address(text.split("%", 1)[0])
    except ValueError:
        return False
    if getattr(ip, "ipv4_mapped", None):
        ip = ip.ipv4_mapped
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
                or ip.is_reserved or ip.is_unspecified) and ip.is_global


def check_public_url(url, resolve=socket.getaddrinfo):
    """Raise UnsafeUrl unless url is http or https and every resolved address is public."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise UnsafeUrl(f"refused scheme or host: {parts.scheme}")
    try:
        infos = resolve(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80),
                        proto=socket.IPPROTO_TCP)
    except socket.gaierror as err:
        raise UnsafeUrl(f"cannot resolve {parts.hostname}") from err
    addresses = {info[4][0] for info in infos}
    if not addresses or not all(address_is_public(a) for a in addresses):
        raise UnsafeUrl(f"refused address for {parts.hostname}")
