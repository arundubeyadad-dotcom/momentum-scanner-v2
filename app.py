import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(
    page_title="Universal Tier Momentum Engine",
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
# DHAN HQ REST API CREDENTIALS
# -------------------------------------------------------------------
CLIENT_ID = "1102152375"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." # Apna full token daal do

# NSE Security IDs Map
DHAN_WATCHLIST = {
    "TBZ": "14366",
    "RESPONIND": "11915",
    "WONDERLA": "18652",
    "RELIANCE": "2885",
    "BPCL": "526",
    "IOC": "1624",
    "TATASTEEL": "3499"
}

def play_alert_sound():
    audio_script = """
        <script>
        var ctx = new (window.AudioContext || window.webkitAudioContext)();
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.type = "sine";
        osc.frequency.value = 880;
        gain.gain.setValueAtTime(0.3, ctx.currentTime);
        osc.start();
        osc.stop(ctx.currentTime + 0.4);
        </script>
    """
    components.html(audio_script, height=0, width=0)

def fetch_dhan_intraday_data(symbol, security_id):
    headers = {
        "access-token": ACCESS_TOKEN,
        "client-id": CLIENT_ID,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Dhan HQ REST API v2 Direct Endpoint
    url = "https://api.dhan.co/v2/charts/intraday"
    payload = {
        "securityId": str(security_id),
        "exchangeSegment": "NSE_EQ",
        "instrumentType": "EQUITY",
        "interval": "1"
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        if res.status_code != 200:
            return None
            
        json_data = res.json()
        if "close" not in json_data or not json_data["close"]:
            return None

        closes = json_data["close"]
        opens = json_data["open"]
        highs = json_data["high"]
        volumes = json_data["volume"]

        if not volumes or len(volumes) < 2:
            return None

        ltp = float(closes[-1])
        day_open = float(opens[0])
        day_high = max([float(h) for h in highs])
        
        # PDC proxy from candle 1 open if historical PDC unavailable
        pdc = float(opens[0])

        curr_1m_vol = float(volumes[-1])
        total_vol = float(sum([float(v) for v in volumes]))

        # RVOL against 20-candle moving average
        vol_series = pd.Series([float(v) for v in volumes])
        avg_1m_vol = float(vol_series.tail(20).mean()) if len(vol_series) >= 20 else (total_vol / max(len(vol_series), 1))
        rvol = curr_1m_vol / avg_1m_vol if avg_1m_vol > 0 else 1.0

        turnover_1m = ltp * curr_1m_vol
        vwap = sum(float(c) * float(v) for c, v in zip(closes, volumes)) / total_vol if total_vol > 0 else ltp

        candle1_open = float(opens[0])
        candle1_close = float(closes[0])
        candle1_change_pct = ((candle1_close - candle1_open) / candle1_open) * 100 if candle1_open > 0 else 0

        open_gap_pct = ((candle1_open - pdc) / pdc) * 100 if pdc > 0 else 0
        day_gain_pct = ((ltp - pdc) / pdc) * 100 if pdc > 0 else 0
        max_gain_pct = ((day_high - candle1_open) / candle1_open) * 100 if candle1_open > 0 else 0

        # -------------------------------------------------------------------
        # EXACT PRESERVED STRATEGY TIERS
        # -------------------------------------------------------------------
        tier1_signal = (1.0 <= open_gap_pct <= 4.0) and (candle1_change_pct >= 3.0) and (rvol >= 5.0)
        tier2_signal = (rvol >= 3.0)
        tier3_signal = (max_gain_pct >= 10.0) and (ltp < vwap * 0.99)
        tier4_signal = (rvol >= 4.0) and (ltp < candle1_open * 0.975)

        is_triggered = tier1_signal or tier2_signal or tier3_signal or tier4_signal
        capital_deployment = (curr_1m_vol * ltp * 0.0025) / 5

        return {
            "Symbol": symbol,
            "LTP": round(ltp, 2),
            "Day Gain %": f"{day_gain_pct:+.2f}%",
            "RVOL": f"{rvol:.1f}x",
            "VWAP": round(vwap, 2),
            "1m Turnover": f"₹{turnover_1m / 100000:.1f}L",
            "Max Deploy (₹)": f"₹{capital_deployment:,.0f}",
            "Tier 1 (Gap Momentum)": "🟢 TRIGGERED" if tier1_signal else "-",
            "Tier 2 (Stealth Expansion)": "⚡ STEALTH" if tier2_signal else "-",
            "Tier 3 (Pump & Collapse)": "🔴 COLLAPSE" if tier3_signal else "-",
            "Tier 4 (Shock Dump)": "🚨 SHOCK DUMP" if tier4_signal else "-",
            "Triggered": is_triggered
        }
    except Exception:
        return None

# -------------------------------------------------------------------
# STREAMLIT UI ENGINE
# -------------------------------------------------------------------
st.title("⚡ Dynamic Multi-Tier Strategy Screener (Dhan REST)")

if st.button("🔄 Refresh Data", use_container_width=True):
    st.cache_data.clear()

results = []
with ThreadPoolExecutor(max_workers=7) as executor:
    futures = [executor.submit(fetch_dhan_intraday_data, sym, sec_id) for sym, sec_id in DHAN_WATCHLIST.items()]
    for future in futures:
        res = future.result()
        if res:
            results.append(res)

if results:
    df = pd.DataFrame(results)
    
    if any(df["Triggered"]):
        play_alert_sound()
        st.toast("🚨 STRATEGY TRIGGER DETECTED!", icon="🔔")

    st.dataframe(df.drop(columns=["Triggered"]), use_container_width=True)
else:
    st.warning("Connecting to Dhan Direct REST Engine...")
