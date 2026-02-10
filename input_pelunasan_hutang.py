import streamlit as st
import pandas as pd
from datetime import datetime
import new_database

st.set_page_config(page_title="Pelunasan Hutang", page_icon="💸", layout="wide")
st.header("💸 Input Pelunasan Hutang (Supplier)")

if "success_msg" not in st.session_state:
    st.session_state.success_msg = None
if st.session_state.success_msg:
    st.success(st.session_state.success_msg)
    st.session_state.success_msg = None

tab1, tab2, tab3 = st.tabs(["📝 Input Manual", "📤 Upload Excel", "📋 Riwayat Pembayaran"])

# ================= TAB 1: INPUT MANUAL =================
with tab1:
    st.subheader("Input Pembayaran Hutang")
    
    # 1. Pilih Supplier
    suppliers = new_database.get_all_data_supplier(["id", "nama"])
    supp_opts = {"-- Pilih Supplier --": None}
    if not suppliers.empty:
        supp_opts.update(dict(zip(suppliers['nama'], suppliers['id'])))
    
    sel_supp = st.selectbox("Cari Supplier", options=list(supp_opts.keys()))
    
    if sel_supp != "-- Pilih Supplier --":
        id_supp = supp_opts[sel_supp]
        
        # 2. Ambil Invoice Hutang
        invoices = new_database.get_outstanding_invoices("hutang", id_supp)
        
        if invoices.empty:
            st.info("✅ Tidak ada hutang yang belum lunas ke supplier ini.")
        else:
            invoices['display'] = invoices.apply(
                lambda x: f"{x['no_nota']} | Sisa: Rp {x['sisa']:,.0f} | Due: {x['due_date']}", axis=1
            )
            inv_opts = dict(zip(invoices['display'], invoices['id']))
            sel_inv = st.selectbox("Pilih No Nota / Invoice", options=list(inv_opts.keys()))
            id_inv = inv_opts[sel_inv]
            
            sisa_tagihan = invoices[invoices['id'] == id_inv]['sisa'].values[0]
            
            with st.form("form_bayar_hutang"):
                col1, col2 = st.columns(2)
                with col1:
                    tgl_bayar = st.date_input("Tanggal Bayar", value=datetime.now())
                    metode = st.selectbox("Metode", ["Transfer", "Cash", "Giro"])
                with col2:
                    jml_bayar = st.number_input("Jumlah Bayar", min_value=0.0, max_value=float(sisa_tagihan), step=1000.0)
                    ref = st.text_input("No Referensi")
                
                ket = st.text_area("Keterangan")
                
                if st.form_submit_button("💾 Simpan Pembayaran", type="primary"):
                    if jml_bayar <= 0:
                        st.error("Jumlah bayar harus > 0")
                    else:
                        success, msg = new_database.insert_pembayaran(
                            "hutang", id_inv, tgl_bayar, jml_bayar, metode, ref, ket
                        )
                        if success:
                            st.session_state.success_msg = f"✅ {msg}"
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

# ================= TAB 2: UPLOAD EXCEL =================
with tab2:
    st.subheader("Upload Pembayaran Massal")
    st.info("Fitur ini memungkinkan upload pembayaran hutang dari file Excel (Maintenance).")

# ================= TAB 3: RIWAYAT =================
with tab3:
    st.subheader("Riwayat & Pembatalan")
    col1, col2 = st.columns(2)
    with col1: start_d = st.date_input("Dari Tanggal", value=datetime(datetime.now().year, datetime.now().month, 1))
    with col2: end_d = st.date_input("Sampai Tanggal", value=datetime.now())
        
    df_hist = new_database.get_history_pembayaran("hutang", start_d, end_d)
    
    if not df_hist.empty:
        df_hist['jumlah_bayar'] = df_hist['jumlah_bayar'].apply(lambda x: f"Rp {x:,.0f}")
        df_hist.insert(0, "Hapus", False)
        
        edited_df = st.data_editor(df_hist, column_config={"Hapus": st.column_config.CheckboxColumn(), "id": None}, hide_index=True, use_container_width=True)
        
        if st.button("🗑️ Konfirmasi Pembatalan"):
            to_delete = edited_df[edited_df['Hapus'] == True]
            for idx, row in to_delete.iterrows():
                new_database.delete_pembayaran("hutang", row['id'])
            st.success("✅ Pembayaran berhasil dibatalkan.")
            st.rerun()
    else:
        st.info("Tidak ada riwayat pembayaran.")