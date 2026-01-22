import streamlit as st
import pandas as pd
from datetime import datetime
import new_database

st.set_page_config(
    page_title="Data Customer",
    page_icon="👥",
    layout="wide"
)

st.header("Data Customer")

# ===============================
# SESSION STATE GLOBAL
# ===============================

if "active_tab" not in st.session_state:
    st.session_state.active_tab = "tab1"

if "manual_success" not in st.session_state:
    st.session_state.manual_success = False

if "upload_success" not in st.session_state:
    st.session_state.upload_success = False

if "edit_success" not in st.session_state:
    st.session_state.edit_success = False

# State untuk menyimpan pricelist sementara di Tab 1
if "temp_pricelist" not in st.session_state:
    st.session_state.temp_pricelist = []

tab1, tab2, tab3, tab4 = st.tabs([
    "📝 Input Manual",
    "📤 Upload Excel", 
    "👥 Daftar Customer",
    "💰 Daftar Pricelist"
])

current_tab = (
    "tab1" if tab1 else
    "tab2" if tab2 else
    "tab3" if tab3 else
    "tab4"
)

if st.session_state.active_tab != current_tab:
    st.session_state.manual_success = False
    st.session_state.upload_success = False
    st.session_state.edit_success = False
    st.session_state.temp_pricelist = []
    st.session_state.active_tab = current_tab

# ================================================
# TAB 1 : INPUT MANUAL
# ================================================

