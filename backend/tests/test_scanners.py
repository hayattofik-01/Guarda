from app.worker.scanners import nmap_scan, nuclei_scan

NMAP_XML = """<?xml version="1.0"?>
<nmaprun>
  <host>
    <address addr="203.0.113.10" addrtype="ipv4"/>
    <ports>
      <port protocol="tcp" portid="22">
        <state state="open"/>
        <service name="ssh" product="OpenSSH" version="8.9"/>
      </port>
      <port protocol="tcp" portid="23">
        <state state="open"/>
        <service name="telnet"/>
      </port>
      <port protocol="tcp" portid="80">
        <state state="closed"/>
        <service name="http"/>
      </port>
    </ports>
  </host>
</nmaprun>
"""

NUCLEI_JSONL = (
    '{"template-id":"CVE-2021-44228","host":"https://example.com",'
    '"matched-at":"https://example.com/","type":"http",'
    '"info":{"name":"Log4j RCE","severity":"critical",'
    '"classification":{"cve-id":["CVE-2021-44228"],"cvss-score":10.0},'
    '"reference":["https://nvd.nist.gov/vuln/detail/CVE-2021-44228"]}}'
)


def test_nmap_parse_open_ports_only():
    findings = nmap_scan._parse(NMAP_XML)
    ports = {f["port"] for f in findings}
    assert ports == {22, 23}  # closed port 80 excluded


def test_nmap_flags_risky_service():
    findings = nmap_scan._parse(NMAP_XML)
    telnet = next(f for f in findings if f["port"] == 23)
    assert telnet["severity"] == "low"
    assert "cleartext" in telnet["description"].lower()


def test_nuclei_parse_cve():
    findings = nuclei_scan._parse(NUCLEI_JSONL)
    assert len(findings) == 1
    f = findings[0]
    assert f["cve_id"] == "CVE-2021-44228"
    assert f["severity"] == "critical"
    assert f["cvss_score"] == 10.0


def test_nuclei_parse_ignores_garbage_lines():
    assert nuclei_scan._parse("not-json\n\n") == []
