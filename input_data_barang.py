import streamlit as st
import pandas as pd
from datetime import datetime
import new_database

st.set_page_config(
    page_title="Data Barang",
    page_icon="📦",
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

st.header("Data Barang")

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

tab1, tab2, tab3 = st.tabs(["📝 Input Manual", "📤 Upload Excel", "📋 Daftar Barang"])

current_tab = (
    "tab1" if tab1 else
    "tab2" if tab2 else
    "tab3"
)

if st.session_state.active_tab != current_tab:
    # reset semua notifikasi saat pindah tab
    st.session_state.manual_success = False
    st.session_state.upload_success = False
    st.session_state.edit_success = False
    st.session_state.active_tab = current_tab

# ================================================
# TAB 1 : INPUT MANUAL
# ================================================

with tab1:
    st.subheader("➕ Input Barang Baru")
    
    nama_barang_baru = st.text_input("Nama Barang", placeholder="Contoh: AQUA 600ML")
            
    if st.button("💾 Simpan", type="primary", use_container_width=True, key="btn_simpan_manual"):
        if nama_barang_baru.strip() == "":
            st.error("❌ Nama barang tidak boleh kosong!")
        else:
            try:
                # Cek apakah barang sudah ada
                if new_database.check_barang_available(nama_barang_baru):
                    st.warning(f"⚠️ Barang '{nama_barang_baru}' sudah ada di database!")
                else:
                    success, message = new_database.insert_barang(nama_barang_baru.upper())

                    if success:
                        st.session_state.manual_success = message
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")

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

    with st.expander("ℹ️ Format file Excel data barang"):
        st.write("""
        - Kolom wajib: `Nama`
        """)

    uploaded_file = st.file_uploader(
        "Pilih file Excel",
        type=["xlsx"],
        help="Upload file Excel dengan format yang sesuai"
    )

    if uploaded_file is not None:
        try:
            df_raw = pd.read_excel(uploaded_file, header=None)

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

            # Bersihkan nama kolom
            df.columns = [str(col).strip().replace("'", "") for col in df.columns]

            target_cols = {
                "NAMA": "Nama",
                "MODEL_PREDIKSI": "model_prediksi",
                "P": "p", 
                "D": "d", 
                "Q": "q"
            }

            # Cari kolom mana saja yang tersedia di Excel
            available_cols = []
            rename_map = {}
            
            for col in df.columns:
                col_upper = col.upper()
                if col_upper in target_cols:
                    standard_name = target_cols[col_upper]
                    available_cols.append(col)
                    rename_map[col] = standard_name

            # Pastikan kolom Nama ada (seharusnya ada karena validasi header di atas)
            if not any(rename_map[c] == "Nama" for c in available_cols):
                 st.error("❌ Kolom 'Nama' hilang setelah pemrosesan.")
                 st.stop()

            # Ambil hanya kolom yang relevan dan rename ke standar
            df = df[available_cols].rename(columns=rename_map)

            # Paksa nama jadi uppercase
            if "Nama" in df.columns:
                df["Nama"] = df["Nama"].astype(str).str.upper()
            
            # Hapus baris yang kosong total
            df = df.dropna(how="all")

            df = new_database.clean_excel_apostrophe(df)

            st.success("✅ Data berhasil dibersihkan!")

            st.subheader("📋 Preview Data")
            st.dataframe(df.head(10), use_container_width=True)
            st.info(f"Total baris: {len(df)}")

            if st.button("💾 Simpan", type="primary", use_container_width=True, key="btn_simpan_excel"):
                success_count = 0
                error_count = 0
                errors = []

                with st.spinner("Mengupload data ke database..."):
                    for idx, row in df.iterrows():
                        try:
                            success, message = new_database.insert_barang(
                                nama=row.get("Nama"),
                                model_prediksi=row.get("model_prediksi", "Mean"),
                                p=row.get("p"),
                                d=row.get("d"),
                                q=row.get("q")
                            )

                            if success:
                                success_count += 1
                            else:
                                error_count += 1
                                errors.append(f"Baris {idx+1}: {message}")

                        except Exception as e:
                            error_count += 1
                            errors.append(f"Baris {idx+1}: {str(e)}")
                
                st.session_state.upload_success = {
                        "success": success_count,
                        "error": error_count,
                        "errors": errors
                    }
                st.rerun()

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
                            st.info(f"... dan {len(result["errors"]) - 20} error lainnya")

                # reset supaya tidak muncul terus
                st.session_state.upload_success = None

        except Exception as e:
            st.error(f"❌ Error membaca file: {str(e)}")

# ================================================
# TAB 3 : TABEL BARANG
# ================================================

with tab3:
    st.subheader("📋 Daftar Barang")
    with st.expander("ℹ️ Info edit & hapus barang"):
        st.write("""
        - Double klik pada sel untuk mengedit.
        - Pilih baris dan tekan logo sampah pada bagian atas tabel atau tombol delete di keyboard untuk menghapus.
        
        ⚠️ Menghapus data barang akan menghapus seluruh data penjualan, prediksi, stok, dan rekomendasi stok untuk barang tersebut.
        """)
    
    try:
        df_barang = new_database.get_all_data_barang()

        if not df_barang.empty:
            df_barang = df_barang.sort_values("nama").reset_index(drop=True)

            column_config = {
                "id": None,
                "nama": st.column_config.TextColumn(
                    "Nama Barang", required=True
                ),
                "model_prediksi": st.column_config.SelectboxColumn(
                    "Model", options=["ARIMA", "Mean"], required=True
                ),
                "p": st.column_config.NumberColumn("p"),
                "d": st.column_config.NumberColumn("d"),
                "q": st.column_config.NumberColumn("q"),
            }

            edited_df = st.data_editor(
                df_barang,
                column_config=column_config,
                disabled=["id"],
                num_rows="dynamic",
                use_container_width=True,
                key="barang_editor",
                hide_index=True
            )

            if st.button("💾 Simpan Perubahan", type="primary", key="btn_simpan_edit_barang"):
                changes = st.session_state["barang_editor"]

                conflicts = []
                if changes["deleted_rows"]:
                    for index in changes["deleted_rows"]:
                        row = df_barang.iloc[index]
                        related = new_database.check_related_data(row["id"])
                        if related:
                            conflicts.append({
                                "nama": row["nama"],
                                "related": related
                            })

                if conflicts:
                    st.session_state["delete_conflicts"] = conflicts
                    st.session_state["pending_changes"] = changes
                    changes = st.session_state.get("pending_changes", st.session_state["barang_editor"])
                    st.rerun()
                else:
                    try:
                        with st.spinner("Menyimpan perubahan..."):

                            # 1️⃣ HAPUS DATA
                            if changes["deleted_rows"]:
                                for index in changes["deleted_rows"]:
                                    id_to_delete = int(df_barang.iloc[index]['id'])
                                    new_database.delete_barang(id_to_delete)

                            # 2️⃣ EDIT DATA
                            if changes["edited_rows"]:
                                for index, new_values in changes["edited_rows"].items():
                                    row = df_barang.iloc[index].to_dict()
                                    row.update(new_values)

                                    # Bersihkan nilai NaN menjadi None agar tidak error di MySQL
                                    p_val = row.get('p')
                                    d_val = row.get('d')
                                    q_val = row.get('q')

                                    # Helper sederhana untuk ubah NaN jadi None
                                    def clean_nan(val):
                                        if pd.isna(val) or val == "":
                                            return None
                                        return val

                                    new_database.update_barang(
                                        int(row['id']),
                                        str(row['nama']).upper(), # UPDATED: Force Uppercase saat edit
                                        row['model_prediksi'],
                                        clean_nan(p_val), # UPDATED: Bersihkan NaN
                                        clean_nan(d_val), # UPDATED: Bersihkan NaN
                                        clean_nan(q_val)  # UPDATED: Bersihkan NaN
                                    )

                            # 3️⃣ TAMBAH DATA
                            if changes["added_rows"]:
                                for new_row in changes["added_rows"]:
                                    nama = new_row.get("nama", "")

                                    if not nama:
                                        continue  # skip baris kosong

                                    # Normalisasi nama
                                    nama = nama.strip().upper()

                                    # Validasi duplikasi
                                    if new_database.check_barang_available(nama):
                                        raise Exception(f"Barang '{nama}' sudah ada di database")

                                    if nama and not new_database.check_barang_available(nama):
                                        new_database.insert_barang(
                                            nama=nama,
                                            model_prediksi=new_row.get("model_prediksi", "Mean"),
                                            p=new_row.get("p"),
                                            d=new_row.get("d"),
                                            q=new_row.get("q")
                                        )

                        st.session_state.edit_success = True

                        # Bersihkan state
                        st.session_state.pop("delete_conflicts", None)
                        st.session_state.pop("pending_changes", None)

                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Gagal menyimpan: {str(e)}")

            if st.session_state.edit_success:
                st.success("✅ Perubahan berhasil disimpan!")
                # st.toast("Perubahan berhasil disimpan!", icon="✅")
                st.session_state.edit_success = False
            
    except Exception as e:
        st.error(f"Error: {str(e)}")

# Footer
# st.markdown("---")
# st.markdown("""
#     <div style='text-align: center; color: #666; padding: 10px;'>
#         <small>📦 Sistem Kelola Data Barang | Developed with Streamlit</small>
#     </div>
# """, unsafe_allow_html=True)