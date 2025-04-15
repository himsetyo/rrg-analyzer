import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import time
import os
import tempfile

# Konfigurasi halaman harus menjadi perintah Streamlit pertama
st.set_page_config(
    page_title="RRG Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sekarang aman untuk import RRGAnalyzer
try:
    from rrg import RRGAnalyzer
except Exception as e:
    st.error(f"Error mengimpor modul RRGAnalyzer: {str(e)}")
    st.stop()

# Judul aplikasi
st.title("📊 Relative Rotation Graph (RRG) Analyzer")

st.markdown("""
Aplikasi ini menganalisis kinerja relatif saham-saham dalam portofolio Anda 
dibandingkan dengan benchmark menggunakan metode Relative Rotation Graph (RRG).
""")

# Styling
def local_css():
    st.markdown("""
    <style>
        .stApp {
            max-width: 1200px;
            margin: 0 auto;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        h1 {
            color: #0066cc;
        }
        .stButton>button {
            width: 100%;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# Sidebar untuk upload file
st.sidebar.header("Upload Data")

# Upload benchmark file
benchmark_file = st.sidebar.file_uploader(
    "Upload file CSV Benchmark (contoh: IHSG.csv):",
    type=["csv"],
    help="File CSV dengan format: Date,Open,High,Low,Close,Volume"
)

# Upload stock files
stock_files = st.sidebar.file_uploader(
    "Upload file CSV Saham (multiple files):",
    type=["csv"],
    accept_multiple_files=True,
    help="File CSV dengan format: Date,Open,High,Low,Close,Volume"
)

# Parameter analisis
st.sidebar.header("Parameter Analisis")

col1, col2 = st.sidebar.columns(2)
with col1:
    period_years = st.number_input("Periode Data (tahun):", 0.5, 10.0, 3.0, step=0.5)
with col2:
    trail_length = st.number_input("Panjang Trail:", 1, 20, 8, help="Jumlah periode terakhir yang ditampilkan pada grafik")

col3, col4 = st.sidebar.columns(2)
with col3:
    rs_ratio_period = st.number_input("Periode RS-Ratio:", 5, 100, 63, help="Periode untuk perhitungan RS-Ratio (hari trading)")
with col4:
    rs_momentum_period = st.number_input("Periode RS-Momentum:", 3, 60, 21, help="Periode untuk perhitungan RS-Momentum (hari trading)")

# Debug mode
debug_mode = st.sidebar.checkbox("Mode Debug", True)

# Tombol untuk menjalankan analisis
analyze_button = st.sidebar.button("🔍 Jalankan Analisis", type="primary")

# Tampilkan tanggal analisis
st.sidebar.markdown(f"**Tanggal Analisis:** {datetime.now().strftime('%d %B %Y')}")

# Tampilkan penjelasan RRG
with st.sidebar.expander("ℹ️ Tentang RRG"):
    st.write("""
    **Interpretasi Kuadran:**

    - **Leading (Kanan Atas)**: Saham dengan kekuatan relatif dan momentum positif. Rekomendasi: Hold/Buy
    - **Weakening (Kanan Bawah)**: Saham dengan kekuatan relatif tinggi tapi momentum menurun. Rekomendasi: Hold/Take Profit
    - **Lagging (Kiri Bawah)**: Saham dengan kekuatan relatif rendah dan momentum negatif. Rekomendasi: Sell/Cut Loss
    - **Improving (Kiri Atas)**: Saham dengan kekuatan relatif rendah tapi momentum meningkat. Rekomendasi: Accumulate/Buy Carefully
    
    **Cara Membaca:**
    - Posisi pada grafik menunjukkan kinerja relatif dan momentum saham terhadap benchmark
    - Trail menunjukkan pergerakan saham selama beberapa periode terakhir
    - Rotasi biasanya bergerak searah jarum jam: Improving → Leading → Weakening → Lagging
    """)

# Fungsi untuk menyimpan file yang di-upload ke file sementara
def save_uploaded_file(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as f:
        f.write(uploaded_file.getvalue())
        return f.name

if analyze_button:
    if benchmark_file is None:
        st.error("Silakan upload file benchmark terlebih dahulu.")
    elif not stock_files:
        st.error("Silakan upload setidaknya satu file saham.")
    else:
        try:
            # Simpan file ke temporary files
            benchmark_temp = save_uploaded_file(benchmark_file)
            stock_temps = [save_uploaded_file(f) for f in stock_files]
            
            # Mode debug
            if debug_mode:
                st.sidebar.subheader("Informasi Debug")
                st.sidebar.write("Benchmark:", benchmark_file.name)
                st.sidebar.write("Jumlah File Saham:", len(stock_files))
                
                # Preview data benchmark
                st.sidebar.subheader("Preview Benchmark")
                benchmark_preview = pd.read_csv(benchmark_temp)
                st.sidebar.write(benchmark_preview.head(3))
                
                # Preview data saham pertama
                if stock_files:
                    st.sidebar.subheader(f"Preview {stock_files[0].name}")
                    stock_preview = pd.read_csv(stock_temps[0])
                    st.sidebar.write(stock_preview.head(3))
            
            # Jalankan analisis dengan progress bar
            progress_text = "Menganalisis data saham..."
            my_bar = st.progress(0, text=progress_text)
            
            # Step 1: Inisialisasi
            my_bar.progress(10, text="Inisialisasi analisis...")
            analyzer = RRGAnalyzer(benchmark_file=benchmark_temp, stock_files=stock_temps, period_years=period_years)
            
            # Step 2: Load data
            my_bar.progress(30, text="Memuat data dari file CSV...")
            success = analyzer.load_data_from_files()
            if not success:
                st.error("Gagal memuat data dari file. Periksa format file CSV Anda.")
                my_bar.empty()
                # Clean up temp files
                os.unlink(benchmark_temp)
                for temp_file in stock_temps:
                    os.unlink(temp_file)
                st.stop()
            
            # Step 3: Hitung RS-Ratio
            my_bar.progress(50, text="Menghitung RS-Ratio...")
            analyzer.calculate_rs_ratio(period=rs_ratio_period)
            if not analyzer.rs_ratio:
                st.error("Gagal menghitung RS-Ratio. Mungkin tidak cukup data.")
                my_bar.empty()
                # Clean up temp files
                os.unlink(benchmark_temp)
                for temp_file in stock_temps:
                    os.unlink(temp_file)
                st.stop()
            
            # Step 4: Hitung RS-Momentum
            my_bar.progress(70, text="Menghitung RS-Momentum...")
            analyzer.calculate_rs_momentum(period=rs_momentum_period)
            if not analyzer.rs_momentum:
                st.error("Gagal menghitung RS-Momentum. Mungkin tidak cukup data.")
                my_bar.empty()
                # Clean up temp files
                os.unlink(benchmark_temp)
                for temp_file in stock_temps:
                    os.unlink(temp_file)
                st.stop()
            
            # Step 5: Normalisasi data
            my_bar.progress(80, text="Menormalisasi data...")
            success = analyzer.normalize_data()
            if not success:
                st.error("Gagal melakukan normalisasi data. Mungkin tidak cukup variasi dalam data.")
                my_bar.empty()
                # Clean up temp files
                os.unlink(benchmark_temp)
                for temp_file in stock_temps:
                    os.unlink(temp_file)
                st.stop()
            
            # Step 6: Dapatkan hasil
            my_bar.progress(90, text="Mempersiapkan hasil...")
            results = analyzer.get_latest_data()
            
            # Step 7: Selesai
            my_bar.progress(100, text="Analisis selesai!")
            time.sleep(0.5)  # Beri waktu user untuk melihat progress 100%
            my_bar.empty()
            
            # Clean up temp files
            os.unlink(benchmark_temp)
            for temp_file in stock_temps:
                os.unlink(temp_file)
            
            # Tampilkan hasil
            if results is None or len(results) == 0:
                st.error("Tidak dapat melakukan analisis. Pastikan data tersedia dan parameter sudah benar.")
            else:
                # Bagi layar menjadi dua kolom
                col_chart, col_table = st.columns([2, 1])
                
                with col_chart:
                    # Tampilkan grafik RRG
                    st.subheader("Relative Rotation Graph (RRG)")
                    fig = analyzer.plot_rrg(trail_length=trail_length)
                    st.pyplot(fig)
                
                with col_table:
                    # Tampilkan hasil dalam tabel
                    st.subheader("Hasil Analisis")
                    
                    # Formatting untuk tabel
                    def highlight_quadrant(val):
                        if val == "Leading":
                            return 'background-color: rgba(0, 176, 80, 0.2)'
                        elif val == "Weakening":
                            return 'background-color: rgba(255, 255, 0, 0.2)'
                        elif val == "Lagging":
                            return 'background-color: rgba(255, 0, 0, 0.2)'
                        elif val == "Improving":
                            return 'background-color: rgba(0, 112, 192, 0.2)'
                        return ''
                    
                    # Tampilkan tabel dengan format
                    st.dataframe(
                        results.style
                        .format({'RS-Ratio': '{:.2f}', 'RS-Momentum': '{:.2f}'})
                        .applymap(highlight_quadrant, subset=['Quadrant'])
                    )
                    
                    # Opsi untuk mengunduh hasil analisis
                    csv = results.to_csv(index=False)
                    st.download_button(
                        label="📥 Unduh Hasil Analisis (CSV)",
                        data=csv,
                        file_name=f"rrg_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                
                # Tampilkan ringkasan per kuadran
                st.subheader("Ringkasan per Kuadran")
                
                # Buat 4 kolom untuk 4 kuadran
                col_leading, col_improving, col_weakening, col_lagging = st.columns(4)
                
                with col_leading:
                    st.markdown("### Leading 📈")
                    leading_stocks = results[results['Quadrant'] == 'Leading']['Symbol'].tolist()
                    if leading_stocks:
                        for stock in leading_stocks:
                            st.markdown(f"- {stock}")
                    else:
                        st.markdown("*Tidak ada saham pada kuadran ini*")
                
                with col_improving:
                    st.markdown("### Improving 🌱")
                    improving_stocks = results[results['Quadrant'] == 'Improving']['Symbol'].tolist()
                    if improving_stocks:
                        for stock in improving_stocks:
                            st.markdown(f"- {stock}")
                    else:
                        st.markdown("*Tidak ada saham pada kuadran ini*")
                        
                with col_weakening:
                    st.markdown("### Weakening ⚠️")
                    weakening_stocks = results[results['Quadrant'] == 'Weakening']['Symbol'].tolist()
                    if weakening_stocks:
                        for stock in weakening_stocks:
                            st.markdown(f"- {stock}")
                    else:
                        st.markdown("*Tidak ada saham pada kuadran ini*")
                
                with col_lagging:
                    st.markdown("### Lagging 📉")
                    lagging_stocks = results[results['Quadrant'] == 'Lagging']['Symbol'].tolist()
                    if lagging_stocks:
                        for stock in lagging_stocks:
                            st.markdown(f"- {stock}")
                    else:
                        st.markdown("*Tidak ada saham pada kuadran ini*")
        
        except Exception as e:
            st.error(f"Terjadi kesalahan dalam analisis: {str(e)}")
            
            if debug_mode:
                st.error(f"Detail error: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
else:
    # Tampilkan info default ketika aplikasi pertama kali dibuka
    st.info("👈 Upload file CSV di panel sebelah kiri dan atur parameter, lalu klik 'Jalankan Analisis'.")
    
    # Tampilkan contoh format file CSV
    with st.expander("📝 Format File CSV yang Diperlukan"):
        st.markdown("""
        ### Format untuk Data Benchmark (misalnya: IHSG.csv)

        ```csv
        Date,Open,High,Low,Close,Volume
        2024-01-01,7100.5,7150.2,7095.6,7125.8,10500000
        2024-01-02,7125.8,7180.4,7110.3,7160.7,11200000
        ...
        ```

        ### Format untuk Data Saham (misalnya: BBCA.csv)

        ```csv
        Date,Open,High,Low,Close,Volume
        2024-01-01,9500,9550,9475,9525,5000000
        2024-01-02,9525,9600,9510,9590,5500000
        ...
        ```

        ### Catatan Penting Format:
        - **Header**: Wajib menggunakan header `Date,Open,High,Low,Close,Volume`
        - **Format Tanggal**: Sebaiknya gunakan format YYYY-MM-DD (2024-01-01)
        - **Pemisah Desimal**: Gunakan titik (.) bukan koma (,)
        - **Pemisah Kolom**: Gunakan koma (,) - format CSV standar
        - **Urutan Data**: Urutkan dari tanggal terlama ke terbaru (ascending)
        """)

# Footer
st.markdown("---")
st.markdown("Dibuat dengan ❤️ menggunakan Python dan Streamlit | © 2025")
