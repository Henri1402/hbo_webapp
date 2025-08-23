# dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# -----------------------
# PAGE CONFIGURATION
# -----------------------
st.set_page_config(
    page_title="HBO Portfolio Dashboard",
    page_icon="hbo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------
# PASSWORD PROTECTION
# -----------------------
PASSWORD = "hbo2024"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 HBO Portfolio Dashboard Login")
    password_input = st.text_input("Enter password:", type="password")
    if password_input == PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    elif password_input:
        st.error("Incorrect password. Please try again.")
        st.stop()
    else:
        st.info("Please enter the password to access the dashboard.")
        st.stop()

# -----------------------
# DATA LOADING & CACHING
# -----------------------
@st.cache_data(ttl=600)  # Cache data for 10 minutes
def load_data():
    """Loads and cleans data from Google Sheets."""
    try:
        hbo_url = "https://docs.google.com/spreadsheets/d/1QgnWMF_fF0fdkAEvZvfO-MfR1Gme6kwOqC4928te1J0/export?format=csv&gid=0"
        ownership_url = "https://docs.google.com/spreadsheets/d/1QgnWMF_fF0fdkAEvZvfO-MfR1Gme6kwOqC4928te1J0/export?format=csv&gid=900806856"
        
        hbo_df = pd.read_csv(hbo_url, sep=",", decimal=",", encoding="utf-8-sig")
        hbo_df.rename(columns=lambda x: x.strip().replace('\ufeff', ''), inplace=True)
        hbo_df['Date'] = pd.to_datetime(hbo_df['Date'], dayfirst=True)
        
        owner_df = pd.read_csv(ownership_url, sep=",", decimal=",", encoding="utf-8-sig")
        owner_df.rename(columns=lambda x: x.strip().replace('\ufeff', ''), inplace=True)
        return hbo_df, owner_df
    except Exception as e:
        st.error(f"Failed to load data. Please check the connection. Error: {e}")
        return None, None

hbo_df, owner_df = load_data()

# Stop execution if data loading fails
if hbo_df is None or owner_df is None:
    st.stop()

# -----------------------
# DATA PROCESSING
# -----------------------
def process_data(hbo_df, owner_df):
    """Processes loaded data to compute key metrics."""
    # Convert 'Invested Capital' to a numeric type, removing currency symbols, thousands separators, and whitespace
    owner_df['Invested Capital'] = owner_df['Invested Capital'].replace({'€': '', ',': '', '\s+': ''}, regex=True).astype(float)
    owner_df['Total Shares'] = owner_df['Total Shares'].astype(int)

    hbo_df['HBO Share Price'] = hbo_df['HBO Share Price'].astype(str).str.replace(',', '.').astype(float)
    
    latest_price = hbo_df.sort_values("Date", ascending=False)["HBO Share Price"].iloc[0]
    
    owner_df['Total Value (€)'] = owner_df['Total Shares'] * latest_price
    owner_df['Return (€)'] = owner_df['Total Value (€)'] - owner_df['Invested Capital']
    
    # Avoid division by zero for new investments
    owner_df['ROI (%)'] = 0.0
    # Calculate ROI only for rows where 'Invested Capital' is not zero
    non_zero_capital = owner_df['Invested Capital'] != 0
    owner_df.loc[non_zero_capital, 'ROI (%)'] = (owner_df.loc[non_zero_capital, 'Return (€)'] / owner_df.loc[non_zero_capital, 'Invested Capital']) * 100

    total_aum = owner_df['Total Value (€)'].sum()
    
    return latest_price, total_aum, owner_df

latest_price, total_aum, owner_df = process_data(hbo_df, owner_df)


# -----------------------
# SIDEBAR NAVIGATION
# -----------------------
st.sidebar.image("hbo.png", width=150)
st.sidebar.title("HBO Portfolio")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["Dashboard Overview", "Investor Details", "Data Downloads"]
)

st.sidebar.markdown("---")
st.sidebar.info("© Built by Henri | Live from Google Sheets")

