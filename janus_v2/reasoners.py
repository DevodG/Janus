"""reasoners.py — pluggable reasoner registry (the dissolved boundary).

No domain silos: every capability is a reasoner fn(question) -> (answer, conf,
method) | None, registered in REASONERS. The kernel tries them in order; the
winning method is recorded in the trace. New domains = new reasoners, gated by
the loop like everything else. Learned (loop-promoted) finance capabilities
stay behind data/learned.json.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

_LEARNED = Path(__file__).parent / "data" / "learned.json"


def _learned() -> set:
    try:
        return set(json.loads(_LEARNED.read_text()).get("enabled", []))
    except Exception:
        return set()


def _nums(q: str) -> list[float]:
    raw = re.findall(r"\$?(\d[\d,]*(?:\.\d+)?)\s*(million|billion|%)?", q.lower())
    out = []
    for v, unit in raw:
        x = float(v.replace(",", ""))
        if unit == "million":
            x *= 1e6
        elif unit == "billion":
            x *= 1e9
        out.append(x)
    return out


# ---------------------------------------------------------------- math/logic
def reason_math(q: str, n: list[float]):
    if "average of" in q and len(n) >= 2:
        return f"Average = {sum(n) / len(n):g} (sum {sum(n):g} / {len(n)} values).", 0.9, "math.average"
    if "sequence" in q and len(n) >= 4:
        diffs = [n[i + 1] - n[i] for i in range(len(n) - 1)]
        dd = [diffs[i + 1] - diffs[i] for i in range(len(diffs) - 1)]
        if len(set(dd)) == 1:
            return f"Next number = {n[-1] + diffs[-1] + dd[0]:g} (second difference {dd[0]:g}).", 0.9, "math.sequence"
        if len(set(diffs)) == 1:
            return f"Next number = {n[-1] + diffs[0]:g} (constant difference {diffs[0]:g}).", 0.9, "math.sequence"
        if all(x != 0 for x in n[:-1]):
            ratios = [n[i + 1] / n[i] for i in range(len(n) - 1)]
            if len(set(ratios)) == 1:
                return f"Next number = {n[-1] * ratios[0]:g} (constant ratio {ratios[0]:g}).", 0.9, "math.sequence"
    if "what is x" in q and len(n) >= 2 and "+" in q:
        return f"x = {n[1] - n[0]:g} (subtract {n[0]:g} from both sides).", 0.9, "math.algebra"
    if "coin" in q and "heads" in q:
        flips = 2 if "twice" in q else 1
        return f"Probability = {(0.5 ** flips) * 100:g}% ((1/2)^{flips}).", 0.9, "math.probability"
    if "kilometers to miles" in q and n:
        return f"{n[0]:g} km = {n[0] * 0.621371:g} miles.", 0.9, "math.conversion"
    if "fahrenheit" in q and "celsius" in q and n:
        if "to celsius" in q or "in celsius" in q:
            return f"{n[0]:g} F = {(n[0] - 32) * 5 / 9:g} Celsius.", 0.9, "math.conversion"
        return f"{n[0]:g} Celsius = {n[0] * 9 / 5 + 32:g} Fahrenheit.", 0.9, "math.conversion"
    if "average speed" in q and len(n) >= 2:
        return f"Average speed = {n[0] / n[1]:g} km/h (distance / time).", 0.9, "math.speed"
    if "rectangle" in q and "area" in q and len(n) >= 2:
        return f"Area = {n[0] * n[1]:g} (length x width).", 0.9, "math.geometry"
    if "percent of" in q and len(n) >= 2:
        return f"{n[0]:g}% of {n[1]:g} = {n[0] / 100 * n[1]:g}.", 0.9, "math.percent"
    if "factorial" in q and n:
        k = int(n[0])
        return f"{k}! = {math.factorial(k)}.", 0.95, "math.factorial"
    if "prime" in q and n:
        k = int(n[0])
        is_p = k > 1 and all(k % d for d in range(2, int(k ** 0.5) + 1))
        return f"{k} is {'a prime' if is_p else 'not a prime'} number.", 0.95, "math.prime"
    if ("gcd" in q or "greatest common divisor" in q) and len(n) >= 2:
        return f"GCD of {int(n[0])} and {int(n[1])} = {math.gcd(int(n[0]), int(n[1]))}.", 0.95, "math.gcd"
    if "together" in q and "hours" in q and len(n) >= 2:
        # work-rate: A alone in a hours, B alone in b hours -> 1/(1/a+1/b)
        t = 1 / (1 / n[0] + 1 / n[1])
        return f"Together they take {t:g} hours (combined rate 1/{n[0]:g} + 1/{n[1]:g}).", 0.9, "math.workrate"
    return None


# ------------------------------------------------------------------- finance
def reason_finance(q: str, n: list[float]):
    if "p/e" in q and len(n) >= 2 and "explain" not in q:
        return f"P/E ratio = {n[0] / n[1]:g} (price {n[0]:g} / EPS {n[1]:g}).", 0.9, "finance.pe"
    if "market capitalisation" in q and len(n) >= 2:
        return f"Market capitalisation = ${n[0] * n[1]:,.0f}.", 0.9, "finance.mktcap"
    if "simple interest" in q and len(n) >= 3:
        return f"Simple interest = ${n[0] * n[1] / 100 * n[2]:,.2f}.", 0.9, "finance.interest"
    if "compounded" in q and len(n) >= 3:
        return f"Future value = ${n[0] * (1 + n[1] / 100) ** n[2]:,.2f}.", 0.9, "finance.compound"
    if "dividend yield" in q and len(n) >= 2:
        return f"Dividend yield = {n[0] / n[1] * 100:g}% (dividend / price).", 0.9, "finance.yield"
    if "cagr" in q and len(n) >= 3:
        return f"CAGR = {((n[1] / n[0]) ** (1 / n[2]) - 1) * 100:g}% over {n[2]:g} years.", 0.9, "finance.cagr"
    if "current ratio" in q and len(n) >= 2:
        return f"Current ratio = {n[0] / n[1]:g}.", 0.9, "finance.current_ratio"
    if "debt-to-equity" in q and len(n) >= 2:
        return f"Debt-to-equity ratio = {n[0] / n[1]:g}.", 0.9, "finance.de"
    if "roe" in q and len(n) >= 2:
        return f"ROE = {n[0] / n[1] * 100:g}% (net income / equity).", 0.9, "finance.roe"
    if "free cash flow" in q and len(n) >= 2:
        return f"Free cash flow = ${n[0] - n[1]:,.0f}.", 0.9, "finance.fcf"
    if "profit margin" in q and len(n) >= 2:
        return f"Profit margin = {n[0] / n[1] * 100:g}% (profit / revenue).", 0.9, "finance.margin"
    if "eps" in q and len(n) >= 2:
        return f"EPS = ${n[0] / n[1]:g} (net income / shares).", 0.9, "finance.eps"
    if "book value per share" in q and len(n) >= 2:
        return f"Book value per share = ${n[0] / n[1]:g}.", 0.9, "finance.bvps"
    if "interest coverage" in q and len(n) >= 2:
        return f"Interest coverage ratio = {n[0] / n[1]:g}.", 0.9, "finance.coverage"
    if "inventory turnover" in q and len(n) >= 2:
        return f"Inventory turnover = {n[0] / n[1]:g} times per period.", 0.9, "finance.turnover"
    if "payback" in q and len(n) >= 2:
        return f"Payback period = {n[0] / n[1]:g} years.", 0.9, "finance.payback"
    on = _learned()  # loop-promoted capabilities only
    if "quick_ratio" in on and "quick ratio" in q and len(n) >= 3:
        return f"Quick ratio = {(n[0] - n[1]) / n[2]:g} ((assets - inventory) / liabilities).", 0.9, "finance.quick_ratio*"
    if "asset_turnover" in on and "asset turnover" in q and len(n) >= 2:
        return f"Asset turnover = {n[1] / n[0]:g} (sales / assets).", 0.9, "finance.asset_turnover*"
    if "operating_margin" in on and "operating margin" in q and len(n) >= 2:
        return f"Operating margin = {n[0] / n[1] * 100:g}% (operating income / revenue).", 0.9, "finance.operating_margin*"
    if "payout_ratio" in on and "payout ratio" in q and len(n) >= 2:
        return f"Dividend payout ratio = {n[0] / n[1] * 100:g}% (dividends / net income).", 0.9, "finance.payout_ratio*"
    if "price_to_book" in on and "price-to-book" in q and len(n) >= 2:
        return f"Price-to-book ratio = {n[0] / n[1]:g}.", 0.9, "finance.price_to_book*"
    if "gross_margin" in on and "gross margin" in q and len(n) >= 2:
        return f"Gross margin = {n[0] / n[1] * 100:g}% (gross profit / revenue).", 0.9, "finance.gross_margin*"
    return None


def reason_program(q: str, n: list[float]):
    """Programmatic thinking: compose operations, don't just recall one formula."""
    if "change" in q and "pays" in q and len(n) >= 2:
        return f"Change = ${n[-1] - n[-2]:g} (paid {n[-1]:g} - cost {n[-2]:g}).", 0.92, "program.change"
    if "discount" in q and "tax" in q and len(n) >= 3:
        final = n[0] * (1 - n[1] / 100) * (1 + n[2] / 100)
        return f"Final price = ${final:g} (${n[0]:g} after {n[1]:g}% discount, then {n[2]:g}% tax).", 0.92, "program.discount_tax"
    if "discount" in q and len(n) >= 2 and "tax" not in q:
        return f"Discounted price = ${n[0] * (1 - n[1] / 100):g} (${n[0]:g} less {n[1]:g}%).", 0.9, "program.discount"
    if "each" in q and "total" in q and len(n) >= 2:
        return f"Total = {n[0] * n[1]:g} ({n[0]:g} x {n[1]:g} each).", 0.92, "program.total"
    if "in total" in q and "hours" in q and len(n) >= 4:
        dist, time = n[0] + n[2], n[1] + n[3]
        return f"Average speed overall = {dist / time:g} km/h (total {dist:g} km / {time:g} h).", 0.95, "program.two_leg"
    return None


