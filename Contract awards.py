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
        write_monthly_trends()
        write_all_dataset()

    else:
        st.warning("No data found for the selected period")
else:
    st.warning("No data in parquet files")