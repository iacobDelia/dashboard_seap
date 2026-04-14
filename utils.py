import streamlit as st
import pandas as pd
import os
import json

@st.cache_data
def load_data(path):
    if os.path.exists(path):
        df = pd.read_parquet(path)
        date_cols = ['caPublicationDate', 'contractDate', 'publicationDate']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col]).dt.tz_localize(None)
        return df
    return pd.DataFrame()

@st.cache_data
def load_local_geojson(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)