# %%
from dotenv import load_dotenv

print("dotenv imported successfully")

# %%
import streamlit as st

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Sales Dashboard", layout="wide")
st.markdown("""
<style>

/* Multiselect box */
div[data-baseweb="select"] > div {
    background-color: #DDF5E3 !important;
    border: 2px solid #008037 !important;
    border-radius: 8px !important;
}

/* Selected month tags */
span[data-baseweb="tag"] {
    background-color: #008037 !important;
    color: white !important;
}

</style>
""", unsafe_allow_html=True)
# ---------------- SESSION STATE ----------------

# -------- SIDEBAR --------
# Logo (URL image directly use karo)
logo_url = "https://oswalsolar.smartlogics.in/images/logo.png"
with st.sidebar:
    col1, col2, col3 = st.columns(3)

    with col2:
        st.image(logo_url, width=400)
st.sidebar.markdown(
    """
    <div style="text-align:center;">
        <h2 style="color:Black; font-size:40px;">
            📊 SALES DASHBOARD
        </h2>
    </div>
    """,
    unsafe_allow_html=True
)

# ---------------- GLOBAL FILTERS ----------------

import os
import sys
import plotly.express as px
import plotly.graph_objects as go
import requests
import pandas as pd
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# ------------------------------------------------------------
# Load environment variables from the .env file
# ------------------------------------------------------------
# The .env file should contain:
# BC_ODATA_URL=your_business_central_odata_url
# BC_USERNAME=your_username
# BC_PASSWORD_OR_ACCESS_KEY=your_password_or_access_key
# OUTPUT_CSV=optional_output_file_name.csv
# VERIFY_SSL=true
load_dotenv(override=True)
# ------------------------------------------------------------
# Read configuration values from environment variables
# ------------------------------------------------------------
BC_ODATA_URL = os.getenv("BC_ODATA_URL")
BC_ODATA_URL_2 = os.getenv("BC_ODATA_URL_2")
BC_USERNAME = os.getenv("BC_USERNAME")
BC_PASSWORD_OR_ACCESS_KEY = os.getenv("BC_PASSWORD_OR_ACCESS_KEY")

# Default CSV file name if OUTPUT_CSV is not provided in .env
OUTPUT_CSV = os.getenv("OUTPUT_CSV", "business_central_export.csv")

# Convert VERIFY_SSL value from string to boolean
# true  -> SSL certificate will be verified
# false -> SSL certificate verification will be skipped
VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() == "true"


def validate_env():
    """
    Validates that all required environment variables are available.

    If any required variable is missing, the script stops immediately.
    This prevents the script from running with incomplete configuration.
    """

    print("[STEP 1] Validating environment variables...")

    required_vars = {
        "BC_ODATA_URL": BC_ODATA_URL,
        "BC_ODATA_URL_2": BC_ODATA_URL_2,
        "BC_USERNAME": BC_USERNAME,
        "BC_PASSWORD_OR_ACCESS_KEY": BC_PASSWORD_OR_ACCESS_KEY,
    }

    missing = [key for key, value in required_vars.items() if not value]

    if missing:
        print("\n[ERROR] Missing required environment variables:")
        for key in missing:
            print(f"  - {key}")

        print("\nPlease check your .env file and try again.")
        sys.exit(1)

    print("[OK] All required environment variables are present.")


def get_output_file_path(file_name):
    """
    Returns the full CSV file path inside the current working directory.

    Example:
    If current working directory is:
      D:/Projects/BCExport

    and file_name is:
      export.csv

    then this function returns:
      D:/Projects/BCExport/export.csv
    """

    print("\n[STEP 2] Preparing output file location...")
    current_working_directory = os.getcwd()

    # Keep only the file name, even if user accidentally gives a path.
    # This ensures the file is saved in the current working directory.
    safe_file_name = os.path.basename(file_name)
    output_path = os.path.join(current_working_directory, safe_file_name)

    print(f"[INFO] Current working directory: {current_working_directory}")
    print(f"[INFO] Output CSV file name: {safe_file_name}")
    print(f"[INFO] Full output path: {output_path}")

    return output_path


def create_session():
    """
    Creates and configures a requests session for Business Central.

    The session contains:
    - Basic authentication
    - JSON response header
    - Read-only intent header

    Important:
    This script only uses GET requests.
    It does not use POST, PATCH, PUT, or DELETE.
    So it does not create, update, or delete Business Central records.
    """

    print("\n[STEP 3] Creating secure HTTP session...")
    session = requests.Session()

    # Add Basic Authentication credentials.
    # Depending on your Business Central setup, this may be:
    # - username + password
    # - username + web service access key
    session.auth = HTTPBasicAuth(BC_USERNAME, BC_PASSWORD_OR_ACCESS_KEY)

    # Accept JSON response from Business Central.
    # Data-Access-Intent: ReadOnly tells Business Central that
    # this request is intended only for reading data.
    session.headers.update(
        {
            "Accept": "application/json",
            "Data-Access-Intent": "ReadOnly",
        }
    )

    print("[OK] HTTP session created.")
    print("[INFO] Request method used by this script: GET only")
    print("[INFO] Data access intent: ReadOnly")

    return session

