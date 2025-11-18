import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from scipy.signal import savgol_filter
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import warnings
warnings.filterwarnings('ignore')
import database

def get_next_3_months(base_date=None):
    if base_date is None:
        base_date = datetime.now()
    
    if not isinstance(base_date, datetime):
        base_date = datetime.combine(base_date, datetime.min.time())
    
    next_month = base_date.replace(day=1) + relativedelta(months=1)

    dates = []
    for i in range(3):
        next_month = next_month + relativedelta(months=i)
        dates.append(pd.Timestamp(next_month.strftime("%Y-%m-01")))

    print("GET NEXT 3 MONTHS")
    print(f"Base date: {base_date.strftime('%Y-%m-%d')}")
    print(dates)
    print("=" * 60)

    return dates

def check_prediksi(id_barang, base_date=None):
    required_dates = get_next_3_months(base_date)
    start_date = required_dates[0].strftime('%Y-%m-%d')
    end_date = required_dates[2].strftime('%Y-%m-%d')

    df_prediksi = database.get_data_prediksi(id_barang, start_date, end_date)

    # Cek bulan mana yang belum ada
    missing_months = []
    for date in required_dates:
        date_normalized = pd.Timestamp(date.strftime('%Y-%m-01'))
        if date_normalized not in df_prediksi.index:
            missing_months.append(date)

    print("CHECK PREDIKSI")
    print("exists: ", len(missing_months) == 0)
    print("missing_months: ", missing_months)
    print("existing_data: ", df_prediksi)
    print("required_count: ", len(required_dates))
    print("existing_count: ", len(df_prediksi))
    print("=" * 60)
        
    return {
        'exists': len(missing_months) == 0,
        'missing_months': missing_months,
        'existing_data': df_prediksi,
        'required_count': len(required_dates),
        'existing_count': len(df_prediksi)
    }

def prediksi_arima(id_barang, p, d, q, base_date=None):
    first_sales_date = database.get_first_sales_date(id_barang)
    end_date = base_date.replace(day=1) + relativedelta(months=1) - relativedelta(days=1)

    sales = database.get_data_penjualan_with_date_range(
        id_barang=id_barang,
        start_date=first_sales_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )

    # sales = database.get_all_data_penjualan(id_barang)
    sales.index.name = None
    
    # FIX: Pastikan tidak ada NaN di sales
    sales['kuantitas'] = sales['kuantitas'].fillna(0)

    all_months = pd.date_range(
        start=sales.index.min(),
        end=end_date,
        freq='MS'
    )
    sales = sales.reindex(all_months, fill_value=0)
    sales.index.name = None
    
    # Periksa apakah data cukup
    # available_months = len(sales)
    
    # if available_months < min_data_months:
    #     # Coba lengkapi dengan data prediksi yang sudah ada
    #     print(f"   ⚠ Data penjualan hanya {available_months} bulan, mencoba melengkapi dengan data prediksi...")
        
    #     # Cari data prediksi sebelum base_date
    #     if base_date is None:
    #         base_date = datetime.now()
        
    #     # FIX: Pastikan base_date adalah datetime
    #     if not isinstance(base_date, datetime):
    #         base_date = datetime.combine(base_date, datetime.min.time())
        
    #     # Ambil prediksi hingga bulan base_date
    #     last_sales_date = sales.index[-1] if len(sales) > 0 else base_date - relativedelta(months=12)
        
    #     # FIX: Pastikan last_sales_date adalah datetime untuk operasi
    #     if isinstance(last_sales_date, (pd.Timestamp, np.datetime64)):
    #         last_sales_date = pd.Timestamp(last_sales_date).to_pydatetime()
    #     elif not isinstance(last_sales_date, datetime):
    #         last_sales_date = datetime.combine(last_sales_date, datetime.min.time())
        
    #     # Cari prediksi antara last_sales_date dan base_date
    #     prediksi_existing = database.get_data_prediksi(
    #         id_barang,
    #         (last_sales_date + relativedelta(months=1)).strftime('%Y-%m-%d'),
    #         base_date.strftime('%Y-%m-%d')
    #     )
        
    #     if len(prediksi_existing) > 0:
    #         # Gabungkan sales dengan prediksi
    #         combined = pd.concat([sales, prediksi_existing])
    #         combined = combined[~combined.index.duplicated(keep='first')]
    #         combined = combined.sort_index()
    #         # FIX: Isi NaN dengan 0 setelah concat
    #         combined['kuantitas'] = combined['kuantitas'].fillna(0)
    #         sales = combined
    #         print(f"   ✓ Data dilengkapi dengan {len(prediksi_existing)} bulan prediksi")
    #         print(f"   ✓ Total data: {len(sales)} bulan")
        
    #     # Cek lagi setelah dilengkapi
    #     if len(sales) < min_data_months:
    #         raise ValueError(
    #             f"Data tidak cukup untuk prediksi ARIMA. "
    #             f"Minimal {min_data_months} bulan, tersedia {len(sales)} bulan "
    #             f"(penjualan: {available_months}, prediksi: {len(prediksi_existing) if len(prediksi_existing) > 0 else 0}). "
    #         )
    
    ori_sales = sales.copy()

    print("ORI SALES")
    print(ori_sales)
    print("=" * 60)
    
    # Smoothing dengan Savitzky-Golay filter
    # if len(sales) >= 5:
    #     window_size = min(5, len(sales) if len(sales) % 2 == 1 else len(sales)-1)
    #     sales['kuantitas'] = savgol_filter(sales['kuantitas'], window_size, 2)

    sales['kuantitas'] = savgol_filter(sales['kuantitas'], 5, 2)

    print("ORI SALES")
    print(ori_sales)
    print("=" * 60)
    
    future_dates = get_next_3_months(base_date)

    model = ARIMA(sales['kuantitas'], order=(p,d,q))
    result = model.fit()

    forecast = result.forecast(steps=len(future_dates))
    mean_residual = (ori_sales['kuantitas'] - sales['kuantitas']).mean()
    forecast_values = forecast + mean_residual

    # Pastikan tidak ada nilai negatif
    forecast_values = np.maximum(forecast_values, 0)

    result = pd.DataFrame({
        'tanggal': future_dates,
        'kuantitas': forecast_values.values
    })

    print("HASIL PREDIKSI ARIMA")
    print(result)
    print("=" * 60)

    return result

