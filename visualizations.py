import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st
from plotly.subplots import make_subplots

def plot_combined_trend(df):
    st.subheader("📈 Xu hướng điểm đánh giá theo thời gian")
    df_trend = df.copy()
    df_trend["YearMonth"] = df_trend["Date"].dt.to_period("M").astype(str)

    trend_agg = df_trend.groupby("YearMonth").agg(
        Avg_Rating=("Overall_Rating", "mean"),
        Review_Count=("Overall_Rating", "count")
    ).reset_index()

    trend_agg["Rolling_Avg"] = trend_agg["Avg_Rating"].rolling(window=3, min_periods=1).mean()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=trend_agg["YearMonth"], y=trend_agg["Review_Count"], name="Số lượng reviews", 
                         marker_color="rgba(100,160,220,0.3)", yaxis="y2"))
    fig.add_trace(go.Scatter(x=trend_agg["YearMonth"], y=trend_agg["Avg_Rating"], mode="lines+markers", 
                             name="Rating TB", line=dict(color="#1e8c4e", width=2)))
    
    fig.update_layout(yaxis=dict(title="Rating (1-10)", range=[0, 11]),
                      yaxis2=dict(title="Số lượng", overlaying="y", side="right", showgrid=False),
                      hovermode="x unified", height=450)
    st.plotly_chart(fig, use_container_width=True)

