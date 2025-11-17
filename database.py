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










# ================================================
# DATA BARANG
# ================================================

def get_all_nama_barang():
    conn = get_connection()
    query = "SELECT nama FROM barang"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

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
    
def get_all_data_barang():
    conn = get_connection()
    query = "SELECT * FROM barang"
    df = pd.read_sql(query, conn)
    conn.close()
    return df










# ================================================
# DATA PENJUALAN
# ================================================

def insert_data_penjualan(df):
    conn = get_connection()
    cursor = conn.cursor()
    success_count = 0
    errors = []

    try:
        conn.start_transaction()
        
        for index, row in df.iterrows():
            nama_barang = row.get('Keterangan Barang')
            
            if pd.isna(nama_barang):
                raise Exception(f"Baris {index + 2}: Nama barang kosong")
            
            id_barang = get_data_barang(nama_barang)

            if id_barang:
                id_barang = id_barang[0]
            
            if not id_barang:
                raise Exception(f"Baris {index + 2}: Barang '{nama_barang}' tidak ditemukan di database")
            
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
        
        conn.commit()
        cursor.close()
        conn.close()
        return success_count, 0, []
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        errors.append(str(e))
        return 0, df.shape[0], errors

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
        
        first_date = df.index.min()
        last_date = df.index.max()

        # Buat range bulanan lengkap dari awal sampai akhir
        all_months = pd.date_range(start=first_date, end=last_date, freq='MS')

        # Isi bulan kosong dengan 0
        df = df.reindex(all_months, fill_value=0)
        df.index = df.index.date
        
    return df

def get_data_penjualan_with_start_date(id_barang, start_date):
    conn = get_connection()

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

def get_last_12_data_penjualan(id_barang):
    """
    Ambil 12 bulan data penjualan terakhir untuk training model.
    
    LOGIC PENTING:
    - Kalau bulan HISTORIS kosong (dalam range data real) → ISI DENGAN 0 (memang ga ada sales)
    - Kalau bulan FUTURE kosong (di luar range data real) → BOLEH fill dengan prediksi
    
    Returns:
        DataFrame dengan 12 bulan data (termasuk prediksi untuk future months)
    """
    # Tentukan range tanggal (12 bulan ke belakang dari bulan sekarang)
    end_date = datetime.now().replace(day=1).date()
    start_date = end_date - timedelta(days=365)

    # Ambil data penjualan (HANYA yang ada di database)
    penjualan = get_data_penjualan_with_start_date(id_barang, start_date.strftime('%Y-%m-%d'))

    # Buat range bulan lengkap untuk 12 bulan
    date_range = [d.date() for d in pd.date_range(start=start_date, end=end_date, freq='MS')]
    
    # Inisialisasi dengan 0 (asumsi awal: semua bulan tidak ada penjualan)
    combined = pd.DataFrame(index=date_range, columns=['kuantitas'])
    combined['kuantitas'] = 0
    combined.index.name = 'tanggal'
    
    # === STEP 1: ISI DENGAN DATA PENJUALAN REAL ===
    if len(penjualan) > 0:
        if 'tanggal' in penjualan.columns:
            penjualan = penjualan.set_index('tanggal')
        penjualan = penjualan.sort_index()
        
        # Update HANYA untuk tanggal yang ada di data penjualan
        for idx in penjualan.index:
            if idx in combined.index:
                combined.loc[idx, 'kuantitas'] = penjualan.loc[idx, 'kuantitas']
    
    # === STEP 2: TENTUKAN RANGE DATA HISTORIS ===
    # Ambil SEMUA data penjualan untuk cari range real
    all_penjualan = get_all_data_penjualan(id_barang)
    
    if len(all_penjualan) > 0:
        # Tanggal penjualan PERTAMA dan TERAKHIR yang ada di database
        first_sales_date = all_penjualan.index.min()
        last_sales_date = all_penjualan.index.max()
        
        print(f"\n📊 RANGE DATA PENJUALAN REAL:")
        print(f"   Pertama: {first_sales_date}")
        print(f"   Terakhir: {last_sales_date}")
        
        # === STEP 3: FILL DENGAN PREDIKSI HANYA UNTUK FUTURE MONTHS ===
        # Bulan yang perlu di-fill = bulan yang masih 0 DAN di luar range historis
        future_months = []
        for idx in combined.index:
            # Kalau masih 0 DAN tanggalnya > last_sales_date = ini future month
            if combined.loc[idx, 'kuantitas'] == 0 and idx > last_sales_date:
                future_months.append(idx)
        
        print(f"\n🔮 FUTURE MONTHS yang perlu prediksi: {len(future_months)}")
        if len(future_months) > 0:
            print(f"   Range: {future_months[0]} - {future_months[-1]}")
        
        # Fill future months dengan prediksi (kalau ada)
        if len(future_months) > 0:
            prediksi = get_data_prediksi(
                id_barang, 
                future_months[0].strftime('%Y-%m-%d'),
                future_months[-1].strftime('%Y-%m-%d')
            )
            
            if len(prediksi) > 0:
                if 'tanggal' in prediksi.columns:
                    prediksi = prediksi.set_index('tanggal')
                prediksi = prediksi.sort_index()
                
                # Update hanya untuk future months yang ada prediksinya
                for idx in prediksi.index:
                    if idx in future_months:
                        combined.loc[idx, 'kuantitas'] = prediksi.loc[idx, 'kuantitas']
                        print(f"   ✓ Fill {idx} dengan prediksi: {prediksi.loc[idx, 'kuantitas']:.2f}")
        
        # === STEP 4: BULAN HISTORIS YANG KOSONG TETAP 0 ===
        # (sudah otomatis karena kita inisialisasi dengan 0)
        historical_zeros = []
        for idx in combined.index:
            # Kalau masih 0 DAN dalam range historis (first <= idx <= last)
            if combined.loc[idx, 'kuantitas'] == 0 and first_sales_date <= idx <= last_sales_date:
                historical_zeros.append(idx)
        
        if len(historical_zeros) > 0:
            print(f"\n⚠️  BULAN HISTORIS dengan 0 penjualan: {len(historical_zeros)}")
            for zero_month in historical_zeros:
                print(f"   • {zero_month}: TETAP 0 (memang tidak ada penjualan)")
    
    else:
        print("⚠️  Tidak ada data penjualan historis")
    
    # Ambil 12 bulan terakhir saja
    combined = combined.iloc[-12:]
    combined['kuantitas'] = pd.to_numeric(combined['kuantitas'], errors='coerce').fillna(0)
    
    print("\n" + "=" * 60)
    print("FINAL: LAST 12 DATA PENJUALAN")
    print(combined)
    print("=" * 60)

    return combined

