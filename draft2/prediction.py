import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from scipy.signal import savgol_filter
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import warnings
warnings.filterwarnings('ignore')
import database

def get_next_3_months():
    today = datetime.now().date()
    next_month = today.replace(day=1) + relativedelta(months=1)

    dates = []
    for i in range(3):
        dates.append(next_month + relativedelta(months=i))

    print("GET NEXT 3 MONTHS")
    print(dates)
    print("=" * 60)

    return dates

def check_prediksi(id_barang):
    required_dates = get_next_3_months()
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

def prediksi_arima(id_barang, p, d, q):
    sales = database.get_data_penjualan(id_barang)
    # df['tgl_faktur'] = pd.to_datetime(df['tgl_faktur'])
    # sales = df.set_index('tgl_faktur').resample('MS').agg(Quantity=('kuantitas', 'sum')).fillna(0)
    # sales.index = sales.index.strftime('%Y-%m')
    sales.index.name = None
    ori_sales = sales.copy()

    print("\nPREDIKSI ARIMA - DATA SALES")
    print(sales)
    print("=" * 60)
    
    sales['kuantitas'] = savgol_filter(sales['kuantitas'], 5, 2)

    future_dates = get_next_3_months()

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

def prediksi_mean(id_barang):
    combined_data = database.get_last_12_data_penjualan(id_barang)
    future_dates = get_next_3_months()
    
    predictions = []
    for i in range(len(future_dates)):
        # Hitung rata-rata dari 12 data terakhir
        window_data = combined_data['kuantitas'].tail(12)
        mean_value = window_data.mean()
            
        if pd.isna(mean_value):
            # Jika masih NaN, gunakan prediksi sebelumnya atau 0
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

def generate_prediksi(info_barang):
    id_barang = info_barang[0]
    model_prediksi = info_barang[2]
    p=int(info_barang[3]) if pd.notna(info_barang[3]) else None
    d=int(info_barang[4]) if pd.notna(info_barang[4]) else None
    q=int(info_barang[5]) if pd.notna(info_barang[5]) else None

    try:
        if model_prediksi == 'ARIMA':
            if p is None or d is None or q is None:
                raise ValueError("Order ARIMA (p, d, q) harus disediakan")
            result = prediksi_arima(id_barang, p, d, q)
        elif model_prediksi == 'Mean':
            result = prediksi_mean(id_barang)
        else:
            raise ValueError(f"Model prediksi tidak ditemukan")
        
        # Simpan ke database
        for idx, row in result.iterrows():
            database.insert_hasil_prediksi(
                id_barang=id_barang,
                tanggal=row['tanggal'],
                kuantitas=round(row['kuantitas'], 2)
            )

        return {
            'status': 'generated',
            'message': f"✓ Prediksi berhasil di-generate untuk {months_ahead} bulan ke depan",
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
    
    