def plot_seat_rating(df):
    st.subheader("💺 Đánh giá theo hạng ghế")
    seat_rating = df.groupby("Seat Type")["Overall_Rating"].mean().reset_index().sort_values("Overall_Rating", ascending=False)
    fig = px.bar(seat_rating, x="Seat Type", y="Overall_Rating", color="Seat Type", text_auto=".2f")
    fig.update_layout(yaxis=dict(range=[0, 11]), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

def plot_traveller_pie(df):
    st.subheader("👤 Loại hành khách")
    traveller_count = df["Type Of Traveller"].value_counts().reset_index()
    fig = px.pie(traveller_count, names="Type Of Traveller", values="count", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

def plot_service_comparison(df):
    st.subheader("⚖️ Đánh giá chi tiết dịch vụ")
    service_cols = ["Seat Comfort", "Cabin Staff Service", "Food & Beverages", "Inflight Entertainment", "Ground Service", "Value For Money"]
    
    df_services = df.copy()
    available_cols = [c for c in service_cols if c in df_services.columns]
    for col in available_cols:
        df_services[col] = pd.to_numeric(df_services[col], errors="coerce")

    service_avg = df_services.groupby("Seat Type")[available_cols].mean().reset_index()
    
    if service_avg.empty:
        st.warning("Không có đủ dữ liệu dịch vụ để hiển thị.")
        return

    service_melted = pd.melt(service_avg, id_vars=["Seat Type"], value_vars=available_cols, 
                             var_name="Dịch vụ", value_name="Điểm")

    fig = px.bar(service_melted, x="Dịch vụ", y="Điểm", color="Seat Type", barmode="group", text_auto=".1f")
    fig.update_layout(yaxis=dict(range=[0, 5.5]))
    st.plotly_chart(fig, use_container_width=True)
def plot_pca_clusters(df):
    st.subheader("🎯 Phân tích Phân khúc khách hàng (Machine Learning)")

    # 1. Định nghĩa thông tin cụm (Labels & Colors)
    # Lưu ý: Map đúng giá trị Cluster từ data_processor (0, 1, 2)
    cluster_info = {
        "0": {"label": "Medium Satisfaction", "color": "#52BCA3"}, # Xanh ngọc
        "1": {"label": "Low Satisfaction", "color": "#E58606"},    # Cam
        "2": {"label": "High Satisfaction", "color": "#5D69B1"}    # Tím xanh
    }

    # Tạo cột nhãn mới dựa trên mã cụm
    df['Cluster_Label'] = df['Cluster'].map(lambda x: cluster_info.get(str(x), {"label": "Unknown"})["label"])

    # 2. Biểu đồ phân tán PCA
    fig_pca = px.scatter(
        df, x='PCA1', y='PCA2', 
        color='Cluster_Label',
        hover_data=['Overall_Rating', 'Seat Type'],
        labels={'PCA1': 'Mức độ hài lòng (Thấp → Cao)', 'PCA2': 'Đặc điểm phàn nàn'},
        color_discrete_map={v["label"]: v["color"] for v in cluster_info.values()},
        opacity=0.7,
        height=500
    )
    fig_pca.update_layout(plot_bgcolor='white', legend_title="Phân khúc")
    st.plotly_chart(fig_pca, use_container_width=True)

    # 3. BIỂU ĐỒ TRÒN (DONUT) THEO TỪNG HẠNG GHẾ
    st.write("### 📊 Tỷ lệ phân khúc hài lòng theo từng Hạng ghế")
    
    # Lấy danh sách hạng ghế hiện có trong dữ liệu đã lọc
    seat_types = sorted(df['Seat Type'].dropna().unique())
    
    if not seat_types:
        st.info("Không có dữ liệu hạng ghế để hiển thị biểu đồ tròn.")
        return

    # Tạo subplots: mỗi hạng ghế là một cột
    fig_pie = make_subplots(
        rows=1, cols=len(seat_types),
        specs=[[{'type': 'domain'}] * len(seat_types)],
        subplot_titles=seat_types
    )

    for i, seat in enumerate(seat_types):
        df_seat = df[df['Seat Type'] == seat]
        counts = df_seat['Cluster'].value_counts(normalize=True).reset_index()
        counts.columns = ['Cluster', 'Percent']

        fig_pie.add_trace(
            go.Pie(
                labels=[cluster_info.get(str(c), {"label": "Khác"})["label"] for c in counts['Cluster']],
                values=counts['Percent'],
                marker=dict(colors=[cluster_info.get(str(c), {"color": "gray"})["color"] for c in counts['Cluster']]),
                hole=0.45,
                name=seat,
                textinfo='percent'
            ),
            row=1, col=i + 1
        )

    fig_pie.update_layout(
        height=400,
        margin=dict(t=80, b=20, l=10, r=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    # 4. Bảng thống kê chỉ số trung bình theo nhóm
    st.write("### 📋 Chỉ số dịch vụ trung bình của các nhóm")
    stats_cols = ['Overall_Rating', 'Value For Money', 'Ground Service', 'Seat Comfort']
    # Chỉ lấy các cột tồn tại trong dataframe
    existing_stats = [c for c in stats_cols if c in df.columns]
    
    stats_df = df.groupby('Cluster_Label')[existing_stats].mean().round(2)
    st.dataframe(stats_df, use_container_width=True)

def plot_heatmap(df):
    st.subheader("🔥 Ma trận tương quan")

    # Chỉ lấy các feature cần thiết
    selected_cols = [
        "Overall_Rating",
        "Seat Comfort",
        "Cabin Staff Service",
        "Food & Beverages",
        "Inflight Entertainment",
        "Ground Service",
        "Value For Money"
    ]

    # Giữ các cột tồn tại trong dataframe
    available_cols = [col for col in selected_cols if col in df.columns]

    if len(available_cols) < 2:
        st.warning("Không đủ dữ liệu để tạo heatmap.")
        return

    heatmap_df = df[available_cols].copy()

    for col in available_cols:
        heatmap_df[col] = pd.to_numeric(
            heatmap_df[col],
            errors="coerce"
        )

    # tính toán ma trận tương quan
    corr_matrix = heatmap_df.corr().round(2)

    # vẽ heatmap
    fig = px.imshow(
        corr_matrix,
        text_auto=True,
        color_continuous_scale="RdBu_r",
        aspect="auto"
    )

    fig.update_layout(
        height=600,
    )
    st.plotly_chart(fig, use_container_width=True)