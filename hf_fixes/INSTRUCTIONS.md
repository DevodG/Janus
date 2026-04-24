# Janus — HF Spaces Fix Instructions

## The core problem: HF Spaces ≠ localhost

Your backend lives at `https://devodg-janus.hf.space` (or similar).
This means:
- No `.env` files — use **Space Secrets** in Settings
- Port is **7860**, not 8000
- Filesystem **resets** on every sleep/restart (all `data/*.json` lost)
- No `pkill`, no shell scripts, no local filesystem scripts
- Frontend (Next.js) is a **separate Space** with a different origin → CORS matters

---

## Step 1 — Add Secrets to your HF Space

Go to your Space → **Settings** → **Repository secrets** → Add each:

```
PRIMARY_PROVIDER          = openrouter
OPENROUTER_API_KEY        = sk-or-v1-YOUR_KEY

GROQ_API_KEY              = gsk_YOUR_KEY
GEMINI_API_KEY            = YOUR_KEY

TAVILY_API_KEY            = tvly-dev-YOUR_KEY
NEWSAPI_KEY               = YOUR_KEY

FINNHUB_API_KEY           = d7c3h31r01quh9fcd7vgd7c3h31r01quh9fcd800
FMP_API_KEY               = hCaGfRXZvNuzoVZUtwjFYfrQX9EbfiS8
EODHD_API_KEY             = 69d7d692628e55.48198547

# For persistent memory across restarts:
HF_TOKEN                  = hf_YOUR_TOKEN    (your HF write token)
HF_STORE_REPO             = DevodG/janus-memory

# Feature flags — keep experimental stuff OFF until core works:
SIMULATION_ENABLED        = true
SENTINEL_ENABLED          = true
LEARNING_ENABLED          = false
ADAPTIVE_INTELLIGENCE_ENABLED = false
CONTINUOUS_TRAINING_ENABLED   = false
CURIOSITY_ENGINE_ENABLED      = false
AUTONOMOUS_LEARNER_ENABLED    = false
MIROFISH_COMPAT_MODE          = false

# CORS — add your frontend Space URL:
ALLOWED_ORIGINS           = https://devodg-janus-frontend.hf.space,http://localhost:3000
CORS_ALLOW_ALL            = false
```

> If you don't know your frontend Space URL yet, set `CORS_ALLOW_ALL = true` temporarily.

---

## Step 2 — Copy the patched files into your repo

```bash
# Clone your repo locally
git clone https://github.com/DevodG/Janus.git
cd Janus

# Copy patched files (from the hf_fixes package)
cp hf_fixes/backend_patches/main.py         backend/app/main.py
cp hf_fixes/backend_patches/smart_router.py backend/app/agents/smart_router.py
cp hf_fixes/new_services/persistent_store.py backend/app/services/persistent_store.py
cp hf_fixes/new_services/response_cache.py  backend/app/services/response_cache.py
cp hf_fixes/new_services/memory_manager.py  backend/app/services/memory_manager.py
cp hf_fixes/new_services/skill_executor.py  backend/app/services/skill_executor.py
cp hf_fixes/root_files/requirements.txt     backend/requirements.txt
cp hf_fixes/new_files/LineChart.tsx         frontend/src/components/LineChart.tsx

# Apply market_data patch (adds yfinance + fallback chain)
python3 hf_fixes/apply_market_data_patch.py backend/app
```

---

## Step 3 — Apply market_data patch manually

Open `backend/app/domain_packs/finance/market_data.py` and:

**At the top, add `import os`** if not present.

**Replace or add `get_historical_data`:**