with tab1:
    st.subheader("➕ Input Customer & Pricelist Baru")

    mode = st.radio(
        "Pilih Mode Input:",
        ["👥 Customer Baru", "💰 Tambah Pricelist ke Customer"],
        horizontal=True,
        key="input_mode"
    )
    
    col1, col2 = st.columns([2, 3])
    
    with col1:
        if mode == "👥 Customer Baru":
            nama_customer_baru = st.text_input(
                "Nama Customer Baru", 
                placeholder="Contoh: Toko Sumber Rejeki",
                help="Nama akan otomatis diformat ke Title Case"
            )
            
            if nama_customer_baru:
                formatted_name = new_database.normalize_customer_name(nama_customer_baru)
                if formatted_name != nama_customer_baru:
                    st.info(f"📝 Format otomatis: **{formatted_name}**")
            
            selected_customer_id = None
            selected_customer_name = formatted_name if nama_customer_baru else None
        
        else:  # Mode: Tambah ke existing customer
            df_customers = new_database.get_all_data_customer(["id", "nama"])
            
            if df_customers.empty:
                st.warning("⚠️ Belum ada customer di database. Silakan buat customer baru terlebih dahulu.")
                selected_customer_id = None
                selected_customer_name = None
            else:
                selected_customer_name = st.selectbox(
                    "Pilih Customer",
                    options=df_customers["nama"].tolist(),
                    key="select_existing_customer"
                )
                selected_customer_id = new_database.get_customer_id(selected_customer_name)
            
            nama_customer_baru = None
    
    with col2:
        st.markdown("### 💰 Pricelist")
        
        # Ambil daftar barang untuk dropdown
        df_barang = new_database.get_all_data_barang(["id", "nama"])
        
        if not df_barang.empty:
            col_barang, col_harga, col_btn = st.columns([3, 2, 1])
            
            with col_barang:
                selected_barang = st.selectbox(
                    "Pilih Barang",
                    options=df_barang["nama"].tolist(),
                    key="select_barang_manual"
                )
            
            with col_harga:
                harga_input = st.number_input(
                    "Harga",
                    min_value=0,
                    step=1000,
                    key="harga_manual"
                )
            
            with col_btn:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("➕", help="Tambah ke Pricelist", key="btn_add_pricelist"):
                    if harga_input > 0:
                        # Cek duplikasi
                        exists = any(p["barang"] == selected_barang for p in st.session_state.temp_pricelist)
                        if exists:
                            st.warning(f"⚠️ Barang '{selected_barang}' sudah ada di pricelist")
                        else:
                            # PERBAIKAN 1: Cek apakah sudah ada di database (untuk mode tambah ke existing customer)
                            if mode == "📝 Tambah Pricelist ke Customer" and selected_customer_id:
                                id_barang = new_database.get_barang_id(selected_barang)
                                if new_database.check_cust_pricelist_exists(selected_customer_id, id_barang):
                                    st.error(f"❌ Pricelist untuk barang '{selected_barang}' sudah ada di database!")
                                    st.info("💡 Silakan edit harga di tab **Daftar Pricelist**")
                                else:
                                    st.session_state.temp_pricelist.append({
                                        "barang": selected_barang,
                                        "harga": harga_input
                                    })
                                    st.rerun()
                            else:
                                # Mode customer baru, langsung tambahkan
                                st.session_state.temp_pricelist.append({
                                    "barang": selected_barang,
                                    "harga": harga_input
                                })
                                st.rerun()
                    else:
                        st.error("❌ Harga harus lebih dari 0")
        
        # Tampilkan pricelist sementara
        if st.session_state.temp_pricelist:
            st.markdown("#### 📋 Pricelist yang akan disimpan:")
            for idx, item in enumerate(st.session_state.temp_pricelist):
                col_item, col_del = st.columns([4, 1])
                with col_item:
                    st.text(f"{item['barang']}: Rp {item['harga']:,}")
                with col_del:
                    if st.button("🗑️", key=f"del_pricelist_{idx}", help="Hapus"):
                        st.session_state.temp_pricelist.pop(idx)
                        st.rerun()
        else:
            st.info("Belum ada pricelist. Tambahkan barang di atas.")
    
    st.markdown("---")
    
    # Tombol simpan dengan label yang sesuai mode
    btn_label = "💾 Simpan Customer & Pricelist" if mode == "🆕 Customer Baru" else "💾 Simpan Pricelist"
    
    if st.button(btn_label, type="primary", use_container_width=True, key="btn_simpan_manual"):
        # Validasi berdasarkan mode
        if mode == "🆕 Customer Baru":
            if not nama_customer_baru or nama_customer_baru.strip() == "":
                st.error("❌ Nama customer tidak boleh kosong!")
            else:
                try:
                    formatted_name = new_database.normalize_customer_name(nama_customer_baru)
                    
                    # Cek apakah customer sudah ada
                    if new_database.check_customer_available(formatted_name):
                        st.warning(f"⚠️ Customer '{formatted_name}' sudah ada di database!")
                    else:
                        # Insert customer
                        success, message = new_database.insert_customer(formatted_name)
                        
                        if success:
                            if st.session_state.temp_pricelist:
                                # Insert pricelist jika ada
                                id_customer = new_database.get_customer_id(formatted_name)
                                pricelist_success = 0
                                
                                for item in st.session_state.temp_pricelist:
                                    id_barang = new_database.get_barang_id(item["barang"])
                                    if new_database.upsert_customer_pricelist(id_customer, id_barang, item["harga"]):
                                        pricelist_success += 1
                                
                                st.session_state.manual_success = f"Customer '{formatted_name}' dan {pricelist_success} pricelist berhasil disimpan!"
                            else:
                                # Customer saja tanpa pricelist
                                st.session_state.manual_success = f"Customer '{formatted_name}' berhasil disimpan!"
                            
                            st.session_state.temp_pricelist = []
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        else:  # Mode: Tambah ke existing customer
            if not selected_customer_id:
                st.error("❌ Pilih customer terlebih dahulu!")
            elif not st.session_state.temp_pricelist:
                st.error("❌ Tambahkan minimal 1 barang ke pricelist!")
            else:
                try:
                    pricelist_success = 0
                    pricelist_updated = 0
                    
                    for item in st.session_state.temp_pricelist:
                        id_barang = new_database.get_barang_id(item["barang"])
                        
                        # Cek apakah pricelist sudah ada
                        existing = new_database.check_cust_pricelist_exists(selected_customer_id, id_barang)
                        
                        if new_database.upsert_customer_pricelist(selected_customer_id, id_barang, item["harga"]):
                            if existing:
                                pricelist_updated += 1
                            else:
                                pricelist_success += 1
                    
                    msg_parts = []
                    if pricelist_success > 0:
                        msg_parts.append(f"{pricelist_success} pricelist baru ditambahkan")
                    if pricelist_updated > 0:
                        msg_parts.append(f"{pricelist_updated} pricelist diupdate")
                    
                    st.session_state.manual_success = f"Pricelist untuk '{selected_customer_name}' berhasil disimpan! ({', '.join(msg_parts)})"
                    st.session_state.temp_pricelist = []
                    st.rerun()
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    if st.session_state.manual_success:
        st.success(f"✅ {st.session_state.manual_success}")
        st.session_state.manual_success = False

