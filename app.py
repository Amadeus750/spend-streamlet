import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="Spend Analytics Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# No custom CSS - using default Streamlit light theme


def clean_currency(value):
    """Convert currency string to float."""
    if pd.isna(value):
        return 0.0
    # Convert to string if not already
    s = str(value)
    # Check for negative (parentheses format)
    is_negative = '(' in s and ')' in s
    # Remove $, commas, parentheses
    s = s.replace('$', '').replace(',', '').replace('(', '').replace(')', '')
    try:
        result = float(s)
        return -result if is_negative else result
    except ValueError:
        return 0.0


@st.cache_data
def load_data():
    """Load and prepare the spend data."""
    df = pd.read_parquet('data/spend_data_categorized.parquet')
    # Clean column names for display
    df['Fiscal_Year'] = df['Spend_Data_Posting_Date_Fiscal_Year'].astype(str)
    df['Quarter'] = df['Spend_Data_Posting_Date_Fiscal_Year_and_Quarter']
    # Clean and convert currency strings to numeric
    df['Spend_Amount'] = df['Spend_Data_Vendor_Invoice_Amount_LC2_USD_'].apply(clean_currency)
    return df


def format_currency(value):
    """Format large numbers as currency."""
    try:
        value = float(value)
    except (ValueError, TypeError):
        return "$0.00"
    
    if value >= 1_000_000:
        return f"${value/1_000_000:,.2f}M"
    elif value >= 1_000:
        return f"${value/1_000:,.1f}K"
    return f"${value:,.2f}"




# Load data
df = load_data()

# Header
st.title("💰 Enterprise Managed Software Spend Analytics Dashboard")
st.caption("**Sourcing Portfolio:** Technology  •  **Sourcing Category:** Enterprise Managed Software")
st.divider()

# Sidebar filters
with st.sidebar:
    st.header("🎛️ Filters")
    
    # Get default values
    years = sorted(df['Fiscal_Year'].unique())
    quarters = sorted(df['Quarter'].dropna().unique())
    categories = sorted(df['category'].dropna().unique())
    geos = sorted(df['Spend_Data_Geo'].dropna().unique())
    divisions = sorted(df['Spend_Data_Division_Description'].dropna().unique())
    organizations = sorted(df['Spend_Data_Organization'].dropna().unique())
    business_units = sorted(df['Spend_Data_Business_Unit_Description'].dropna().unique())
    all_vendors = sorted(df['Spend_Data_Vendor_Name'].dropna().unique())
    
    # Clear all filters button
    if st.button("🗑️ Clear All Filters", use_container_width=True):
        # Reset all filter keys to defaults
        st.session_state["filter_years"] = years  # All years selected by default
        st.session_state["filter_quarters"] = []
        st.session_state["filter_categories"] = []
        st.session_state["filter_subcategories"] = []
        st.session_state["filter_geos"] = []
        st.session_state["filter_divisions"] = []
        st.session_state["filter_organizations"] = []
        st.session_state["filter_business_units"] = []
        st.session_state["filter_vendor_search"] = ""
        st.rerun()
    
    st.markdown("---")
    
    # Time Filters
    st.subheader("📅 Time Period")
    
    selected_years = st.multiselect(
        "Fiscal Year",
        options=years,
        default=years,
        help="Select one or more fiscal years",
        key="filter_years"
    )
    
    selected_quarters = st.multiselect(
        "Fiscal Quarter",
        options=quarters,
        default=[],
        help="Select quarters to filter (leave empty for all)",
        key="filter_quarters"
    )
    
    st.divider()
    st.subheader("📁 Categories")
    
    selected_categories = st.multiselect(
        "Category",
        options=categories,
        default=[],
        help="Select categories to filter (leave empty for all)",
        key="filter_categories"
    )
    
    if selected_categories:
        available_subcategories = sorted(
            df[df['category'].isin(selected_categories)]['sub_category'].dropna().unique()
        )
    else:
        available_subcategories = sorted(df['sub_category'].dropna().unique())
    
    selected_subcategories = st.multiselect(
        "Sub-Category",
        options=available_subcategories,
        default=[],
        help="Select sub-categories to filter (leave empty for all)",
        key="filter_subcategories"
    )
    
    st.divider()
    st.subheader("🌍 Organization")
    
    selected_geos = st.multiselect(
        "Geo/Region",
        options=geos,
        default=[],
        help="Select geographic regions (leave empty for all)",
        key="filter_geos"
    )
    
    selected_divisions = st.multiselect(
        "Division",
        options=divisions,
        default=[],
        help="Select divisions (leave empty for all)",
        key="filter_divisions"
    )
    
    selected_organizations = st.multiselect(
        "Organization",
        options=organizations,
        default=[],
        help="Select organizations (leave empty for all)",
        key="filter_organizations"
    )
    
    selected_business_units = st.multiselect(
        "Business Unit",
        options=business_units,
        default=[],
        help="Select business units (leave empty for all)",
        key="filter_business_units"
    )
    
    st.divider()
    st.subheader("🔍 Vendor")
    
    vendor_search = st.text_input(
        "Search Vendor",
        placeholder="Type to search vendors...",
        help="Type to see matching vendors",
        key="filter_vendor_search"
    )
    
    selected_vendor = None
    if vendor_search:
        matching_vendors = [v for v in all_vendors if vendor_search.lower() in v.lower()]
        
        if matching_vendors:
            display_vendors = matching_vendors[:10]
            if len(matching_vendors) > 10:
                st.caption(f"Showing top 10 of {len(matching_vendors)} matches")
            
            selected_vendor = st.selectbox(
                "Select vendor",
                options=[""] + display_vendors,
                format_func=lambda x: "-- Select a vendor --" if x == "" else x,
                help="Select a vendor from matches"
            )
        else:
            st.caption("No matching vendors found")

