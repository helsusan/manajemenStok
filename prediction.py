import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from scipy.signal import savgol_filter
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import warnings
warnings.filterwarnings('ignore')
import database

def get_months_in_range(start_date, end_date):
    if not isinstance(start_date, datetime):
        start_date = datetime.combine(start_date, datetime.min.time())
    if not isinstance(end_date, datetime):
        end_date = datetime.combine(end_date, datetime.min.time())
    
    dates = []
    current = start_date.replace(day=1)
    end = end_date.replace(day=1)
    
    while current <= end:
        dates.append(current.date())
        current += relativedelta(months=1)
    
    return dates

def check_prediksi_range(id_barang, start_date, end_date):
    # Parse string ke datetime jika perlu
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    
    required_dates = get_months_in_range(start_date, end_date)
    
    df_prediksi = database.get_data_prediksi(
        id_barang, 
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d')
    )
    
    # Cek bulan mana yang belum ada
    missing_months = []
    existing_months = []
    
    for date in required_dates:
        date_normalized = pd.Timestamp(date.strftime('%Y-%m-01'))
        if date_normalized not in df_prediksi.index:
            missing_months.append(date)
        else:
            existing_months.append(date)
    
    return {
        'exists': len(missing_months) == 0,
        'missing_months': missing_months,
        'existing_months': existing_months,
        'missing_count': len(missing_months),
        'existing_count': len(existing_months),
        'required_count': len(required_dates)
    }

def prediksi_arima(id_barang, p, d, q, target_dates):
    """
    Prediksi menggunakan ARIMA untuk range tanggal tertentu
    
    Args:
        id_barang: ID barang
        p, d, q: Order ARIMA
        target_dates: List of date objects untuk prediksi
    """
    sales = database.get_all_data_penjualan(id_barang)
    sales.index.name = None
    sales['kuantitas'] = sales['kuantitas'].fillna(0)
    
    if len(sales) < 12:
        raise ValueError(f"Data tidak cukup untuk prediksi ARIMA. Minimal 12 bulan, tersedia {len(sales)} bulan")
    
    ori_sales = sales.copy()

    print("\nPREDIKSI ARIMA - DATA SALES")
    print(f"Total data: {len(sales)} bulan")
    print("=" * 60)
    
    # Smoothing dengan Savitzky-Golay filter
    if len(sales) >= 5:
        window_size = min(5, len(sales) if len(sales) % 2 == 1 else len(sales)-1)
        sales['kuantitas'] = savgol_filter(sales['kuantitas'], window_size, 2)

    model = ARIMA(sales['kuantitas'], order=(p,d,q))
    result = model.fit()

    # Hitung berapa bulan dari data terakhir ke target pertama
    last_sales_date = sales.index[-1]
    if not isinstance(last_sales_date, datetime):
        last_sales_date = datetime.combine(last_sales_date, datetime.min.time())
    
    first_target = target_dates[0]
    if not isinstance(first_target, datetime):
        first_target = datetime.combine(first_target, datetime.min.time())
    
    months_ahead = (first_target.year - last_sales_date.year) * 12 + (first_target.month - last_sales_date.month)
    
    # Forecast sampai bulan terakhir target
    total_steps = months_ahead + len(target_dates) - 1
    forecast = result.forecast(steps=total_steps)
    
    mean_residual = (ori_sales['kuantitas'] - sales['kuantitas']).mean()
    forecast_values = forecast + mean_residual
    forecast_values = np.maximum(forecast_values, 0)
    
    # Ambil hanya nilai untuk target_dates
    forecast_for_targets = forecast_values[months_ahead-1:months_ahead-1+len(target_dates)]

    result_df = pd.DataFrame({
        'tanggal': target_dates,
        'kuantitas': forecast_for_targets.values
    })

    print("HASIL PREDIKSI ARIMA")
    print(result_df)
    print("=" * 60)

    return result_df

def prediksi_mean(id_barang, target_dates):
    """
    Prediksi menggunakan Mean untuk range tanggal tertentu
    
    Args:
        id_barang: ID barang
        target_dates: List of date objects untuk prediksi
    """
    combined_data = database.get_last_12_data_penjualan(id_barang)
    combined_data['kuantitas'] = combined_data['kuantitas'].fillna(0)
    
    predictions = []
    for i, target_date in enumerate(target_dates):
        # Hitung rata-rata dari 12 data terakhir
        window_data = combined_data['kuantitas'].tail(12).fillna(0)
        mean_value = window_data.mean()
        
        if pd.isna(mean_value):
            mean_value = predictions[-1] if predictions else 0
        
        predictions.append(mean_value)
        
        # Tambahkan prediksi ini ke combined_data untuk iterasi berikutnya
        new_row = pd.DataFrame({
            'kuantitas': [mean_value]
        }, index=[target_date])
        combined_data = pd.concat([combined_data, new_row])

    result = pd.DataFrame({
        'tanggal': target_dates,
        'kuantitas': predictions
    })

    print("HASIL PREDIKSI MEAN")
    print(result)
    print("=" * 60)

    return result

