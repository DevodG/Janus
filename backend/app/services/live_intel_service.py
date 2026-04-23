from __future__ import annotations

import asyncio
import base64
import os
import socket
import time
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import logging

import httpx

logger = logging.getLogger(__name__)

try:
    import whois  # pip package: whois
except Exception:  # pragma: no cover
    whois = None


TIMEOUT = httpx.Timeout(5.0, connect=3.0)
CACHE_TTL_SECONDS = 300

_CACHE: Dict[str, tuple[float, dict]] = {}


BRAND_VERIFY: Dict[str, Dict[str, str]] = {
    "sbi": {
        "brand": "SBI",
        "instruction": "Open the official SBI app/site manually. Do not use the message link.",
        "official_site": "https://retail.onlinesbi.sbi/",
    },
    "hdfc": {
        "brand": "HDFC Bank",
        "instruction": "Open the official HDFC Bank app/site manually. Do not use the message link.",
        "official_site": "https://www.hdfcbank.com/",
    },
    "icici": {
        "brand": "ICICI Bank",
        "instruction": "Open the official ICICI Bank app/site manually. Do not use the message link.",
        "official_site": "https://www.icicibank.com/",
    },
    "axis": {
        "brand": "Axis Bank",
        "instruction": "Open the official Axis Bank app/site manually. Do not use the message link.",
        "official_site": "https://www.axisbank.com/",
    },
    "paytm": {
        "brand": "Paytm",
        "instruction": "Open the official Paytm app/site manually. Do not use the message link.",
        "official_site": "https://paytm.com/",
    },
    "amazon": {
        "brand": "Amazon",
        "instruction": "Open the official Amazon app/site manually. Do not use the message link.",
        "official_site": "https://www.amazon.in/",
    },
    "flipkart": {
        "brand": "Flipkart",
        "instruction": "Open the official Flipkart app/site manually. Do not use the message link.",
        "official_site": "https://www.flipkart.com/",
    },
    "airtel": {
        "brand": "Airtel",
        "instruction": "Open the official Airtel app/site manually. Do not use the message link.",
        "official_site": "https://www.airtel.in/",
    },
    "jio": {
        "brand": "Jio",
        "instruction": "Open the official Jio app/site manually. Do not use the message link.",
        "official_site": "https://www.jio.com/",
    },
    "india post": {
        "brand": "India Post",
        "instruction": "Use the official India Post tracking flow only. Do not use the message link.",
        "official_site": "https://www.indiapost.gov.in/",
    },
}

DEFAULT_NEXT_STEPS = [
    "Do not click the message link.",
    "Do not share OTP, PIN, CVV, or banking credentials.",
    "Verify only via the official app/site manually.",
    "Report suspicious communication via Sanchar Saathi Chakshu.",
    "If money is already lost, call 1930 immediately and report at cybercrime.gov.in.",
]


def _now_ts() -> float:
    return time.time()


def _cache_get(key: str) -> Optional[dict]:
    item = _CACHE.get(key)
    if not item:
        return None
    ts, value = item
    if _now_ts() - ts > CACHE_TTL_SECONDS:
        _CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: Any) -> None:
    _CACHE[key] = (_now_ts(), value)