# Apply filters
filtered_df = df.copy()

# Time filters
if selected_years:
    filtered_df = filtered_df[filtered_df['Fiscal_Year'].isin(selected_years)]

if selected_quarters:
    filtered_df = filtered_df[filtered_df['Quarter'].isin(selected_quarters)]

# Category filters
if selected_categories:
    filtered_df = filtered_df[filtered_df['category'].isin(selected_categories)]

if selected_subcategories:
    filtered_df = filtered_df[filtered_df['sub_category'].isin(selected_subcategories)]

# Organization filters
if selected_geos:
    filtered_df = filtered_df[filtered_df['Spend_Data_Geo'].isin(selected_geos)]

if selected_divisions:
    filtered_df = filtered_df[filtered_df['Spend_Data_Division_Description'].isin(selected_divisions)]

if selected_organizations:
    filtered_df = filtered_df[filtered_df['Spend_Data_Organization'].isin(selected_organizations)]

if selected_business_units:
    filtered_df = filtered_df[filtered_df['Spend_Data_Business_Unit_Description'].isin(selected_business_units)]

# Vendor filter - use exact match if vendor selected, otherwise partial match
if selected_vendor:
    filtered_df = filtered_df[filtered_df['Spend_Data_Vendor_Name'] == selected_vendor]
elif vendor_search:
    filtered_df = filtered_df[
        filtered_df['Spend_Data_Vendor_Name'].str.contains(vendor_search, case=False, na=False)
    ]

# KPI Metrics Row
col1, col2, col3, col4 = st.columns(4)

total_spend = filtered_df['Spend_Amount'].sum()
num_vendors = filtered_df['Spend_Data_Vendor_Number'].nunique()
num_transactions = len(filtered_df)
num_categories = filtered_df['category'].nunique()

with col1:
    st.metric("Total Spend", format_currency(total_spend))

with col2:
    st.metric("Unique Vendors", f"{num_vendors:,}")

with col3:
    st.metric("Transactions", f"{num_transactions:,}")

with col4:
    st.metric("Categories", f"{num_categories}")

st.markdown("<br>", unsafe_allow_html=True)

# Charts Row 1
col_left, col_right = st.columns(2)

# Define color palette
color_palette = px.colors.sequential.Plasma

with col_left:
    st.subheader("📊 Spend by Category")
    
    category_spend = filtered_df.groupby('category')['Spend_Amount'].sum().reset_index()
    category_spend = category_spend.sort_values('Spend_Amount', ascending=True).tail(10)
    
    fig_category = px.bar(
        category_spend,
        x='Spend_Amount',
        y='category',
        orientation='h',
        color='Spend_Amount',
        color_continuous_scale='Plasma',
        labels={'Spend_Amount': 'Spend ($)', 'category': 'Category'}
    )
    fig_category.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e8f0', size=13),
        showlegend=False,
        coloraxis_showscale=False,
        xaxis=dict(gridcolor='rgba(99, 102, 241, 0.1)', tickfont=dict(size=12)),
        yaxis=dict(gridcolor='rgba(99, 102, 241, 0.1)', tickfont=dict(size=12)),
        margin=dict(l=0, r=0, t=20, b=0),
        height=400
    )
    st.plotly_chart(fig_category, use_container_width=True)

with col_right:
    st.subheader("🥧 Spend Distribution")
    
    category_spend_pie = filtered_df.groupby('category')['Spend_Amount'].sum().reset_index()
    category_spend_pie = category_spend_pie.nlargest(8, 'Spend_Amount')
    
    fig_pie = px.pie(
        category_spend_pie,
        values='Spend_Amount',
        names='category',
        color_discrete_sequence=px.colors.sequential.Plasma,
        hole=0.4
    )
    fig_pie.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e8f0', size=13),
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02,
            font=dict(size=11)
        ),
        margin=dict(l=0, r=120, t=20, b=0),
        height=400
    )
    fig_pie.update_traces(textposition='inside', textinfo='percent', textfont_size=13)
    st.plotly_chart(fig_pie, use_container_width=True)