# -----------------------
# PAGE: DASHBOARD OVERVIEW
# -----------------------
if page == "Dashboard Overview":
    st.title("📈 Dashboard Overview")

    # --- Key Metrics ---
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="**Total Assets Under Management (AUM)**", value=f"€ {total_aum:,.2f}")
    with col2:
        st.metric(label="**Latest Share Price**", value=f"€ {latest_price:,.2f}")

    st.markdown("---")

    # --- Share Price Chart ---
    st.subheader("HBO Share Price Performance")
    fig_line = px.line(hbo_df, x="Date", y="HBO Share Price", markers=True,
                       labels={"Date": "Date", "HBO Share Price": "Share Price (€)"})
    fig_line.update_traces(line=dict(color='royalblue', width=2), marker=dict(color='darkblue', size=8))
    fig_line.update_layout(
        template="plotly_white",
        title="",
        xaxis_title="Date",
        yaxis_title="Share Price (€)",
        margin=dict(t=20, l=20, r=20, b=20),
        height=450
    )
    st.plotly_chart(fig_line, use_container_width=True)

# -----------------------
# PAGE: INVESTOR DETAILS
# -----------------------
elif page == "Investor Details":
    st.title("👥 Investor Details")
    st.markdown("An in-depth look at capital distribution and individual performance.")
    
    # --- Investor Performance Table ---
    st.subheader("Investor Performance Overview")
    table_df = owner_df.copy()
    table_df = table_df.rename(columns={
        "Full Name": "Name",
        "Invested Capital": "Invested (€)",
        "Total Shares": "Shares"
    })
    
    # Formatting for display
    table_df["Invested (€)"] = table_df["Invested (€)"].map("€ {:,.2f}".format)
    table_df["Total Value (€)"] = table_df["Total Value (€)"].map("€ {:,.2f}".format)
    table_df["Return (€)"] = table_df["Return (€)"].map("€ {:,.2f}".format)
    table_df["ROI (%)"] = table_df["ROI (%)"].map("{:.2f}%".format)
    
    st.dataframe(
        table_df[["Name", "Invested (€)", "Shares", "Total Value (€)", "Return (€)", "ROI (%)"]],
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")
    
    # --- Pie & Bar Charts ---
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Capital Invested Distribution")
        fig_pie = px.pie(owner_df, values="Invested Capital", names="Full Name")
        fig_pie.update_layout(template="plotly_white", legend_title="Investors", margin=dict(t=20, b=20))
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.subheader("Shares Held Per Investor")
        fig_bar = px.bar(owner_df.sort_values('Total Shares', ascending=False), 
                         x="Full Name", y="Total Shares", text_auto=True)
        fig_bar.update_layout(template="plotly_white", xaxis_title="", yaxis_title="Number of Shares", margin=dict(t=20, b=20))
        fig_bar.update_traces(marker_color='lightskyblue')
        st.plotly_chart(fig_bar, use_container_width=True)

# -----------------------
# PAGE: DATA DOWNLOADS
# -----------------------
elif page == "Data Downloads":
    st.title("📥 Data Downloads")
    st.markdown("Download the underlying data for your own analysis.")

    # --- Download Buttons ---
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="⬇️ Download HBO Price Data",
            data=hbo_df.to_csv(index=False).encode('utf-8'),
            file_name="hbo_price_history.csv",
            mime="text/csv",
            help="Download the complete HBO share price history as a CSV file."
        )

    with col2:
        # Prepare a clean version for download
        download_owner_df = owner_df.rename(columns={
            "Full Name": "Name",
            "Invested Capital": "Invested (€)",
            "Total Shares": "Shares"
        })
        
        st.download_button(
            label="⬇️ Download Investor Table",
            data=download_owner_df.to_csv(index=False).encode('utf-8'),
            file_name="investor_performance.csv",
            mime="text/csv",
            help="Download the investor performance table as a CSV file."
        )
