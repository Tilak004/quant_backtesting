"""
notifier.py — Build and send HTML email alerts via Gmail SMTP.

Each signal becomes one trade-card block inside a single daily email.
If there are no signals, a brief "all quiet" summary is sent so you
know the scanner ran successfully.
"""

import smtplib
import sys
import os
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from bot.config import GMAIL_SENDER, GMAIL_APP_PASS, ALERT_RECIPIENTS


# ── Colour palette ─────────────────────────────────────────────────────────────
_GREEN  = "#1db954"
_RED    = "#e53e3e"
_ORANGE = "#dd6b20"
_BLUE   = "#3182ce"
_DARK   = "#1a202c"
_CARD   = "#2d3748"
_MUTED  = "#a0aec0"
_WHITE  = "#f7fafc"


# ── Per-signal HTML card ───────────────────────────────────────────────────────
def _signal_card(sig: dict) -> str:
    is_long    = sig["direction"] == "LONG"
    accent     = _GREEN if is_long else _RED
    dir_label  = "⬆ LONG" if is_long else "⬇ SHORT"
    score      = sig["score"]
    score_color = _GREEN if score >= 5 else (_ORANGE if score >= 4 else _RED)
    score_label = "High Conviction" if score >= 5 else ("Moderate" if score >= 4 else "Low")

    neg_warn = ""
    if sig.get("negative_edge"):
        neg_warn = f"""
        <tr>
          <td colspan="2" style="padding:6px 12px;background:#744210;border-radius:4px;
              color:#fbd38d;font-size:12px;text-align:center;">
            ⚠️  Backtest shows NEGATIVE edge on this ticker — trade with extra caution
          </td>
        </tr>"""

    mesh_color = _GREEN if sig["green_mesh"] else _RED
    mesh_label = f"{'Green' if sig['green_mesh'] else 'Red'} mesh · {sig['mesh_bars']} bars"

    weekly_icon  = "✅" if sig["weekly_bull"]  else "❌"
    weekly_label = "Bullish" if sig["weekly_bull"] else "Bearish"

    return f"""
    <!-- ── SIGNAL CARD ──────────────────────────────────── -->
    <table width="100%" cellpadding="0" cellspacing="0"
           style="background:{_CARD};border-radius:10px;margin-bottom:24px;
                  border-left:5px solid {accent};overflow:hidden;">
      <tr>
        <!-- Header -->
        <td colspan="2" style="padding:14px 16px;background:{_DARK};">
          <span style="font-size:20px;font-weight:700;color:{accent};">{sig['emoji']}  {sig['ticker']}</span>
          <span style="float:right;font-size:13px;color:{_MUTED};">{sig['date']}</span>
        </td>
      </tr>
      <tr>
        <td style="padding:8px 16px 4px;font-size:13px;color:{_MUTED};">Signal</td>
        <td style="padding:8px 16px 4px;text-align:right;">
          <span style="background:{accent};color:#fff;padding:3px 10px;border-radius:12px;
                font-size:12px;font-weight:600;">{dir_label}</span>
          &nbsp;
          <span style="color:#fff;font-size:13px;">{sig['label']}
            <span style="color:{_MUTED};font-size:11px;">({sig['signal_type']})</span>
          </span>
        </td>
      </tr>
      <tr>
        <td style="padding:4px 16px;font-size:13px;color:{_MUTED};">Score</td>
        <td style="padding:4px 16px;text-align:right;font-size:13px;">
          <span style="color:{score_color};font-weight:700;">{score} / 6</span>
          <span style="color:{_MUTED};font-size:11px;"> — {score_label}</span>
        </td>
      </tr>
      {neg_warn}

      <!-- Divider -->
      <tr><td colspan="2" style="padding:0 16px;">
        <hr style="border:none;border-top:1px solid #4a5568;margin:8px 0;">
      </td></tr>

      <!-- Price levels -->
      <tr>
        <td style="padding:6px 16px;font-size:13px;color:{_MUTED};">Entry (today's close)</td>
        <td style="padding:6px 16px;text-align:right;font-size:15px;
                   font-weight:700;color:{_WHITE};">₹{sig['entry']:,.2f}</td>
      </tr>
      <tr>
        <td style="padding:6px 16px;font-size:13px;color:{_MUTED};">Stop Loss</td>
        <td style="padding:6px 16px;text-align:right;font-size:14px;color:{_RED};font-weight:600;">
          ₹{sig['sl']:,.2f}
          <span style="font-size:12px;color:{_MUTED};"> ({sig['sl_pct']:+.1f}%)</span>
        </td>
      </tr>
      <tr>
        <td style="padding:6px 16px;font-size:13px;color:{_MUTED};">Take Profit</td>
        <td style="padding:6px 16px;text-align:right;font-size:14px;color:{_GREEN};font-weight:600;">
          ₹{sig['tp']:,.2f}
          <span style="font-size:12px;color:{_MUTED};"> ({sig['tp_pct']:+.1f}%)</span>
        </td>
      </tr>
      <tr>
        <td style="padding:6px 16px;font-size:13px;color:{_MUTED};">Risk / Reward</td>
        <td style="padding:6px 16px;text-align:right;font-size:13px;color:{_WHITE};">
          1 : {sig['rr']}
        </td>
      </tr>
      <tr>
        <td style="padding:6px 16px 2px;font-size:13px;color:{_MUTED};">ATR (volatility)</td>
        <td style="padding:6px 16px 2px;text-align:right;font-size:13px;color:{_WHITE};">
          ₹{sig['atr']:,.2f}
        </td>
      </tr>

      <!-- Divider -->
      <tr><td colspan="2" style="padding:0 16px;">
        <hr style="border:none;border-top:1px solid #4a5568;margin:8px 0;">
      </td></tr>

      <!-- Indicators -->
      <tr>
        <td style="padding:4px 16px;font-size:12px;color:{_MUTED};">ADX</td>
        <td style="padding:4px 16px;text-align:right;font-size:12px;color:{_WHITE};">
          {sig['adx']}
          <span style="color:{_GREEN if sig['adx'] >= 20 else _ORANGE};"> ✅</span>
          <span style="color:{_MUTED};">({'Strong' if sig['adx'] >= 30 else 'Moderate' if sig['adx'] >= 20 else 'Weak'} trend)</span>
        </td>
      </tr>
      <tr>
        <td style="padding:4px 16px;font-size:12px;color:{_MUTED};">RSI</td>
        <td style="padding:4px 16px;text-align:right;font-size:12px;color:{_WHITE};">
          {sig['rsi']}
          <span style="color:{_MUTED};">({'Overbought' if sig['rsi'] >= 70 else 'Oversold' if sig['rsi'] <= 30 else 'Neutral zone'})</span>
        </td>
      </tr>
      <tr>
        <td style="padding:4px 16px;font-size:12px;color:{_MUTED};">Volume</td>
        <td style="padding:4px 16px;text-align:right;font-size:12px;color:{_WHITE};">
          {sig['vol_ratio']:.2f}× avg
          <span style="color:{_GREEN};"> ✅</span>
        </td>
      </tr>
      <tr>
        <td style="padding:4px 16px;font-size:12px;color:{_MUTED};">EMA mesh</td>
        <td style="padding:4px 16px;text-align:right;font-size:12px;color:{mesh_color};">
          {mesh_label}
        </td>
      </tr>
      <tr>
        <td style="padding:4px 16px 12px;font-size:12px;color:{_MUTED};">Weekly EMA 50</td>
        <td style="padding:4px 16px 12px;text-align:right;font-size:12px;color:{_WHITE};">
          {weekly_icon} {weekly_label}
        </td>
      </tr>
      <tr>
        <td style="padding:4px 16px 10px;font-size:12px;color:{_MUTED};">Sector</td>
        <td style="padding:4px 16px 10px;text-align:right;">
          <span style="background:#2c5282;color:#bee3f8;padding:2px 9px;border-radius:10px;
                font-size:11px;font-weight:600;">{sig.get('sector','Other')}</span>
        </td>
      </tr>

      <!-- EMA levels for chart reference -->
      <tr>
        <td colspan="2" style="padding:6px 16px 12px;">
          <span style="font-size:11px;color:{_MUTED};">
            EMA21: ₹{sig['ema21']:,.2f} &nbsp;·&nbsp;
            EMA50: ₹{sig['ema50']:,.2f} &nbsp;·&nbsp;
            EMA200: ₹{sig['ema200']:,.2f}
          </span>
        </td>
      </tr>
    </table>"""


