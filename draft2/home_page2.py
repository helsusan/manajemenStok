import streamlit as st
import database
import prediction
from datetime import datetime
import plotly.graph_objects as go
import sys
import os
import pandas as pd

barang_df = database.get_all_nama_barang()
# barang_list = barang_df.tolist()
barang = st.selectbox(
    "Pilih jenis barang", 
    barang_df
)

st.header(f"Penjualan {barang}")

info_barang = database.get_data_barang(barang)

check_status = prediction.check_prediksi(info_barang[0])

# Kalau baru generate, kita panggil ulang untuk refresh data
if "last_generated" in st.session_state and st.session_state["last_generated"] == barang:
    # ambil status terbaru setelah generate
    check_status = prediction.check_prediksi(info_barang[0])
else:
    check_status = prediction.check_prediksi(info_barang[0])

col1, col2 = st.columns(2)
    
with col1:
    if check_status['exists']:
        st.success(f"✅ Prediksi tersedia ({check_status['existing_count']}/3 bulan)")
    else:
        st.warning(f"⚠️ Prediksi belum lengkap ({check_status['existing_count']}/3 bulan)")
with col2:
    btn_generate = st.button(
        "📊 Generate Prediksi" if not check_status['exists'] else "🔄 Regenerate",
        use_container_width=True,
        type="primary" if not check_status['exists'] else "secondary",
        help="..."
    )

if btn_generate:
    with st.spinner(f"Sedang generate prediksi untuk {barang}..."):
        result = prediction.generate_prediksi(info_barang)
        if result['status'] == 'generated':
            st.success(f"✅ Prediksi berhasil di-generate!")
            st.rerun()





# ================================================
# AMBIL DATA DARI DATABASE
# ================================================

# Data historis penjualan (actual)
penjualan_df = database.get_data_penjualan(info_barang[0])

# Data prediksi 3 bulan ke depan
next_month = prediction.get_next_3_months()
prediksi_df = database.get_data_prediksi(
    info_barang[0],
    next_month[0].strftime('%Y-%m-%d'),
    next_month[-1].strftime('%Y-%m-%d')
)

# Check if data exists
if len(penjualan_df) == 0:
    st.warning(f"⚠️ Tidak ada data penjualan untuk barang {barang}")
    st.info("💡 Silakan input data penjualan terlebih dahulu")
    st.stop()

if len(prediksi_df) == 0:
    st.warning(f"⚠️ Tidak ada data prediksi untuk barang {barang}")
    st.info("💡 Klik tombol 'Generate Prediksi' untuk membuat prediksi")
    st.stop()

# ================================================
# METRICS
# ================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_penjualan = penjualan_df['kuantitas'].sum()
    st.metric("📦 Total Penjualan", f"{total_penjualan:,.0f}")

with col2:
    avg_penjualan = penjualan_df['kuantitas'].mean()
    st.metric("📊 Rata-rata Bulanan", f"{avg_penjualan:,.1f}")

with col3:
    next_month_pred = prediksi_df.iloc[0]['kuantitas']
    st.metric("🔮 Prediksi Bulan Depan", f"{next_month_pred:,.0f}")

with col4:
    last_month = penjualan_df.iloc[-1]['kuantitas']
    if len(penjualan_df) > 1:
        prev_month = penjualan_df.iloc[-2]['kuantitas']
        delta = ((last_month - prev_month) / prev_month * 100) if prev_month != 0 else 0
        st.metric("📈 Trend Bulan Lalu", f"{last_month:,.0f}", f"{delta:+.1f}%")
    else:
        st.metric("📈 Bulan Lalu", f"{last_month:,.0f}")

st.markdown("---")

# ================================================
# INFO PREDIKSI
# ================================================

col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    st.caption(f"📅 **Periode Data:** {penjualan_df.index.min().strftime('%b %Y')} - {penjualan_df.index.max().strftime('%b %Y')} ({len(penjualan_df)} bulan)")

