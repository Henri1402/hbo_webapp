# dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import yfinance as yf

# -----------------------
# CONFIG
# -----------------------
st.set_page_config(page_title="HBO Portfolio Dashboard", layout="wide")

# -----------------------
# PASSWORD
# -----------------------
PASSWORD = "hbo2024"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("HBO Portfolio Dashboard")
    password_input = st.text_input("Enter password:", type="password")
    if password_input == PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    elif password_input:
        st.error("Incorrect password")
        st.stop()
    else:
        st.stop()

# -----------------------
# LOAD DATA
# -----------------------
@st.cache_data(ttl=600)
def load_data():
    hbo_url = "https://docs.google.com/spreadsheets/d/1QgnWMF_fF0fdkAEvZvfO-MfR1Gme6kwOqC4928te1J0/export?format=csv&gid=0"
    ownership_url = "https://docs.google.com/spreadsheets/d/1QgnWMF_fF0fdkAEvZvfO-MfR1Gme6kwOqC4928te1J0/export?format=csv&gid=900806856"
    hbo_df = pd.read_csv(hbo_url, sep=",", decimal=",", encoding="utf-8-sig")
    hbo_df.rename(columns=lambda x: x.strip().replace('\ufeff', ''), inplace=True)
    hbo_df['Date'] = pd.to_datetime(hbo_df['Date'], dayfirst=True)
    owner_df = pd.read_csv(ownership_url, sep=",", decimal=",", encoding="utf-8-sig")
    owner_df.rename(columns=lambda x: x.strip().replace('\ufeff', ''), inplace=True)
    return hbo_df, owner_df

hbo_df, owner_df = load_data()

# -----------------------
# PROCESS DATA
# -----------------------
owner_df['Invested Capital'] = owner_df['Invested Capital'].replace({'€': '', ',': ''}, regex=True).astype(float)
owner_df['Total Shares'] = owner_df['Total Shares'].astype(int)
latest_price = hbo_df.sort_values("Date")["HBO Share Price"].iloc[-1]
owner_df['Total Value (€)'] = owner_df['Total Shares'] * latest_price
owner_df['Return (€)'] = owner_df['Total Value (€)'] - owner_df['Invested Capital']
owner_df['ROI (%)'] = (owner_df['Return (€)'] / owner_df['Invested Capital']) * 100

# -----------------------
# SHARE PRICE CHART
# -----------------------
col1, col2 = st.columns([4, 1])
with col1:
    st.title("HBO Share Price Performance")
with col2:
    st.markdown(f"""
        <div style='background-color: #f9f9f9; padding: 1rem; border-radius: 0.5rem; border: 1px solid #ccc; text-align: center;'>
            <div><strong>Latest Share Price</strong></div>
            <div style='font-size: 1.5rem;'>€ {latest_price:.2f}</div>
        </div>
    """, unsafe_allow_html=True)

fig_line = px.line(hbo_df, x="Date", y="HBO Share Price", markers=True)
fig_line.update_layout(template="plotly_white", margin=dict(t=40))
st.plotly_chart(fig_line, use_container_width=True)

# -----------------------
# PIE & BAR CHARTS
# -----------------------
col1, col2 = st.columns(2)

with col1:
    fig_pie = px.pie(owner_df, values="Invested Capital", names="Full Name", title="Capital Invested Distribution")
    fig_pie.update_layout(template="plotly_white")
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    fig_bar = px.bar(owner_df, x="Full Name", y="Total Shares", title="Shares Held Per Investor", text_auto=True)
    fig_bar.update_layout(template="plotly_white")
    st.plotly_chart(fig_bar, use_container_width=True)

# -----------------------
# BENCHMARK RETURNS
# -----------------------
@st.cache_data(ttl=3600)
def fetch_benchmark_returns(period):
    tickers = {
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "BEL20": "^BFX",
        "Gold": "GC=F"
    }
    end = datetime.today()
    start = {
        "YTD": datetime(end.year, 1, 1),
        "1M": end - pd.DateOffset(months=1),
        "1Y": end - pd.DateOffset(years=1),
        "2Y": end - pd.DateOffset(years=2)
    }[period]

    try:
        prices = yf.download(list(tickers.values()), start=start, end=end, progress=False)
        if isinstance(prices.columns, pd.MultiIndex) and "Close" in prices.columns.get_level_values(0):
            close_prices = prices["Close"]
        else:
            return None

        returns = ((close_prices.iloc[-1] / close_prices.iloc[0]) - 1) * 100
        df = pd.DataFrame({
            "Benchmark": list(tickers.keys()),
            "Return (%)": returns.values
        })
        return df
    except Exception:
        return None

st.subheader("📊 HBO vs Benchmark Returns")
period = st.selectbox("Select Time Period", ["YTD", "1M", "1Y", "2Y"], index=2)
bench_df = fetch_benchmark_returns(period)

if bench_df is not None:
    start_date = {
        "YTD": datetime(datetime.today().year, 1, 1),
        "1M": datetime.today() - pd.DateOffset(months=1),
        "1Y": datetime.today() - pd.DateOffset(years=1),
        "2Y": datetime.today() - pd.DateOffset(years=2),
    }[period]
    hbo_filtered = hbo_df[hbo_df["Date"] >= start_date]
    if not hbo_filtered.empty:
        hbo_return = ((hbo_filtered["HBO Share Price"].iloc[-1] / hbo_filtered["HBO Share Price"].iloc[0]) - 1) * 100
        bench_df.loc[len(bench_df.index)] = ["HBO Fund", hbo_return]
    fig_benchmark = px.bar(bench_df, x="Benchmark", y="Return (%)", text_auto=".2f")
    fig_benchmark.update_layout(template="plotly_white")
    st.plotly_chart(fig_benchmark, use_container_width=True)
else:
    st.warning("⚠️ Failed to fetch benchmark data. Try refreshing later.")

# -----------------------
# PERFORMANCE TABLE
# -----------------------
st.subheader("Investor Performance Overview")
table_df = owner_df.copy()
table_df = table_df.rename(columns={
    "Full Name": "Name",
    "Invested Capital": "Invested (€)",
    "Total Shares": "Shares"
})
table_df["Invested (€)"] = table_df["Invested (€)"].map("€ {:,.2f}".format)
table_df["Total Value (€)"] = table_df["Total Value (€)"].map("€ {:,.2f}".format)
table_df["Return (€)"] = table_df["Return (€)"].map("€ {:,.2f}".format)
table_df["ROI (%)"] = table_df["ROI (%)"].map("{:.2f}%".format)
st.dataframe(table_df[["Name", "Invested (€)", "Shares", "Total Value (€)", "Return (€)", "ROI (%)"]],
             use_container_width=True)

# -----------------------
# DOWNLOAD BUTTONS
# -----------------------
st.markdown("### Downloads")
col1, col2 = st.columns(2)

with col1:
    st.download_button("Download HBO Price Data", hbo_df.to_csv(index=False).encode('utf-8'),
                       "hbo_data.csv", "text/csv", key="hbo_download", help="Download full HBO share price history")

with col2:
    st.download_button("Download Investor Table", table_df.to_csv(index=False).encode('utf-8'),
                       "investors.csv", "text/csv", key="inv_download", help="Download investor performance table")

st.image("hbo.png", width=500)

st.caption("© Built by Henri | Live from Google Sheets")
