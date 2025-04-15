import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta

class RRGAnalyzer:
    def __init__(self, benchmark_symbol, stock_symbols, period_years=3):
        """
        Inisialisasi analyzer RRG
        :param benchmark_symbol: simbol benchmark (misalnya '^JKSE' untuk IHSG)
        :param stock_symbols: list simbol saham yang akan dianalisis
        :param period_years: periode tahun data yang akan diambil
        """
        self.benchmark_symbol = benchmark_symbol
        self.stock_symbols = stock_symbols
        self.period_years = period_years
        self.benchmark_data = None
        self.stock_data = {}
        self.rs_ratio = {}
        self.rs_momentum = {}
        self.rs_ratio_norm = {}
        self.rs_momentum_norm = {}
        
    def download_data(self):
        """
        Download data historis dari Yahoo Finance
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.period_years*365)
        
        # Download data benchmark
    try:
        benchmark_data = yf.download(self.benchmark_symbol, start=start_date, end=end_date, progress=False)
        
        if benchmark_data.empty:
            raise Exception(f"Data untuk benchmark {self.benchmark_symbol} kosong")
            
        self.benchmark_data = benchmark_data
        print(f"Berhasil download data benchmark {self.benchmark_symbol}: {len(benchmark_data)} baris")
            
    except Exception as e:
        raise Exception(f"Error saat mengunduh data benchmark {self.benchmark_symbol}: {str(e)}")
    
    # Download data saham
    success_count = 0
    for symbol in self.stock_symbols:
        try:
            data = yf.download(symbol, start=start_date, end=end_date, progress=False)
            
            if data.empty:
                print(f"Warning: Data untuk {symbol} kosong")
                continue
                
            self.stock_data[symbol] = data
            success_count += 1
            
        except Exception as e:
            print(f"Error saat mengunduh data untuk {symbol}: {str(e)}")
    
    if success_count == 0:
        raise Exception("Tidak ada data saham yang berhasil diunduh")
                
    def calculate_rs_ratio(self, period=63):
    """
    Menghitung Relative Strength Ratio (RS-Ratio)
    :param period: periode untuk perhitungan rata-rata (default ~3 bulan trading)
    """
    for symbol, data in self.stock_data.items():
        if len(data) == 0:
            continue
            
        # Pastikan benchmark dan data saham memiliki index yang sama
        # Dengan melakukan reindex pada data yang sama-sama ada
        common_index = data.index.intersection(self.benchmark_data.index)
        
        if len(common_index) == 0:
            print(f"Warning: Tidak ada tanggal yang sama antara {symbol} dan benchmark")
            continue
            
        stock_aligned = data.loc[common_index]
        benchmark_aligned = self.benchmark_data.loc[common_index]
        
        # Menghitung Relative Strength Ratio
        relative_price = (stock_aligned['Close'] / benchmark_aligned['Close']) * 100
        
        # Menghitung rata-rata bergerak
        rs_ratio = relative_price.rolling(window=min(period, len(relative_price))).mean()
        
        self.rs_ratio[symbol] = rs_ratio
            
    def calculate_rs_momentum(self, period=21):
        """
        Menghitung Relative Strength Momentum (RS-Momentum)
        :param period: periode untuk perhitungan momentum (default ~1 bulan trading)
        """
        for symbol, rs_ratio in self.rs_ratio.items():
            # Menghitung persentase perubahan RS-Ratio
            rs_momentum = rs_ratio.pct_change(periods=period) * 100
            
            self.rs_momentum[symbol] = rs_momentum
            
    def normalize_data(self):
        """
        Normalisasi data RS-Ratio dan RS-Momentum
        """
        # Mengumpulkan semua nilai RS-Ratio dan RS-Momentum yang valid
        all_rs_ratio = []
        all_rs_momentum = []
        
        for symbol in self.stock_symbols:
            if symbol in self.rs_ratio and symbol in self.rs_momentum:
                all_rs_ratio.extend(self.rs_ratio[symbol].dropna().values)
                all_rs_momentum.extend(self.rs_momentum[symbol].dropna().values)
        
        # Menghitung mean dan standard deviation
        rs_ratio_mean = np.mean(all_rs_ratio)
        rs_ratio_std = np.std(all_rs_ratio)
        rs_momentum_mean = np.mean(all_rs_momentum)
        rs_momentum_std = np.std(all_rs_momentum)
        
        # Normalisasi dengan Z-score dan pindahkan mean ke 100
        for symbol in self.stock_symbols:
            if symbol in self.rs_ratio and symbol in self.rs_momentum:
                self.rs_ratio_norm[symbol] = 100 + 10 * ((self.rs_ratio[symbol] - rs_ratio_mean) / rs_ratio_std)
                self.rs_momentum_norm[symbol] = 100 + 10 * ((self.rs_momentum[symbol] - rs_momentum_mean) / rs_momentum_std)
    
    def get_latest_data(self):
        """
        Dapatkan data terbaru untuk setiap saham
        :return: DataFrame dengan data terbaru
        """
        latest_data = []
        
        for symbol in self.stock_symbols:
            if symbol in self.rs_ratio_norm and symbol in self.rs_momentum_norm:
                rs_ratio = self.rs_ratio_norm[symbol].iloc[-1]
                rs_momentum = self.rs_momentum_norm[symbol].iloc[-1]
                
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
                    'Symbol': symbol,
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
        fig, ax = plt.subplots(figsize=(12, 10))
        
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
        for symbol in self.stock_symbols:
            if symbol in self.rs_ratio_norm and symbol in self.rs_momentum_norm:
                # Dapatkan data terbaru dan trail
                x_data = self.rs_ratio_norm[symbol].iloc[-trail_length:].values
                y_data = self.rs_momentum_norm[symbol].iloc[-trail_length:].values
                
                # Plot trail
                ax.plot(x_data, y_data, '-', linewidth=1, alpha=0.6)
                
                # Plot titik terbaru
                ax.scatter(x_data[-1], y_data[-1], s=50)
                
                # Tambahkan label
                ax.annotate(symbol, (x_data[-1], y_data[-1]), 
                             xytext=(5, 5), textcoords='offset points')
        
        ax.set_xlim(80, 120)
        ax.set_ylim(80, 120)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('RS-Ratio (Relative Strength)')
        ax.set_ylabel('RS-Momentum')
        
        if title:
            ax.set_title(title)
        else:
            ax.set_title(f'Relative Rotation Graph (RRG) vs {self.benchmark_symbol}')
        
        plt.tight_layout()
        return fig
    
    def analyze(self):
        """
        Jalankan analisis lengkap
        """
        self.download_data()
        self.calculate_rs_ratio()
        self.calculate_rs_momentum()
        self.normalize_data()
        
        return self.get_latest_data()
