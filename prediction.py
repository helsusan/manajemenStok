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
    sales = database.get_all_data_penjualan(id_barang)
    sales.index.name = None
    sales['kuantitas'] = sales['kuantitas'].fillna(0)
    
    if len(sales) < 12:
        raise ValueError(f"Data tidak cukup untuk prediksi ARIMA. Minimal 12 bulan, tersedia {len(sales)} bulan")
    
    ori_sales = sales.copy()

    print("\nPREDIKSI ARIMA - DATA SALES")
    print(f"Total data: {len(sales)} bulan")
    print("=" * 60)

    sales['kuantitas'] = savgol_filter(sales['kuantitas'], 5, 2)

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
    combined_data = database.get_last_12_data_penjualan(id_barang)
    combined_data['kuantitas'] = combined_data['kuantitas'].fillna(0)
    
    predictions = []
    for i, target_date in enumerate(target_dates):
        window_data = combined_data['kuantitas'].tail(12).fillna(0)
        mean_value = window_data.mean()
        
        if pd.isna(mean_value):
            mean_value = predictions[-1] if predictions else 0
        
        predictions.append(mean_value)
        
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

    target_dates = get_months_in_range(start_month, end_month)
    
    try:
        if model_prediksi == 'ARIMA':
            if p is None or d is None or q is None:
                raise ValueError("Order ARIMA (p, d, q) harus disediakan")
            
            result = prediksi_arima(id_barang, p, d, q, target_dates)
            used_model = 'ARIMA'

        elif model_prediksi == 'Mean':
            result = prediksi_mean(id_barang, target_dates)
            used_model = 'MEAN'

        else:
            raise ValueError("Model prediksi tidak dikenali")

        return {
            'status': 'generated',
            'message': f"Prediksi berhasil di-generate untuk {len(result)} bulan",
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

def generate_all_prediksi():
    base_date = datetime.now()

    all_barang = database.get_all_data_barang()
    
    next_month = (base_date.replace(day=1) + pd.DateOffset(months=1)).date()
    target_dates = [next_month]

    for _, row in all_barang.iterrows():
        id_barang = row['id']
        nama_barang = row['nama']
        model = row['model_prediksi']
        p, d, q = row['p'], row['d'], row['q']

        print(f"🔹 Barang: {nama_barang} (Model: {model})")

        df_penjualan = database.get_all_data_penjualan(id_barang)

        try:
            database.cek_data_penjualan_lengkap(df_penjualan, base_date)
        except ValueError as e:
            print(f"❌ ERROR: {nama_barang} -> {str(e)}")
            return None 

        if model == 'ARIMA' and pd.notna(p) and pd.notna(d) and pd.notna(q):
            result = prediksi_arima(id_barang, int(p), int(d), int(q), target_dates)
        elif model == 'Mean':
            result = prediksi_mean(id_barang, target_dates)

        for _, row_pred in result.iterrows():
            tanggal = row_pred['tanggal']
            qty = row_pred['kuantitas']
            database.insert_hasil_prediksi(id_barang, tanggal, qty)
            print(f"   ✅ Disimpan prediksi {tanggal}: {qty:.2f}")

        print("   ------------------------------------------")

    print("\n🎯 Semua prediksi berhasil diproses!")

# def generate_prediksi_official(info_barang, base_date=None):
#     """
#     Generate prediksi OFFICIAL untuk 1 bulan ke depan (DISIMPAN ke DB)
#     Digunakan untuk proses akhir bulan
    
#     Args:
#         info_barang: Tuple dari database.get_data_barang()
#         base_date: Tanggal referensi (default: datetime.now())
    
#     Returns:
#         dict dengan status dan data prediksi
#     """
#     id_barang = info_barang[0]
#     nama_barang = info_barang[1]
#     model_prediksi = info_barang[2]
#     p = int(info_barang[3]) if pd.notna(info_barang[3]) else None
#     d = int(info_barang[4]) if pd.notna(info_barang[4]) else None
#     q = int(info_barang[5]) if pd.notna(info_barang[5]) else None

#     try:
#         # Generate untuk 1 BULAN ke depan saja
#         if model_prediksi == 'ARIMA':
#             if p is None or d is None or q is None:
#                 raise ValueError("Order ARIMA (p, d, q) harus disediakan")
            
#             try:
#                 # Ubah get_next_3_months jadi ambil 1 bulan saja
#                 if base_date is None:
#                     base_date = datetime.now()
                
#                 next_month = base_date.replace(day=1) + relativedelta(months=1)
#                 future_dates = [next_month]
                
#                 sales = database.get_all_data_penjualan(id_barang)
#                 sales.index.name = None
#                 ori_sales = sales.copy()
                
#                 if len(sales) >= 5:
#                     window_size = min(5, len(sales) if len(sales) % 2 == 1 else len(sales)-1)
#                     sales['kuantitas'] = savgol_filter(sales['kuantitas'], window_size, 2)
                
#                 model = ARIMA(sales['kuantitas'], order=(p,d,q))
#                 result_model = model.fit()
#                 forecast = result_model.forecast(steps=1)
#                 mean_residual = (ori_sales['kuantitas'] - sales['kuantitas']).mean()
#                 forecast_values = forecast + mean_residual
#                 forecast_values = np.maximum(forecast_values, 0)
                
#                 result = pd.DataFrame({
#                     'tanggal': future_dates,
#                     'kuantitas': forecast_values.values
#                 })
#                 used_model = 'ARIMA'
                
#             except ValueError as e:
#                 if "Data tidak cukup" in str(e):
#                     print(f"   ⚠ ARIMA gagal: {str(e)}")
#                     print(f"   🔄 Fallback ke model Mean...")
                    
#                     combined_data = database.get_last_12_data_penjualan(id_barang)
#                     mean_value = combined_data['kuantitas'].tail(12).mean()
                    
#                     if base_date is None:
#                         base_date = datetime.now()
#                     next_month = base_date.replace(day=1) + relativedelta(months=1)
                    
#                     result = pd.DataFrame({
#                         'tanggal': [next_month],
#                         'kuantitas': [mean_value]
#                     })
#                     used_model = 'MEAN (Fallback)'
#                 else:
#                     raise
                    
#         elif model_prediksi == 'Mean':
#             combined_data = database.get_last_12_data_penjualan(id_barang)
#             mean_value = combined_data['kuantitas'].tail(12).mean()
            
#             if base_date is None:
#                 base_date = datetime.now()
#             next_month = base_date.replace(day=1) + relativedelta(months=1)
            
#             result = pd.DataFrame({
#                 'tanggal': [next_month],
#                 'kuantitas': [mean_value]
#             })
#             used_model = 'MEAN'
#         else:
#             raise ValueError(f"Model prediksi tidak ditemukan")
        
#         # SIMPAN ke database
#         for idx, row in result.iterrows():
#             database.insert_hasil_prediksi(
#                 id_barang=id_barang,
#                 tanggal=row['tanggal'],
#                 kuantitas=round(row['kuantitas'], 2)
#             )

#         return {
#             'status': 'success',
#             'message': f"✓ Prediksi official berhasil (Model: {used_model})",
#             'data': result,
#             'model': used_model
#         }

#     except Exception as e:
#         return {
#             'status': 'error',
#             'message': f"✗ Error: {str(e)}",
#             'data': None
#         }


def generate_prediksi_temp(info_barang, start_month, end_month):

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
            
            try:
                result = prediksi_arima(id_barang, p, d, q, target_dates)
                used_model = 'ARIMA'
            except ValueError as e:
                if "Data tidak cukup" in str(e):
                    # Fallback ke Mean
                    result = prediksi_mean(id_barang, target_dates)
                    used_model = 'MEAN (Fallback)'
                else:
                    raise

        # ==== MODEL MEAN ====
        elif model_prediksi == 'Mean':
            result = prediksi_mean(id_barang, target_dates)
            used_model = 'MEAN'

        # ==== MODEL TIDAK DITEMUKAN ====
        else:
            raise ValueError("Model prediksi tidak dikenali (harus 'ARIMA' atau 'Mean')")

        # PENTING: TIDAK DISIMPAN KE DATABASE
        # Hanya return data untuk visualisasi
        
        return {
            'status': 'success',
            'message': f"Prediksi berhasil di-generate (Model: {used_model})",
            'data': result
        }

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}",
            'data': None
        }


