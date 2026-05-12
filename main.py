# python -m streamlit run main.py

import streamlit as st
import pandas as pd

from data_processor import (
    load_data,
    preprocess_data,
    apply_advanced_analytics
)

import sidebar
import visualizations as viz


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Hệ thống Giám sát BA",
    layout="wide"
)

st.title("British Airways Data Monitoring System")


# =========================================================
# 1. LOAD & PREPROCESS
# =========================================================

df = load_data()

if df is not None:

    df = preprocess_data(df)


# =========================================================
# 2. SIDEBAR
# =========================================================

with st.sidebar:

    sidebar.render_management_panel()

    if df is not None:

        filters = sidebar.render_filters(df)


# =========================================================
# 3. MAIN DISPLAY
# =========================================================

if df is not None:

    # =====================================================
    # APPLY ML ANALYTICS
    # =====================================================

    df_with_ml, scaled_df, pca_variance = (
        apply_advanced_analytics(df)
    )

    # =====================================================
    # COPY DATAFRAME FOR FILTERING
    # =====================================================

    df_filt = df_with_ml.copy()

    # =====================================================
    # DATE FILTER
    # =====================================================

    date_range = filters["date_range"]

    if (
        isinstance(date_range, (list, tuple))
        and len(date_range) == 2
    ):

        df_filt = df_filt[
            (
                df_filt["Date"]
                >= pd.Timestamp(date_range[0])
            )
            &
            (
                df_filt["Date"]
                <= pd.Timestamp(date_range[1])
            )
        ]

    # =====================================================
    # SEAT TYPE FILTER
    # =====================================================

    if filters["seats"] is not None:

        df_filt = df_filt[
            df_filt["Seat Type"].isin(
                filters["seats"]
            )
        ]

    else:

        df_filt = df_filt.iloc[0:0]

    # =====================================================
    # TRAVELLER TYPE FILTER
    # =====================================================

    if filters["travellers"] is not None:

        df_filt = df_filt[
            df_filt["Type Of Traveller"].isin(
                filters["travellers"]
            )
        ]

    else:

        df_filt = df_filt.iloc[0:0]

    # =====================================================
    # RATING FILTER
    # =====================================================

    df_filt = df_filt[
        (
            df_filt["Overall_Rating"]
            >= filters["rating_range"][0]
        )
        &
        (
            df_filt["Overall_Rating"]
            <= filters["rating_range"][1]
        )
    ]

    # =====================================================
    # RECOMMENDED FILTER
    # =====================================================

    if filters["recommended"] is not None:

        df_filt = df_filt[
            df_filt["Recommended"].isin(
                filters["recommended"]
            )
        ]

    else:

        df_filt = df_filt.iloc[0:0]

    # =====================================================
    # AIRCRAFT FILTER
    # =====================================================

    if filters["aircraft"] != "Tất cả":

        df_filt = df_filt[
            df_filt["Aircraft"]
            == filters["aircraft"]
        ]

    # =====================================================
    # ORIGIN FILTER
    # =====================================================

    if (
        filters["origin"] != "Tất cả"
        and "Origin" in df_filt.columns
    ):

        df_filt = df_filt[
            df_filt["Origin"]
            == filters["origin"]
        ]

    # =====================================================
    # DESTINATION FILTER
    # =====================================================

    if (
        filters["destination"] != "Tất cả"
        and "Destination" in df_filt.columns
    ):

        df_filt = df_filt[
            df_filt["Destination"]
            == filters["destination"]
        ]

    # =====================================================
    # IMPORTANT
    # Sync scaled dataframe with filtered dataframe
    # =====================================================

    scaled_filt = scaled_df.loc[
        df_filt.index
    ]

    # =====================================================
    # METRICS
    # =====================================================

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Tổng dữ liệu gốc",
        f"{len(df)} dòng"
    )

    c2.metric(
        "Số dữ liệu lọc",
        f"{len(df_filt)} dòng"
    )

    c3.metric(
        "Rating trung bình",
        (
            f"{df_filt['Overall_Rating'].mean():.2f} /10.00"
            if len(df_filt) > 0
            else "N/A"
        )
    )

    c4.metric(
        "Ngày cập nhật cuối",
        str(df["Date"].max().date())
    )

    st.markdown("---")

    # =====================================================
    # EMPTY FILTER RESULT
    # =====================================================

    if len(df_filt) == 0:

        st.warning(
            "Không có dữ liệu phù hợp với bộ lọc hiện tại. "
            "Hãy điều chỉnh điều kiện lọc ở thanh bên trái."
        )

    else:

        # =================================================
        # TABS
        # =================================================

        tab1, tab2 = st.tabs(
            [
                "📊 Biểu đồ phân tích",
                "📋 Dữ liệu chi tiết"
            ]
        )

        # =================================================
        # TAB 1
        # =================================================

        with tab1:

            # ---------------------------------------------
            # Trend
            # ---------------------------------------------

            viz.plot_combined_trend(df_filt)

            st.markdown("---")

            # ---------------------------------------------
            # Seat + Traveller
            # ---------------------------------------------

            col1, col2 = st.columns(2)

            with col1:

                viz.plot_seat_rating(df_filt)

            with col2:

                viz.plot_traveller_pie(df_filt)

            viz.plot_seat_traveller_insight()

            st.markdown("---")

            # ---------------------------------------------
            # Service Comparison
            # ---------------------------------------------

            viz.plot_service_comparison(df_filt)

            st.markdown("---")

            # ---------------------------------------------
            # PCA + Clustering
            # ---------------------------------------------

            viz.plot_pca_clusters(
                df_filt,
                scaled_filt,
                pca_variance
            )

        # =================================================
        # TAB 2
        # =================================================

        with tab2:

            st.subheader(
                "Top 20 đánh giá mới nhất"
            )

            st.dataframe(
                df_filt
                .sort_values(
                    "Date",
                    ascending=False
                )
                .head(20),

                use_container_width=True
            )

            st.download_button(
                label="⬇ Tải dữ liệu CSV (đã lọc)",

                data=(
                    df_filt
                    .to_csv(index=False)
                    .encode("utf-8-sig")
                ),

                file_name="ba_filtered_data.csv",

                mime="text/csv"
            )

else:

    st.info(
        "Đang chờ dữ liệu từ Cloud hoặc Local..."
    )