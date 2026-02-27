import streamlit as st
import pandas as pd
from datetime import datetime
import new_database
import io
from fpdf import FPDF

st.set_page_config(
    page_title="Data Penjualan",
    page_icon="🛍️",
    layout="wide"
)

# Header
# st.markdown("""
#     <div style='background-color: #28a745; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
#         <h1 style='color: white; text-align: center; margin: 0;'>
#             📦 KELOLA DATA BARANG
#         </h1>
#     </div>
# """, unsafe_allow_html=True)

st.header("Data Penjualan")

tab1, tab2, tab3, tab4 = st.tabs(["📝 Input Manual", "📤 Upload Excel", "📋 Daftar Penjualan", "🖨️ Print Nota"])

# ================================================
# TAB 1 : INPUT MANUAL
# ================================================

with tab1:
    st.subheader("➕ Input Transaksi Baru")

    # Initialize session state untuk harga total
    if 'jumlah' not in st.session_state:
        st.session_state.jumlah = 0
    if 'harga_satuan' not in st.session_state:
        st.session_state.harga_satuan = 0
    
    col1, col2 = st.columns(2)
    
    with col1:
        no_faktur = st.text_input("No Faktur")
        
        tanggal = st.date_input(
            "Tanggal",
            value=datetime.now(),
            help="Pilih tanggal transaksi",
            format="DD/MM/YYYY"
        )
        
        data_customer = new_database.get_all_data_customer(columns="nama")

        if not data_customer.empty:
            data_customer = data_customer.sort_values("nama")

        nama_customer = st.selectbox(
            "Nama Customer",
            options=data_customer["nama"].tolist(),
            help="Pilih customer yang telah terdaftar"
        )
        
        data_barang = new_database.get_all_data_barang(columns="nama")

        if not data_barang.empty:
            data_barang = data_barang.sort_values("nama")

        jenis_barang = st.selectbox(
            "Jenis Barang",
            options=data_barang["nama"].tolist(),
            help="Pilih jenis barang yang telah terdaftar"
        )

    with col2:
        satuan_barang = new_database.get_satuan_barang(jenis_barang)

        col_qty, col_sat = st.columns([2, 1])
        with col_qty:
            kuantitas = st.number_input(
                "Kuantitas:",
                min_value=0,
                step=1,
                format="%d",
                key="input_kuantitas"
            )
        with col_sat:
            st.text_input("Satuan", value=satuan_barang, disabled=True)
        
        harga_satuan = new_database.get_harga_customer(nama_customer, jenis_barang)

        if harga_satuan is None:
            harga_satuan = 0

        st.text_input(
            "Harga Satuan",
            value=f"Rp {harga_satuan:,.0f}".replace(",", "."),
            disabled=True
        )
        
        total = kuantitas * harga_satuan        
        # st.markdown(f"""
        #     <div style='background-color: #e8f4f8; padding: 10px; border-radius: 5px; border-left: 4px solid #0066cc;'>
        #         <p style='margin: 0; font-size: 14px; color: #666;'>Total yang harus dibayar:</p>
        #         <p style='margin: 0; font-size: 24px; font-weight: bold; color: #0066cc;'>
        #             Rp {total:,.0f}
        #         </p>
        #     </div>
        # """.replace(",", "."), unsafe_allow_html=True)

        st.text_input(
            "Total ",
            value=f"Rp {total:,.0f}".replace(",", "."),
            disabled=True
        )

        default_top = new_database.get_top_customer(nama_customer) if nama_customer else 0
        
        top = st.number_input(
            "Terms of Payment (hari)",
            min_value=0,
            step=1,
            value=int(default_top),
            format="%d",
            help="Pembayaran harus lunas dalam berapa hari (Otomatis menggunakan default customer)"
        )
    
    st.markdown("---")
    
    if st.button("💾 Simpan", type="primary", use_container_width=True, key="btn_input_manual"):
        # ======================
        # VALIDASI SEDERHANA
        # ======================
        if not no_faktur:
            st.error("No Faktur wajib diisi")
            st.stop()

        if kuantitas <= 0:
            st.error("Kuantitas harus lebih dari 0")
            st.stop()

        # ======================
        # CEK VALIDASI NOTA & DUPLIKASI
        # ======================
        # Ambil data transaksi berdasarkan customer saja (agar bisa mengecek seluruh barang di nota tersebut)
        df_existing = new_database.get_data_penjualan(
            customer=nama_customer
        )
        
        if not df_existing.empty:
            # Bersihkan dan samakan tipe data
            df_existing["no_nota_str"] = df_existing["no_nota"].astype(str).str.strip()
            df_existing["tanggal_date"] = pd.to_datetime(df_existing["tanggal"]).dt.date
            df_existing["qty_int"] = df_existing["kuantitas"].fillna(0).astype(int)
            df_existing["top_int"] = df_existing["top"].fillna(0).astype(int)
            
            # Cari apakah Nota & Tanggal ini sudah ada di database
            same_nota = df_existing[
                (df_existing["no_nota_str"] == str(no_faktur).strip()) &
                (df_existing["tanggal_date"] == tanggal)
            ]
            
            if not same_nota.empty:
                # 1️⃣ CEK KONSISTENSI TOP
                # Ambil nilai TOP yang sudah tersimpan untuk nota ini
                existing_top = same_nota.iloc[0]["top_int"]
                
                if existing_top != int(top):
                    st.error(f"❌ Input Gagal: No Faktur '{no_faktur}' sudah tersimpan dengan TOP {existing_top} hari. Dalam 1 nota, TOP tidak boleh berbeda!")
                    st.stop()
                
                # 2️⃣ CEK DUPLIKASI BARANG & QTY (Mencegah input dobel)
                duplicate = same_nota[
                    (same_nota["nama_barang"] == jenis_barang) &
                    (same_nota["qty_int"] == int(kuantitas))
                ]
                
                if not duplicate.empty:
                    st.warning(f"⚠️ Transaksi untuk faktur {no_faktur} dengan barang {jenis_barang} (Qty: {kuantitas}) sudah pernah diinput!")
                    st.stop()

        # ======================
        # BENTUK DATAFRAME SESUAI INSERT_PENJUALAN
        # ======================
        df_input = pd.DataFrame([{
            "No. Faktur": no_faktur,
            "Tgl Faktur": tanggal,
            "Nama Pelanggan": nama_customer,
            "Keterangan Barang": jenis_barang,
            "Kuantitas": kuantitas,
            "Harga Satuan": float(harga_satuan),
            "Jumlah": float(total)
        }])

        success, failed, errors = new_database.insert_penjualan(df_input, default_top=top)

        if success > 0:
            st.success("✅ Transaksi berhasil disimpan")
        else:
            st.error("❌ Gagal menyimpan transaksi")
            if errors:
                st.error(errors[0])

