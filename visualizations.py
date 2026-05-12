import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st
from plotly.subplots import make_subplots
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, silhouette_samples
import matplotlib.pyplot as plt
import seaborn as sns

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
    st.subheader("💺 Average Rating by Seat Type")

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

# --- PHẦN BỔ SUNG: PHÂN TÍCH NÂNG CAO (PCA & CLUSTERING) ---

  
# def plot_pca_clusters(df):

#     st.subheader("🎯 Bản đồ phân khúc Trải nghiệm khách hàng (ML)")

#     # =========================================================
#     # 1. Cluster Info Mapping
#     # =========================================================
#     cluster_info = {
#         "1": {
#             "label": "Low Satisfaction",
#             "color": "#E58606"   # Cam
#         },
#         "0": {
#             "label": "Medium Satisfaction",
#             "color": "#52BCA3"   # Xanh ngọc
#         },
#         "2": {
#             "label": "High Satisfaction",
#             "color": "#5D69B1"   # Tím xanh
#         }
#     }

#     # =========================================================
#     # 2. Mapping label cho dataframe
#     # =========================================================
#     df['Cluster_Label'] = df['Cluster'].astype(str).map(
#         lambda x: cluster_info[x]["label"]
#     )

#     # =========================================================
#     # 3. PCA Scatter Plot
#     # =========================================================
#     fig_pca = px.scatter(
#         df,
#         x='PCA1',
#         y='PCA2',
#         color='Cluster_Label',

#         hover_data=[
#             'Overall_Rating',
#             'Seat Type'
#         ],

#         labels={
#             'PCA1': 'Mức độ hài lòng (Thấp → Cao)',
#             'PCA2': 'Đặc điểm phàn nàn'
#         },

#         color_discrete_map={
#             "Low Satisfaction": "#E58606",
#             "Medium Satisfaction": "#52BCA3",
#             "High Satisfaction": "#5D69B1"
#         },

#         opacity=0.7
#     )

#     fig_pca.update_layout(
#         plot_bgcolor='white',
#         height=500,
#         legend_title="Phân khúc khách hàng"
#     )

#     st.plotly_chart(fig_pca, use_container_width=True)

#     # =========================================================
#     # 4. Donut Chart theo từng Hạng ghế
#     # =========================================================
#     st.write("### 📊 Tỷ lệ phân khúc hài lòng theo từng Hạng ghế")

#     seat_types = sorted(df['Seat Type'].dropna().unique())

#     fig_pie = make_subplots(
#         rows=1,
#         cols=len(seat_types),

#         specs=[[{'type': 'domain'}] * len(seat_types)],

#         subplot_titles=seat_types
#     )

#     for i, seat in enumerate(seat_types):

#         df_seat = df[df['Seat Type'] == seat]

#         counts = (
#             df_seat['Cluster']
#             .value_counts(normalize=True)
#             .reset_index()
#         )

#         counts.columns = ['Cluster', 'Percent']

#         fig_pie.add_trace(

#             go.Pie(

#                 labels=[
#                     cluster_info[str(c)]["label"]
#                     for c in counts['Cluster']
#                 ],

#                 values=counts['Percent'],

#                 marker=dict(
#                     colors=[
#                         cluster_info[str(c)]["color"]
#                         for c in counts['Cluster']
#                     ]
#                 ),

#                 hole=0.45,

#                 name=seat,

#                 textinfo='percent',

#                 hovertemplate=
#                 "<b>%{label}</b><br>" +
#                 "Tỷ lệ: %{percent}<extra></extra>"
#             ),

#             row=1,
#             col=i + 1
#         )

#     fig_pie.update_layout(

#         height=450,

#         margin=dict(
#             t=80,
#             b=20,
#             l=10,
#             r=10
#         ),

#         legend_title="Phân khúc",

#         legend=dict(
#             orientation="h",
#             yanchor="bottom",
#             y=-0.15,
#             xanchor="center",
#             x=0.5
#         )
#     )