# Charts Row 2
col_left2, col_right2 = st.columns(2)

with col_left2:
    st.subheader("📈 Spend Trend")
    
    yearly_spend = filtered_df.groupby('Fiscal_Year')['Spend_Amount'].sum().reset_index()
    yearly_spend = yearly_spend.sort_values('Fiscal_Year')
    
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=yearly_spend['Fiscal_Year'],
        y=yearly_spend['Spend_Amount'],
        mode='lines+markers',
        line=dict(color='#818cf8', width=3),
        marker=dict(size=12, color='#c084fc', line=dict(width=2, color='#818cf8')),
        fill='tozeroy',
        fillcolor='rgba(129, 140, 248, 0.2)'
    ))
    fig_trend.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e8f0', size=13),
        xaxis=dict(gridcolor='rgba(99, 102, 241, 0.1)', title='Fiscal Year', tickfont=dict(size=12)),
        yaxis=dict(gridcolor='rgba(99, 102, 241, 0.1)', title='Spend ($)', tickfont=dict(size=12)),
        margin=dict(l=0, r=0, t=20, b=0),
        height=350
    )
    st.plotly_chart(fig_trend, use_container_width=True)

with col_right2:
    st.subheader("🏢 Top 10 Vendors")
    
    vendor_spend = filtered_df.groupby('Spend_Data_Vendor_Name')['Spend_Amount'].sum().reset_index()
    vendor_spend = vendor_spend.nlargest(10, 'Spend_Amount').sort_values('Spend_Amount', ascending=True)
    
    fig_vendors = px.bar(
        vendor_spend,
        x='Spend_Amount',
        y='Spend_Data_Vendor_Name',
        orientation='h',
        color='Spend_Amount',
        color_continuous_scale='Viridis',
        labels={'Spend_Amount': 'Spend ($)', 'Spend_Data_Vendor_Name': 'Vendor'}
    )
    fig_vendors.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e8f0', size=13),
        showlegend=False,
        coloraxis_showscale=False,
        xaxis=dict(gridcolor='rgba(99, 102, 241, 0.1)', tickfont=dict(size=12)),
        yaxis=dict(gridcolor='rgba(99, 102, 241, 0.1)', tickfont=dict(size=11)),
        margin=dict(l=0, r=0, t=20, b=0),
        height=350
    )
    st.plotly_chart(fig_vendors, use_container_width=True)

# Geo & Organization Breakdown
st.subheader("🌍 Geographic & Organization Breakdown")

col_geo, col_org = st.columns(2)

with col_geo:
    geo_spend = filtered_df.groupby('Spend_Data_Geo')['Spend_Amount'].sum().reset_index()
    geo_spend = geo_spend.sort_values('Spend_Amount', ascending=False)
    
    fig_geo = px.pie(
        geo_spend,
        values='Spend_Amount',
        names='Spend_Data_Geo',
        color_discrete_sequence=px.colors.sequential.Viridis,
        hole=0.4,
        title='Spend by Geo/Region'
    )
    fig_geo.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e8f0', size=12),
        showlegend=True,
        legend=dict(font=dict(size=11)),
        margin=dict(l=0, r=0, t=40, b=0),
        height=350,
        title=dict(font=dict(size=14, color='#c084fc'))
    )
    fig_geo.update_traces(textposition='inside', textinfo='percent+label', textfont_size=11)
    st.plotly_chart(fig_geo, use_container_width=True)

with col_org:
    org_spend = filtered_df.groupby('Spend_Data_Organization')['Spend_Amount'].sum().reset_index()
    org_spend = org_spend.nlargest(10, 'Spend_Amount').sort_values('Spend_Amount', ascending=True)
    
    fig_org = px.bar(
        org_spend,
        x='Spend_Amount',
        y='Spend_Data_Organization',
        orientation='h',
        color='Spend_Amount',
        color_continuous_scale='Plasma',
        labels={'Spend_Amount': 'Spend ($)', 'Spend_Data_Organization': 'Organization'},
        title='Top 10 Organizations by Spend'
    )
    fig_org.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e8f0', size=12),
        showlegend=False,
        coloraxis_showscale=False,
        xaxis=dict(gridcolor='rgba(99, 102, 241, 0.1)', tickfont=dict(size=11)),
        yaxis=dict(gridcolor='rgba(99, 102, 241, 0.1)', tickfont=dict(size=10)),
        margin=dict(l=0, r=0, t=40, b=0),
        height=350,
        title=dict(font=dict(size=14, color='#c084fc'))
    )
    st.plotly_chart(fig_org, use_container_width=True)

