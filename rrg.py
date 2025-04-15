import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
import re

class RRGAnalyzer:
    def __init__(self, excel_file=None, benchmark_ticker=None, stock_tickers=None, period_years=3):
        """
        Inisialisasi analyzer RRG dengan file Excel Bloomberg
        :param excel_file: path file Excel dari Bloomberg
        :param benchmark_ticker: ticker benchmark (misalnya "JCI Index")
        :param stock_tickers: list ticker saham untuk analisis
        :param period_years: periode tahun data yang akan digunakan
        """
        self.excel_file = excel_file
        self.benchmark_ticker = benchmark_ticker
        self.stock_tickers = stock_tickers if stock_tickers else []
        self.period_years = period_years
        self.benchmark_data = None
        self.stock_data = {}
        self.rs_ratio = {}
        self.rs_momentum = {}
        self.rs_ratio_norm = {}
        self.rs_momentum_norm = {}
        
    def load_data_from_bloomberg_excel(self):
        """
        Load data dari file Excel Bloomberg
        """
        if not self.excel_file or not self.benchmark_ticker or not self.stock_tickers:
            print("File Excel, benchmark ticker atau stock tickers tidak valid")
            return False
            
        try:
            # Baca seluruh file Excel
            df = pd.read_excel(self.excel_file, header=None)
            
            # Find the relevant data rows (starting after the second table header)
            # Biasanya data dimulai setelah baris header "Dates"
            for i, row in df.iterrows():
                if isinstance(row[0], datetime) or (isinstance(row[0], str) and row[0].lower() == 'dates'):
                    start_row = i
                    break
            else:
                print("Format data tidak ditemukan")
                return False
                
            # Tentukan apakah header adalah "Dates" atau tanggal langsung
            if isinstance(df.iloc[start_row, 0], str) and df.iloc[start_row, 0].lower() == 'dates':
                # Header found, data starts on the next row
                data_start_row = start_row + 1
                date_col = 0
            else:
                # No header, this row already contains dates
                data_start_row = start_row
                date_col = 0
            
            # Temukan kolom untuk ticker yang diperlukan
            ticker_columns = {}
            for ticker in [self.benchmark_ticker] + self.stock_tickers:
                ticker_pattern = re.compile(f"{re.escape(ticker)}\\s*$", re.IGNORECASE)
                
                # Cari kolom PX_LAST (Close) untuk ticker
                found = False
                for col in range(len(df.columns)):
                    cell_value = str(df.iloc[data_start_row-1, col]) if data_start_row > 0 else ""
                    if ticker_pattern.search(cell_value):
                        # Simpan informasi kolom (kita butuh 5 kolom berturut-turut untuk OHLCV)
                        base_col = col
                        # Periksa 5 kolom berikutnya untuk memastikan mereka adalah OHLCV
                        ticker_columns[ticker] = {
                            'open': base_col,      # PX_OPEN
                            'high': base_col + 1,  # PX_HIGH
                            'low': base_col + 2,   # PX_LOW
                            'close': base_col + 3, # PX_LAST
                            'volume': base_col + 4 # PX_VOLUME
                        }
                        found = True
                        break
                
                if not found:
                    print(f"Ticker {ticker} tidak ditemukan di file Excel")
                    if ticker == self.benchmark_ticker:
                        # Jika benchmark tidak ditemukan, kita tidak bisa melanjutkan
                        return False
            
            # Proses data untuk benchmark
            if self.benchmark_ticker in ticker_columns:
                cols = ticker_columns[self.benchmark_ticker]
                
                # Extract date and OHLCV data untuk benchmark
                benchmark_data = df.iloc[data_start_row:, [date_col, cols['open'], cols['high'], cols['low'], cols['close'], cols['volume']]]
                benchmark_data.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
                
                # Konversi data ke format yang diperlukan
                benchmark_data['Date'] = pd.to_datetime(benchmark_data['Date'])
                benchmark_data = benchmark_data.set_index('Date')
                benchmark_data = benchmark_data.apply(pd.to_numeric, errors='coerce')
                
                # Filter untuk periode yang diminta
                if self.period_years > 0:
                    end_date = benchmark_data.index.max()
                    start_date = end_date - pd.DateOffset(years=self.period_years)
                    benchmark_data = benchmark_data.loc[start_date:end_date]
                
                # Simpan data benchmark
                self.benchmark_data = benchmark_data
            
            # Proses data untuk saham
            for ticker in self.stock_tickers:
                if ticker in ticker_columns:
                    cols = ticker_columns[ticker]
                    
                    # Extract date and OHLCV data untuk saham
                    stock_data = df.iloc[data_start_row:, [date_col, cols['open'], cols['high'], cols['low'], cols['close'], cols['volume']]]
                    stock_data.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
                    
                    # Konversi data ke format yang diperlukan
                    stock_data['Date'] = pd.to_datetime(stock_data['Date'])
                    stock_data = stock_data.set_index('Date')
                    stock_data = stock_data.apply(pd.to_numeric, errors='coerce')
                    
                    # Filter untuk periode yang diminta
                    if self.period_years > 0:
                        end_date = stock_data.index.max()
                        start_date = end_date - pd.DateOffset(years=self.period_years)
                        stock_data = stock_data.loc[start_date:end_date]
                    
                    # Simpan data saham
                    self.stock_data[ticker] = stock_data
            
            # Periksa apakah ada data saham yang berhasil dimuat
            if not self.stock_data:
                print("Tidak ada data saham yang berhasil dimuat")
                return False
                
            return True
                
        except Exception as e:
            print(f"Error saat memuat data dari file Excel: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
    def calculate_rs_ratio(self, period=63):
        """
        Menghitung Relative Strength Ratio (RS-Ratio)
        :param period: periode untuk perhitungan rata-rata (default ~3 bulan trading)
        """
        self.rs_ratio = {}  # Reset untuk menghindari data lama
        
        for ticker, data in self.stock_data.items():
            if len(data) == 0:
                continue
            
            # Pastikan data memiliki index yang sama
            common_index = data.index.intersection(self.benchmark_data.index)
            if len(common_index) < period:
                print(f"Data tidak cukup untuk {ticker}, minimal {period} hari diperlukan")
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
        
        for ticker in self.stock_tickers:
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
                
                latest_data.append({
                    'Symbol': ticker,
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
        
        # Tambahkan latar belakang kuadran
        ax.fill_between([100, 120], 100, 120, color='green', alpha=0.1)  # Leading
        ax.fill_between([100, 120], 80, 100, color='yellow', alpha=0.1)  # Weakening
        ax.fill_between([80, 100], 80, 100, color='red', alpha=0.1)      # Lagging
        ax.fill_between([80, 100], 100, 120, color='blue', alpha=0.1)    # Improving
        
        # Tambahkan label kuadran
        ax.text(110, 110, 'LEADING', fontsize=12, ha='center')
        ax.text(110, 90, 'WEAKENING', fontsize=12, ha='center')
        ax.text(90, 90, 'LAGGING', fontsize=12, ha='center')
        ax.text(90, 110, 'IMPROVING', fontsize=12, ha='center')
        
        # Plot data untuk setiap saham
        for ticker in list(self.rs_ratio_norm.keys()):
            if ticker in self.rs_momentum_norm:
                # Dapatkan data terbaru dan trail
                x_series = self.rs_ratio_norm[ticker].dropna()
                y_series = self.rs_momentum_norm[ticker].dropna()
                
                # Pastikan ada cukup data
                if len(x_series) < 2 or len(y_series) < 2:
                    continue
                
                # Ambil nilai untuk trail (batasi dengan min untuk menghindari error)
                x_data = x_series.iloc[-min(trail_length, len(x_series)):].values
                y_data = y_series.iloc[-min(trail_length, len(y_series)):].values
                
                # Plot trail jika ada cukup data
                if len(x_data) >= 2 and len(y_data) >= 2:
                    ax.plot(x_data, y_data, '-', linewidth=1, alpha=0.6)
                    
                    # Plot titik terbaru (hanya jika ada data)
                    ax.scatter(x_data[-1], y_data[-1], s=50)
                    
                    # Tampilkan label ticker yang lebih bersih
                    # Jika ticker berakhir dengan " Index" atau " Equity", hapus itu
                    display_name = ticker
                    if " Index" in display_name:
                        display_name = display_name.replace(" Index", "")
                    elif " Equity" in display_name:
                        display_name = display_name.replace(" Equity", "")
                        
                    # Jika masih terlalu panjang, potong ke 8 karakter
                    if len(display_name) > 8:
                        display_name = display_name[:8]
                        
                    # Tampilkan label
                    ax.annotate(display_name, (x_data[-1], y_data[-1]), 
                                 xytext=(5, 5), textcoords='offset points')
        
        # Set batas dan label
        ax.set_xlim(80, 120)
        ax.set_ylim(80, 120)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('RS-Ratio (Relative Strength)')
        ax.set_ylabel('RS-Momentum')
        
        # Format judul dengan nama benchmark yang lebih bersih
        benchmark_display = self.benchmark_ticker
        if " Index" in benchmark_display:
            benchmark_display = benchmark_display.replace(" Index", "")
        
        if title:
            ax.set_title(title)
        else:
            ax.set_title(f'Relative Rotation Graph (RRG) vs {benchmark_display}')
        
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
        success = self.load_data_from_bloomberg_excel()
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