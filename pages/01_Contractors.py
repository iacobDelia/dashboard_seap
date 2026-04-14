from utils import *
import streamlit as st
import plotly.express as px
import numpy as np

st.set_page_config(
    page_title="SEAP IT dashboard", 
    layout="wide"
)

st.title("Vendor analysis")

df_contractors = load_data("seap_dataset/contractors/")
df_all_contracts = load_data("seap_dataset/contracts/") 
df_contract_winners = load_data("seap_dataset/contract_winners/")

def write_general_data():
    contractors_rom = df_contractors[df_contractors['country'] == 'Romania']
    SMEs = df_contractors[df_contractors['isSME'] == True]
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Number of vendors", f"{len(df_contractors):,}")
    with m2:
        st.metric("Number of Romanian vendors", len(contractors_rom), 
                    delta=f"{(len(contractors_rom)/len(df_contractors)*100):.2f}%", delta_color="inverse")
    with m3:
        st.metric("Number of small/medium enterprises", len(SMEs), 
                    delta=f"{(len(SMEs)/len(df_contractors)*100):.2f}%", delta_color="off")

def write_county_info():
    # count by county
    county_counts = df_contractors['county'].value_counts().reset_index()
    county_counts.columns = ['county', 'vendor_count']

    if "Caras-Severin" not in county_counts['county'].values:
        county_counts.loc[len(county_counts)] = ["Caras-Severin", 0]
    if "Ialomita" not in county_counts['county'].values:
        county_counts.loc[len(county_counts)] = ["Ialomita", 0]
    if "Calarasi" not in county_counts['county'].values:
        county_counts.loc[len(county_counts)] = ["Calarasi", 0]

    county_counts['log_vendor_count'] = np.log10(county_counts['vendor_count'] + 1)

    county_counts = county_counts[county_counts['county'] != 'NA']
    geojson_ro = load_local_geojson("romania.geojson")
    fig = px.choropleth(
        county_counts,
        geojson=geojson_ro,
        locations='county',
        featureidkey="properties.name", 
        color='log_vendor_count',
        color_continuous_scale="Blues",
        scope="europe",
        labels={'vendor_count': 'Number of vendors'}
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(height = 600, margin={"r":0,"t":0,"l":0,"b":0})

    st.divider()
    st.write("### Distribution by county")
    #st.plotly_chart(fig, use_container_width=True)
    col_map, col_table = st.columns([3, 1])
    col_map.plotly_chart(fig)

    df_sorted = county_counts.sort_values(by='vendor_count', ascending = False,)
    col_table.dataframe(df_sorted, height=600, column_order = ('county', 'vendor_count'))

def write_top_10():
    st.divider()
    
    col_title, col_sel = st.columns([2, 1])
    
    with col_title:
        st.write("### Top 10 vendors")
    
    with col_sel:
        metric_choice = st.selectbox(
            "Sort by:",
            ["Total Value (RON)", "Number of Contracts"],
            label_visibility="collapsed"
        )

    df_contract_winners['caNoticeContractId'] = pd.to_numeric(df_contract_winners['caNoticeContractId'], errors='coerce')
    df_all_contracts['caNoticeContractId'] = pd.to_numeric(df_all_contracts['caNoticeContractId'], errors='coerce')

    if metric_choice == "Total Value (RON)":
        df_winner_values = df_contract_winners.merge(
            df_all_contracts[['caNoticeContractId', 'totalContractValue']], 
            on='caNoticeContractId', 
            how='inner'
        )
        df_full = df_winner_values.merge(df_contractors[['CUI', 'officialName']], on='CUI', how='inner')
        
        plot_data = df_full.groupby('officialName')['totalContractValue'].sum().reset_index()
        x_col = 'totalContractValue'
        x_label = 'Total Value (RON)'
    else:
        df_full = df_contract_winners.merge(df_contractors[['CUI', 'officialName']], on='CUI', how='inner')
        
        plot_data = df_full.groupby('officialName').size().reset_index(name='contract_count')
        x_col = 'contract_count'
        x_label = 'Number of Contracts'

    top_10 = plot_data.sort_values(by=x_col, ascending=False).head(10)

    fig_top = px.bar(
        top_10,
        x=x_col,
        y='officialName',
        orientation='h',
        labels={x_col: x_label, 'officialName': 'Vendor Name'},
        color_discrete_sequence=['#1f77b4']
    )
    
    fig_top.update_layout(
        yaxis={'categoryorder':'total ascending'},
        height=450,
        margin=dict(l=0, r=0, t=20, b=0)
    )
    
    st.plotly_chart(fig_top, use_container_width=True)

def write_all():
    st.divider()
    st.write("### All data")

    contract_counts = df_contract_winners.groupby('CUI').size().reset_index(name='number of signed contracts')
    df_vendor_stats = df_contractors.merge(
        contract_counts,
        on='CUI',
        how='left'
    )

    st.dataframe(df_vendor_stats.sort_values(by='number of signed contracts', ascending = False), width='stretch',
                 column_order = ("CUI", "officialName", "number of signed contracts", "country", "county", "isSME"))


write_general_data()
write_county_info()
write_top_10()
write_all()