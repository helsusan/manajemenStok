import streamlit as st
import pandas as pd
from datetime import datetime
import new_database

st.set_page_config(page_title="Pelunasan Piutang", page_icon="💰", layout="wide")
st.header("💰 Input Pelunasan Piutang (Customer)")

# --- SESSION STATE ---
if "success_msg" not in st.session_state:
    st.session_state.success_msg = None

if st.session_state.success_msg:
    st.success(st.session_state.success_msg)
    st.session_state.success_msg = None

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📝 Input Manual", "📤 Upload Excel", "📋 Riwayat Pembayaran"])

# ================= TAB 1: INPUT MANUAL =================
with tab1:
    st.subheader("Input Pembayaran Piutang")
    
    # 1. Pilih Customer
    customers = new_database.get_all_data_customer(["id", "nama"])
    cust_opts = {"-- Pilih Customer --": None}
    if not customers.empty:
        cust_opts.update(dict(zip(customers['nama'], customers['id'])))
    
    sel_cust = st.selectbox("Cari Customer", options=list(cust_opts.keys()))
    
    if sel_cust != "-- Pilih Customer --":
        id_cust = cust_opts[sel_cust]
        
        # 2. Ambil Invoice Belum Lunas
        available_piutang = new_database.get_outstanding_invoices("piutang", id_cust)
        
        if available_piutang.empty:
            st.info("✅ Tidak ada piutang yang belum lunas untuk customer ini.")
        else:
            # Tampilkan detail nota yang belum lunas
            st.markdown("### 📋 Daftar Nota Belum Lunas:")

            # Format invoice untuk dropdown
            available_piutang['display'] = available_piutang.apply(
                lambda x: f"No. Nota: {x['no_nota']} | Total: Rp {x['total']:,.0f} | Terbayar: Rp {x['terbayar']:,.0f} | Sisa: Rp {x['sisa']:,.0f} | Jatuh Tempo: {pd.to_datetime(x['due_date']).strftime('%d %b %Y')}", axis=1
            )

            # Dictionary mapping: display text -> id piutang
            inv_opts = dict(zip(available_piutang['display'], available_piutang['id']))
            
            sel_inv = st.selectbox(
                "Pilih Nota yang akan dibayar",
                options=list(inv_opts.keys()),
                key="select_invoice"
            )

            # id_piutang yang dipilih (ini yang akan disimpan ke database)
            id_piutang_selected = inv_opts[sel_inv]
            
            # Ambil data detail nota yang dipilih
            selected_invoice = available_piutang[available_piutang['id'] == id_piutang_selected].iloc[0]
            
            # Tampilkan info nota yang dipilih
            st.markdown("---")
            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                st.metric("Total Tagihan", f"Rp {selected_invoice['total']:,.0f}".replace(",", "."))
            with col_info2:
                st.metric("Sudah Terbayar", f"Rp {selected_invoice['terbayar']:,.0f}".replace(",", "."))
            with col_info3:
                st.metric("Sisa Tagihan", f"Rp {selected_invoice['sisa']:,.0f}".replace(",", "."))
            
            st.markdown("---")
            
            # Form Input Pembayaran
            with st.form("form_bayar_piutang"):
                st.markdown("### 💳 Form Pembayaran")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Field: no_invoice (invoice pembayaran)
                    no_invoice_bayar = st.text_input(
                        "No. Invoice Pembayaran", 
                        placeholder="Contoh: INV-PAY-001",
                        help="Nomor invoice untuk pembayaran ini (opsional)"
                    )
                    
                    # Field: tanggal_bayar
                    tanggal_bayar = st.date_input(
                        "Tanggal Bayar", 
                        value=datetime.now(),
                        help="Tanggal dilakukan pembayaran"
                    )
                
                with col2:
                    # Field: jumlah (jumlah pembayaran)
                    jumlah_bayar = st.number_input(
                        "Jumlah Bayar (Rp)", 
                        min_value=0.0, 
                        max_value=float(selected_invoice['sisa']), 
                        value=float(selected_invoice['sisa']),
                        step=1000.0,
                        format="%.0f",
                        help=f"Maksimal: Rp {selected_invoice['sisa']:,.0f}".replace(",", "."),
                        key="input_jumlah_bayar"
                    )
                
                # Field: keterangan
                keterangan = st.text_area(
                    "Keterangan", 
                    placeholder="Contoh: Pembayaran via transfer BCA",
                    help="Catatan tambahan untuk pembayaran ini"
                )
                
                st.markdown("---")
                
                # Tombol Submit
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    submit_bayar = st.form_submit_button(
                        "💾 Simpan Pembayaran", 
                        type="primary", 
                        use_container_width=True
                    )
                
                with col_btn2:
                    cancel_bayar = st.form_submit_button(
                        "❌ Batal", 
                        use_container_width=True
                    )
                
                # Proses Submit
                if submit_bayar and not cancel_bayar:
                    # Validasi
                    if jumlah_bayar <= 0:
                        st.error("⚠️ Jumlah bayar harus lebih dari 0")
                        st.stop()
                    else:
                        # Siapkan data untuk insert
                        # created_at akan di-handle di function insert
                        success, msg = new_database.insert_pembayaran_piutang(
                            id_piutang=id_piutang_selected,
                            no_invoice=no_invoice_bayar if no_invoice_bayar else None,
                            tanggal_bayar=tanggal_bayar,
                            jumlah=jumlah_bayar,
                            keterangan=keterangan
                        )
                        
                        if success:
                            st.session_state.success_msg = f"✅ {msg}"
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
                
                if cancel_bayar:
                    st.rerun()