# ── Sector distribution bar chart ─────────────────────────────────────────────
def _sector_chart(signals: list[dict]) -> str:
    """
    Build an HTML horizontal bar chart showing how many signals
    (LONG vs SHORT) came from each sector.
    Returns an empty string if there are no signals.
    """
    if not signals:
        return ""

    from collections import Counter
    long_counts:  Counter = Counter()
    short_counts: Counter = Counter()
    for s in signals:
        sector = s.get("sector", "Other")
        if s["direction"] == "LONG":
            long_counts[sector] += 1
        else:
            short_counts[sector] += 1

    all_sectors = sorted(
        set(long_counts) | set(short_counts),
        key=lambda sec: -(long_counts[sec] + short_counts[sec]),
    )
    max_total = max(long_counts[sec] + short_counts[sec] for sec in all_sectors) or 1

    rows = []
    for sec in all_sectors:
        l = long_counts[sec]
        s = short_counts[sec]
        total = l + s
        bar_pct = int(total / max_total * 100)
        long_pct  = int(l / total * 100) if total else 0
        short_pct = 100 - long_pct

        badge_long  = (f'<span style="color:{_GREEN};font-size:11px;">▲{l}L</span> '
                       if l else "")
        badge_short = (f'<span style="color:{_RED};font-size:11px;">▼{s}S</span>'
                       if s else "")

        # Segmented bar: green portion = longs, red portion = shorts
        green_w = int(bar_pct * long_pct / 100)
        red_w   = bar_pct - green_w

        rows.append(f"""
        <tr>
          <td style="width:38%;padding:5px 10px 5px 0;font-size:12px;
                     color:#e2e8f0;white-space:nowrap;">{sec}</td>
          <td style="width:48%;padding:5px 4px;">
            <div style="display:flex;height:12px;border-radius:6px;overflow:hidden;
                        background:#2d3748;width:100%;">
              {'<div style="width:'+str(green_w)+'%;background:'+_GREEN+';"></div>' if green_w else ''}
              {'<div style="width:'+str(red_w)+'%;background:'+_RED+';"></div>' if red_w else ''}
            </div>
          </td>
          <td style="width:14%;padding:5px 0 5px 6px;font-size:11px;
                     white-space:nowrap;">{badge_long}{badge_short}</td>
        </tr>""")

    rows_html = "".join(rows)
    total_signals = len(signals)
    long_total  = sum(1 for s in signals if s["direction"] == "LONG")
    short_total = total_signals - long_total

    return f"""
    <!-- ── SECTOR DISTRIBUTION ───────────────────────────────── -->
    <table width="100%" cellpadding="0" cellspacing="0"
           style="background:{_CARD};border-radius:10px;margin-bottom:24px;
                  border-left:5px solid {_BLUE};overflow:hidden;">
      <tr>
        <td colspan="3" style="padding:12px 16px 6px;background:{_DARK};">
          <span style="font-size:15px;font-weight:700;color:{_WHITE};">
            🗂 &nbsp;Sector Distribution
          </span>
          <span style="float:right;font-size:12px;color:{_MUTED};">
            <span style="color:{_GREEN};">▲ {long_total} Long</span>
            &nbsp;·&nbsp;
            <span style="color:{_RED};">▼ {short_total} Short</span>
          </span>
        </td>
      </tr>
      <tr>
        <td colspan="3" style="padding:2px 16px 10px;">
          <table width="100%" cellpadding="0" cellspacing="0">
            {rows_html}
          </table>
        </td>
      </tr>
    </table>"""


