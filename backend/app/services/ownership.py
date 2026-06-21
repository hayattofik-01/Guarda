"""Target ownership verification.

A scan may only run against a target whose ownership has been proven. We support
two zero-cost methods:

- ``dns_txt``: the user adds a TXT record ``perimeter-verification=<token>``.
- ``http_file``: the user serves ``/.well-known/perimeter-verification.txt``
  containing the token over HTTP(S).

This is the same pattern used by ACME / search-console style verification and
keeps the scanner from being pointed at assets the user does not control.
"""

from __future__ import annotations

import ipaddress

import dns.resolver
import httpx

TXT_PREFIX = "perimeter-verification="
WELL_KNOWN_PATH = "/.well-known/perimeter-verification.txt"


def _is_ip_or_cidr(address: str) -> bool:
    try:
        ipaddress.ip_network(address, strict=False)
        return True
    except ValueError:
        return False


def dns_instructions(address: str, token: str) -> str:
    return (
        f"Add this DNS TXT record to {address} and then click Verify:\n\n"
        f"    {address}.  IN  TXT  \"{TXT_PREFIX}{token}\""
    )


def http_instructions(address: str, token: str) -> str:
    return (
        f"Serve this file over HTTP(S) on {address} and then click Verify:\n\n"
        f"    URL:     http(s)://{address}{WELL_KNOWN_PATH}\n"
        f"    Content: {token}"
    )


def verify_dns_txt(address: str, token: str) -> bool:
    if _is_ip_or_cidr(address):
        # DNS TXT verification only applies to hostnames.
        return False
    expected = f"{TXT_PREFIX}{token}"
    try:
        answers = dns.resolver.resolve(address, "TXT", lifetime=10)
    except Exception:
        return False
    for rdata in answers:
        if hasattr(rdata, "strings"):
            value = b"".join(rdata.strings).decode("utf-8", "ignore")
        else:
            value = str(rdata)
        if expected in value.strip().strip('"'):
            return True
    return False


def verify_http_file(address: str, token: str) -> bool:
    for scheme in ("https", "http"):
        url = f"{scheme}://{address}{WELL_KNOWN_PATH}"
        try:
            resp = httpx.get(url, timeout=10, follow_redirects=True)
            if resp.status_code == 200 and token in resp.text.strip():
                return True
        except Exception:
            continue
    return False