@st.cache_data(ttl=3600)  # 1 hour cache
def fetch_all_records(url):
    """
    Fetches all records from the Business Central OData endpoint.

    Business Central may return data in multiple pages.
    If more pages are available, the response contains '@odata.nextLink'.

    This function keeps fetching records until there is no next page left.
    """

    print("\n[STEP 4] Starting data fetch from Business Central...")
    print(f"[INFO] Source OData URL: {url}")
    print(f"[INFO] SSL verification enabled: {VERIFY_SSL}")

    all_records = []
    next_url = url
    page_number = 1

    session = create_session()

    while next_url:
        print(f"\n[FETCH] Reading page {page_number}...")
        print(f"[FETCH] URL: {next_url}")

        try:
            # This is the actual read-only request.
            # GET means fetch/read data only.
            response = session.get(
                next_url,
                verify=VERIFY_SSL,
                   timeout=30
            )

        except requests.exceptions.SSLError as error:
            print("\n[ERROR] SSL certificate verification failed.")
            print("Possible solutions:")
            print("  1. Use a valid SSL certificate on the server.")
            print("  2. For local/testing only, set VERIFY_SSL=false in .env.")
            print(f"\nTechnical details: {error}")
            sys.exit(1)

        except requests.exceptions.ConnectionError as error:
            print("\n[ERROR] Could not connect to the Business Central server.")
            print("Please check:")
            print("  1. Server URL")
            print("  2. Port number")
            print("  3. Network/VPN connectivity")
            print("  4. Firewall settings")
            print(f"\nTechnical details: {error}")
            sys.exit(1)

        except requests.exceptions.Timeout as error:
            print("\n[ERROR] Request timed out.")
            print("The server took too long to respond.")
            print("Try again later or export a smaller filtered dataset.")
            print(f"\nTechnical details: {error}")
            sys.exit(1)

        except requests.exceptions.RequestException as error:
            print("\n[ERROR] Unexpected request error occurred.")
            print(f"Technical details: {error}")
            sys.exit(1)

        print(f"[INFO] HTTP status code: {response.status_code}")

        if response.status_code != 200:
            print("\n[ERROR] Request failed.")

            if response.status_code == 401:
                print(
                    "[CAUSE] Unauthorized. Username/password/access key may be incorrect."
                )
            elif response.status_code == 403:
                print(
                    "[CAUSE] Forbidden. Your user may not have permission to access this OData service."
                )
            elif response.status_code == 404:
                print(
                    "[CAUSE] Not found. The OData URL, company, or service name may be incorrect."
                )
            elif response.status_code >= 500:
                print("[CAUSE] Server-side error from Business Central.")

            print(f"\nResponse from server:\n{response.text}")
            response.raise_for_status()

        try:
            data = response.json()

        except ValueError:
            print("\n[ERROR] Server response is not valid JSON.")
            print(
                "Please check if the URL is a valid Business Central OData JSON endpoint."
            )
            print(f"\nResponse text:\n{response.text}")
            sys.exit(1)

        # In OData responses, actual records are usually inside the "value" key.
        records = data.get("value", [])
        print(f"[OK] Records fetched from page {page_number}: {len(records)}")
        all_records.extend(records)
        print(f"[INFO] Total records fetched so far: {len(all_records)}")

        # If Business Central has more pages, it provides @odata.nextLink.
        next_url = data.get("@odata.nextLink")
        if next_url:
            print("[INFO] More records available. Moving to next page...")
        else:
            print("[INFO] No more pages found.")

        page_number += 1

    print("\n[OK] Data fetch completed.")
    print(f"[INFO] Total records fetched: {len(all_records)}")
    return all_records


