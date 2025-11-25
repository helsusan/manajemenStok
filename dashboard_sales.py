import streamlit as st
import database
import prediction
from datetime import datetime
import plotly.graph_objects as go
import sys
import os
import pandas as pd
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="Dashboard Sales", page_icon="📊", layout="wide")

barang_df = database.get_all_nama_barang()
barang = st.selectbox(
    "Pilih jenis barang", 
    barang_df
)

st.header(f"Penjualan {barang}")

info_barang = database.get_data_barang(barang)

# ================================================
# SECTION GENERATE PREDIKSI SEMENTARA (TIDAK DISIMPAN)
# ================================================

st.markdown("### 🔮 Generate Prediksi (Sementara)")
st.info("💡 Prediksi ini hanya untuk visualisasi dan TIDAK akan disimpan ke database")

col1, col2 = st.columns(2)

with col1:
    # Slider untuk pilih berapa bulan ke depan
    months_ahead = st.slider(
        "Berapa bulan ke depan?",
        min_value=1,
        max_value=6,
        value=3,
        help="Pilih jumlah bulan yang akan diprediksi dari bulan depan"
    )

with col2:
    # Hitung range
    next_month = datetime.now().replace(day=1) + relativedelta(months=1)
    end_month = next_month + relativedelta(months=months_ahead-1)
    st.caption(f"📅 Range: {next_month.strftime('%b %Y')} - {end_month.strftime('%b %Y')}")

btn_generate_temp = st.button(
    f"📊 Generate Prediksi {months_ahead} Bulan",
    use_container_width=True,
    type="primary",
    help=f"Generate prediksi sementara untuk visualisasi (tidak disimpan)"
)

# State untuk menyimpan prediksi sementara - SPECIFIC PER BARANG
temp_pred_key = f"temp_prediction_{barang}"

if temp_pred_key not in st.session_state:
    st.session_state[temp_pred_key] = None

# Reset temp prediction jika barang berubah
if 'last_barang' in st.session_state and st.session_state.last_barang != barang:
    # Barang berubah, clear temp prediction untuk barang sebelumnya
    prev_temp_pred_key = f"temp_prediction_{st.session_state.last_barang}"
    if prev_temp_pred_key in st.session_state:
        st.session_state[prev_temp_pred_key] = None

# Simpan barang saat ini untuk pengecekan selanjutnya
st.session_state.last_barang = barang

# Gunakan temp prediction untuk barang saat ini
temp_prediction = st.session_state[temp_pred_key]

# Handle generate prediksi sementara
if btn_generate_temp:
    with st.spinner(f"Sedang generate prediksi {months_ahead} bulan..."):
        result = prediction.generate_prediksi_temp(
            info_barang,
            next_month,
            end_month
        )
        
        if result['status'] == 'success':
            temp_prediction = result['data']
            st.success(f"✅ Prediksi berhasil di-generate")
        else:
            st.error(f"❌ {result['message']}")
            temp_prediction = None

st.markdown("---")

# ================================================
# AMBIL DATA DARI DATABASE
# ================================================

# Data historis penjualan (actual)
penjualan_df = database.get_all_data_penjualan(info_barang[0])

# Data prediksi yang tersedia (semua)
prediksi_df = database.get_data_prediksi(info_barang[0])

# Check if data exists
if len(penjualan_df) == 0:
    st.warning(f"⚠️ Tidak ada data penjualan untuk barang {barang}")
    st.info("💡 Silakan input data penjualan terlebih dahulu")
    st.stop()

# ================================================
# METRICS
# ================================================

current_date = datetime.now().date()
current_month = current_date.replace(day=1)
last_month = (current_month - relativedelta(months=1))
next_month = (current_month + relativedelta(months=1))

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_penjualan = penjualan_df['kuantitas'].sum()
    st.metric("📦 Total Penjualan", f"{total_penjualan:,.0f}")

with col2:
    avg_penjualan = penjualan_df['kuantitas'].mean()
    st.metric("📊 Rata-rata Bulanan", f"{avg_penjualan:,.1f}")

with col3:
    # Prediksi bulan depan (hanya jika ada)
    if len(prediksi_df) > 0 and next_month in prediksi_df.index:
        next_month_pred = prediksi_df.loc[next_month, 'kuantitas']
        st.metric("🔮 Prediksi Bulan Depan", f"{next_month_pred:,.0f}")
    else:
        st.metric("🔮 Prediksi Bulan Depan", "-", help="Belum tersedia")