# ================================================
# TAB 2 : UPLOAD EXCEL
# ================================================

with tab2:
    st.subheader("📤 Upload File Excel")
    
    with st.expander("ℹ️ Format file Excel data penjualan"):
        st.write("""
        - Kolom wajib: `No. Faktur`, `Tgl Faktur`, `Nama Pelanggan`, `Keterangan Barang`, `Kuantitas`, `Jumlah`
        - Kolom opsional: `Satuan`, `Harga Satuan`, `TOP`
        - Nama Barang dan Customer harus sudah ada di database
        """)
    
    uploaded_file = st.file_uploader(
        "Pilih file Excel",
        type=["xlsx"],
        help="Upload file Excel dengan format yang sesuai"
    )
    
    if uploaded_file is not None:
        try:
            df_raw = pd.read_excel(uploaded_file, header=None)

            EXPECTED_COLS = ["Tgl Faktur", "No. Faktur", "Nama Pelanggan", "Keterangan Barang", "Kuantitas", "Jumlah"]

            header_row_index = None

            for i, row in df_raw.iterrows():
                row_str = row.astype(str).str.upper()
                if all(any(col.upper() in cell for cell in row_str) for col in EXPECTED_COLS):
                    header_row_index = i
                    break

            df = pd.read_excel(uploaded_file, header=header_row_index)

            # Identifikasi kolom yang akan dipakai
            actual_cols = [col for col in EXPECTED_COLS if col in df.columns]

            # Cek jika excel memiliki kolom opsional
            if "Satuan" in df.columns:
                actual_cols.append("Satuan")
            if "Harga Satuan" in df.columns:
                actual_cols.append("Harga Satuan")
            if "TOP" in df.columns:
                actual_cols.append("TOP")

            df = df.dropna(how="all")
            df = df[EXPECTED_COLS]
            df = new_database.clean_excel_apostrophe(df)

            mismatch_errors = []

            # 1. PENGECEKAN SATUAN BARANG
            if "Satuan" in df.columns:
                df_barang_db = new_database.get_all_data_barang(["nama", "satuan"])
                dict_satuan_db = dict(zip(df_barang_db['nama'].str.upper(), df_barang_db['satuan'].astype(str).str.lower()))
                
                for idx, row in df.iterrows():
                    excel_nama = str(row.get('Keterangan Barang')).strip().upper()
                    excel_satuan = str(row.get('Satuan')).strip().lower()
                    
                    if not pd.isna(row.get('Satuan')) and excel_nama in dict_satuan_db:
                        db_satuan = dict_satuan_db[excel_nama]
                        if excel_satuan != db_satuan:
                            mismatch_errors.append(f"Baris {idx + header_row_index + 2}: Barang '{row['Keterangan Barang']}' (Satuan Excel: {row['Satuan']} | Satuan DB: {db_satuan})")
            
            # 2. PENGECEKAN HARGA SATUAN
            if "Harga Satuan" in df.columns:
                for idx, row in df.iterrows():
                    customer = str(row.get('Nama Pelanggan')).strip()
                    barang = str(row.get('Keterangan Barang')).strip()
                    excel_price = row.get('Harga Satuan')
                    
                    if pd.notna(excel_price):
                        db_price = new_database.get_harga_customer(customer, barang)
                        if db_price is None:
                            db_price = 0
                        
                        # Toleransi perbedaan koma / desimal kecil (jika selisih >= 1 Rupiah, anggap beda)
                        if abs(float(excel_price) - float(db_price)) >= 1:
                            mismatch_errors.append(f"Baris {idx + header_row_index + 2}: Harga Satuan '{barang}' untuk '{customer}' tidak sesuai! (Excel: Rp {float(excel_price):,.0f} | DB: Rp {float(db_price):,.0f})")
            else:
                # 3. JIKA TIDAK ADA KOLOM HARGA SATUAN, HITUNG OTOMATIS
                # Mencegah error pembagian dengan 0 (ZeroDivisionError)
                df["Harga Satuan"] = df.apply(
                    lambda row: float(row["Jumlah"]) / float(row["Kuantitas"]) if float(row["Kuantitas"]) > 0 else 0, 
                    axis=1
                )
            
            # Jika ada error dari satuan ATAU harga satuan, blokir proses
            if mismatch_errors:
                st.error("❌ Terdapat ketidaksesuaian data (Satuan / Harga) dengan yang ada di database. Upload dibatalkan.")
                with st.expander("Lihat detail error"):
                    for err in mismatch_errors:
                        st.error(err)
                st.stop()

            st.success("✅ Data berhasil dibersihkan!")
                    
            st.subheader("📋 Preview Data")
            st.dataframe(df.head(10), use_container_width=True)
            st.info(f"Total baris: {len(df)}")

            if st.button("💾 Simpan", type="primary", use_container_width=True):
                with st.spinner("Mengupload data ke database..."):
                    success_count, error_count, errors = new_database.insert_penjualan(df, default_top=None)
                            
                if success_count > 0:
                    st.success(f"✅ Berhasil mengupload {success_count} baris data!")
                            
                if error_count > 0:
                    st.warning(f"⚠️ {error_count} baris gagal diupload")
                                
                    with st.expander("Lihat detail error"):
                        for error in errors[:20]:
                            st.error(error)
                                    
                        if len(errors) > 20:
                            st.info(f"... dan {len(errors) - 20} error lainnya")
        except Exception as e:
            st.error(f"❌ Error membaca file: {str(e)}")

