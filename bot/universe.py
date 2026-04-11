"""
universe.py — Stock universe for the NSE swing screener.

This is the ONLY file you need to edit to add or remove stocks.
All tickers are in yfinance / Yahoo Finance format  (e.g. "WIPRO.NS").

Current coverage  : ~175 liquid NSE stocks
  — Nifty 50       (complete)
  — Nifty Next 50  (most liquid)
  — Nifty Midcap   (key names)
  — Popular small-caps & themes

To add a stock   : append "TICKER.NS" to any section below.
To remove a stock: delete or comment out the line.

NOTE — TATAMOTORS.NS is excluded: Yahoo Finance currently does not serve
this ticker (NSE demerger/restructuring broke the data feed). Re-add once
Yahoo Finance fixes it.
"""

WATCHLIST = [

    # ══════════════════════════════════════════════════════════════════════
    # BANKING & FINANCIAL SERVICES
    # ══════════════════════════════════════════════════════════════════════
    "HDFCBANK.NS",    "ICICIBANK.NS",   "SBIN.NS",        "KOTAKBANK.NS",
    "AXISBANK.NS",    "INDUSINDBK.NS",  "BANKBARODA.NS",  "PNB.NS",
    "BANDHANBNK.NS",  "IDFCFIRSTB.NS",  "RBLBANK.NS",     "AUBANK.NS",
    "FEDERALBNK.NS",  "CANBK.NS",

    # NBFCs & Insurance
    "BAJFINANCE.NS",  "BAJAJFINSV.NS",  "CHOLAFIN.NS",    "MUTHOOTFIN.NS",
    "MANAPPURAM.NS",  "SHRIRAMFIN.NS",  "LICHSGFIN.NS",   "FIVESTAR.NS",
    "HDFCLIFE.NS",    "SBILIFE.NS",     "ICICIGI.NS",     "ICICIPRULI.NS",
    "LICI.NS",

    # ══════════════════════════════════════════════════════════════════════
    # IT & TECHNOLOGY
    # ══════════════════════════════════════════════════════════════════════
    "TCS.NS",         "INFY.NS",        "HCLTECH.NS",     "WIPRO.NS",
    "TECHM.NS",       "LTIM.NS",        "MPHASIS.NS",     "COFORGE.NS",
    "PERSISTENT.NS",  "OFSS.NS",        "KPITTECH.NS",    "TATAELXSI.NS",
    "LTTS.NS",        "ZENSARTECH.NS",  "HAPPSTMNDS.NS",  "BSOFT.NS",

    # ══════════════════════════════════════════════════════════════════════
    # PHARMA & HEALTHCARE
    # ══════════════════════════════════════════════════════════════════════
    "SUNPHARMA.NS",   "DRREDDY.NS",     "CIPLA.NS",       "APOLLOHOSP.NS",
    "LUPIN.NS",       "AUROPHARMA.NS",  "TORNTPHARM.NS",  "IPCALAB.NS",
    "ALKEM.NS",       "ZYDUSLIFE.NS",   "GLENMARK.NS",    "NATCOPHARM.NS",
    "LALPATHLAB.NS",  "METROPOLIS.NS",  "MAXHEALTH.NS",   "FORTIS.NS",

    # ══════════════════════════════════════════════════════════════════════
    # AUTO & AUTO ANCILLARY
    # ══════════════════════════════════════════════════════════════════════
    "MARUTI.NS",      "M&M.NS",         "BAJAJ-AUTO.NS",  "HEROMOTOCO.NS",
    "EICHERMOT.NS",   "TVSMOTOR.NS",    "ASHOKLEY.NS",    "APOLLOTYRE.NS",
    "TIINDIA.NS",     "SONACOMS.NS",    "BOSCHLTD.NS",    "MOTHERSON.NS",

    # ══════════════════════════════════════════════════════════════════════
    # CAPITAL GOODS, INFRA & DEFENCE
    # ══════════════════════════════════════════════════════════════════════
    "LT.NS",          "SIEMENS.NS",     "ABB.NS",         "BHEL.NS",
    "HAL.NS",         "BEL.NS",         "CUMMINSIND.NS",  "THERMAX.NS",
    "CGPOWER.NS",     "APLAPOLLO.NS",   "POLYCAB.NS",     "KEI.NS",
    "HAVELLS.NS",     "CROMPTON.NS",    "VOLTAS.NS",      "VGUARD.NS",
    "ENGINERSIN.NS",  "TITAGARH.NS",    "IRFC.NS",        "CONCOR.NS",
    "JSWINFRA.NS",

    # ══════════════════════════════════════════════════════════════════════
    # METALS & COMMODITIES
    # ══════════════════════════════════════════════════════════════════════
    "TATASTEEL.NS",   "JSWSTEEL.NS",    "JINDALSTEL.NS",  "HINDALCO.NS",
    "COALINDIA.NS",   "NMDC.NS",        "SAIL.NS",        "VEDL.NS",
    "NATIONALUM.NS",  "RATNAMANI.NS",

    # ══════════════════════════════════════════════════════════════════════
    # CHEMICALS & SPECIALTY
    # ══════════════════════════════════════════════════════════════════════
    "PIDILITIND.NS",  "AARTIIND.NS",    "DEEPAKFERT.NS",  "NAVINFLUOR.NS",
    "ALKYLAMINE.NS",  "SRF.NS",         "PIIND.NS",       "UPL.NS",
    "SUMICHEM.NS",    "FINEORG.NS",     "VINATIORGA.NS",  "GNFC.NS",

    # ══════════════════════════════════════════════════════════════════════
    # CONSUMER, FMCG & RETAIL
    # ══════════════════════════════════════════════════════════════════════
    "HINDUNILVR.NS",  "ITC.NS",         "NESTLEIND.NS",   "BRITANNIA.NS",
    "DABUR.NS",       "MARICO.NS",      "COLPAL.NS",      "GODREJCP.NS",
    "TATACONSUM.NS",  "EMAMILTD.NS",    "UNITDSPR.NS",    "JUBLFOOD.NS",
    "DMART.NS",       "TRENT.NS",       "NYKAA.NS",       "TITAN.NS",
    "KALYANKJIL.NS",  "PAGEIND.NS",     "RELAXO.NS",

    # ══════════════════════════════════════════════════════════════════════
    # ENERGY, OIL & POWER
    # ══════════════════════════════════════════════════════════════════════
    "RELIANCE.NS",    "ONGC.NS",        "BPCL.NS",        "IOC.NS",
    "GAIL.NS",        "PETRONET.NS",    "NTPC.NS",        "POWERGRID.NS",
    "TATAPOWER.NS",   "ADANIGREEN.NS",  "ADANIPORTS.NS",  "TORNTPOWER.NS",
    "JSWENERGY.NS",   "NHPC.NS",        "SJVN.NS",        "RECLTD.NS",
    "PFC.NS",

    # ══════════════════════════════════════════════════════════════════════
    # CEMENT & BUILDING MATERIALS
    # ══════════════════════════════════════════════════════════════════════
    "ULTRACEMCO.NS",  "SHREECEM.NS",    "AMBUJACEM.NS",   "ACC.NS",
    "DALBHARAT.NS",   "JKCEMENT.NS",    "RAMCOCEM.NS",    "ASTRAL.NS",

    # ══════════════════════════════════════════════════════════════════════
    # REAL ESTATE
    # ══════════════════════════════════════════════════════════════════════
    "DLF.NS",         "GODREJPROP.NS",  "OBEROIRLTY.NS",  "PRESTIGE.NS",
    "PHOENIXLTD.NS",  "DBREALTY.NS",

    # ══════════════════════════════════════════════════════════════════════
    # TELECOM, MEDIA & NEW-AGE
    # ══════════════════════════════════════════════════════════════════════
    "BHARTIARTL.NS",  "INDUSTOWER.NS",  "IDEA.NS",        "ZEEL.NS",
    "PVRINOX.NS",     "PAYTM.NS",

    # ══════════════════════════════════════════════════════════════════════
    # DIVERSIFIED & OTHERS
    # ══════════════════════════════════════════════════════════════════════
    "GRASIM.NS",      "ASIANPAINT.NS",  "BERGEPAINT.NS",  "KANSAINER.NS",
    "DIXON.NS",       "BSE.NS",         "IRCTC.NS",       "ETERNAL.NS",
    "NAUKRI.NS",      "TATATECH.NS",    "SUZLON.NS",      "IEX.NS",
    "HDFCAMC.NS",     "CAMS.NS",        "BAJAJHLDNG.NS",

]

# ── Stocks with statistically NEGATIVE backtest edge (p < 0.05) ───────────────
# Screener still scans these but marks the alert with a ⚠️ warning.
NEGATIVE_EDGE = {
    "CIPLA.NS", "KOTAKBANK.NS", "ACC.NS", "SHREECEM.NS", "ZEEL.NS",
}