def save_to_csv(records, output_path):
    """
    Converts fetched Business Central records into a CSV file.

    Steps:
    1. Convert JSON records into a pandas DataFrame.
    2. Remove technical OData metadata columns.
    3. Save the DataFrame as a CSV file.
    """

    print("\n[STEP 5] Preparing data for CSV export...")
    if not records:
        print("[WARNING] No records found.")
        print("[INFO] CSV file was not created because there is no data to export.")
        return

    print("[INFO] Converting JSON records into table format...")

    # Converts nested JSON into a flat table where possible.
    df = pd.json_normalize(records)
    print(f"[OK] Data converted successfully.")
    print(f"[INFO] Number of rows: {len(df)}")
    print(f"[INFO] Number of columns before cleanup: {len(df.columns)}")

    # Remove technical OData metadata columns such as @odata.etag.
    metadata_columns = [col for col in df.columns if col.startswith("@odata.")]

    if metadata_columns:
        print(f"[INFO] Removing OData metadata columns: {metadata_columns}")
        df.drop(columns=metadata_columns, inplace=True)
    else:
        print("[INFO] No OData metadata columns found.")

    print(f"[INFO] Number of columns after cleanup: {len(df.columns)}")
    print("\n[STEP 6] Saving data to CSV file...")

    try:
        # utf-8-sig works well with Microsoft Excel.
        df.to_csv(output_path, index=False, encoding="utf-8-sig")

    except PermissionError:
        print("\n[ERROR] Permission denied while saving CSV file.")
        print("Please check:")
        print("  1. The CSV file is not already open in Excel.")
        print("  2. You have write permission in the current folder.")
        print(f"  3. Output path: {output_path}")
        sys.exit(1)

    except Exception as error:
        print("\n[ERROR] Failed to save CSV file.")
        print(f"Technical details: {error}")
        sys.exit(1)

    print("\n[SUCCESS] Export completed successfully.")
    print(f"[SUCCESS] Rows exported: {len(df)}")
    print(f"[SUCCESS] Columns exported: {len(df.columns)}")
    print(f"[SUCCESS] CSV saved at: {output_path}")

@st.cache_data(ttl=3600)
def fetch_all_records(url):
    """Fetch all records from the given URL.

    Placeholder implementation: returns an empty list if not implemented.
    """
    try:
        print(f"[INFO] fetch_all_records called for URL: {url}")
        # TODO: implement actual fetch logic. Returning empty list to avoid crash.
        return []
    except Exception as e:
        print(f"[ERROR] fetch_all_records failed: {e}")
        return []

def main():
    validate_env()
    output_path = get_output_file_path(OUTPUT_CSV)
    # -----------------------------
    # FETCH DATA
    # -----------------------------
    records1 = fetch_all_records(BC_ODATA_URL)
    records2 = fetch_all_records(BC_ODATA_URL_2)

    df1 = pd.json_normalize(records1)
    df2 = pd.json_normalize(records2)

    print("DF1 columns:", df1.columns.tolist())
    print("DF2 columns:", df2.columns.tolist())

    # -----------------------------
    # CLEAN DF1 (Invoice Line)
    # -----------------------------
    selected_cols_df1 = [
        'Amount',
        'AmountIncludingVAT',
        'Description',
        'DocumentNo',
        'BilltoCustomerNo',
        'Quantity',
        'PostingDate',
        'LocationCode',
        'GSTAssessableValueLCY',
        'InvDiscountAmount',
        'ItemCategoryCode'
    ]

    df1_clean = df1[[col for col in selected_cols_df1 if col in df1.columns]]

    # -----------------------------
    # CLEAN DF2 (Invoice Header)
    # IMPORTANT: No column may NOT exist, so we handle safely
    # -----------------------------

    # Find correct key column automatically
    possible_keys = ['No', 'No_', 'no', 'DocumentNo', 'Document_No']

    header_key = None
    for col in possible_keys:
        if col in df2.columns:
            header_key = col
            break

    if header_key is None:
        print("\n[ERROR] No valid key column found in df2!")
        print("Available columns:", df2.columns.tolist())
        sys.exit(1)

    print(f"\n[INFO] Using header key column: {header_key}")

    selected_cols_df2 = [
        header_key,
        'billToName',
        'billToCity', 
         'state',
    ]

    df2_clean = df2[[col for col in selected_cols_df2 if col in df2.columns]]

    # -----------------------------
    # SAFE MERGE
    # -----------------------------
    df_merged = df1_clean.merge(
        df2_clean,
        left_on='DocumentNo',
        right_on=header_key,
        how='left'
    )

    # -----------------------------
    # OUTPUT FILES
    # -----------------------------
    df1_clean.to_csv("InvoiceLine.csv", index=False, encoding="utf-8-sig")
    df2_clean.to_csv("InvoiceHeader.csv", index=False, encoding="utf-8-sig")
    df_merged.to_csv("InvoiceMerged.csv", index=False, encoding="utf-8-sig")

    print("\n[SUCCESS] Files created successfully!")
    print("InvoiceLine.csv")
    print("InvoiceHeader.csv")
    print("InvoiceMerged.csv")
    # print(df2_clean)

    print("\nMerged Shape:", df_merged.shape)

    return df1_clean, df2_clean, df_merged


# if __name__ == "__main__":
    
# #     main  ()
    # %%
@st.cache_data
def load_saved_data():
    return pd.read_csv("InvoiceMerged.csv")


with st.spinner("Loading Dashboard Data..."):
    df_merged = load_saved_data()

st.success("Data Loaded Successfully")

# =====================================================
# GLOBAL FILTERS
# =====================================================

import streamlit as st


