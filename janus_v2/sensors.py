"""sensors.py — live sensor grid: the world's data at Janus's fingertips, keyless.

Feeds: Open-Meteo weather + air quality, USGS earthquakes (live seismic),
ISS orbital position, BBC/NASA RSS headlines. Every reading is normalized,
receipt-logged by tools.py, and stored only as gated untrusted facts —
sensors propose, verification disposes. No API keys anywhere.
"""
from __future__ import annotations


def _get_json(url: str):
    import httpx
    r = httpx.get(url, timeout=20, follow_redirects=True,
                  headers={"User-Agent": "Mozilla/5.0 JanusV2/1.0"})
    r.raise_for_status()
    return r.json()


def weather(lat: float = 13.0, lon: float = 77.6) -> dict:
    """Open-Meteo current conditions (Bengaluru default)."""
    d = _get_json(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                  "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code")
    c = d["current"]
    return {"sensor": "weather", "lat": lat, "lon": lon, "temp_c": c["temperature_2m"],
            "humidity": c["relative_humidity_2m"], "wind_kmh": c["wind_speed_10m"],
            "time": c["time"]}


def air_quality(lat: float = 13.0, lon: float = 77.6) -> dict:
    d = _get_json(f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}"
                  f"&longitude={lon}&current=pm2_5,pm10,us_aqi")
    c = d["current"]
    return {"sensor": "air_quality", "pm2_5": c.get("pm2_5"), "pm10": c.get("pm10"),
            "us_aqi": c.get("us_aqi"), "time": c.get("time")}


def earthquakes(min_magnitude: float = 4.5, limit: int = 8) -> list[dict]:
    """USGS live seismic feed (past day, magnitude >= threshold)."""
    d = _get_json("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/"
                  "4.5_day.geojson")
    out = []
    for f in d.get("features", [])[:limit]:
        p = f["properties"]
        if p.get("mag", 0) >= min_magnitude:
            out.append({"sensor": "earthquake", "mag": p["mag"], "place": p.get("place"),
                        "time": p.get("time"), "url": p.get("url")})
    return out


def iss_position() -> dict:
    d = _get_json("http://api.open-notify.org/iss-now.json")
    p = d["iss_position"]
    return {"sensor": "iss", "lat": float(p["latitude"]), "lon": float(p["longitude"]),
            "timestamp": d.get("timestamp")}


def headlines(feed: str = "https://feeds.bbci.co.uk/news/world/rss.xml", limit: int = 8) -> list[dict]:
    from janus_v2 import crawlers
    out = crawlers.crawl_feed(feed, limit)
    return [{"sensor": "news", "title": it["title"], "url": it["link"]} for it in out["items"]]


def snapshot() -> dict:
    """One live snapshot across the grid; per-sensor failures reported, not hidden."""
    out, errors = {}, {}
    for name, fn in (("weather", weather), ("air_quality", air_quality),
                     ("earthquakes", earthquakes), ("iss", iss_position),
                     ("headlines", headlines)):
        try:
            out[name] = fn()
        except Exception as e:
            errors[name] = str(e)[:100]
    return {"live": out, "errors": errors}


SENSORS = {"weather": weather, "air_quality": air_quality, "earthquakes": earthquakes,
           "iss": iss_position, "headlines": headlines}
