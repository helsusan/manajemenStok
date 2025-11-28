import streamlit as st
import pandas as pd
from datetime import datetime
import database

st.set_page_config(page_title="Data Barang", page_icon="🧰", layout="wide")

st.header("➕ Tambah Barang Baru")
 
with st.form("form_tambah_barang"):
    nama_barang_baru = st.text_input("Nama Barang *", placeholder="Contoh: AQUA 600ML")
            
    submit_barang = st.form_submit_button("💾 Simpan Barang", type="primary", use_container_width=True)
            
    if submit_barang:
        if nama_barang_baru.strip() == "":
            st.error("❌ Nama barang tidak boleh kosong!")
        else:
            try:
                conn = database.get_connection()
                cursor = conn.cursor()
                        
                # Cek apakah barang sudah ada
                cursor.execute("SELECT id FROM barang WHERE nama = %s", (nama_barang_baru,))
                existing = cursor.fetchone()
                        
                if existing:
                    st.warning(f"⚠️ Barang '{nama_barang_baru}' sudah ada di database!")
                else:
                    # Insert barang baru
                    query = "INSERT INTO barang (nama, model_prediksi) VALUES (%s, %s)"
                    cursor.execute(query, (nama_barang_baru, "Mean"))
                    conn.commit()
                    st.success(f"✅ Barang '{nama_barang_baru}' berhasil ditambahkan!")
                        
                cursor.close()
                conn.close()
                        
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")






# Divider
st.divider()
    
# Section untuk melihat data barang yang tersedia
st.subheader("🔍 Daftar Barang")
st.caption("Double klik pada sel untuk mengedit. Pilih baris dan tekan tombol delete di keyboard untuk menghapus.")
st.info("⚠️ Menghapus data barang akan menghapus seluruh data penjualan, prediksi, stok, dan rekomendasi stok untuk barang tersebut.")
    
# --- FUNGSI PROSES SIMPAN (Dipakai ulang) ---
def process_save_changes(changes, df_barang):
    try:
        with st.spinner("Menyimpan perubahan..."):
            # 1. Hapus Data (Deleted Rows)
            if changes["deleted_rows"]:
                for index in changes["deleted_rows"]:
                    id_to_delete = int(df_barang.iloc[index]['id'])  # ← TAMBAHKAN int() DI SINI
                    # Langsung delete (Cascade di DB akan mengurus anak-anaknya)
                    database.delete_barang(id_to_delete)

            # 2. Edit Data (Edited Rows)
            if changes["edited_rows"]:
                for index, new_values in changes["edited_rows"].items():
                    row = df_barang.iloc[index].to_dict()
                    row.update(new_values)
                    database.update_barang(
                        int(row['id']),  # ← TAMBAHKAN int() DI SINI JUGA
                        row['nama'], 
                        row['model_prediksi'], 
                        row['p'], 
                        row['d'], 
                        row['q']
                    )
            
            # 3. Tambah Data (Added Rows)
            if changes["added_rows"]:
                for new_row in changes["added_rows"]:
                    nama = new_row.get('nama', '')
                    if nama:
                        cursor = database.get_connection().cursor()
                        query = "INSERT INTO barang (nama, model_prediksi, p, d, q) VALUES (%s, %s, %s, %s, %s)"
                        p = new_row.get('p', None)
                        d = new_row.get('d', None)
                        q = new_row.get('q', None)
                        model = new_row.get('model_prediksi', 'Mean')
                        cursor.execute(query, (nama, model, p, d, q))
                        cursor.connection.commit()
                        cursor.close()

        st.success("✅ Perubahan berhasil disimpan!")
        
        # Bersihkan state konfirmasi jika ada
        if "delete_conflicts" in st.session_state:
            del st.session_state["delete_conflicts"]
        if "pending_changes" in st.session_state:
            del st.session_state["pending_changes"]
            
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Gagal menyimpan: {str(e)}")


# --- MAIN LOGIC ---
try:
    df_barang = database.get_all_data_barang()
    
    if not df_barang.empty:
        # SORT ALFABETIS BERDASARKAN NAMA (ASCENDING)
        df_barang = df_barang.sort_values('nama', ascending=True).reset_index(drop=True)

        # Konfigurasi Kolom
        column_config = {
            # "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
            "id": None,
            "nama": st.column_config.TextColumn("Nama Barang", required=True, width="medium"),
            "model_prediksi": st.column_config.SelectboxColumn("Model", options=["ARIMA", "Mean"], width="small", required=True),
            "p": st.column_config.NumberColumn("p", width="small"),
            "d": st.column_config.NumberColumn("d", width="small"),
            "q": st.column_config.NumberColumn("q", width="small"),
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

        # Tombol Simpan
        if st.button("💾 Simpan Perubahan", type="primary"):
            changes = st.session_state["barang_editor"]
            
            # Cek Konflik Hapus
            conflicts = []
            if changes["deleted_rows"]:
                for index in changes["deleted_rows"]:
                    row = df_barang.iloc[index]
                    id_barang = row['id']
                    nama_barang = row['nama']
                    
                    # Cek database
                    related = database.check_related_data(id_barang)
                    if related:
                        conflicts.append({
                            'nama': nama_barang,
                            'related': related
                        })
            
            if conflicts:
                # Jika ada konflik, JANGAN simpan dulu. Simpan state & minta konfirmasi.
                st.session_state["delete_conflicts"] = conflicts
                st.session_state["pending_changes"] = changes
                st.rerun()
            else:
                # Jika aman, langsung simpan
                process_save_changes(changes, df_barang)

        # --- TAMPILAN KONFIRMASI (Muncul jika ada konflik) ---
        if "delete_conflicts" in st.session_state and st.session_state["delete_conflicts"]:
            st.warning("⚠️ PERINGATAN: Barang yang akan dihapus memiliki data terkait!")
            st.write("Barang berikut memiliki history (Penjualan/Stok/dll). Menghapus barang ini akan **MENGHAPUS SELURUH DATA TERKAIT** secara otomatis (Cascade).")
            
            for item in st.session_state["delete_conflicts"]:
                # Format text: "Nama Barang: Penjualan (10), Stok (5)"
                details = ", ".join([f"{k} ({v})" for k,v in item['related'].items()])
                st.markdown(f"- **{item['nama']}**: {details}")
            
            st.write("Apakah Anda yakin ingin melanjutkan?")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                # Tombol Confirm
                if st.button("🔥 Ya, Hapus Semuanya", type="primary"):
                    changes = st.session_state.get("pending_changes")
                    if changes:
                        process_save_changes(changes, df_barang)
            
            with col2:
                # Tombol Cancel
                if st.button("❌ Batal"):
                    del st.session_state["delete_conflicts"]
                    del st.session_state["pending_changes"]
                    st.info("Perubahan dibatalkan.")
                    st.rerun()

    else:
        st.info("Belum ada data barang di database.")
            
except Exception as e:
    st.error(f"Error loading data: {str(e)}")