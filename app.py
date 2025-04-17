import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time
import numpy as np
from report import create_and_download_report
from analysis_engine import AnalysisEngine

# Inisialisasi session state untuk menyimpan hasil analisis
if 'has_analyzed' not in st.session_state:
    st.session_state.has_analyzed = False
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'combined_results' not in st.session_state:
    st.session_state.combined_results = None
if 'rrg_results' not in st.session_state:
    st.session_state.rrg_results = None
if 'analysis_type' not in st.session_state:
    st.session_state.analysis_type = None
if 'use_fundamental' not in st.session_state:
    st.session_state.use_fundamental = False
if 'use_universe_score' not in st.session_state:
    st.session_state.use_universe_score = False
if 'analysis_date' not in st.session_state:
    st.session_state.analysis_date = None

# Konfigurasi halaman
st.set_page_config(
    page_title="Comprehensive Stock Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Judul aplikasi
st.title("📊 Comprehensive Stock Analyzer")

st.markdown("""
Aplikasi ini menganalisis saham dari dua perspektif:
1. **Teknikal**: Kinerja relatif saham dibandingkan benchmark menggunakan metode Relative Rotation Graph (RRG)
2. **Fundamental**: Kesehatan keuangan perusahaan berdasarkan data dari Yahoo Finance
""")

# ------------------ SIDEBAR ------------------
def create_sidebar():
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
    use_max_date = st.sidebar.checkbox(
        "Batasi Tanggal Analisis", 
        value=False,
        help="Aktifkan untuk membatasi analisis hingga tanggal tertentu"
    )
    
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
    
    # Parameter periode
    col1, col2 = st.sidebar.columns(2)
    with col1:
        period_years = st.number_input(
            "Periode Data (tahun):", 
            0.5, 10.0, 3.0, 
            step=0.5
        )
    with col2:
        trail_length = st.number_input(
            "Panjang Trail:", 
            1, 20, 12,
            help="Jumlah periode terakhir yang ditampilkan pada grafik"
        )
    
    # Parameter RS-Ratio dan RS-Momentum
    col3, col4 = st.sidebar.columns(2)
    with col3:
        rs_ratio_period = st.number_input(
            "Periode RS-Ratio:", 
            5, 100, 52,
            help="Periode untuk perhitungan RS-Ratio (hari trading)"
        )
    with col4:
        rs_momentum_period = st.number_input(
            "Periode RS-Momentum:", 
            3, 60, 26,
            help="Periode untuk perhitungan RS-Momentum (hari trading)"
        )
    
    # Opsi untuk analisis fundamental
    use_fundamental = st.sidebar.checkbox(
        "Aktifkan Analisis Fundamental",
        value=True if analysis_type in ["Fundamental", "Gabungan (Teknikal + Fundamental)"] else False
    )
    
    fundamental_params = {}
    
    if use_fundamental:
        st.sidebar.info("Analisis fundamental akan mengambil data dari Yahoo Finance. Proses ini mungkin memerlukan waktu beberapa saat karena adanya pembatasan API.")
        
        # Stock Universe Score
        st.sidebar.subheader("Stock Universe Score")
        use_universe_score = st.sidebar.checkbox("Aktifkan Stock Universe Score", value=True)
        
        universe_score_input = 50
        if use_universe_score:
            universe_score_input = st.sidebar.number_input(
                "Scoring Stock Universe (0-100):", 
                min_value=0, 
                max_value=100, 
                value=50,
                help="Masukkan skor kesehatan emiten (0-100) berdasarkan penilaian laba 3 tahun terakhir, total return, dan notasi bursa"
            )
        
        # Refresh data fundamental
        refresh_fundamental = st.sidebar.checkbox(
            "Refresh Data Fundamental", 
            value=False, 
            key="refresh_fundamental_key",
            help="Aktifkan untuk memaksa refresh data fundamental dari Yahoo Finance"
        )
        
        # Indikator fundamental
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
        
        # Simpan parameter untuk analisis fundamental
        fundamental_params = {
            'refresh_fundamental': refresh_fundamental,
            'include_roe': include_roe,
            'include_roa': include_roa,
            'include_profit_margin': include_profit_margin,
            'include_earnings_growth': include_earnings_growth,
            'include_debt_equity': include_debt_equity,
            'roe_weight': roe_weight,
            'roa_weight': roa_weight,
            'pm_weight': pm_weight,
            'eg_weight': eg_weight,
            'de_weight': de_weight
        }
    
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
    
    # Tambahkan expander untuk menjelaskan RRG, Fundamental dan Analisis Gabungan
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
    
    with st.sidebar.expander("ℹ️ Tentang Analisis Gabungan"):
        st.write("""
        **Indikator yang Digunakan:**
        - **Return on Equity (ROE)**: Mengukur kemampuan perusahaan menghasilkan laba dari ekuitas pemegang saham
        - **Return on Assets (ROA)**: Mengukur seberapa efisien perusahaan menggunakan asetnya untuk menghasilkan laba
        - **Profit Margins**: Mengukur persentase pendapatan yang menjadi laba bersih
        - **Earnings Growth**: Pertumbuhan laba perusahaan
        - **Debt to Equity**: Mengukur berapa banyak hutang vs ekuitas yang digunakan perusahaan

        **Stock Universe Score**: Penilaian manual (0-100) berdasarkan:
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
    
    # Mengumpulkan semua parameter yang diperlukan untuk analisis
    analysis_params = {
        'period_years': period_years,
        'trail_length': trail_length,
        'rs_ratio_period': rs_ratio_period,
        'rs_momentum_period': rs_momentum_period,
        'max_date': max_date,
        'analysis_type': analysis_type,
        'use_fundamental': use_fundamental,
        'use_universe_score': use_universe_score,
        'universe_score_input': universe_score_input,
        'debug_mode': debug_mode,
        **fundamental_params
    }
    
    return benchmark_file, stock_files, analysis_params, analyze_button

# ------------------ FUNGSI ANALISIS ------------------
def run_analysis(benchmark_file, stock_files, analysis_params):
    if benchmark_file is None:
        st.error("Silakan upload file benchmark terlebih dahulu.")
        return
    
    if not stock_files:
        st.error("Silakan upload setidaknya satu file saham.")
        return
    
    # Tampilkan progress bar
    progress_text = "Menganalisis data saham..."
    my_bar = st.progress(0, text=progress_text)
    
    try:
        # Inisialisasi engine analisis
        engine = AnalysisEngine()
        
        # Tampilkan progress bertahap
        for i, step in enumerate([
            "Inisialisasi analisis...",
            "Memuat data dari file...",
            "Menghitung RS-Ratio...",
            "Menghitung RS-Momentum...",
            "Normalisasi data...",
            "Analisis fundamental...",
            "Menggabungkan hasil...",
            "Menyelesaikan analisis..."
        ]):
            my_bar.progress((i+1) * 12, text=step)
            time.sleep(0.3)  # Berikan sedikit waktu untuk animasi
        
        # Jalankan analisis
        success, message, results = engine.run_analysis(benchmark_file, stock_files, analysis_params)
        
        # Update progress bar
        my_bar.progress(100, text="Analisis selesai!")
        time.sleep(0.5)  # Berikan waktu untuk animasi 100%
        my_bar.empty()
        
        if not success:
            st.error(message)
            return
        
        # Simpan hasil ke session state
        st.session_state.has_analyzed = True
        st.session_state.rrg_results = results['rrg_results']
        st.session_state.combined_results = results['combined_results']
        st.session_state.analysis_type = results['analysis_type']
        st.session_state.use_fundamental = results['use_fundamental']
        st.session_state.use_universe_score = results['use_universe_score']
        st.session_state.analysis_date = results['analysis_date']
        
        # Muat hasil untuk ditampilkan
        display_results()
        
    except Exception as e:
        my_bar.empty()
        st.error(f"Terjadi kesalahan: {str(e)}")
        if analysis_params.get('debug_mode', False):
            import traceback
            st.code(traceback.format_exc())

# ------------------ FUNGSI DISPLAY RESULTS ------------------
def display_results():
    if not st.session_state.has_analyzed:
        return
    
    # Ambil data dari session state
    rrg_results = st.session_state.rrg_results
    combined_results = st.session_state.combined_results
    analysis_type = st.session_state.analysis_type
    use_fundamental = st.session_state.use_fundamental
    use_universe_score = st.session_state.use_universe_score
    analysis_date = st.session_state.analysis_date
    
    # Tampilkan tanggal analisis
    st.subheader(f"Analisis pada tanggal: {analysis_date}")
    
    # Bagi layar menjadi dua kolom
    col_chart, col_table = st.columns([2, 1])
    
    # Import modul untuk plotting
    try:
        from rrg import RRGAnalyzer
        if use_fundamental:
            from fundamental_analyzer import FundamentalAnalyzer
    except Exception as e:
        st.error(f"Error mengimpor modul: {str(e)}")
        return
    
    # Tampilkan visualisasi
    with col_chart:
        if analysis_type == "RRG (Teknikal)" or not use_fundamental:
            # Tampilkan grafik RRG saja
            st.subheader("Relative Rotation Graph (RRG)")
            
            # Buat instance kosong untuk plotting
            rrg_analyzer = RRGAnalyzer()
            # Setel data yang diperlukan untuk plotting
            rrg_analyzer.normalized_data = rrg_results
            
            # Plot
            fig = rrg_analyzer.plot_rrg(trail_length=12)
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
            
            fundamental_analyzer = FundamentalAnalyzer()
            fig = fundamental_analyzer.plot_combined_analysis(combined_results)
            st.pyplot(fig)
    
    # Tampilkan tabel hasil
    with col_table:
        if analysis_type == "RRG (Teknikal)" or not use_fundamental:
            st.subheader("Hasil Analisis Teknikal")
            results_to_show = rrg_results
        elif analysis_type == "Fundamental" and use_fundamental:
            st.subheader("Hasil Analisis Fundamental")
            
            # Pilih kolom yang ingin ditampilkan
            columns_to_show = ['Symbol', 'Fundamental_Score']
            
            if use_fundamental:
                fundamental_analyzer = FundamentalAnalyzer()
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
        
        # Formatting tabel
        format_and_display_table(results_to_show)
        
        # Opsi untuk mengunduh hasil analisis
        csv = results_to_show.to_csv(index=False)
        st.download_button(
            label="📥 Unduh Hasil Analisis (CSV)",
            data=csv,
            file_name=f"stock_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    # Tampilkan ringkasan
    display_summary(rrg_results, combined_results, analysis_type, use_fundamental, use_universe_score)
    
    # Tambahkan catatan tentang data fundamental
    if use_fundamental:
        st.markdown("---")
        st.markdown("""
        **Catatan tentang Data Fundamental:**
        - Data fundamental diambil dari Yahoo Finance dan mungkin tidak selalu tersedia atau terbaru untuk semua emiten
        - Anda dapat melakukan refresh data fundamental dengan mencentang opsi "Refresh Data Fundamental" di sidebar
        - Skor fundamental dihitung berdasarkan indikator yang Anda pilih dengan bobot yang telah ditentukan
        """)
    
    # Tambahkan tombol untuk generate report
    display_report_button()

# Fungsi formatting tabel
def format_and_display_table(results_to_show):
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
        'Universe_Score': '{:.2f}',
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

# Fungsi menampilkan ringkasan
def display_summary(rrg_results, combined_results, analysis_type, use_fundamental, use_universe_score):
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

# Fungsi Generate Report
def display_report_button():
    st.markdown("---")
    st.subheader("📄 Generate Report")
    
    report_col1, report_col2 = st.columns([1, 1])
    
    with report_col1:
        html_report = st.button("🌐 Open HTML Report", type="primary", key="html_report")
    
    with report_col2:
        pdf_report = st.button("📄 Download PDF Report", key="pdf_report")
    
    if html_report:
        # Tampilkan indikator proses
        report_progress = st.progress(0, text="Mempersiapkan laporan HTML...")
        
        # Buat placeholder untuk pesan status
        status_placeholder = st.empty()
        status_placeholder.info("Membuat laporan HTML, mohon tunggu...")
        
        try:
            # Update progress
            report_progress.progress(30, text="Mengumpulkan data analisis...")
            time.sleep(0.5)
            
            report_progress.progress(60, text="Membuat visualisasi...")
            time.sleep(0.5)
            
            report_progress.progress(90, text="Menyusun laporan...")
            
            # Import modul report_html
            from report_html import create_html_report
            
            # Buat laporan HTML
            html_content, filename = create_html_report(
                st.session_state.combined_results if st.session_state.combined_results is not None else st.session_state.rrg_results,
                st.session_state.analysis_type,
                st.session_state.use_fundamental,
                st.session_state.use_universe_score
            )
            
            # Update progress ke 100% menandakan selesai
            report_progress.progress(100, text="Laporan selesai!")
            time.sleep(0.5)
            
            # Hapus progress bar
            report_progress.empty()
            
            # Gunakan HTML display untuk menampilkan laporan
            # Simpan HTML ke file sementara dan buka di tab baru
            import tempfile
            import webbrowser
            import os
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w') as f:
                f.write(html_content)
                temp_html_path = f.name
            
            # Buka file HTML di browser default
            #webbrowser.open('file://' + os.path.realpath(temp_html_path), new=2)
            with open(temp_html_path, "r") as f:
                html_content = f.read()

            # Tampilkan tombol download HTML
            st.download_button(
                label="📥 Download HTML Report",
                data=html_content,
                file_name=filename,
                mime="text/html",
                key="download_html_report"
            )

            # Opsional: Tambahkan instruksi
            st.info("Setelah mengunduh file HTML, buka di browser Anda lalu gunakan fitur 'Print' atau 'Save as PDF' di browser.")
            
            # Update pesan status
            status_placeholder.success("✅ Laporan HTML berhasil dibuat dan dibuka di tab browser baru!")
            
        except Exception as e:
            # Jika terjadi error, tampilkan pesan error
            report_progress.empty()
            status_placeholder.error(f"❌ Terjadi kesalahan saat membuat laporan: {str(e)}")
            st.error(f"Detail error: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
    
    if pdf_report:
        # Tampilkan indikator proses
        report_progress = st.progress(0, text="Mempersiapkan laporan PDF...")
        
        # Buat placeholder untuk pesan status
        status_placeholder = st.empty()
        status_placeholder.info("Membuat laporan PDF, mohon tunggu...")
        
        try:
            # Update progress
            report_progress.progress(30, text="Mengumpulkan data analisis...")
            time.sleep(0.5)
            
            report_progress.progress(60, text="Membuat visualisasi...")
            time.sleep(0.5)
            
            report_progress.progress(90, text="Menyusun laporan...")
            
            # Gunakan create_and_download_report dari report.py untuk PDF
            create_and_download_report(
                st.session_state.combined_results if st.session_state.combined_results is not None else st.session_state.rrg_results,
                st.session_state.analysis_type,
                st.session_state.use_fundamental,
                st.session_state.use_universe_score
            )
            
            # Update progress ke 100% menandakan selesai
            report_progress.progress(100, text="Laporan selesai!")
            time.sleep(0.5)
            
            # Hapus progress bar setelah selesai
            report_progress.empty()
            
            # Update pesan status
            status_placeholder.success("✅ Laporan PDF berhasil dibuat! Klik tombol download di bawah untuk mengunduh.")
        
        except Exception as e:
            # Jika terjadi error, tampilkan pesan error
            report_progress.empty()
            status_placeholder.error(f"❌ Terjadi kesalahan saat membuat laporan: {str(e)}")
            st.error(f"Detail error: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

# Tampilkan info default dan contoh format file CSV
def display_default_info():
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

# ------------------ MAIN APP ------------------
def main():
    # Buat sidebar untuk pengaturan
    benchmark_file, stock_files, analysis_params, analyze_button = create_sidebar()
    
    # Jika tombol analisis ditekan, jalankan analisis
    if analyze_button:
        run_analysis(benchmark_file, stock_files, analysis_params)
    # Jika sudah ada hasil analisis sebelumnya, tampilkan
    elif st.session_state.has_analyzed:
        display_results()
    # Jika belum ada analisis, tampilkan info default
    else:
        display_default_info()
    
    # Footer
    st.markdown("---")
    st.markdown("Dibuat dengan ❤️ oleh Himawan Susetyo menggunakan Python dan Streamlit | © 2025")

if __name__ == "__main__":
    main()