with col4:
    # Trend bulan lalu
    if last_month in penjualan_df.index:
        last_month_val = penjualan_df.loc[last_month, 'kuantitas']
        
        # Cari bulan sebelumnya
        prev_month = last_month - relativedelta(months=1)
        
        if prev_month in penjualan_df.index:
            prev_month_val = penjualan_df.loc[prev_month, 'kuantitas']
            delta = ((last_month_val - prev_month_val) / prev_month_val * 100) if prev_month_val != 0 else 0
            st.metric("📈 Trend Bulan Lalu", f"{last_month_val:,.0f}", f"{delta:+.1f}%")
        else:
            st.metric("📈 Bulan Lalu", f"{last_month_val:,.0f}")
    else:
        st.metric("📈 Bulan Lalu", "-", help="Data belum tersedia")

st.markdown("---")

# ================================================
# INFO PREDIKSI
# ================================================

col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    st.caption(f"📅 **Periode Data:** {penjualan_df.index.min().strftime('%b %Y')} - {penjualan_df.index.max().strftime('%b %Y')} ({len(penjualan_df)} bulan)")

with col2:
    if len(prediksi_df) > 0:
        st.caption(f"🔮 **Periode Prediksi:** {prediksi_df.index.min().strftime('%b %Y')} - {prediksi_df.index.max().strftime('%b %Y')} ({len(prediksi_df)} bulan)")
    else:
        st.caption(f"🔮 **Periode Prediksi:** Belum ada")

with col3:
    current_month_str = datetime.now().strftime('%b %Y')
    st.caption(f"📍 **Bulan Ini:** {current_month_str}")

st.markdown("---")

# ================================================
# CHART PLOTLY
# ================================================

fig = go.Figure()

# Trace 1: Actual Sales (Data Historis)
fig.add_trace(go.Scatter(
    x=penjualan_df.index.map(lambda d: d.strftime('%Y-%m')),
    y=penjualan_df['kuantitas'].values,
    mode='lines+markers',
    name='Actual Sales',
    line=dict(color='#2E86AB', width=2),
    marker=dict(size=8),
    hovertemplate='<b>%{x}</b><br>Actual Sales: %{y:,.0f}<extra></extra>'
))

# Trace 2: Prediksi (dari database)
if len(prediksi_df) > 0:
    fig.add_trace(go.Scatter(
        x=prediksi_df.index.map(lambda d: d.strftime('%Y-%m')),
        y=prediksi_df['kuantitas'].values,
        mode='lines+markers',
        name='Prediksi (Database)',
        line=dict(color='#06D6A0', width=2, dash='dot'),
        marker=dict(size=8, symbol='diamond'),
        hovertemplate='<b>%{x}</b><br>Prediksi: %{y:,.0f}<extra></extra>'
    ))

# Trace 3: Prediksi Sementara (jika ada)
if temp_prediction is not None:
    temp_pred = temp_prediction
    fig.add_trace(go.Scatter(
        x=temp_pred['tanggal'].map(lambda d: d.strftime('%Y-%m')),
        y=temp_pred['kuantitas'].values,
        mode='lines+markers',
        name='Prediksi Sementara (Visualisasi)',
        line=dict(color='#F77F00', width=2, dash='dash'),
        marker=dict(size=10),
        hovertemplate='<b>%{x}</b><br>Prediksi Temp: %{y:,.0f}<extra></extra>'
    ))

# Vertical line untuk marking "bulan ini"
current_date_ts = pd.to_datetime(current_month).timestamp()
fig.add_vline(
    x=current_date_ts,
    line_dash="dash",
    line_color="gray",
    opacity=0.5,
    annotation_text="Bulan Ini",
    annotation_position="top"
)

# Gabungkan semua tanggal
all_dates = penjualan_df.index

if len(prediksi_df) > 0:
    all_dates = all_dates.union(prediksi_df.index)

if temp_prediction is not None:
    temp_dates = pd.DatetimeIndex(temp_prediction['tanggal'])
    all_dates = all_dates.union(temp_dates)

# 🔥 FIX: Samakan semua tipe datetime
all_dates = pd.to_datetime(all_dates)

# Layout
fig.update_xaxes(
    dtick="M1",
    tickformat="%b %Y",
    tickangle=45,
    range=[all_dates.min(), all_dates.max()]
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

# Keterangan
st.markdown("---")
st.markdown("""
### 📖 Keterangan:
- **Actual Sales (Biru)**: Data penjualan historis dari database
- **Prediksi (Hijau)**: Prediksi yang tersimpan di database (hasil dari Proses Akhir Bulan)
- **Prediksi Sementara (Orange)**: Prediksi untuk visualisasi saja, tidak disimpan ke database
""")