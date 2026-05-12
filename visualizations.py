import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st

def plot_combined_trend(df):
    st.subheader("📈 Xu hướng điểm đánh giá theo thời gian")
    df_trend = df.copy()
    df_trend['YearMonth'] = df_trend['Date'].dt.to_period('M').astype(str)
    
    trend_agg = df_trend.groupby('YearMonth').agg(
        Avg_Rating=('Overall_Rating', 'mean'),
        Review_Count=('Overall_Rating', 'count')
    ).reset_index()
    
    fig = go.Figure()
    # Cột Review Count
    fig.add_trace(go.Bar(x=trend_agg['YearMonth'], y=trend_agg['Review_Count'], name='Số lượng reviews', 
                         marker_color='rgba(100,160,220,0.3)', yaxis='y2'))
    # Đường Avg Rating
    fig.add_trace(go.Scatter(x=trend_agg['YearMonth'], y=trend_agg['Avg_Rating'], mode='lines+markers', 
                             name='Rating trung bình', line=dict(color='#1e8c4e', width=3)))
    
    fig.update_layout(yaxis=dict(title='Rating (1-10)', range=[0, 10]),
                      yaxis2=dict(title='Số lượng', overlaying='y', side='right', showgrid=False),
                      hovermode='x unified')
    st.plotly_chart(fig, use_container_width=True)

def plot_service_comparison(df):
    st.subheader("⚖️ Chi tiết dịch vụ theo hạng ghế")
    service_cols = ['Seat Comfort', 'Cabin Staff Service', 'Food & Beverages', 'Inflight Entertainment', 'Ground Service', 'Value For Money']
    
    df_services = df.copy()
    for col in service_cols:
        if col in df_services.columns:
            df_services[col] = pd.to_numeric(df_services[col], errors='coerce')
    
    service_avg = df_services.groupby('Seat Type')[service_cols].mean().reset_index()
    service_melted = pd.melt(service_avg, id_vars=['Seat Type'], value_vars=service_cols, var_name='Dịch vụ', value_name='Điểm')
    
    fig = px.bar(service_melted, x='Dịch vụ', y='Điểm', color='Seat Type', barmode='group', text_auto='.1f')
    st.plotly_chart(fig, use_container_width=True)