def generate_prediksi_official(info_barang, base_date=None):
    id_barang = info_barang[0]
    nama_barang = info_barang[1]
    model_prediksi = info_barang[2]
    p = int(info_barang[3]) if pd.notna(info_barang[3]) else None
    d = int(info_barang[4]) if pd.notna(info_barang[4]) else None
    q = int(info_barang[5]) if pd.notna(info_barang[5]) else None

    if base_date is None:
        base_date = datetime.now()

    try:
        next_month = base_date.replace(day=1) + relativedelta(months=1)
        target_dates = [next_month.date()]
        
        if model_prediksi == 'ARIMA':
            if p is None or d is None or q is None:
                raise ValueError("Order ARIMA (p, d, q) harus disediakan")
            
            try:
                result = prediksi_arima(id_barang, p, d, q, target_dates)
                used_model = 'ARIMA'
                
            except ValueError as e:
                if "Data tidak cukup" in str(e):
                    result = prediksi_mean(id_barang, target_dates)
                    used_model = 'MEAN (Fallback)'
                else:
                    raise
                    
        elif model_prediksi == 'Mean':
            result = prediksi_mean(id_barang, target_dates)
            used_model = 'MEAN'
            
        else:
            raise ValueError(f"Model prediksi tidak ditemukan: {model_prediksi}")
        
        for idx, row in result.iterrows():
            database.insert_hasil_prediksi(
                id_barang=id_barang,
                tanggal=row['tanggal'],
                kuantitas=round(row['kuantitas'], 2)
            )

        return {
            'status': 'success',
            'message': f"Prediksi official berhasil (Model: {used_model})",
            'data': result,
            'model': used_model
        }

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error: {str(e)}",
            'data': None
        }