def cek_data_penjualan_lengkap(df, base_date=None):
    """
    Mengecek apakah data penjualan memiliki bulan terakhir yang sesuai.
    Misal: kalau base_date = 2025-12-01, maka data terakhir minimal harus ada sampai 2025-11-01.
    """
    if base_date is None:
        base_date = datetime.now().date()
        
    if df.empty:
        raise ValueError("Data penjualan kosong, tidak bisa melakukan prediksi.")
        
    # Ambil tanggal terakhir dari data penjualan
    last_date = df.index.max()
    
    # Hitung tanggal minimal yang seharusnya ada
    expected_last_date = (base_date.replace(day=1) - pd.DateOffset(months=1)).date()
    
    if last_date < expected_last_date:
        raise ValueError(
            f"Data penjualan belum lengkap. Data terakhir: {last_date}, "
            f"seharusnya minimal ada data sampai {expected_last_date}."
        )
    
    print(f"✅ Data penjualan lengkap sampai {last_date}")
    return True

def get_latest_penjualan_date():
    conn = get_connection()
    query = "SELECT MAX(tgl_faktur) as latest FROM penjualan"
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query)
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result['latest'] if result['latest'] else None

def check_data_penjualan_bulan_ini():
    """
    Cek apakah data penjualan bulan ini sudah ada
    Returns:
        dict: {
            'exists': bool,
            'last_date': date,
            'current_month': date,
            'message': str
        }
    """
    from datetime import datetime
    
    latest_date = get_latest_penjualan_date()
    current_month = datetime.now().replace(day=1).date()
    
    if not latest_date:
        return {
            'exists': False,
            'last_date': None,
            'current_month': current_month,
            'message': 'Belum ada data penjualan di database'
        }
    
    # Convert ke date jika datetime
    if hasattr(latest_date, 'date'):
        latest_date = latest_date.date()
    
    latest_month = latest_date.replace(day=1)
    
    if latest_month < current_month:
        return {
            'exists': False,
            'last_date': latest_date,
            'current_month': current_month,
            'message': f'Data penjualan terakhir: {latest_date.strftime("%d %b %Y")}. Belum ada data untuk bulan {current_month.strftime("%B %Y")}'
        }
    
    return {
        'exists': True,
        'last_date': latest_date,
        'current_month': current_month,
        'message': f'Data penjualan bulan ini sudah ada (terakhir: {latest_date.strftime("%d %b %Y")})'
    }