# ================================================
# TAB 2 : UPLOAD EXCEL
# ================================================

with tab2:
    st.subheader("📤 Upload File Excel")

    with st.expander("ℹ️ Format file Excel data customer & pricelist"):
        st.write("""
        **Format 1: Customer saja**
        - Kolom: `Nama`
        
        **Format 2: Customer + Pricelist**
        - Kolom: `Nama`, `Barang`, `Harga`
        - Jika ada pricelist, setiap baris = 1 customer + 1 barang + 1 harga
        - Customer yang sama bisa muncul di banyak baris dengan barang berbeda
        """)

    uploaded_file = st.file_uploader(
        "Pilih file Excel",
        type=["xlsx"],
        help="Upload file Excel dengan format yang sesuai"
    )

    if uploaded_file is not None:
        try:
            df_raw = pd.read_excel(uploaded_file, header=None)

            # Deteksi header
            EXPECTED_COLS = ["nama"]
            header_row_index = None

            for i, row in df_raw.iterrows():
                row_str = row.astype(str).str.upper()
                if all(any(col.upper() in cell for cell in row_str) for col in EXPECTED_COLS):
                    header_row_index = i
                    break

            if header_row_index is None:
                st.error("❌ Header kolom 'Nama' tidak ditemukan")
                st.stop()

            df = pd.read_excel(uploaded_file, header=header_row_index)
            df.columns = [str(col).strip().replace("'", "") for col in df.columns]

            target_cols = {
                "NAMA": "Nama",
                "BARANG": "Barang",
                "HARGA": "Harga"
            }

            available_cols = []
            rename_map = {}
            
            for col in df.columns:
                col_upper = col.upper()
                if col_upper in target_cols:
                    standard_name = target_cols[col_upper]
                    available_cols.append(col)
                    rename_map[col] = standard_name

            if not any(rename_map[c] == "Nama" for c in available_cols):
                st.error("❌ Kolom 'Nama' hilang setelah pemrosesan.")
                st.stop()

            df = df[available_cols].rename(columns=rename_map)
            df = df.dropna(how="all")
            df = new_database.clean_excel_apostrophe(df)

            # Normalize nama customer
            df["Nama"] = df["Nama"].apply(new_database.normalize_customer_name)

            has_pricelist = "Barang" in df.columns and "Harga" in df.columns

            st.success("✅ Data berhasil dibersihkan!")
            st.subheader("📋 Preview Data")
            st.dataframe(df.head(10), use_container_width=True)
            st.info(f"Total baris: {len(df)} | Mode: {'Customer + Pricelist' if has_pricelist else 'Customer Saja'}")

            if st.button("💾 Simpan", type="primary", use_container_width=True, key="btn_simpan_excel"):
                success_count = 0
                error_count = 0
                errors = []

                with st.spinner("Mengupload data ke database..."):
                    if has_pricelist:
                        # Mode: Customer + Pricelist
                        for idx, row in df.iterrows():
                            try:
                                nama = row.get("Nama")
                                barang = row.get("Barang")
                                harga = row.get("Harga")
                                
                                if pd.isna(nama) or pd.isna(barang) or pd.isna(harga):
                                    error_count += 1
                                    errors.append(f"Baris {idx+1}: Data tidak lengkap")
                                    continue
                                
                                # Insert/get customer
                                if not new_database.check_customer_available(nama):
                                    new_database.insert_customer(nama)
                                
                                id_customer = new_database.get_customer_id(nama)
                                id_barang = new_database.get_barang_id(barang)
                                
                                if id_barang is None:
                                    error_count += 1
                                    errors.append(f"Baris {idx+1}: Barang '{barang}' tidak ditemukan")
                                    continue
                                
                                if new_database.upsert_customer_pricelist(id_customer, id_barang, int(harga)):
                                    success_count += 1
                                else:
                                    error_count += 1
                                    errors.append(f"Baris {idx+1}: Gagal menyimpan pricelist")
                                    
                            except Exception as e:
                                error_count += 1
                                errors.append(f"Baris {idx+1}: {str(e)}")
                    else:
                        # Mode: Customer saja
                        for idx, row in df.iterrows():
                            try:
                                nama = row.get("Nama")
                                
                                if pd.isna(nama):
                                    error_count += 1
                                    errors.append(f"Baris {idx+1}: Nama kosong")
                                    continue
                                
                                if not new_database.check_customer_available(nama):
                                    success, message = new_database.insert_customer(nama)
                                    if success:
                                        success_count += 1
                                    else:
                                        error_count += 1
                                        errors.append(f"Baris {idx+1}: {message}")
                                else:
                                    error_count += 1
                                    errors.append(f"Baris {idx+1}: Customer '{nama}' sudah ada")
                                    
                            except Exception as e:
                                error_count += 1
                                errors.append(f"Baris {idx+1}: {str(e)}")
                
                st.session_state.upload_success = {
                    "success": success_count,
                    "error": error_count,
                    "errors": errors
                }
                st.rerun()

        except Exception as e:
            st.error(f"❌ Error membaca file: {str(e)}")

    if st.session_state.upload_success:
        result = st.session_state.upload_success

        if result["success"] > 0:
            st.success(f"✅ Berhasil mengupload {result['success']} baris data")

        if result["error"] > 0:
            st.warning(f"⚠️ {result['error']} baris gagal diupload")

            with st.expander("Lihat detail error"):
                for err in result["errors"][:20]:
                    st.error(err)

                if len(result["errors"]) > 20:
                    st.info(f"... dan {len(result['errors']) - 20} error lainnya")

        st.session_state.upload_success = None