# ================================================
# TAB 3 : TABEL PENJUALAN
# ================================================

with tab3:
    st.subheader("📋 Daftar Transaksi Penjualan")

    with st.expander("ℹ️ Info edit & hapus transaksi"):
        st.write("""
        - Pilih checkbox untuk menandai transaksi yang akan dihapus. Klik tombol `Hapus Data Terpilih` untuk menghapus transaksi yang ditandai.
        - Jika ingin edit data, hapus data lama dan input kembali pada tab `Input Manual`.
        
        ⚠️ Menghapus transaksi bersifat permanen dan tidak dapat dikembalikan
        """)

    col1, col2, col3 = st.columns([1.5, 1.5, 1.5])

    with col1:
        selected_date = st.date_input(
            "📅 Tanggal",
            value=[],
            help="Kosongkan untuk tampilkan semua."
        )

        start_date, end_date = None, None
        if len(selected_date) == 2:
            start_date, end_date = selected_date
        elif len(selected_date) == 1:
            start_date = end_date = selected_date[0]

    with col2:
        data_customer = new_database.get_all_data_customer(columns="nama")

        if not data_customer.empty:
            data_customer = data_customer.sort_values("nama")

        customer_options = ["Semua"] + data_customer["nama"].tolist()
        selected_pelanggan = st.selectbox("👤 Nama Customer", customer_options)

    with col3:
        data_barang = new_database.get_all_data_barang(columns="nama")

        if not data_barang.empty:
            data_barang = data_barang.sort_values("nama")

        barang_options = ["Semua"] + data_barang["nama"].tolist()
        selected_barang = st.selectbox("📦 Nama Barang", barang_options)

    # ======================
    # AMBIL DATA
    # ======================
    df_penjualan = new_database.get_data_penjualan(
        start_date=start_date,
        end_date=end_date,
        customer=selected_pelanggan,
        barang=selected_barang
    )

    if not df_penjualan.empty:
        total_semua_penjualan = df_penjualan['subtotal'].sum()

        df_penjualan['tanggal'] = pd.to_datetime(df_penjualan['tanggal']).dt.strftime('%d %b %Y')

        if 'harga_satuan' in df_penjualan.columns:
            df_penjualan['harga_satuan'] = df_penjualan['harga_satuan'].apply(
                lambda x: f"Rp {x:,.0f}".replace(",", ".") if pd.notna(x) else "Rp 0"
            )

        df_penjualan['subtotal'] = df_penjualan['subtotal'].apply(
            lambda x: f"Rp {x:,.0f}".replace(",", ".")
        )

        if 'total_nota' in df_penjualan.columns:
            df_penjualan['total_nota'] = df_penjualan['total_nota'].apply(
                lambda x: f"Rp {x:,.0f}".replace(",", ".")
            )

        # Hitung total transaksi yang tertampil
        total_transaksi = len(df_penjualan)
        st.info(f"Menampilkan {total_transaksi} transaksi")

        # Tambah kolom checkbox untuk hapus
        df_penjualan.insert(0, 'Hapus', False)

        # Prepare kolom untuk ditampilkan (hide id)
        df_display = df_penjualan[['Hapus', 'no_nota', 'tanggal', 'nama_customer', 'nama_barang', 'satuan', 'kuantitas', 'harga_satuan', 'subtotal', 'total_nota', 'top']].copy()

        column_config = {
            "Hapus": st.column_config.CheckboxColumn("Pilih"),
            "no_nota": st.column_config.TextColumn("No. Faktur"),
            "tanggal": st.column_config.TextColumn("Tanggal"),
            "nama_customer": st.column_config.TextColumn("Customer"),
            "nama_barang": st.column_config.TextColumn("Barang"),
            "satuan": st.column_config.TextColumn("Satuan"),
            "kuantitas": st.column_config.NumberColumn("Qty"),
            "harga_satuan": st.column_config.TextColumn("Price"),
            "subtotal": st.column_config.TextColumn("Subtotal"),
            "total_nota": st.column_config.TextColumn("Total"),
            "top": st.column_config.NumberColumn("TOP"),
        }

        edited_df = st.data_editor(
            df_display,
            hide_index=True,
            use_container_width=True,
            disabled=["no_nota", "tanggal", "nama_customer", "nama_barang", "satuan", "kuantitas", "harga_satuan", "subtotal", "total_nota", "top"],
            column_config=column_config,
            key="penjualan_editor"
        )

        st.write("")
        _, col_total_bawah = st.columns([3, 1])
        with col_total_bawah:
            total_fmt = f"Rp {total_semua_penjualan:,.0f}".replace(",", ".")
            st.markdown(
                f"<div style='text-align:right; font-size:18px; font-weight:bold; color:#28a745;'>"
                f"Total: <br>{total_fmt}</div>",
                unsafe_allow_html=True
            )

        # Ambil baris yang dicentang
        selected_rows = edited_df[edited_df['Hapus'] == True]

        if not selected_rows.empty:
            # Ambil ID dari dataframe asli berdasarkan index yang sama
            selected_ids = df_penjualan.loc[selected_rows.index, 'id'].unique()
            
            st.warning(f"⚠️ {len(selected_ids)} transaksi akan dihapus")

            if st.button("🗑️ Hapus Data Terpilih", type="primary"):
                try:
                    with st.spinner("Menghapus data..."):
                        for pid in selected_ids:
                            new_database.delete_penjualan(pid)

                    st.success("✅ Data berhasil dihapus")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Gagal menghapus data: {str(e)}")
    else:
        st.warning("⚠️ Tidak ada data transaksi sesuai filter")