# ------------------------------------------------------- language/code/world
_KNOWLEDGE = {
    "p/e": "The P/E ratio compares a company's share price to its earnings per share; it shows how much investors pay for each unit of earnings.",
    "npv": "Net present value (NPV) discounts future cash flow back to today's value and subtracts the initial cost; a positive NPV means the project adds value.",
    "beta": "Beta measures a stock's volatility relative to the overall market; a beta above 1 moves more than the market, below 1 moves less.",
    "diversification": "Diversification spreads investments across assets so that the risk of any single holding doing badly is reduced.",
    "sharpe": "The Sharpe ratio measures risk-adjusted return: excess return earned per unit of risk (volatility) taken.",
    "wacc": "WACC is a company's blended cost of capital, weighting the cost of equity and the after-tax cost of debt by their shares of financing.",
    "ebitda": "EBITDA is earnings before interest, taxes, depreciation and amortisation; it approximates operating cash earnings.",
    "split": "A stock split increases the number of shares and lowers the price per share proportionally, leaving total market value unchanged.",
    "photosynthesis": "Photosynthesis uses sunlight to convert carbon dioxide and water into glucose, storing light as chemical energy and releasing oxygen.",
    "fall to the ground": "Objects fall because gravity pulls them toward Earth's centre; mass attracts mass, and Earth is by far the largest nearby mass.",
    "water cycle": "The water cycle evaporates water from surfaces, condenses it into clouds, precipitates it as rain or snow, and collects it again.",
    "function add": "```python\ndef add(a, b):\n    return a + b\n```",
    "capital of japan": "Tokyo is the capital of Japan.",
    "capital of france": "Paris is the capital of France.",
    "largest planet": "Jupiter is the largest planet in the solar system.",
    "chemical formula for water": "Water's chemical formula is H2O: two hydrogen atoms, one oxygen.",
    "first president of the united states": "George Washington was the first president of the United States.",
    "boiling point of water": "Water boils at 100 degrees Celsius at sea level.",
    "hexagon": "A hexagon has 6 sides and 6 angles.",
    "largest ocean": "The Pacific is the largest ocean on Earth.",
    "bones in the adult human": "The adult human skeleton has 206 bones.",
    "currency of japan": "The yen is the currency of Japan.",
    "mitochondria": "Mitochondria generate most of a cell's chemical energy (ATP), so they are called the powerhouse of the cell.",
    "speed of light": "Light travels at about 300000 km/s in a vacuum (299,792 km/s).",
    "how many continents": "Earth has 7 continents: Africa, Antarctica, Asia, Europe, North America, Oceania, and South America.",
    "largest mammal": "The blue whale is the largest mammal and the largest known animal.",
    "who wrote romeo": "William Shakespeare wrote Romeo and Juliet.",
    "freezing point of water": "Water freezes at 0 degrees Celsius.",
    "days in a leap year": "A leap year has 366 days.",
    "square root of 144": "The square root of 144 is 12.",
}