# ================= INIT =================
# ================= INIT =================
if "page" not in st.session_state:
    st.session_state.page = "Home"

# ================= SIDEBAR =================
st.sidebar.title("CONTENTS")

# Refresh Button
if st.sidebar.button("🔄 Refresh Live Data"):
    with st.spinner("Refreshing from API..."):
        df1_clean, df2_clean, df_merged = main()

        # overwrite old merged file
        df_merged.to_csv("InvoiceMerged.csv", index=False)

        st.cache_data.clear()

    st.success("Data Refreshed Successfully")
    st.rerun()

st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "",
    [
        " Home",
        " Top Customers",
        " City Wise",
        " State Wise",
        " Watt Wise",
        " Month Wise"
    ]
)

st.session_state.page = menu

def show_home():
    st.title("Welcome to the Sales Dashboard")
    st.markdown("""
    This dashboard provides insights into sales data, including top products, customers, and geographical analysis.
    Use the sidebar to navigate through different sections of the dashboard.
    """)

def show_top_customers():
    st.title("Top Customers")

def show_city_analysis():
    st.title("City Wise Analysis")

def show_state_analysis():
    st.title("State Wise Analysis")

def show_watt_analysis():
    st.title("Watt Wise Analysis")

def show_monthly_analysis():
    st.title("Monthly Sales Analysis")


# ================= ROUTING =================
if st.session_state.page == "Home":
    show_home()

elif st.session_state.page == "Customers":
    show_top_customers()

elif st.session_state.page == "City":
    show_city_analysis()

elif st.session_state.page == "State":
    show_state_analysis()

elif st.session_state.page == "Watt":
    show_watt_analysis()

elif st.session_state.page == "Month":
    show_monthly_analysis()


# ================= DATE CLEANING =================
df = df_merged.copy()
df_base = df.copy()
df['PostingDate'] = pd.to_datetime(df['PostingDate'], errors='coerce')
df = df.dropna(subset=['PostingDate'])

df['FinancialYear'] = df['PostingDate'].apply(
    lambda x: f"{x.year}-{x.year+1}"
    if x.month >= 4
    else f"{x.year-1}-{x.year}"
)

df['Month'] = df['PostingDate'].dt.month_name()

# SIDEBAR FILTERS
st.sidebar.title("Filters")

financial_years = sorted(df['FinancialYear'].unique())
financial_years = [fy for fy in financial_years if fy not in ['0-1', '0 - 1', '0', 0]]

selected_fy = st.sidebar.selectbox(
    "📅 Financial Year",
    financial_years
)

df_filtered = df[df['FinancialYear'] == selected_fy]

month_list = sorted(df['Month'].dropna().unique())
selected_months = st.sidebar.multiselect(
    "Month",
    month_list,
    default=month_list
)

# Calculate previous period data for revenue comparison
previous_fy = None
try:
    start_year, end_year = selected_fy.split('-')
    previous_fy = f"{int(start_year) - 1}-{int(end_year) - 1}"
except Exception:
    previous_fy = None

if previous_fy is not None:
    df_previous = df[
        (df['FinancialYear'] == previous_fy) &
        (df['Month'].isin(selected_months))
    ]
else:
    df_previous = pd.DataFrame(columns=df.columns)

# Narrow the dataset to the selected financial year
# This is needed for the dashboard metrics below.
df = df[df['FinancialYear'] == selected_fy]

# APPLY FILTERS
df_filter = df[
    (df['FinancialYear'] == selected_fy) &
    (df['Month'].isin(selected_months))
]
st.markdown("""
<style>
.stButton > button {
    background-color: #C8E6C9;
    color: black;
    border-radius: 8px;
}
.stButton > button:hover {
    background-color: #A5D6A7;
    color: black;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style='text-align:center'>
<h1>📊 SALES ANALYTICS DASHBOARD</h1>
<p>Interactive Revenue Dashboard</p>
</div>
""", unsafe_allow_html=True)
# %%
type(main)

# %%
col1, col2, col3, col4 = st.columns(4)
total_revenue = df_filtered['Amount'].sum()
revenue = df_filter['Amount'].sum()


revenue_pct = 0
if total_revenue > 0:
    revenue_pct = (revenue / total_revenue) 
    # revenue_pct = revenue_pct * 100

col1.metric(
    "Revenue Share",
    f"₹{revenue/10000000:.2f} Cr"
)
col2.metric(
    "Customers",
    df_filter['BilltoCustomerNo'].nunique()
)

col3.metric(
    "Cities",
    df_filter['billToCity'].nunique()
)

col4.metric(
    "States",
    df_filter['state'].nunique()
)

st.markdown("---")
# %%
print(df1_clean.columns.tolist())

# %%
df1_clean.sort_values(by='Amount', ascending=False)

# %% [markdown]
# TOP PRODUCTS WITH SALES AMOUNT

