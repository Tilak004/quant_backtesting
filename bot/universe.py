"""
universe.py — Stock universe for the NSE swing screener.

Primary source : stocks_list.csv  (NSE equity list, one level above this file)
                 Symbols are read from the SYMBOL column and suffixed with .NS
                 for yfinance / Yahoo Finance format.

Fallback       : The hardcoded WATCHLIST below is used when the CSV is absent.

Tickers that fail data quality (>5 % missing bars) are auto-skipped by
the pipeline — adding extras is safe.

NOTE: TATAMOTORS.NS excluded — Yahoo Finance data feed broken post-demerger.
"""

from pathlib import Path
import csv
import logging

logger = logging.getLogger(__name__)


def _load_from_csv() -> list[str]:
    """Read SYMBOL column from stocks_list.csv and return yfinance tickers."""
    csv_path = Path(__file__).parent.parent / "stocks_list.csv"
    if not csv_path.exists():
        return []
    tickers = []
    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                symbol = row.get("SYMBOL", "").strip()
                if symbol:
                    tickers.append(f"{symbol}.NS")
        logger.info("universe: loaded %d tickers from %s", len(tickers), csv_path.name)
    except Exception as exc:
        logger.warning("universe: could not read %s (%s) — falling back to hardcoded list", csv_path.name, exc)
        return []
    return tickers


_CSV_WATCHLIST = _load_from_csv()

