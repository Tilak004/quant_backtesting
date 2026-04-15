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