# ================================================
# DATA PREDIKSI
# ================================================

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
        df['tanggal'] = df['tanggal'].dt.date
        df = df.set_index('tanggal')
        
    return df

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










# ================================================
# DATA STOK
# ================================================

def insert_data_stok(df, tanggal):
    conn = get_connection()
    cursor = conn.cursor()
    success_count = 0
    errors = []

    try:
        conn.start_transaction()
        
        for index, row in df.iterrows():
            nama_barang = row.get('Deskripsi Barang')
            
            if pd.isna(nama_barang):
                raise Exception(f"Baris {index + 2}: Nama barang kosong")
            
            barang_info = get_data_barang(nama_barang)
            
            if not barang_info:
                raise Exception(f"Baris {index + 2}: Barang '{nama_barang}' tidak ditemukan di database")
            
            id_barang = barang_info[0]
            gudang_bjm = row.get('BANJARMASIN', 0)
            gudang_sby = row.get('CENTRE', 0)

            if pd.isna(gudang_bjm):
                gudang_bjm = 0
            if pd.isna(gudang_sby):
                gudang_sby = 0
            
            if isinstance(tanggal, str):
                tanggal_str = tanggal
            else:
                tanggal_str = tanggal.strftime('%Y-%m-%d')
            
            # Check if data exists
            check_query = """
            SELECT id FROM stok 
            WHERE tanggal = %s AND id_barang = %s
            """
            cursor.execute(check_query, (tanggal_str, id_barang))
            existing = cursor.fetchone()
            
            if existing:
                # Update
                update_query = """
                UPDATE stok 
                SET gudang_bjm = %s, gudang_sby = %s
                WHERE tanggal = %s AND id_barang = %s
                """
                cursor.execute(update_query, (gudang_bjm, gudang_sby, tanggal_str, id_barang))
            else:
                # Insert
                insert_query = """
                INSERT INTO stok (tanggal, id_barang, gudang_bjm, gudang_sby)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(insert_query, (tanggal_str, id_barang, gudang_bjm, gudang_sby))
            
            success_count += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        return success_count, 0, []
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        errors.append(str(e))
        return 0, df.shape[0], errors

def get_all_data_stok():
    conn = get_connection()
    query = """
    SELECT s.tanggal, b.nama, s.gudang_bjm, s.gudang_sby,
           (s.gudang_bjm + s.gudang_sby) as total_stok
    FROM stok s
    JOIN barang b ON s.id_barang = b.id
    ORDER BY s.tanggal DESC, b.nama
    """
    df = pd.read_sql(query, conn)
    conn.close()
    
    if len(df) > 0:
        df['tanggal'] = pd.to_datetime(df['tanggal'])
    
    return df

def get_latest_stok_date():
    conn = get_connection()
    query = "SELECT MAX(tanggal) as latest FROM stok"
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query)
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result['latest'] if result['latest'] else None

def get_stok_by_date(tanggal):
    conn = get_connection()
    query = """
    SELECT b.id, b.nama, s.gudang_bjm, s.gudang_sby,
           (s.gudang_bjm + s.gudang_sby) as total_stok
    FROM barang b
    LEFT JOIN stok s ON b.id = s.id_barang AND s.tanggal = %s
    ORDER BY b.nama
    """
    df = pd.read_sql(query, conn, params=(tanggal,))
    conn.close()
    return df

def update_lead_time(id_barang, max_lead_time, avg_lead_time):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if exists
    check_query = "SELECT id FROM rekomendasi_stok WHERE id_barang = %s"
    cursor.execute(check_query, (id_barang,))
    existing = cursor.fetchone()
    
    if existing:
        update_query = """
        UPDATE rekomendasi_stok 
        SET max_lead_time = %s, avg_lead_time = %s
        WHERE id_barang = %s
        """
        cursor.execute(update_query, (max_lead_time, avg_lead_time, id_barang))
    else:
        insert_query = """
        INSERT INTO rekomendasi_stok (id_barang, max_lead_time, avg_lead_time)
        VALUES (%s, %s)
        """
        cursor.execute(insert_query, (id_barang, max_lead_time, avg_lead_time))
    
    conn.commit()
    cursor.close()
    conn.close()

def check_data_stok_hari_ini():
    latest_date = get_latest_stok_date()
    today = datetime.now().date()
    
    if not latest_date:
        return {
            'exists': False,
            'last_date': None,
            'today': today,
            'message': 'Belum ada data stok di database'
        }
    
    # Convert ke date jika datetime
    if hasattr(latest_date, 'date'):
        latest_date = latest_date.date()
    
    if latest_date < today:
        return {
            'exists': False,
            'last_date': latest_date,
            'today': today,
            'message': f'Data stok terakhir: {latest_date.strftime("%d %b %Y")}. Belum ada data untuk hari ini ({today.strftime("%d %b %Y")})'
        }
    
    return {
        'exists': True,
        'last_date': latest_date,
        'today': today,
        'message': f'Data stok hari ini sudah ada ({latest_date.strftime("%d %b %Y")})'
    }










# ================================================
# DATA REKOMENDASI STOK
# ================================================

def get_rekomendasi_stok():
    conn = get_connection()
    query = """
    SELECT r.*, b.nama
    FROM rekomendasi_stok r
    JOIN barang b ON r.id_barang = b.id
    ORDER BY b.nama
    """
    df = pd.read_sql(query, conn)
    conn.close()
    
    if len(df) > 0 and 'tgl_update' in df.columns:
        df['tgl_update'] = pd.to_datetime(df['tgl_update'])
    
    return df

def get_latest_rekomendasi_date():
    conn = get_connection()
    query = "SELECT MAX(tgl_update) as latest FROM rekomendasi_stok"
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query)
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result['latest'] if result['latest'] else None

def insert_rekomendasi_stok(id_barang, max_lead_time, avg_lead_time, safety_stock, reorder_point, 
                            stok_aktual, hasil_prediksi, saran_stok):
    conn = get_connection()
    cursor = conn.cursor()
    
    tgl_update = datetime.now().strftime('%Y-%m-%d')
    
    # Check if exists
    check_query = "SELECT id FROM rekomendasi_stok WHERE id_barang = %s"
    cursor.execute(check_query, (id_barang,))
    existing = cursor.fetchone()
    
    if existing:
        update_query = """
        UPDATE rekomendasi_stok 
        SET max_lead_time = %s, avg_lead_time = %s, safety_stock = %s, reorder_point = %s,
            tgl_update = %s, stok_aktual = %s, hasil_prediksi = %s, saran_stok = %s
        WHERE id_barang = %s
        """
        cursor.execute(update_query, (max_lead_time, avg_lead_time, safety_stock, reorder_point, 
                                     tgl_update, stok_aktual, hasil_prediksi, saran_stok, id_barang))
    else:
        insert_query = """
        INSERT INTO rekomendasi_stok 
        (id_barang, max_lead_time, avg_lead_time, safety_stock, reorder_point, tgl_update, 
         stok_aktual, hasil_prediksi, saran_stok)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (id_barang, max_lead_time, avg_lead_time, safety_stock, reorder_point,
                                     tgl_update, stok_aktual, hasil_prediksi, saran_stok))
    
    conn.commit()
    cursor.close()
    conn.close()