# %%
import plotly.express as px
import pandas as pd

def to_crore(x):
    return f"₹ {x/1e7:.2f} Cr"

df['Amount_Cr'] = df['Amount'].apply(to_crore)

# =====================================================
# TOP 10 PRODUCT CATEGORIES
# =====================================================
import streamlit as st
import plotly.express as px
import pandas as pd

def show_product_pie(df_merged):

    st.subheader(" Product / Category Share (Pie Chart)")

    df = df_merged.copy()

    # ---------------- CLEAN DATA ----------------
    df = df[df['ItemCategoryCode'].fillna('').str.strip() != '']
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
    df = df.dropna(subset=['Amount'])

    # ---------------- TOP 10 ----------------
    top_df = (
        df.groupby('ItemCategoryCode', as_index=False)['Amount']
        .sum()
        .sort_values('Amount', ascending=False)
        .head(10)
    )

    # Convert to Crores (optional Power BI style)
    top_df['Amount_Cr'] = top_df['Amount'] / 1e7

    # ---------------- PIE CHART ----------------
    fig = px.pie(
        top_df,
        names='ItemCategoryCode',
        values='Amount_Cr',
        hole=0.5,   # donut style
        color_discrete_sequence=px.colors.qualitative.Pastel
    )

    fig.update_traces(
        textinfo='label+percent',
        textposition='outside',
        hovertemplate=
        "<b>Category:</b> %{label}<br>" +
        "<b>Revenue:</b> ₹ %{value:.2f} Cr<br>" +
        "<b>Share:</b> %{percent}<extra></extra>"
    )

    fig.update_layout(
        title="Top 10 Product Categories Share",
        title_x=0.5,
        height=600,
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend=dict(orientation="v", x=1.05)
    )

    st.plotly_chart(fig, use_container_width=True)

    # ---------------- INSIGHT ----------------
    top_item = top_df.iloc[0]

    st.success(
        f"🔥 Top Category: **{top_item['ItemCategoryCode']}** | "
        f"Revenue: **₹ {top_item['Amount_Cr']:.2f} Cr**"
    )
    # 🔥 2 graphs same page
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.plotly_chart(fig, use_container_width=True)
# %% [markdown]
# TOP 10 CUSTOMERS BY REVENUE 
st.header(" Top Customer Analysis")
# st.plotly_chart(fig, use_container_width=True)
# %%
print(df1_clean.columns)

# %%
df['Customer_Label'] = (
    df_filter['BilltoCustomerNo'].astype(str)
    + ' - '
    + df_filter['billToName'].astype(str)
)

top_customers = (
    df.groupby('Customer_Label', as_index=False)['Amount']
    .sum()
    .sort_values('Amount', ascending=False)
    .head(10)
)

# %%
df_filter[df_filter['BilltoCustomerNo'] == 'C000106'][['BilltoCustomerNo','billToName']].drop_duplicates()

## %% [markdown]
# TOP CUSTOMERS BY REVENUE

# %%
def show_top_customers():
    st.subheader("# Top  Customers by Revenue")
import plotly.express as px
import pandas as pd

# df = df_merged.copy()
df = df_filter.copy()

# ---------------- CLEAN DATA ----------------
df = df.dropna(subset=['BilltoCustomerNo', 'Amount'])
df = df[df['BilltoCustomerNo'].astype(str).str.strip() != '0']

df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
df = df.dropna(subset=['Amount'])
 
# ---------------- TOP 10 CUSTOMERS ----------------
top_customers = (
    df.groupby(['BilltoCustomerNo', 'billToName'], as_index=False)['Amount']
    .sum()
    .sort_values('Amount', ascending=False)
    .head(10)
)

# Convert to Crores
top_customers['Revenue_Cr'] = top_customers['Amount'] / 1e7
max_rev = top_customers['Revenue_Cr'].max()

