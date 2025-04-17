import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time
import os
import tempfile
import numpy as np
from report import create_and_download_report

# Konfigurasi halaman harus menjadi perintah Streamlit pertama
st.set_page_config(
    page_title="Comprehensive Stock Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import untuk analisis RRG dan fundamental
try:
    from rrg import RRGAnalyzer
    from fundamental_analyzer import FundamentalAnalyzer
except Exception as e:
    st.error(f"Error mengimpor modul: {str(e)}")
    st.stop()

# Judul aplikasi
st.title("📊 Comprehensive Stock Analyzer")

st.markdown("""
Aplikasi ini menganalisis saham dari dua perspektif:
1. **Teknikal**: Kinerja relatif saham dibandingkan benchmark menggunakan metode Relative Rotation Graph (RRG)
2. **Fundamental**: Kesehatan keuangan perusahaan berdasarkan data dari Yahoo Finance
""")

# Sidebar untuk upload file CSV
st.sidebar.header("Upload Data CSV")

# Upload benchmark file CSV
benchmark_file = st.sidebar.file_uploader(
    "Upload file CSV Benchmark (contoh: LQ45.csv):",
    type=["csv"],
    help="File CSV dengan format: Ticker,Date,Open,High,Low,Close,Volume"
)

# Upload stock files CSV
stock_files = st.sidebar.file_uploader(
    "Upload file CSV Saham (multiple files):",
    type=["csv"],
    accept_multiple_files=True,
    help="File CSV dengan format: Ticker,Date,Open,High,Low,Close,Volume"
)

# Parameter analisis
st.sidebar.header("Parameter Analisis")

# Tipe analisis
analysis_type = st.sidebar.radio(
    "Tipe Analisis:",
    ["RRG (Teknikal)", "Fundamental", "Gabungan (Teknikal + Fundamental)"],
    index=2,
    help="Pilih jenis analisis yang ingin dilakukan"
)

# Maksimal tanggal analisis
use_max_date = st.sidebar.checkbox("Batasi Tanggal Analisis", value=False, 
                                 help="Aktifkan untuk membatasi analisis hingga tanggal tertentu")
if use_max_date:
    max_date = st.sidebar.date_input(
        "Maksimal Tanggal Analisis:",
        datetime.now() - timedelta(days=1),
        help="Analisis hanya akan menggunakan data hingga tanggal ini"
    )
    # Konversi date_input ke string format yang kompatibel
    max_date = pd.to_datetime(max_date)
else:
    max_date = None

col1, col2 = st.sidebar.columns(2)
with col1:
    period_years = st.number_input("Periode Data (tahun):", 0.5, 10.0, 3.0, step=0.5)
with col2:
    trail_length = st.number_input("Panjang Trail:", 1, 20, 12, 
                                  help="Jumlah periode terakhir yang ditampilkan pada grafik")

col3, col4 = st.sidebar.columns(2)
with col3:
    rs_ratio_period = st.number_input("Periode RS-Ratio:", 5, 100, 52, 
                                    help="Periode untuk perhitungan RS-Ratio (hari trading)")
with col4:
    rs_momentum_period = st.number_input("Periode RS-Momentum:", 3, 60, 26, 
                                       help="Periode untuk perhitungan RS-Momentum (hari trading)")

# Opsi untuk analisis fundamental
use_fundamental = st.sidebar.checkbox("Aktifkan Analisis Fundamental", 
                                    value=True if analysis_type in ["Fundamental", "Gabungan (Teknikal + Fundamental)"] else False)

if use_fundamental:
    # st.sidebar.info("Analisis fundamental akan mengambil data dari Yahoo Finance. Proses ini mungkin memerlukan waktu beberapa saat karena adanya pembatasan API.")
    
    refresh_fundamental = st.sidebar.checkbox("Refresh Data Fundamental", value=False, key="refresh_fundamental_key", 
                                            help="Aktifkan untuk memaksa refresh data fundamental dari Yahoo Finance")
    
    if use_fundamental:
        st.sidebar.info("Analisis fundamental akan mengambil data dari Yahoo Finance. Proses ini mungkin memerlukan waktu beberapa saat karena adanya pembatasan API.")

        # Tambahkan pengaturan untuk Stock Universe Score
        st.sidebar.subheader("Stock Universe Score")
        use_universe_score = st.sidebar.checkbox("Aktifkan Stock Universe Score", value=True)
        
        if use_universe_score:
            universe_score_input = st.sidebar.number_input(
                "Scoring Stock Universe (0-100):", 
                min_value=0, 
                max_value=100, 
                value=100,
                help="Masukkan skor kesehatan emiten (0-100) berdasarkan penilaian laba 3 tahun terakhir, total return, dan notasi bursa"
            )
        
        refresh_fundamental = st.sidebar.checkbox("Refresh Data Fundamental", value=False, 
                                               help="Aktifkan untuk memaksa refresh data fundamental dari Yahoo Finance")

    # Tambahkan indikator fundamental yang ingin disertakan
    st.sidebar.subheader("Indikator Fundamental")
    include_roe = st.sidebar.checkbox("Return on Equity (ROE)", value=True)
    include_roa = st.sidebar.checkbox("Return on Assets (ROA)", value=True)
    include_profit_margin = st.sidebar.checkbox("Profit Margin", value=True)
    include_earnings_growth = st.sidebar.checkbox("Earnings Growth", value=True)
    include_debt_equity = st.sidebar.checkbox("Debt to Equity", value=True)
    
    # Bobot untuk masing-masing indikator
    st.sidebar.subheader("Bobot Indikator Fundamental")
    roe_weight = st.sidebar.slider("ROE Weight:", 0, 100, 25, disabled=not include_roe)
    roa_weight = st.sidebar.slider("ROA Weight:", 0, 100, 20, disabled=not include_roa)
    pm_weight = st.sidebar.slider("Profit Margin Weight:", 0, 100, 20, disabled=not include_profit_margin)
    eg_weight = st.sidebar.slider("Earnings Growth Weight:", 0, 100, 20, disabled=not include_earnings_growth)
    de_weight = st.sidebar.slider("Debt/Equity Weight:", 0, 100, 15, disabled=not include_debt_equity)
    
    # Normalisasi bobot agar totalnya 100%
    total_weight = (roe_weight if include_roe else 0) + \
                  (roa_weight if include_roa else 0) + \
                  (pm_weight if include_profit_margin else 0) + \
                  (eg_weight if include_earnings_growth else 0) + \
                  (de_weight if include_debt_equity else 0)
    
    if total_weight > 0:
        roe_weight = roe_weight / total_weight if include_roe else 0
        roa_weight = roa_weight / total_weight if include_roa else 0
        pm_weight = pm_weight / total_weight if include_profit_margin else 0
        eg_weight = eg_weight / total_weight if include_earnings_growth else 0
        de_weight = de_weight / total_weight if include_debt_equity else 0

# Debug mode
debug_mode = st.sidebar.checkbox("Mode Debug", False)

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

# Tampilkan penjelasan Analisis Fundamental
with st.sidebar.expander("ℹ️ Tentang Analisis Fundamental"):
    st.write("""
    **Indikator yang Digunakan:**
    - **Return on Equity (ROE)**: Mengukur kemampuan perusahaan menghasilkan laba dari ekuitas pemegang saham
    - **Return on Assets (ROA)**: Mengukur seberapa efisien perusahaan menggunakan asetnya untuk menghasilkan laba
    - **Profit Margins**: Mengukur persentase pendapatan yang menjadi laba bersih
    - **Earnings Growth**: Pertumbuhan laba perusahaan
    - **Debt to Equity**: Mengukur berapa banyak hutang vs ekuitas yang digunakan perusahaan

    **Cara Membaca:**
    - Skor fundamental 0-100 menunjukkan kesehatan keuangan perusahaan
    - Skor gabungan menggabungkan skor fundamental dan RS-Momentum sesuai bobot yang ditentukan
    - Rekomendasi gabungan mempertimbangkan aspek teknikal dan fundamental
    """)

# Tampilkan penjelasan Analisis Gabungan
with st.sidebar.expander("ℹ️ Tentang Analisis Gabungan"):
    st.write("""
    **Indikator yang Digunakan:**
    - **Return on Equity (ROE)**: Mengukur kemampuan perusahaan menghasilkan laba dari ekuitas pemegang saham
    - **Return on Assets (ROA)**: Mengukur seberapa efisien perusahaan menggunakan asetnya untuk menghasilkan laba
    - **Profit Margins**: Mengukur persentase pendapatan yang menjadi laba bersih
    - **Earnings Growth**: Pertumbuhan laba perusahaan
    - **Debt to Equity**: Mengukur berapa banyak hutang vs ekuitas yang digunakan perusahaan
    
    **Stock Universe Score**:
    Penilaian manual (0-100) berdasarkan:
    - Laba positif 3 tahun terakhir
    - Total return (dividen + capital gain)
    - Notasi khusus di bursa
    
    **Cara Membaca:**
    - Skor gabungan menggabungkan:
      - 40% Stock Universe Score
      - 30% Skor fundamental
      - 30% RS-Momentum
    - Rekomendasi gabungan mempertimbangkan ketiga aspek di atas
    """)

# Fungsi untuk menyimpan file yang di-upload ke file sementara
def save_uploaded_file(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as f:
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
            
            # Jalankan analisis RRG
            progress_text = "Menganalisis data saham..."
            my_bar = st.progress(0, text=progress_text)
            
            # Step 1: Inisialisasi RRG Analyzer
            my_bar.progress(10, text="Inisialisasi analisis RRG...")
            rrg_analyzer = RRGAnalyzer(
                benchmark_file=benchmark_temp,
                stock_files=stock_temps,
                period_years=period_years,
                max_date=max_date
            )
            
            # Step 2: Load data
            my_bar.progress(20, text="Memuat data dari file CSV...")
            success = rrg_analyzer.load_data_from_files()
            if not success:
                st.error("Gagal memuat data dari file. Periksa format file CSV Anda.")
                my_bar.empty()
                # Clean up temp files
                os.unlink(benchmark_temp)
                for temp_file in stock_temps:
                    os.unlink(temp_file)
                st.stop()
            
            # Step 3: Hitung RS-Ratio
            my_bar.progress(30, text="Menghitung RS-Ratio...")
            rrg_analyzer.calculate_rs_ratio(period=rs_ratio_period)
            if not rrg_analyzer.rs_ratio:
                st.error("Gagal menghitung RS-Ratio. Mungkin tidak cukup data.")
                my_bar.empty()
                # Clean up temp files
                os.unlink(benchmark_temp)
                for temp_file in stock_temps:
                    os.unlink(temp_file)
                st.stop()
            
            # Step 4: Hitung RS-Momentum
            my_bar.progress(40, text="Menghitung RS-Momentum...")
            rrg_analyzer.calculate_rs_momentum(period=rs_momentum_period)
            if not rrg_analyzer.rs_momentum:
                st.error("Gagal menghitung RS-Momentum. Mungkin tidak cukup data.")
                my_bar.empty()
                # Clean up temp files
                os.unlink(benchmark_temp)
                for temp_file in stock_temps:
                    os.unlink(temp_file)
                st.stop()
            
            # Step 5: Normalisasi data
            my_bar.progress(50, text="Menormalisasi data...")
            success = rrg_analyzer.normalize_data()
            if not success:
                st.error("Gagal melakukan normalisasi data. Mungkin tidak cukup variasi dalam data.")
                my_bar.empty()
                # Clean up temp files
                os.unlink(benchmark_temp)
                for temp_file in stock_temps:
                    os.unlink(temp_file)
                st.stop()
            
            # Step 6: Dapatkan hasil RRG
            my_bar.progress(60, text="Mempersiapkan hasil RRG...")
            rrg_results = rrg_analyzer.get_latest_data()
            
            # Analisis Fundamental jika diaktifkan
            combined_results = None
            if use_fundamental and analysis_type in ["Fundamental", "Gabungan (Teknikal + Fundamental)"]:
                my_bar.progress(70, text="Menginisialisasi analisis fundamental...")
                
                # Konfigurasi analyzer fundamental dengan indikator dan bobot yang dipilih
                indicators = []
                weights = {}
                
                if include_roe:
                    indicators.append('returnOnEquity')
                    weights['returnOnEquity'] = roe_weight
                    
                if include_roa:
                    indicators.append('returnOnAssets')
                    weights['returnOnAssets'] = roa_weight
                    
                if include_profit_margin:
                    indicators.append('profitMargins')
                    weights['profitMargins'] = pm_weight
                    
                if include_earnings_growth:
                    indicators.append('earningsGrowth')
                    weights['earningsGrowth'] = eg_weight
                    
                if include_debt_equity:
                    indicators.append('debtToEquity')
                    weights['debtToEquity'] = de_weight
                
                fundamental_analyzer = FundamentalAnalyzer()
                
                # Set indikator dan bobot yang dipilih user
                if indicators:
                    fundamental_analyzer.fundamental_indicators = indicators
                    fundamental_analyzer.indicator_weights = weights
                
                # Ekstrak ticker dari hasil RRG
                tickers = rrg_results['Symbol'].tolist()
                
                my_bar.progress(80, text="Mengambil data fundamental dari Yahoo Finance...")
                fundamental_results = fundamental_analyzer.get_fundamental_analysis(tickers)
                
                my_bar.progress(90, text="Menggabungkan hasil analisis...")
                
                # Untuk menggunakan bobot tetap dan skor universe
                if use_fundamental:
                    # Tetapkan bobot tetap: 30% fundamental, 30% technical, 40% universe
                    fundamental_analyzer.technical_weight = 0.3
                    fundamental_analyzer.fundamental_weight = 0.3
                    
                    # Gabungkan hasil RRG dan fundamental
                    combined_results = fundamental_analyzer.combine_with_rrg(fundamental_results, rrg_results)
                    
                    # Tambahkan Stock Universe Score jika diaktifkan
                    if use_universe_score:
                        # Tambahkan kolom universe score
                        combined_results['Universe_Score'] = universe_score_input
                        
                        # Hitung skor gabungan baru dengan 3 komponen
                        combined_results['Combined_Score'] = (
                            combined_results['Universe_Score'] * 0.4 +
                            combined_results['Fundamental_Score'] * 0.3 +
                            combined_results['RS_Momentum_Normalized'] * 0.3
                        )
                        
                        # Update rekomendasi berdasarkan skor gabungan baru
                        def get_combined_recommendation(score):
                            if score >= 80:
                                return "Strong Buy"
                            elif score >= 65:
                                return "Buy"
                            elif score >= 50:
                                return "Hold"
                            elif score >= 35:
                                return "Reduce"
                            else:
                                return "Sell"
                        
                        combined_results['Combined_Recommendation'] = combined_results['Combined_Score'].apply(get_combined_recommendation)
                                         
            # Step 7: Selesai
            my_bar.progress(100, text="Analisis selesai!")
            time.sleep(0.5)  # Beri waktu user untuk melihat progress 100%
            my_bar.empty()
            
            # Clean up temp files
            os.unlink(benchmark_temp)
            for temp_file in stock_temps:
                os.unlink(temp_file)
            
            # Tampilkan hasil
            if (rrg_results is None or len(rrg_results) == 0) and combined_results is None:
                st.error("Tidak dapat melakukan analisis. Pastikan data tersedia dan parameter sudah benar.")
            else:
                # Tampilkan tanggal analisis aktual
                analysis_date = rrg_analyzer.get_analysis_date().strftime('%d %B %Y')
                st.subheader(f"Analisis pada tanggal: {analysis_date}")
                
                # Bagi layar menjadi dua kolom
                col_chart, col_table = st.columns([2, 1])
                
                with col_chart:
                    if analysis_type == "RRG (Teknikal)" or not use_fundamental:
                        # Tampilkan grafik RRG saja
                        st.subheader("Relative Rotation Graph (RRG)")
                        fig = rrg_analyzer.plot_rrg(trail_length=trail_length)
                        st.pyplot(fig)
                    elif analysis_type == "Fundamental" and use_fundamental:
                        # Tampilkan grafik Fundamental vs RS-Ratio
                        st.subheader("Fundamental Analysis")
                        fig, ax = plt.subplots(figsize=(10, 8))
                        
                        # Gunakan market cap untuk ukuran jika tersedia
                        if 'marketCap' in combined_results.columns:
                            sizes = combined_results['marketCap'].apply(lambda x: 
                                max(100, min(1000, (np.log10(x+1) * 100) if x is not None else 100)))
                        else:
                            sizes = 200
                        
                        # Gunakan sektor untuk warna jika tersedia
                        if 'sector' in combined_results.columns:
                            sectors = combined_results['sector'].fillna('Unknown').unique()
                            sector_codes = {sector: i for i, sector in enumerate(sectors)}
                            colors = combined_results['sector'].fillna('Unknown').map(sector_codes)
                            
                            scatter = ax.scatter(
                                combined_results['RS-Ratio'], 
                                combined_results['Fundamental_Score'],
                                s=sizes, 
                                c=colors,
                                alpha=0.7, 
                                cmap='tab10'
                            )
                            
                            # Tambahkan legend untuk sektor
                            legend_elements = [plt.Line2D([0], [0], marker='o', color='w', 
                                                       label=sector, 
                                                       markerfacecolor=plt.cm.tab10(sector_codes[sector] / len(sectors)), 
                                                       markersize=8) 
                                            for sector in sectors]
                            ax.legend(handles=legend_elements, title="Sektor", loc="upper left")
                        else:
                            scatter = ax.scatter(
                                combined_results['RS-Ratio'], 
                                combined_results['Fundamental_Score'],
                                s=sizes,
                                alpha=0.7, 
                                color='blue'
                            )
                        
                        # Tambahkan label ticker
                        for idx, row in combined_results.iterrows():
                            # Cek apakah Universe_Score tersedia
                            if 'Universe_Score' in row:
                                label_text = f"{row['Symbol']}: U={row['Universe_Score']:.0f}, F={row['Fundamental_Score']:.0f}"
                            else:
                                label_text = row['Symbol']
                                
                            ax.annotate(
                                label_text,
                                (row['RS-Ratio'], row['Fundamental_Score']),
                                xytext=(5, 5),
                                textcoords='offset points',
                                fontsize=9
                            )
                        
                        # Tambahkan garis pembatas
                        ax.axhline(y=70, color='green', linestyle='--', alpha=0.5)
                        ax.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
                        ax.axhline(y=30, color='red', linestyle='--', alpha=0.5)
                        
                        # Tambahkan garis vertikal di nilai 100 (garis tengah RS-Ratio)
                        ax.axvline(x=100, color='gray', linestyle='-', alpha=0.3)
                        ax.set_title('Fundamental Score vs RS-Ratio', fontsize=14)
                        ax.set_xlabel('RS-Ratio (Technical Strength)', fontsize=12)
                        ax.set_ylabel('Fundamental Score', fontsize=12)
                        
                        # Tambahkan grid
                        ax.grid(True, alpha=0.3)
                        
                        # Set interval sumbu y dari 0-100
                        ax.set_ylim(0, 100)
                        
                        st.pyplot(fig)
                    else:
                        # Gabungan
                        # Tampilkan grafik Gabungan
                        st.subheader("Combined Technical & Fundamental Analysis")
                        fig = fundamental_analyzer.plot_combined_analysis(combined_results)
                        st.pyplot(fig)
                
                with col_table:
                    # Tampilkan hasil dalam tabel
                    if analysis_type == "RRG (Teknikal)" or not use_fundamental:
                        st.subheader("Hasil Analisis Teknikal")
                        results_to_show = rrg_results
                    elif analysis_type == "Fundamental" and use_fundamental:
                        st.subheader("Hasil Analisis Fundamental")
                        # Pilih kolom yang ingin ditampilkan
                        columns_to_show = ['Symbol', 'Fundamental_Score']
                        for indicator in fundamental_analyzer.fundamental_indicators:
                            if indicator in combined_results.columns:
                                columns_to_show.append(indicator)
                        
                        if 'longName' in combined_results.columns:
                            columns_to_show.insert(1, 'longName')
                        if 'sector' in combined_results.columns:
                            columns_to_show.append('sector')
                        if 'industry' in combined_results.columns:
                            columns_to_show.append('industry')
                        
                        results_to_show = combined_results[columns_to_show]
                    else:
                        # Gabungan
                        st.subheader("Hasil Analisis Gabungan")
                        # Pilih kolom yang ingin ditampilkan
                        columns_to_show = ['Symbol', 'RS-Ratio', 'RS-Momentum', 'Quadrant']

                        # Jika menggunakan Universe Score
                        if use_universe_score:
                            columns_to_show.append('Universe_Score')

                        # Tambahkan kolom fundamental dan kombinasi
                        columns_to_show.extend(['Fundamental_Score', 'Combined_Score', 'Combined_Recommendation'])
                        
                        if 'longName' in combined_results.columns:
                            columns_to_show.insert(1, 'longName')
                        
                        results_to_show = combined_results[columns_to_show]
                    
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
                    
                    def highlight_recommendation(val):
                        if val == "Strong Buy":
                            return 'background-color: rgba(0, 128, 0, 0.3)'
                        elif val == "Buy":
                            return 'background-color: rgba(144, 238, 144, 0.3)'
                        elif val == "Hold":
                            return 'background-color: rgba(211, 211, 211, 0.3)'
                        elif val == "Reduce":
                            return 'background-color: rgba(255, 165, 0, 0.3)'
                        elif val == "Sell":
                            return 'background-color: rgba(255, 0, 0, 0.3)'
                        return ''
                    
                    # Format numerik untuk kolom
                    format_dict = {
                        'RS-Ratio': '{:.2f}',
                        'RS-Momentum': '{:.2f}',
                        'Fundamental_Score': '{:.2f}',
                        'Combined_Score': '{:.2f}',
                        'returnOnEquity': '{:.2%}',
                        'returnOnAssets': '{:.2%}',
                        'profitMargins': '{:.2%}',
                        'earningsGrowth': '{:.2%}',
                        'debtToEquity': '{:.2f}'
                    }
                    
                    # Buat salinan data untuk menghindari warning
                    results_to_show_copy = results_to_show.copy()

                    # Format tabel untuk ditampilkan
                    styled_table = results_to_show_copy.style

                    # Terapkan format numerik pada kolom yang ada
                    for col, fmt in format_dict.items():
                        if col in results_to_show_copy.columns:
                            if any(pd.isna(results_to_show_copy[col])):
                                # Jika ada nilai NaN di kolom, gunakan na_rep='N/A'
                                styled_table = styled_table.format({col: fmt}, na_rep='N/A')
                            else:
                                styled_table = styled_table.format({col: fmt})
                    
                    # Terapkan highlight pada kolom yang ada
                    if 'Quadrant' in results_to_show.columns:
                        styled_table = styled_table.map(highlight_quadrant, subset=['Quadrant'])
                    
                    if 'Combined_Recommendation' in results_to_show.columns:
                        styled_table = styled_table.map(highlight_recommendation, subset=['Combined_Recommendation'])
                    
                    # Tampilkan tabel dengan format
                    st.dataframe(styled_table)
                    
                    # Opsi untuk mengunduh hasil analisis
                    csv = results_to_show.to_csv(index=False)
                    st.download_button(
                        label="📥 Unduh Hasil Analisis (CSV)",
                        data=csv,
                        file_name=f"stock_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                
                # Tampilkan ringkasan berdasarkan jenis analisis
                if analysis_type == "RRG (Teknikal)" or not use_fundamental:
                    # Tampilkan ringkasan RRG
                    st.subheader("Ringkasan per Kuadran")
                    # Buat 4 kolom untuk 4 kuadran
                    col_leading, col_improving, col_weakening, col_lagging = st.columns(4)
                    
                    with col_leading:
                        st.markdown("### Leading 📈")
                        leading_stocks = rrg_results[rrg_results['Quadrant'] == 'Leading']['Symbol'].tolist()
                        if leading_stocks:
                            for stock in leading_stocks:
                                st.markdown(f"- {stock}")
                        else:
                            st.markdown("*Tidak ada saham pada kuadran ini*")
                    
                    with col_improving:
                        st.markdown("### Improving 🌱")
                        improving_stocks = rrg_results[rrg_results['Quadrant'] == 'Improving']['Symbol'].tolist()
                        if improving_stocks:
                            for stock in improving_stocks:
                                st.markdown(f"- {stock}")
                        else:
                            st.markdown("*Tidak ada saham pada kuadran ini*")
                    
                    with col_weakening:
                        st.markdown("### Weakening ⚠️")
                        weakening_stocks = rrg_results[rrg_results['Quadrant'] == 'Weakening']['Symbol'].tolist()
                        if weakening_stocks:
                            for stock in weakening_stocks:
                                st.markdown(f"- {stock}")
                        else:
                            st.markdown("*Tidak ada saham pada kuadran ini*")
                    
                    with col_lagging:
                        st.markdown("### Lagging 📉")
                        lagging_stocks = rrg_results[rrg_results['Quadrant'] == 'Lagging']['Symbol'].tolist()
                        if lagging_stocks:
                            for stock in lagging_stocks:
                                st.markdown(f"- {stock}")
                        else:
                            st.markdown("*Tidak ada saham pada kuadran ini*")
                
                elif analysis_type == "Fundamental" and use_fundamental:
                    # Tampilkan ringkasan Fundamental
                    st.subheader("Ringkasan Fundamental")
                    # Buat 3 kolom untuk kategori fundamental
                    col_strong, col_average, col_weak = st.columns(3)
                    
                    with col_strong:
                        st.markdown("### Kuat (Skor > 70) 💪")
                        strong_stocks = combined_results[combined_results['Fundamental_Score'] > 70]['Symbol'].tolist()
                        if strong_stocks:
                            for stock in strong_stocks:
                                score = combined_results[combined_results['Symbol'] == stock]['Fundamental_Score'].values[0]
                                st.markdown(f"- {stock}: {score:.2f}")
                        else:
                            st.markdown("*Tidak ada saham dalam kategori ini*")
                    
                    with col_average:
                        st.markdown("### Rata-rata (Skor 40-70) ⚖️")
                        avg_stocks = combined_results[(combined_results['Fundamental_Score'] > 40) & 
                                                    (combined_results['Fundamental_Score'] <= 70)]['Symbol'].tolist()
                        if avg_stocks:
                            for stock in avg_stocks:
                                score = combined_results[combined_results['Symbol'] == stock]['Fundamental_Score'].values[0]
                                st.markdown(f"- {stock}: {score:.2f}")
                        else:
                            st.markdown("*Tidak ada saham dalam kategori ini*")
                    
                    with col_weak:
                        st.markdown("### Lemah (Skor ≤ 40) ⚠️")
                        weak_stocks = combined_results[combined_results['Fundamental_Score'] <= 40]['Symbol'].tolist()
                        if weak_stocks:
                            for stock in weak_stocks:
                                score = combined_results[combined_results['Symbol'] == stock]['Fundamental_Score'].values[0]
                                st.markdown(f"- {stock}: {score:.2f}")
                        else:
                            st.markdown("*Tidak ada saham dalam kategori ini*")
                
                else:
                    # Gabungan
                    # Tampilkan ringkasan Gabungan
                    st.subheader("Ringkasan Rekomendasi Gabungan")
                    # Buat 5 kolom untuk rekomendasi gabungan
                    col_sbuy, col_buy, col_hold, col_reduce, col_sell = st.columns(5)
                    
                    with col_sbuy:
                        st.markdown("### Strong Buy 🔥")
                        sbuy_stocks = combined_results[combined_results['Combined_Recommendation'] == 'Strong Buy']['Symbol'].tolist()
                        if sbuy_stocks:
                            for stock in sbuy_stocks:
                                score = combined_results[combined_results['Symbol'] == stock]['Combined_Score'].values[0]
                                st.markdown(f"- {stock}: {score:.2f}")
                        else:
                            st.markdown("*Tidak ada saham dalam kategori ini*")
                    
                    with col_buy:
                        st.markdown("### Buy 📈")
                        buy_stocks = combined_results[combined_results['Combined_Recommendation'] == 'Buy']['Symbol'].tolist()
                        if buy_stocks:
                            for stock in buy_stocks:
                                score = combined_results[combined_results['Symbol'] == stock]['Combined_Score'].values[0]
                                st.markdown(f"- {stock}: {score:.2f}")
                        else:
                            st.markdown("*Tidak ada saham dalam kategori ini*")
                    
                    with col_hold:
                        st.markdown("### Hold ⚖️")
                        hold_stocks = combined_results[combined_results['Combined_Recommendation'] == 'Hold']['Symbol'].tolist()
                        if hold_stocks:
                            for stock in hold_stocks:
                                score = combined_results[combined_results['Symbol'] == stock]['Combined_Score'].values[0]
                                st.markdown(f"- {stock}: {score:.2f}")
                        else:
                            st.markdown("*Tidak ada saham dalam kategori ini*")
                    
                    with col_reduce:
                        st.markdown("### Reduce ⚠️")
                        reduce_stocks = combined_results[combined_results['Combined_Recommendation'] == 'Reduce']['Symbol'].tolist()
                        if reduce_stocks:
                            for stock in reduce_stocks:
                                score = combined_results[combined_results['Symbol'] == stock]['Combined_Score'].values[0]
                                st.markdown(f"- {stock}: {score:.2f}")
                        else:
                            st.markdown("*Tidak ada saham dalam kategori ini*")
                    
                    with col_sell:
                        st.markdown("### Sell 📉")
                        sell_stocks = combined_results[combined_results['Combined_Recommendation'] == 'Sell']['Symbol'].tolist()
                        if sell_stocks:
                            for stock in sell_stocks:
                                score = combined_results[combined_results['Symbol'] == stock]['Combined_Score'].values[0]
                                st.markdown(f"- {stock}: {score:.2f}")
                        else:
                            st.markdown("*Tidak ada saham dalam kategori ini*")
                
                # Tambahkan catatan tentang data fundamental
                if use_fundamental:
                    st.markdown("---")
                    st.markdown("""
                    **Catatan tentang Data Fundamental:**
                    - Data fundamental diambil dari Yahoo Finance dan mungkin tidak selalu tersedia atau terbaru untuk semua emiten
                    - Anda dapat melakukan refresh data fundamental dengan mencentang opsi "Refresh Data Fundamental" di sidebar
                    - Skor fundamental dihitung berdasarkan indikator yang Anda pilih dengan bobot yang telah ditentukan
                    """)

                # tombol untuk generate report
                st.markdown("---")
                st.subheader("📄 Generate Report")

                if st.button("📊 Generate PDF Report", type="primary"):
                    # Panggil fungsi untuk membuat laporan PDF
                    create_and_download_report(
                        combined_results if combined_results is not None else rrg_results, 
                        analysis_type,
                        use_fundamental,
                        use_universe_score if 'use_universe_score' in locals() else False
                    )
                
        except Exception as e:
            st.error(f"Terjadi kesalahan dalam analisis: {str(e)}")
            if debug_mode:
                st.error(f"Detail error: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
            
            # Clean up temp files
            if 'benchmark_temp' in locals() and os.path.exists(benchmark_temp):
                os.unlink(benchmark_temp)
            if 'stock_temps' in locals():
                for temp_file in stock_temps:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
            else: # Tampilkan info default ketika aplikasi pertama kali dibuka st.info("👈 Upload file CSV di panel sebelah kiri dan atur parameter, lalu klik 'Jalankan Analisis'.")
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

                # Tampilkan informasi analisis fundamental
                with st.expander("📝 Analisis Gabungan Teknikal & Fundamental"):
                    st.markdown("""
                    ### Tentang Analisis Gabungan
                    
                    Aplikasi ini menggabungkan dua pendekatan analisis:
                    
                    1. **Analisis Teknikal (RRG)**: Menganalisis pergerakan harga saham relatif terhadap benchmark
                       - RS-Ratio: Mengukur kekuatan relatif saham dibandingkan benchmark
                       - RS-Momentum: Mengukur momentum pergerakan saham
                    
                    2. **Analisis Fundamental**: Menilai kesehatan keuangan perusahaan
                       - Return on Equity (ROE): Mengukur efisiensi penggunaan modal
                       - Return on Assets (ROA): Mengukur efisiensi penggunaan aset
                       - Profit Margin: Mengukur kemampuan menghasilkan laba dari pendapatan
                       - Earnings Growth: Pertumbuhan laba
                       - Debt to Equity Ratio: Mengukur tingkat hutang
                    
                    ### Skor Gabungan
                    
                    **Catatan Analisis Gabungan:**
                    - Data fundamental diambil dari Yahoo Finance dan mungkin tidak selalu tersedia atau terbaru
                    - Stock Universe Score adalah input manual (0-100) berdasarkan penilaian laba 3 tahun terakhir, total return, dan notasi bursa
                    - Skor gabungan dihitung dengan bobot:
                      - 40% Stock Universe Score
                      - 30% Skor Fundamental
                      - 30% Skor RS-Momentum (Technical)
                    
                    Rekomendasi didasarkan pada skor gabungan:
                    - **Strong Buy** (80-100): Fundamental kuat dan momentum teknikal positif
                    - **Buy** (65-80): Fundamental dan teknikal cukup baik
                    - **Hold** (50-65): Performa cukup stabil
                    - **Reduce** (35-50): Menunjukkan kelemahan
                    - **Sell** (0-35): Fundamental lemah dan teknikal negatif
                    """)
# Footer
st.markdown("---")
st.markdown("Dibuat dengan ❤️ oleh Himawan Susetyo menggunakan Python dan Streamlit | © 2025")
