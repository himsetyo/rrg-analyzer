# Simpan dalam file bernama app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta
import io

# Import kelas RRGAnalyzer dari file rrg.py
# Asumsi kode di atas disimpan dalam file rrg.py
from rrg import RRGAnalyzer

st.title("Relative Rotation Graph (RRG) Analyzer")

st.write("""
Aplikasi ini menganalisis kinerja relatif saham-saham dalam portofolio Anda 
dibandingkan dengan benchmark menggunakan metode Relative Rotation Graph (RRG).
""")

# Input parameter
st.sidebar.header("Parameter Input")

benchmark = st.sidebar.text_input("Benchmark Symbol (contoh: ^JKSE untuk IHSG):", "^JKSE")

stocks_input = st.sidebar.text_area(
    "Daftar Saham (satu simbol per baris, tambahkan .JK untuk saham Indonesia):",
    "BBCA.JK\nBBRI.JK\nTLKM.JK\nASII.JK\nUNVR.JK\nBMRI.JK"
)

period_years = st.sidebar.slider("Periode Data (tahun):", 1, 5, 3)
rs_ratio_period = st.sidebar.slider("Periode RS-Ratio (hari trading):", 20, 100, 63)
rs_momentum_period = st.sidebar.slider("Periode RS-Momentum (hari trading):", 5, 60, 21)
trail_length = st.sidebar.slider("Panjang Trail:", 1, 20, 8)

# Tombol untuk menjalankan analisis
if st.sidebar.button("Jalankan Analisis"):
    stocks = [s.strip() for s in stocks_input.split("\n") if s.strip()]
    
    if not stocks:
        st.error("Silakan masukkan setidaknya satu simbol saham.")
    else:
        try:
            # Tampilkan progress
            with st.spinner("Mengunduh data dan melakukan analisis..."):
                analyzer = RRGAnalyzer(benchmark, stocks, period_years)
                analyzer.download_data()
                analyzer.calculate_rs_ratio(period=rs_ratio_period)
                analyzer.calculate_rs_momentum(period=rs_momentum_period)
                analyzer.normalize_data()
                
                results = analyzer.get_latest_data()
                
                # Tampilkan hasil dalam tabel
                st.subheader("Hasil Analisis RRG")
                st.dataframe(results.style.highlight_max(axis=0, subset=['RS-Ratio', 'RS-Momentum']))
                
                # Tampilkan grafik
                st.subheader("Relative Rotation Graph (RRG)")
                fig = plt.figure(figsize=(10, 8))
                
                # Plot detail seperti dalam metode plot_rrg
                plt.axhline(y=100, color='gray', linestyle='-', alpha=0.3)
                plt.axvline(x=100, color='gray', linestyle='-', alpha=0.3)
                
                plt.fill_between([100, 120], 100, 120, color='green', alpha=0.1)
                plt.fill_between([100, 120], 80, 100, color='yellow', alpha=0.1)
                plt.fill_between([80, 100], 80, 100, color='red', alpha=0.1)
                plt.fill_between([80, 100], 100, 120, color='blue', alpha=0.1)
                
                plt.text(110, 110, 'LEADING', fontsize=12, ha='center')
                plt.text(110, 90, 'WEAKENING', fontsize=12, ha='center')
                plt.text(90, 90, 'LAGGING', fontsize=12, ha='center')
                plt.text(90, 110, 'IMPROVING', fontsize=12, ha='center')
                
                for symbol in stocks:
                    if symbol in analyzer.rs_ratio_norm and symbol in analyzer.rs_momentum_norm:
                        x_data = analyzer.rs_ratio_norm[symbol].iloc[-trail_length:].values
                        y_data = analyzer.rs_momentum_norm[symbol].iloc[-trail_length:].values
                        
                        plt.plot(x_data, y_data, '-', linewidth=1, alpha=0.6)
                        plt.scatter(x_data[-1], y_data[-1], s=50)
                        plt.annotate(symbol, (x_data[-1], y_data[-1]), 
                                    xytext=(5, 5), textcoords='offset points')
                
                plt.xlim(80, 120)
                plt.ylim(80, 120)
                plt.grid(True, alpha=0.3)
                plt.xlabel('RS-Ratio (Relative Strength)')
                plt.ylabel('RS-Momentum')
                plt.title(f'Relative Rotation Graph (RRG) vs {benchmark}')
                
                st.pyplot(fig)
                
                # Opsi untuk mengunduh hasil analisis
                csv = results.to_csv(index=False)
                st.download_button(
                    label="Unduh Hasil Analisis (CSV)",
                    data=csv,
                    file_name="rrg_analysis_results.csv",
                    mime="text/csv"
                )
                
        except Exception as e:
            st.error(f"Terjadi kesalahan dalam analisis: {str(e)}")

# Tampilkan penjelasan RRG
st.sidebar.markdown("---")
st.sidebar.header("Tentang RRG")
st.sidebar.write("""
**Interpretasi Kuadran:**

- **Leading (Kanan Atas)**: Saham dengan kekuatan relatif dan momentum positif. Rekomendasi: Hold/Buy
- **Weakening (Kanan Bawah)**: Saham dengan kekuatan relatif tinggi tapi momentum menurun. Rekomendasi: Hold/Take Profit
- **Lagging (Kiri Bawah)**: Saham dengan kekuatan relatif rendah dan momentum negatif. Rekomendasi: Sell/Cut Loss
- **Improving (Kiri Atas)**: Saham dengan kekuatan relatif rendah tapi momentum meningkat. Rekomendasi: Accumulate/Buy Carefully
""")
