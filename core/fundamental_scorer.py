"""
core/fundamental_scorer.py — Unified Fundamental Quality Score for NSE stocks.

Single 0–10 score combining:
  • Level checks  — is the business good RIGHT NOW?
  • Trend checks  — is it getting BETTER or WORSE? (Piotroski-style YoY deltas)

Both lenses together answer the question Gautam Baid asks:
  "Is this a quality business that is compounding its competitive advantage?"

Score breakdown (10 pts total):
  ┌─────────────────────────────────────────┬──────┬─────────┐
  │ Component                               │ Pts  │ Type    │
  ├─────────────────────────────────────────┼──────┼─────────┤
  │ ROE (sector-adjusted thresholds)        │ 0–2  │ Level   │
  │ Revenue growth > 10% YoY               │ 0–2  │ Level   │
  │ Current ratio > 1.5  (skip for banks)  │ 0–1  │ Level   │
  │ ROA improving YoY                      │ 0–1  │ Trend ✦ │
  │ CFO > Net Income  (cash quality check) │ 0–1  │ Trend ✦ │
  │ Total debt falling YoY                 │ 0–1  │ Trend ✦ │
  │ Gross margin stable or rising YoY      │ 0–1  │ Trend ✦ │
  │ No share dilution  (≤ 2% increase)     │ 0–1  │ Trend ✦ │
  └─────────────────────────────────────────┴──────┴─────────┘
  ✦ Piotroski-style signals

Tier:
  HIGH   7–10  🟢  Strong fundamentals — green light
  MEDIUM 4–6   🟡  Decent — proceed with normal conviction
  LOW    0–3   🔴  Weak — reduce position size or skip

Data source: yfinance (free, no API key needed)
Cache: data/fundamentals/<TICKER>.json — refreshed every 90 days
"""

import json
import math
import time
from datetime import datetime, timedelta
from pathlib import Path

import yfinance as yf

BASE_DIR  = Path(__file__).parent.parent
FUND_DIR  = BASE_DIR / "data" / "fundamentals"
CACHE_TTL = 90  # days before cache is considered stale


# ── Low-level helpers ─────────────────────────────────────────────────────────

def _safe_float(val, default=None):
    try:
        f = float(val)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return default


def _cache_path(ticker: str) -> Path:
    safe = ticker.replace(".", "_").replace("^", "IDX_").replace("/", "-")
    return FUND_DIR / f"{safe}.json"


def _is_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    return age < timedelta(days=CACHE_TTL)


def _row(df, *names):
    """
    Try multiple possible row labels in a yfinance DataFrame.
    Returns the matching Series, or None if not found.
    yfinance row names changed across versions — this handles both old and new.
    """
    if df is None or df.empty:
        return None
    for name in names:
        if name in df.index:
            return df.loc[name]
    return None


def _col(series, pos=0):
    """Safely get value at column position (0 = most recent year)."""
    if series is None:
        return None
    try:
        return _safe_float(series.iloc[pos])
    except (IndexError, AttributeError):
        return None


# ── Data fetcher ──────────────────────────────────────────────────────────────

