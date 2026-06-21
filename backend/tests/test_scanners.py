from app.worker.scanners import (
    gitleaks_scan,
    httpx_scan,
    nuclei_scan,
    subfinder_scan,
)

NUCLEI_JSONL = (
    '{"template-id":"git-config","host":"https://example.com",'
    '"matched-at":"https://example.com/.git/config","type":"http",'
    '"info":{"name":"Exposed .git config","severity":"medium","tags":["exposure","config"]}}\n'
    '{"template-id":"aws-token","host":"https://example.com",'
    '"matched-at":"https://example.com/app.js","type":"http",'
    '"info":{"name":"AWS token","severity":"high","tags":["token","secret"]}}'
)


def test_nuclei_parse_and_classify():
    findings = nuclei_scan._parse(NUCLEI_JSONL)
    assert len(findings) == 2
    by_title = {f["title"]: f for f in findings}
    assert by_title["Exposed .git config"]["category"] == "exposed_data"
    assert by_title["AWS token"]["category"] == "sensitive_info"


def test_nuclei_classify_takeover():
    assert nuclei_scan._classify(["takeover"], "aws-takeover") == "reputation_risk"


def test_nuclei_parse_ignores_garbage():
    assert nuclei_scan._parse("not-json\n\n") == []


def test_subfinder_to_findings_excludes_root():
    findings = subfinder_scan.to_findings(["example.com", "api.example.com"], "example.com")
    assert len(findings) == 1
    assert findings[0]["host"] == "api.example.com"
    assert findings[0]["category"] == "footprint"


def test_httpx_flags_risky_titles():
    results = [
        {"url": "https://example.com", "title": "Home", "status_code": 200},
        {"url": "https://example.com/db", "title": "phpMyAdmin", "status_code": 200},
    ]
    findings = httpx_scan.to_findings(results)
    risky = next(f for f in findings if "phpMyAdmin" in (f["title"] + f["description"]))
    assert risky["category"] == "exposed_data"
    assert risky["severity"] == "medium"


def test_httpx_live_urls():
    assert httpx_scan.live_urls([{"url": "https://a.com"}, {"input": "https://b.com"}]) == [
        "https://a.com",
        "https://b.com",
    ]


def test_gitleaks_normalize_repo_url():
    assert gitleaks_scan._normalize_repo_url("owner/repo") == "https://github.com/owner/repo.git"
    assert gitleaks_scan._normalize_repo_url("https://github.com/o/r") == (
        "https://github.com/o/r.git"
    )
    # bare org page is rejected
    assert gitleaks_scan._normalize_repo_url("owner") is None


def test_gitleaks_parse():
    raw = (
        '[{"RuleID":"aws-access-token","File":"config.py","StartLine":12,'
        '"Commit":"abcdef123456"}]'
    )
    findings = gitleaks_scan._parse(raw, "https://github.com/o/r.git")
    assert len(findings) == 1
    assert findings[0]["category"] == "sensitive_info"
    assert findings[0]["severity"] == "high"
    assert findings[0]["location"] == "config.py:12"
