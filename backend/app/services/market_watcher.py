"""
Market Watcher — Background daemon service for Janus.
Polls Alpha Vantage for watchlist tickers, detects anomalies, stores signals.
"""

import os
import json
import time
import logging
import httpx
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from app.config import DATA_DIR as BASE_DATA_DIR
except ImportError:
    BASE_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DATA_DIR = Path(BASE_DATA_DIR) / "daemon"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class MarketWatcher:
    def __init__(self, watchlist: List[str] = None):
        self.api_key = os.getenv("ALPHAVANTAGE_API_KEY", "")
        self.watchlist = watchlist or [
            "AAPL",
            "MSFT",
            "NVDA",
            "AMZN",
            "GOOGL",
            "META",
            "TSLA",
            "TSM",
            "ASML",
            "JPM",
            "XOM",
            "SPY",
            "QQQ",
            "DIA",
            "IWM",
            "EEM",
            "FXI",
            "EWJ",
            "INDA",
            "EWG",
        ]
        self.price_history: Dict[str, List[Dict]] = {}
        self._load_history()

    def _load_history(self):
        """Load price history from disk."""
        history_file = DATA_DIR / "market_history.json"
        if history_file.exists():
            try:
                with open(history_file) as f:
                    self.price_history = json.load(f)
            except:
                self.price_history = {}

    def _save_history(self):
        """Save price history to disk."""
        history_file = DATA_DIR / "market_history.json"
        with open(history_file, "w") as f:
            json.dump(self.price_history, f, indent=2)

    def poll(self) -> List[Dict]:
        """Poll all watchlist tickers. Returns list of signals."""
        if not self.api_key:
            logger.warning("[MARKET] No Alpha Vantage API key")
            return []

        signals = []
        for symbol in self.watchlist:
            try:
                quote = self._fetch_quote(symbol)
                if quote:
                    signal = self._analyze_quote(symbol, quote)
                    if signal:
                        signals.append(signal)
                    self._record_price(symbol, quote)
            except Exception as e:
                logger.error(f"[MARKET] Error fetching {symbol}: {e}")

        if signals:
            logger.info(f"[MARKET] Generated {len(signals)} signals")

        return signals

    def _fetch_quote(self, symbol: str) -> Optional[Dict]:
        """Fetch current quote from Alpha Vantage."""
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={self.api_key}"
        r = httpx.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("Global Quote")

    def _analyze_quote(self, symbol: str, quote: Dict) -> Optional[Dict]:
        """Analyze quote for anomalies. Returns signal if found."""
        price = quote.get("05. price", "")
        change = quote.get("09. change", "")
        change_pct = quote.get("10. change percent", "")
        volume = quote.get("06. volume", "")

        if not price or not change_pct:
            return None

        try:
            price_val = float(price)
            change_pct_val = float(change_pct.replace("%", ""))
            volume_val = int(volume) if volume else 0
        except:
            return None

        signals = []
        severity = "low"

        # Price movement detection
        if abs(change_pct_val) > 5:
            signals.append(f"Major price movement: {change_pct}")
            severity = "high"
        elif abs(change_pct_val) > 3:
            signals.append(f"Significant price movement: {change_pct}")
            severity = "medium"
        elif abs(change_pct_val) > 1:
            signals.append(f"Price movement: {change_pct}")
            severity = "low"

        # Volume spike detection (compare to average)
        history = self.price_history.get(symbol, [])
        if history:
            avg_volume = sum(h.get("volume", 0) for h in history[-20:]) / min(
                len(history), 20
            )
            if avg_volume > 0 and volume_val > avg_volume * 2:
                signals.append(f"Volume spike: {volume_val} (avg: {avg_volume:.0f})")
                severity = "medium" if severity == "low" else severity

        if not signals:
            return None

        signal = {
            "type": "market",
            "symbol": symbol,
            "price": price_val,
            "change_pct": change_pct_val,
            "volume": volume_val,
            "signals": signals,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(f"[MARKET] {symbol}: {', '.join(signals)}")
        return signal

    def _record_price(self, symbol: str, quote: Dict):
        """Record price to history."""
        try:
            price = float(quote.get("05. price", 0))
            volume = int(quote.get("06. volume", 0))
        except:
            return

        if symbol not in self.price_history:
            self.price_history[symbol] = []

        self.price_history[symbol].append(
            {
                "price": price,
                "volume": volume,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Keep last 100 entries per symbol
        self.price_history[symbol] = self.price_history[symbol][-100:]
        self._save_history()

    def get_watchlist_status(self) -> List[Dict]:
        """Get current status of all watchlist tickers."""
        status = []
        for symbol in self.watchlist:
            history = self.price_history.get(symbol, [])
            if history:
                latest = history[-1]
                status.append(
                    {
                        "symbol": symbol,
                        "price": latest.get("price"),
                        "timestamp": latest.get("timestamp"),
                        "data_points": len(history),
                    }
                )
            else:
                status.append(
                    {
                        "symbol": symbol,
                        "price": None,
                        "timestamp": None,
                        "data_points": 0,
                    }
                )
        return status