def _fetch(ticker: str) -> dict:
    """
    Pull all raw fundamental data from yfinance for one ticker.
    Returns a flat dict that is JSON-serialisable and cached to disk.
    """
    try:
        t    = yf.Ticker(ticker)
        info = t.info or {}

        fin = t.financials    # income statement  (rows=metrics, cols=years newest→oldest)
        bs  = t.balance_sheet # balance sheet
        cf  = t.cashflow      # cash flow statement

        # ── Income statement rows ─────────────────────────────────────────────
        rev_s   = _row(fin, "Total Revenue",     "Revenue")
        gp_s    = _row(fin, "Gross Profit")
        ni_s    = _row(fin, "Net Income",         "Net Income Common Stockholders")

        rev_cur  = _col(rev_s,  0)
        rev_prv  = _col(rev_s,  1)
        gp_cur   = _col(gp_s,   0)
        gp_prv   = _col(gp_s,   1)
        ni_cur   = _col(ni_s,   0)
        ni_prv   = _col(ni_s,   1)

        # ── Balance sheet rows ────────────────────────────────────────────────
        assets_s = _row(bs, "Total Assets")
        debt_s   = _row(bs, "Total Debt",
                            "Long Term Debt",
                            "Long Term Debt And Capital Lease Obligation")
        shares_s = _row(bs, "Ordinary Shares Number",
                            "Share Issued",
                            "Common Stock")

        assets_cur = _col(assets_s, 0)
        assets_prv = _col(assets_s, 1)
        debt_cur   = _col(debt_s,   0)
        debt_prv   = _col(debt_s,   1)
        shares_cur = _col(shares_s, 0)
        shares_prv = _col(shares_s, 1)

        # ── Cash flow rows ────────────────────────────────────────────────────
        ocf_s = _row(cf, "Operating Cash Flow",
                         "Total Cash From Operating Activities",
                         "Cash From Operations")
        ocf_cur = _col(ocf_s, 0)

        # ── Derived ratios ────────────────────────────────────────────────────
        # Gross margin (both years for trend)
        gm_cur = (gp_cur / rev_cur) if (gp_cur and rev_cur and rev_cur != 0) else None
        gm_prv = (gp_prv / rev_prv) if (gp_prv and rev_prv and rev_prv != 0) else None

        # ROA both years (Net Income / Total Assets)
        roa_cur = (ni_cur / assets_cur) if (ni_cur and assets_cur and assets_cur != 0) else None
        roa_prv = (ni_prv and assets_prv and assets_prv != 0
                   and ni_prv / assets_prv) or None

        # Revenue growth (from statements — more reliable than info for NSE)
        rev_growth = None
        if rev_cur and rev_prv and rev_prv != 0:
            rev_growth = (rev_cur - rev_prv) / abs(rev_prv)

        # Accruals: CFO vs Net Income (Piotroski cash quality signal)
        cfo_gt_ni = None
        if ocf_cur is not None and ni_cur is not None:
            cfo_gt_ni = ocf_cur > ni_cur

        raw = {
            "source":       "yfinance",
            "fetched_at":   datetime.now().isoformat(),
            "ticker":       ticker,

            # From info (snapshot)
            "roe":          _safe_float(info.get("returnOnEquity")),
            "current_ratio":_safe_float(info.get("currentRatio")),
            "pe":           _safe_float(info.get("trailingPE")),
            "pb":           _safe_float(info.get("priceToBook")),
            "eps":          _safe_float(info.get("trailingEps")),
            "market_cap":   _safe_float(info.get("marketCap")),
            "sector":       info.get("sector",   ""),
            "industry":     info.get("industry", ""),
            "company_name": info.get("longName", info.get("shortName", "")),

            # Revenue growth (statement-derived preferred; info fallback)
            "rev_growth":   rev_growth if rev_growth is not None
                            else _safe_float(info.get("revenueGrowth")),

            # Computed from statements
            "roa_cur":      roa_cur,
            "roa_prv":      roa_prv,
            "gm_cur":       gm_cur,
            "gm_prv":       gm_prv,
            "cfo_gt_ni":    cfo_gt_ni,

            # Debt trend
            "debt_cur":     debt_cur,
            "debt_prv":     debt_prv,

            # Share dilution
            "shares_cur":   shares_cur,
            "shares_prv":   shares_prv,

            # Net income (for sign check)
            "ni_cur":       ni_cur,

            # Operating cash flow
            "ocf_cur":      ocf_cur,
        }
        return raw

    except Exception as e:
        return {
            "source":     "yfinance",
            "error":      str(e),
            "fetched_at": datetime.now().isoformat(),
            "ticker":     ticker,
        }


# ── Unified scorer ────────────────────────────────────────────────────────────

