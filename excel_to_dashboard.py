import streamlit as st
import pandas as pd
import re
import unicodedata

st.set_page_config(layout="wide", page_title="Trade Dashboard", page_icon="📊")

st.markdown("""
<style>
    /* Main app background and font */
    .stApp { background-color: #121212; }
    bo  , .st-b7 { color: #EAEAEA; }
    h1 { color: #FFFFFF; font-weight: 600; }
    h2 { color: #FFFFFF; font-weight: 500; } /* For Welcome Message */
    h3 {
        color: #A0A0A0; border-bottom: 1px solid #333333;
        padding-bottom: 8px; margin-top: 2.5rem; margin-bottom: 1rem; font-weight: 400;
    }
    
    /* Hover-effect Styling for Metrics on Main Dashboard */
    .metric-card {
        background-color: transparent; border: none; box-shadow: none; padding: 0;
        display: flex; flex-direction: column; justify-content: space-between; height: 100%;
    }
    [data-testid="stMetric"] {
        background-color: transparent; border: 1px solid #333333;
        border-radius: 12px; padding: 20px; transition: all 0.2s ease-in-out;
    }
    [data-testid="stMetric"]:hover {
        background-color: #0A84FF; transform: translateY(-5px);
        box-shadow: 0 12px 32px rgba(0,123,255,0.3); border-color: #0A84FF;
    }
    
    /* Breakdown container */
    .breakdown-container {
        background-color: #1E1E1E; padding: 20px; border-radius: 12px;
        margin-top: 1rem; border: 1px solid #333333;
    }
    
    /* Text color for metrics */
    [data-testid="stMetricLabel"] { color: #A0A0A0 !important; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; }
    
    .metric-card .stButton { margin-top: 10px; }
    
    /* Blue Expander Card Styling for Tabs 2 & 3 */
    [data-testid="stExpander"] {
        background-color: #0A84FF; border-radius: 12px; border: none;
        box-shadow: 0 8px 16px rgba(0,0,0,0.2); margin-bottom: 1rem;
    }
    [data-testid="stExpander"] summary { font-size: 1.1rem; font-weight: 600; color: #FFFFFF; }
    [data-testid="stExpander"] summary svg { fill: #FFFFFF; }
    
    /* Styling for metrics INSIDE the blue expander */
    [data-testid="stExpander"] [data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.5);
        border-radius: 8px; padding: 10px;
    }
    [data-testid="stExpander"] [data-testid="stMetric"]:hover {
        border-color: #FFFFFF; background-color: rgba(255, 255, 255, 0.2);
        transform: none; box-shadow: none;
    }
</style>
""", unsafe_allow_html=True)


USERS = {
    "admin": {"password": "admin@123", "role": "admin", "logo": None},
    "pragyawan": {"password": "pragyawan@123", "role": "PTPL", "logo": "assets/ptpl.png"},
    "iti": {"password": "iti@123", "role": "ITI", "logo": "assets/iti.png"},
    "vtl": {"password": "vtl@123", "role": "VTL", "logo": "assets/vtl.png"},
}


def find_column(pattern, df_columns):
    for col in df_columns:
        if re.search(pattern, str(col).lower()):
            return col
    return None


