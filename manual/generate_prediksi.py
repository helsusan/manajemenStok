"""
Script untuk manual prediksi September - November 2025
Jalankan SEKALI SAJA untuk setup awal data prediksi

CARA PAKAI:
1. Edit SIMULATED_DATE dan DB_CONFIG sesuai kebutuhan
2. Jalankan: python manual_prediksi_september.py
3. Script akan generate prediksi dari tanggal simulasi
4. Setelah selesai, gunakan dashboard normal (dengan tanggal real-time)

CONTOH:
- SIMULATED_DATE = 1 September 2025
- Akan generate prediksi: Oktober, November, Desember 2025

CATATAN:
- Script ini menggunakan parameter base_date untuk simulate tanggal
- Aman digunakan tanpa perlu mock/patch datetime
- Hanya untuk one-time setup, jangan dipakai di production!
"""

import sys
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import manual_database
import manual_prediction

# Misal 1 Agustus 2025 -> prediksi Sep, Okt, Nov
SIMULATED_DATE = datetime(2025, 5, 1)  

# Prediksi 3 bulan ke depan
MONTHS_AHEAD = 6

FALLBACK_TO_MEAN = False

def main():
    print(f"Simulasi tanggal: {SIMULATED_DATE.strftime('%d %B %Y')}")
    print(f"Generate prediksi untuk {MONTHS_AHEAD} bulan ke depan:")
    print(f"🔄 Fallback ke Mean: {'AKTIF' if FALLBACK_TO_MEAN else 'TIDAK AKTIF'}")
    print()
    
    # Hitung tanggal prediksi yang akan di-generate
    next_month = SIMULATED_DATE.replace(day=1) + relativedelta(months=1)
    
    for i in range(MONTHS_AHEAD):
        target_month = next_month + relativedelta(months=i)
        print(f"  {i+1}. {target_month.strftime('%B %Y')}")
    
    print("="*70)
    print()
    
    # Konfirmasi dari user
    confirm = input("Lanjutkan generate prediksi? (y/n): ").lower().strip()
    if confirm != 'y':
        print("Canceled")
        return
    
    print("\nMulai prediksi...\n")
    print("-"*70)
    
    try:
        # Inisialisasi
        print("Menghubungkan ke database...")
        manual_database.get_connection()
        
        print("Inisialisasi model prediksi...")
        
        # Get all barang
        barang_list = manual_database.get_all_nama_barang()
        
        print(f"Total barang: {len(barang_list)}")
        print("-"*70)
        print()
        
        success_count = 0
        error_count = 0
        error_details = []
        
        # Loop setiap barang
        for idx, barang in barang_list.iterrows():
            nama = barang['nama']
            info_barang = manual_database.get_data_barang(nama)
            
            try:
                print(f"[{idx+1}/{len(barang_list)}] {nama}...", end=" ")
                
                result = manual_prediction.generate_prediksi(
                    info_barang=info_barang,
                    base_date=SIMULATED_DATE,
                    months_ahead=MONTHS_AHEAD
                )
                
                if result['status'] == 'generated':
                    print("✅ SUCCESS")
                    success_count += 1
                    
                    # Tampilkan detail prediksi
                    if result['data'] is not None:
                        for _, row in result['data'].iterrows():
                            print(f"      → {row['tanggal'].strftime('%b %Y')}: {row['kuantitas']:.2f}")
                else:
                    print(f"❌ {result['status'].upper()}")
                    print(f"      ✗ {result['message']}")
                    error_count += 1
                    error_details.append((nama, result['message']))
                    
            except Exception as e:
                print(f"❌ ERROR")
                print(f"      ✗ {str(e)}")
                error_count += 1
                error_details.append((nama, str(e)))
            
            print()
        
        print("="*70)
        print("📊 SUMMARY HASIL PREDIKSI MANUAL")
        print("="*70)
        print(f"✅ Berhasil: {success_count}/{len(barang_list)} barang")
        print(f"❌ Error: {error_count}/{len(barang_list)} barang")
        print("="*70)
        
        if error_details:
            print("\n⚠️ DETAIL ERROR:")
            print("-"*70)
            for nama, message in error_details:
                print(f"  • {nama}:")
                print(f"    {message}")
            print("-"*70)
        
        print()
        
        if success_count > 0:
            print("✅ PREDIKSI MANUAL SELESAI!")
            print(f"Data prediksi {(next_month).strftime('%B %Y')} - {(next_month + relativedelta(months=MONTHS_AHEAD-1)).strftime('%B %Y')} berhasil disimpan")
        else:
            print("⚠️ TIDAK ADA DATA YANG BERHASIL DI-GENERATE")
            # print("💡 Cek error message di atas untuk troubleshooting")
            # print("💡 Pastikan:")
            # print("   - Database sudah terkoneksi dengan benar")
            # print("   - Ada data penjualan yang cukup (minimal 12 bulan untuk ARIMA)")
            # print("   - Konfigurasi model di tabel 'barang' sudah benar")
            # print("   - Set FALLBACK_TO_MEAN=True jika data kurang dari 12 bulan")
        
        print()
        
    except Exception as e:
        print()
        print("="*70)
        print("❌ ERROR FATAL")
        print("="*70)
        print(f"Error: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        print("="*70)
        return 1
    
    return 0 if error_count == 0 else 1

if __name__ == "__main__":
    exit_code = main()
    
    print()
    input("Press Enter to exit...")
    
    sys.exit(exit_code)