# Pastel colors
pastel_colors= [
    "#1F3A5F",  # Navy Blue
    "#E67E22",  # Orange
    "#2E8B57",  # Green
    "#F7E6B2",  # Gold Yellow
    "#D88888",  # Red
    "#7C3AED",  # Purple
    "#EC4899",  # Pink
    "#06B6D4",  # Cyan
    "#4A5568",  # Gray
    "#8B5E3C",  # Brown
    "#91C347",  # Lime
    "#F97316"   # Bright Orange
]
# ---------------- PLOT ----------------
fig = px.pie(
    top_customers,
    names='billToName',
    values='Revenue_Cr',
    color_discrete_sequence=pastel_colors,
    hole=0.4,  # donut chart
    custom_data=['BilltoCustomerNo']
)
fig.update_traces(
    textinfo='label+percent',
    textposition='outside',

    hovertemplate=
    '<b>Customer:</b> %{label}<br>' +
    '<b>Customer No:</b> %{customdata[0]}<br>' +
    '<b>Revenue:</b> ₹ %{value:.2f} Cr<br>' +
    '<b>Contribution:</b> %{percent}' +
    '<extra></extra>'
)
fig.update_layout(
    title='Top 10 Customers Revenue Contribution',
    title_x=0.5,
     paper_bgcolor='#F5F5DC',
    plot_bgcolor="#EAF1F1",

    height = 500,
        hoverlabel=dict(
        bgcolor="#FFFDD0",
        font_color="black",
    ),
    width= 800,
    margin=dict(
        l=150,
        r=250,
        t=100,
        b=80
        ),

    yaxis=dict(

        autorange="reversed",
        title="Bill to Name",
        title_font=dict(size=18, family=" Arial Black",color="black"),
        tickfont=dict(size=14, family="Arial Black",color="black")
    ),

    xaxis=dict(
        title='Revenue (₹ Crores)',
        tickformat='.2f',
        ticksuffix=' Cr',
        title_font=dict(size=18, family="Arial Black"),
        tickfont=dict(size=14, family="Arial Black"),
        range=[0, max_rev * 1.25]
    ),
)
st.plotly_chart(fig, use_container_width=True)


# %%
df[['billToCity','state']].head()

# %% [markdown]
# TOP 10 CITIES BY REVENUE
st.header("#Top Cities Analysis")
# st.plotly_chart(fig, use_container_width=True)
# %%
print(df_filter.columns.tolist())

# %% 
import pandas as pd

# ---------------- CLEAN DATA ----------------
df = df.dropna(subset=['billToCity', 'Amount'])

df['Bill-to City'] = df['billToCity'].astype(str).str.strip()
df = df[df['billToCity'] != '']

df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
df = df.dropna(subset=['Amount'])

# ---------------- TOP 10 CITIES ----------------
def show_top_cities():
    st.subheader("#Top Cities ")
top_cities = (
    df.groupby(['billToCity', 'state'], as_index=False)['Amount']
      .sum()
      .sort_values('Amount', ascending=False)
      .head(10)
)

top_cities['Revenue_Cr'] = top_cities['Amount'] / 1e7
top_cities['Revenue_Percent'] = (top_cities['Amount'] / top_cities['Amount'].sum()) * 100

# ---------------- PLOT ----------------
fig = px.pie(
    top_cities,
    names='billToCity',
    values='Amount',
    hole=0.4,
    custom_data=['state'],
    color_discrete_sequence=[
    "#1F3A5F",  # Navy Blue
    "#E67E22",  # Orange
    "#2E8B57",  # Green
    "#F7E6B2",  # Gold Yellow
    "#D88888",  # Red
    "#7C3AED",  # Purple
    "#EC4899",  # Pink
    "#06B6D4",  # Cyan
    "#4A5568",  # Gray
    "#8B5E3C",  # Brown
    "#91C347",  # Lime
    "#F97316"   # Bright Orange
]
)

fig.update_traces(
    textinfo='label+percent',
    textposition='inside',
    hovertemplate=(
        '<b>State:</b> %{customdata[0]}<br>'
        '<b>Contribution:</b> %{percent:.2f}%<br>'
        '<extra></extra>'
    )
)

max_rev = top_cities['Revenue_Cr'].max()

fig.update_layout(
        title=' Top 10 Cities Revenue Contribution (%)',
        title_x=0.5,    
        paper_bgcolor='#F5F5DC',
    plot_bgcolor='#EAF1F1',
        
            height=500,   
    width=800,

      hoverlabel=dict(
        bgcolor="#FFFDD0",
        font_color="black"
    ),
    margin=dict(
        l=180,
        r=350,
        t=80,
        b=80
    )
)
st.plotly_chart(fig, use_container_width=True)

# %% [markdown]
# STATE WISE ANALYSIS
st.subheader("# Top States")
# %%
import plotly.express as px
import pandas as pd

# df = df_merged.copy()
df = df_filter.copy()
# ---------------- CLEAN DATA ----------------
df = df.dropna(subset=['state', 'Amount'])

df['state'] = df['state'].astype(str).str.strip()
df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
df = df.dropna(subset=['Amount'])

# ---------------- GROUP ----------------
state_sales = (
    df.groupby('state', as_index=False)['Amount']
      .sum()
      .sort_values('Amount', ascending=False)
      .head(10)
)

# Convert to Crores
state_sales['Revenue_Cr'] = state_sales['Amount'] / 1e7