@st.cache_data
def load_and_process_data(uploaded_file):
    xls = pd.ExcelFile(uploaded_file)
    
    def find_sheet_name(pattern, sheet_list):
        pattern_lower = pattern.lower().strip()
        for name in sheet_list:
            if pattern_lower in name.lower().strip():
                return name
        return None

    all_sheet_names = xls.sheet_names
    summary_sheet = find_sheet_name("Summary", all_sheet_names)
    location_sheet = find_sheet_name("Location Wise", all_sheet_names)

    if not summary_sheet: raise ValueError(f"Could not find the 'Summary' sheet. Available sheets are: {all_sheet_names}")
    if not location_sheet: raise ValueError(f"Could not find the 'Location Wise' sheet. Available sheets are: {all_sheet_names}")

    df_summary = pd.read_excel(xls, sheet_name=summary_sheet, header=0)
    df_location_raw = pd.read_excel(xls, sheet_name=location_sheet, header=None)
    
    col_map = {
        "company": find_column(r'company', df_summary.columns), "trade": find_column(r'row labels', df_summary.columns),
        "offered": find_column(r'offered', df_summary.columns), "total_received": find_column(r'received according to portal total', df_summary.columns),
        "total_pending": find_column(r'pending according to portal total', df_summary.columns), "payment_30_count": find_column(r'count of 30% payment done', df_summary.columns),
        "balance_count": find_column(r'balance count as per vendor', df_summary.columns), "payment_30_amount": find_column(r'sum of 30% payment received', df_summary.columns),
        "balance_30": find_column(r'balance 30 %', df_summary.columns), "delivery": find_column(r'no. of delivery as per portal', df_summary.columns),
        "pending_delivery": find_column(r'difference between paid and delivery updated', df_summary.columns), "payment_70_amount": find_column(r'sum of 70% payment received', df_summary.columns),
        "balance_70": find_column(r'balance 70%', df_summary.columns), 
    }
    
    def clean_text(text):
        text = str(text if pd.notna(text) else '')
        text = unicodedata.normalize('NFKC', text)
        text = re.sub(r'\s+', ' ', text)
        return text.lower().strip()

    df = df_summary.copy()
    df['cleaned_company_label'] = df[col_map["company"]].apply(clean_text)
    
    numeric_cols = list(col_map.keys())[2:]
    for key in numeric_cols:
        if col_map[key] and col_map[key] in df.columns:
            df[col_map[key]] = pd.to_numeric(df[col_map[key]], errors='coerce')
    df.fillna(0, inplace=True)
    
    total_rows = df[df['cleaned_company_label'].str.contains('total', na=False)]
    trade_rows = df[~df['cleaned_company_label'].str.contains('total', na=False)]
    
    split_index = df_location_raw[df_location_raw.iloc[:, 0] == 'Company'].index
    if len(split_index) < 2: raise ValueError("Could not find two separate tables in 'Location Wise' sheet.")
    
    received_df_raw = df_location_raw.iloc[:split_index[1]].dropna(how='all')
    pending_df_raw = df_location_raw.iloc[split_index[1]:].dropna(how='all')
    
    def process_location_table(df_raw, value_name):
        df_raw.columns = df_raw.iloc[0]
        df_raw = df_raw[1:].dropna(subset=[df_raw.columns[0]])
        
        thirty_percent_val_col = find_column(r'thirty', df_raw.columns)
        if not thirty_percent_val_col:
            raise ValueError(f"Required column 'Thirty' not found in the 'Location Wise' sheet.")

        id_vars = [df_raw.columns[0], df_raw.columns[1], thirty_percent_val_col]
        location_vars = [col for col in df_raw.columns if col not in id_vars]
        
        df_tidy = df_raw.melt(id_vars=id_vars, value_vars=location_vars, var_name="Location", value_name=value_name)
        df_tidy[value_name] = pd.to_numeric(df_tidy[value_name], errors='coerce').fillna(0)
        df_tidy = df_tidy[df_tidy[value_name] > 0]
        return df_tidy, thirty_percent_val_col

    received_tidy, _ = process_location_table(received_df_raw, "Received Count")
    pending_tidy, thirty_percent_col_name = process_location_table(pending_df_raw, "Pending Count")

    location_final = pd.merge(received_tidy, pending_tidy, on=['Company', 'Row Labels', 'Location', thirty_percent_col_name], how='outer').fillna(0)
    
    col_map['thirty_percent_value'] = thirty_percent_col_name

    return total_rows, trade_rows, col_map, location_final


