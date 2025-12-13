import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import warnings
warnings.filterwarnings('ignore')
import manual_database

# Prediksi n bulan ke depan (default: 1 bulan)
def get_next_n_months(base_date=None, months_ahead=1):
    if base_date is None:
        base_date = datetime.now()
    
    if not isinstance(base_date, datetime):
        base_date = datetime.combine(base_date, datetime.min.time())
    
    # Mulai prediksi dari bulan depan setelah base_date
    start_prediction_date = base_date.replace(day=1) + relativedelta(months=1)

    dates = []
    for i in range(months_ahead):
        future_date = start_prediction_date + relativedelta(months=i)
        dates.append(pd.Timestamp(future_date.strftime("%Y-%m-01")))

    print("GET NEXT 3 MONTHS")
    print(f"Base date: {base_date.strftime('%Y-%m-%d')}")
    print(dates)
    print("=" * 60)

    return dates

# def check_prediksi(id_barang, base_date=None):
#     required_dates = get_next_3_months(base_date)
#     start_date = required_dates[0].strftime('%Y-%m-%d')
#     end_date = required_dates[2].strftime('%Y-%m-%d')

#     df_prediksi = manual_database.get_data_prediksi(id_barang, start_date, end_date)

#     # Cek bulan mana yang belum ada
#     missing_months = []
#     for date in required_dates:
#         date_normalized = pd.Timestamp(date.strftime('%Y-%m-01'))
#         if date_normalized not in df_prediksi.index:
#             missing_months.append(date)

#     print("CHECK PREDIKSI")
#     print("exists: ", len(missing_months) == 0)
#     print("missing_months: ", missing_months)
#     print("existing_data: ", df_prediksi)
#     print("required_count: ", len(required_dates))
#     print("existing_count: ", len(df_prediksi))
#     print("=" * 60)
        
#     return {
#         'exists': len(missing_months) == 0,
#         'missing_months': missing_months,
#         'existing_data': df_prediksi,
#         'required_count': len(required_dates),
#         'existing_count': len(df_prediksi)
#     }

def prediksi_arima(id_barang, p, d, q, base_date, months_ahead):
    first_sales_date = manual_database.get_first_sales_date(id_barang)

    # Jika tidak ada data penjualan sama sekali (None/NaT), lempar error agar fallback ke Mean
    if first_sales_date is None or pd.isna(first_sales_date):
        raise ValueError("Data penjualan kosong (Barang Baru)")

    # Hitung tanggal akhir data training (akhir bulan dari base_date)
    # Misal base_date = 1 Sept, maka end_date = 30 Sept
    end_date = base_date.replace(day=1) + relativedelta(months=1) - relativedelta(days=1)

    # Ambil data HANYA sampai end_date
    sales = manual_database.get_data_penjualan_with_date_range(
        id_barang=id_barang,
        start_date=first_sales_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )

    # sales = manual_database.get_all_data_penjualan(id_barang)
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

    ori_sales = sales.copy()

    print("ORI SALES")
    print(ori_sales)
    print("=" * 60)

    print("DEBUG DATA COMPARISON:")
    print("Start Date:", sales.index.min())
    print("End Date:", sales.index.max())
    print("Mean Kuantitas (Original):", ori_sales['kuantitas'].mean())
    print("Sample 5 data terakhir:", ori_sales['kuantitas'].tail(5).values)
    print("=" * 60)

    from sklearn.preprocessing import PowerTransformer
    transformer = PowerTransformer(method='yeo-johnson', standardize=True)
    transformed_data = transformer.fit_transform(sales[['kuantitas']])
    sales['kuantitas'] = transformed_data

    # print("ORI SALES")
    # print(ori_sales)
    # print("=" * 60)
    
    future_dates = get_next_n_months(base_date, months_ahead)

    train_data = sales['kuantitas'].values
    model = ARIMA(train_data, order=(p,d,q))
    result = model.fit()

    forecast = result.forecast(steps=len(future_dates))
    forecast_values = forecast.values if hasattr(forecast, 'values') else forecast
    forecast_values = forecast_values.reshape(-1, 1)
    forecast_values = transformer.inverse_transform(forecast_values)
    forecast_values = np.maximum(forecast_values, 0)

    # 5. Flatten kembali jadi 1D array agar mudah di-slice
    forecast_values = forecast_values.flatten()

    result = pd.DataFrame({
        'tanggal': future_dates,
        'kuantitas': forecast_values
    })

    print("HASIL PREDIKSI ARIMA")
    print(result)
    print("=" * 60)

    return result

def prediksi_mean(id_barang, base_date, months_ahead):
    combined_data = manual_database.get_last_12_data_penjualan(id_barang)
    combined_data['kuantitas'] = combined_data['kuantitas'].fillna(0)
    
    future_dates = get_next_n_months(base_date, months_ahead)
    
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

def generate_prediksi(info_barang, base_date, months_ahead):
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
            
            result = prediksi_arima(id_barang, p, d, q, base_date, months_ahead)
            used_model = 'ARIMA'

        elif model_prediksi == 'Mean':
            result = prediksi_mean(id_barang, base_date, months_ahead)
            used_model = 'MEAN'

        else:
            raise ValueError("Model prediksi tidak dikenali (harus 'ARIMA' atau 'Mean')")

        for idx, row in result.iterrows():
            # --- PERBAIKAN 2: Sanitasi nilai sebelum round ---
            qty_val = row['kuantitas']
            
            # Cek jika NaN, NaT, atau None -> Ubah jadi 0
            if pd.isna(qty_val):
                qty_val = 0
            
            # Pastikan tipe data float agar round aman
            qty_val = float(qty_val)
            
            manual_database.insert_hasil_prediksi(
                id_barang=id_barang,
                tanggal=row['tanggal'].strftime("%Y-%m-%d"),
                kuantitas=round(qty_val, 2) # Sekarang aman
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