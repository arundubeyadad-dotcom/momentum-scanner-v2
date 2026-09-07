import streamlit as st
import pandas as pd
from dhanhq import dhanhq
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time

st.set_page_config(
    page_title="Institutional Stealth Engine",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    .stMetric { background-color: #1e222d; padding: 10px; border-radius: 8px; }
    h3 { font-size: 1.2rem !important; }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------
# HARDCODED CREDENTIALS
# -------------------------------------------------------------------
CLIENT_ID = "1102152375"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJ1c2VyUmVaw9uUijoiUjEiLCJpc3MiOiJkaGFuR3UIIwicGFydG5lckIJOiIwiZXhwIjoxNzg4ODQxMjA1LCJpYXQiOjE3MDg3NTQ4MDUsInRva2Vu2Q2uc3VtZXJXB1IjoiU0VMRIisInd1Ymhvb2tvCwmwi0iIIlCJkaGFuFuQ2xpZW50SWQioiIxMTAyMTYmZC1In0.2_sopwOWgEc-ABkluQms4EVW31Q00BQXBoBGI0ovu8W-LIAvc1QV5bniIZo6hM_eU4Up_CNhrjev5gR19m0s8Q"

try:
    dhan = dhanhq(client_id=CLIENT_ID, access_token=ACCESS_TOKEN)
except Exception as e:
    st.error(f"Connection Error: {e}")
    st.stop()

DHAN_WATCHLIST = {
    "TBZ": "14366",
    "RESPONIND": "11915",
    "WONDERLA": "18652",
    "RELIANCE": "2885",
    "BPCL": "526",
    "IOC": "1624",
    "TATASTEEL": "3499"
}

def analyze_ticker(symbol, security_id):
    try:
        data = dhan.historical_minute_charts(
            security_id=security_id,
            exchange_segment="NSE_EQ",
            instrument_type="EQUITY",
            from_date=datetime.now().strftime('%Y-%m-%d'),
            to_date=datetime.now().strftime('%Y-%m-%d')
        )

        if data.get('status') != 'success' or not data.get('data'):
            return None

        df_1m = pd.DataFrame(data['data'])
        if df_1m.empty:
            return None

        ltp = float(df_1m['close'].iloc[-1])
        day_open = float(df_1m['open'].iloc[0])
        day_high = float(df_1m['high'].max())
        pdc = float(df_1m['open'].iloc[0])
        
        curr_1m_vol = float(df_1m['volume'].iloc[-1])
        avg_1m_vol = float(df_1m['volume'].tail(20).mean())
        rvol = curr_1m_vol / avg_1m_vol if avg_1m_vol > 0 else 1.0
        
        turnover_1m = ltp * curr_1m_vol
        
        v_sum = df_1m['volume'].sum()
        vwap = (df_1m['close'] * df_1m['volume']).sum() / v_sum if v_sum > 0 else ltp

        open_gap_pct = ((day_open - pdc) / pdc) * 100 if pdc > 0 else 0
        candle1_change_pct = ((float(df_1m['close'].iloc[0]) - day_open) / day_open) * 100
        day_gain_pct = ((ltp - pdc) / pdc) * 100 if pdc > 0 else 0
        max_gain_pct = ((day_high - day_open) / day_open) * 100

        tier1_signal = (1.0 <= open_gap_pct <= 4.0) and (candle1_change_pct >= 3.0) and (rvol >= 5.0)
        tier2_signal = (rvol >= 3.0) and (turnover_1m >= 1_000_000)
        tier3_signal = (max_gain_pct >= 10.0) and (ltp < vwap * 0.99) and (datetime.now().time() <= time(10, 30))
        tier4_signal = (rvol >= 4.0) and (ltp < day_open * 0.975)

        capital_deployment = (curr_1m_vol * ltp * 0.0025) / 5

        return {
            "Symbol": symbol,
            "LTP": round(ltp, 2),
            "Day Gain %": f"{day_gain_pct:+.2f}%",
            "RVOL": f"{rvol:.1f}x",
            "VWAP": round(vwap, 2),
            "Turnover (1m)": f"₹{turnover_1m / 100000:.1f}L",
            "Max Deploy (₹)": f"₹{capital_deployment:,.0f}",
            "Tier 1 (TBZ)": "🟢 TRIGGERED" if tier1_signal else "-",
            "Tier 2 (RESPONIND)": "⚡ STEALTH" if tier2_signal else "-",
            "Tier 3 (Pump Short)": "🔴 COLLAPSE" if tier3_signal else "-",
            "Tier 4 (Wonderla)": "🚨 SHOCK DUMP" if tier4_signal else "-"
        }
    except Exception:
        return None

st.title("⚡ Direct Dhan Live Market Engine")

if st.button("🔄 Refresh Live Ticks", use_container_width=True):
    st.cache_data.clear()

triggered_stocks = []
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(analyze_ticker, sym, sec_id) for sym, sec_id in DHAN_WATCHLIST.items()]
    for future in futures:
        res = future.result()
        if res:
            triggered_stocks.append(res)

if triggered_stocks:
    st.dataframe(pd.DataFrame(triggered_stocks), use_container_width=True)
else:
    st.info("Scanning live market...")