#     st.plotly_chart(fig_pie, use_container_width=True)

#     # =========================================================
#     # 5. Bảng thống kê trung bình
#     # =========================================================
#     st.write("### 📋 Chỉ số dịch vụ trung bình của các nhóm")

#     stats_df = (
#         df.groupby('Cluster_Label')[
#             [
#                 'Overall_Rating',
#                 'Value For Money',
#                 'Ground Service',
#                 'Seat Comfort'
#             ]
#         ]
#         .mean()
#         .round(2)
#     )

#     st.dataframe(
#         stats_df,
#         use_container_width=True
#     )

#     # =========================================================
#     # 6. Nhận xét phân tích
#     # =========================================================
#     st.markdown("---")








# =========================================================
# MAIN FUNCTION
# =========================================================
def plot_pca_clusters(
    df,
    scaled_df,
    pca_variance
):

    import streamlit as st
    import numpy as np
    import pandas as pd

    import matplotlib.pyplot as plt
    import seaborn as sns

    import plotly.express as px
    import plotly.graph_objects as go

    from plotly.subplots import make_subplots

    from sklearn.cluster import KMeans

    from sklearn.metrics import (
        silhouette_score,
        silhouette_samples
    )

    # =====================================================
    # SAFETY CHECK
    # =====================================================

    if (
        df is None
        or df.empty
        or scaled_df is None
        or scaled_df.empty
    ):
        st.warning("Không đủ dữ liệu để phân tích clustering.")
        return

    # =====================================================
    # CONVERT TO NUMPY
    # =====================================================

    X_scaled = scaled_df.values

    labels = df['Cluster'].astype(int).values

    # =====================================================
    # CLUSTER INFO
    # =====================================================

    cluster_info = {

        "1": {
            "label": "Low Satisfaction",
            "color": "#E58606"
        },

        "0": {
            "label": "Medium Satisfaction",
            "color": "#52BCA3"
        },

        "2": {
            "label": "High Satisfaction",
            "color": "#5D69B1"
        }
    }

    # =====================================================
    # MAP LABEL
    # =====================================================

    df = df.copy()

    df['Cluster_Label'] = (
        df['Cluster']
        .astype(str)
        .map(
            lambda x:
            cluster_info[x]["label"]
        )
    )

    # =====================================================
    # HEADER
    # =====================================================

    st.subheader(
        "🎯 Bản đồ phân khúc Trải nghiệm khách hàng (ML)"
    )

    # =====================================================
    # 1. PCA SCATTER PLOT
    # =====================================================

    fig_pca = px.scatter(

        df,

        x='PCA1',
        y='PCA2',

        color='Cluster_Label',

        hover_data=[
            'Overall_Rating',
            'Seat Type'
        ],

        labels={
            'PCA1': 'Mức độ hài lòng (Thấp → Cao)',
            'PCA2': 'Đặc điểm phàn nàn'
        },

        color_discrete_map={

            "Low Satisfaction": "#E58606",

            "Medium Satisfaction": "#52BCA3",

            "High Satisfaction": "#5D69B1"
        },

        opacity=0.7
    )

    fig_pca.update_layout(

        plot_bgcolor='white',

        height=550,

        legend_title="Phân khúc khách hàng"
    )

    st.plotly_chart(
        fig_pca,
        use_container_width=True
    )

    st.markdown("""
### Phân tích PCA Map

- Nếu các cụm đứng tách xa nhau:
    → clustering tách biệt tốt

- Nếu nhiều điểm chồng lên nhau:
    → overlap cao

- Nếu cụm trải dài liên tục:
    → model đang chia theo gradient hài lòng
""")

    # =====================================================
    # 2. DONUT CHART
    # =====================================================

    st.write(
        "### 📊 Tỷ lệ phân khúc hài lòng theo từng Hạng ghế"
    )

    seat_types = sorted(
        df['Seat Type']
        .dropna()
        .unique()
    )

    fig_pie = make_subplots(

        rows=1,

        cols=len(seat_types),

        specs=[
            [{'type': 'domain'}]
            * len(seat_types)
        ],

        subplot_titles=seat_types
    )

    for i, seat in enumerate(seat_types):

        df_seat = (
            df[
                df['Seat Type'] == seat
            ]
        )

        counts = (

            df_seat['Cluster']

            .value_counts(
                normalize=True
            )

            .reset_index()
        )

        counts.columns = [
            'Cluster',
            'Percent'
        ]

        fig_pie.add_trace(

            go.Pie(

                labels=[

                    cluster_info[str(c)]["label"]

                    for c in counts['Cluster']
                ],

                values=counts['Percent'],

                marker=dict(

                    colors=[

                        cluster_info[str(c)]["color"]

                        for c in counts['Cluster']
                    ]
                ),

                hole=0.45,

                name=seat,

                textinfo='percent',

                hovertemplate=
                "<b>%{label}</b><br>"
                +
                "Tỷ lệ: %{percent}"
                +
                "<extra></extra>"
            ),

            row=1,
            col=i + 1
        )

    fig_pie.update_layout(

        height=450,

        margin=dict(
            t=80,
            b=20,
            l=10,
            r=10
        ),

        legend_title="Phân khúc",

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5
        )
    )

    st.plotly_chart(
        fig_pie,
        use_container_width=True
    )

    st.markdown("""
### Phân tích Donut Chart

- Nếu Economy chứa nhiều màu cam:
    → khách phổ thông đang không hài lòng

- Nếu Business/First chủ yếu xanh:
    → premium experience tốt hơn rõ rệt

- Nếu tất cả hạng ghế có phân phối giống nhau:
    → cluster chưa phản ánh behavioral segmentation
""")

    # =====================================================
    # 3. SILHOUETTE SCORE
    # =====================================================

    st.subheader(
        "🧠 Đánh giá chất lượng Clustering"
    )

    st.write("## 📌 1. Silhouette Score")

    sil_score = silhouette_score(
        X_scaled,
        labels
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Silhouette Score",
        f"{sil_score:.3f}"
    )

    # -----------------------------------------------------

    if sil_score >= 0.7:

        verdict = "Rất tốt"

    elif sil_score >= 0.5:

        verdict = "Tốt"

    elif sil_score >= 0.3:

        verdict = "Chấp nhận được"

    else:

        verdict = "Overlap cao"

    # -----------------------------------------------------

    col2.metric(
        "Đánh giá",
        verdict
    )

    col3.metric(
        "Số cụm",
        len(np.unique(labels))
    )

    st.markdown("""
### Ý nghĩa:

- Score gần 1 → cụm tách biệt tốt
- Score gần 0 → overlap mạnh
- Score âm → nhiều điểm bị gán sai cluster
""")

    # =====================================================
    # 4. SILHOUETTE PLOT
    # =====================================================

    st.write("## 📊 2. Silhouette Plot")

    sample_silhouette_values = (
        silhouette_samples(
            X_scaled,
            labels
        )
    )

    fig, ax = plt.subplots(
        figsize=(10, 6)
    )

    y_lower = 10

    n_clusters = len(np.unique(labels))

    colors = [
        "#E58606",
        "#52BCA3",
        "#5D69B1"
    ]

    for i in range(n_clusters):

        ith_cluster_silhouette_values = (
            sample_silhouette_values[
                labels == i
            ]
        )

        ith_cluster_silhouette_values.sort()

        size_cluster_i = (
            ith_cluster_silhouette_values
            .shape[0]
        )

        y_upper = y_lower + size_cluster_i

        color = colors[i]

        ax.fill_betweenx(
            np.arange(y_lower, y_upper),
            0,
            ith_cluster_silhouette_values,
            facecolor=color,
            edgecolor=color,
            alpha=0.7
        )

        ax.text(
            -0.05,
            y_lower + 0.5 * size_cluster_i,
            str(i)
        )

        y_lower = y_upper + 10

    ax.axvline(
        x=sil_score,
        color="red",
        linestyle="--",
        label=f"Average = {sil_score:.3f}"
    )

    ax.set_title(
        "Silhouette Plot"
    )

    ax.set_xlabel(
        "Silhouette Coefficient"
    )

    ax.set_ylabel(
        "Cluster"
    )

    ax.legend()

    st.pyplot(fig)

    # =====================================================
    # 5. ELBOW METHOD
    # =====================================================

    st.write("## 📉 3. Elbow Method")

    inertia = []

    K = range(1, 10)

    for k in K:

        km = KMeans(
            n_clusters=k,
            random_state=42,
            n_init=10
        )

        km.fit(X_scaled)

        inertia.append(
            km.inertia_
        )

    fig_elbow = px.line(

        x=list(K),

        y=inertia,

        markers=True,

        labels={
            "x": "Số cụm (K)",
            "y": "Inertia"
        },

        title="Elbow Method"
    )

    st.plotly_chart(
        fig_elbow,
        use_container_width=True
    )

    # =====================================================
    # 6. HEATMAP CENTROID
    # =====================================================

    st.write("## 🌡️ 4. Heatmap Centroid")

    feature_cols = [

        'Seat Comfort',

        'Cabin Staff Service',

        'Food & Beverages',

        'Ground Service',

        'Value For Money'
    ]

    centroid_df = (

        df.groupby('Cluster')[feature_cols]

        .mean()

        .round(2)
    )

    fig_heatmap, ax = plt.subplots(
        figsize=(10, 5)
    )

    sns.heatmap(

        centroid_df,

        annot=True,

        cmap="YlGnBu",

        fmt=".2f",

        ax=ax
    )

    ax.set_title(
        "Cluster Centroid Heatmap"
    )

    st.pyplot(fig_heatmap)

    # =====================================================
    # 7. PCA VARIANCE
    # =====================================================

    st.write("## 📐 5. PCA Explained Variance")

    pca1_ratio = pca_variance[0]
    pca2_ratio = pca_variance[1]

    variance_df = pd.DataFrame({

        "Component": [
            "PCA1",
            "PCA2"
        ],

        "Explained Variance": [
            pca1_ratio,
            pca2_ratio
        ]
    })

    fig_var = px.bar(

        variance_df,

        x="Component",

        y="Explained Variance",

        text="Explained Variance",

        title="PCA Variance Explained"
    )

    st.plotly_chart(
        fig_var,
        use_container_width=True
    )

    # =====================================================
    # 8. OVERALL ANALYSIS
    # =====================================================

    st.write("## 📝 6. Đánh giá tổng thể")

    overlap_level = (
        "Thấp"
        if sil_score > 0.5
        else "Trung bình"
        if sil_score > 0.3
        else "Cao"
    )

    separation = (
        "Tốt"
        if sil_score > 0.5
        else "Tạm ổn"
        if sil_score > 0.3
        else "Yếu"
    )

    artificial_risk = (
        "Thấp"
        if pca1_ratio < 0.7
        else "Trung bình"
        if pca1_ratio < 0.85
        else "Cao"
    )

    summary_df = pd.DataFrame({

        "Tiêu chí": [

            "Overlap",

            "Separation",

            "Business Meaning",

            "Artificial Split Risk"
        ],

        "Đánh giá": [

            overlap_level,

            separation,

            "Tốt",

            artificial_risk
        ]
    })

    st.dataframe(
        summary_df,
        use_container_width=True
    )

    st.markdown("""
### Kết luận:

- Nếu silhouette cao + heatmap khác biệt rõ:
    → clustering có chất lượng tốt

- Nếu PCA1 chiếm quá mạnh:
    → model chủ yếu chia theo satisfaction level

- Nếu centroid có pattern đa dạng:
    → clustering có behavioral meaning thực sự
""")