def get_barang_with_lead_time():
    conn = get_connection()
    query = """
    SELECT b.id, b.nama, 
           COALESCE(r.max_lead_time, 7) as max_lead_time,
           COALESCE(r.avg_lead_time, 7) as avg_lead_time
    FROM barang b
    LEFT JOIN rekomendasi_stok r ON b.id = r.id_barang
    ORDER BY b.nama
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def analyze_gudang_distribution():
    """
    Analisis distribusi stok antara Gudang SBY vs BJM.
    
    Deteksi kasus:
    1. Stok total cukup, tapi masih banyak di SBY (perlu transfer)
    2. Stok BJM sudah mencapai reorder point (urgent)
    3. Stok BJM aman, tapi SBY menumpuk (warning)
    
    Returns:
        dict: {
            'need_transfer': list,      # Barang yang perlu transfer SBY -> BJM
            'bjm_critical': list,        # Stok BJM kritis (perlu reorder/transfer urgent)
            'sby_stockpile': list,       # Stok SBY menumpuk (perlu dimonitor)
            'balanced': list             # Distribusi stok sudah baik
        }
    """
    from datetime import datetime
    
    results = {
        'need_transfer': [],
        'bjm_critical': [],
        'sby_stockpile': [],
        'balanced': []
    }
    
    # Ambil data stok terbaru
    latest_stok_date = get_latest_stok_date()
    if not latest_stok_date:
        return results
    
    stok_data = get_stok_by_date(latest_stok_date)
    
    # Ambil data rekomendasi (untuk reorder point)
    rekomendasi = get_rekomendasi_stok()
    
    if len(rekomendasi) == 0:
        return results
    
    # Merge data
    merged = pd.merge(
        stok_data,
        rekomendasi[['id_barang', 'reorder_point', 'safety_stock', 'hasil_prediksi']],
        left_on='id',
        right_on='id_barang',
        how='inner'
    )
    
    # Analisis setiap barang
    for idx, row in merged.iterrows():
        nama = row['nama']
        bjm = row['gudang_bjm'] if not pd.isna(row['gudang_bjm']) else 0
        sby = row['gudang_sby'] if not pd.isna(row['gudang_sby']) else 0
        total = row['total_stok']
        reorder_point = row['reorder_point']
        safety_stock = row['safety_stock']
        prediksi = row['hasil_prediksi']
        
        # Hitung ideal distribution (BJM harus punya minimal reorder point)
        ideal_bjm = reorder_point
        
        # === CASE 1: BJM KRITIS (< reorder point) ===
        if bjm <= reorder_point:
            # Cek apakah ada stok di SBY yang bisa di-transfer
            if sby > 0:
                # Ada stok di SBY, HARUS transfer!
                transfer_needed = min(sby, reorder_point - bjm)
                urgency = 'URGENT' if bjm <= safety_stock else 'HIGH'
                
                results['need_transfer'].append({
                    'nama': nama,
                    'gudang_bjm': bjm,
                    'gudang_sby': sby,
                    'total_stok': total,
                    'reorder_point': reorder_point,
                    'transfer_needed': round(transfer_needed, 2),
                    'urgency': urgency,
                    'reason': f'BJM kritis ({bjm:.0f} < {reorder_point:.0f}), tapi ada {sby:.0f} di SBY'
                })
                
                # Jika sangat kritis (< safety stock), masukkan juga ke bjm_critical
                if bjm <= safety_stock:
                    results['bjm_critical'].append({
                        'nama': nama,
                        'gudang_bjm': bjm,
                        'gudang_sby': sby,
                        'total_stok': total,
                        'reorder_point': reorder_point,
                        'safety_stock': safety_stock,
                        'gap': round(reorder_point - bjm, 2),
                        'reason': f'BJM sangat kritis! ({bjm:.0f} < safety stock {safety_stock:.0f})'
                    })
            else:
                # Tidak ada stok di SBY, benar-benar perlu order
                results['bjm_critical'].append({
                    'nama': nama,
                    'gudang_bjm': bjm,
                    'gudang_sby': sby,
                    'total_stok': total,
                    'reorder_point': reorder_point,
                    'safety_stock': safety_stock,
                    'gap': round(reorder_point - bjm, 2),
                    'reason': f'Tidak ada stok di SBY, perlu order! Gap: {(reorder_point - bjm):.0f} unit'
                })
        
        # === CASE 2: BJM AMAN, tapi SBY MENUMPUK ===
        elif bjm > reorder_point and sby > prediksi:
            # BJM sudah aman, tapi SBY punya stok > prediksi bulan depan
            # Ini warning untuk monitoring (mungkin tidak perlu transfer urgent)
            results['sby_stockpile'].append({
                'nama': nama,
                'gudang_bjm': bjm,
                'gudang_sby': sby,
                'total_stok': total,
                'reorder_point': reorder_point,
                'prediksi': prediksi,
                'reason': f'SBY menumpuk ({sby:.0f} > prediksi {prediksi:.0f}), BJM sudah aman'
            })
        
        # === CASE 3: DISTRIBUSI SEIMBANG ===
        else:
            results['balanced'].append({
                'nama': nama,
                'gudang_bjm': bjm,
                'gudang_sby': sby,
                'total_stok': total,
                'reorder_point': reorder_point
            })
    
    return results


def get_transfer_priority_list():
    """
    Generate daftar prioritas transfer dari SBY ke BJM.
    Diurutkan berdasarkan urgency.
    
    Returns:
        DataFrame dengan kolom: nama, bjm, sby, transfer_needed, urgency, reason
    """
    analysis = analyze_gudang_distribution()
    
    # Ambil data yang perlu transfer
    need_transfer = analysis['need_transfer']
    
    if len(need_transfer) == 0:
        return pd.DataFrame()
    
    # Convert ke DataFrame
    df = pd.DataFrame(need_transfer)
    
    # Sort berdasarkan urgency (URGENT > HIGH) dan gudang_bjm (ascending)
    urgency_order = {'URGENT': 0, 'HIGH': 1}
    df['urgency_rank'] = df['urgency'].map(urgency_order)
    df = df.sort_values(['urgency_rank', 'gudang_bjm'])
    df = df.drop('urgency_rank', axis=1)
    
    return df


def get_rekomendasi_stok_with_gudang():
    """
    Ambil data rekomendasi stok LENGKAP dengan info gudang.
    Termasuk breakdown BJM vs SBY.
    
    Returns:
        DataFrame dengan tambahan kolom: gudang_bjm, gudang_sby, distribution_status
    """
    # Ambil rekomendasi biasa
    rekomendasi = get_rekomendasi_stok()
    
    if len(rekomendasi) == 0:
        return rekomendasi
    
    # Ambil data stok terbaru
    latest_stok_date = get_latest_stok_date()
    if not latest_stok_date:
        return rekomendasi
    
    stok_data = get_stok_by_date(latest_stok_date)
    
    # Merge
    merged = pd.merge(
        rekomendasi,
        stok_data[['id', 'gudang_bjm', 'gudang_sby']],
        left_on='id_barang',
        right_on='id',
        how='left'
    )
    
    # Tambahkan status distribusi
    def get_distribution_status(row):
        bjm = row['gudang_bjm'] if not pd.isna(row['gudang_bjm']) else 0
        sby = row['gudang_sby'] if not pd.isna(row['gudang_sby']) else 0
        reorder = row['reorder_point']
        
        if bjm <= reorder and sby > 0:
            return '⚠️ PERLU TRANSFER'
        elif bjm <= reorder:
            return '🔴 KRITIS'
        elif sby > row['hasil_prediksi']:
            return '📦 SBY MENUMPUK'
        else:
            return '✅ SEIMBANG'
    
    merged['distribution_status'] = merged.apply(get_distribution_status, axis=1)
    
    # Update stok_aktual dengan breakdown
    merged['stok_aktual'] = merged['gudang_bjm'] + merged['gudang_sby']
    
    return merged












import pandas as pd

def clean_excel_apostrophe(df):
    """
    Membersihkan apostrof (') di awal string pada seluruh cell
    dan juga pada nama kolom DataFrame.
    """
    
    def clean_value(value):
        # Handle NaN/None
        if pd.isna(value):
            return None
        
        # Convert ke string dan strip
        str_value = str(value).strip()
        
        # Remove leading apostrophe
        if str_value.startswith("'"):
            str_value = str_value[1:]
        
        return str_value if str_value else None

    # Copy df agar tidak ubah yang asli
    df = df.copy()

    # --- Bersihkan Nama Kolom ---
    df.columns = [
        col[1:] if isinstance(col, str) and col.startswith("'") else col
        for col in df.columns
    ]

    # --- Bersihkan Isi Cell ---
    for col in df.columns:
        df[col] = df[col].apply(clean_value)

    return df