def process_end_of_month():    
    results = {
        'prediksi_success': [],
        'prediksi_failed': [],
        'rekomendasi_success': [],
        'rekomendasi_failed': []
    }
    
    barang_list = database.get_all_nama_barang()
    
    for idx, row in barang_list.iterrows():
        nama = row['nama']
        info_barang = database.get_data_barang(nama)

        if not info_barang:
            results['prediksi_failed'].append((nama, "Data barang tidak ditemukan"))
            continue

        id_barang = info_barang[0]
        
        # ===== GENERATE PREDIKSI BULAN DEPAN =====
        try:
            result = generate_prediksi_official(info_barang)
            if result['status'] == 'success':
                results['prediksi_success'].append(nama)
                hasil_prediksi = result['data']['kuantitas'].values[0]
            else:
                results['prediksi_failed'].append((nama, result['message']))
                continue
        except Exception as e:
            results['prediksi_failed'].append((nama, str(e)))
    
        # ===== HITUNG SAFETY STOCK & REORDER POINT =====
        try:
            barang_lead = database.get_barang_with_lead_time()
            lead_time_row = barang_lead[barang_lead['id'] == id_barang]
            
            if len(lead_time_row) == 0:
                max_lead_time = 10
                avg_lead_time = 7
            else:
                max_lead_time = lead_time_row['max_lead_time'].values[0]
                avg_lead_time = lead_time_row['avg_lead_time'].values[0]
            
            penjualan = database.get_all_data_penjualan(id_barang)
            
            if len(penjualan) == 0:
                results['rekomendasi_failed'].append((nama, "Tidak ada data penjualan"))
                continue
            
            # Hitung average & max daily usage
            avg_monthly_sales = penjualan['kuantitas'].mean()
            avg_daily_usage = avg_monthly_sales / 30
            
            max_monthly_sales = penjualan['kuantitas'].max()
            max_daily_usage = max_monthly_sales / 30
            
            safety_stock = (max_daily_usage * max_lead_time) - (avg_daily_usage * avg_lead_time)
            safety_stock = max(0, round(safety_stock, 2))
            
            reorder_point = (avg_daily_usage * avg_lead_time) + safety_stock
            reorder_point = round(reorder_point, 2)

            latest_stok_date = database.get_latest_stok_date()
            if latest_stok_date:
                stok_data = database.get_stok_by_date(latest_stok_date)
                stok_row = stok_data[stok_data['id'] == id_barang]
                stok_aktual = stok_row['total_stok'].values[0] if len(stok_row) > 0 else 0
            else:
                stok_aktual = 0
            
            saran_stok = reorder_point + hasil_prediksi - stok_aktual
            saran_stok = max(0, round(saran_stok, 2))

            # ===== SIMPAN REKOMENDASI STOK KE DATABASE =====
            database.insert_rekomendasi_stok(
                id_barang=id_barang,
                max_lead_time=max_lead_time,
                avg_lead_time=avg_lead_time,
                safety_stock=safety_stock,
                reorder_point=reorder_point,
                stok_aktual=stok_aktual,
                hasil_prediksi=hasil_prediksi,
                saran_stok=saran_stok
            )
            
            results['rekomendasi_success'].append(nama)
        except Exception as e:
            results['rekomendasi_failed'].append((nama, str(e)))

    return results