import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
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
Aplikasi ini menganalisis kinerja relatif saham-saham dalam portofolio Anda dibandingkan dengan benchmark menggunakan metode Relative Rotation Graph (RRG).
""")

# Styling
def local_css():
    st.markdown("""
    """, unsafe_allow_html=True)

local_css()

# Mode input data
input_mode = st.sidebar.radio(
    "Pilih Sumber Data:",
    ["Bloomberg Excel", "File CSV Terpisah"],
    index=1  # Default ke CSV untuk kasus Anda
)

# Sidebar untuk upload file dan input
st.sidebar.header("Upload Data")

if input_mode == "Bloomberg Excel":
    # Upload Bloomberg Excel file
    excel_file = st.sidebar.file_uploader(
        "Upload file Excel Bloomberg:",
        type=["xlsx", "xls"],
        help="File Excel dari Bloomberg dengan format standar Bloomberg"
    )
    
    if excel_file:
        # Preview file untuk membantu input ticker
        try:
            excel_preview = pd.read_excel(excel_file, header=None, nrows=15)
            with st.expander("Preview File Excel", expanded=False):
                st.dataframe(excel_preview)
        except Exception as e:
            st.warning(f"Tidak dapat menampilkan preview: {str(e)}")
    
    # Input ticker benchmark
    benchmark_ticker = st.sidebar.text_input(
        "Ticker Benchmark:",
        "JCI Index",
        help="Masukkan ticker benchmark persis seperti di Excel (contoh: 'JCI Index')"
    )
    
    # Input ticker saham
    stock_tickers_input = st.sidebar.text_area(
        "Ticker Saham (satu ticker per baris):",
        "BBCA IJ Equity\nBBRI IJ Equity\nTLKM IJ Equity\nASII IJ Equity\nUNVR IJ Equity",
        help="Masukkan ticker saham persis seperti di Excel (contoh: 'BBCA IJ Equity')"
    )

else:
    # Upload benchmark file CSV
    benchmark_file = st.sidebar.file_uploader(
        "Upload file CSV Benchmark (contoh: LQ45.csv):",
        type=["csv"],
        help="File CSV dengan format: Date,Open,High,Low,Close,Volume"
    )
    
    # Upload stock files CSV
    stock_files = st.sidebar.file_uploader(
        "Upload file CSV Saham (multiple files):",
        type=["csv"],
        accept_multiple_files=True,
        help="File CSV dengan format: Date,Open,High,Low,Close,Volume"
    )

# Parameter analisis
st.sidebar.header("Parameter Analisis")

# Maksimal tanggal analisis
use_max_date = st.sidebar.checkbox("Batasi Tanggal Analisis", value=False, help="Aktifkan untuk membatasi analisis hingga tanggal tertentu")
if use_max_date:
    max_date = st.sidebar.date_input(
        "Maksimal Tanggal Analisis:",
        datetime.now() - timedelta(days=1),
        help="Analisis hanya akan menggunakan data hingga tanggal ini"
    )
else:
    max_date = None

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

# Tampilkan tanggal analisis saat ini
current_date = datetime.now().strftime('%d %B %Y')
if use_max_date:
    analysis_date = max_date.strftime('%d %B %Y')
    st.sidebar.markdown(f"**Tanggal Analisis:** {analysis_date} (dibatasi)")
else:
    st.sidebar.markdown(f"**Tanggal Analisis:** {current_date} (terkini)")

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
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as f:
        f.write(uploaded_file.getvalue())
        return f.name

if analyze_button:
    if input_mode == "Bloomberg Excel":
        if excel_file is None:
            st.error("Silakan upload file Excel Bloomberg terlebih dahulu.")
            st.stop()
        
        # Parse input ticker
        stock_tickers = [ticker.strip() for ticker in stock_tickers_input.split("\n") if ticker.strip()]
        if not stock_tickers:
            st.error("Silakan masukkan setidaknya satu ticker saham.")
            st.stop()
        
        # Simpan file ke temporary file
        excel_temp = save_uploaded_file(excel_file)
        
        try:
            # Mode debug
            if debug_mode:
                st.sidebar.subheader("Informasi Debug")
                st.sidebar.write("File Excel:", excel_file.name)
                st.sidebar.write("Benchmark Ticker:", benchmark_ticker)
                st.sidebar.write("Stock Tickers:", stock_tickers)
                if use_max_date:
                    st.sidebar.write("Maksimal Tanggal:", max_date)
            
            # Jalankan analisis dengan progress bar
            progress_text = "Menganalisis data saham..."
            my_bar = st.progress(0, text=progress_text)
            
            # Step 1: Inisialisasi
            my_bar.progress(10, text="Inisialisasi analisis...")
            analyzer = RRGAnalyzer(
                excel_file=excel_temp,
                benchmark_ticker=benchmark_ticker,
                stock_tickers=stock_tickers,
                period_years=period_years,
                max_date=max_date
            )
            
            # Step 2: Load data
            my_bar.progress(30, text="Memuat data dari Excel Bloomberg...")
            success = analyzer.load_data_from_bloomberg_excel()
            if not success:
                st.error("Gagal memuat data dari file Excel. Periksa format file dan ticker yang dimasukkan.")
                my_bar.empty()
                # Clean up temp file
                os.unlink(excel_temp)
                st.stop()
            
            # Step 3: Hitung RS-Ratio
            my_bar.progress(50, text="Menghitung RS-Ratio...")
            analyzer.calculate_rs_ratio(period=rs_ratio_period)
            if not analyzer.rs_ratio:
                st.error("Gagal menghitung RS-Ratio. Mungkin tidak cukup data.")
                my_bar.empty()
                # Clean up temp file
                os.unlink(excel_temp)
                st.stop()
            
            # Step 4: Hitung RS-Momentum
            my_bar.progress(70, text="Menghitung RS-Momentum...")
            analyzer.calculate_rs_momentum(period=rs_momentum_period)
            if not analyzer.rs_momentum:
                st.error("Gagal menghitung RS-Momentum. Mungkin tidak cukup data.")
                my_bar.empty()
                # Clean up temp file
                os.unlink(excel_temp)
                st.stop()
            
            # Step 5: Normalisasi data
            my_bar.progress(80, text="Menormalisasi data...")
            success = analyzer.normalize_data()
            if not success:
                st.error("Gagal melakukan normalisasi data. Mungkin tidak cukup variasi dalam data.")
                my_bar.empty()
                # Clean up temp file
                os.unlink(excel_temp)
                st.stop()
            
            # Step 6: Dapatkan hasil
            my_bar.progress(90, text="Mempersiapkan hasil...")
            results = analyzer.get_latest_data()
            
            # Step 7: Selesai
            my_bar.progress(100, text="Analisis selesai!")
            time.sleep(0.5)  # Beri waktu user untuk melihat progress 100%
            my_bar.empty()
            
            # Clean up temp file
            os.unlink(excel_temp)
            
            # Tampilkan hasil
            if results is None or len(results) == 0:
                st.error("Tidak dapat melakukan analisis. Pastikan data tersedia dan parameter sudah benar.")
            else:
                # Tampilkan tanggal analisis aktual
                analysis_date = analyzer.get_analysis_date().strftime('%d %B %Y')
                st.subheader(f"Analisis pada tanggal: {analysis_date}")
                
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
            
            # Clean up temp file
            if 'excel_temp' in locals():
                os.unlink(excel_temp)
    
    else:
        # File CSV Terpisah
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
                    if use_max_date:
                        st.sidebar.write("Maksimal Tanggal:", max_date)
                    
                    # Preview data benchmark
                    try:
                        st.sidebar.subheader("Preview Benchmark")
                        benchmark_preview = pd.read_csv(benchmark_temp)
                        st.sidebar.write(benchmark_preview.head(3))
                        
                        # Preview data saham pertama
                        if stock_files:
                            st.sidebar.subheader(f"Preview {stock_files[0].name}")
                            stock_preview = pd.read_csv(stock_temps[0])
                            st.sidebar.write(stock_preview.head(3))
                    except Exception as e:
                        st.sidebar.error(f"Error saat preview data: {str(e)}")
                
                # Jalankan analisis dengan progress bar
                progress_text = "Menganalisis data saham..."
                my_bar = st.progress(0, text=progress_text)
                
                # Step 1: Inisialisasi
                my_bar.progress(10, text="Inisialisasi analisis...")
                analyzer = RRGAnalyzer(
                    benchmark_file=benchmark_temp,
                    stock_files=stock_temps,
                    period_years=period_years,
                    max_date=max_date
                )
                
                # Step 2: Load data
                my_bar.progress(30, text="Memuat data dari file CSV...")
                success = analyzer.load_data_from_files()  # Pastikan menggunakan metode ini untuk CSV
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
                    # Tampilkan tanggal analisis aktual
                    analysis_date = analyzer.get_analysis_date().strftime('%d %B %Y')
                    st.subheader(f"Analisis pada tanggal: {analysis_date}")
                    
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
                
                # Clean up temp files
                if 'benchmark_temp' in locals():
                    os.unlink(benchmark_temp)
                if 'stock_temps' in locals():
                    for temp_file in stock_temps:
                        os.unlink(temp_file)

else:
    # Tampilkan info default ketika aplikasi pertama kali dibuka
    if input_mode == "Bloomberg Excel":
        st.info("👈 Upload file Excel Bloomberg di panel sebelah kiri, masukkan ticker benchmark dan saham, lalu klik 'Jalankan Analisis'.")
        
        # Tampilkan contoh format file Excel Bloomberg
        with st.expander("📝 Format File Excel Bloomberg", expanded=False):
            st.markdown("""
            ### Format Excel Bloomberg
            
            File Excel dari Bloomberg Terminal biasanya memiliki format horizontal, di mana:
            
            1. **Baris awal**: Berisi informasi metadata seperti tanggal mulai dan akhir data
            2. **Baris header**: Berisi nama ticker seperti "JCI Index", "BBCA IJ Equity", dll.
            3. **Kolom data**: Setiap ticker memiliki 5 kolom berurutan untuk data OHLCV:
               - PX_OPEN (Open)
               - PX_HIGH (High)
               - PX_LOW (Low)
               - PX_LAST (Close)
               - PX_VOLUME (Volume)
            
            ### Contoh Data Ticker yang Didukung:
            - Untuk Benchmark: "JCI Index", "LQ45 Index"
            - Untuk Saham: "BBCA IJ Equity", "ASII IJ Equity", dll.
            
            *Catatan*: Pastikan format ticker yang Anda masukkan persis sama dengan yang tertulis di file Excel.
            """)
    else:
        st.info("👈 Upload file CSV di panel sebelah kiri dan atur parameter, lalu klik 'Jalankan Analisis'.")
        
        # Tampilkan contoh format file CSV
        with st.expander("📝 Format File CSV yang Diperlukan"):
            st.markdown("""
            ### Format untuk Data Benchmark (misalnya: LQ45.csv)
            
            ```csv
            Ticker,Date,Open,High,Low,Close,Volume
            LQ45,01/01/2020,1022.344,1023.884,1014.473,1014.473,809234400
            LQ45,01/02/2020,1017.158,1017.52,1007.5,1011.618,612725900
            ...
            ```
            
            ### Format untuk Data Saham (misalnya: BBCA.csv)
            
            ```csv
            Ticker,Date,Open,High,Low,Close,Volume
            BBCA,01/01/2020,6675,6720,6670,6685,61168000
            BBCA,01/02/2020,6695,6780,6680,6690,49445000
            ...
            ```
            
            ### Catatan Penting Format:
            - **Header**: Wajib menggunakan header yang sesuai dengan kolom data
            - **Kolom Ticker**: Sebaiknya disertakan untuk menampilkan nama ticker yang benar pada grafik
            - **Format Tanggal**: Aplikasi mendukung format MM/DD/YYYY (01/01/2020) atau YYYY-MM-DD (2020-01-01)
            - **Pemisah Desimal**: Gunakan titik (.) bukan koma (,)
            - **Pemisah Kolom**: Gunakan koma (,) - format CSV standar
            - **Urutan Data**: Urutkan dari tanggal terlama ke terbaru (ascending)
            """)

# Footer
st.markdown("---")
st.markdown("Dibuat dengan ❤️ menggunakan Python dan Streamlit | © 2025")