def _score(data: dict) -> dict:
    """
    Convert raw fundamental data into the unified 0–10 quality score.

    Returns a flat dict of qual_* keys ready to merge into signal dicts.
    All individual signals are also stored for the dashboard breakdown table.
    """
    pts   = 0
    signals = {}   # name → (earned, max, description)

    sector      = (data.get("sector") or "").lower()
    is_financial = any(k in sector for k in
                       ["financial", "bank", "insurance", "nbfc", "credit"])

    # ══ LEVEL CHECKS ══════════════════════════════════════════════════════════

    # ── 1. ROE — Return on Equity (0–2 pts) ───────────────────────────────────
    # yfinance returns as decimal fraction (0.18 = 18%).
    # Financial companies run at structurally lower ROE — use adjusted bars.
    roe = data.get("roe")
    if roe is not None:
        if is_financial:
            hi, lo = 0.15, 0.10    # banks: 15% = excellent, 10% = ok
        else:
            hi, lo = 0.20, 0.12    # others: 20% = excellent, 12% = ok
        if roe >= hi:
            pts += 2
            signals["ROE"] = (2, 2, f"{roe*100:.1f}% — excellent")
        elif roe >= lo:
            pts += 1
            signals["ROE"] = (1, 2, f"{roe*100:.1f}% — decent")
        else:
            signals["ROE"] = (0, 2, f"{roe*100:.1f}% — weak")
    else:
        signals["ROE"] = (0, 2, "N/A")

    # ── 2. Revenue Growth (0–2 pts) ───────────────────────────────────────────
    rg = data.get("rev_growth")
    if rg is not None:
        if rg >= 0.20:
            pts += 2
            signals["Revenue Growth"] = (2, 2, f"{rg*100:.1f}% — strong")
        elif rg >= 0.10:
            pts += 1
            signals["Revenue Growth"] = (1, 2, f"{rg*100:.1f}% — moderate")
        elif rg >= 0:
            signals["Revenue Growth"] = (0, 2, f"{rg*100:.1f}% — slow")
        else:
            signals["Revenue Growth"] = (0, 2, f"{rg*100:.1f}% — shrinking")
    else:
        signals["Revenue Growth"] = (0, 2, "N/A")

    # ── 3. Current Ratio (0–1 pt) — skipped for banks ─────────────────────────
    if is_financial:
        signals["Current Ratio"] = (0, 1, "N/A (bank/NBFC)")
    else:
        cr = data.get("current_ratio")
        if cr is not None:
            if cr >= 1.5:
                pts += 1
                signals["Current Ratio"] = (1, 1, f"{cr:.2f} — healthy")
            elif cr >= 1.0:
                signals["Current Ratio"] = (0, 1, f"{cr:.2f} — adequate")
            else:
                signals["Current Ratio"] = (0, 1, f"{cr:.2f} — tight")
        else:
            signals["Current Ratio"] = (0, 1, "N/A")

    # ══ TREND CHECKS (Piotroski-style YoY deltas) ═════════════════════════════

    # ── 4. ROA Improving YoY (0–1 pt) ─────────────────────────────────────────
    roa_cur = data.get("roa_cur")
    roa_prv = data.get("roa_prv")
    if roa_cur is not None and roa_prv is not None:
        improving = roa_cur > roa_prv
        if improving:
            pts += 1
            signals["ROA Trend"] = (1, 1,
                f"{roa_prv*100:.1f}% → {roa_cur*100:.1f}% — improving ✓")
        else:
            signals["ROA Trend"] = (0, 1,
                f"{roa_prv*100:.1f}% → {roa_cur*100:.1f}% — declining")
    else:
        signals["ROA Trend"] = (0, 1, "N/A (need 2 years data)")

    # ── 5. CFO > Net Income — Cash Quality (0–1 pt) ───────────────────────────
    # If operating cash flow > net income, earnings are backed by real cash.
    # Gap in the other direction = revenue recognised before cash received (red flag).
    cfo_gt_ni = data.get("cfo_gt_ni")
    ocf = data.get("ocf_cur")
    ni  = data.get("ni_cur")
    if cfo_gt_ni is True:
        pts += 1
        ocf_str = f"₹{ocf/1e9:.1f}B" if ocf else "?"
        ni_str  = f"₹{ni/1e9:.1f}B"  if ni  else "?"
        signals["Cash Quality (CFO>NI)"] = (1, 1,
            f"CFO {ocf_str} > NI {ni_str} — real cash ✓")
    elif cfo_gt_ni is False:
        ocf_str = f"₹{ocf/1e9:.1f}B" if ocf else "?"
        ni_str  = f"₹{ni/1e9:.1f}B"  if ni  else "?"
        signals["Cash Quality (CFO>NI)"] = (0, 1,
            f"CFO {ocf_str} < NI {ni_str} — accruals warning")
    else:
        signals["Cash Quality (CFO>NI)"] = (0, 1, "N/A")

    # ── 6. Debt Falling YoY (0–1 pt) ──────────────────────────────────────────
    # Skip for banks (their "debt" is deposits — inherently high and not a risk signal)
    debt_cur = data.get("debt_cur")
    debt_prv = data.get("debt_prv")
    if is_financial:
        signals["Debt Trend"] = (0, 1, "N/A (bank/NBFC — deposits, not corporate debt)")
    elif debt_cur is not None and debt_prv is not None and debt_prv > 0:
        falling = debt_cur <= debt_prv
        if falling:
            pts += 1
            pct = (debt_prv - debt_cur) / debt_prv * 100
            signals["Debt Trend"] = (1, 1, f"Down {pct:.1f}% YoY — deleveraging ✓")
        else:
            pct = (debt_cur - debt_prv) / debt_prv * 100
            signals["Debt Trend"] = (0, 1, f"Up {pct:.1f}% YoY — taking on debt")
    else:
        signals["Debt Trend"] = (0, 1, "N/A")

    # ── 7. Gross Margin Stable or Rising (0–1 pt) ─────────────────────────────
    # Falling gross margins = losing pricing power or cost inflation
    gm_cur = data.get("gm_cur")
    gm_prv = data.get("gm_prv")
    if gm_cur is not None and gm_prv is not None:
        stable = gm_cur >= gm_prv - 0.01   # allow 1pp tolerance
        if stable:
            pts += 1
            delta = (gm_cur - gm_prv) * 100
            signals["Gross Margin Trend"] = (1, 1,
                f"{gm_prv*100:.1f}% → {gm_cur*100:.1f}% ({delta:+.1f}pp) — holding ✓")
        else:
            delta = (gm_cur - gm_prv) * 100
            signals["Gross Margin Trend"] = (0, 1,
                f"{gm_prv*100:.1f}% → {gm_cur*100:.1f}% ({delta:+.1f}pp) — compressing")
    else:
        signals["Gross Margin Trend"] = (0, 1, "N/A")

    # ── 8. No Share Dilution (0–1 pt) ─────────────────────────────────────────
    # Companies that keep issuing shares dilute existing shareholders.
    # Allow up to 2% increase (stock option plans are normal).
    shares_cur = data.get("shares_cur")
    shares_prv = data.get("shares_prv")
    if shares_cur is not None and shares_prv is not None and shares_prv > 0:
        dilution_pct = (shares_cur - shares_prv) / shares_prv * 100
        if dilution_pct <= 2.0:
            pts += 1
            signals["Share Dilution"] = (1, 1,
                f"{dilution_pct:+.1f}% YoY — no meaningful dilution ✓")
        else:
            signals["Share Dilution"] = (0, 1,
                f"+{dilution_pct:.1f}% YoY — diluting shareholders")
    else:
        signals["Share Dilution"] = (0, 1, "N/A")

    # ── EPS positive — sanity penalty ─────────────────────────────────────────
    eps = data.get("eps")
    if eps is not None and eps < 0:
        pts = max(0, pts - 1)
        signals["EPS Check"] = (0, 0, f"₹{eps:.2f} — loss-making (−1 penalty)")

    # Clamp
    pts = max(0, min(10, pts))

    # Tier
    if pts >= 7:
        tier, color = "HIGH",   "🟢"
    elif pts >= 4:
        tier, color = "MEDIUM", "🟡"
    else:
        tier, color = "LOW",    "🔴"

    # ── Readable breakdown for display ────────────────────────────────────────
    breakdown = {}
    for name, (earned, max_pts, desc) in signals.items():
        tick = "✅" if earned > 0 else ("➖" if "N/A" in desc else "❌")
        breakdown[name] = f"{tick}  {desc}  [{earned}/{max_pts}]"

    return {
        # Core fields used everywhere
        "qual_score":       pts,
        "qual_tier":        tier,
        "qual_tier_color":  color,
        "qual_breakdown":   breakdown,

        # Raw signals for programmatic use
        "qual_signals":     {k: v[0] for k, v in signals.items()},

        # Key metrics for inline display in signal cards
        "qual_roe":         data.get("roe"),
        "qual_rev_growth":  data.get("rev_growth"),
        "qual_current":     data.get("current_ratio"),
        "qual_roa_cur":     roa_cur,
        "qual_roa_prv":     roa_prv,
        "qual_gm_cur":      gm_cur,
        "qual_gm_prv":      gm_prv,
        "qual_debt_cur":    debt_cur,
        "qual_debt_prv":    debt_prv,
        "qual_cfo_gt_ni":   cfo_gt_ni,
        "qual_pe":          data.get("pe"),
        "qual_pb":          data.get("pb"),
        "qual_mktcap":      data.get("market_cap"),
        "qual_sector":      data.get("sector", ""),
        "qual_industry":    data.get("industry", ""),
        "qual_company":     data.get("company_name", ""),
        "qual_fetched_at":  data.get("fetched_at", ""),
        "qual_has_fmp":     False,   # FMP removed — single system now
    }


