# python -m streamlit run main.py
import streamlit as st
import pandas as pd
from data_processor import load_data, preprocess_data
import sidebar
import visualizations as viz

st.set_page_config(page_title="Hệ thống Giám sát BA", layout="wide")
st.title("British Airways Data Monitoring System")

# --- 1. LOAD & PREPROCESS ---
df = load_data()
if df is not None:
    df = preprocess_data(df)

# --- 2. SIDEBAR ---
with st.sidebar:
    sidebar.render_management_panel()
    if df is not None:
        filters = sidebar.render_filters(df)

# --- 3. MAIN DISPLAY ---
if df is not None:
    # Áp dụng toàn bộ 8 bộ lọc
    df_filt = df.copy()

    # Lọc thời gian
    date_range = filters["date_range"]
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        df_filt = df_filt[
            (df_filt["Date"] >= pd.Timestamp(date_range[0]))
            & (df_filt["Date"] <= pd.Timestamp(date_range[1]))
        ]

    # Lọc Seat Type
    if filters["seats"] is not None:
        df_filt = df_filt[df_filt["Seat Type"].isin(filters["seats"])]
    else:
        df_filt = df_filt.iloc[0:0]

    # Lọc Traveller Type
    if filters["travellers"] is not None:
        df_filt = df_filt[df_filt["Type Of Traveller"].isin(filters["travellers"])]
    else:
        df_filt = df_filt.iloc[0:0]

    # Lọc Điểm đánh giá
    df_filt = df_filt[
        (df_filt["Overall_Rating"] >= filters["rating_range"][0])
        & (df_filt["Overall_Rating"] <= filters["rating_range"][1])
    ]

    # Lọc Recommended
    if filters["recommended"] is not None:
        df_filt = df_filt[df_filt["Recommended"].isin(filters["recommended"])]
    else:
        df_filt = df_filt.iloc[0:0]

    # Lọc Aircraft
    if filters["aircraft"] != "Tất cả":
        df_filt = df_filt[df_filt["Aircraft"] == filters["aircraft"]]

    # Lọc Origin
    if filters["origin"] != "Tất cả" and "Origin" in df_filt.columns:
        df_filt = df_filt[df_filt["Origin"] == filters["origin"]]

    # Lọc Destination
    if filters["destination"] != "Tất cả" and "Destination" in df_filt.columns:
        df_filt = df_filt[df_filt["Destination"] == filters["destination"]]

    # --- 4 METRICS ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng dữ liệu gốc", f"{len(df)} dòng")
    c2.metric("Số dữ liệu lọc", f"{len(df_filt)} dòng")
    c3.metric(
        "Rating trung bình",
        f"{df_filt['Overall_Rating'].mean():.2f} /10.00" if len(df_filt) > 0 else "N/A",
    )
    c4.metric("Ngày cập nhật cuối", str(df["Date"].max().date()))

    st.markdown("---")
    st.header("Dashboard phân tích đánh giá")

    if len(df_filt) == 0:
        st.warning(
            "Không có dữ liệu phù hợp với bộ lọc hiện tại. "
            "Hãy điều chỉnh điều kiện lọc ở thanh bên trái."
        )
    else:
        tab1, tab2 = st.tabs(["Biểu đồ phân tích", "Dữ liệu chi tiết"])

        with tab1:
            # Xu hướng theo thời gian
            viz.plot_combined_trend(df_filt)

            st.markdown("---")

            # Rating by Seat + Pie Traveller (2 cột ngang)
            col1, col2 = st.columns(2)
            with col1:
                viz.plot_seat_rating(df_filt)
            with col2:
                viz.plot_traveller_pie(df_filt)
            viz.plot_seat_traveller_insight()

            st.markdown("---")

            # Đánh giá chi tiết dịch vụ
            viz.plot_service_comparison(df_filt)

        with tab2:
            st.subheader("Top 20 đánh giá mới nhất")
            st.dataframe(
                df_filt.sort_values("Date", ascending=False).head(20),
                use_container_width=True,
            )
            st.download_button(
                "⬇Tải dữ liệu CSV (đã lọc)",
                data=df_filt.to_csv(index=False).encode("utf-8-sig"),
                file_name="ba_filtered_data.csv",
                mime="text/csv",
            )
else:
    st.info("Đang chờ dữ liệu từ Cloud hoặc Local...")