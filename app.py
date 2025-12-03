import streamlit as st
import pandas as pd

# Cache the data loading so it doesn't re-run on every interaction
@st.cache_data
def load_data():
    return pd.read_parquet('data/spend_data_categorized.parquet')

df = load_data()