import streamlit as st
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(
    page_title="NSE Live Screener Engine",
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
# DIRECT NSE LIVE DATA ENGINE (NO BROKER SDK)
# -------------------------------------------------------------------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/"
}

@st.cache_resource(ttl=120)
def get_nse_session():
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        session.get("https://www.nseindia.com", timeout=5)
    except Exception:
        pass
    return session

WATCHLIST = ["TBZ", "RESPONIND", "WONDERLA", "RELIANCE", "BPCL", "IOC", "TATASTEEL"]

def fetch_nse_ticker(symbol):
    session = get_nse_session()
    url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
    
    try:
        res = session.get(url, timeout=5)
        if res.status_code != 200:
            session = get_nse_session()
            res = session.get(url, timeout=5)
            
        data = res.json()
        price_info = data.get('priceInfo', {})
        
        ltp = float(price_info.get('lastPrice', 0))
        day_open = float(price_info.get('open', 0))
        day_high = float(price_info.get('intraDayHighLow', {}).get('max', 0))
        pdc = float(price_info.get('previousClose', 0))
        total_vol = float(price_info.get('totalTradedVolume', 0))
        
        vwap = float(price_info.get('vwap', ltp))
        day_gain_pct = float(price_info.get('pChange', 0))
        
        # Volume metric calculations from live feed
        avg_vol_est = total_vol / 375 if total_vol > 0 else 1.0
        rvol = (total_vol / 100) / avg_vol_est if avg_vol_est > 0 else 1.0
        
        turnover_est = ltp * (total_vol / 375)
        open_gap_pct = ((day_open - pdc) / pdc) * 100 if pdc > 0 else 0
        max_gain_pct = ((day_high - day_open) / day_open) * 100 if day_open > 0 else 0

        # Tier Screening Signals
        tier1_signal = (1.0 <= open_gap_pct <= 4.0) and (day_gain_pct >= 3.0) and (rvol >= 2.0)
        tier2_signal = (rvol >= 2.5) and (turnover_est >= 500_000)
        tier3_signal = (max_gain_pct >= 8.0) and (ltp < vwap * 0.99)
        tier4_signal = (rvol >= 3.0) and (ltp < day_open * 0.98)

        capital_deployment = ((total_vol / 375) * ltp * 0.0025) / 5

        return {
            "Symbol": symbol,
            "LTP": round(ltp, 2),
            "Day Gain %": f"{day_gain_pct:+.2f}%",
            "VWAP": round(vwap, 2),
            "Gap %": f"{open_gap_pct:+.2f}%",
            "Total Vol": f"{total_vol:,.0f}",
            "Max Deploy (₹)": f"₹{capital_deployment:,.0f}",
            "Tier 1 (TBZ)": "🟢 TRIGGERED" if tier1_signal else "-",
            "Tier 2 (RESPONIND)": "⚡ STEALTH" if tier2_signal else "-",
            "Tier 3 (Pump Short)": "🔴 COLLAPSE" if tier3_signal else "-",
            "Tier 4 (Wonderla)": "🚨 SHOCK DUMP" if tier4_signal else "-"
        }
    except Exception:
        return None

# -------------------------------------------------------------------
# APP DISPLAY ENGINE
# -------------------------------------------------------------------
st.title("⚡ Direct NSE Live Market Engine")

if st.button("🔄 Refresh Data", use_container_width=True):
    st.cache_data.clear()

results = []
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(fetch_nse_ticker, sym) for sym in WATCHLIST]
    for future in futures:
        res = future.result()
        if res:
            results.append(res)

if results:
    st.dataframe(pd.DataFrame(results), use_container_width=True)
else:
    st.warning("Scanning NSE live stream... Click Refresh.")