# ================================================
# TAB 3 : DAFTAR CUSTOMER
# ================================================

with tab3:
    st.subheader("👥 Daftar Customer")

    with st.expander("ℹ️ Info edit & hapus customer"):
        st.write("""
        - Double klik pada sel untuk mengedit nama customer.
        - Pilih baris dan tekan logo sampah pada bagian atas tabel atau tombol delete di keyboard untuk menghapus.
        
        ⚠️ Menghapus customer akan menghapus seluruh pricelist customer tersebut.
        """)
    
    # Filter
    data_customer = new_database.get_all_data_customer(columns="nama")
    customer_options = ["Semua"] + data_customer["nama"].tolist()
    
    search_customer = st.selectbox(
        "🔍 Customer",
        options=customer_options,
        index=0,
        key="filter_customer"
    )

    try:
        # Ambil data customer
        df_customers = new_database.get_all_data_customer()

        if df_customers.empty:
            st.info("Belum ada data customer")
            st.stop()

        # Apply filter
        if search_customer != "Semua":
            df_customers = df_customers[
                df_customers["nama"].str.contains(search_customer, case=False, na=False)
            ]

        if df_customers.empty:
            st.warning("⚠️ Tidak ada customer sesuai filter")
            st.stop()

        # Download button
        # st.download_button(
        #     label="⬇️ Download Data Customer",
        #     data=df_customers.to_csv(index=False),
        #     file_name="customer.csv",
        #     mime="text/csv",
        #     use_container_width=True
        # )

        st.info(f"Total: {len(df_customers)} customer")
        
        column_config = {
            "id": None,  # Hide ID column
            "nama": st.column_config.TextColumn(
                "Nama Customer",
                required=True,
                width="large"
            )
        }

        edited_df = st.data_editor(
            df_customers,
            column_config=column_config,
            disabled=["id"],
            num_rows="dynamic",  # Allow deletion
            use_container_width=True,
            key="customer_editor",
            hide_index=True
        )

        # Button untuk save changes
        if st.button("💾 Simpan Perubahan", type="primary", key="btn_save_customer"):
            changes = st.session_state["customer_editor"]
            
            try:
                with st.spinner("Menyimpan perubahan..."):
                    
                    # 1️⃣ HAPUS DATA
                    if changes["deleted_rows"]:
                        for index in changes["deleted_rows"]:
                            id_to_delete = int(df_customers.iloc[index]['id'])
                            new_database.delete_customer(id_to_delete)
                    
                    # 2️⃣ EDIT DATA
                    if changes["edited_rows"]:
                        for index, new_values in changes["edited_rows"].items():
                            id_customer = int(df_customers.iloc[index]["id"])
                            new_nama = new_values.get("nama")
                            
                            if new_nama:
                                new_database.update_customer(id_customer, new_nama)
                    
                    # 3️⃣ TAMBAH DATA (jika ada)
                    if changes["added_rows"]:
                        for new_row in changes["added_rows"]:
                            nama = new_row.get("nama", "").strip()
                            if nama and not new_database.check_customer_available(nama):
                                new_database.insert_customer(nama)
                
                st.session_state.edit_success = True
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Gagal menyimpan: {str(e)}")

        if st.session_state.edit_success:
            st.success("✅ Perubahan berhasil disimpan!")
            st.session_state.edit_success = False

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