# ---------------- PLOT ----------------
fig = px.pie(
    state_sales,
    names='state',
    values='Amount',
    hole=0.4,   # Donut chart
    color_discrete_sequence=[
    "#1F3A5F",  # Navy Blue
    "#E67E22",  # Orange
    "#2E8B57",  # Green
    "#F7E6B2",  # Gold Yellow
    "#D88888",  # Red
    "#7C3AED",  # Purple
    "#EC4899",  # Pink
    "#06B6D4",  # Cyan
    "#4A5568",  # Gray
    "#8B5E3C",  # Brown
    "#91C347",  # Lime
    "#F97316"   # Bright Orange
]
)
fig.update_traces(
    textinfo='label+percent',
    textposition='inside',

    hovertemplate=
    '<b>State:</b> %{label}<br>' +
    '<b>Contribution:</b> %{percent}<br>' +
    '<extra></extra>'
)

fig.update_layout(
    title='📊 Top States Revenue Contribution',
    title_x=0.5,

    paper_bgcolor='#F5F5DC',
    plot_bgcolor='#EAF1F1',

    height=500,
    width=800,

    hoverlabel=dict(
        bgcolor="#FFFDD0",
        font_color="black"
    ),

    margin=dict(
        l=50,
        r=50,
        t=80,
        b=50
    )
)

st.plotly_chart(fig, use_container_width=True)
# %% [markdown]
# WATT WISE ANALYSIS
st.subheader("#Watt Wise Analysis")
def show_Watt_Wise():
    # st.subheader("#Watt Wise Analysis")
    pass
# %%
# df = df_merged.copy()
df = df_filter.copy()
df['Watt'] = df['Description'].astype(str).str.extract(r'(\d+)\s*W', expand=False)
df['Watt'] = pd.to_numeric(df['Watt'], errors='coerce')

df = df.dropna(subset=['Watt', 'Amount'])

# %%
watt_wise = df.groupby('Watt', as_index=False)['Amount'].sum()

# %%
import pandas as pd
import plotly.express as px

# df = df_merged.copy()
df = df_filter.copy()

# -------- EXTRACT WATT --------
df['Watt'] = df['Description'].astype(str).str.extract(r'(\d+)\s*W')
df['Watt'] = pd.to_numeric(df['Watt'], errors='coerce')

df = df.dropna(subset=['Watt', 'Amount'])

# -------- GROUP --------
watt_df = (
    df.groupby('Watt')['Amount']
      .sum()
      .sort_values(ascending=False)
      .head(10)
      .reset_index()
)

# convert to crores
watt_df['Revenue_Cr'] = watt_df['Amount'] / 1e7

watt_df['Watt_label'] = watt_df['Watt'].astype(int).astype(str) + "W"

watt_df = watt_df.sort_values('Revenue_Cr', ascending=True)

# -------- PLOT --------
fig = px.pie(
    watt_df,
    names='Watt_label',
    values='Amount',
    hole=0.4,
    color_discrete_sequence=[
    "#1F3A5F",  # Navy Blue
    "#E67E22",  # Orange
    "#2E8B57",  # Green
    "#F7E6B2",  # Gold Yellow
    "#D88888",  # Red
    "#7C3AED",  # Purple
    "#EC4899",  # Pink
    "#06B6D4",  # Cyan
    "#4A5568",  # Gray
    "#8B5E3C",  # Brown
    "#91C347",  # Lime
    "#F97316"   # Bright Orange
]
)

# -------- STYLE UPDATE --------
fig.update_traces(
    textposition='inside',
    textinfo='percent+label',
    hovertemplate=
    '<b>%{label}</b><br>' +
    'Contribution: %{percent}<br>' +
    'Revenue: ₹ %{value:.2f} Cr<extra></extra>'
)
fig.update_layout(
    title=' Watt Wise Revenue Contribution',
    title_x=0.5,

    paper_bgcolor='#F5F5DC',
    plot_bgcolor='#EAF1F1',

    height=500,
    width=800,

    hoverlabel=dict(
        bgcolor="#FFFDD0",
        font_color="black"
    ),
    
    margin=dict(
        l=50,
        r=50,
        t=80,
        b=50
    )
)

st.plotly_chart(fig, use_container_width=True)

# %% [markdown]
# MONTHLY SALES ANALYSIS

# %% [markdown]
# Month ON MONTH TREND ANALYSIS
st.subheader("#Monthly Sales Analysis")
# %%
# df = df_merged.copy()
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

df = df_filter.copy()
def show_monthly_analysis():
    df = df_filter.copy()
    # st.header("📅 Monthly Sales Analysis")

    # ---------------- CLEAN DATA ----------------
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
    df['PostingDate'] = pd.to_datetime(df['PostingDate'], errors='coerce')
    df = df.dropna(subset=['Amount', 'PostingDate'])

    df['Year'] = df['PostingDate'].dt.year
    df['Month'] = df['PostingDate'].dt.strftime('%b')

    df = df[df['Year'] >= 2000]

    month_order = ["Apr","May","Jun",
                   "Jul","Aug","Sep","Oct","Nov","Dec","Jan","Feb","Mar",]

    years = sorted(df['Year'].unique())

    # ---------------- ALL YEARS DATA ----------------
    all_monthly = (
        df.groupby('Month')['Amount']
          .sum()
          .reindex(month_order, fill_value=0)
          .reset_index()
    )

    all_monthly.columns = ['Month', 'Amount']
    all_monthly['Revenue_Cr'] = all_monthly['Amount'] / 1e7
    return df, all_monthly, years, month_order