with col2:
    st.caption(f"🔮 **Periode Prediksi:** {prediksi_df.index.min().strftime('%b %Y')} - {prediksi_df.index.max().strftime('%b %Y')} ({len(prediksi_df)} bulan)")

with col3:
    current_month = datetime.now().strftime('%b %Y')
    st.caption(f"📍 **Bulan Ini:** {current_month}")

st.markdown("---")

# ================================================
# CHART PLOTLY
# ================================================

fig = go.Figure()

# Trace 1: Actual Sales (Data Historis)
fig.add_trace(go.Scatter(
    x=penjualan_df.index.strftime('%Y-%m'),
    y=penjualan_df['kuantitas'].values,
    mode='lines+markers',
    name='Data Penjualan',
    line=dict(color='#2E86AB', width=3),
    marker=dict(size=8, symbol='circle'),
    hovertemplate='<b>%{x}</b><br>Penjualan: %{y:,.0f}<extra></extra>'
))

# Trace 2: Predicted Sales (Data Prediksi)
fig.add_trace(go.Scatter(
    x=prediksi_df.index.strftime('%Y-%m'),
    y=prediksi_df['kuantitas'].values,
    mode='lines+markers',
    name='Prediksi',
    line=dict(color='#F77F00', width=3, dash='dot'),
    marker=dict(size=10, symbol='star'),
    hovertemplate='<b>%{x}</b><br>Prediksi: %{y:,.0f}<extra></extra>'
))

# Vertical line untuk marking "sekarang"
x_value = pd.to_datetime(penjualan_df.index.max()).timestamp()
fig.add_vline(
    x=x_value,
    line_dash="dash",
    line_color="gray",
    opacity=0.5,
    annotation_text="Bulan Terakhir",
    annotation_position="top"
)

# Layout
fig.update_xaxes(
    dtick="M1",
    tickformat="%b %Y",
    # tickformat="%Y-%m",
    tickangle=45
)

fig.update_layout(
    title={
        'text': f"Penjualan & Prediksi: {barang}",
        'font': {'size': 20, 'color': '#2C3E50'}
    },
    xaxis_title="Periode",
    yaxis_title="Kuantitas Penjualan",
    hovermode='x unified',
    height=500,
    showlegend=True,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        bgcolor="rgba(255,255,255,0.8)"
    ),
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
)

# Grid
fig.update_yaxes(gridcolor='lightgray', gridwidth=0.5)
fig.update_xaxes(gridcolor='lightgray', gridwidth=0.5)

st.plotly_chart(fig, use_container_width=True)

# ================================================
# TABEL DATA PREDIKSI
# ================================================

st.markdown("---")
st.subheader("📋 Detail Prediksi 3 Bulan Ke Depan")

# Format tabel prediksi
tabel_prediksi = prediksi_df.copy()
tabel_prediksi['Bulan'] = tabel_prediksi.index.strftime('%B %Y')
tabel_prediksi['Kuantitas'] = tabel_prediksi['kuantitas'].apply(lambda x: f"{x:,.0f}")
tabel_prediksi = tabel_prediksi[['Bulan', 'Kuantitas']].reset_index(drop=True)
tabel_prediksi.index = tabel_prediksi.index + 1

st.dataframe(
    tabel_prediksi,
    use_container_width=True,
    hide_index=False
)

# ================================================
# FOOTER INFO
# ================================================

st.markdown("---")
st.caption(f"""
💡 **Tips:**
- Klik tombol **Generate** untuk membuat prediksi baru jika data penjualan diupdate
- Klik tombol **Force Update** untuk regenerate prediksi dengan model terbaru
- Prediksi akan otomatis di-generate jika belum tersedia
- Data prediksi disimpan di database dan tidak perlu di-generate ulang setiap kali membuka halaman ini
""")

# Last update info
st.caption(f"🕒 Last viewed: {datetime.now().strftime('%d %B %Y, %H:%M:%S')}")