# ── Public API ────────────────────────────────────────────────────────────────

def get_quality(ticker: str, force: bool = False) -> dict:
    """
    Return the unified quality dict for one ticker.
    Fetches fresh data if cache is missing or older than 90 days.

    Parameters
    ----------
    ticker : e.g. "INFY.NS"
    force  : bypass cache and always re-fetch

    Returns
    -------
    dict with qual_score, qual_tier, qual_tier_color, qual_breakdown, ...
    """
    FUND_DIR.mkdir(parents=True, exist_ok=True)
    cache = _cache_path(ticker)

    if not force and _is_fresh(cache):
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            return _score(data)
        except Exception:
            pass

    data = _fetch(ticker)

    try:
        cache.write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )
    except Exception:
        pass

    return _score(data)


def get_cached_quality(ticker: str) -> dict:
    """
    Serve from cache ONLY — no network call.
    Safe to use inside the screener hot path.
    Returns UNKNOWN defaults if no cache exists.
    """
    cache = _cache_path(ticker)
    if cache.exists():
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            return _score(data)
        except Exception:
            pass
    return {
        "qual_score":      None,
        "qual_tier":       "UNKNOWN",
        "qual_tier_color": "⚪",
        "qual_breakdown":  {},
        "qual_signals":    {},
        "qual_roe":        None,
        "qual_rev_growth": None,
        "qual_current":    None,
        "qual_roa_cur":    None,
        "qual_roa_prv":    None,
        "qual_gm_cur":     None,
        "qual_gm_prv":     None,
        "qual_debt_cur":   None,
        "qual_debt_prv":   None,
        "qual_cfo_gt_ni":  None,
        "qual_pe":         None,
        "qual_pb":         None,
        "qual_mktcap":     None,
        "qual_sector":     "",
        "qual_industry":   "",
        "qual_company":    "",
        "qual_fetched_at": "",
        "qual_has_fmp":    False,
    }