def prediksi_mean(id_barang, base_date=None):
    combined_data = database.get_last_12_data_penjualan(id_barang)
    combined_data['kuantitas'] = combined_data['kuantitas'].fillna(0)
    
    future_dates = get_next_3_months(base_date)
    
    predictions = []
    for i in range(len(future_dates)):
        # Hitung rata-rata dari 12 data terakhir
        window_data = combined_data['kuantitas'].tail(12).fillna(0)
        mean_value = window_data.mean()
            
        if pd.isna(mean_value):
            mean_value = predictions[-1] if predictions else 0
            
        predictions.append(mean_value)
            
        # Tambahkan prediksi ini ke combined_data untuk iterasi berikutnya
        new_row = pd.DataFrame({
            'kuantitas': [mean_value]
        }, index=[future_dates[i]])
        combined_data = pd.concat([combined_data, new_row])

    result = pd.DataFrame({
        'tanggal': future_dates,
        'kuantitas': predictions
    })

    print("HASIL PREDIKSI MEAN")
    print(result)
    print("=" * 60)

    return result

def generate_prediksi(info_barang, base_date=None):
    id_barang = info_barang[0]
    nama_barang = info_barang[1]
    model_prediksi = info_barang[2]
    p = int(info_barang[3]) if pd.notna(info_barang[3]) else None
    d = int(info_barang[4]) if pd.notna(info_barang[4]) else None
    q = int(info_barang[5]) if pd.notna(info_barang[5]) else None

    try:
        if model_prediksi == 'ARIMA':
            if p is None or d is None or q is None:
                raise ValueError("Order ARIMA (p, d, q) harus disediakan")
            
            result = prediksi_arima(id_barang, p, d, q, base_date)
            used_model = 'ARIMA'

        elif model_prediksi == 'Mean':
            result = prediksi_mean(id_barang, base_date)
            used_model = 'MEAN'

        else:
            raise ValueError("Model prediksi tidak dikenali (harus 'ARIMA' atau 'Mean')")

        for idx, row in result.iterrows():
            database.insert_hasil_prediksi(
                id_barang=id_barang,
                tanggal=row['tanggal'].strftime("%Y-%m-%d"),
                kuantitas=round(row['kuantitas'], 2)
            )

        return {
            'status': 'generated',
            'message': f"✓ Prediksi berhasil di-generate untuk 3 bulan ke depan (Model: {used_model})",
            'data': result,
            'info': f"{len(result)} bulan prediksi berhasil disimpan"
        }

    except Exception as e:
        return {
            'status': 'error',
            'message': f"✗ Error: {str(e)}",
            'data': None,
            'info': None
        }