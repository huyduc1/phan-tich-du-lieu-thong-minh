import pandas as pd
import os
import streamlit as st
import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

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
    
    df["Date"] = pd.to_datetime(df["Date"], format='mixed', dayfirst=False)
    df["Overall_Rating"] = pd.to_numeric(df["Overall_Rating"], errors="coerce")
    
    if 'Route' in df.columns:
        route_split = df['Route'].str.split(r'\s+to\s+', n=1, expand=True)
        df['Origin'] = route_split[0].str.strip()
        df['Destination'] = route_split[1].str.strip() if route_split.shape[1] > 1 else None

    if 'Recommended' in df.columns:
        df['Recommended'] = df['Recommended'].str.strip().str.lower()
        
    return df

def apply_advanced_analytics(df):
    if df is None or df.empty:
        return df

    features = ['Seat Comfort', 'Cabin Staff Service', 'Food & Beverages', 'Ground Service', 'Value For Money']
    existing_features = [f for f in features if f in df.columns]

    if not existing_features:
        return df

    # Xử lý dữ liệu số và điền khuyết
    data_for_ml = df[existing_features].apply(pd.to_numeric, errors='coerce')
    data_for_ml = data_for_ml.fillna(data_for_ml.median())

    # Thêm nhiễu nhẹ (jitter) để tránh trùng lặp tọa độ PCA
    data_jittered = data_for_ml + np.random.normal(0, 0.05, size=data_for_ml.shape)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(data_jittered)

    # Lưu kết quả Scale
    for i, col in enumerate(existing_features):
        df[f"{col}_scaled"] = X_scaled[:, i]

    # K-Means Clustering
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    df['Cluster'] = kmeans.fit_predict(X_scaled).astype(str)

    # PCA giảm chiều
    pca = PCA(n_components=2)
    pca_res = pca.fit_transform(X_scaled)
    df['PCA1'] = pca_res[:, 0]
    df['PCA2'] = pca_res[:, 1]

    # KHẮC PHỤC LỖI: Chuyển numpy array thành list để Pandas so sánh được attrs
    df.attrs['pca_variance'] = pca.explained_variance_ratio_.tolist()

    return df