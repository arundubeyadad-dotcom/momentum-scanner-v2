import streamlit as st
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor

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

WATCHLIST = ["TBZ", "RESPONIND", "WONDERLA", "RELIANCE", "BPCL", "IOC", "TATASTEEL"]

def fetch_ticker_metrics(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval=1m&range=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=4)
        data = res.json()['chart']['result'][0]
        
        meta = data['meta']
        ltp = float(meta['regularMarketPrice'])
        pdc = float(meta['chartPreviousClose'])
        day_open = float(meta.get('regularMarketDayOpen', ltp))
        day_high = float(meta.get('regularMarketDayHigh', ltp))
        
        quotes = data['indicators']['quote'][0]
        volumes = [v for v in quotes.get('volume', []) if v is not None]
        total_vol = sum(volumes) if volumes else 1.0
        curr_1m_vol = float(volumes[-1]) if volumes else 1.0
        
        avg_1m_vol = float(pd.Series(volumes).tail(20).mean()) if len(volumes) >= 20 else (total_vol / len(volumes) if volumes else 1.0)
        rvol = curr_1m_vol / avg_1m_vol if avg_1m_vol > 0 else 1.0
        
        turnover_1m = ltp * curr_1m_vol
        
        closes = [c for c in quotes.get('close', []) if c is not None]
        vwap = sum(c * v for c, v in zip(closes, volumes)) / sum(volumes) if sum(volumes) > 0 else ltp

        open_gap_pct = ((day_open - pdc) / pdc) * 100 if pdc > 0 else 0
        candle1_open = float(quotes.get('open', [day_open])[0] or day_open)
        candle1_close = float(quotes.get('close', [day_open])[0] or day_open)
        candle1_change_pct = ((candle1_close - candle1_open) / candle1_open) * 100 if candle1_open > 0 else 0
        
        day_gain_pct = ((ltp - pdc) / pdc) * 100 if pdc > 0 else 0
        max_gain_pct = ((day_high - day_open) / day_open) * 100 if day_open > 0 else 0

        # -------------------------------------------------------------------
        # EXACT PRESERVED STRATEGY PARAMETERS
        # -------------------------------------------------------------------
        tier1_signal = (1.0 <= open_gap_pct <= 4.0) and (candle1_change_pct >= 3.0) and (rvol >= 5.0)
        tier2_signal = (rvol >= 3.0) and (turnover_1m >= 1_000_000)
        tier3_signal = (max_gain_pct >= 10.0) and (ltp < vwap * 0.99)
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

# -------------------------------------------------------------------
# STREAMLIT UI
# -------------------------------------------------------------------
st.title("⚡ Direct Live Market Engine")

if st.button("🔄 Refresh Data", use_container_width=True):
    st.cache_data.clear()

results = []
with ThreadPoolExecutor(max_workers=7) as executor:
    futures = [executor.submit(fetch_ticker_metrics, sym) for sym in WATCHLIST]
    for future in futures:
        res = future.result()
        if res:
            results.append(res)

if results:
    st.dataframe(pd.DataFrame(results), use_container_width=True)
else:
    st.info("Market feed scanning...")
