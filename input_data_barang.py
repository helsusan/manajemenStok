import streamlit as st
import pandas as pd
from datetime import datetime
import new_database

st.set_page_config(
    page_title="Data Barang",
    page_icon="",
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

tab1, tab2, tab3 = st.tabs(["📝 Input Manual", "📤 Upload Excel", "📋 Daftar Barang"])

# ================================================
# TAB 1 : INPUT MANUAL
# ================================================

with tab1:
    st.subheader("➕ Input Barang Baru")
    
    nama_barang_baru = st.text_input("Nama Barang", placeholder="Contoh: AQUA 600ML")
            
    if st.button("💾 Simpan", type="primary", use_container_width=True):
        if nama_barang_baru.strip() == "":
            st.error("❌ Nama barang tidak boleh kosong!")
        else:
            try:
                # Cek apakah barang sudah ada
                if new_database.check_barang_available(nama_barang_baru):
                    st.warning(f"⚠️ Barang '{nama_barang_baru}' sudah ada di database!")
                else:
                    new_database.insert_barang(nama_barang_baru)
                    st.success(f"✅ Barang '{nama_barang_baru}' berhasil ditambahkan!")
                    st.rerun()

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

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
            df = df.dropna(how="all")
            df = df[EXPECTED_COLS]

            df = new_database.clean_excel_apostrophe(df)

            st.success("✅ Data berhasil dibersihkan!")

            st.subheader("📋 Preview Data")
            st.dataframe(df.head(10), use_container_width=True)
            st.info(f"Total baris: {len(df)}")

            if st.button("💾 Simpan", type="primary", use_container_width=True):
                with st.spinner("Mengupload data ke database..."):
                    success_count, error_count, errors = (
                        new_database.insert_data_barang(df)
                    )

                if success_count > 0:
                    st.success(f"✅ Berhasil mengupload {success_count} baris data")

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
    st.subheader("📋 Daftar Barang")
    
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

            if st.button("💾 Simpan Perubahan", type="primary"):
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

                                    new_database.update_barang(
                                        int(row['id']),
                                        row['nama'],
                                        row['model_prediksi'],
                                        row['p'],
                                        row['d'],
                                        row['q']
                                    )

                            # 3️⃣ TAMBAH DATA
                            if changes["added_rows"]:
                                for new_row in changes["added_rows"]:
                                    nama = new_row.get("nama", "").strip()
                                    if nama:
                                        new_database.insert_barang_full(
                                            nama=nama,
                                            model_prediksi=new_row.get("model_prediksi", "Mean"),
                                            p=new_row.get("p"),
                                            d=new_row.get("d"),
                                            q=new_row.get("q")
                                        )

                        st.success("✅ Perubahan berhasil disimpan!")

                        # Bersihkan state
                        st.session_state.pop("delete_conflicts", None)
                        st.session_state.pop("pending_changes", None)

                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Gagal menyimpan: {str(e)}")
            
    except Exception as e:
        st.error(f"Error: {str(e)}")

# Footer
# st.markdown("---")
# st.markdown("""
#     <div style='text-align: center; color: #666; padding: 10px;'>
#         <small>📦 Sistem Kelola Data Barang | Developed with Streamlit</small>
#     </div>
# """, unsafe_allow_html=True)