# analysis_engine.py
import pandas as pd
import numpy as np
import os
import tempfile
from datetime import datetime

class AnalysisEngine:
    """
    Engine untuk menangani logika analisis dan pemrosesan data
    """
    def __init__(self):
        self.benchmark_data = None
        self.stock_data = {}
        self.results = None
        self.combined_results = None
        self.rrg_results = None
        self.analysis_date = None
        self.temp_files = []
    
    def save_uploaded_file(self, uploaded_file):
        """
        Menyimpan file yang di-upload ke file sementara
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as f:
            f.write(uploaded_file.getvalue())
            self.temp_files.append(f.name)
            return f.name
    
    def run_analysis(self, benchmark_file, stock_files, analysis_params):
        """
        Menjalankan analisis berdasarkan file yang di-upload dan parameter yang diberikan
        
        :param benchmark_file: File benchmark
        :param stock_files: Daftar file saham
        :param analysis_params: Dictionary parameter analisis
        :return: Tuple (success, message, results)
        """
        try:
            # Simpan file ke temporary files
            benchmark_temp = self.save_uploaded_file(benchmark_file)
            stock_temps = [self.save_uploaded_file(f) for f in stock_files]
            
            # Ekstrak parameter
            period_years = analysis_params.get('period_years', 3.0)
            rs_ratio_period = analysis_params.get('rs_ratio_period', 52)
            rs_momentum_period = analysis_params.get('rs_momentum_period', 26)
            max_date = analysis_params.get('max_date', None)
            analysis_type = analysis_params.get('analysis_type', 'RRG (Teknikal)')
            use_fundamental = analysis_params.get('use_fundamental', False)
            use_universe_score = analysis_params.get('use_universe_score', False)
            universe_score_input = analysis_params.get('universe_score_input', 50)
            
            # Import modul RRG dan fundamental
            from rrg import RRGAnalyzer
            if use_fundamental:
                from fundamental_analyzer import FundamentalAnalyzer
            
            # Step 1: Inisialisasi RRG Analyzer
            rrg_analyzer = RRGAnalyzer(
                benchmark_file=benchmark_temp,
                stock_files=stock_temps,
                period_years=period_years,
                max_date=max_date
            )
            
            # Step 2: Load data
            success = rrg_analyzer.load_data_from_files()
            if not success:
                return False, "Gagal memuat data dari file. Periksa format file CSV Anda.", None
            
            # Step 3: Hitung RS-Ratio
            rrg_analyzer.calculate_rs_ratio(period=rs_ratio_period)
            if not rrg_analyzer.rs_ratio:
                return False, "Gagal menghitung RS-Ratio. Mungkin tidak cukup data.", None
            
            # Step 4: Hitung RS-Momentum
            rrg_analyzer.calculate_rs_momentum(period=rs_momentum_period)
            if not rrg_analyzer.rs_momentum:
                return False, "Gagal menghitung RS-Momentum. Mungkin tidak cukup data.", None
            
            # Step 5: Normalisasi data
            success = rrg_analyzer.normalize_data()
            if not success:
                return False, "Gagal melakukan normalisasi data. Mungkin tidak cukup variasi dalam data.", None
            
            # Step 6: Dapatkan hasil RRG
            rrg_results = rrg_analyzer.get_latest_data()
            
            # Analisis Fundamental jika diaktifkan
            combined_results = None
            if use_fundamental and analysis_type in ["Fundamental", "Gabungan (Teknikal + Fundamental)"]:
                # Konfigurasi indikator dan bobot fundamental
                indicators = []
                weights = {}
                
                include_roe = analysis_params.get('include_roe', True)
                include_roa = analysis_params.get('include_roa', True)
                include_profit_margin = analysis_params.get('include_profit_margin', True)
                include_earnings_growth = analysis_params.get('include_earnings_growth', True)
                include_debt_equity = analysis_params.get('include_debt_equity', True)
                
                roe_weight = analysis_params.get('roe_weight', 0.25)
                roa_weight = analysis_params.get('roa_weight', 0.20)
                pm_weight = analysis_params.get('pm_weight', 0.20)
                eg_weight = analysis_params.get('eg_weight', 0.20)
                de_weight = analysis_params.get('de_weight', 0.15)
                
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
                
                # Inisialisasi FundamentalAnalyzer
                fundamental_analyzer = FundamentalAnalyzer()
                
                # Set indikator dan bobot yang dipilih user
                if indicators:
                    fundamental_analyzer.fundamental_indicators = indicators
                    fundamental_analyzer.indicator_weights = weights
                
                # Ekstrak ticker dari hasil RRG
                tickers = rrg_results['Symbol'].tolist()
                
                # Dapatkan data fundamental
                refresh_fundamental = analysis_params.get('refresh_fundamental', False)
                fundamental_results = fundamental_analyzer.get_fundamental_analysis(tickers)
                
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
            
            # Ambil tanggal analisis
            analysis_date = rrg_analyzer.get_analysis_date().strftime('%d %B %Y')
            
            # Simpan hasil
            self.rrg_results = rrg_results
            self.combined_results = combined_results
            self.analysis_date = analysis_date
            
            return True, "Analisis berhasil.", {
                'rrg_results': rrg_results,
                'combined_results': combined_results,
                'analysis_date': analysis_date,
                'analysis_type': analysis_type,
                'use_fundamental': use_fundamental,
                'use_universe_score': use_universe_score
            }
            
        except Exception as e:
            return False, f"Terjadi kesalahan dalam analisis: {str(e)}", None
        
        finally:
            # Clean up temp files
            self.cleanup_temp_files()
    
    def cleanup_temp_files(self):
        """
        Membersihkan file sementara
        """
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass
        self.temp_files = []