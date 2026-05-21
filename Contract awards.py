import streamlit as st
import pandas as pd
import os
from datetime import date
from utils import load_data
st.set_page_config(
    page_title="SEAP IT dashboard", 
    layout="wide"
)

st.title("Analysis of the IT sector of public procurement in Romania")
df_all_ca = load_data("seap_dataset/contract_awards")
most_recent_date = df_all_ca['caPublicationDate'].max()
st.markdown(f"""
This dashboard visualizes data from the IT sector of public procurement in Romania. The data is publicly available and was extracted from the SEAP platform.
This analysis also includes anomaly detection using Isolation Forest for contract awards.
            
Latest contract published on: **{most_recent_date}**. Updates daily.
""")

col_sel, col_start, col_end = st.columns([2, 1, 1])

with col_sel:
    procedura = st.selectbox(
        "Procedure type:",
        ["Open auctions", "Negotiation without prior notice"]
    )

current_file = "open_auctions.parquet" if procedura == "Open auctions" else "closed_auctions.parquet"
df_raw = load_data(os.path.join("seap_dataset/contract_awards_IF/", current_file))
df_all_contracts = load_data("seap_dataset/contracts/") 

def write_general_stats():
    anomalii = df[df['anomaly_label'] == -1]
    single_bidder_count = len(df[df['numberOfReceivedOffers'] == 1])

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Number of awards", f"{len(df):,}")
    with m2:
        st.metric("Number of anomalies", len(anomalii), 
                    delta=f"{(len(anomalii)/len(df)*100):.2f}%", delta_color="inverse")
    with m3:
        st.metric("Single bidder awards", single_bidder_count, 
                    delta=f"{(single_bidder_count/len(df)*100):.2f}%", delta_color="off")

def write_monthly_trends():
    st.divider()
    col_chart_title, col_chart_sel = st.columns([2, 1])
    with col_chart_title:
        st.write("### Monthly Trends")
    with col_chart_sel:
        metric_choice = st.selectbox(
            "Select metric to visualize:",
            ["Average number of offers", "Total value", "Number of contracts"]
        )

    if metric_choice == "Number of contracts":
        merged = df_all_contracts.merge(df[['caNoticeId', 'caPublicationDate']], on='caNoticeId')
        timeline_df = merged.set_index('caPublicationDate').resample('MS').size().reset_index()
        
        timeline_df.columns = ['Month', 'Contracts']
        
        timeline_df['Contracts'] = timeline_df['Contracts'].astype(int)
        st.line_chart(timeline_df, x='Month', y='Contracts', height=350)
    else:
        metric_map = {
            "Average number of offers": ("numberOfReceivedOffers", "mean", "Average Offers"),
            "Total value": ("totalAcquisitionValue", "sum", "Total RON")
        }
        col_name, agg_func, y_col = metric_map[metric_choice]

        timeline_df = df.groupby(pd.Grouper(key='caPublicationDate', freq='MS'))[col_name].agg(agg_func).reset_index()
        timeline_df.columns = ['Month', y_col]
        timeline_df[y_col] = timeline_df[y_col].round(2)
        st.line_chart(timeline_df, x='Month', y=y_col, height=350)

def write_all_dataset():
    st.divider()
    
    col_title, col_filter = st.columns([3, 1])
    
    with col_title:
        st.write("### Explore the entire dataset")
    
    with col_filter:
        view_choice = st.selectbox(
            "Filter by:",
            ["All", "Anomalies"],
            label_visibility="collapsed"
        )

    df_to_display = df.copy()
    if view_choice == "Anomalies":
        df_to_display = df_to_display[df_to_display['anomaly_label'] == -1]

    st.dataframe(
        df_to_display.sort_values(by='anomaly_score'), 
        width='stretch',
        column_order=(
            'caNoticeId', 'noticeNo', 'title', 'mainCPVCode', 'sysProcedureState', 
            'sysContractAssigmentType', 'publicationDate', 'caPublicationDate', 
            'publicationTime', 'estimatedValue', 'totalAcquisitionValue', 
            'budgetDifference', 'budgetDiffPercentage', 'numberOfReceivedOffers', 
            'numberOfWinners', 'valuePerOffer', 'numberOfLots', 'meanLotValue', 
            'isEUFunded', 'softwareModules', 'experts', 'projectDuration', 
            'anomaly_score', 'anomaly_label'
        )
    )

