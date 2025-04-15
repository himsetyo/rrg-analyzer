import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import time
from datetime import datetime

# Konfigurasi halaman
st.set_page_config(
    page_title="RRG Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import kelas RRGAnalyzer dari file rrg.py
from rrg import RRGAnalyzer

# Judul aplikasi
st.title("📊 Relative Rotation Graph (RRG) Analyzer")

st.markdown("""
Aplikasi ini menganalisis kinerja relatif saham-saham dalam portofolio Anda 
dibandingkan dengan benchmark menggunakan metode Relative Rotation Graph (RRG).
""")

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

# Fungsi cache untuk mengunduh data
@st.cache_data(ttl=3600)  # Cache selama 1 jam
def get_analysis(benchmark, stocks, period_years, rs_ratio_period, rs_momentum_period):
    analyzer = RRGAnalyzer(benchmark, stocks, period_years)
    
    with st.spinner("Mengunduh data saham..."):
        analyzer.download_data()
    
    with st.spinner("Menghitung RS-Ratio..."):
        analyzer.calculate_rs_ratio(period=rs_ratio_period)
    
    with st.spinner("Menghitung RS-Momentum..."):
        analyzer.calculate_rs_momentum(period=rs_momentum_period)
    
    with st.spinner("Menormalisasi data..."):
        analyzer.normalize_data()
    
    results = analyzer.get_latest_data()
    
    return analyzer, results

# Di app.py
@st.cache_data(ttl=3600)
def download_single_stock(symbol, start_date, end_date):
    try:
        return yf.download(symbol, start=start_date, end=end_date, progress=False)
    except Exception as e:
        st.warning(f"Tidak dapat mengunduh data untuk {symbol}: {e}")
        return pd.DataFrame()

# Input parameter di sidebar
st.sidebar.header("Parameter Input")

benchmark = st.sidebar.text_input("Benchmark Symbol:", "^JKSE", help="Contoh: ^JKSE untuk IHSG, ^GSPC untuk S&P 500")

stocks_input = st.sidebar.text_area(
    "Daftar Saham (satu simbol per baris):",
    "BBCA.JK\nBBRI.JK\nTLKM.JK\nASII.JK\nUNVR.JK",
    help="Untuk saham Indonesia, tambahkan .JK di akhir simbol. Contoh: BBCA.JK"
)

col1, col2 = st.sidebar.columns(2)
with col1:
    period_years = st.number_input("Periode Data (tahun):", 1, 5, 3)
with col2:
    trail_length = st.number_input("Panjang Trail:", 1, 20, 8, help="Jumlah periode terakhir yang ditampilkan pada grafik")

col3, col4 = st.sidebar.columns(2)
with col3:
    rs_ratio_period = st.number_input("Periode RS-Ratio:", 20, 100, 63, help="Periode untuk perhitungan RS-Ratio (hari trading)")
with col4:
    rs_momentum_period = st.number_input("Periode RS-Momentum:", 5, 60, 21, help="Periode untuk perhitungan RS-Momentum (hari trading)")

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

if analyze_button:
    stocks = [s.strip() for s in stocks_input.split("\n") if s.strip()]
    
    if not stocks:
        st.error("Silakan masukkan setidaknya satu simbol saham.")
    else:
        try:
            # Jalankan analisis
            analyzer, results = get_analysis(benchmark, stocks, period_years, rs_ratio_period, rs_momentum_period)
            
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
                    .set_properties(**{'text-align': 'center'})
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
            st.info("Periksa apakah simbol saham dan benchmark sudah benar. Pastikan juga koneksi internet Anda stabil.")
else:
    # Tampilkan info default ketika aplikasi pertama kali dibuka
    st.info("👈 Masukkan parameter analisis di panel sebelah kiri, lalu klik 'Jalankan Analisis'.")
    
    # Tampilkan contoh RRG
    st.image("https://chartschool.stockcharts.com/~gitbook/image?url=https%3A%2F%2F436553459-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252FERtrZrZOhufFzk6ZQO4B%252Fuploads%252FNj5BTpv50yRLXg4kNUHw%252Frrgs-03-quandrants.png%3Falt%3Dmedia%26token%3D6d870d19-af00-4f12-b1b1-acbd9ee535ef", 
             caption="Contoh visualisasi Relative Rotation Graph (RRG)")

# Footer
st.markdown("---")
st.markdown("Dibuat dengan ❤️ menggunakan Python dan Streamlit | © 2025")


# Tambahkan di bagian bawah app.py
if st.sidebar.checkbox("Debug Info", False):
    st.sidebar.write("Informasi Debug:")
    st.sidebar.write(f"Streamlit version: {st.__version__}")
    st.sidebar.write(f"Pandas version: {pd.__version__}")
    st.sidebar.write(f"Current time: {datetime.now()}")