def _unique_strs(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if not item:
            continue
        item = item.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _extract_domain(value: str) -> Optional[str]:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    if "://" not in raw:
        raw = f"https://{raw}"
    try:
        parsed = urlparse(raw)
        host = parsed.netloc or parsed.path
        host = host.lower().strip()
        if host.startswith("www."):
            host = host[4:]
        if ":" in host:
            host = host.split(":", 1)[0]
        return host or None
    except Exception:
        return None


def _normalize_url(value: str) -> Optional[str]:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    if "://" not in raw:
        raw = f"https://{raw}"
    try:
        parsed = urlparse(raw)
        if not parsed.netloc:
            return None
        return raw
    except Exception:
        return None


def _parse_creation_date(raw_value: Any) -> Optional[datetime]:
    if raw_value is None:
        return None
    if isinstance(raw_value, list) and raw_value:
        return _parse_creation_date(raw_value[0])
    if isinstance(raw_value, datetime):
        return raw_value
    if isinstance(raw_value, date):
        return datetime.combine(raw_value, datetime.min.time()).replace(tzinfo=timezone.utc)
    if isinstance(raw_value, str):
        # Very permissive fallback; enough for hackathon usage.
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d-%b-%Y", "%Y.%m.%d"):
            try:
                return datetime.strptime(raw_value[:19], fmt).replace(tzinfo=timezone.utc)
            except Exception:
                continue
    return None


def _severity_points(severity: str) -> int:
    return {"low": 5, "medium": 12, "high": 22}.get(severity, 0)


class LiveIntelService:
    def __init__(self) -> None:
        self.safe_browsing_key = os.getenv("SAFE_BROWSING_API_KEY", "").strip()
        self.virustotal_key = (
            os.getenv("VIRUSTOTAL_API_KEY", "").strip()
            or os.getenv("VT_API_KEY", "").strip()
        )
        self.urlscan_key = os.getenv("URLSCAN_API_KEY", "").strip()
        self.abuseipdb_key = os.getenv("ABUSEIPDB_API_KEY", "").strip()

    async def analyze(
        self,
        *,
        urls: List[str],
        domains: List[str],
        brands: List[str],
    ) -> dict:
        breadcrumbs = []
        urls = _unique_strs([u for u in (_normalize_url(x) for x in urls) if u])[:2]
        domain_candidates = domains[:]
        for u in urls:
            d = _extract_domain(u)
            if d:
                domain_candidates.append(d)
        domains = _unique_strs([d for d in (_extract_domain(x) for x in domain_candidates) if d])[:2]

        claimed_brand = self._pick_brand(brands, domains)
        if claimed_brand:
            breadcrumbs.append(f"Targeting brand analysis for: {claimed_brand}")

        tasks = []
        for url in urls:
            breadcrumbs.append(f"Analyzing live URL path: {url}")
            tasks.append(self._safe_browsing(url))
            tasks.append(self._virustotal(url))
            tasks.append(self._urlscan_search(url))
            tasks.append(self._http_probe(url))
        for domain in domains:
            breadcrumbs.append(f"Probing domain infrastructure: {domain}")
            tasks.append(self._domain_age(domain))
            tasks.append(self._abuseipdb(domain))
            tasks.append(self._dns_details(domain))

        evidence: List[dict] = []
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception) or not result:
                    continue
                if isinstance(result, list):
                    evidence.extend(result)

        # Deduplicate similar evidence entries
        seen = set()
        cleaned: List[dict] = []
        for item in evidence:
            key = (item.get("source"), item.get("signal"), str(item.get("value")))
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(item)

        risk_boost = min(45, sum(_severity_points(x.get("severity", "low")) for x in cleaned))
        reasons = [x["explanation"] for x in cleaned[:4] if x.get("explanation")]

        next_steps = list(DEFAULT_NEXT_STEPS)
        official_verify = self._official_verify(claimed_brand)

        if official_verify:
            next_steps = [
                official_verify["instruction"],
                *[x for x in DEFAULT_NEXT_STEPS if x != "Verify only via the official app/site manually."],
            ]
        
        breadcrumbs.append("Forensic scan complete.")
        return {
            "evidence": cleaned,
            "risk_boost": risk_boost,
            "claimed_brand": official_verify["brand"] if official_verify else claimed_brand,
            "official_verify": official_verify,
            "next_steps": next_steps,
            "reasons": reasons,
            "breadcrumbs": breadcrumbs,
        }

    def _pick_brand(self, brands: List[str], domains: List[str]) -> Optional[str]:
        lowered = " | ".join([*(b.lower() for b in brands), *(d.lower() for d in domains)])
        for key, meta in BRAND_VERIFY.items():
            if key in lowered:
                return meta["brand"]
        return brands[0] if brands else None

    def _official_verify(self, claimed_brand: Optional[str]) -> Optional[dict]:
        if not claimed_brand:
            return None
        c = claimed_brand.lower()
        for key, meta in BRAND_VERIFY.items():
            if key in c or c in key:
                return meta
        return {
            "brand": claimed_brand,
            "instruction": f"Verify {claimed_brand} only through its official app/site. Do not use the message link.",
            "official_site": None,
        }

    async def _safe_browsing(self, url: str) -> List[dict]:
        if not self.safe_browsing_key:
            return []

        cache_key = f"safe:{url}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        endpoint = (
            "https://safebrowsing.googleapis.com/v4/threatMatches:find"
            f"?key={self.safe_browsing_key}"
        )
        payload = {
            "client": {"clientId": "janus-guardian", "clientVersion": "1.0"},
            "threatInfo": {
                "threatTypes": [
                    "MALWARE",
                    "SOCIAL_ENGINEERING",
                    "UNWANTED_SOFTWARE",
                    "POTENTIALLY_HARMFUL_APPLICATION",
                ],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": url}],
            },
        }

        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.post(endpoint, json=payload)
                data = resp.json() if resp.content else {}
        except Exception:
            return []

        matches = data.get("matches", []) if isinstance(data, dict) else []
        if not matches:
            _cache_set(cache_key, [])
            return []

        out = [{
            "source": "Google Safe Browsing",
            "signal": "unsafe_url",
            "value": len(matches),
            "severity": "high",
            "explanation": "Google Safe Browsing flagged this URL as unsafe.",
        }]
        _cache_set(cache_key, out)
        return out

    async def _virustotal(self, url: str) -> List[dict]:
        if not self.virustotal_key:
            return []

        cache_key = f"vt:{url}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        encoded = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
        endpoint = f"https://www.virustotal.com/api/v3/urls/{encoded}"

        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(
                    endpoint,
                    headers={"x-apikey": self.virustotal_key, "accept": "application/json"},
                )
                if resp.status_code >= 400:
                    return []
                data = resp.json()
        except Exception:
            return []

        attrs = (((data or {}).get("data") or {}).get("attributes") or {})
        stats = attrs.get("last_analysis_stats") or {}
        malicious = int(stats.get("malicious", 0) or 0)
        suspicious = int(stats.get("suspicious", 0) or 0)

        out: List[dict] = []
        if malicious > 0:
            out.append({
                "source": "VirusTotal",
                "signal": "malicious_detections",
                "value": malicious,
                "severity": "high",
                "explanation": f"VirusTotal reported {malicious} malicious detections for this URL.",
            })
        elif suspicious > 0:
            out.append({
                "source": "VirusTotal",
                "signal": "suspicious_detections",
                "value": suspicious,
                "severity": "medium",
                "explanation": f"VirusTotal reported {suspicious} suspicious detections for this URL.",
            })

        _cache_set(cache_key, out)
        return out

    async def _urlscan_search(self, url: str) -> List[dict]:
        cache_key = f"urlscan:{url}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        headers = {}
        if self.urlscan_key:
            headers["API-Key"] = self.urlscan_key

        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(
                    "https://urlscan.io/api/v1/search/",
                    params={"q": f'page.url:"{url}"'},
                    headers=headers,
                )
                if resp.status_code >= 400:
                    return []
                data = resp.json()
        except Exception:
            return []

        results = (data or {}).get("results") or []
        if not results:
            _cache_set(cache_key, [])
            return []

        first = results[0] or {}
        overall = ((first.get("verdicts") or {}).get("overall") or {})
        malicious = bool(overall.get("malicious"))
        score = overall.get("score")

        out: List[dict] = []
        if malicious:
            out.append({
                "source": "urlscan.io",
                "signal": "historical_malicious_scan",
                "value": score,
                "severity": "high",
                "explanation": "urlscan.io historical scan data marked this URL as malicious.",
            })
        else:
            out.append({
                "source": "urlscan.io",
                "signal": "historical_scan_found",
                "value": len(results),
                "severity": "low",
                "explanation": "This URL/domain has prior scan history on urlscan.io.",
            })

        _cache_set(cache_key, out)
        return out

    async def _domain_age(self, domain: str) -> List[dict]:
        if whois is None:
            return []

        cache_key = f"whois:{domain}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            record = await asyncio.wait_for(asyncio.to_thread(whois.whois, domain), timeout=4.0)
        except Exception:
            return []

        created_at = _parse_creation_date(getattr(record, "creation_date", None))
        if not created_at:
            return []

        age_days = max(0, int((datetime.now(timezone.utc) - created_at.astimezone(timezone.utc)).days))
        out: List[dict] = []

        if age_days <= 30:
            out.append({
                "source": "WHOIS/RDAP",
                "signal": "new_domain",
                "value": age_days,
                "severity": "high",
                "explanation": f"Domain appears very new ({age_days} days old).",
            })
        elif age_days <= 180:
            out.append({
                "source": "WHOIS/RDAP",
                "signal": "young_domain",
                "value": age_days,
                "severity": "medium",
                "explanation": f"Domain is relatively new ({age_days} days old).",
            })

        _cache_set(cache_key, out)
        return out

    async def _abuseipdb(self, domain: str) -> List[dict]:
        if not self.abuseipdb_key:
            return []

        try:
            ip = await asyncio.wait_for(asyncio.to_thread(socket.gethostbyname, domain), timeout=2.5)
        except Exception:
            return []

        cache_key = f"abuse:{ip}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(
                    "https://api.abuseipdb.com/api/v2/check",
                    params={"ipAddress": ip, "maxAgeInDays": 90},
                    headers={"Key": self.abuseipdb_key, "Accept": "application/json"},
                )
                if resp.status_code >= 400:
                    return []
                data = resp.json()
        except Exception:
            return []

        payload = (data or {}).get("data") or {}
        score = int(payload.get("abuseConfidenceScore", 0) or 0)
        reports = int(payload.get("totalReports", 0) or 0)

        out: List[dict] = []
        if score >= 60:
            out.append({
                "source": "AbuseIPDB",
                "signal": "high_abuse_confidence",
                "value": score,
                "severity": "high",
                "explanation": f"Resolved IP has high abuse confidence ({score}) with {reports} reports.",
            })
        elif score >= 20:
            out.append({
                "source": "AbuseIPDB",
                "signal": "moderate_abuse_confidence",
                "value": score,
                "severity": "medium",
                "explanation": f"Resolved IP has moderate abuse confidence ({score}).",
            })

        _cache_set(cache_key, out)
        return out

    async def _http_probe(self, url: str) -> List[dict]:
        """Proactively probe the URL for phishing kit signatures or suspicious redirects."""
        cache_key = f"http:{url}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
                resp = await client.head(url)
                
                out: List[dict] = []
                # Check for suspicious redirection
                if len(resp.history) > 1:
                    out.append({
                        "source": "Janus HTTP Probe",
                        "signal": "redirect_chain",
                        "value": len(resp.history),
                        "severity": "medium",
                        "explanation": f"URL redirected {len(resp.history)} times, common in phishing camouflage.",
                    })
                
                # Heuristic: Scammers often use specific server headers
                server = resp.headers.get("server", "").lower()
                if not server or "unknown" in server:
                    out.append({
                        "source": "Janus Infrastructure Scan",
                        "signal": "hidden_server_identity",
                        "value": "unknown",
                        "severity": "low",
                        "explanation": "Hosting server is hiding its identity, a common tactic in ephemeral phishing sites.",
                    })
                
                return out
        except Exception:
            return []

    async def _dns_details(self, domain: str) -> List[dict]:
        """Check for DNS anomalies like suspicious TLDs."""
        cache_key = f"dns:{domain}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        out: List[dict] = []
        try:
            # Check for suspicious TLDs favored by scammers
            suspicious_tld = [".xyz", ".top", ".buzz", ".live", ".work", ".link", ".verify", ".secure-login", ".tk"]
            tld = domain.split(".")[-1].lower()
            if f".{tld}" in suspicious_tld:
                out.append({
                    "source": "Janus Infrastructure Scan",
                    "signal": "suspicious_tld",
                    "value": f".{tld}",
                    "severity": "medium",
                    "explanation": f"Domain uses a high-risk TLD (.{tld}) often associated with malicious campaigns.",
                })

            return out
        except Exception:
            return []


live_intel_service = LiveIntelService()