# ================================================
# TAB 4 : PRINT NOTA
# ================================================

with tab4:
    st.subheader("🖨️ Print Nota Penjualan")

    # Gunakan fungsi baru yang mengembalikan dictionary
    dict_nota = new_database.get_list_nota_untuk_print()
    list_nota_display = ["-- Pilih Nota --"] + list(dict_nota.keys())
    
    selected_nota_display = st.selectbox(
        "Pilih No. Nota", 
        list_nota_display,
        help="Pilih nota yang ingin dicetak"
    )

    if selected_nota_display != "-- Pilih Nota --":
        # Ambil ID Penjualan unik dari dictionary
        selected_id_penjualan = dict_nota[selected_nota_display]

        # Ambil data spesifik MENGGUNAKAN ID PENJUALAN
        df_cetak = new_database.get_data_penjualan(id_penjualan=selected_id_penjualan)

        if not df_cetak.empty:
            # Info Header Nota
            selected_nota = df_cetak.iloc[0]['no_nota'] # Ambil no_nota bersih untuk nama file & text rendering
            tgl_nota = pd.to_datetime(df_cetak.iloc[0]['tanggal']).strftime('%d %b %Y')
            cust_nota = df_cetak.iloc[0]['nama_customer']
            total_nota = df_cetak.iloc[0]['total_nota']

            # ── HEADER NOTA (pakai komponen native Streamlit, bukan HTML mentah) ──
            with st.container(border=True):
                st.markdown("### BERKAT MAJU BERSAMA")
                st.caption("Email: berkatmajubersama99999@gmail.com  |  📞 0898-105-9090")
                st.divider()

                col_left, col_right = st.columns(2)
                with col_left:
                    st.markdown(f"**NOTA:** No. {selected_nota}")
                with col_right:
                    st.markdown(f"**Tanggal:** {tgl_nota}")
                    st.markdown(f"**Toko:** {cust_nota}")

                # Spasi antara info nota dan tabel
                st.write("")

                # Persiapkan tabel untuk preview dan export
                df_table = df_cetak[['kuantitas', 'satuan', 'nama_barang', 'harga_satuan', 'subtotal']].copy()
                df_table['Kuantitas'] = df_table['kuantitas'].astype(str) + " " + df_table['satuan'].fillna("").astype(str)

                # Format harga untuk preview
                df_table['Harga (Rp)'] = df_table['harga_satuan'].apply(lambda x: f"{x:,.0f}".replace(",", "."))
                df_table['Jumlah (Rp)'] = df_table['subtotal'].apply(lambda x: f"{x:,.0f}".replace(",", "."))

                df_preview = (
                    df_table[['Kuantitas', 'nama_barang', 'Harga (Rp)', 'Jumlah (Rp)']]
                    .rename(columns={'nama_barang': 'Nama Barang'})
                    .reset_index(drop=True)
                )
                df_preview.index += 1  # index mulai dari 1 (bukan 0)

                # Tampilkan tabel dengan lebar kolom yang konsisten
                st.dataframe(
                    df_preview,
                    use_container_width=True,
                    column_config={
                        "Kuantitas":   st.column_config.TextColumn("Kuantitas",   width="small"),
                        "Nama Barang": st.column_config.TextColumn("Nama Barang", width="large"),
                        "Harga (Rp)":  st.column_config.TextColumn("Harga (Rp)",  width="medium"),
                        "Jumlah (Rp)": st.column_config.TextColumn("Jumlah (Rp)", width="medium"),
                    }
                )

                # Baris total di kanan bawah
                st.write("")
                _, col_total = st.columns([3, 1])
                with col_total:
                    total_fmt = f"Rp {total_nota:,.0f}".replace(",", ".")
                    st.markdown(
                        f"<div style='text-align:right; font-size:18px; font-weight:bold; color:#d9534f;'>"
                        f"Total: {total_fmt}</div>",
                        unsafe_allow_html=True
                    )

            st.markdown("---")
            
            # ==============================
            # BUTTON EXPORT EXCEL & PDF
            # ==============================
            col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])

            # 1. EXPORT TO EXCEL
            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
                workbook = writer.book
                worksheet = workbook.add_worksheet('Nota')
                
                bold = workbook.add_format({'bold': True})
                header_format = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1, 'align': 'center'})
                border_format = workbook.add_format({'border': 1})
                num_format = workbook.add_format({'border': 1, 'num_format': '#,##0'})
                
                worksheet.write('A1', 'BERKAT MAJU BERSAMA', bold)
                worksheet.write('A2', 'Email: berkatmajubersama99999@gmail.com')
                worksheet.write('A3', '0898-105-9090')
                
                worksheet.write('A5', f'NOTA: No. {selected_nota}', bold)
                worksheet.write('D5', f'Tanggal: {tgl_nota}')
                worksheet.write('D6', f'Tuan/Toko: {cust_nota}')
                
                headers = ['Kuantitas', 'Nama Barang', 'Harga (Rp)', 'Jumlah (Rp)']
                for col_num, data in enumerate(headers):
                    worksheet.write(7, col_num, data, header_format)
                
                row = 8
                for idx, item in df_table.iterrows():
                    worksheet.write(row, 0, item['kuantitas'], border_format)
                    worksheet.write(row, 1, item['nama_barang'], border_format)
                    worksheet.write(row, 2, item['harga_satuan'], num_format)
                    worksheet.write(row, 3, item['subtotal'], num_format)
                    row += 1
                
                worksheet.write(row, 2, 'Total Rp.', bold)
                worksheet.write(row, 3, total_nota, num_format)
                
                worksheet.set_column('A:A', 15)
                worksheet.set_column('B:B', 40)
                worksheet.set_column('C:D', 20)

            excel_data = output_excel.getvalue()

            with col_btn1:
                st.download_button(
                    label="📥 Download Excel",
                    data=excel_data,
                    file_name=f"Nota_{selected_nota}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            # 2. EXPORT TO PDF
            class PDF(FPDF):
                def header(self):
                    self.set_font('Arial', 'B', 16)
                    self.set_text_color(0, 86, 179)
                    self.cell(0, 8, 'BERKAT MAJU BERSAMA', 0, 1, 'L')
                    
                    self.set_font('Arial', '', 10)
                    self.set_text_color(50, 50, 50)
                    self.cell(0, 5, 'Email: berkatmajubersama99999@gmail.com', 0, 1, 'L')
                    self.cell(0, 5, '0898-105-9090', 0, 1, 'L')
                    
                    self.set_draw_color(0, 86, 179)
                    self.line(10, 32, 200, 32)
                    self.ln(10)

            pdf = PDF()
            pdf.add_page()
            
            pdf.set_font('Arial', 'B', 12)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(100, 8, f'NOTA: No. {selected_nota}', 0, 0, 'L')
            
            pdf.set_font('Arial', '', 11)
            pdf.cell(90, 8, f'Tanggal: {tgl_nota}', 0, 1, 'R')
            pdf.cell(190, 8, f'Tuan/Toko: {cust_nota}', 0, 1, 'R')
            pdf.ln(5)

            pdf.set_font('Arial', 'B', 11)
            pdf.set_fill_color(217, 225, 242)
            pdf.cell(30, 10, 'Kuantitas', 1, 0, 'C', fill=True)
            pdf.cell(90, 10, 'Nama Barang', 1, 0, 'C', fill=True)
            pdf.cell(35, 10, 'Harga (Rp)', 1, 0, 'C', fill=True)
            pdf.cell(35, 10, 'Jumlah (Rp)', 1, 1, 'C', fill=True)

            pdf.set_font('Arial', '', 11)
            for idx, item in df_table.iterrows():
                pdf.cell(30, 10, str(item['kuantitas']), 1, 0, 'C')
                pdf.cell(90, 10, str(item['nama_barang'])[:45], 1, 0, 'L')
                pdf.cell(35, 10, f"{item['harga_satuan']:,.0f}".replace(",", "."), 1, 0, 'R')
                pdf.cell(35, 10, f"{item['subtotal']:,.0f}".replace(",", "."), 1, 1, 'R')

            pdf.set_font('Arial', 'B', 12)
            pdf.cell(120, 10, '', 0, 0)
            pdf.cell(35, 10, 'Total Rp.', 1, 0, 'R', fill=True)
            pdf.set_text_color(200, 0, 0)
            pdf.cell(35, 10, f"{total_nota:,.0f}".replace(",", "."), 1, 1, 'R')

            pdf_bytes = pdf.output(dest='S').encode('latin1')

            with col_btn2:
                st.download_button(
                    label="📄 Download PDF",
                    data=pdf_bytes,
                    file_name=f"Nota_{selected_nota}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

# Footer
# st.markdown("---")
# st.markdown("""
#     <div style='text-align: center; color: #666; padding: 10px;'>
#         <small>📦 Sistem Kelola Data Barang | Developed with Streamlit</small>
#     </div>
# """, unsafe_allow_html=True)