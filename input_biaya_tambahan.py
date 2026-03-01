import streamlit as st
import pandas as pd
from datetime import datetime
import new_database
import io

st.set_page_config(page_title="Biaya Tambahan", page_icon="💸", layout="wide")
st.header("Biaya Tambahan")

tab1, tab2 = st.tabs(["📝 Input Manual", "📋 Daftar Biaya Tambahan"])

# ================= TAB 1: INPUT MANUAL =================
with tab1:
    st.subheader("➕ Input Biaya Tambahan")
    
    # with st.form("form_biaya_tambahan"):
    col1, col2 = st.columns(2)
    
    with col1:
        nama_biaya = st.text_input(
            "Nama / Keterangan Biaya", 
            placeholder="Contoh: Beli Token Listrik, Gaji Karyawan, dll."
        )
        tanggal_biaya = st.date_input(
            "Tanggal", 
            value=datetime.now()
        )
        
    with col2:
        jumlah_biaya = st.number_input(
            "Jumlah (Rp)", 
            min_value=0.0, 
            step=1000.0,
            format="%.0f"
        )

    st.markdown("---")
    submit_btn = st.button("💾 Simpan Biaya", type="primary", use_container_width=True)
    
    if submit_btn:
        if not nama_biaya or nama_biaya.strip() == "":
            st.error("⚠️ Nama / Keterangan biaya wajib diisi!")
        elif jumlah_biaya <= 0:
            st.error("⚠️ Jumlah biaya harus lebih dari Rp 0!")
        else:
            with st.spinner("Menyimpan data..."):
                success, msg = new_database.insert_biaya_tambahan(nama_biaya.title(), tanggal_biaya, jumlah_biaya)
                if success:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ Gagal menyimpan: {msg}")

# ================= TAB 2: DAFTAR BIAYA TAMBAHAN =================
with tab2:
    st.subheader("📋 Daftar Biaya Tambahan")
    
    # Filter rentang tanggal
    # col_filter1, col_filter2 = st.columns(2)
    # with col_filter1:
    #     start_d = st.date_input("Dari Tanggal", value=datetime(datetime.now().year, datetime.now().month, 1), key="start_d_biaya")
    # with col_filter2:
    #     end_d = st.date_input("Sampai Tanggal", value=datetime.now(), key="end_d_biaya")

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
        
    df_biaya = new_database.get_all_biaya_tambahan(start_date, end_date)
    
    if not df_biaya.empty:
        # Format kolom untuk tampilan
        df_display = df_biaya.copy()
        df_display['tanggal'] = pd.to_datetime(df_display['tanggal']).dt.strftime('%d %b %Y')
        df_display['jumlah'] = df_display['jumlah'].astype(float)
        
        # Total
        total_biaya = df_biaya['jumlah'].sum()
        st.info(f"**Total Biaya Tambahan pada periode ini:** Rp {total_biaya:,.0f}".replace(",", "."))

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_display.drop(columns=['id'], errors='ignore').to_excel(writer, index=False, sheet_name='Biaya Tambahan')

        tanggal_download = datetime.now().strftime("%d-%m-%Y")
        
        st.download_button(
            label="📥 Download Biaya Tambahan (Excel)",
            data=output.getvalue(),
            file_name=f"Biaya Tambahan_{tanggal_download}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        # Tambahkan kolom checkbox untuk menghapus
        df_display.insert(0, "Hapus", False)
        
        edited_df = st.data_editor(
            df_display,
            column_config={
                "Hapus": st.column_config.CheckboxColumn("Pilih", help="Centang untuk menghapus data"),
                "id": None, # Sembunyikan ID
                "nama": st.column_config.TextColumn("Nama / Keterangan Biaya"),
                "tanggal": st.column_config.TextColumn("Tanggal"),
                "jumlah": st.column_config.NumberColumn(
                    "Jumlah Biaya", 
                    help="Klik angka untuk mengedit jumlah biaya",
                    min_value=0.0,
                    step=1000.0,
                    format="Rp %d"
                ),
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Deteksi jika ada perubahan pada kolom 'jumlah'
        diff_mask = edited_df['jumlah'] != df_display['jumlah']
        changed_rows = edited_df[diff_mask]
        
        # Deteksi data yang dipilih untuk dihapus
        to_delete = edited_df[edited_df['Hapus'] == True]
        
        # Tampilkan tombol aksi berdampingan
        col_action1, col_action2 = st.columns(2)
        
        with col_action1:
            if not to_delete.empty:
                st.warning(f"⚠️ Anda akan menghapus {len(to_delete)} data biaya tambahan.")
                if st.button("🗑️ Hapus Data Terpilih", type="primary"):
                    success_count = 0
                    for idx, row in to_delete.iterrows():
                        res = new_database.delete_biaya_tambahan(row['id'])
                        if res: 
                            success_count += 1
                    
                    st.success(f"✅ {success_count} data berhasil dihapus.")
                    st.rerun()
                    
        with col_action2:
            if not changed_rows.empty:
                st.info(f"✏️ Ada {len(changed_rows)} data yang jumlahnya diubah.")
                if st.button("💾 Simpan Perubahan Jumlah", type="primary"):
                    success_count = 0
                    for idx, row in changed_rows.iterrows():
                        res = new_database.update_biaya_tambahan(row['id'], row['jumlah'])
                        if res:
                            success_count += 1
                    
                    st.success(f"✅ {success_count} data berhasil diupdate.")
                    st.rerun()
    else:
        st.info("Tidak ada data biaya tambahan pada periode ini.")