# Sub-category Analysis
st.subheader("📋 Sub-Category Breakdown")

col_tree, col_bar = st.columns([1, 1])

with col_tree:
    # Treemap - better for hierarchical data with many categories
    treemap_df = filtered_df.dropna(subset=['category', 'sub_category']).copy()
    
    # Aggregate and filter to top subcategories per category for readability
    subcategory_agg = treemap_df.groupby(['category', 'sub_category'])['Spend_Amount'].sum().reset_index()
    
    # Keep only subcategories with meaningful spend (top 80% of total)
    total_spend_val = subcategory_agg['Spend_Amount'].sum()
    subcategory_agg = subcategory_agg.sort_values('Spend_Amount', ascending=False)
    subcategory_agg['cumsum'] = subcategory_agg['Spend_Amount'].cumsum()
    subcategory_agg = subcategory_agg[subcategory_agg['cumsum'] <= total_spend_val * 0.85]
    
    if len(subcategory_agg) > 0:
        fig_treemap = px.treemap(
            subcategory_agg,
            path=['category', 'sub_category'],
            values='Spend_Amount',
            color='Spend_Amount',
            color_continuous_scale='Plasma'
        )
        fig_treemap.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e2e8f0', size=12),
            margin=dict(l=10, r=10, t=30, b=10),
            height=450,
            coloraxis_showscale=False
        )
        fig_treemap.update_traces(
            textfont=dict(size=13),
            textinfo='label+percent parent'
        )
        st.plotly_chart(fig_treemap, use_container_width=True)
    else:
        st.info("No subcategory data available for treemap.")

with col_bar:
    # Top 15 subcategories bar chart - clear and readable
    subcategory_spend = filtered_df.groupby('sub_category')['Spend_Amount'].sum().reset_index()
    subcategory_spend = subcategory_spend.nlargest(15, 'Spend_Amount').sort_values('Spend_Amount', ascending=True)
    
    fig_subcat = px.bar(
        subcategory_spend,
        x='Spend_Amount',
        y='sub_category',
        orientation='h',
        color='Spend_Amount',
        color_continuous_scale='Viridis',
        labels={'Spend_Amount': 'Spend ($)', 'sub_category': 'Sub-Category'},
        title='Top 15 Sub-Categories'
    )
    fig_subcat.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e8f0', size=12),
        showlegend=False,
        coloraxis_showscale=False,
        xaxis=dict(gridcolor='rgba(99, 102, 241, 0.1)', tickfont=dict(size=11)),
        yaxis=dict(gridcolor='rgba(99, 102, 241, 0.1)', tickfont=dict(size=11)),
        margin=dict(l=0, r=0, t=40, b=0),
        height=450,
        title=dict(font=dict(size=14, color='#c084fc'))
    )
    st.plotly_chart(fig_subcat, use_container_width=True)

# Data Table
st.subheader("📑 Detailed Spend Data")

# Select columns to display
display_columns = [
    'Fiscal_Year',
    'Quarter', 
    'Spend_Data_Vendor_Name',
    'category',
    'sub_category',
    'Spend_Amount',
    'Spend_Data_Geo',
    'Spend_Data_Division_Description',
    'Spend_Data_Organization',
    'Spend_Data_Business_Unit_Description',
    'Spend_Data_Line_Item_Text'
]

display_df = filtered_df[display_columns].copy()
display_df.columns = [
    'Year', 'Quarter', 'Vendor', 'Category', 'Sub-Category', 
    'Amount ($)', 'Geo', 'Division', 'Organization', 'Business Unit', 'Line Item'
]

# Format the amount column
display_df['Amount ($)'] = display_df['Amount ($)'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "N/A")

st.dataframe(
    display_df,
    use_container_width=True,
    height=400,
    hide_index=True
)

# Export Button
st.markdown("<br>", unsafe_allow_html=True)
col_export1, col_export2, col_export3 = st.columns([1, 1, 2])

with col_export1:
    # CSV Export
    csv_data = display_df.to_csv(index=False)
    st.download_button(
        label="📥 Download CSV",
        data=csv_data,
        file_name="spend_data_filtered.csv",
        mime="text/csv",
        help="Download filtered data as CSV"
    )

with col_export2:
    # Excel Export
    from io import BytesIO
    excel_buffer = BytesIO()
    display_df.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_data = excel_buffer.getvalue()
    st.download_button(
        label="📥 Download Excel",
        data=excel_data,
        file_name="spend_data_filtered.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Download filtered data as Excel"
    )

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #64748b;'>Spend Analytics Dashboard | Data filtered: "
    f"{num_transactions:,} transactions</p>",
    unsafe_allow_html=True
)
