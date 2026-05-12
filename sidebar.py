import streamlit as st
import pandas as pd
import os
from data_crawler import scrape_data
from data_processor import FILE_LOCAL


def render_management_panel():
    """Render nút quản lý dữ liệu (khởi tạo / cập nhật) trong sidebar."""
    st.header("⚙️ Quản lý hệ thống")

    if not os.path.exists(FILE_LOCAL):
        st.warning("Chưa tìm thấy file dữ liệu cục bộ.")
        if st.button("Khởi tạo & Cào 10 trang đầu"):
            with st.spinner("Đang khởi tạo dữ liệu..."):
                new_df = scrape_data(max_pages=10)
                if not new_df.empty:
                    new_df.to_csv(FILE_LOCAL, index=False, encoding="utf-8-sig")
                    st.success("Đã tạo file! Hãy chạy lại App.")
                    st.rerun()
    else:
        st.success("Chế độ: Máy trạm (Local)")
        if st.button("Cập nhật dữ liệu mới"):
            df_history = pd.read_csv(FILE_LOCAL)
            df_history["Date"] = pd.to_datetime(df_history["Date"], format="mixed")
            last_checkpoint = df_history["Date"].max()

            with st.spinner("Đang kiểm tra dữ liệu mới trên Skytrax..."):
                new_df = scrape_data(max_pages=40, checkpoint_date=last_checkpoint)
                if not new_df.empty:
                    final_df = pd.concat([new_df, df_history]).drop_duplicates(
                        subset=["Header", "Date"]
                    )
                    final_df.to_csv(FILE_LOCAL, index=False, encoding="utf-8-sig")
                    st.success(f"Đã thêm {len(new_df)} dòng mới!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.info("ℹDữ liệu đã là mới nhất.")


def render_filters(df) -> dict:
    """
    Render toàn bộ 8 bộ lọc trong sidebar.
    Trả về dict chứa các giá trị người dùng đã chọn.
    """
    st.markdown("---")
    st.header("🔍 Bộ lọc")

    # 1. Khoảng thời gian
    min_date = df["Date"].min().date()
    max_date = df["Date"].max().date()
    date_range = st.date_input(
        "Thời gian",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    # 2. Hạng ghế
    all_seats = sorted(df["Seat Type"].dropna().unique().tolist())
    sel_seats = st.pills(
        "Hạng ghế",
        options=all_seats,
        default=all_seats,
        selection_mode="multi",
    )

    # 3. Loại hành khách
    all_travellers = sorted(df["Type Of Traveller"].dropna().unique().tolist())
    sel_travellers = st.pills(
        "Loại hành khách",
        options=all_travellers,
        default=all_travellers,
        selection_mode="multi",
    )

    # 4. Khoảng điểm đánh giá
    rating_range = st.slider(
        "Điểm đánh giá",
        min_value=1,
        max_value=10,
        value=(1, 10),
    )

    # 5. Đề xuất (Recommended)
    sel_recommended = st.pills(
        "Đề xuất",
        options=["yes", "no"],
        default=["yes", "no"],
        selection_mode="multi",
    )

    # 6. Loại máy bay
    all_aircraft = ["Tất cả"] + sorted(df["Aircraft"].dropna().unique().tolist())
    sel_aircraft = st.selectbox("Loại máy bay", options=all_aircraft, index=0)

    # 7. Thành phố đi (Origin)
    all_origins = ["Tất cả"] + (
        sorted(df["Origin"].dropna().unique().tolist())
        if "Origin" in df.columns
        else []
    )
    sel_origin = st.selectbox("Thành phố đi", options=all_origins, index=0)

    # 8. Thành phố đến (Destination)
    all_destinations = ["Tất cả"] + (
        sorted(df["Destination"].dropna().unique().tolist())
        if "Destination" in df.columns
        else []
    )
    sel_destination = st.selectbox(
        "Thành phố đến", options=all_destinations, index=0
    )

    return {
        "date_range": date_range,
        "seats": sel_seats,
        "travellers": sel_travellers,
        "rating_range": rating_range,
        "recommended": sel_recommended,
        "aircraft": sel_aircraft,
        "origin": sel_origin,
        "destination": sel_destination,
    }