# ================= TAB 2: UPLOAD EXCEL =================
with tab2:
    st.subheader("Upload Pembayaran Massal")
    with st.expander("ℹ️ Format Excel"):
        st.write("Kolom Wajib: `No Invoice`, `Tanggal`, `Jumlah`, `Metode`")
        st.write("Pastikan `No Invoice` sama persis dengan yang ada di database.")
        
    uploaded_file = st.file_uploader("Upload File .xlsx", type=["xlsx"])
    
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            st.dataframe(df.head())
            
            if st.button("Proses Upload", type="primary"):
                # Logic sederhana: Loop dan insert
                # (Disarankan menambahkan validasi No Invoice ke database dulu di real app)
                st.info("Fitur ini akan memproses baris per baris...")
                # Implementasi loop insert_pembayaran di sini mirip tab manual
                st.warning("⚠️ Logic mapping No Invoice ke ID Invoice perlu query tambahan. Gunakan Tab Manual dulu untuk saat ini.")
        except Exception as e:
            st.error(f"Error: {e}")

# ================= TAB 3: RIWAYAT =================
with tab3:
    st.subheader("Riwayat Pembayaran Piutang")
    
    col1, col2 = st.columns(2)
    with col1:
        start_d = st.date_input("Dari Tanggal", value=datetime(datetime.now().year, datetime.now().month, 1))
    with col2:
        end_d = st.date_input("Sampai Tanggal", value=datetime.now())
        
    df_hist = new_database.get_history_pembayaran("piutang", start_d, end_d)
    
    if not df_hist.empty:
        # Format Dataframe
        df_hist['tanggal_bayar'] = pd.to_datetime(df_hist['tanggal_bayar']).dt.strftime('%d %b %Y')
        df_hist['jumlah_bayar'] = df_hist['jumlah_bayar'].apply(lambda x: f"Rp {x:,.0f}")
        
        # Tambahkan kolom delete
        df_hist.insert(0, "Hapus", False)
        
        edited_df = st.data_editor(
            df_hist,
            column_config={
                "Hapus": st.column_config.CheckboxColumn("Hapus", help="Centang untuk menghapus pembayaran"),
                "id": None, # Hide ID
                "no_pembayaran": st.column_config.TextColumn("No. Invoice Pembayaran"),
                "tanggal_bayar": st.column_config.TextColumn("Tanggal"),
                "no_invoice_tagihan": st.column_config.TextColumn("No. Faktur Penjualan"),
                "partner": st.column_config.TextColumn("Customer"),
                "jumlah_bayar": st.column_config.TextColumn("Jumlah Bayar"),
                "keterangan": st.column_config.TextColumn("Keterangan"),
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Logic Hapus
        to_delete = edited_df[edited_df['Hapus'] == True]
        if not to_delete.empty:
            st.warning(f"⚠️ Anda akan menghapus {len(to_delete)} pembayaran. Saldo invoice akan kembali bertambah.")
            if st.button("🗑️ Konfirmasi Pembatalan"):
                success_count = 0
                for idx, row in to_delete.iterrows():
                    res, _ = new_database.delete_pembayaran("piutang", row['id'])
                    if res: success_count += 1
                
                st.success(f"✅ {success_count} pembayaran berhasil dihapus.")
                st.rerun()
    else:
        st.info("Tidak ada riwayat pembayaran pada periode ini.")