def get_quality_bulk(tickers: list,
                     delay: float = 0.5,
                     force: bool  = False,
                     verbose: bool = True) -> dict:
    """
    Fetch quality scores for a list of tickers, respecting cache.
    Returns {ticker: quality_dict}.
    """
    stale   = [t for t in tickers if force or not _is_fresh(_cache_path(t))]
    results = {}

    if verbose:
        print(f"  [FundamentalScorer] {len(tickers)} tickers — "
              f"{len(tickers) - len(stale)} from cache, "
              f"{len(stale)} to fetch")

    for i, ticker in enumerate(tickers):
        needs_fetch = ticker in stale
        results[ticker] = get_quality(ticker, force=(force and needs_fetch))
        if needs_fetch:
            time.sleep(delay)

    return results


def list_cached() -> list:
    """Return list of tickers that have cached fundamental data."""
    if not FUND_DIR.exists():
        return []
    out = []
    for f in FUND_DIR.glob("*.json"):
        name = f.stem  # e.g. "INFY_NS"
        # Convert back to ticker format
        ticker = name.replace("_NS", ".NS").replace("_BO", ".BO")
        out.append(ticker)
    return out


def cache_stats() -> dict:
    if not FUND_DIR.exists():
        return {"total": 0, "fresh": 0, "stale": 0, "cache_dir": str(FUND_DIR)}
    files = list(FUND_DIR.glob("*.json"))
    fresh = sum(1 for f in files if _is_fresh(f))
    return {
        "total":     len(files),
        "fresh":     fresh,
        "stale":     len(files) - fresh,
        "cache_dir": str(FUND_DIR),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import argparse

    sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, str(BASE_DIR))

    parser = argparse.ArgumentParser(
        description="Unified Fundamental Quality Scorer for NSE stocks"
    )
    parser.add_argument("--ticker",  default="",    help="Single ticker e.g. INFY.NS")
    parser.add_argument("--force",   action="store_true", help="Re-fetch even if cached")
    parser.add_argument("--all",     action="store_true", help="Fetch all universe tickers")
    args = parser.parse_args()

    if args.ticker:
        ticker = args.ticker.upper()
        if not ticker.endswith(".NS"):
            ticker += ".NS"
        q = get_quality(ticker, force=args.force)
        print(f"\n{'═'*55}")
        print(f"  {ticker}  —  {q['qual_tier_color']} {q['qual_tier']}  ({q['qual_score']}/10)")
        print(f"{'═'*55}")
        print(f"  {'Signal':<30} {'Result'}")
        print(f"  {'─'*52}")
        for name, desc in q["qual_breakdown"].items():
            print(f"  {name:<30} {desc}")

    elif args.all:
        from data import TICKERS
        print(f"\nFetching unified quality scores for {len(TICKERS)} stocks...")
        results = get_quality_bulk(TICKERS, force=args.force, verbose=True)
        s = cache_stats()
        print(f"\nCache: {s['total']} stocks cached  |  {s['fresh']} fresh")

        # Print tier summary
        by_tier: dict = {"HIGH": [], "MEDIUM": [], "LOW": [], "UNKNOWN": []}
        for t, q in sorted(results.items(), key=lambda x: -(x[1]["qual_score"] or 0)):
            by_tier[q["qual_tier"]].append((t.replace(".NS",""), q["qual_score"]))

        for tier, color in [("HIGH","🟢"), ("MEDIUM","🟡"), ("LOW","🔴")]:
            stocks = by_tier[tier]
            print(f"\n{color} {tier} ({len(stocks)}):")
            for name, sc in stocks[:15]:
                print(f"  {name:<20} {sc}/10")
            if len(stocks) > 15:
                print(f"  ... and {len(stocks)-15} more")

    else:
        # Default demo: run on a few well-known stocks
        demos = ["INFY.NS", "HDFCBANK.NS", "COALINDIA.NS", "WIPRO.NS", "TITAN.NS"]
        print("\nUnified Fundamental Quality Score — Demo")
        print(f"{'═'*55}")
        for t in demos:
            q = get_quality(t, force=args.force)
            print(f"  {t:<20} {q['qual_tier_color']} {q['qual_score']:>2}/10  {q['qual_tier']}")
