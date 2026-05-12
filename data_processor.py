import pandas as pd
import numpy as np
import os
import streamlit as st
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

# --- PHẦN PHÂN TÍCH NÂNG CAO (HUY ĐỨC) ---

def apply_advanced_analytics(df):
    """
    Thực hiện:
    - Xử lý missing values
    - Jittering
    - KMeans Clustering
    - PCA Visualization

    Return:
    - df_with_ml
    - scaled_df
    - pca_variance
    """

    # =====================================================
    # 1. Validate input
    # =====================================================
    if df is None or df.empty:
        return df, None, None

    # =====================================================
    # 2. Copy dataframe
    # =====================================================
    df = df.copy()

    # =====================================================
    # 3. Feature columns
    # =====================================================
    features = [
        'Seat Comfort',
        'Cabin Staff Service',
        'Food & Beverages',
        'Ground Service',
        'Value For Money'
    ]

    # =====================================================
    # 4. Check existing columns
    # =====================================================
    existing_features = [
        f for f in features
        if f in df.columns
    ]

    if len(existing_features) == 0:
        return df, None, None

    # =====================================================
    # 5. Convert numeric
    # =====================================================
    data_for_ml = (
        df[existing_features]
        .apply(pd.to_numeric, errors='coerce')
    )

    # =====================================================
    # 6. Fill NaN with median
    # =====================================================
    data_for_ml = data_for_ml.fillna(
        data_for_ml.median()
    )

    # =====================================================
    # 7. Jittering
    # =====================================================
    np.random.seed(42)

    data_jittered = (
        data_for_ml
        + np.random.normal(
            loc=0,
            scale=0.1,
            size=data_for_ml.shape
        )
    )

    # =====================================================
    # 8. Standard Scaling
    # =====================================================
    scaler = StandardScaler()

    X_scaled = scaler.fit_transform(
        data_jittered
    )

    # =====================================================
    # 9. Create scaled dataframe
    # =====================================================
    scaled_df = pd.DataFrame(
        X_scaled,
        columns=existing_features,
        index=df.index
    )

    # =====================================================
    # 10. KMeans Clustering
    # =====================================================
    kmeans = KMeans(
        n_clusters=3,
        random_state=42,
        n_init=10
    )

    clusters = kmeans.fit_predict(
        X_scaled
    )

    df['Cluster'] = clusters.astype(str)

    # =====================================================
    # 11. PCA
    # =====================================================
    pca = PCA(
        n_components=2,
        random_state=42
    )

    pca_result = pca.fit_transform(
        X_scaled
    )

    df['PCA1'] = pca_result[:, 0]
    df['PCA2'] = pca_result[:, 1]

    # =====================================================
    # 12. PCA Variance
    # =====================================================
    pca_variance = (
        pca.explained_variance_ratio_
        .tolist()
    )

    # =====================================================
    # 13. Return
    # =====================================================
    return df, scaled_df, pca_variance