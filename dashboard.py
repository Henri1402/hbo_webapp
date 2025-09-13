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
@st.cache_data(ttl=600)
def load_data():
    """Loads and cleans data from Google Sheets."""
    try:
        hbo_url = "https://docs.google.com/spreadsheets/d/1QgnWMF_fF0fdkAEvZvfO-MfR1Gme6kwOqC4928te1J0/export?format=csv&gid=0"
        ownership_url = "https://docs.google.com/spreadsheets/d/1QgnWMF_fF0fdkAEvZvfO-MfR1Gme6kwOqC4928te1J0/export?format=csv&gid=900806856"

        # --- Load and Clean HBO Data Sheet ---
        hbo_df = pd.read_csv(hbo_url, sep=",", encoding="utf-8-sig", dtype=str)
        hbo_df.rename(columns=lambda x: x.strip().replace('\ufeff', ''), inplace=True)
        hbo_df['Date'] = pd.to_datetime(hbo_df['Date'], dayfirst=True)

        cols_to_clean = ['Degiro', 'InteractiveBrokers', 'Total HBO Value', 'Shares', 'HBO Share Price']
        for col in cols_to_clean:
            if col in hbo_df.columns:
                # Correctly handle numbers like '1.500,00' -> 1500.00
                hbo_df[col] = (
                    hbo_df[col]
                    .str.replace(r"\.", "", regex=True)   # remove thousand separators
                    .str.replace(",", ".", regex=False)   # fix decimal separator
                    .astype(float)
                )

        # --- Load and Clean Ownership Data Sheet ---
        owner_df = pd.read_csv(ownership_url, sep=",", encoding="utf-8-sig", dtype=str)
        owner_df.rename(columns=lambda x: x.strip().replace('\ufeff', ''), inplace=True)

        # Proper fix for European-style numbers: "€ 2,144.68" -> 2144.68
        owner_df['Invested Capital'] = (
            owner_df['Invested Capital']
            .str.replace("€", "", regex=False)
            .str.strip()
            .str.replace(r"[,.](?=\d{3}(?:\D|$))", "", regex=True)  # remove thousand separators only
            .str.replace(",", ".", regex=False)                     # replace decimal comma if present
            .astype(float)
        )

        owner_df['Total Shares'] = owner_df['Total Shares'].astype(int)

        return hbo_df, owner_df
    except Exception as e:
        st.error(f"Failed to load data. The data format in Google Sheets might be incorrect. Error: {e}")
        return None, None

hbo_df, owner_df = load_data()

if hbo_df is None or owner_df is None:
    st.stop()

# -----------------------
# DATA PROCESSING
# -----------------------
def process_data(hbo_df, owner_df):
    """Processes loaded data to compute key metrics."""
    latest_data = hbo_df.sort_values("Date", ascending=False).iloc[0]
    latest_price = latest_data["HBO Share Price"]
    total_aum = latest_data["Total HBO Value"]

    owner_df['Total Value (€)'] = owner_df['Total Shares'] * latest_price
    owner_df['Return (€)'] = owner_df['Total Value (€)'] - owner_df['Invested Capital']

    owner_df['ROI (%)'] = 0.0
    non_zero_capital = owner_df['Invested Capital'] > 0
    owner_df.loc[non_zero_capital, 'ROI (%)'] = (
        owner_df.loc[non_zero_capital, 'Return (€)'] / owner_df.loc[non_zero_capital, 'Invested Capital']
    ) * 100

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
    ["HBO Share Price", "HBO Portfolio", "Investor Details", "Data Downloads"]
)

st.sidebar.markdown("---")
st.sidebar.info("© Built by Henri | Live from Google Sheets")

# -----------------------
# PAGE: HBO SHARE PRICE
# -----------------------
if page == "HBO Share Price":
    st.title("📈 HBO Share Price")

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="**Total Assets Under Management (AUM)**", value=f"€ {total_aum:,.2f}")
    with col2:
        st.metric(label="**Latest Share Price**", value=f"€ {latest_price:,.2f}")

    st.markdown("---")

    st.subheader("HBO Share Price Performance")
    fig_line = px.line(hbo_df, x="Date", y="HBO Share Price", markers=True,
                       labels={"Date": "Date", "HBO Share Price": "Share Price (€)"})
    fig_line.update_traces(line=dict(color='royalblue', width=2), marker=dict(color='darkblue', size=8))
    fig_line.update_layout(
        template="plotly_white",
        xaxis_title="Date",
        yaxis_title="Share Price (€)",
        margin=dict(t=20, l=20, r=20, b=20),
        height=450
    )
    st.plotly_chart(fig_line, use_container_width=True)

# -----------------------
# PAGE: HBO PORTFOLIO
# -----------------------
elif page == "HBO Portfolio":
    st.title("📊 HBO Portfolio Value")

    portfolio_df = hbo_df.melt(id_vars=['Date'], value_vars=['Degiro', 'InteractiveBrokers', 'Total HBO Value'],
                               var_name='Portfolio', value_name='Value (€)')

    fig_portfolio = px.line(portfolio_df, x='Date', y='Value (€)', color='Portfolio',
                            title='Portfolio Value Over Time by Broker',
                            labels={'Value (€)': 'Portfolio Value (€)', 'Date': 'Date', 'Portfolio': 'Broker/Total'})
    fig_portfolio.update_layout(
        template="plotly_white",
        legend_title_text='Portfolio',
        height=600
    )
    st.plotly_chart(fig_portfolio, use_container_width=True)

# -----------------------
# PAGE: INVESTOR DETAILS
# -----------------------
elif page == "Investor Details":
    st.title("👥 Investor Details")
    st.markdown("An in-depth look at capital distribution and individual performance.")

    st.subheader("Investor Performance Overview")
    table_df = owner_df.copy()
    table_df = table_df.rename(columns={
        "Full Name": "Name",
        "Invested Capital": "Invested (€)",
        "Total Shares": "Shares"
    })

    # --- Add Total Row ---
    total_row = {
        "Name": "TOTAL",
        "Invested (€)": table_df["Invested (€)"].sum(),
        "Shares": table_df["Shares"].sum(),
        "Total Value (€)": table_df["Total Value (€)"].sum(),
        "Return (€)": table_df["Return (€)"].sum(),
        "ROI (%)": (
            (table_df["Return (€)"].sum() / table_df["Invested (€)"].sum()) * 100
            if table_df["Invested (€)"].sum() > 0 else 0
        )
    }
    table_df = pd.concat([table_df, pd.DataFrame([total_row])], ignore_index=True)

    # Format numbers
    table_df["Invested (€)"] = table_df["Invested (€)"].map("€ {:,.2f}".format)
    table_df["Total Value (€)"] = table_df["Total Value (€)"].map("€ {:,.2f}".format)
    table_df["Return (€)"] = table_df["Return (€)"].map("€ {:,.2f}".format)
    table_df["ROI (%)"] = table_df["ROI (%)"].map("{:.2f}%".format)

    # --- Styling for TOTAL row ---
    def highlight_total(row):
        if row["Name"] == "TOTAL":
            return ['font-weight: bold; background-color: #f4f4f4; color: black'] * len(row)
        else:
            return [''] * len(row)

    styled_df = table_df[["Name", "Invested (€)", "Shares", "Total Value (€)", "Return (€)", "ROI (%)"]].style.apply(
        highlight_total, axis=1
    )

    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    st.markdown("---")

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