# ================================================
# TAB 4 : DAFTAR PRICELIST
# ================================================

with tab4:
    st.subheader("💰 Daftar Pricelist")
    
    with st.expander("ℹ️ Info edit & hapus pricelist"):
        st.write("""
        - Double klik pada sel harga untuk mengedit.
        - Pilih baris dan tekan logo sampah pada bagian atas tabel atau tombol delete di keyboard untuk menghapus.
        """)
    
    # Filter
    col_filter1, col_filter2 = st.columns(2)
    
    with col_filter1:
        data_customer = new_database.get_all_data_customer(columns="nama")
        customer_options = ["Semua"] + data_customer["nama"].tolist()
        
        search_customer = st.selectbox(
            "🔍 Customer",
            options=customer_options,
            index=0,
            key="filter_customer_pricelist"
        )
    
    with col_filter2:
        data_barang = new_database.get_all_data_barang(columns="nama")
        barang_options = ["Semua"] + data_barang["nama"].tolist()

        search_barang = st.selectbox(
            "🔍 Barang",
            options=barang_options,
            index=0,
            key="filter_barang_pricelist"
        )
    
    try:
        # Ambil data pricelist
        df = new_database.get_customer_with_pricelist()

        if df.empty:
            st.info("Belum ada data pricelist")
            st.stop()

        # Apply filter
        if search_customer != "Semua":
            df = df[df["customer"] == search_customer]

        if search_barang != "Semua":
            df = df[df["barang"] == search_barang]

        if df.empty:
            st.warning("⚠️ Tidak ada data sesuai filter")
            st.stop()

        st.info(
            f"Menampilkan {len(df)} pricelist dari "
            f"{df['customer'].nunique()} customer"
        )

        # Prepare data untuk editing
        df_edit = df[["id_pricelist", "customer", "barang", "harga", "updated_at"]].copy()

        column_config = {
            "id_pricelist": None,  # Hide ID
            "customer": st.column_config.TextColumn(
                "Customer",
                disabled=True,
                width="medium"
            ),
            "barang": st.column_config.TextColumn(
                "Barang",
                disabled=True,
                width="medium"
            ),
            "harga": st.column_config.NumberColumn(
                "Harga",
                required=True,
                format="Rp %d",
                width="medium"
            ),
            "updated_at": st.column_config.DatetimeColumn(
                "Update Terakhir",
                disabled=True,
                format="DD/MM/YYYY",
                width="medium"
            )
        }

        edited_df = st.data_editor(
            df_edit,
            column_config=column_config,
            disabled=["id_pricelist", "customer", "barang", "updated_at"],
            num_rows="dynamic",  # Allow deletion
            use_container_width=True,
            key="pricelist_editor",
            hide_index=True
        )

        # Button untuk save changes
        if st.button("💾 Simpan Perubahan", type="primary", key="btn_save_pricelist"):
            changes = st.session_state["pricelist_editor"]
            
            try:
                with st.spinner("Menyimpan perubahan..."):
                    
                    # 1️⃣ HAPUS DATA
                    if changes["deleted_rows"]:
                        for index in changes["deleted_rows"]:
                            id_to_delete = int(df_edit.iloc[index]['id_pricelist'])
                            new_database.delete_customer_pricelist(id_to_delete)
                    
                    # 2️⃣ EDIT DATA
                    if changes["edited_rows"]:
                        for index, new_values in changes["edited_rows"].items():
                            id_pricelist = int(df_edit.iloc[index]["id_pricelist"])
                            new_harga = new_values.get("harga")
                            
                            if new_harga is not None:
                                new_database.update_customer_pricelist(id_pricelist, int(new_harga))
                
                st.session_state.edit_success = True
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Gagal menyimpan: {str(e)}")

        if st.session_state.edit_success:
            st.success("✅ Perubahan berhasil disimpan!")
            st.session_state.edit_success = False

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")