# ── Full email HTML ────────────────────────────────────────────────────────────
def _build_html(signals: list[dict], scan_date: str) -> str:
    n = len(signals)
    headline = (
        f"{n} Signal{'s' if n != 1 else ''} Found — {scan_date}"
        if n > 0 else
        f"No Signals Today — {scan_date}"
    )
    subline = (
        f"NSE swing screener detected {n} trade setup{'s' if n != 1 else ''}. "
        "Review each card, open the chart, and decide manually."
        if n > 0 else
        "The screener ran successfully. No setups met the entry criteria today."
    )

    sector_chart_html = _sector_chart(signals)
    cards_html = "".join(_signal_card(s) for s in signals) if n > 0 else f"""
    <p style="color:{_MUTED};text-align:center;padding:32px 0;font-size:15px;">
      📭 &nbsp; No trade setups today. The market is either choppy or no stocks
      met all entry conditions simultaneously.
    </p>"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0f1117;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:24px 12px;">
      <table width="620" cellpadding="0" cellspacing="0">

        <!-- Header -->
        <tr>
          <td style="background:#1a202c;border-radius:12px 12px 0 0;
                     padding:24px 28px;border-bottom:2px solid {_BLUE};">
            <div style="font-size:22px;font-weight:700;color:{_WHITE};">
              📊 &nbsp; NSE Swing Screener
            </div>
            <div style="font-size:14px;color:{_MUTED};margin-top:4px;">
              Daily signal alert — strategy: EMA + RSI + ADX + Volume
            </div>
          </td>
        </tr>

        <!-- Sub-header -->
        <tr>
          <td style="background:#2d3748;padding:14px 28px;">
            <div style="font-size:17px;font-weight:600;color:{_WHITE if n > 0 else _MUTED};">
              {headline}
            </div>
            <div style="font-size:13px;color:{_MUTED};margin-top:4px;">{subline}</div>
          </td>
        </tr>

        <!-- Sector chart + Cards -->
        <tr>
          <td style="padding:20px 8px;">
            {sector_chart_html}
            {cards_html}
          </td>
        </tr>

        <!-- Risk disclaimer -->
        <tr>
          <td style="background:#1a202c;border-radius:0 0 12px 12px;
                     padding:18px 28px;">
            <p style="font-size:11px;color:#718096;margin:0;line-height:1.6;">
              <strong style="color:{_MUTED};">Reminder:</strong>
              These are algorithmically screened setups based on historical backtest
              parameters.  <strong>Always open the chart</strong>, confirm with your own
              technical analysis, and apply position sizing appropriate for your risk
              tolerance.  Past performance does not guarantee future results.
              SL and TP levels are calculated at today's close — actual entry tomorrow
              may differ.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ── Send function ──────────────────────────────────────────────────────────────
def send_alert(signals: list[dict]) -> bool:
    """
    Send the daily alert email.

    Returns True on success, False on failure (error is printed, not raised).
    """
    if not GMAIL_SENDER or not GMAIL_APP_PASS or not ALERT_RECIPIENTS:
        print(
            "[NOTIFIER] Gmail credentials not configured.\n"
            "  Set GMAIL_SENDER, GMAIL_APP_PASS, ALERT_RECIPIENTS in your .env file."
        )
        return False

    scan_date = datetime.now().strftime("%d %b %Y")
    n         = len(signals)
    subject   = (
        f"[NSE Screener] {n} Signal{'s' if n != 1 else ''} — {scan_date}"
        if n > 0 else
        f"[NSE Screener] No signals — {scan_date}"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_SENDER
    msg["To"]      = ", ".join(ALERT_RECIPIENTS)

    # Plain-text fallback
    plain_lines = [f"NSE Swing Screener — {scan_date}", ""]
    if signals:
        for s in signals:
            plain_lines += [
                f"{s['emoji']} {s['ticker']}  |  {s['direction']}  |  {s['label']}  |  Score {s['score']}/6  |  {s.get('sector','Other')}",
                f"   Entry ₹{s['entry']:,.2f}   SL ₹{s['sl']:,.2f} ({s['sl_pct']:+.1f}%)   TP ₹{s['tp']:,.2f} ({s['tp_pct']:+.1f}%)",
                f"   R/R 1:{s['rr']}   ADX {s['adx']}   RSI {s['rsi']}   Vol {s['vol_ratio']:.1f}×",
                "",
            ]
    else:
        plain_lines.append("No trade setups today.")

    msg.attach(MIMEText("\n".join(plain_lines), "plain"))
    msg.attach(MIMEText(_build_html(signals, scan_date), "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_SENDER, GMAIL_APP_PASS)
            server.sendmail(GMAIL_SENDER, ALERT_RECIPIENTS, msg.as_string())
        print(f"[NOTIFIER] Email sent → {', '.join(ALERT_RECIPIENTS)}  ({n} signal(s))")
        return True
    except smtplib.SMTPAuthenticationError:
        print(
            "[NOTIFIER] Gmail authentication failed.\n"
            "  Make sure you are using a Gmail App Password, not your normal password.\n"
            "  Generate one at: myaccount.google.com/apppasswords"
        )
        return False
    except Exception as e:
        print(f"[NOTIFIER] Failed to send email: {e}")
        return False
