import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="FinOptic Vault", page_icon="📈", layout="wide")

# --- CUSTOM CSS: THE FIX FOR BUTTON VISIBILITY ---
st.markdown("""
    <style>
    /* 1. Main Dashboard - Pure Black */
    .stApp { background-color: #000000 !important; }
    
    /* 2. Global Text (Skin Color) */
    h1, h2, h3, h4, th, td, p, .stMarkdown, .stSubheader, .stCaption {
        color: #FFEBCD !important; 
    }

    /* 3. Sidebar (White) */
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {
        color: #000000 !important; font-weight: 700 !important;
    }

    /* 4. BUTTONS: Gold Background, Black Text */
    /* This targets ALL buttons: Update Vault, Add Goal, and Delete */
    div.stButton > button, button[kind="primaryFormSubmit"] {
        background-color: #D4AF37 !important; /* Gold Background */
        color: #000000 !important;           /* BLACK TEXT (For Add Goal & Update Vault) */
        border: 2px solid #FFFFFF !important;
        font-weight: 900 !important;
        width: 100% !important;
        border-radius: 8px !important;
        height: 3em !important;
    }
    
    /* Hover effect */
    div.stButton > button:hover, button[kind="primaryFormSubmit"]:hover {
        background-color: #000000 !important; 
        color: #D4AF37 !important; 
        border-color: #D4AF37 !important;
    }

    /* 5. Metrics */
    [data-testid="stMetricValue"] { color: #D4AF37 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- DATA FETCHING ---
CACHE_FILE = "last_rates.csv"
def get_live_prices():
    try:
        tickers = yf.download(["GC=F", "SI=F", "INR=X"], period="1d", interval="1m", progress=False)['Close']
        u_i = tickers["INR=X"].dropna().iloc[-1]
        g_p = (tickers["GC=F"].dropna().iloc[-1] / 31.1) * u_i
        s_p = (tickers["SI=F"].dropna().iloc[-1] / 31.1) * u_i
        pd.DataFrame({"r": ["g", "s", "u"], "v": [g_p, s_p, u_i]}).to_csv(CACHE_FILE, index=False)
        return g_p, s_p, u_i, "Online"
    except:
        if os.path.exists(CACHE_FILE):
            df = pd.read_csv(CACHE_FILE); r = dict(zip(df.r, df.v))
            return r['g'], r['s'], r['u'], "Offline"
        return 6300.0, 78.0, 83.5, "Offline"

g_rate, s_rate, u_rate, status = get_live_prices()

# --- SESSION STATE ---
if 'goals_list' not in st.session_state: st.session_state.goals_list = []
if 'prev_total' not in st.session_state: st.session_state.prev_total = 0.0

# --- SIDEBAR (Update Vault Button here) ---
with st.sidebar:
    st.header("📂 Asset Input")
    upi = st.number_input("UPI / Cash (INR)", min_value=0.0, format="%.2f", step=1000.0)
    g_g = st.number_input("Gold (grams)", min_value=0.0, format="%.2f", step=1.0)
    s_g = st.number_input("Silver (grams)", min_value=0.0, format="%.2f", step=10.0)
    f_usd = st.number_input("Forex (USD)", min_value=0.0, format="%.2f", step=50.0)
    
    if st.button("🔄 Update Vault"):
        st.session_state.prev_total = upi + (g_g * g_rate) + (s_g * s_rate) + (f_usd * u_rate)
        st.toast("Vault Updated!")
        st.rerun()

# --- CALCULATIONS ---
g_val, s_val, f_val = g_g * g_rate, s_g * s_rate, f_usd * u_rate
c_total = upi + g_val + s_val + f_val
growth_val = c_total - st.session_state.prev_total
growth_pct = (growth_val / st.session_state.prev_total * 100) if st.session_state.prev_total > 0 else 0.0

# --- MAIN UI ---
st.title("📈 FinOptic: Strategic Wealth Vault")
m1, m2 = st.columns(2)
m1.metric("Total Net Worth", f"₹{c_total:,.2f}")
with m2:
    st.write("### Net Growth (%)")
    clr = "growth-positive" if growth_val >= 0 else "growth-negative"
    st.markdown(f'<span class="{clr}">{growth_pct:+.2f}%</span>', unsafe_allow_html=True)

st.divider()

# Charts
col_a, col_b = st.columns([0.4, 0.6])
asset_df = pd.DataFrame({"Asset": ["UPI", "Gold", "Silver", "Forex"], "Value (INR)": [upi, g_val, s_val, f_val]})
with col_a:
    st.subheader("📋 Asset Summary")
    st.table(asset_df.style.format({"Value (INR)": "₹{:,.2f}"}))
with col_b:
    st.subheader("📊 Allocation Breakdown")
    fig = px.bar(asset_df, x="Asset", y="Value (INR)", color="Asset", color_discrete_sequence=["#D4AF37", "#C0C0C0", "#E5E4E2", "#008080"])
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#FFEBCD")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- GOAL TRACKER (Add Goal Button here) ---
st.subheader("🎯 Purchase Goals & Liquidity Reserve")
with st.form("goal_form", clear_on_submit=True):
    gc1, gc2, gc3 = st.columns([2, 1, 1])
    name_in = gc1.text_input("Item Name")
    cost_in = gc2.number_input("Base Cost (INR)", min_value=0.0)
    res_in = gc3.slider("Liquidity Reserve (%)", 0, 100, 20)
    
    if st.form_submit_button("Add Goal"):
        if name_in and cost_in > 0:
            target_val = cost_in * (1 + (res_in/100))
            st.session_state.goals_list.append({"name": name_in, "target": target_val, "base": cost_in, "reserve_pct": res_in})
            st.rerun()

for i, goal in enumerate(st.session_state.goals_list):
    with st.container(border=True):
        col_info, col_del = st.columns([0.85, 0.15])
        with col_info:
            st.write(f"### {goal['name']}")
            st.write(f"**Target:** ₹{goal['target']:,.2f}")
            st.progress(min(c_total / goal['target'], 1.0) if goal['target'] > 0 else 0.0)
        with col_del:
            if st.button("🗑️ Delete", key=f"del_{i}"):
                st.session_state.goals_list.pop(i)
                st.rerun()