```python
def get_historical_data(symbol: str, outputsize: str = "compact") -> list:
    """Waterfall: yfinance → AlphaVantage → Finnhub → FMP → EODHD"""
    days = 100 if outputsize == "compact" else 730
    return (
        _hist_yfinance(symbol, days)
        or _hist_alphavantage(symbol, outputsize)
        or _hist_finnhub(symbol, days)
        or _hist_fmp(symbol, days)
        or []
    )

def _hist_yfinance(symbol: str, days: int) -> list:
    try:
        import yfinance as yf
        from datetime import datetime, timedelta
        # Translate exchange suffixes: RELIANCE.BSE → RELIANCE.BO
        s = symbol.upper()
        if s.endswith(".BSE"): s = s[:-4] + ".BO"
        if s.endswith(".NSE"): s = s[:-4] + ".NS"
        end   = datetime.utcnow()
        start = end - timedelta(days=days)
        df = yf.Ticker(s).history(
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval="1d", auto_adjust=True
        )
        if df.empty: return []
        out = []
        for idx, row in df.iterrows():
            out.append({
                "date":   idx.strftime("%Y-%m-%d"),
                "open":   round(float(row["Open"]),  4),
                "high":   round(float(row["High"]),  4),
                "low":    round(float(row["Low"]),   4),
                "close":  round(float(row["Close"]), 4),
                "volume": int(row.get("Volume", 0)),
            })
        out.sort(key=lambda x: x["date"])
        logger.info("yfinance: %d points for %s", len(out), symbol)
        return out
    except Exception as e:
        logger.warning("yfinance failed for %s: %s", symbol, e)
        return []

def _hist_alphavantage(symbol: str, outputsize: str) -> list:
    if not ALPHAVANTAGE_API_KEY: return []
    try:
        with httpx.Client(timeout=20) as c:
            r = c.get("https://www.alphavantage.co/query", params={
                "function": "TIME_SERIES_DAILY", "symbol": symbol.upper(),
                "outputsize": outputsize, "apikey": ALPHAVANTAGE_API_KEY,
            })
        data = r.json()
        if "Information" in data or "Note" in data: return []
        series = data.get("Time Series (Daily)", {})
        if not series: return []
        out = [{"date": d, "open": float(v["1. open"]), "high": float(v["2. high"]),
                "low": float(v["3. low"]), "close": float(v["4. close"]),
                "volume": int(v["5. volume"])} for d, v in series.items()]
        out.sort(key=lambda x: x["date"])
        return out
    except Exception as e:
        logger.warning("AlphaVantage failed: %s", e)
        return []

def _hist_finnhub(symbol: str, days: int) -> list:
    key = os.getenv("FINNHUB_API_KEY", "")
    if not key: return []
    try:
        import time as t
        from datetime import datetime as dt
        end = int(t.time()); start = end - days * 86400
        with httpx.Client(timeout=15) as c:
            r = c.get("https://finnhub.io/api/v1/stock/candle",
                params={"symbol": symbol.upper(), "resolution": "D",
                        "from": start, "to": end, "token": key})
        data = r.json()
        if data.get("s") != "ok": return []
        out = [{"date": dt.utcfromtimestamp(ts).strftime("%Y-%m-%d"),
                "open": data["o"][i], "high": data["h"][i], "low": data["l"][i],
                "close": data["c"][i], "volume": int(data["v"][i])}
               for i, ts in enumerate(data.get("t", []))]
        return out
    except Exception as e:
        logger.warning("Finnhub failed: %s", e)
        return []

def _hist_fmp(symbol: str, days: int) -> list:
    key = os.getenv("FMP_API_KEY", "")
    if not key: return []
    try:
        from datetime import datetime as dt, timedelta
        end   = dt.utcnow().strftime("%Y-%m-%d")
        start = (dt.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        with httpx.Client(timeout=15) as c:
            r = c.get(f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol.upper()}",
                      params={"from": start, "to": end, "apikey": key})
        history = r.json().get("historical", [])
        out = [{"date": row["date"], "open": float(row["open"]), "high": float(row["high"]),
                "low": float(row["low"]), "close": float(row["close"]),
                "volume": int(row.get("volume", 0))} for row in history]
        out.sort(key=lambda x: x["date"])
        return out
    except Exception as e:
        logger.warning("FMP failed: %s", e)
        return []
```

---

## Step 4 — Fix GNews for Indian stocks

In `backend/app/domain_packs/finance/news.py`, find where it builds the `q` param for GNews/NewsAPI and change:

