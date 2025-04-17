import yfinance as yf
import pandas as pd
import numpy as np
import time
import os
import re

class FundamentalAnalyzer:
    """
    Kelas untuk menganalisis data fundamental dari Yahoo Finance
    """
    
    def __init__(self):
        """
        Inisialisasi analyzer dengan indikator yang akan digunakan
        """
        # Indikator fundamental yang akan digunakan untuk analisis
        self.fundamental_indicators = [
            'returnOnEquity',      # ROE
            'returnOnAssets',      # ROA
            'profitMargins',       # Profit Margin
            'earningsGrowth',      # Pertumbuhan Laba
            'debtToEquity'         # Rasio Hutang terhadap Ekuitas
        ]
        
        # Bobot untuk masing-masing indikator
        self.indicator_weights = {
            'returnOnEquity': 0.25,       # 25%
            'returnOnAssets': 0.20,        # 20%
            'profitMargins': 0.20,         # 20%
            'earningsGrowth': 0.20,        # 20%
            'debtToEquity': 0.15           # 15%
        }
        
        # Mapping dari kode ticker ke kode Yahoo Finance
        self.ticker_mapping = {}
        
        # Cache untuk data fundamental
        self.fundamental_data_cache = {}
    
    def convert_to_yahoo_ticker(self, ticker):
        """
        Mengkonversi ticker dari format lokal ke format Yahoo Finance
        
        Contoh:
        - BBCA -> BBCA.JK (untuk saham Indonesia)
        - LQ45 -> ^JKLQ45 (untuk indeks Indonesia)
        
        :param ticker: string, ticker dalam format lokal
        :return: string, ticker dalam format Yahoo Finance
        """
        # Cek jika ticker sudah ada di mapping
        if ticker in self.ticker_mapping:
            return self.ticker_mapping[ticker]
        
        # Cek jika ticker adalah indeks
        if ticker in ['LQ45', 'IHSG', 'JCI']:
            if ticker == 'LQ45':
                yahoo_ticker = '^JKLQ45'
            elif ticker in ['IHSG', 'JCI']:
                yahoo_ticker = '^JKSE'
            else:
                yahoo_ticker = ticker  # Gunakan ticker asli jika tidak ada mapping
        else:
            # Asumsikan ini adalah saham Indonesia dan tambahkan .JK
            # Hapus spasi dan karakter khusus
            clean_ticker = ticker.split()[0]  # Ambil bagian pertama jika ada spasi
            clean_ticker = re.sub(r'[^\w]', '', clean_ticker)  # Hapus karakter non-alfanumerik
            yahoo_ticker = f"{clean_ticker}.JK"
        
        # Simpan mapping untuk penggunaan berikutnya
        self.ticker_mapping[ticker] = yahoo_ticker
        
        return yahoo_ticker
    
    def get_fundamental_data(self, ticker, force_refresh=False):
        """
        Mendapatkan data fundamental dari Yahoo Finance
        
        :param ticker: string, ticker dalam format lokal
        :param force_refresh: boolean, apakah memaksa refresh data dari API
        :return: dict, data fundamental
        """
        # Cek cache jika tidak dipaksa refresh
        if not force_refresh and ticker in self.fundamental_data_cache:
            return self.fundamental_data_cache[ticker]
        
        # Konversi ticker ke format Yahoo Finance
        yahoo_ticker = self.convert_to_yahoo_ticker(ticker)
        
        try:
            # Dapatkan data dari Yahoo Finance
            yf_ticker = yf.Ticker(yahoo_ticker)
            info = yf_ticker.info
            
            # Ekstrak data fundamental yang dibutuhkan
            fundamental_data = {}
            for indicator in self.fundamental_indicators:
                if indicator in info and info[indicator] is not None:
                    fundamental_data[indicator] = info[indicator]
                else:
                    fundamental_data[indicator] = None
            
            # Tambahkan informasi dasar perusahaan
            if 'longName' in info:
                fundamental_data['longName'] = info['longName']
            if 'sector' in info:
                fundamental_data['sector'] = info['sector']
            if 'industry' in info:
                fundamental_data['industry'] = info['industry']
            if 'marketCap' in info:
                fundamental_data['marketCap'] = info['marketCap']
            
            # Simpan ke cache
            self.fundamental_data_cache[ticker] = fundamental_data
            
            # Tunggu sedikit untuk menghindari rate limiting
            time.sleep(0.2)
            
            return fundamental_data
        
        except Exception as e:
            print(f"Error saat mendapatkan data fundamental untuk {ticker}: {str(e)}")
            return {}
    
    def calculate_fundamental_score(self, ticker_data):
        """
        Menghitung skor fundamental berdasarkan data yang diambil
        
        :param ticker_data: dict, data fundamental ticker
        :return: float, skor fundamental (0-100)
        """
        if not ticker_data:
            return 0
        
        scores = {}
        total_weight = 0
        
        # ROE Score (0-100)
        if 'returnOnEquity' in ticker_data and ticker_data['returnOnEquity'] is not None:
            roe = ticker_data['returnOnEquity']
            # ROE 0% = 0, ROE 20% = 100, linear scale
            roe_score = min(100, max(0, roe * 500))  # ROE 0.2 (20%) = score 100
            scores['returnOnEquity'] = roe_score
            total_weight += self.indicator_weights['returnOnEquity']
        
        # ROA Score (0-100)
        if 'returnOnAssets' in ticker_data and ticker_data['returnOnAssets'] is not None:
            roa = ticker_data['returnOnAssets']
            # ROA 0% = 0, ROA 10% = 100, linear scale
            roa_score = min(100, max(0, roa * 1000))  # ROA 0.1 (10%) = score 100
            scores['returnOnAssets'] = roa_score
            total_weight += self.indicator_weights['returnOnAssets']
        
        # Profit Margin Score (0-100)
        if 'profitMargins' in ticker_data and ticker_data['profitMargins'] is not None:
            margin = ticker_data['profitMargins']
            # Margin 0% = 0, Margin 20% = 100, linear scale
            margin_score = min(100, max(0, margin * 500))  # Margin 0.2 (20%) = score 100
            scores['profitMargins'] = margin_score
            total_weight += self.indicator_weights['profitMargins']
        
        # Earnings Growth Score (0-100)
        if 'earningsGrowth' in ticker_data and ticker_data['earningsGrowth'] is not None:
            growth = ticker_data['earningsGrowth']
            # Growth -20% = 0, Growth 0% = 50, Growth 20% = 100, linear scale
            growth_score = min(100, max(0, (growth + 0.2) * 250))  # Growth 0.2 (20%) = score 100
            scores['earningsGrowth'] = growth_score
            total_weight += self.indicator_weights['earningsGrowth']
        
        # Debt to Equity Score (100-0, lower is better)
        if 'debtToEquity' in ticker_data and ticker_data['debtToEquity'] is not None:
            dte = ticker_data['debtToEquity']
            if dte <= 0:
                dte_score = 100  # No debt = perfect score
            elif dte >= 2:
                dte_score = 0    # DTE >= 200% = zero score
            else:
                dte_score = 100 - (dte * 50)  # Linear scale: DTE 100% = score 50
            scores['debtToEquity'] = dte_score
            total_weight += self.indicator_weights['debtToEquity']
        
        # Calculate weighted average score
        if scores and total_weight > 0:
            weighted_score = sum(scores[indicator] * self.indicator_weights[indicator] for indicator in scores) / total_weight
            return weighted_score
        else:
            return 0
    
    def get_fundamental_analysis(self, tickers):
        """
        Mendapatkan analisis fundamental untuk daftar ticker
        
        :param tickers: list, daftar ticker dalam format lokal
        :return: DataFrame, hasil analisis fundamental
        """
        results = []
        
        for ticker in tickers:
            fundamental_data = self.get_fundamental_data(ticker)
            fundamental_score = self.calculate_fundamental_score(fundamental_data)
            
            result = {
                'Symbol': ticker,
                'Fundamental_Score': fundamental_score
            }
            
            # Tambahkan data mentah untuk referensi
            for indicator in self.fundamental_indicators:
                if indicator in fundamental_data:
                    result[indicator] = fundamental_data[indicator]
            
            # Tambahkan informasi tambahan jika tersedia
            for info_field in ['longName', 'sector', 'industry', 'marketCap']:
                if info_field in fundamental_data:
                    result[info_field] = fundamental_data[info_field]
            
            results.append(result)
        
        return pd.DataFrame(results)
    
    def combine_with_rrg(self, fundamental_data, rrg_data):
        """
        Menggabungkan data fundamental dengan data RRG
        
        :param fundamental_data: DataFrame, data fundamental
        :param rrg_data: DataFrame, data RRG
        :return: DataFrame, data gabungan
        """
        # Pastikan kedua DataFrame memiliki kolom 'Symbol' untuk join
        if 'Symbol' not in fundamental_data.columns or 'Symbol' not in rrg_data.columns:
            raise ValueError("Kedua DataFrame harus memiliki kolom 'Symbol'")
        
        # Join berdasarkan Symbol
        combined_data = pd.merge(rrg_data, fundamental_data, on='Symbol', how='left')
        
        # Isi nilai NaN dengan 0 untuk skor fundamental
        if 'Fundamental_Score' in combined_data.columns:
            combined_data = combined_data.copy()  # Membuat salinan eksplisit
            combined_data['Fundamental_Score'] = combined_data['Fundamental_Score'].fillna(0)
        else:
            combined_data['Fundamental_Score'] = 0
        
        # Normalisasi RS-Momentum ke skala 0-100
        # Asumsikan RS-Momentum biasanya berada di sekitar 100 dengan std 10
        combined_data['RS_Momentum_Normalized'] = (combined_data['RS-Momentum'] - 90) * 100 / 20
        combined_data['RS_Momentum_Normalized'] = combined_data['RS_Momentum_Normalized'].apply(lambda x: max(0, min(100, x)))
        
        # Hitung skor gabungan (50% fundamental, 50% RS-Momentum)
        combined_data['Combined_Score'] = (
            combined_data['Fundamental_Score'] * 0.5 + 
            combined_data['RS_Momentum_Normalized'] * 0.5
        )
        
        # Tentukan rekomendasi gabungan
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
        
        combined_data['Combined_Recommendation'] = combined_data['Combined_Score'].apply(get_combined_recommendation)
        
        return combined_data
    
    def plot_combined_analysis(self, combined_data, ax=None):
        """
        Visualisasi analisis gabungan fundamental dan RRG
        
        :param combined_data: DataFrame, data gabungan
        :param ax: matplotlib axes, jika None akan dibuat baru
        :return: matplotlib figure
        """
        import matplotlib.pyplot as plt
        
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 8))
        else:
            fig = ax.figure
        
        # Pilih kolom marketCap untuk ukuran bubble jika tersedia
        if 'marketCap' in combined_data.columns:
            # Log scale untuk market cap untuk menghindari bubbles terlalu besar
            sizes = combined_data['marketCap'].apply(lambda x: max(100, min(1000, (np.log10(x+1) * 100) if x is not None else 100)))
        else:
            sizes = 200  # Ukuran default
        
        # Pilih kolom sector untuk warna jika tersedia
        if 'sector' in combined_data.columns:
            # Encode sektor menjadi kode warna
            sectors = combined_data['sector'].fillna('Unknown').unique()
            sector_codes = {sector: i for i, sector in enumerate(sectors)}
            colors = combined_data['sector'].fillna('Unknown').map(sector_codes)
            
            # Buat scatter plot dengan warna berdasarkan sektor
            scatter = ax.scatter(
                combined_data['RS-Ratio'], 
                combined_data['Combined_Score'],
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
            # Buat scatter plot tanpa pengelompokan sektor
            scatter = ax.scatter(
                combined_data['RS-Ratio'], 
                combined_data['Combined_Score'],
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
                (row['RS-Ratio'], row['Combined_Score']),
                xytext=(5, 5),
                textcoords='offset points',
                fontsize=9
            )
        
        # Tambahkan garis pembatas untuk rekomendasi
        ax.axhline(y=80, color='green', linestyle='--', alpha=0.5)
        ax.axhline(y=65, color='lightgreen', linestyle='--', alpha=0.5)
        ax.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
        ax.axhline(y=35, color='orange', linestyle='--', alpha=0.5)
        
        # Tambahkan garis vertikal di nilai 100 (garis tengah RS-Ratio)
        ax.axvline(x=100, color='gray', linestyle='-', alpha=0.3)
        
        # Tambahkan label di sebelah kanan untuk setiap zona
        ax.text(ax.get_xlim()[1]*0.95, 90, "Strong Buy", verticalalignment='center', fontsize=10, color='darkgreen')
        ax.text(ax.get_xlim()[1]*0.95, 72.5, "Buy", verticalalignment='center', fontsize=10, color='green')
        ax.text(ax.get_xlim()[1]*0.95, 57.5, "Hold", verticalalignment='center', fontsize=10, color='gray')
        ax.text(ax.get_xlim()[1]*0.95, 42.5, "Reduce", verticalalignment='center', fontsize=10, color='orange')
        ax.text(ax.get_xlim()[1]*0.95, 25, "Sell", verticalalignment='center', fontsize=10, color='red')
        
        # Set judul dan label
        ax.set_title('Combined Technical & Fundamental Analysis', fontsize=14)
        ax.set_xlabel('RS-Ratio (Technical Strength)', fontsize=12)
        ax.set_ylabel('Combined Score (Technical + Fundamental)', fontsize=12)
        
        # Tambahkan grid
        ax.grid(True, alpha=0.3)
        
        # Set interval sumbu y dari 0-100
        ax.set_ylim(0, 100)
        
        plt.tight_layout()
        return fig

# Fungsi bantuan untuk pengujian
if __name__ == "__main__":
    # Uji analyzer
    analyzer = FundamentalAnalyzer()
    
    # Uji konversi ticker
    print("Testing ticker conversion:")
    test_tickers = ["BBCA", "TLKM", "UNVR", "LQ45", "IHSG"]
    for ticker in test_tickers:
        yahoo_ticker = analyzer.convert_to_yahoo_ticker(ticker)
        print(f"  {ticker} -> {yahoo_ticker}")
    
    # Uji pengambilan data fundamental
    print("\nTesting fundamental data retrieval:")
    test_ticker = "BBCA"
    fundamental_data = analyzer.get_fundamental_data(test_ticker)
    print(f"  Data for {test_ticker}:")
    for k, v in fundamental_data.items():
        print(f"    {k}: {v}")
    
    # Uji penghitungan skor fundamental
    print("\nTesting fundamental score calculation:")
    score = analyzer.calculate_fundamental_score(fundamental_data)
    print(f"  Fundamental score for {test_ticker}: {score:.2f}")