def generate_prediksi_range(info_barang, start_month, end_month):
    id_barang = info_barang[0]
    nama_barang = info_barang[1]
    model_prediksi = info_barang[2]
    p = int(info_barang[3]) if pd.notna(info_barang[3]) else None
    d = int(info_barang[4]) if pd.notna(info_barang[4]) else None
    q = int(info_barang[5]) if pd.notna(info_barang[5]) else None

    # Dapatkan list bulan yang akan diprediksi
    target_dates = get_months_in_range(start_month, end_month)
    
    try:
        # ==== MODEL ARIMA ====
        if model_prediksi == 'ARIMA':
            if p is None or d is None or q is None:
                raise ValueError("Order ARIMA (p, d, q) harus disediakan")
            
            result = prediksi_arima(id_barang, p, d, q, target_dates)
            used_model = 'ARIMA'

        # ==== MODEL MEAN ====
        elif model_prediksi == 'Mean':
            result = prediksi_mean(id_barang, target_dates)
            used_model = 'MEAN'

        # ==== MODEL TIDAK DITEMUKAN ====
        else:
            raise ValueError("Model prediksi tidak dikenali (harus 'ARIMA' atau 'Mean')")

        return {
            'status': 'generated',
            'message': f"Prediksi berhasil di-generate untuk {len(result)} bulan (Model: {used_model})",
            'data': result,
            'info': f"{len(result)} bulan prediksi berhasil disimpan"
        }

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}",
            'data': None,
            'info': None
        }

def generate_prediksi(info_barang, base_date=None):
    """
    Generate prediksi OFFICIAL untuk 1 bulan ke depan (DISIMPAN ke DB)
    Digunakan untuk proses akhir bulan
    
    Args:
        info_barang: Tuple dari database.get_data_barang()
        base_date: Tanggal referensi (default: datetime.now())
    
    Returns:
        dict dengan status dan data prediksi
    """
    id_barang = info_barang[0]
    nama_barang = info_barang[1]
    model_prediksi = info_barang[2]
    p = int(info_barang[3]) if pd.notna(info_barang[3]) else None
    d = int(info_barang[4]) if pd.notna(info_barang[4]) else None
    q = int(info_barang[5]) if pd.notna(info_barang[5]) else None

    # Dapatkan list bulan yang akan diprediksi
    target_dates = get_months_in_range(start_month, end_month)

    try:
        # Generate untuk 1 BULAN ke depan saja
        if model_prediksi == 'ARIMA':
            if p is None or d is None or q is None:
                raise ValueError("Order ARIMA (p, d, q) harus disediakan")
            
            result = prediksi_arima(id_barang, p, d, q, target_dates)
            used_model = 'ARIMA'
                    
        elif model_prediksi == 'Mean':
            result = prediksi_mean(id_barang, target_dates)
            used_model = 'MEAN'

        else:
            raise ValueError(f"Model prediksi tidak ditemukan")
        
        # SIMPAN ke database
        for idx, row in result.iterrows():
            database.insert_hasil_prediksi(
                id_barang=id_barang,
                tanggal=row['tanggal'],
                kuantitas=round(row['kuantitas'], 2)
            )

        return {
            'status': 'success',
            'message': f"✓ Prediksi official berhasil (Model: {used_model})",
            'data': result,
            'model': used_model
        }

    except Exception as e:
        return {
            'status': 'error',
            'message': f"✗ Error: {str(e)}",
            'data': None
        }

def process_end_of_month():
    """
    Proses akhir bulan:
    1. Generate prediksi 1 bulan ke depan untuk semua barang
    2. Hitung safety stock & reorder point
    3. Simpan rekomendasi stok
    
    Returns:
        dict dengan summary hasil proses
    """
    
    results = {
        'prediksi_success': [],
        'prediksi_failed': [],
        'rekomendasi_success': [],
        'rekomendasi_failed': []
    }
    
    # 1. Generate prediksi untuk semua barang
    barang_list = database.get_all_nama_barang()
    
    for idx, row in barang_list.iterrows():
        nama = row['nama']
        info_barang = database.get_data_barang(nama)
        
        try:
            result = generate_prediksi(info_barang)
            if result['status'] == 'success':
                results['prediksi_success'].append(nama)
            else:
                results['prediksi_failed'].append((nama, result['message']))
        except Exception as e:
            results['prediksi_failed'].append((nama, str(e)))
    
    # 2. Hitung safety stock & reorder point
    # (logic dari dashboard_stock.py)
    # ... kode safety stock calculation ...
    
    return results