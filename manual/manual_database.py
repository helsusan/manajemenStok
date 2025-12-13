import mysql.connector
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="manajemen_stok"
    )

def run_query(query):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

def get_data_barang(nama_barang):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM barang WHERE nama = %s"
        cursor.execute(query, (nama_barang,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return result
        else:
            return None
    except Exception as e:
        st.error(f"Error mencari barang: {e}")
        return None
    
def insert_data_penjualan(df):
    """
    Insert data penjualan dari DataFrame ke database
    """
    conn = get_connection()
    cursor = conn.cursor()
    success_count = 0
    errors = []

    try:
        # Mulai transaction
        conn.start_transaction()
        
        for index, row in df.iterrows():
            # Ambil nama barang dari CSV
            nama_barang = row.get('Keterangan Barang')
            
            if pd.isna(nama_barang):
                raise Exception(f"Baris {index + 2}: Nama barang kosong")
            
            # Cari id_barang dari tabel barang
            id_barang = get_data_barang(nama_barang)
            
            if not id_barang:
                raise Exception(f"Baris {index + 2}: Barang '{nama_barang}' tidak ditemukan di database")
            
            # Ambil data lainnya dari CSV
            no_faktur = row.get('No. Faktur')
            tgl_faktur = row.get('Tgl Faktur')
            nama_pelanggan = row.get('Nama Pelanggan')
            kuantitas = row.get('Kuantitas')
            jumlah = row.get('Jumlah')
            
            # Validasi data wajib
            if pd.isna(no_faktur) or pd.isna(tgl_faktur) or pd.isna(kuantitas):
                raise Exception(f"Baris {index + 2}: Data wajib (no_faktur, tgl_faktur, atau kuantitas) kosong")
            
            # Konversi tanggal jika perlu
            if isinstance(tgl_faktur, str):
                try:
                    tgl_faktur = pd.to_datetime(tgl_faktur).strftime('%Y-%m-%d')
                except:
                    raise Exception(f"Baris {index + 2}: Format tanggal tidak valid")
            
            # Query insert
            query = """
            INSERT INTO penjualan (no_faktur, tgl_faktur, nama_pelanggan, id_barang, kuantitas, jumlah)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            values = (
                str(no_faktur),
                tgl_faktur,
                str(nama_pelanggan) if not pd.isna(nama_pelanggan) else None,
                id_barang,
                int(kuantitas),
                float(jumlah) if not pd.isna(jumlah) else 0
            )
            
            cursor.execute(query, values)
            success_count += 1
        
        # Jika semua berhasil, commit transaction
        conn.commit()
        cursor.close()
        conn.close()
        return success_count, 0, []
        
    except Exception as e:
        # Jika ada error, rollback semua perubahan
        conn.rollback()
        cursor.close()
        conn.close()
        errors.append(str(e))
        return 0, df.shape[0], errors
    
def get_all_nama_barang():
    conn = get_connection()
    query = "SELECT nama FROM barang"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def get_all_data_penjualan(id_barang):
    conn = get_connection()

    query = """
    SELECT 
        DATE_FORMAT(tgl_faktur, '%Y-%m-01') AS tanggal,
        SUM(kuantitas) AS kuantitas
    FROM penjualan
    WHERE id_barang = %s
    GROUP BY DATE_FORMAT(tgl_faktur, '%Y-%m-01')
    ORDER BY tanggal;
    """

    df = pd.read_sql(query, conn, params=(id_barang,))
    conn.close()
        
    if len(df) > 0:
        df['tanggal'] = pd.to_datetime(df['tanggal'], errors='coerce')
        df = df.set_index('tanggal').sort_index()

        # Tentukan tanggal awal dan akhir dari data yang ada
        first_date = df.index.min()
        last_date = df.index.max()

        # Buat range bulanan lengkap dari awal sampai akhir
        all_months = pd.date_range(start=first_date, end=last_date, freq='MS')

        # Isi bulan kosong dengan 0
        df = df.reindex(all_months, fill_value=0)
        df.index = df.index.date
        
    return df

def get_data_penjualan_with_date_range(id_barang, start_date, end_date):
    conn = get_connection()

    query = """
    SELECT 
        DATE_FORMAT(tgl_faktur, '%Y-%m-01') AS tanggal,
        SUM(kuantitas) AS kuantitas
    FROM penjualan
    WHERE id_barang = %s
        AND tgl_faktur BETWEEN %s AND %s
    GROUP BY DATE_FORMAT(tgl_faktur, '%Y-%m-01')
    ORDER BY tanggal;
    """

    df = pd.read_sql(query, conn, params=(id_barang, start_date, end_date))
    conn.close()

    if len(df) > 0:
        df['tanggal'] = pd.to_datetime(df['tanggal'], errors='coerce')
        df['tanggal'] = df['tanggal'].dt.date
        df = df.set_index('tanggal')

    return df

def get_first_sales_date(id_barang):
    conn = get_connection()
    query = "SELECT MIN(tgl_faktur) AS first_date FROM penjualan WHERE id_barang = %s"
    df = pd.read_sql(query, conn, params=(id_barang,))
    conn.close()
    return df['first_date'].iloc[0]

def get_data_penjualan(id_barang, start_date=None):
    conn = get_connection()

    # 3 bulan terakhir dari tanggal saat ini
    start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')

    query = """
    SELECT 
        DATE_FORMAT(tgl_faktur, '%Y-%m-01') AS tanggal,
        SUM(kuantitas) AS kuantitas
    FROM penjualan
    WHERE id_barang = %s
        AND tgl_faktur >= %s
    GROUP BY DATE_FORMAT(tgl_faktur, '%Y-%m-01')
    ORDER BY tanggal;
    """

    df = pd.read_sql(query, conn, params=(id_barang, start_date))
    conn.close()
        
    if len(df) > 0:
        df['tanggal'] = pd.to_datetime(df['tanggal'], errors='coerce')
        df['tanggal'] = df['tanggal'].dt.date
        df = df.set_index('tanggal')
        
    return df

def get_data_prediksi(id_barang, start_date=None, end_date=None):
    conn = get_connection()
    query = "SELECT tanggal, kuantitas FROM prediksi WHERE id_barang = %s"

    params = [id_barang]
        
    if start_date:
        query += " AND tanggal >= %s"
        params.append(start_date)
        
    if end_date:
        query += " AND tanggal <= %s"
        params.append(end_date)
        
    query += " ORDER BY tanggal"

    df = pd.read_sql(query, conn, params=tuple(params))
    conn.close()
        
    if len(df) > 0:
        df['tanggal'] = pd.to_datetime(df['tanggal'], errors='coerce')
        # df['tanggal'] = df['tanggal'].dt.date
        df['tanggal'] = pd.to_datetime(df['tanggal']).dt.to_period('M').dt.to_timestamp()
        df = df.set_index('tanggal')
        
    return df

# def get_last_12_data_penjualan(id_barang):
#     # Tentukan range tanggal (12 bulan ke belakang dari bulan sekarang)
#     end_date = datetime.now().replace(day=1).date()
#     start_date = end_date - timedelta(days=365)

#     penjualan = get_data_penjualan(id_barang, start_date.strftime('%Y-%m-%d'))

#     # Buat range bulan lengkap
#     date_range = [d.date() for d in pd.date_range(start=start_date, end=end_date, freq='MS')]
#     combined = pd.DataFrame(index=date_range, columns=['kuantitas'])
#     combined.index.name = 'tanggal'
        
#     # Fill dengan data penjualan
#     if len(penjualan) > 0:
#         if 'tanggal' in penjualan.columns:
#             penjualan = penjualan.set_index('tanggal')
#         penjualan = penjualan.sort_index()
#         combined.update(penjualan)
        
#     # Fill missing values dengan data prediksi
#     missing_dates = combined[combined['kuantitas'].isna()].index
#     if len(missing_dates) > 0:
#             prediksi = get_data_prediksi(
#             id_barang, 
#             missing_dates.min().strftime('%Y-%m-%d'),
#             missing_dates.max().strftime('%Y-%m-%d')
#         )
#     if len(prediksi) > 0:
#         if 'tanggal' in prediksi.columns:
#             prediksi = prediksi.set_index('tanggal')
#         prediksi = prediksi.sort_index()
#         combined.update(prediksi)
        
#     # Ambil 12 bulan terakhir saja
#     combined = combined.iloc[-12:]
#     combined['kuantitas'] = pd.to_numeric(combined['kuantitas'], errors='coerce')
    
#     print("\nDATA PENJUALAN")
#     print(penjualan)
#     print("=" * 60)
#     print("DATA PREDIKSI")
#     print(prediksi)
#     print("=" * 60)
#     print("LAST 12 DATA PENJUALAN")
#     print(combined)
#     print("=" * 60)

#     return combined

def get_last_12_data_penjualan(id_barang):
    # Tentukan range tanggal (12 bulan ke belakang dari bulan sekarang)
    end_date = datetime.now().replace(day=1).date()
    start_date = end_date - timedelta(days=365)

    penjualan = get_data_penjualan(id_barang, start_date.strftime('%Y-%m-%d'))

    # Buat range bulan lengkap
    date_range = [d.date() for d in pd.date_range(start=start_date, end=end_date, freq='MS')]
    
    # FIX: Inisialisasi dengan 0, bukan NaN
    combined = pd.DataFrame(index=date_range, columns=['kuantitas'])
    combined['kuantitas'] = 0  # <-- INI YANG DITAMBAHKAN
    combined.index.name = 'tanggal'
        
    # Fill dengan data penjualan
    if len(penjualan) > 0:
        if 'tanggal' in penjualan.columns:
            penjualan = penjualan.set_index('tanggal')
        penjualan = penjualan.sort_index()
        
        # FIX: Update hanya untuk tanggal yang ada di penjualan
        for idx in penjualan.index:
            if idx in combined.index:
                combined.loc[idx, 'kuantitas'] = penjualan.loc[idx, 'kuantitas']
        
    # Fill missing values dengan data prediksi
    missing_dates = combined[combined['kuantitas'] == 0].index
    if len(missing_dates) > 0:
        prediksi = get_data_prediksi(
            id_barang, 
            missing_dates.min().strftime('%Y-%m-%d'),
            missing_dates.max().strftime('%Y-%m-%d')
        )
        
        if len(prediksi) > 0:
            if 'tanggal' in prediksi.columns:
                prediksi = prediksi.set_index('tanggal')
            prediksi = prediksi.sort_index()
            
            # FIX: Update hanya untuk tanggal yang ada di prediksi
            for idx in prediksi.index:
                if idx in combined.index and combined.loc[idx, 'kuantitas'] == 0:
                    combined.loc[idx, 'kuantitas'] = prediksi.loc[idx, 'kuantitas']
    
    # Ambil 12 bulan terakhir saja
    combined = combined.iloc[-12:]
    combined['kuantitas'] = pd.to_numeric(combined['kuantitas'], errors='coerce').fillna(0)
    
    print("\nDATA PENJUALAN")
    print(penjualan)
    print("=" * 60)
    print("DATA PREDIKSI")
    if len(missing_dates) > 0 and 'prediksi' in locals():
        print(prediksi)
    else:
        print("Tidak ada prediksi")
    print("=" * 60)
    print("LAST 12 DATA PENJUALAN")
    print(combined)
    print("=" * 60)

    return combined

def insert_hasil_prediksi(id_barang, tanggal, kuantitas):
    conn = get_connection()
    cursor = conn.cursor()

    # Check if prediction already exists
    check_query = """
    SELECT id FROM prediksi 
    WHERE id_barang = %s AND tanggal = %s
    """
    cursor.execute(check_query, (id_barang, tanggal))
    existing = cursor.fetchone()
        
    if existing:
        # Update existing prediction
        update_query = """
        UPDATE prediksi 
        SET kuantitas = %s
        WHERE id_barang = %s AND tanggal = %s
        """
        cursor.execute(update_query, (kuantitas, id_barang, tanggal))
    else:
        # Insert new prediction
        insert_query = """
        INSERT INTO prediksi (id_barang, tanggal, kuantitas)
        VALUES (%s, %s, %s)
        """
        cursor.execute(insert_query, (id_barang, tanggal, kuantitas))
        
    conn.commit()
    cursor.close()
    conn.close()

