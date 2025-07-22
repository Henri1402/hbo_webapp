import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
from dotenv import load_dotenv

# load_dotenv()  # ✅ Only used for local development

st.set_page_config(page_title="HBO Investor Dashboard", layout="wide", initial_sidebar_state="collapsed")

# -------------------
# Theme Toggle
# -------------------
mode = st.toggle("Dark mode", value=False)
theme = "plotly_dark" if mode else "plotly_white"
button_style = """
    <style>
    .download-button button {
        color: black !important;
        background-color: white !important;
    }
    </style>
""" if not mode else """
    <style>
    .download-button button {
        color: white !important;
        background-color: #444 !important;
        border: 1px solid white !important;
    }
    </style>
"""
st.markdown(button_style, unsafe_allow_html=True)

# -------------------
# Password protection
# -------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    pw_input = st.text_input("Enter password to continue", type="password")
    if pw_input == os.environ.get("APP_PASSWORD"):
        st.session_state.authenticated = True
    elif pw_input:
        st.error("Incorrect password")
    st.stop()

# -------------------
# Load data
# -------------------
@st.cache_data
def load_data():
    hbo_url = os.environ.get("HBO_SHEET_URL")
    ownership_url = os.environ.get("OWNERSHIP_SHEET_URL")

    hbo_df = pd.read_csv(hbo_url)
    hbo_df.columns = hbo_df.columns.str.strip()
    hbo_df["Date"] = pd.to_datetime(hbo_df["Date"], dayfirst=True)
    hbo_df = hbo_df.sort_values("Date")

    owner_df = pd.read_csv(ownership_url)
    owner_df.columns = owner_df.columns.str.strip()
    owner_df["Invested Capital"] = owner_df["Invested Capital"].replace("[€\s]", "", regex=True).str.replace(",", "").astype(float)
    owner_df["Total Shares"] = owner_df["Total Shares"].astype(float)

    return hbo_df, owner_df

hbo_df, owner_df = load_data()
latest_price = hbo_df.iloc[-1]["HBO Share Price"]
total_value = hbo_df.iloc[-1]["Total HBO Value"]

# -------------------
# HBO Share Price Chart
# -------------------
col1, col2 = st.columns([4, 1])
with col1:
    st.subheader("HBO Share Price Performance")
with col2:
    st.markdown(
        f"""
        <div style='border: 1px solid {"#888" if mode else "#ccc"}; padding: 10px; border-radius: 8px;
                    background-color: {"#333" if mode else "#f9f9f9"}; text-align: center;'>
            <div style='font-size: 14px; color: {"#ccc" if mode else "#333"};'>Latest Share Price</div>
            <div style='font-size: 24px; font-weight: bold; color: {"#fff" if mode else "#111"};'>€ {latest_price:.2f}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

fig = px.line(hbo_df, x="Date", y="HBO Share Price", title="", template=theme)
fig.update_traces(line=dict(width=3))
fig.update_layout(margin=dict(t=20, l=0, r=0, b=0), height=400)
st.plotly_chart(fig, use_container_width=True)

# -------------------
# Ownership Table
# -------------------
owner_df["Value"] = owner_df["Total Shares"] * latest_price
owner_df["Return (€)"] = owner_df["Value"] - owner_df["Invested Capital"]
owner_df["ROI (%)"] = (owner_df["Return (€)"] / owner_df["Invested Capital"]) * 100

owner_df_display = owner_df.copy()
owner_df_display["Invested Capital"] = owner_df_display["Invested Capital"].map("€ {:.2f}".format)
owner_df_display["Value"] = owner_df_display["Value"].map("€ {:.2f}".format)
owner_df_display["Return (€)"] = owner_df_display["Return (€)"].map("€ {:.2f}".format)
owner_df_display["ROI (%)"] = owner_df_display["ROI (%)"].map("{:.1f}%".format)

st.subheader("Investor Breakdown")
st.dataframe(owner_df_display.style.format(), use_container_width=True)

# -------------------
# Downloads
# -------------------
col1, col2 = st.columns(2)
with col1:
    st.download_button(
        "Download HBO History CSV",
        hbo_df.to_csv(index=False).encode(),
        "hbo_history.csv",
        mime="text/csv",
        key="download-hbo",
        help="Download share price history",
    )
with col2:
    st.download_button(
        "Download Investor Table CSV",
        owner_df.to_csv(index=False).encode(),
        "investors.csv",
        mime="text/csv",
        key="download-investors",
        help="Download investor data",
    )

# -----------------------
# FOOTER
# -----------------------
st.caption("© Built by Henri | Live from Google Sheets")