# ── Hardcoded fallback (used only when stocks_list.csv is missing) ─────────────
_FALLBACK_WATCHLIST = [

    # ══════════════════════════════════════════════════════════════════════
    # BANKING — PUBLIC SECTOR
    # ══════════════════════════════════════════════════════════════════════
    "SBIN.NS",        "PNB.NS",         "BANKBARODA.NS",  "CANBK.NS",
    "UNIONBANK.NS",   "INDIANB.NS",     "MAHABANK.NS",    "UCOBK.NS",
    "JKBANK.NS",      "BANKINDIA.NS",   "CENTRALBK.NS",   "IOB.NS",
    "SYNDIBANK.NS",   "PSBANKLTD.NS",   "VIJAYABANK.NS",

    # ══════════════════════════════════════════════════════════════════════
    # BANKING — PRIVATE SECTOR
    # ══════════════════════════════════════════════════════════════════════
    "HDFCBANK.NS",    "ICICIBANK.NS",   "KOTAKBANK.NS",   "AXISBANK.NS",
    "INDUSINDBK.NS",  "BANDHANBNK.NS",  "IDFCFIRSTB.NS",  "RBLBANK.NS",
    "AUBANK.NS",      "FEDERALBNK.NS",  "KARURVYSYA.NS",  "TMB.NS",
    "DCBBANK.NS",     "CSBBANK.NS",     "EQUITASBNK.NS",  "UJJIVANSFB.NS",
    "ESAFSFB.NS",     "UTKARSH.NS",     "SURYODAY.NS",    "SOUTHBANK.NS",
    "LAKSHVILAS.NS",

    # ══════════════════════════════════════════════════════════════════════
    # NBFCs — LARGE & MID
    # ══════════════════════════════════════════════════════════════════════
    "BAJFINANCE.NS",  "BAJAJFINSV.NS",  "CHOLAFIN.NS",    "MUTHOOTFIN.NS",
    "MANAPPURAM.NS",  "SHRIRAMFIN.NS",  "LICHSGFIN.NS",   "FIVESTAR.NS",
    "LTF.NS",         "PNBHOUSING.NS",  "CANFINHOME.NS",  "AAVAS.NS",
    "HOMEFIRST.NS",   "APTUS.NS",       "REPCO.NS",       "SPANDANA.NS",
    "CREDITACC.NS",   "FUSION.NS",      "SBFC.NS",        "ARMANFIN.NS",
    "MASFIN.NS",      "ABCAPITAL.NS",   "IIFL.NS",        "SUNDARMFIN.NS",
    "IBULHSGFIN.NS",

    # ══════════════════════════════════════════════════════════════════════
    # INSURANCE
    # ══════════════════════════════════════════════════════════════════════
    "HDFCLIFE.NS",    "SBILIFE.NS",     "ICICIGI.NS",     "ICICIPRULI.NS",
    "LICI.NS",        "STARHEALTH.NS",  "NIACL.NS",       "GICRE.NS",
    "MFSL.NS",

    # ══════════════════════════════════════════════════════════════════════
    # CAPITAL MARKETS, EXCHANGES & AMCs
    # ══════════════════════════════════════════════════════════════════════
    "BSE.NS",         "MCX.NS",         "CDSL.NS",        "IEX.NS",
    "HDFCAMC.NS",     "CAMS.NS",        "KFINTECH.NS",    "ANGELONE.NS",
    "MOTILALOFS.NS",  "MOFSL.NS",       "ICICISEC.NS",    "NUVAMA.NS",
    "PRUDENT.NS",     "POLICYBZR.NS",

    # ══════════════════════════════════════════════════════════════════════
    # IT & SOFTWARE — LARGE CAP
    # ══════════════════════════════════════════════════════════════════════
    "TCS.NS",         "INFY.NS",        "HCLTECH.NS",     "WIPRO.NS",
    "TECHM.NS",       "LTIM.NS",        "MPHASIS.NS",     "COFORGE.NS",
    "PERSISTENT.NS",  "OFSS.NS",

    # IT — MID & SMALL CAP
    "KPITTECH.NS",    "TATAELXSI.NS",   "LTTS.NS",        "ZENSARTECH.NS",
    "HAPPSTMNDS.NS",  "BSOFT.NS",       "CYIENT.NS",      "MASTEK.NS",
    "BIRLASOFT.NS",   "SONATSOFTW.NS",  "INTELLECT.NS",   "NEWGEN.NS",
    "TANLA.NS",       "LATENTVIEW.NS",  "RATEGAIN.NS",    "INDIAMART.NS",
    "HEXAWARE.NS",    "SUBEXLTD.NS",    "NIIT.NS",        "SASKEN.NS",
    "RAMCOIND.NS",    "ECLERX.NS",      "TATATECH.NS",    "ROUTE.NS",
    "DATAMATICS.NS",  "MAJESCO.NS",

    # ══════════════════════════════════════════════════════════════════════
    # PHARMA & HEALTHCARE — LARGE CAP
    # ══════════════════════════════════════════════════════════════════════
    "SUNPHARMA.NS",   "DRREDDY.NS",     "CIPLA.NS",       "LUPIN.NS",
    "AUROPHARMA.NS",  "TORNTPHARM.NS",  "DIVISLAB.NS",    "MANKIND.NS",
    "ALKEM.NS",       "ZYDUSLIFE.NS",   "IPCALAB.NS",

    # Pharma — Mid & Small
    "GLENMARK.NS",    "NATCOPHARM.NS",  "GRANULES.NS",    "AJANTPHARM.NS",
    "LAURUSLABS.NS",  "GLAND.NS",       "ERIS.NS",        "JBCHEPHARM.NS",
    "STRIDES.NS",     "SOLARA.NS",      "ABBOTINDIA.NS",  "PFIZER.NS",
    "SANOFI.NS",      "GLAXO.NS",       "CAPLINPOINT.NS", "SUVENPHAR.NS",
    "BIOCON.NS",      "HERANBA.NS",     "KRSNAA.NS",

    # Healthcare Services & Diagnostics
    "APOLLOHOSP.NS",  "MAXHEALTH.NS",   "FORTIS.NS",      "NARAYANA.NS",
    "KIMS.NS",        "ASTER.NS",       "RAINBOW.NS",     "MEDPLUS.NS",
    "LALPATHLAB.NS",  "METROPOLIS.NS",  "THYROCARE.NS",   "VIJAYADIAG.NS",
    "POLYMED.NS",

    # ══════════════════════════════════════════════════════════════════════
    # AUTO OEMs
    # ══════════════════════════════════════════════════════════════════════
    "MARUTI.NS",      "M&M.NS",         "BAJAJ-AUTO.NS",  "HEROMOTOCO.NS",
    "EICHERMOT.NS",   "TVSMOTOR.NS",    "ASHOKLEY.NS",    "ESCORTS.NS",
    "SMLISUZU.NS",

    # Auto Ancillaries
    "APOLLOTYRE.NS",  "BOSCHLTD.NS",    "MOTHERSON.NS",   "TIINDIA.NS",
    "SONACOMS.NS",    "SCHAEFFLER.NS",  "SKFINDIA.NS",    "SUNDRMFAST.NS",
    "EXIDEIND.NS",    "AMARARAJA.NS",   "CEATLTD.NS",     "MRF.NS",
    "BALKRISIND.NS",  "UNOMINDA.NS",    "ENDURANCE.NS",   "CRAFTSMAN.NS",
    "GABRIEL.NS",     "SUPRAJIT.NS",    "GRINDWELL.NS",   "MAHINDCIE.NS",
    "VARROC.NS",      "FIEM.NS",        "LUMAXTECH.NS",   "SWARAJENG.NS",
    "JBMA.NS",        "SUBROS.NS",

    # ══════════════════════════════════════════════════════════════════════
    # CAPITAL GOODS & ENGINEERING
    # ══════════════════════════════════════════════════════════════════════
    "LT.NS",          "SIEMENS.NS",     "ABB.NS",         "CUMMINSIND.NS",
    "THERMAX.NS",     "CGPOWER.NS",     "HAVELLS.NS",     "POLYCAB.NS",
    "KEI.NS",         "CROMPTON.NS",    "VOLTAS.NS",      "VGUARD.NS",
    "AIAENG.NS",      "PRAJIND.NS",     "ELECON.NS",      "GREAVESCOT.NS",
    "KSB.NS",         "GRAPHITE.NS",    "VOLTAMP.NS",     "ISGEC.NS",
    "CARBORUNIV.NS",  "ELGIEQUIP.NS",   "LAXMIMACH.NS",   "KIRLOSBROS.NS",
    "ESAB.NS",        "SHAKTIPUMP.NS",  "TDPOWERSYS.NS",

    # ══════════════════════════════════════════════════════════════════════
    # INFRASTRUCTURE — CONSTRUCTION, ROADS & EPC
    # ══════════════════════════════════════════════════════════════════════
    "APLAPOLLO.NS",   "JSWINFRA.NS",    "CONCOR.NS",      "ENGINERSIN.NS",
    "TITAGARH.NS",    "NCC.NS",         "KNR.NS",         "PNCINFRA.NS",
    "ASHOKA.NS",      "AHLUWALIA.NS",   "HCC.NS",         "JKIL.NS",
    "PSPPROJECT.NS",  "CAPACITE.NS",    "HGINFRA.NS",     "IRB.NS",
    "GMRINFRA.NS",    "WELCORP.NS",     "JINDALSAW.NS",   "KEC.NS",
    "KALPATPOWR.NS",  "KPIL.NS",

    # ══════════════════════════════════════════════════════════════════════
    # PSU — RAILWAYS, DEFENCE & STRATEGIC
    # ══════════════════════════════════════════════════════════════════════
    "HAL.NS",         "BEL.NS",         "BHEL.NS",        "BEML.NS",
    "RVNL.NS",        "IRFC.NS",        "IRCON.NS",       "RAILTEL.NS",
    "RITES.NS",       "HUDCO.NS",       "IREDA.NS",       "NBCC.NS",
    "COCHINSHIP.NS",  "MAZAGON.NS",     "GARDENREACH.NS", "MIDHANI.NS",
    "SOLARINDS.NS",   "MTAR.NS",        "DATAPATTNS.NS",  "IDEAFORGE.NS",

    # ══════════════════════════════════════════════════════════════════════
    # METALS & MINING
    # ══════════════════════════════════════════════════════════════════════
    "TATASTEEL.NS",   "JSWSTEEL.NS",    "JINDALSTEL.NS",  "HINDALCO.NS",
    "COALINDIA.NS",   "NMDC.NS",        "SAIL.NS",        "VEDL.NS",
    "NATIONALUM.NS",  "RATNAMANI.NS",   "JSL.NS",         "HINDCOPPER.NS",
    "MOIL.NS",        "SHYAMMETL.NS",   "GALLANTT.NS",    "SARDAEN.NS",
    "GPIL.NS",        "TINPLATE.NS",    "MAHSEAMLES.NS",  "NAVA.NS",
    "MSTCLTD.NS",     "STEELSTRIP.NS",  "GMDC.NS",        "RAIN.NS",
    "LINDE.NS",

    # ══════════════════════════════════════════════════════════════════════
    # CHEMICALS & SPECIALTY
    # ══════════════════════════════════════════════════════════════════════
    "PIDILITIND.NS",  "SRF.NS",         "AARTIIND.NS",    "NAVINFLUOR.NS",
    "ALKYLAMINE.NS",  "PIIND.NS",       "UPL.NS",         "SUMICHEM.NS",
    "FINEORG.NS",     "VINATIORGA.NS",  "GNFC.NS",        "DEEPAKFERT.NS",
    "DEEPAKNTR.NS",   "ATUL.NS",        "TATACHEM.NS",    "GHCL.NS",
    "NOCIL.NS",       "BASF.NS",        "SUDARSCHEM.NS",  "FLUOROCHEM.NS",
    "ROSSARI.NS",     "PCBL.NS",        "GALAXYSURF.NS",  "CLEAN.NS",
    "NEOGEN.NS",      "ANUPAM.NS",      "BODAL.NS",       "EPIGRAL.NS",
    "GUJALKALI.NS",   "HFCL.NS",        "APCOTEX.NS",     "TATVA.NS",
    "HIKAL.NS",       "EXCEL.NS",

    # ══════════════════════════════════════════════════════════════════════
    # CONSUMER, FMCG & RETAIL
    # ══════════════════════════════════════════════════════════════════════
    "HINDUNILVR.NS",  "ITC.NS",         "NESTLEIND.NS",   "BRITANNIA.NS",
    "DABUR.NS",       "MARICO.NS",      "COLPAL.NS",      "GODREJCP.NS",
    "TATACONSUM.NS",  "EMAMILTD.NS",    "UNITDSPR.NS",    "JUBLFOOD.NS",
    "DMART.NS",       "TRENT.NS",       "NYKAA.NS",       "TITAN.NS",
    "KALYANKJIL.NS",  "PAGEIND.NS",     "RELAXO.NS",
    "JYOTHYLAB.NS",   "BAJAJCON.NS",    "GILLETTE.NS",    "PGHH.NS",
    "MCDOWELL-N.NS",  "RADICO.NS",      "DEVYANI.NS",     "WESTLIFE.NS",
    "VBL.NS",         "BIKAJI.NS",      "PRATAAP.NS",     "SAPPHIRE.NS",
    "INDIGOPNTS.NS",  "NAZARA.NS",      "VSTINDS.NS",     "GODFRYPHLP.NS",
    "BATAINDIA.NS",   "METROBRAND.NS",  "CAMPUS.NS",      "VMART.NS",
    "SHOPERSTOP.NS",  "HONASA.NS",      "VEDANTFASH.NS",  "ABFRL.NS",
    "TCNSBRANDS.NS",  "SENCO.NS",       "SAFARI.NS",      "WHIRLPOOL.NS",
    "SYMPHONY.NS",    "BLUESTARCO.NS",  "ORIENTELEC.NS",  "BAJAJELEC.NS",
    "SHEELA.NS",

    # ══════════════════════════════════════════════════════════════════════
    # ENERGY — OIL, GAS & REFINERIES
    # ══════════════════════════════════════════════════════════════════════
    "RELIANCE.NS",    "ONGC.NS",        "BPCL.NS",        "IOC.NS",
    "HPCL.NS",        "GAIL.NS",        "PETRONET.NS",    "OIL.NS",
    "MRPL.NS",        "CPCL.NS",

    # Gas Distribution
    "MGL.NS",         "IGL.NS",         "ATGL.NS",        "GUJGASLTD.NS",

    # ══════════════════════════════════════════════════════════════════════
    # POWER & RENEWABLES
    # ══════════════════════════════════════════════════════════════════════
    "NTPC.NS",        "POWERGRID.NS",   "TATAPOWER.NS",   "ADANIGREEN.NS",
    "TORNTPOWER.NS",  "JSWENERGY.NS",   "NHPC.NS",        "SJVN.NS",
    "RECLTD.NS",      "PFC.NS",         "CESC.NS",        "RPOWER.NS",
    "GIPCL.NS",       "INOXWIND.NS",    "OLECTRA.NS",     "WAAREE.NS",
    "JPPOWER.NS",     "ADANIPOWER.NS",  "SWSOLAR.NS",
    "WEBSOL.NS",

    # ══════════════════════════════════════════════════════════════════════
    # CEMENT & BUILDING MATERIALS
    # ══════════════════════════════════════════════════════════════════════
    "ULTRACEMCO.NS",  "SHREECEM.NS",    "AMBUJACEM.NS",   "ACC.NS",
    "DALBHARAT.NS",   "JKCEMENT.NS",    "RAMCOCEM.NS",    "ASTRAL.NS",
    "NUVOCO.NS",      "ORIENTCEM.NS",   "HEIDELBERG.NS",  "STARCEMENT.NS",
    "KAJARIA.NS",     "CERA.NS",        "SUPREMEIND.NS",  "PRINCEPIPE.NS",
    "FINPIPE.NS",     "CENTURYPLY.NS",  "GREENPANEL.NS",  "SOMANY.NS",
    "HSIL.NS",

    # ══════════════════════════════════════════════════════════════════════
    # REAL ESTATE & HOUSING
    # ══════════════════════════════════════════════════════════════════════
    "DLF.NS",         "GODREJPROP.NS",  "OBEROIRLTY.NS",  "PRESTIGE.NS",
    "PHOENIXLTD.NS",  "DBREALTY.NS",    "BRIGADE.NS",     "SOBHA.NS",
    "MAHLIFE.NS",     "KOLTEPATIL.NS",  "PURAVANKARA.NS", "ANANTRAJ.NS",
    "LODHA.NS",       "GODREJIND.NS",   "SUNTECK.NS",     "NESCO.NS",
    "SIGNATURE.NS",   "AADHAR.NS",

    # ══════════════════════════════════════════════════════════════════════
    # PAINTS & ADHESIVES
    # ══════════════════════════════════════════════════════════════════════
    "ASIANPAINT.NS",  "BERGEPAINT.NS",  "KANSAINER.NS",   "AKZONOBEL.NS",
    "SHALPAINTS.NS",

    # ══════════════════════════════════════════════════════════════════════
    # TEXTILES & APPAREL
    # ══════════════════════════════════════════════════════════════════════
    "RAYMOND.NS",     "ARVIND.NS",      "TRIDENT.NS",     "WELSPUNLIV.NS",
    "VARDHMAN.NS",    "KPR.NS",         "KITEX.NS",       "GOKALDAS.NS",
    "CENTURYTEX.NS",  "DCMSHRIRAM.NS",

    # ══════════════════════════════════════════════════════════════════════
    # LOGISTICS & TRANSPORT
    # ══════════════════════════════════════════════════════════════════════
    "ADANIPORTS.NS",  "BLUEDART.NS",    "DELHIVERY.NS",
    "TCI.NS",         "VRL.NS",         "ALLCARGO.NS",    "GATI.NS",
    "TVSL.NS",        "GPPL.NS",        "SNOWMAN.NS",

    # ══════════════════════════════════════════════════════════════════════
    # AVIATION
    # ══════════════════════════════════════════════════════════════════════
    "INDIGO.NS",      "GMRAIRPORT.NS",

    # ══════════════════════════════════════════════════════════════════════
    # HOSPITALITY & TOURISM
    # ══════════════════════════════════════════════════════════════════════
    "INDHOTEL.NS",    "EIHOTEL.NS",     "LEMONTREE.NS",   "CHALET.NS",
    "MAHINDHOLIDAY.NS",

    # ══════════════════════════════════════════════════════════════════════
    # TELECOM & MEDIA
    # ══════════════════════════════════════════════════════════════════════
    "BHARTIARTL.NS",  "INDUSTOWER.NS",  "IDEA.NS",        "TATACOMM.NS",
    "SUNTV.NS",       "NETWORK18.NS",   "TV18BRDCST.NS",  "HATHWAY.NS",
    "DISHTV.NS",      "PVRINOX.NS",     "ZEEL.NS",        "BALAJI.NS",

    # ══════════════════════════════════════════════════════════════════════
    # AGRICULTURE & FERTILIZERS
    # ══════════════════════════════════════════════════════════════════════
    "CHAMBLFERT.NS",  "COROMANDEL.NS",  "GSFC.NS",
    "KAVERI.NS",      "BAYERCROP.NS",   "KRBL.NS",
    "BALRAMCHIN.NS",  "TRIVENI.NS",     "RENUKA.NS",      "BAJAJHIND.NS",
    "DWARIKESH.NS",   "UTTAMSUGAR.NS",

    # ══════════════════════════════════════════════════════════════════════
    # PAPER & PACKAGING
    # ══════════════════════════════════════════════════════════════════════
    "JKPAPER.NS",     "TNPL.NS",        "UFLEX.NS",       "MOGLISH.NS",

    # ══════════════════════════════════════════════════════════════════════
    # ELECTRONICS, COMPONENTS & EMS
    # ══════════════════════════════════════════════════════════════════════
    "DIXON.NS",       "AMBER.NS",       "SYRMA.NS",       "KAYNES.NS",
    "AEROFLEX.NS",    "RRKABEL.NS",     "HBLPOWER.NS",    "INOXGREEN.NS",
    "REDINGTON.NS",

    # ══════════════════════════════════════════════════════════════════════
    # DIVERSIFIED CONGLOMERATES & NEW-AGE
    # ══════════════════════════════════════════════════════════════════════
    "GRASIM.NS",      "ADANIENT.NS",    "BAJAJHLDNG.NS",  "IRCTC.NS",
    "NAUKRI.NS",      "ETERNAL.NS",     "PAYTM.NS",       "SUZLON.NS",
    "CARTRADE.NS",    "EASEMYTRIP.NS",  "IXIGO.NS",       "MAPMYINDIA.NS",
    "REDTAPE.NS",     "TATAINVEST.NS",  "KPIGREEN.NS",

]