def write_top_contracts():
    st.divider()
    col_chart_title, col_chart_sel = st.columns([2, 1])
    with col_chart_title:
        st.write("### Top contract awards in the last 30 days")
    with col_chart_sel:
        metric_choice = st.selectbox(
            "Select metric to visualize:",
            ["Total value of the contract award", "Number of offers received"]
        )

    if not df.empty:
        # keep entries from the last 30 days
        max_date = df['caPublicationDate'].max()
        start_date = max_date - pd.Timedelta(days=30)
        df_last_30 = df[df['caPublicationDate'] >= start_date].copy()

        if df_last_30.empty:
            st.warning("no contracts in the last 30 days")
            return

        df_authorities = load_data("seap_dataset/authorities")

        # merge with authorities
        if 'authorityId' in df_last_30.columns and 'authorityId' in df_authorities.columns:
            df_last_30 = df_last_30.merge(
                df_authorities[['authorityId', 'officialName']], 
                on='authorityId', 
                how='left'
            )
        else:
            df_last_30['officialName'] = "Unknown Authority"

        # map selection to dataframe columns
        metric_map = {
            "Total value of the contract award": ("totalAcquisitionValue", "Total Value (RON)"),
            "Number of offers received": ("numberOfReceivedOffers", "Number of Offers")
        }
        val_col, display_col = metric_map[metric_choice]
        
        name_col = 'contractTitle' if 'contractTitle' in df_last_30.columns else 'title'

        # filter and structure the top 10 view
        top_df = df_last_30[['caNoticeId', name_col, 'officialName', val_col]].dropna(subset=[val_col])
        
        if val_col == "totalAcquisitionValue":
            top_df[val_col] = top_df[val_col].round(2)
            
        # sort from highest to lowest
        top_df = top_df.sort_values(by=val_col, ascending=False).head(10).reset_index(drop=True)
        
        # use a rank column
        top_df['Rank'] = [f"#{i+1:02d}" for i in range(len(top_df))]

        # render the bar chart
        st.write(f"**Top 10 by {display_col}**")
        chart_df = top_df.copy()
        chart_df['Chart Axis'] = chart_df['Rank'] + " - " + chart_df['caNoticeId'].astype(str)

        chart_df = chart_df.rename(columns={val_col: display_col})
        chart_data = chart_df.set_index('Chart Axis')[[display_col]]
        
        st.bar_chart(chart_data, y=display_col, height=400, horizontal=True)

        st.write("")

        # render the data table
        st.write("**Detailed data view**")
        
        top_df['Notice ID Link'] = top_df['caNoticeId'].apply(
            lambda x: f"https://www.e-licitatie.ro/pub/notices/ca-notices/view-c/{x}"
        )
        
        table_df = top_df[['Rank', 'Notice ID Link', name_col, 'officialName', val_col]]
        table_df.columns = ['Rank', 'Notice ID', 'Contract Title', 'Contracting Authority', display_col]

        st.dataframe(
            table_df, 
            use_container_width=True,
            hide_index=True,
            column_config={
                "Notice ID": st.column_config.LinkColumn(
                    "Notice ID", 
                    display_text=r"(\d+)$"
                )
            }
        )

if not df_raw.empty:
    min_date = df_raw['caPublicationDate'].min().date()
    max_date = df_raw['caPublicationDate'].max().date()

    with col_start:
        start_date = st.date_input("Starting date:", min_date, min_value=min_date, max_value=max_date)
    with col_end:
        end_date = st.date_input("End date:", max_date, min_value=min_date, max_value=max_date)

    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date).replace(hour=23, minute=59, second=59)
    df = df_raw[(df_raw['caPublicationDate'] >= start_ts) & (df_raw['caPublicationDate'] <= end_ts)].copy()

    if not df.empty:
        write_general_stats()
        write_top_contracts()
        write_monthly_trends()
        write_all_dataset()

    else:
        st.warning("No data found for the selected period")
else:
    st.warning("No data in parquet files")