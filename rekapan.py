import streamlit as st
import pandas as pd
import plotly.express as px
import new_database
from datetime import datetime

st.set_page_config(page_title="Dashboard Keuangan", page_icon="📊", layout="wide")

st.title("📊 Rekapan & Analisis Keuangan")
st.caption("Ringkasan status Hutang (AP) dan Piutang (AR) Perusahaan")

# ================= DATA FETCHING =================
# Mengambil ringkasan dari database
summ_piutang, overdue_piutang = new_database.get_analisis_summary("piutang")
summ_hutang, overdue_hutang = new_database.get_analisis_summary("hutang")

# ================= TOP KPI CARDS =================
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Piutang (Akan Diterima)", 
        f"Rp {summ_piutang['sisa_outstanding']:,.0f}",
        f"{summ_piutang['total_inv']} Invoice"
    )

with col2:
    st.metric(
        "Piutang Overdue (Macet)",
        f"Rp {overdue_piutang['nominal']:,.0f}",
        f"{overdue_piutang['count']} Invoice",
        delta_color="inverse" # Merah kalau tinggi (buruk)
    )

with col3:
    st.metric(
        "Total Hutang (Harus Dibayar)", 
        f"Rp {summ_hutang['sisa_outstanding']:,.0f}",
        f"{summ_hutang['total_inv']} Invoice",
        delta_color="inverse"
    )

with col4:
    st.metric(
        "Hutang Overdue (Bahaya)",
        f"Rp {overdue_hutang['nominal']:,.0f}",
        f"{overdue_hutang['count']} Invoice",
        delta_color="inverse"
    )

st.markdown("---")

# ================= TABS ANALISIS =================
tab1, tab2 = st.tabs(["📉 Analisis Piutang (Receivables)", "💸 Analisis Hutang (Payables)"])

def show_aging_table(jenis):
    """Helper untuk menampilkan tabel detail overdue"""
    df = new_database.get_outstanding_invoices(jenis)
    
    if df.empty:
        st.success("🎉 Tidak ada invoice outstanding!")
        return

    # Hitung Hari Keterlambatan
    df['due_date'] = pd.to_datetime(df['due_date'])
    df['overdue_days'] = (datetime.now() - df['due_date']).dt.days
    
    # Kategori Status Aging
    def get_status(days):
        if days < 0: return "Not Due"
        elif days <= 30: return "1-30 Hari"
        elif days <= 60: return "31-60 Hari"
        else: return "> 60 Hari"
        
    df['Status'] = df['overdue_days'].apply(get_status)
    
    # HAPUS BARIS YANG ERROR DULU (partner_ids = ...)
    # Sekarang kita langsung pakai kolom 'partner_name' dari query baru
    
    st.subheader(f"📋 Detail Invoice Outstanding ({'Customer' if jenis == 'piutang' else 'Supplier'})")
    
    # Tampilkan Tabel
    # Kita tambahkan kolom 'partner_name' agar terlihat siapa yang berhutang/dihutangi
    display_cols = ['no_nota', 'partner_name', 'due_date', 'total', 'sisa', 'overdue_days', 'Status']
    
    # Rename kolom untuk tampilan agar lebih rapi
    df_display = df[display_cols].rename(columns={
        'no_nota': 'No Invoice',
        'partner_name': 'Customer' if jenis == 'piutang' else 'Supplier',
        'due_date': 'Jatuh Tempo',
        'total': 'Total Tagihan',
        'sisa': 'Sisa Tagihan',
        'overdue_days': 'Telat (Hari)'
    })

    # Warnai tabel: Merah jika overdue (telat > 0 hari)
    st.dataframe(
        df_display.style.applymap(
            lambda v: 'color: red; font-weight: bold;' if isinstance(v, (int, float)) and v > 0 else '', 
            subset=['Telat (Hari)']
        ).format({
            'Total Tagihan': "Rp {:,.0f}",
            'Sisa Tagihan': "Rp {:,.0f}"
        }),
        use_container_width=True
    )
    
    # Chart Pie Aging
    st.subheader(f"📊 Distribusi Umur {jenis.capitalize()}")
    pie_data = df.groupby('Status')['sisa'].sum().reset_index()
    fig = px.pie(pie_data, values='sisa', names='Status', title=f"Aging {jenis.capitalize()} (Berdasarkan Nominal Sisa)")
    st.plotly_chart(fig, use_container_width=True)

with tab1:
    show_aging_table("piutang")

with tab2:
    show_aging_table("hutang")