# Use CSV if available, otherwise fall back to the hardcoded list
WATCHLIST = list(dict.fromkeys(_CSV_WATCHLIST if _CSV_WATCHLIST else _FALLBACK_WATCHLIST))

# ── Stocks with statistically NEGATIVE backtest edge (p < 0.05) ───────────────
# Screener still scans these but marks the alert with a ⚠️ warning.
NEGATIVE_EDGE = {
    "CIPLA.NS", "KOTAKBANK.NS", "ACC.NS", "SHREECEM.NS", "ZEEL.NS",
}

# ── Sector map : ticker → sector label ────────────────────────────────────────
# Covers every ticker in the hardcoded fallback list.
# Tickers loaded from stocks_list.csv that are NOT in this map will be resolved
# at runtime via get_sector() using yfinance info (cached per session).
SECTOR_MAP: dict[str, str] = {
    # Banking - PSU
    "SBIN.NS": "Banking - PSU",      "PNB.NS": "Banking - PSU",
    "BANKBARODA.NS": "Banking - PSU","CANBK.NS": "Banking - PSU",
    "UNIONBANK.NS": "Banking - PSU", "INDIANB.NS": "Banking - PSU",
    "MAHABANK.NS": "Banking - PSU",  "UCOBK.NS": "Banking - PSU",
    "JKBANK.NS": "Banking - PSU",    "BANKINDIA.NS": "Banking - PSU",
    "CENTRALBK.NS": "Banking - PSU", "IOB.NS": "Banking - PSU",
    "SYNDIBANK.NS": "Banking - PSU", "PSBANKLTD.NS": "Banking - PSU",
    "VIJAYABANK.NS": "Banking - PSU",
    # Banking - Private
    "HDFCBANK.NS": "Banking - Private",  "ICICIBANK.NS": "Banking - Private",
    "KOTAKBANK.NS": "Banking - Private", "AXISBANK.NS": "Banking - Private",
    "INDUSINDBK.NS": "Banking - Private","BANDHANBNK.NS": "Banking - Private",
    "IDFCFIRSTB.NS": "Banking - Private","RBLBANK.NS": "Banking - Private",
    "AUBANK.NS": "Banking - Private",    "FEDERALBNK.NS": "Banking - Private",
    "KARURVYSYA.NS": "Banking - Private","TMB.NS": "Banking - Private",
    "DCBBANK.NS": "Banking - Private",   "CSBBANK.NS": "Banking - Private",
    "EQUITASBNK.NS": "Banking - Private","UJJIVANSFB.NS": "Banking - Private",
    "ESAFSFB.NS": "Banking - Private",   "UTKARSH.NS": "Banking - Private",
    "SURYODAY.NS": "Banking - Private",  "SOUTHBANK.NS": "Banking - Private",
    "LAKSHVILAS.NS": "Banking - Private",
    # NBFC
    "BAJFINANCE.NS": "NBFC",  "BAJAJFINSV.NS": "NBFC", "CHOLAFIN.NS": "NBFC",
    "MUTHOOTFIN.NS": "NBFC",  "MANAPPURAM.NS": "NBFC", "SHRIRAMFIN.NS": "NBFC",
    "LICHSGFIN.NS": "NBFC",   "FIVESTAR.NS": "NBFC",   "LTF.NS": "NBFC",
    "PNBHOUSING.NS": "NBFC",  "CANFINHOME.NS": "NBFC", "AAVAS.NS": "NBFC",
    "HOMEFIRST.NS": "NBFC",   "APTUS.NS": "NBFC",      "REPCO.NS": "NBFC",
    "SPANDANA.NS": "NBFC",    "CREDITACC.NS": "NBFC",  "FUSION.NS": "NBFC",
    "SBFC.NS": "NBFC",        "ARMANFIN.NS": "NBFC",   "MASFIN.NS": "NBFC",
    "ABCAPITAL.NS": "NBFC",   "IIFL.NS": "NBFC",       "SUNDARMFIN.NS": "NBFC",
    "IBULHSGFIN.NS": "NBFC",  "MMFL.NS": "NBFC",
    # Insurance
    "HDFCLIFE.NS": "Insurance",  "SBILIFE.NS": "Insurance",
    "ICICIGI.NS": "Insurance",   "ICICIPRULI.NS": "Insurance",
    "LICI.NS": "Insurance",      "STARHEALTH.NS": "Insurance",
    "NIACL.NS": "Insurance",     "GICRE.NS": "Insurance",
    "MFSL.NS": "Insurance",      "GICL.NS": "Insurance",
    # Capital Markets
    "BSE.NS": "Capital Markets",     "MCX.NS": "Capital Markets",
    "CDSL.NS": "Capital Markets",    "IEX.NS": "Capital Markets",
    "HDFCAMC.NS": "Capital Markets", "CAMS.NS": "Capital Markets",
    "KFINTECH.NS": "Capital Markets","ANGELONE.NS": "Capital Markets",
    "MOTILALOFS.NS": "Capital Markets","MOFSL.NS": "Capital Markets",
    "ICICISEC.NS": "Capital Markets", "NUVAMA.NS": "Capital Markets",
    "PRUDENT.NS": "Capital Markets",  "POLICYBZR.NS": "Capital Markets",
    "ABSLAMC.NS": "Capital Markets",
    # IT - Large Cap
    "TCS.NS": "IT - Large Cap",   "INFY.NS": "IT - Large Cap",
    "HCLTECH.NS": "IT - Large Cap","WIPRO.NS": "IT - Large Cap",
    "TECHM.NS": "IT - Large Cap", "LTIM.NS": "IT - Large Cap",
    "MPHASIS.NS": "IT - Large Cap","COFORGE.NS": "IT - Large Cap",
    "PERSISTENT.NS": "IT - Large Cap","OFSS.NS": "IT - Large Cap",
    # IT - Mid & Small
    "KPITTECH.NS": "IT - Mid & Small",  "TATAELXSI.NS": "IT - Mid & Small",
    "LTTS.NS": "IT - Mid & Small",      "ZENSARTECH.NS": "IT - Mid & Small",
    "HAPPSTMNDS.NS": "IT - Mid & Small","BSOFT.NS": "IT - Mid & Small",
    "CYIENT.NS": "IT - Mid & Small",    "MASTEK.NS": "IT - Mid & Small",
    "BIRLASOFT.NS": "IT - Mid & Small", "SONATSOFTW.NS": "IT - Mid & Small",
    "INTELLECT.NS": "IT - Mid & Small", "NEWGEN.NS": "IT - Mid & Small",
    "TANLA.NS": "IT - Mid & Small",     "LATENTVIEW.NS": "IT - Mid & Small",
    "RATEGAIN.NS": "IT - Mid & Small",  "INDIAMART.NS": "IT - Mid & Small",
    "HEXAWARE.NS": "IT - Mid & Small",  "SUBEXLTD.NS": "IT - Mid & Small",
    "NIIT.NS": "IT - Mid & Small",      "SASKEN.NS": "IT - Mid & Small",
    "RAMCOIND.NS": "IT - Mid & Small",  "ECLERX.NS": "IT - Mid & Small",
    "TATATECH.NS": "IT - Mid & Small",  "ROUTE.NS": "IT - Mid & Small",
    "DATAMATICS.NS": "IT - Mid & Small","MAJESCO.NS": "IT - Mid & Small",
    "NETWEB.NS": "IT - Mid & Small",
    # Pharma - Large Cap
    "SUNPHARMA.NS": "Pharma - Large Cap","DRREDDY.NS": "Pharma - Large Cap",
    "CIPLA.NS": "Pharma - Large Cap",    "LUPIN.NS": "Pharma - Large Cap",
    "AUROPHARMA.NS": "Pharma - Large Cap","TORNTPHARM.NS": "Pharma - Large Cap",
    "DIVISLAB.NS": "Pharma - Large Cap", "MANKIND.NS": "Pharma - Large Cap",
    "ALKEM.NS": "Pharma - Large Cap",    "ZYDUSLIFE.NS": "Pharma - Large Cap",
    "IPCALAB.NS": "Pharma - Large Cap",
    # Pharma - Mid & Small
    "GLENMARK.NS": "Pharma",   "NATCOPHARM.NS": "Pharma",
    "GRANULES.NS": "Pharma",   "AJANTPHARM.NS": "Pharma",
    "LAURUSLABS.NS": "Pharma", "GLAND.NS": "Pharma",
    "ERIS.NS": "Pharma",       "JBCHEPHARM.NS": "Pharma",
    "STRIDES.NS": "Pharma",    "SOLARA.NS": "Pharma",
    "ABBOTINDIA.NS": "Pharma", "PFIZER.NS": "Pharma",
    "SANOFI.NS": "Pharma",     "GLAXO.NS": "Pharma",
    "CAPLINPOINT.NS": "Pharma","SUVENPHAR.NS": "Pharma",
    "BIOCON.NS": "Pharma",     "HERANBA.NS": "Pharma",
    "KRSNAA.NS": "Pharma",     "SMSPHARMA.NS": "Pharma",
    # Healthcare Services
    "APOLLOHOSP.NS": "Healthcare", "MAXHEALTH.NS": "Healthcare",
    "FORTIS.NS": "Healthcare",     "NARAYANA.NS": "Healthcare",
    "KIMS.NS": "Healthcare",       "ASTER.NS": "Healthcare",
    "RAINBOW.NS": "Healthcare",    "MEDPLUS.NS": "Healthcare",
    "LALPATHLAB.NS": "Healthcare", "METROPOLIS.NS": "Healthcare",
    "THYROCARE.NS": "Healthcare",  "VIJAYADIAG.NS": "Healthcare",
    "POLYMED.NS": "Healthcare",    "YATHARTH.NS": "Healthcare",
    # Auto OEM
    "MARUTI.NS": "Auto OEM",    "M&M.NS": "Auto OEM",
    "BAJAJ-AUTO.NS": "Auto OEM","HEROMOTOCO.NS": "Auto OEM",
    "EICHERMOT.NS": "Auto OEM", "TVSMOTOR.NS": "Auto OEM",
    "ASHOKLEY.NS": "Auto OEM",  "ESCORTS.NS": "Auto OEM",
    "SMLISUZU.NS": "Auto OEM",
    # Auto Ancillaries
    "APOLLOTYRE.NS": "Auto Ancillaries", "BOSCHLTD.NS": "Auto Ancillaries",
    "MOTHERSON.NS": "Auto Ancillaries",  "TIINDIA.NS": "Auto Ancillaries",
    "SONACOMS.NS": "Auto Ancillaries",   "SCHAEFFLER.NS": "Auto Ancillaries",
    "SKFINDIA.NS": "Auto Ancillaries",   "SUNDRMFAST.NS": "Auto Ancillaries",
    "EXIDEIND.NS": "Auto Ancillaries",   "AMARARAJA.NS": "Auto Ancillaries",
    "CEATLTD.NS": "Auto Ancillaries",    "MRF.NS": "Auto Ancillaries",
    "BALKRISIND.NS": "Auto Ancillaries", "UNOMINDA.NS": "Auto Ancillaries",
    "ENDURANCE.NS": "Auto Ancillaries",  "CRAFTSMAN.NS": "Auto Ancillaries",
    "GABRIEL.NS": "Auto Ancillaries",    "SUPRAJIT.NS": "Auto Ancillaries",
    "GRINDWELL.NS": "Auto Ancillaries",  "MAHINDCIE.NS": "Auto Ancillaries",
    "VARROC.NS": "Auto Ancillaries",     "FIEM.NS": "Auto Ancillaries",
    "LUMAXTECH.NS": "Auto Ancillaries",  "SWARAJENG.NS": "Auto Ancillaries",
    "JBMA.NS": "Auto Ancillaries",       "SUBROS.NS": "Auto Ancillaries",
    "BHARATFORG.NS": "Auto Ancillaries", "DIVGIITTS.NS": "Auto Ancillaries",
    # Capital Goods & Engineering
    "LT.NS": "Capital Goods",        "SIEMENS.NS": "Capital Goods",
    "ABB.NS": "Capital Goods",        "CUMMINSIND.NS": "Capital Goods",
    "THERMAX.NS": "Capital Goods",    "CGPOWER.NS": "Capital Goods",
    "HAVELLS.NS": "Capital Goods",    "POLYCAB.NS": "Capital Goods",
    "KEI.NS": "Capital Goods",        "CROMPTON.NS": "Capital Goods",
    "VOLTAS.NS": "Capital Goods",     "VGUARD.NS": "Capital Goods",
    "AIAENG.NS": "Capital Goods",     "PRAJIND.NS": "Capital Goods",
    "ELECON.NS": "Capital Goods",     "GREAVESCOT.NS": "Capital Goods",
    "KSB.NS": "Capital Goods",        "GRAPHITE.NS": "Capital Goods",
    "VOLTAMP.NS": "Capital Goods",    "ISGEC.NS": "Capital Goods",
    "CARBORUNIV.NS": "Capital Goods", "ELGIEQUIP.NS": "Capital Goods",
    "LAXMIMACH.NS": "Capital Goods",  "KIRLOSBROS.NS": "Capital Goods",
    "ESAB.NS": "Capital Goods",       "SHAKTIPUMP.NS": "Capital Goods",
    "TDPOWERSYS.NS": "Capital Goods", "KIRLOSENG.NS": "Capital Goods",
    "KRN.NS": "Capital Goods",        "RISHABH.NS": "Capital Goods",
    # Infrastructure
    "APLAPOLLO.NS": "Infrastructure",  "JSWINFRA.NS": "Infrastructure",
    "CONCOR.NS": "Infrastructure",     "ENGINERSIN.NS": "Infrastructure",
    "TITAGARH.NS": "Infrastructure",   "NCC.NS": "Infrastructure",
    "KNR.NS": "Infrastructure",        "PNCINFRA.NS": "Infrastructure",
    "ASHOKA.NS": "Infrastructure",     "AHLUWALIA.NS": "Infrastructure",
    "HCC.NS": "Infrastructure",        "JKIL.NS": "Infrastructure",
    "PSPPROJECT.NS": "Infrastructure", "CAPACITE.NS": "Infrastructure",
    "HGINFRA.NS": "Infrastructure",    "IRB.NS": "Infrastructure",
    "GMRINFRA.NS": "Infrastructure",   "WELCORP.NS": "Infrastructure",
    "JINDALSAW.NS": "Infrastructure",  "KEC.NS": "Infrastructure",
    "KALPATPOWR.NS": "Infrastructure", "KPIL.NS": "Infrastructure",
    # Defence & Railways
    "HAL.NS": "Defence & Railways",       "BEL.NS": "Defence & Railways",
    "BHEL.NS": "Defence & Railways",      "BEML.NS": "Defence & Railways",
    "RVNL.NS": "Defence & Railways",      "IRFC.NS": "Defence & Railways",
    "IRCON.NS": "Defence & Railways",     "RAILTEL.NS": "Defence & Railways",
    "RITES.NS": "Defence & Railways",     "HUDCO.NS": "Defence & Railways",
    "IREDA.NS": "Defence & Railways",     "NBCC.NS": "Defence & Railways",
    "COCHINSHIP.NS": "Defence & Railways","MAZAGON.NS": "Defence & Railways",
    "GARDENREACH.NS": "Defence & Railways","MIDHANI.NS": "Defence & Railways",
    "SOLARINDS.NS": "Defence & Railways", "MTAR.NS": "Defence & Railways",
    "DATAPATTNS.NS": "Defence & Railways","IDEAFORGE.NS": "Defence & Railways",
    # Metals & Mining
    "TATASTEEL.NS": "Metals & Mining",  "JSWSTEEL.NS": "Metals & Mining",
    "JINDALSTEL.NS": "Metals & Mining", "HINDALCO.NS": "Metals & Mining",
    "COALINDIA.NS": "Metals & Mining",  "NMDC.NS": "Metals & Mining",
    "SAIL.NS": "Metals & Mining",       "VEDL.NS": "Metals & Mining",
    "NATIONALUM.NS": "Metals & Mining", "RATNAMANI.NS": "Metals & Mining",
    "JSL.NS": "Metals & Mining",        "HINDCOPPER.NS": "Metals & Mining",
    "MOIL.NS": "Metals & Mining",       "SHYAMMETL.NS": "Metals & Mining",
    "GALLANTT.NS": "Metals & Mining",   "SARDAEN.NS": "Metals & Mining",
    "GPIL.NS": "Metals & Mining",       "TINPLATE.NS": "Metals & Mining",
    "MAHSEAMLES.NS": "Metals & Mining", "NAVA.NS": "Metals & Mining",
    "MSTCLTD.NS": "Metals & Mining",    "STEELSTRIP.NS": "Metals & Mining",
    "GMDC.NS": "Metals & Mining",       "RAIN.NS": "Metals & Mining",
    "LINDE.NS": "Metals & Mining",
    # Chemicals & Specialty
    "PIDILITIND.NS": "Chemicals", "SRF.NS": "Chemicals",
    "AARTIIND.NS": "Chemicals",   "NAVINFLUOR.NS": "Chemicals",
    "ALKYLAMINE.NS": "Chemicals", "PIIND.NS": "Chemicals",
    "UPL.NS": "Chemicals",        "SUMICHEM.NS": "Chemicals",
    "FINEORG.NS": "Chemicals",    "VINATIORGA.NS": "Chemicals",
    "GNFC.NS": "Chemicals",       "DEEPAKFERT.NS": "Chemicals",
    "DEEPAKNTR.NS": "Chemicals",  "ATUL.NS": "Chemicals",
    "TATACHEM.NS": "Chemicals",   "GHCL.NS": "Chemicals",
    "NOCIL.NS": "Chemicals",      "BASF.NS": "Chemicals",
    "SUDARSCHEM.NS": "Chemicals", "FLUOROCHEM.NS": "Chemicals",
    "ROSSARI.NS": "Chemicals",    "PCBL.NS": "Chemicals",
    "GALAXYSURF.NS": "Chemicals", "CLEAN.NS": "Chemicals",
    "NEOGEN.NS": "Chemicals",     "ANUPAM.NS": "Chemicals",
    "BODAL.NS": "Chemicals",      "EPIGRAL.NS": "Chemicals",
    "GUJALKALI.NS": "Chemicals",  "HFCL.NS": "Chemicals",
    "APCOTEX.NS": "Chemicals",    "TATVA.NS": "Chemicals",
    "HIKAL.NS": "Chemicals",      "EXCEL.NS": "Chemicals",
    "KINGFA.NS": "Chemicals",
    # Consumer & FMCG
    "HINDUNILVR.NS": "Consumer & FMCG","ITC.NS": "Consumer & FMCG",
    "NESTLEIND.NS": "Consumer & FMCG", "BRITANNIA.NS": "Consumer & FMCG",
    "DABUR.NS": "Consumer & FMCG",     "MARICO.NS": "Consumer & FMCG",
    "COLPAL.NS": "Consumer & FMCG",    "GODREJCP.NS": "Consumer & FMCG",
    "TATACONSUM.NS": "Consumer & FMCG","EMAMILTD.NS": "Consumer & FMCG",
    "UNITDSPR.NS": "Consumer & FMCG",  "JUBLFOOD.NS": "Consumer & FMCG",
    "DMART.NS": "Consumer & FMCG",     "TRENT.NS": "Consumer & FMCG",
    "NYKAA.NS": "Consumer & FMCG",     "TITAN.NS": "Consumer & FMCG",
    "KALYANKJIL.NS": "Consumer & FMCG","PAGEIND.NS": "Consumer & FMCG",
    "RELAXO.NS": "Consumer & FMCG",    "JYOTHYLAB.NS": "Consumer & FMCG",
    "BAJAJCON.NS": "Consumer & FMCG",  "GILLETTE.NS": "Consumer & FMCG",
    "PGHH.NS": "Consumer & FMCG",      "MCDOWELL-N.NS": "Consumer & FMCG",
    "RADICO.NS": "Consumer & FMCG",    "DEVYANI.NS": "Consumer & FMCG",
    "WESTLIFE.NS": "Consumer & FMCG",  "VBL.NS": "Consumer & FMCG",
    "BIKAJI.NS": "Consumer & FMCG",    "PRATAAP.NS": "Consumer & FMCG",
    "SAPPHIRE.NS": "Consumer & FMCG",  "INDIGOPNTS.NS": "Consumer & FMCG",
    "NAZARA.NS": "Consumer & FMCG",    "VSTINDS.NS": "Consumer & FMCG",
    "GODFRYPHLP.NS": "Consumer & FMCG","BATAINDIA.NS": "Consumer & FMCG",
    "METROBRAND.NS": "Consumer & FMCG","CAMPUS.NS": "Consumer & FMCG",
    "VMART.NS": "Consumer & FMCG",     "SHOPERSTOP.NS": "Consumer & FMCG",
    "HONASA.NS": "Consumer & FMCG",    "VEDANTFASH.NS": "Consumer & FMCG",
    "ABFRL.NS": "Consumer & FMCG",     "TCNSBRANDS.NS": "Consumer & FMCG",
    "SENCO.NS": "Consumer & FMCG",     "SAFARI.NS": "Consumer & FMCG",
    "WHIRLPOOL.NS": "Consumer & FMCG", "SYMPHONY.NS": "Consumer & FMCG",
    "BLUESTARCO.NS": "Consumer & FMCG","ORIENTELEC.NS": "Consumer & FMCG",
    "BAJAJELEC.NS": "Consumer & FMCG", "SHEELA.NS": "Consumer & FMCG",
    "SKYGOLD.NS": "Consumer & FMCG",   "THANGAMAYL.NS": "Consumer & FMCG",
    # Oil & Gas
    "RELIANCE.NS": "Oil & Gas","ONGC.NS": "Oil & Gas",
    "BPCL.NS": "Oil & Gas",   "IOC.NS": "Oil & Gas",
    "HPCL.NS": "Oil & Gas",   "GAIL.NS": "Oil & Gas",
    "PETRONET.NS": "Oil & Gas","OIL.NS": "Oil & Gas",
    "MRPL.NS": "Oil & Gas",   "CPCL.NS": "Oil & Gas",
    "MGL.NS": "Oil & Gas",    "IGL.NS": "Oil & Gas",
    "ATGL.NS": "Oil & Gas",   "GUJGASLTD.NS": "Oil & Gas",
    # Power & Renewables
    "NTPC.NS": "Power & Renewables",     "POWERGRID.NS": "Power & Renewables",
    "TATAPOWER.NS": "Power & Renewables","ADANIGREEN.NS": "Power & Renewables",
    "TORNTPOWER.NS": "Power & Renewables","JSWENERGY.NS": "Power & Renewables",
    "NHPC.NS": "Power & Renewables",     "SJVN.NS": "Power & Renewables",
    "RECLTD.NS": "Power & Renewables",   "PFC.NS": "Power & Renewables",
    "CESC.NS": "Power & Renewables",     "RPOWER.NS": "Power & Renewables",
    "GIPCL.NS": "Power & Renewables",    "INOXWIND.NS": "Power & Renewables",
    "OLECTRA.NS": "Power & Renewables",  "WAAREE.NS": "Power & Renewables",
    "JPPOWER.NS": "Power & Renewables",  "ADANIPOWER.NS": "Power & Renewables",
    "SWSOLAR.NS": "Power & Renewables",  "WEBSOL.NS": "Power & Renewables",
    "PTC.NS": "Power & Renewables",
    # Cement & Building Materials
    "ULTRACEMCO.NS": "Cement & Materials","SHREECEM.NS": "Cement & Materials",
    "AMBUJACEM.NS": "Cement & Materials", "ACC.NS": "Cement & Materials",
    "DALBHARAT.NS": "Cement & Materials", "JKCEMENT.NS": "Cement & Materials",
    "RAMCOCEM.NS": "Cement & Materials",  "ASTRAL.NS": "Cement & Materials",
    "NUVOCO.NS": "Cement & Materials",    "ORIENTCEM.NS": "Cement & Materials",
    "HEIDELBERG.NS": "Cement & Materials","STARCEMENT.NS": "Cement & Materials",
    "KAJARIA.NS": "Cement & Materials",   "CERA.NS": "Cement & Materials",
    "SUPREMEIND.NS": "Cement & Materials","PRINCEPIPE.NS": "Cement & Materials",
    "FINPIPE.NS": "Cement & Materials",   "CENTURYPLY.NS": "Cement & Materials",
    "GREENPANEL.NS": "Cement & Materials","SOMANY.NS": "Cement & Materials",
    "HSIL.NS": "Cement & Materials",      "MANGLMCEM.NS": "Cement & Materials",
    # Real Estate
    "DLF.NS": "Real Estate",       "GODREJPROP.NS": "Real Estate",
    "OBEROIRLTY.NS": "Real Estate","PRESTIGE.NS": "Real Estate",
    "PHOENIXLTD.NS": "Real Estate","DBREALTY.NS": "Real Estate",
    "BRIGADE.NS": "Real Estate",   "SOBHA.NS": "Real Estate",
    "MAHLIFE.NS": "Real Estate",   "KOLTEPATIL.NS": "Real Estate",
    "PURAVANKARA.NS": "Real Estate","ANANTRAJ.NS": "Real Estate",
    "LODHA.NS": "Real Estate",     "GODREJIND.NS": "Real Estate",
    "SUNTECK.NS": "Real Estate",   "NESCO.NS": "Real Estate",
    "SIGNATURE.NS": "Real Estate", "AADHAR.NS": "Real Estate",
    # Paints
    "ASIANPAINT.NS": "Paints","BERGEPAINT.NS": "Paints",
    "KANSAINER.NS": "Paints", "AKZONOBEL.NS": "Paints",
    "SHALPAINTS.NS": "Paints",
    # Textiles
    "RAYMOND.NS": "Textiles",  "ARVIND.NS": "Textiles",
    "TRIDENT.NS": "Textiles",  "WELSPUNLIV.NS": "Textiles",
    "VARDHMAN.NS": "Textiles", "KPR.NS": "Textiles",
    "KITEX.NS": "Textiles",    "GOKALDAS.NS": "Textiles",
    "CENTURYTEX.NS": "Textiles","DCMSHRIRAM.NS": "Textiles",
    # Logistics & Transport
    "ADANIPORTS.NS": "Logistics","BLUEDART.NS": "Logistics",
    "DELHIVERY.NS": "Logistics", "TCI.NS": "Logistics",
    "VRL.NS": "Logistics",       "ALLCARGO.NS": "Logistics",
    "GATI.NS": "Logistics",      "TVSL.NS": "Logistics",
    "GPPL.NS": "Logistics",      "SNOWMAN.NS": "Logistics",
    "SCI.NS": "Logistics",       "MAHLOG.NS": "Logistics",
    # Aviation
    "INDIGO.NS": "Aviation","GMRAIRPORT.NS": "Aviation",
    # Hospitality
    "INDHOTEL.NS": "Hospitality",     "EIHOTEL.NS": "Hospitality",
    "LEMONTREE.NS": "Hospitality",    "CHALET.NS": "Hospitality",
    "MAHINDHOLIDAY.NS": "Hospitality",
    # Telecom & Media
    "BHARTIARTL.NS": "Telecom & Media","INDUSTOWER.NS": "Telecom & Media",
    "IDEA.NS": "Telecom & Media",      "TATACOMM.NS": "Telecom & Media",
    "SUNTV.NS": "Telecom & Media",     "NETWORK18.NS": "Telecom & Media",
    "TV18BRDCST.NS": "Telecom & Media","HATHWAY.NS": "Telecom & Media",
    "DISHTV.NS": "Telecom & Media",    "PVRINOX.NS": "Telecom & Media",
    "ZEEL.NS": "Telecom & Media",      "BALAJI.NS": "Telecom & Media",
    # Agriculture & Fertilizers
    "CHAMBLFERT.NS": "Agri & Fertilizers","COROMANDEL.NS": "Agri & Fertilizers",
    "GSFC.NS": "Agri & Fertilizers",      "KAVERI.NS": "Agri & Fertilizers",
    "BAYERCROP.NS": "Agri & Fertilizers", "KRBL.NS": "Agri & Fertilizers",
    "BALRAMCHIN.NS": "Agri & Fertilizers","TRIVENI.NS": "Agri & Fertilizers",
    "RENUKA.NS": "Agri & Fertilizers",    "BAJAJHIND.NS": "Agri & Fertilizers",
    "DWARIKESH.NS": "Agri & Fertilizers", "UTTAMSUGAR.NS": "Agri & Fertilizers",
    # Paper & Packaging
    "JKPAPER.NS": "Paper & Packaging","TNPL.NS": "Paper & Packaging",
    "UFLEX.NS": "Paper & Packaging",  "MOGLISH.NS": "Paper & Packaging",
    # Electronics & EMS
    "DIXON.NS": "Electronics & EMS",  "AMBER.NS": "Electronics & EMS",
    "SYRMA.NS": "Electronics & EMS",  "KAYNES.NS": "Electronics & EMS",
    "AEROFLEX.NS": "Electronics & EMS","RRKABEL.NS": "Electronics & EMS",
    "HBLPOWER.NS": "Electronics & EMS","INOXGREEN.NS": "Electronics & EMS",
    "REDINGTON.NS": "Electronics & EMS",
    # Diversified / New-Age
    "GRASIM.NS": "Diversified",      "ADANIENT.NS": "Diversified",
    "BAJAJHLDNG.NS": "Diversified",  "IRCTC.NS": "Diversified",
    "NAUKRI.NS": "Diversified",      "ETERNAL.NS": "Diversified",
    "PAYTM.NS": "Diversified",       "SUZLON.NS": "Diversified",
    "CARTRADE.NS": "Diversified",    "EASEMYTRIP.NS": "Diversified",
    "IXIGO.NS": "Diversified",       "MAPMYINDIA.NS": "Diversified",
    "REDTAPE.NS": "Diversified",     "TATAINVEST.NS": "Diversified",
    "KPIGREEN.NS": "Diversified",
    # Security Services
    "PRIMESECU.NS": "Security Services",
}

# ── Runtime sector cache (populated via yfinance for unknown tickers) ──────────
_sector_cache: dict[str, str] = {}


def get_sector(ticker: str) -> str:
    """
    Return the sector label for *ticker*.

    Look-up order:
      1. SECTOR_MAP  (instant, covers all hardcoded tickers)
      2. _sector_cache (in-memory cache for yfinance results this session)
      3. yfinance Ticker.info  (network call — only for CSV-loaded unknowns)
      4. "Other" as final fallback
    """
    if ticker in SECTOR_MAP:
        return SECTOR_MAP[ticker]
    if ticker in _sector_cache:
        return _sector_cache[ticker]
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        sector = info.get("sector") or info.get("industry") or "Other"
    except Exception:
        sector = "Other"
    _sector_cache[ticker] = sector
    return sector