def main_dashboard(user_info):
    if 'active_breakdown' not in st.session_state:
        st.session_state.active_breakdown = None
    
    user_role = user_info['role']
    username = st.session_state['username']
    logo_url = user_info['logo']

    st.title("Trade Performance Dashboard")
    
    
    if logo_url:
        st.sidebar.image(logo_url, use_column_width=True)
    
    st.sidebar.header(f"Welcome, {username}")
    
    if user_role != 'admin':
        st.sidebar.write(f"Company: **{user_role}**")
        
    st.sidebar.divider()
    
    
    if user_role == 'admin':
        company_options = ["Combined", "PTPL", "VTL", "ITI"]
        selected_view = st.sidebar.selectbox(
            "Filter by Company", 
            company_options, 
            index=0, 
            key="admin_view_selector"
        )
    else:
        selected_view = user_role

    
    theme_css = """
        <style>
            .stApp { background-color: #121212; }
            body, .st-b7, h1, h2, [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: #EAEAEA !important; }
            h3 { color: #A0A0A0 !important; border-bottom: 1px solid #333333; }
            [data-testid="stMetric"] { background-color: transparent; border: 1px solid #333333; border-radius: 12px; padding: 20px; transition: all 0.2s ease-in-out; }
            [data-testid="stMetric"]:hover { background-color: #0A84FF; border-color: #0A84FF; transform: translateY(-5px); box-shadow: 0 12px 32px rgba(0,123,255,0.3); }
            .breakdown-container { background-color: #1E1E1E; border: 1px solid #333333; border-radius: 12px; padding: 20px; margin-top: 1rem; }
            [data-testid="stExpander"] { background-color: #0A84FF; border-radius: 12px; border: none; box-shadow: 0 8px 16px rgba(0,0,0,0.2); margin-bottom: 1rem; }
            [data-testid="stExpander"] summary, [data-testid="stExpander"] summary svg { color: #FFFFFF !important; fill: #FFFFFF !important; }
            [data-testid="stExpander"] [data-testid="stMetric"] { background-color: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.5); }
            [data-testid="stExpander"] [data-testid="stMetric"]:hover { border-color: #FFFFFF; background-color: rgba(255, 255, 255, 0.2); transform: none; box-shadow: none;}
        </style>
    """

    if selected_view == 'PTPL':
        theme_css = """
        <style>
            .stApp { background: linear-gradient(to bottom, #4f2310, #2d1409); color: white; }
            [data-testid="stSidebar"] > div:first-child { background: linear-gradient(to bottom, white, #FFDAB9); }
            div[data-testid="stSidebarUserContent"] p, div[data-testid="stSidebarUserContent"] h1, div[data-testid="stSidebarUserContent"] h2, div[data-testid="stSidebarUserContent"] label { color: #4f2310 !important; }
            h1, h2, h3, [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: #FFFFFF !important; }
            h3 { border-bottom-color: #8A6454; }
            [data-testid="stMetric"] { border-color: #8A6454; } [data-testid="stMetric"]:hover { border-color: #FFDAB9; background-color: #8A6454; }
            .breakdown-container { background-color: #693d2b; border-color: #8A6454; }
            [data-testid="stSidebar"] .stButton button {
            background-color: white;
            color: white !important;
            border: 1px solid #4f2310;
            }
            [data-testid="stSidebar"] .stButton button:hover {
            background-color: white;
            border-color: #693d2b;
            color: white !important;
            }
        </style>
        """
    elif selected_view == 'ITI':
        theme_css = """
        <style>
            .stApp { background: linear-gradient(to bottom, #1E3A8A, #E0FFFF); color: #FFF; }
            [data-testid="stSidebar"] > div:first-child { background: linear-gradient(to bottom, #48D1CC, #20B2AA); }
            div[data-testid="stSidebarUserContent"] p, div[data-testid="stSidebarUserContent"] h1, div[data-testid="stSidebarUserContent"] h2, div[data-testid="stSidebarUserContent"] label { color: white !important; }
            h1, h2, h3 { color: #FFF !important; } h3 { border-bottom-color: #AFEEEE; }
            [data-testid="stMetric"] { border-color: #AFEEEE; color: #008080 !important; }
            [data-testid="stMetricLabel"], [data-testid="stMetricValue"] { color: white !important; }
            [data-testid="stMetric"]:hover { border-color: #40E0D0; background-color: #F0FFFF;}
            [data-testid="stMetric"]:hover [data-testid="stMetricLabel"],
            [data-testid="stMetric"]:hover [data-testid="stMetricValue"] {
                color: #1E3A8A !important; /* Dark Blue on hover */
            }
            .breakdown-container { background-color: #F0FFFF; border-color: #AFEEEE; }
            
            [data-testid="stSidebar"] img {
                max-height: 100px;
                max-width: 100px; 
                margin: 0 auto 20px auto;
            }

            /* Style for the file uploader label */
            [data-testid="stFileUploader"] label {
                color: #008080 !important;
            }

            /* --- FINAL FIX for the 'Please upload...' info box using the exact selector --- */
            #root > div:nth-child(1) > div.withScreencast > div > div > section.stMain > div.stMainBlockContainer > div > div > div.stElementContainer > div > div {
                background-color: #E0FFFF !important;
                border: 1px solid #40E0D0 !important;
                border-radius: 0.5rem;
            }
            /* Target all text elements inside the info box */
            #root > div:nth-child(1) > div.withScreencast > div > div > section.stMain > div.stMainBlockContainer > div > div > div.stElementContainer > div > div * {
                color: #008080 !important;
            }
            [data-baseweb="tab"] {
            color: #1E3A8A !important; /* Dark Blue for active tab text */
            }
            [data-baseweb="tab"][aria-selected="true"] {
            color:  !important; /* Dark Blue for active tab text */
            }
            [data-baseweb="tab-highlight"] {
            background-color: #1E3A8A !important; /* Dark Blue for the indicator bar */
            }
        </style>
        """
    elif selected_view == 'VTL':
        theme_css = """
        <style>
            .stApp { background: linear-gradient(to bottom, white, #ADD8E6); color: #00008B; }
            [data-testid="stSidebar"] > div:first-child { background: linear-gradient(to bottom, #191970, #000080); }
            div[data-testid="stSidebarUserContent"] p, div[data-testid="stSidebarUserContent"] h1, div[data-testid="stSidebarUserContent"] h2, div[data-testid="stSidebarUserContent"] label { color: white !important; }
            h1, h2, h3 { color: #00008B !important; } h3 { border-bottom-color: #B0C4DE; }
            [data-testid="stMetric"] { border-color: #B0C4DE; color: #00008B !important; }
            [data-testid="stMetricLabel"], [data-testid="stMetricValue"] { color: #00008B !important; }
            [data-testid="stMetric"]:hover { border-color: #4682B4; background-color: #F0F8FF; }
            .breakdown-container { background-color: #F0F8FF; border-color: #B0C4DE; }
            #root > div:nth-child(1) > div.withScreencast > div > div > section.stMain > div.stMainBlockContainer > div > div > div.stElementContainer > div > div * {
                color: #008080 !important;
            }
            [data-baseweb="tab"] {
            color: #1E3A8A !important; /* Dark Blue for active tab text */
            }
            [data-baseweb="tab"][aria-selected="true"] {
            color:  !important; /* Dark Blue for active tab text */
            }
            [data-baseweb="tab-highlight"] {
            background-color: #1E3A8A !important; /* Dark Blue for the indicator bar */
            }
            [data-testid="stButton"] > button {
            color: white !important;
            background-color: #4682B4 !important; /* This is a SteelBlue color */
            border: none;
            }
                </style>
        """
    st.markdown(theme_css, unsafe_allow_html=True)

    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.session_state.pop('user_info', None)
        st.session_state.pop('username', None)
        st.session_state.pop('active_breakdown', None)
        st.rerun()

    
    uploaded_file = None
    if user_role == 'admin':
        uploaded_file = st.file_uploader("Upload your Excel file for an automated analysis", type=["xlsx", "xls"])
    else:
        default_file_path = "assets/master_data.xlsx"
        try:
            # The load_and_process_data function can handle a file path directly
            uploaded_file = default_file_path
            st.info("Displaying dashboard from the latest master data file.")
        except FileNotFoundError:
            st.error(f"Critical Error: The master data file at '{default_file_path}' was not found. Please contact the administrator.")
            st.stop() # Halt execution if the default file is missing
        except Exception as e:
            st.error(f"An error occurred while loading the master data file: {e}")
            st.stop() # Halt execution on other loading errors

    if not uploaded_file:
        st.info("Please upload an Excel file to begin.")
    else:
        try:
            total_rows, trade_rows, col_map, df_location = load_and_process_data(uploaded_file)

            if selected_view == "Combined":
                kpi_data = total_rows[total_rows['cleaned_company_label'] == 'grand total']
                display_trades = trade_rows
            else:
                kpi_data = total_rows[total_rows['cleaned_company_label'] == f'{selected_view.lower()} total']
                display_trades = trade_rows[trade_rows[col_map["company"]] == selected_view]
            
            kpi_groups = {
                "Key Financials 💰": [{"label": "Total Payments Received", "key": "total_received", "metric_format": "₹{:,.2f}", "df_format": "₹ %.2f"}, {"label": "Total Pending Amount", "key": "total_pending", "metric_format": "₹{:,.2f}", "df_format": "₹ %.2f"}],
                "Logistics & Operations 📦": [{"label": "Total Offered", "key": "offered", "metric_format": "{:,.0f}", "df_format": "%d"}, {"label": "Deliveries Made", "key": "delivery", "metric_format": "{:,.0f}", "df_format": "%d"}, {"label": "Items Pending Delivery", "key": "pending_delivery", "metric_format": "{:,.0f}", "df_format": "%d"}],
                "Payment Status (30% Advance)": [{"label": "Sum of 30% Payments", "key": "payment_30_amount", "metric_format": "₹{:,.2f}", "df_format": "₹ %.2f"}, {"label": "Balance 30%", "key": "balance_30", "metric_format": "₹{:,.2f}", "df_format": "₹ %.2f"}, {"label": "30% Payment Count", "key": "payment_30_count", "metric_format": "{:,.0f}", "df_format": "%d"}],
                "Payment Status (70% Balance)": [{"label": "Sum of 70% Payments", "key": "payment_70_amount", "metric_format": "₹{:,.2f}", "df_format": "₹ %.2f"}, {"label": "Balance 70%", "key": "balance_70", "metric_format": "₹{:,.2f}", "df_format": "₹ %.2f"}, {"label": "Overall Balance Count", "key": "balance_count", "metric_format": "{:,.0f}", "df_format": "%d"}]
            }
            
            tab1, tab2, tab3 = st.tabs(["📊 Dashboard Summary", "📋 Trade-wise Details", "📍 Location-wise Payments"])

            with tab1:
                st.markdown(f"### Overall Performance: {selected_view}")
                if kpi_data.empty:
                    st.error(f"Error: Could not find the summary row for '{selected_view}'.")
                else:
                    kpi_row = kpi_data.iloc[0]
                    for group_title, kpis in kpi_groups.items():
                        st.subheader(group_title)
                        cols = st.columns(len(kpis))
                        for i, kpi in enumerate(kpis):
                            with cols[i]:
                                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                                value = kpi_row.get(col_map.get(kpi["key"]), 0)
                                st.metric(label=kpi["label"], value=kpi["metric_format"].format(value))
                                button_label = "Close" if st.session_state.active_breakdown == kpi['key'] else "View Breakdown"
                                if st.button(button_label, key=f"btn_{kpi['key']}", use_container_width=True):
                                    st.session_state.active_breakdown = None if st.session_state.active_breakdown == kpi['key'] else kpi['key']
                                    st.rerun()
                                st.markdown('</div>', unsafe_allow_html=True)
                        active_kpi_in_group = next((k for k in kpis if k['key'] == st.session_state.active_breakdown), None)
                        if active_kpi_in_group:
                            with st.container():
                                st.markdown('<div class="breakdown-container">', unsafe_allow_html=True)
                                st.markdown(f"#### Breakdown for: **{active_kpi_in_group['label']}**")
                                metric_col, trade_col, company_col = col_map.get(active_kpi_in_group['key']), col_map.get('trade'), col_map.get('company')
                                cols_to_show, rename_map = [trade_col], {trade_col: "Trade"}
                                if selected_view == "Combined":
                                    cols_to_show.append(company_col)
                                    rename_map[company_col] = "Company"
                                cols_to_show.append(metric_col)
                                rename_map[metric_col] = active_kpi_in_group['label']
                                breakdown_df = display_trades[cols_to_show].copy().rename(columns=rename_map)
                                col_config = { active_kpi_in_group['label']: st.column_config.NumberColumn(format=active_kpi_in_group['df_format']) }
                                st.dataframe(breakdown_df, use_container_width=True, column_config=col_config, hide_index=True)
                                st.markdown('</div>', unsafe_allow_html=True)

            with tab2:
                st.markdown(f"### Trade-wise Details: {selected_view}")
                trade_emojis = {'potter': '🏺', 'washerman': '🧺', 'metalsmith': '⚙️', 'sculptor': '🗿', 'fishingnet': '🕸️', 'hammer': '🔨', 'armourer': '🛡️', 'boatmaker': '🚤', 'barber': '💈', 'default': '🔧'}
                if display_trades.empty:
                    st.info("No trade data to display for the selected view.")
                else:
                    for _, row in display_trades.iterrows():
                        trade_name = str(row[col_map["trade"]]).strip()
                        if not trade_name: continue
                        company_name = row.get(col_map["company"], "")
                        emoji = trade_emojis.get(trade_name.lower(), trade_emojis['default'])
                        expander_title = f"{emoji} {trade_name}"
                        if selected_view == "Combined" and company_name:
                            expander_title += f" ({company_name})"
                        with st.expander(expander_title):
                            for group_title, kpis in kpi_groups.items():
                                st.markdown(f"**{group_title.split(' ')[0]}**")
                                cols = st.columns(len(kpis))
                                for i, kpi in enumerate(kpis):
                                    with cols[i]:
                                        value = row.get(col_map.get(kpi["key"]), 0)
                                        st.metric(label=kpi["label"], value=kpi["metric_format"].format(value))
                                st.divider()

            with tab3:
                st.markdown("### Location-wise 30% Payment Data")
                if kpi_data.empty:
                    st.error("Cannot display KPI cards because the main summary row is missing.")
                else:
                    kpi_row = kpi_data.iloc[0]
                    st.subheader("Overall 30% Payment Status")
                    
                    thirty_percent_col = col_map['thirty_percent_value']
                    df_location['Pending Amount'] = df_location['Pending Count'] * pd.to_numeric(df_location[thirty_percent_col], errors='coerce')
                    total_pending_amount_30 = df_location['Pending Amount'].sum()
                    
                    c1, c2, c3 = st.columns(3)
                    with c1: st.metric("Total 30% Payments Received (Count)", f"{int(df_location['Received Count'].sum()):,}")
                    with c2: st.metric("Total 30% Payments Pending (Count)", f"{int(df_location['Pending Count'].sum()):,}")
                    with c3: st.metric("Total Pending Amount (30%)", f"₹{total_pending_amount_30:,.2f}")

                    st.divider()
                    st.subheader("Trade-wise Breakdown by Location")

                    for _, trade_row in display_trades.iterrows():
                        trade_name = trade_row[col_map["trade"]]
                        company_name = trade_row[col_map["company"]]
                        received_count_total = int(trade_row.get(col_map.get('payment_30_count'), 0))
                        offered_total = int(trade_row.get(col_map.get('offered'), 0))
                        emoji = trade_emojis.get(trade_name.lower(), trade_emojis['default'])
                        expander_title = f"{emoji} {trade_name} "
                        if selected_view == "Combined": expander_title += f"({company_name}) "
                        expander_title += f"— Received: {received_count_total} / {offered_total}"
                        
                        with st.expander(expander_title):
                            location_df_filtered = df_location[df_location['Row Labels'] == trade_name]
                            if selected_view != "Combined":
                                location_df_filtered = location_df_filtered[location_df_filtered['Company'] == company_name]
                            
                            if location_df_filtered.empty:
                                st.info("No location-specific data found for this trade.")
                                continue
                            
                            final_df = location_df_filtered[['Location', 'Received Count', 'Pending Count', 'Pending Amount']].sort_values(by="Pending Count", ascending=False)
                            col_config = { "Pending Amount": st.column_config.NumberColumn(label="Pending Amount (₹)", format="₹ %.2f") }
                            st.dataframe(final_df, use_container_width=True, hide_index=True, column_config=col_config)

        except Exception as e:
            st.error(f"A critical error occurred. Please check your Excel file. Error: {e}")


if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("Dashboard Login")
    st.write("Please enter your credentials to continue.")
    
    # MODIFICATION: Wrap login inputs in a form
    with st.form(key='login_form'):
        username = st.text_input("User ID")
        password = st.text_input("Password", type="password")
        
        # This button is now the form's submit trigger
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if username in USERS and USERS[username]['password'] == password:
                st.session_state['logged_in'] = True
                st.session_state['user_info'] = USERS[username]
                st.session_state['username'] = username
                st.rerun()
            else:
                st.error("The username or password you entered is incorrect.")
else:
    main_dashboard(st.session_state['user_info'])