# call the function to execute the analysis
df, all_monthly, years, month_order = show_monthly_analysis()


# ---------------- FIGURE ----------------
fig = go.Figure()

fig.add_trace(
    go.Bar(
        x=all_monthly['Month'],
        y=all_monthly['Revenue_Cr'],
        text=[f"₹ {x:.2f} Cr" for x in all_monthly['Revenue_Cr']],
        textposition='outside',
        marker_color='#007A33',
        width=0.5,
        textfont=dict(size=14, color="black")
    )
)

# ---------------- DROPDOWN BUTTONS ----------------
buttons = []

# ALL YEARS
buttons.append(
    dict(
        label="All Years",
        method="update",
        args=[{
            "x": [all_monthly['Month']],
            "y": [all_monthly['Revenue_Cr']],
            "text": [[f"₹ {x:.2f} Cr" for x in all_monthly['Revenue_Cr']]]
        }]
    )
)

# YEAR WISE
for yr in years:
    temp = df[df['Year'] == yr]

    monthly = (
        temp.groupby('Month')['Amount']
            .sum()
            .reindex(month_order, fill_value=0)
            .reset_index()
    )

    monthly.columns = ['Month', 'Amount']
    monthly['Revenue_Cr'] = monthly['Amount'] / 1e7

    buttons.append(
        dict(
            label=str(yr),
            method="update",
            args=[{
                "x": [monthly['Month']],
                "y": [monthly['Revenue_Cr']],
                "text": [[f"₹ {x:.2f} Cr" for x in monthly['Revenue_Cr']]]
            }]
        )
    )

# ---------------- LAYOUT ----------------
fig.update_layout(
      hoverlabel=dict(
        bgcolor="white",
        font_color="black"
    ),
    title='📊 Year-wise Revenue Analysis',
    title_x=0.5,

    xaxis=dict(
        title=dict(
            text='<b>Month</b>',
            font=dict(size=1, color='black')
        ),
        tickfont=dict(size=12)
    ),
    yaxis=dict(
        title=dict(
            text='<b>Revenue (₹ Crores)</b>',
            font=dict(size=16, color='black')
        ),
        tickfont=dict(size=12)
    ),
    updatemenus=[
        dict(
            buttons=buttons,
            direction='down',
            x=1.02,
            y=1.15
        )
    ],

    paper_bgcolor='#F5F5DC',
    plot_bgcolor='#EAF1F1',
    height=600
)

# ---------------- STREAMLIT ----------------
st.plotly_chart(fig, use_container_width=True)

import plotly.express as px
import pandas as pd

def to_crore(x):
    return f"₹ {x/1e7:.2f} Cr"

df['Amount_Cr'] = df['Amount'].apply(to_crore)
# =====================================================
# TOP 10 PRODUCT CATEGORIES
# =====================================================
import streamlit as st
import plotly.express as px
import pandas as pd

def show_product_pie(df_merged):

    st.subheader("📊 Product / Category Share (Pie Chart)")

    df = df_merged.copy()

    # ---------------- CLEAN DATA ----------------
    df = df[df['ItemCategoryCode'].fillna('').str.strip() != '']
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
    df = df.dropna(subset=['Amount'])

    # ---------------- TOP 10 ----------------
    top_df = (
        df.groupby('ItemCategoryCode', as_index=False)['Amount']
        .sum()
        .sort_values('Amount', ascending=False)
        .head(10)
    )

    # Convert to Crores (optional Power BI style)
    top_df['Amount_Cr'] = top_df['Amount'] / 1e7

    # ---------------- PIE CHART ----------------
    fig = px.pie(
        top_df,
        names='ItemCategoryCode',
        values='Amount_Cr',
        hole=0.5,   # donut style
        color_discrete_sequence=px.colors.qualitative.Pastel
    )

    fig.update_traces(
        textinfo='label+percent',
        textposition='outside',
        hovertemplate=
        "<b>Category:</b> %{label}<br>" +
        "<b>Revenue:</b> ₹ %{value:.2f} Cr<br>" +
        "<b>Share:</b> %{percent}<extra></extra>"
    )

    fig.update_layout(
        title="Top 10 Product Categories Share",
        title_x=0.5,
        height=600,
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend=dict(orientation="v", x=1.05)
    )

    st.plotly_chart(fig, use_container_width=True)
    # 🔥 2 graphs same page
    col1, col2 = st.columns(2)
        # 🔥 2 graphs same page
    col1, col2 = st.columns(2)