```python
# BEFORE (breaks for RELIANCE.BSE — returns 400):
"q": symbol

# AFTER:
"q": _news_query(symbol, company_name)
```

Add this function:

```python
def _news_query(symbol: str, company_name: str = "") -> str:
    """Strip exchange suffix so news APIs can find the company."""
    if company_name and len(company_name) > 3:
        return company_name
    s = symbol.upper()
    for suffix in [".BSE", ".NSE", ".BO", ".NS", ".L", ".TO"]:
        if s.endswith(suffix):
            return s[: -len(suffix)]
    return s
```

---

## Step 5 — Fix the import in finance.py router

In `backend/app/routers/finance.py`, the import line should be:

```python
from app.domain_packs.finance.market_data import (
    get_quote,
    get_company_overview,
    search_symbol,
    get_historical_data,   # ← ADD THIS
)
```

---

## Step 6 — Update frontend API base URL

In your frontend Space, set the env var:

```
NEXT_PUBLIC_API_URL = https://devodg-janus.hf.space
```

(Replace `devodg-janus` with your actual backend Space name.)

In `frontend/src/lib/api.ts`, make sure the base URL uses this env var:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
```

---

## Step 7 — Commit and push

```bash
git add -A
git commit -m "fix: HF Spaces compatibility - port, CORS, yfinance, LLM providers"
git push origin main
```

HF Spaces will automatically rebuild on push.

---

## Step 8 — Verify the deployment

```bash
# Replace with your actual Space URL
SPACE=https://devodg-janus.hf.space

# Health check
curl $SPACE/health

# Deep health (shows which API keys are active)
curl $SPACE/health/deep

# Historical data (should work via yfinance, no key needed)
curl "$SPACE/finance/historical/AAPL?outputsize=compact" | python3 -m json.tool | head -20

# Test LLM (will fail if no keys set in Secrets)
curl -X POST $SPACE/run \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the S&P 500?"}'
```

---

## Persistent memory setup (prevent data loss on restart)

1. Go to `https://huggingface.co/new-dataset`
2. Name it `janus-memory`, set to **Private**
3. Add to Space Secrets:
   ```
   HF_TOKEN       = hf_YOUR_WRITE_TOKEN
   HF_STORE_REPO  = DevodG/janus-memory
   ```

After this, all cases, skills, and learned patterns survive Space restarts.

---

## What each file does

| File | Purpose |
|------|---------|
| `backend/app/main.py` | Port 7860, correct CORS, singleton daemon, HF-aware startup logging |
| `backend/app/agents/smart_router.py` | Fixed model IDs, fixed Gemini parsing, retry logic |
| `backend/app/services/persistent_store.py` | HF Datasets backend for persistent memory |
| `backend/app/services/response_cache.py` | TTL cache — prevents AlphaVantage rate limit hammering |
| `backend/app/services/memory_manager.py` | TF-IDF case index — fast similarity search, deduplication |
| `backend/app/services/skill_executor.py` | Auto-distil reusable skills from repeated queries |
| `backend/requirements.txt` | Adds yfinance, pins versions to prevent rebuild breaks |
| `frontend/src/components/LineChart.tsx` | Real chart with yfinance data + timeframe switching |

---

## Common HF Spaces errors and fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `Application startup failed` | Import error in main.py | Check Space logs, look for `ImportError` |
| `HTTP 405 HEAD /health` | Health check uses HEAD method | Fixed in new main.py |
| `CORS error` in browser | Frontend origin not in ALLOWED_ORIGINS | Add frontend Space URL to ALLOWED_ORIGINS secret |
| All LLM calls fail | API keys not in Secrets | Add keys in Space Settings → Secrets |
| Historical data always empty | Only AlphaVantage configured (25/day limit) | yfinance requires no key — should work by default after requirements.txt update |
| Memory lost on restart | No HF_STORE_REPO set | Create private dataset repo, add HF_TOKEN + HF_STORE_REPO secrets |
| Space sleeping kills background tasks | HF free tier sleeps after 48h | Expected — daemon restarts automatically when Space wakes |
