import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components
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

def fetch_ticker_metrics(symbol):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    
    # Primary Endpoint: Yahoo Spark
    url_spark = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={symbol}.NS&range=1d&interval=1m"
    # Fallback Endpoint: Direct Chart API
    url_chart = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?range=1d&interval=1m"
    
    data = None
    try:
        res = requests.get(url_spark, headers=headers, timeout=4)
        if res.status_code == 200:
            data = res.json()['spark']['result'][0]['response'][0]
    except Exception:
        pass

    if not data:
        try:
            res = requests.get(url_chart, headers=headers, timeout=4)
            if res.status_code == 200:
                data = res.json()['chart']['result'][0]
        except Exception:
            return None

    if not data:
        return None

    try:
        meta = data.get('meta', {})
        indicators = data.get('indicators', {}).get('quote', [{}])[0]
        
        ltp = float(meta.get('regularMarketPrice', 0))
        pdc = float(meta.get('chartPreviousClose', ltp))
        day_open = float(meta.get('regularMarketDayOpen', ltp))
        day_high = float(meta.get('regularMarketDayHigh', ltp))
        
        volumes = [v for v in indicators.get('volume', []) if v is not None]
        closes = [c for c in indicators.get('close', []) if c is not None]
        opens = [o for o in indicators.get('open', []) if o is not None]
        
        curr_1m_vol = float(volumes[-1]) if volumes else 1.0
        total_vol = float(sum(volumes)) if volumes else 1.0
        
        avg_1m_vol = float(pd.Series(volumes).tail(20).mean()) if len(volumes) >= 20 else (total_vol / max(len(volumes), 1))
        rvol = curr_1m_vol / avg_1m_vol if avg_1m_vol > 0 else 1.0
        
        turnover_1m = ltp * curr_1m_vol
        vwap = sum(c * v for c, v in zip(closes, volumes)) / sum(volumes) if (volumes and sum(volumes) > 0) else ltp

        candle1_open = float(opens[0]) if opens else day_open
        candle1_close = float(closes[0]) if closes else day_open
        candle1_change_pct = ((candle1_close - candle1_open) / candle1_open) * 100 if candle1_open > 0 else 0
        
        open_gap_pct = ((candle1_open - pdc) / pdc) * 100 if pdc > 0 else 0
        day_gain_pct = ((ltp - pdc) / pdc) * 100 if pdc > 0 else 0
        max_gain_pct = ((day_high - candle1_open) / candle1_open) * 100 if candle1_open > 0 else 0

        # -------------------------------------------------------------------
        # STRICT STRATEGY TIERS (UNTOUCHED LOGIC)
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
            "Turnover (1m)": f"₹{turnover_1m / 100000:.1f}L",
            "Max Deploy (₹)": f"₹{capital_deployment:,.0f}",
            "Tier 1 (TBZ)": "🟢 TRIGGERED" if tier1_signal else "-",
            "Tier 2 (RESPONIND)": "⚡ STEALTH" if tier2_signal else "-",
            "Tier 3 (Pump Short)": "🔴 COLLAPSE" if tier3_signal else "-",
            "Tier 4 (Wonderla)": "🚨 SHOCK DUMP" if tier4_signal else "-",
            "Triggered": is_triggered
        }
    except Exception:
        return None

# -------------------------------------------------------------------
# STREAMLIT UI & AUDIO ENGINE
# -------------------------------------------------------------------
st.title("⚡ Institutional Live Screener Engine")

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
    df = pd.DataFrame(results)
    
    if any(df["Triggered"]):
        play_alert_sound()
        st.toast("🚨 ALERT TRIGGERED ON WATCHLIST!", icon="🔔")

    st.dataframe(df.drop(columns=["Triggered"]), use_container_width=True)
else:
    st.warning("Market feed unreachable or market is closed. Click 'Refresh Data' to try again.")
