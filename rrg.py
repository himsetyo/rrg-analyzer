import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
import re

class RRGAnalyzer:
    def __init__(self, benchmark_file=None, stock_files=None, period_years=3, max_date=None):
        """
        Inisialisasi analyzer RRG
        :param benchmark_file: path file CSV benchmark
        :param stock_files: list path file CSV saham
        :param period_years: periode tahun data yang akan diambil
        :param max_date: tanggal maksimal untuk analisis (datetime, string 'YYYY-MM-DD', atau string date)
        """
        self.benchmark_file = benchmark_file
        self.stock_files = stock_files if stock_files else []
        self.period_years = period_years
        
        # Konversi max_date ke datetime jika string
        if isinstance(max_date, str):
            try:
                # Coba dengan format YYYY-MM-DD
                self.max_date = pd.to_datetime(max_date)
            except:
                try:
                    # Jika gagal, coba format yang lain (seperti MM/DD/YYYY)
                    self.max_date = pd.to_datetime(max_date, format='%m/%d/%Y')
                except Exception as e:
                    print(f"Format tanggal tidak valid: {max_date}. Error: {str(e)}. Menggunakan tanggal hari ini.")
                    self.max_date = pd.to_datetime(datetime.now())
        elif isinstance(max_date, datetime):
            # Konversi datetime ke pandas Timestamp
            self.max_date = pd.to_datetime(max_date)
        else:
            # Jika None, gunakan hari ini
            self.max_date = pd.to_datetime(datetime.now())
        
        self.benchmark_data = None
        self.stock_data = {}
        self.stock_symbols = []
        self.rs_ratio = {}
        self.rs_momentum = {}
        self.rs_ratio_norm = {}
        self.rs_momentum_norm = {}
        self.ticker_map = {}  # Untuk menyimpan mapping ticker asli dari file CSV
    
    def load_data_from_files(self):
        """
        Load data dari file CSV
        """
        if not self.benchmark_file:
            print("File benchmark tidak ditemukan")
            return False
        
        try:
            # Load benchmark data
            self.benchmark_data = pd.read_csv(self.benchmark_file)
            
            # Cek format tanggal dan konversi jika perlu
            date_col = 'Date'
            if date_col in self.benchmark_data.columns:
                # Coba konversi tanggal
                try:
                    # Gunakan pd.to_datetime yang lebih fleksibel
                    self.benchmark_data[date_col] = pd.to_datetime(self.benchmark_data[date_col], errors='coerce')
                    
                    # Hapus data dengan tanggal invalid
                    invalid_dates = self.benchmark_data[date_col].isna()
                    if invalid_dates.any():
                        print(f"Menghapus {invalid_dates.sum()} baris dengan tanggal tidak valid dari benchmark data")
                        self.benchmark_data = self.benchmark_data[~invalid_dates]
                    
                    # Set index dan sort
                    self.benchmark_data.set_index(date_col, inplace=True)
                    self.benchmark_data.sort_index(inplace=True)
                except Exception as e:
                    print(f"Gagal mengkonversi format tanggal benchmark: {str(e)}")
                    return False
            else:
                print("Kolom 'Date' tidak ditemukan di file benchmark")
                return False
            
            # Ekstrak ticker dari data benchmark
            if 'Ticker' in self.benchmark_data.columns:
                benchmark_ticker_value = self.benchmark_data['Ticker'].iloc[0]
                self.benchmark_ticker = benchmark_ticker_value
            else:
                # Jika tidak ada kolom Ticker, gunakan nama file sebagai ticker
                benchmark_basename = os.path.splitext(os.path.basename(self.benchmark_file))[0]
                self.benchmark_ticker = benchmark_basename
            
            # Filter berdasarkan max_date - pastikan menggunakan tipe data yang sama
            try:
                # Pastikan tipe data max_date kompatibel dengan indeks
                max_date_timestamp = pd.to_datetime(self.max_date)
                # Gunakan operator .loc untuk menghindari kesalahan tipe data
                self.benchmark_data = self.benchmark_data.loc[self.benchmark_data.index <= max_date_timestamp]
            except Exception as e:
                print(f"Error saat mem-filter data berdasarkan max_date: {str(e)}")
                # Jika error, jangan filter berdasarkan tanggal dan lanjutkan
            
            if self.benchmark_data.empty:
                print("Data benchmark kosong setelah filter tanggal")
                return False
            
            # Filter data berdasarkan periode tahun
            if self.period_years > 0:
                try:
                    end_date = self.benchmark_data.index.max()
                    start_date = end_date - pd.DateOffset(years=self.period_years)
                    self.benchmark_data = self.benchmark_data.loc[self.benchmark_data.index >= start_date]
                except Exception as e:
                    print(f"Error saat mem-filter data berdasarkan periode tahun: {str(e)}")
                    # Jika error, jangan filter berdasarkan periode dan lanjutkan
            
            # Load stock data
            load_success = False
            self.stock_symbols = []  # Reset daftar symbol
            self.ticker_map = {}  # Reset ticker map
            
            for file_path in self.stock_files:
                try:
                    # Extract symbol dari nama file
                    file_symbol = os.path.splitext(os.path.basename(file_path))[0]
                    
                    # Load data
                    stock_data = pd.read_csv(file_path)
                    
                    # Cek dan konversi format tanggal jika perlu
                    if date_col in stock_data.columns:
                        try:
                            # Gunakan pd.to_datetime yang lebih fleksibel
                            stock_data[date_col] = pd.to_datetime(stock_data[date_col], errors='coerce')
                            
                            # Hapus data dengan tanggal invalid
                            invalid_dates = stock_data[date_col].isna()
                            if invalid_dates.any():
                                print(f"Menghapus {invalid_dates.sum()} baris dengan tanggal tidak valid dari file {file_symbol}")
                                stock_data = stock_data[~invalid_dates]
                            
                            # Set index dan sort
                            stock_data.set_index(date_col, inplace=True)
                            stock_data.sort_index(inplace=True)
                        except Exception as e:
                            print(f"Gagal mengkonversi format tanggal untuk {file_symbol}: {str(e)}")
                            continue
                    else:
                        print(f"Kolom 'Date' tidak ditemukan di file {file_symbol}")
                        continue
                    
                    # Dapatkan ticker dari file jika ada
                    if 'Ticker' in stock_data.columns:
                        # Gunakan ticker dari kolom Ticker file CSV
                        ticker_from_csv = stock_data['Ticker'].iloc[0]
                        symbol = ticker_from_csv
                        # Simpan mapping untuk referensi
                        self.ticker_map[file_symbol] = ticker_from_csv
                    else:
                        # Gunakan nama file sebagai ticker
                        symbol = file_symbol
                        self.ticker_map[file_symbol] = file_symbol
                    
                    # Filter berdasarkan max_date
                    try:
                        # Pastikan tipe data max_date kompatibel dengan indeks
                        max_date_timestamp = pd.to_datetime(self.max_date)
                        # Gunakan operator .loc untuk menghindari kesalahan tipe data
                        stock_data = stock_data.loc[stock_data.index <= max_date_timestamp]
                    except Exception as e:
                        print(f"Error saat mem-filter data {file_symbol} berdasarkan max_date: {str(e)}")
                        # Jika error, jangan filter berdasarkan tanggal dan lanjutkan
                    
                    # Filter data berdasarkan periode tahun
                    if self.period_years > 0 and not self.benchmark_data.empty:
                        try:
                            # Gunakan periode yang sama dengan benchmark
                            start_date = self.benchmark_data.index.min()
                            end_date = self.benchmark_data.index.max()
                            
                            # Cari rentang tanggal yang ada di kedua dataset
                            common_dates = stock_data.index.intersection(pd.date_range(start=start_date, end=end_date))
                            
                            if len(common_dates) > 0:
                                # Gunakan tanggal pertama dan terakhir yang umum
                                stock_data = stock_data.loc[common_dates.min():common_dates.max()]
                            else:
                                # Jika tidak ada tanggal yang sama, filter dengan periode tahun
                                stock_end_date = stock_data.index.max()
                                stock_start_date = stock_end_date - pd.DateOffset(years=self.period_years)
                                stock_data = stock_data.loc[stock_data.index >= stock_start_date]
                        except Exception as e:
                            print(f"Error saat mem-filter data {file_symbol} berdasarkan periode: {str(e)}")
                            # Jika error, jangan filter berdasarkan periode dan lanjutkan
                    
                    # Simpan data dan tambahkan symbol
                    if not stock_data.empty:
                        self.stock_data[file_symbol] = stock_data
                        self.stock_symbols.append(file_symbol)
                        load_success = True
                    else:
                        print(f"Data kosong untuk {file_symbol} setelah filtering")
                
                except Exception as e:
                    print(f"Error saat memuat data untuk {file_path}: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            return load_success
        
        except Exception as e:
            print(f"Error saat memuat data dari file: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def calculate_rs_ratio(self, period=63):
        """
        Menghitung Relative Strength Ratio (RS-Ratio)
        :param period: periode untuk perhitungan rata-rata (default ~3 bulan trading)
        """
        self.rs_ratio = {}  # Reset untuk menghindari data lama
        
        for ticker in self.stock_symbols:
            data = self.stock_data.get(ticker)
            if data is None or len(data) == 0:
                continue
            
            # Pastikan data memiliki index yang sama
            common_index = data.index.intersection(self.benchmark_data.index)
            if len(common_index) < period:
                print(f"Data tidak cukup untuk {ticker}, minimal {period} hari diperlukan. Hanya tersedia {len(common_index)} hari.")
                continue
                
            stock_aligned = data.loc[common_index]
            benchmark_aligned = self.benchmark_data.loc[common_index]
            
            # Menghitung Relative Strength Ratio
            relative_price = (stock_aligned['Close'] / benchmark_aligned['Close']) * 100
            
            # Menghitung rata-rata bergerak
            rs_ratio = relative_price.rolling(window=period, min_periods=1).mean()
            
            # Pastikan tidak ada NaN
            rs_ratio = rs_ratio.dropna()
            
            if len(rs_ratio) > 0:
                self.rs_ratio[ticker] = rs_ratio
    
    def calculate_rs_momentum(self, period=21):
        """
        Menghitung Relative Strength Momentum (RS-Momentum)
        :param period: periode untuk perhitungan momentum (default ~1 bulan trading)
        """
        self.rs_momentum = {}  # Reset untuk menghindari data lama
        
        for ticker in list(self.rs_ratio.keys()):
            rs_ratio_series = self.rs_ratio[ticker]
            
            if len(rs_ratio_series) <= period:
                print(f"Data tidak cukup untuk menghitung momentum {ticker}")
                continue
            
            # Hitung pct_change dengan fill_method=None untuk menghindari warning
            # Dan pastikan tidak ada NaN
            rs_momentum = rs_ratio_series.pct_change(periods=period, fill_method=None) * 100
            rs_momentum = rs_momentum.dropna()
            
            if len(rs_momentum) > 0:
                self.rs_momentum[ticker] = rs_momentum
    
    def normalize_data(self):
        """
        Normalisasi data RS-Ratio dan RS-Momentum
        """
        # Reset untuk menghindari data lama
        self.rs_ratio_norm = {}
        self.rs_momentum_norm = {}
        
        # Mengumpulkan semua nilai RS-Ratio dan RS-Momentum yang valid
        all_rs_ratio = []
        all_rs_momentum = []
        valid_tickers = []
        
        for ticker in list(self.rs_ratio.keys()):
            if ticker in self.rs_momentum:
                rs_ratio_values = self.rs_ratio[ticker].dropna().values
                rs_momentum_values = self.rs_momentum[ticker].dropna().values
                
                if len(rs_ratio_values) > 0 and len(rs_momentum_values) > 0:
                    all_rs_ratio.extend(rs_ratio_values)
                    all_rs_momentum.extend(rs_momentum_values)
                    valid_tickers.append(ticker)
        
        if not valid_tickers:
            print("Tidak ada ticker valid dengan data lengkap")
            return False
        
        if len(all_rs_ratio) < 2 or len(all_rs_momentum) < 2:
            print("Tidak cukup data untuk normalisasi")
            return False
        
        # Menghitung mean dan standard deviation
        rs_ratio_mean = np.mean(all_rs_ratio)
        rs_ratio_std = np.std(all_rs_ratio)
        rs_momentum_mean = np.mean(all_rs_momentum)
        rs_momentum_std = np.std(all_rs_momentum)
        
        # Cek standard deviasi tidak nol
        if rs_ratio_std <= 0.0001 or rs_momentum_std <= 0.0001:
            print("Standard deviasi terlalu kecil, tidak dapat melakukan normalisasi")
            return False
        
        # Normalisasi dengan Z-score dan pindahkan mean ke 100
        for ticker in valid_tickers:
            # Pastikan data yang akan dinormalisasi tidak ada NaN
            ratio_series = self.rs_ratio[ticker].dropna()
            momentum_series = self.rs_momentum[ticker].dropna()
            
            # Hanya lakukan normalisasi jika keduanya memiliki data
            if len(ratio_series) > 0 and len(momentum_series) > 0:
                # Normalisasi dan atur ke mean 100, std 10
                self.rs_ratio_norm[ticker] = 100 + 10 * ((ratio_series - rs_ratio_mean) / rs_ratio_std)
                self.rs_momentum_norm[ticker] = 100 + 10 * ((momentum_series - rs_momentum_mean) / rs_momentum_std)
        
        # Verifikasi hasil normalisasi
        if not self.rs_ratio_norm:
            print("Hasil normalisasi kosong")
            return False
        
        return True
    
    def get_latest_data(self):
        """
        Dapatkan data terbaru untuk setiap saham
        :return: DataFrame dengan data terbaru
        """
        latest_data = []
        
        for ticker in self.stock_symbols:
            if (ticker in self.rs_ratio_norm and 
                ticker in self.rs_momentum_norm and 
                not self.rs_ratio_norm[ticker].empty and 
                not self.rs_momentum_norm[ticker].empty):
                
                # Ambil nilai terakhir
                rs_ratio = self.rs_ratio_norm[ticker].iloc[-1]
                rs_momentum = self.rs_momentum_norm[ticker].iloc[-1]
                
                # Tentukan kuadran
                if rs_ratio >= 100 and rs_momentum >= 100:
                    quadrant = "Leading"
                    recommendation = "Hold/Buy"
                elif rs_ratio >= 100 and rs_momentum < 100:
                    quadrant = "Weakening"
                    recommendation = "Hold/Take Profit"
                elif rs_ratio < 100 and rs_momentum < 100:
                    quadrant = "Lagging"
                    recommendation = "Sell/Cut Loss"
                else:
                    quadrant = "Improving"
                    recommendation = "Accumulate/Buy Carefully"
                
                # Gunakan ticker yang sebenarnya dari data CSV jika tersedia
                display_name = self.ticker_map.get(ticker, ticker)
                
                latest_data.append({
                    'Symbol': display_name,
                    'RS-Ratio': rs_ratio,
                    'RS-Momentum': rs_momentum,
                    'Quadrant': quadrant,
                    'Recommendation': recommendation
                })
        
        return pd.DataFrame(latest_data)
    
    def plot_rrg(self, title=None, trail_length=4):
        """
        Plot Relative Rotation Graph
        :param title: judul grafik
        :param trail_length: panjang trail (berapa periode sebelumnya yang ditampilkan)
        """
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Gambar garis sumbu
        ax.axhline(y=100, color='gray', linestyle='-', alpha=0.3)
        ax.axvline(x=100, color='gray', linestyle='-', alpha=0.3)
        
        # Definisikan batas grafik yang seimbang
        x_min, x_max = 70, 130  # Sekarang seimbang (30 unit ke bawah dan 30 unit ke atas)
        y_min, y_max = 70, 130  # Sekarang seimbang (30 unit ke bawah dan 30 unit ke atas)
        
        # Tambahkan latar belakang kuadran
        ax.fill_between([100, x_max], 100, y_max, color='green', alpha=0.1)  # Leading
        ax.fill_between([100, x_max], y_min, 100, color='yellow', alpha=0.1)  # Weakening
        ax.fill_between([x_min, 100], y_min, 100, color='red', alpha=0.1)     # Lagging
        ax.fill_between([x_min, 100], 100, y_max, color='blue', alpha=0.1)   # Improving
        
        # Label kuadran
        ax.text(115, 115, 'LEADING', fontsize=12, ha='center', va='center')
        ax.text(115, 85, 'WEAKENING', fontsize=12, ha='center', va='center')
        ax.text(85, 85, 'LAGGING', fontsize=12, ha='center', va='center')
        ax.text(85, 115, 'IMPROVING', fontsize=12, ha='center', va='center')

        # Hitung posisi tengah setiap kuadran untuk teks
        leading_x = 100 + (x_max - 100) / 2
        leading_y = 100 + (y_max - 100) / 2
        
        weakening_x = 100 + (x_max - 100) / 2
        weakening_y = 100 - (100 - y_min) / 2
        
        lagging_x = 100 - (100 - x_min) / 2
        lagging_y = 100 - (100 - y_min) / 2
        
        improving_x = 100 - (100 - x_min) / 2
        improving_y = 100 + (y_max - 100) / 2
        
        # Tambahkan label kuadran dengan posisi yang tepat di tengah
        ax.text(leading_x, leading_y, 'LEADING', fontsize=12, ha='center', va='center')
        ax.text(weakening_x, weakening_y, 'WEAKENING', fontsize=12, ha='center', va='center')
        ax.text(lagging_x, lagging_y, 'LAGGING', fontsize=12, ha='center', va='center')
        ax.text(improving_x, improving_y, 'IMPROVING', fontsize=12, ha='center', va='center')
        
        # Plot data untuk setiap saham
        for ticker in list(self.rs_ratio_norm.keys()):
            if ticker in self.rs_momentum_norm:
                # Dapatkan data terbaru dan trail
                x_series = self.rs_ratio_norm[ticker].dropna()
                y_series = self.rs_momentum_norm[ticker].dropna()

                # Pastikan ada cukup data
                if len(x_series) == 0 or len(y_series) == 0:
                    continue

                # Ambil nilai terbaru
                x_latest = x_series.iloc[-1]
                y_latest = y_series.iloc[-1]

                # PERBAIKAN: Plot dengan marker yang lebih jelas dan ukuran lebih besar
                ax.scatter(x_latest, y_latest, s=100, marker='o', color='blue', 
                          edgecolors='black', linewidths=1.5, zorder=10)

                # Tampilkan label ticker
                display_name = self.ticker_map.get(ticker, ticker) if hasattr(self, 'ticker_map') else ticker
                
                # PERBAIKAN: Tambahkan box untuk label
                ax.annotate(display_name, (x_latest, y_latest), 
                            xytext=(7, 7), textcoords='offset points',
                            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8),
                            fontsize=9, fontweight='bold')

                # Plot trail jika ada cukup data untuk trail
                if len(x_series) >= 2 and trail_length > 1:
                    x_trail = x_series.iloc[-min(trail_length, len(x_series)):].values
                    y_trail = y_series.iloc[-min(trail_length, len(y_series)):].values
                    if len(x_trail) >= 2:
                        ax.plot(x_trail, y_trail, '-', linewidth=1, alpha=0.6)
                
                # Plot titik terbaru (hanya jika ada data)
                ax.scatter(x_data[-1], y_data[-1], s=50)
                
                # Tampilkan label ticker yang lebih bersih
                # Gunakan ticker dari file CSV jika tersedia
                display_name = self.ticker_map.get(ticker, ticker)
                
                # Jika masih terlalu panjang, potong ke 8 karakter
                if len(display_name) > 8:
                    display_name = display_name[:8]
                
                # Tampilkan label
                ax.annotate(display_name, (x_data[-1], y_data[-1]), xytext=(5, 5), textcoords='offset points')
        
        # Set batas dan label
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('RS-Ratio (Relative Strength)')
        ax.set_ylabel('RS-Momentum')
        
        # Format judul dengan nama benchmark yang lebih bersih
        analysis_date = datetime.now().strftime('%d %b %Y')
        if hasattr(self, 'get_analysis_date'):
            analysis_date = self.get_analysis_date().strftime('%d %b %Y')
            
        if title:
            ax.set_title(f"{title} ({analysis_date})")
        else:
            benchmark_display = getattr(self, 'benchmark_ticker', 'Benchmark')
            ax.set_title(f'Relative Rotation Graph (RRG) vs {benchmark_display} ({analysis_date})')

        plt.tight_layout()
        return fig
    
    def analyze(self, rs_ratio_period=63, rs_momentum_period=21):
        """
        Jalankan analisis lengkap
        """
        # Validasi input
        if rs_ratio_period <= 0 or rs_momentum_period <= 0:
            print("Periode harus positif")
            return None
        
        # Load data
        success = self.load_data_from_files()
        
        if not success:
            print("Gagal memuat data")
            return None
        
        # Hitung RRG
        self.calculate_rs_ratio(period=rs_ratio_period)
        if not self.rs_ratio:
            print("Gagal menghitung RS-Ratio")
            return None
        
        self.calculate_rs_momentum(period=rs_momentum_period)
        if not self.rs_momentum:
            print("Gagal menghitung RS-Momentum")
            return None
        
        # Normalisasi
        success = self.normalize_data()
        if not success:
            print("Gagal melakukan normalisasi data")
            return None
        
        # Get latest data
        result = self.get_latest_data()
        if result.empty:
            print("Tidak ada hasil analisis")
            return None
        
        return result
    
    def get_analysis_date(self):
        """
        Mendapatkan tanggal analisis (tanggal maksimal yang digunakan)
        """
        if self.benchmark_data is not None and not self.benchmark_data.empty:
            return self.benchmark_data.index.max()
        return pd.to_datetime(self.max_date)