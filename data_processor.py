import pandas as pd
import os
import streamlit as st

FILE_LOCAL = "ba_data.csv"
GSHEET_ID = "1F19cUq04OUQOs9nz097pCJ1uZ0Kbx1HD648dvmmixdg"
CLOUD_URL = f"https://docs.google.com/spreadsheets/d/{GSHEET_ID}/export?format=csv"

@st.cache_data(ttl=300)
def load_data():
    if os.path.exists(FILE_LOCAL):
        try:
            return pd.read_csv(FILE_LOCAL)
        except: return None
    else:
        try:
            return pd.read_csv(CLOUD_URL)
        except Exception as e:
            st.error(f"Lỗi kết nối Cloud: {e}")
            return None

def preprocess_data(df):
    if df is None or df.empty: return df
    
    # Chuẩn hóa ngày và rating
    df["Date"] = pd.to_datetime(df["Date"], format='mixed')
    df["Overall_Rating"] = pd.to_numeric(df["Overall_Rating"], errors="coerce")
    
    # Tách Route
    if 'Route' in df.columns:
        route_split = df['Route'].str.split(r'\s+to\s+', n=1, expand=True)
        df['Origin'] = route_split[0].str.strip()
        df['Destination'] = route_split[1].str.strip() if route_split.shape[1] > 1 else None

    # Chuẩn hóa Recommended
    if 'Recommended' in df.columns:
        df['Recommended'] = df['Recommended'].str.strip().str.lower()
        
    return df