import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import os
from datetime import datetime

# --- 1. CONFIGURATION & STYLING ---
st.set_page_config(page_title="FinOptic: Private Wealth Mirror", layout="wide", page_icon="📈")

# File Paths
CSV_FILE = 'assets.csv'
GOAL_FILE = 'goals.csv'
RATES_CACHE = 'last_rates.csv'
HISTORY_FILE = 'wealth_history.csv'

# --- 2. DATA ENGINES (OFFLINE-FIRST) ---
def get_rates():
    """Fetches live rates or falls back to local cache if offline."""
    default_rates = {"Gold": 7100.0, "Silver": 90.0, "USD": 83.5, "Date": "Manual"}
    try:
        # 1-second timeout prevents the app from hanging when offline
        resp = requests.get("https://open.er-api.com/v6/latest/USD", timeout=1)
        live_usd = resp.json()['rates']['INR']
        # Note: In a production app, you'd fetch live Gold/Silver prices here too
        fresh_rates = {
            "Gold": 7250.0, 
            "Silver": 92.5, 
            "USD": live_usd, 
            "Date": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        pd.DataFrame([fresh_rates]).to_csv(RATES_CACHE, index=False)
        return fresh_rates, "🟢 Live"
    except:
        if os.path.exists(RATES_CACHE):
            cached_df = pd.read_csv(RATES_CACHE)
            return cached_df.iloc[0].to_dict(), f"🟡 Cached ({cached_df.iloc[0]['Date']})"
        return default_rates, "🔴 Offline (No Cache)"

def load_data(file, columns):
    if os.path.exists(file):
        df = pd.read_csv(file)
        if 'Quantity' in df.columns: df['Quantity'] = df['Quantity'].astype(float)
        return df
    return pd.DataFrame(columns=columns)

def save_history(total_wealth):
    """Saves total wealth with a timestamp to track growth over time."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_entry = pd.DataFrame({'Timestamp': [now], 'Total_Wealth': [total_wealth]})
    if os.path.exists(HISTORY_FILE):
        history_df = pd.read_csv(HISTORY_FILE)
        # Avoid saving duplicate entries for the same minute
        if history_df.iloc[-1]['Total_Wealth'] != total_wealth:
            pd.concat([history_df, new_entry], ignore_index=True).to_csv(HISTORY_FILE, index=False)
    else:
        new_entry.to_csv(HISTORY_FILE, index=False)

# --- 3. SIDEBAR: THE VAULT CONTROLS ---
st.sidebar.header("📥 Vault Controls")

# A. Asset Entry (Direct Inputs - No 'Enter to Submit' message)
st.sidebar.subheader("Update Assets")
asset_type = st.sidebar.selectbox("Asset Name", ["Bank", "UPI", "Gold", "Silver", "USD Cash"])
quantity = st.sidebar.number_input("Amount / Weight", min_value=0.0, step=0.01, format="%.2f")
unit = "USD" if "USD" in asset_type else ("Grams" if asset_type in ["Gold", "Silver"] else "INR")

if st.sidebar.button("💾 Save to Local Vault"):
    df = load_data(CSV_FILE, ['Asset_Type', 'Quantity', 'Currency'])
    if asset_type in df['Asset_Type'].values:
        df.loc[df['Asset_Type'] == asset_type, ['Quantity', 'Currency']] = [quantity, unit]
    else:
        new_row = pd.DataFrame({'Asset_Type': [asset_type], 'Quantity': [quantity], 'Currency': [unit]})
        df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(CSV_FILE, index=False)
    st.rerun()

# B. Goal Settings
st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Set Purchase Goal")
g_name = st.sidebar.text_input("Item Name", placeholder="e.g. Gaming Mobile")
g_cost = st.sidebar.number_input("Cost (INR)", min_value=0.0, step=100.0)
g_buffer = st.sidebar.slider("Safety Buffer (%)", 0, 200, 75)

if st.sidebar.button("🚩 Lock Goal"):
    pd.DataFrame({'Goal_Name': [g_name], 'Target_Amount': [g_cost], 'Buffer_Pct': [g_buffer]}).to_csv(GOAL_FILE, index=False)
    st.sidebar.success("Goal Locked!")
    st.rerun()

# --- 4. MAIN DASHBOARD ---
st.title("FinOptic: Unified Command Center")
rates, status_msg = get_rates()
st.caption(f"Connection: {status_msg}")

assets_df = load_data(CSV_FILE, ['Asset_Type', 'Quantity', 'Currency'])
goals_df = load_data(GOAL_FILE, ['Goal_Name', 'Target_Amount', 'Buffer_Pct'])
history_df = load_data(HISTORY_FILE, ['Timestamp', 'Total_Wealth'])

if not assets_df.empty:
    # --- CALCULATIONS ---
    def calc_val(row):
        qty = row['Quantity']
        if row['Asset_Type'] == 'Gold': return qty * rates['Gold']
        if row['Asset_Type'] == 'Silver': return qty * rates['Silver']
        if row['Currency'] == 'USD': return qty * rates['USD']
        return qty
    
    assets_df['Value_INR'] = assets_df.apply(calc_val, axis=1)
    total_wealth = assets_df['Value_INR'].sum()
    save_history(total_wealth)

    # --- GROWTH METRIC ---
    initial_wealth = history_df.iloc[0]['Total_Wealth'] if not history_df.empty else total_wealth
    growth_pct = ((total_wealth - initial_wealth) / initial_wealth * 100) if initial_wealth > 0 else 0

    col1, col2 = st.columns(2)
    col1.metric("Total Liquid Wealth", f"₹ {total_wealth:,.2f}", delta=f"{growth_pct:.2f}% Net Growth")
    
    # --- GOAL TRACKER ---
    if not goals_df.empty:
        g_name, g_cost, g_buff = goals_df.iloc[0]['Goal_Name'], goals_df.iloc[0]['Target_Amount'], goals_df.iloc[0]['Buffer_Pct']
        safe_total = g_cost * (1 + (g_buff / 100))
        
        st.markdown(f"### 🚩 Goal Tracker: {g_name}")
        if total_wealth >= safe_total:
            st.balloons()
            st.success(f"🎊 **Financial Clearance Granted!** You can buy the {g_name} (₹{g_cost:,.0f}) and still keep your {g_buff}% buffer.")
        elif total_wealth >= g_cost:
            st.warning(f"⚠️ You can afford the item, but you are ₹{safe_total - total_wealth:,.2f} away from your {g_buff}% safety net.")
        else:
            progress = (total_wealth / g_cost)
            st.info(f"📈 Saving... You are {progress*100:.1f}% toward the base cost.")
            st.progress(min(progress, 1.0))

    # --- VISUALIZATIONS ---
    st.markdown("---")
    tab1, tab2 = st.tabs(["📊 Visual Analytics", "📋 Detailed Ledger"])
    
    with tab1:
        v_col1, v_col2 = st.columns(2)
        fig_pie = px.pie(assets_df, values='Value_INR', names='Asset_Type', hole=0.5, title="Asset Distribution")
        v_col1.plotly_chart(fig_pie, use_container_width=True)
        
        fig_bar = px.bar(assets_df, x='Asset_Type', y='Value_INR', color='Asset_Type', title="Portfolio Strength")
        v_col2.plotly_chart(fig_bar, use_container_width=True)

    with tab2:
        st.dataframe(assets_df[['Asset_Type', 'Quantity', 'Currency', 'Value_INR']], use_container_width=True)

else:
    st.info("👋 Welcome to FinOptic. Please enter your current assets in the sidebar to begin.")