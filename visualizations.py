import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st


def plot_combined_trend(df):
    """Biểu đồ xu hướng Rating theo thời gian với rolling avg và annotation min/max."""
    st.subheader("📈 Xu hướng điểm đánh giá theo thời gian")

    df_trend = df.copy()
    df_trend["YearMonth"] = df_trend["Date"].dt.to_period("M").astype(str)

    trend_agg = (
        df_trend.groupby("YearMonth")
        .agg(
            Avg_Rating=("Overall_Rating", "mean"),
            Review_Count=("Overall_Rating", "count"),
        )
        .reset_index()
    )

    # Rolling average 3 tháng
    trend_agg["Rolling_Avg"] = trend_agg["Avg_Rating"].rolling(window=3, min_periods=1).mean()

    # Tìm điểm min/max
    idx_max = trend_agg["Avg_Rating"].idxmax()
    idx_min = trend_agg["Avg_Rating"].idxmin()

    fig = go.Figure()

    # Cột: Số lượng reviews (trục Y phụ bên phải)
    fig.add_trace(
        go.Bar(
            x=trend_agg["YearMonth"],
            y=trend_agg["Review_Count"],
            name="Số lượng reviews",
            marker_color="rgba(100,160,220,0.35)",
            yaxis="y2",
        )
    )

    # Đường: Avg Rating
    fig.add_trace(
        go.Scatter(
            x=trend_agg["YearMonth"],
            y=trend_agg["Avg_Rating"],
            mode="lines+markers",
            name="Rating trung bình",
            line=dict(color="#1e8c4e", width=2.5),
            marker=dict(size=6),
        )
    )

    # Đường: Rolling avg 3 tháng
    fig.add_trace(
        go.Scatter(
            x=trend_agg["YearMonth"],
            y=trend_agg["Rolling_Avg"],
            mode="lines",
            name="Rolling avg (3 tháng)",
            line=dict(color="#f4a261", width=2, dash="dash"),
        )
    )

    # Annotation: Cao nhất
    fig.add_annotation(
        x=trend_agg.loc[idx_max, "YearMonth"],
        y=trend_agg.loc[idx_max, "Avg_Rating"],
        text=f"⬆ Cao nhất: {trend_agg.loc[idx_max, 'Avg_Rating']:.2f}",
        showarrow=True,
        arrowhead=2,
        bgcolor="#1e8c4e",
        font=dict(color="white", size=11),
        arrowcolor="#1e8c4e",
    )

    # Annotation: Thấp nhất
    fig.add_annotation(
        x=trend_agg.loc[idx_min, "YearMonth"],
        y=trend_agg.loc[idx_min, "Avg_Rating"],
        text=f"⬇ Thấp nhất: {trend_agg.loc[idx_min, 'Avg_Rating']:.2f}",
        showarrow=True,
        arrowhead=2,
        ay=40,
        bgcolor="#e63946",
        font=dict(color="white", size=11),
        arrowcolor="#e63946",
    )

    fig.update_layout(
        title="Xu hướng Rating trung bình & Số lượng reviews theo tháng",
        yaxis=dict(title="Rating trung bình (1-10)", range=[0, 10.5]),
        yaxis2=dict(
            title="Số lượng reviews", overlaying="y", side="right", showgrid=False
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        xaxis=dict(type="category", tickangle=-45, tickmode="auto"),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.info(
        "💡 **Insight:** Đường **xanh lá** = Rating trung bình thực tế; "
        "Đường **cam đứt** = xu hướng làm mượt 3 tháng (loại bỏ nhiễu); "
        "Cột **xanh nhạt** = số lượng reviews. "
        "Chú ý các tháng có ít reviews → dữ liệu kém đại diện hơn."
    )


def plot_seat_rating(df):
    """Bar chart: Rating trung bình theo từng hạng ghế."""
    st.subheader("🪑 Average Rating by Seat Type")

    seat_rating = (
        df.dropna(subset=["Seat Type", "Overall_Rating"])
        .groupby("Seat Type")["Overall_Rating"]
        .mean()
        .reset_index()
        .sort_values("Overall_Rating", ascending=False)
    )

    fig = px.bar(
        seat_rating,
        x="Seat Type",
        y="Overall_Rating",
        text="Overall_Rating",
        title="Average Rating by Seat Type",
        color="Seat Type",
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(
        yaxis=dict(title="Rating trung bình (1-10)", range=[0, 11]),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def plot_traveller_pie(df):
    """Pie chart: Phân bổ loại hành khách."""
    st.subheader("👤 Distribution of Traveller Types")

    traveller_count = (
        df["Type Of Traveller"].dropna().value_counts().reset_index()
    )
    traveller_count.columns = ["Type Of Traveller", "Count"]

    fig = px.pie(
        traveller_count,
        names="Type Of Traveller",
        values="Count",
        title="Distribution of Traveller Types",
    )
    st.plotly_chart(fig, use_container_width=True)


def plot_seat_traveller_insight():
    """Insight chung cho 2 biểu đồ Seat Rating và Traveller Pie."""
    st.info(
        "💡 **Insight:** Các biểu đồ này so sánh mức độ hài lòng tổng quan theo loại ghế và nhóm hành khách, "
        "giúp nhận diện tệp khách hàng nào đang có trải nghiệm tiêu cực nhất để hãng tập trung cải thiện."
    )


def plot_service_comparison(df):
    """Grouped bar chart: So sánh điểm từng tiêu chí dịch vụ theo hạng ghế."""
    st.subheader("⚖️ Detailed service evaluation by seat class")

    service_cols = [
        "Seat Comfort",
        "Cabin Staff Service",
        "Food & Beverages",
        "Inflight Entertainment",
        "Ground Service",
        "Value For Money",
    ]

    df_services = df.copy()
    for col in service_cols:
        if col in df_services.columns:
            df_services[col] = pd.to_numeric(df_services[col], errors="coerce")

    service_avg = df_services.groupby("Seat Type")[service_cols].mean().reset_index()
    service_melted = pd.melt(
        service_avg,
        id_vars=["Seat Type"],
        value_vars=service_cols,
        var_name="Dịch vụ",
        value_name="Điểm trung bình",
    )

    fig = px.bar(
        service_melted,
        x="Dịch vụ",
        y="Điểm trung bình",
        color="Seat Type",
        barmode="group",
        title="Comparison of service scores (1-5 stars) between seat classes",
        text_auto=".1f",
    )
    fig.update_layout(
        xaxis_title="Service criteria",
        yaxis_title="Average rating (1-5 stars)",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.info(
        "💡 **Insight:** Biểu đồ này đi sâu vào từng tiêu chí dịch vụ thay vì điểm tổng quan. "
        "Nó cho thấy liệu khách Hạng Thương gia (Business) có thực sự hài lòng với Đồ ăn (Food & Beverages) "
        "hơn Hạng Phổ thông không, hay họ còn khắt khe hơn. "
        "Từ đó hãng có chiến lược nâng cấp dịch vụ cụ thể."
    )