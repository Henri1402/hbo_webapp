import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------
# CONFIG
# -----------------------
st.set_page_config(page_title="HBO Portfolio Dashboard", layout="wide")

# Theme toggle
theme = st.toggle("🌙 Dark Mode", value=False)

if theme:
    st.markdown("""
        <style>
        body, .stApp {
            background-color: #0e1117;
            color: white;
        }
        .download-button button {
            background-color: #1f77b4 !important;
            color: white !important;
            border: none;
        }
        .stMetricBox {
            background-color: #1c1f26;
            padding: 1rem;
            border-radius: 0.5rem;
            border: 1px solid #333;
            color: white;
            text-align: center;
            font-size: 1.2rem;
        }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        .download-button button {
            background-color: #f0f0f0 !important;
            color: black !important;
        }
        .stMetricBox {
            background-color: #f9f9f9;
            padding: 1rem;
            border-radius: 0.5rem;
            border: 1px solid #ccc;
            color: black;
            text-align: center;
            font-size: 1.2rem;
        }
        </style>
    """, unsafe_allow_html=True)

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
# CHARTS
# -----------------------

col1, col2 = st.columns([4, 1])
with col1:
    st.title("HBO Share Price Performance")
with col2:
    st.markdown(f"""
        <div class='stMetricBox'>
            <div><strong>Latest Share Price</strong></div>
            <div style='font-size: 1.5rem; margin-top: 5px;'>€ {latest_price:.2f}</div>
        </div>
    """, unsafe_allow_html=True)

fig_line = px.line(hbo_df, x="Date", y="HBO Share Price", markers=True)
fig_line.update_layout(template="plotly_dark" if theme else "plotly_white", margin=dict(t=40))
st.plotly_chart(fig_line, use_container_width=True)

col1, col2 = st.columns(2)

with col1:
    fig_pie = px.pie(owner_df, values="Invested Capital", names="Full Name", title="Capital Invested Distribution")
    fig_pie.update_layout(template="plotly_dark" if theme else "plotly_white")
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    fig_bar = px.bar(owner_df, x="Full Name", y="Total Shares", title="Shares Held Per Investor", text_auto=True)
    fig_bar.update_layout(template="plotly_dark" if theme else "plotly_white")
    st.plotly_chart(fig_bar, use_container_width=True)

st.subheader("Investor Performance Overview")

# Format table
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
                       "hbo_data.csv", "text/csv", key="hbo_download")

with col2:
    st.download_button("Download Investor Table", table_df.to_csv(index=False).encode('utf-8'),
                       "investors.csv", "text/csv", key="inv_download")

# -----------------------
# FOOTER
# -----------------------
st.caption("© Built by Henri | Live from Google Sheets")
