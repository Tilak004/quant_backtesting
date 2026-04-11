@echo off
:: ─────────────────────────────────────────────────────────────────────────────
:: run_screener.bat
:: Launches the NSE Swing Screener scheduler silently in the background.
:: Windows Task Scheduler calls this file automatically at login.
:: ─────────────────────────────────────────────────────────────────────────────

cd /d "C:\Users\shast\Desktop\Quant backtesting\quant_backtest"
start "NSE Screener" /min pythonw bot\scheduler.py