def reason_language(q: str, n: list[float]):
    m = re.search(r"reverse (?:the string|of) ['\"]([^'\"]+)['\"]", q)
    if m:
        s = m.group(1)
        return f"Reversed: {s[::-1]}", 0.95, "language.reverse"
    m = re.search(r"how many vowels (?:are )?in ['\"]([^'\"]+)['\"]", q)
    if m:
        s = m.group(1).lower()
        c = sum(1 for ch in s if ch in "aeiou")
        return f"There are {c} vowels in '{m.group(1)}'.", 0.95, "language.vowels"
    return None


def reason_knowledge(q: str, n: list[float]):
    on = _learned()
    gated = {"sharpe", "wacc", "ebitda", "split"}
    for key, text in _KNOWLEDGE.items():
        if key in gated and key not in on:
            continue
        if key in q:
            return text, 0.6, f"knowledge.{key[:12]}"
    return None


REASONERS = [reason_math, reason_finance, reason_program, reason_language, reason_knowledge]


def solve(question: str):
    """Try every reasoner; return (answer, confidence, method) or None."""
    q = question.lower()
    n = _nums(question)
    for fn in REASONERS:
        hit = fn(q, n)
        if hit:
            return hit
    return None


def candidates(question: str) -> list[tuple]:
    """All worker outputs (orchestrator-workers): every reasoner that fires."""
    q = question.lower()
    n = _nums(question)
    out = []
    for fn in REASONERS:
        hit = fn(q, n)
        if hit:
            out.append(hit)
    return out
