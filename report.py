# report.py
# File untuk menangani pembuatan laporan PDF

import io
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import streamlit as st

def create_and_download_report(data, analysis_type, use_fundamental=False, use_universe_score=False):
    """
    Membuat laporan PDF berdasarkan hasil analisis
    
    :param data: DataFrame hasil analisis
    :param analysis_type: Jenis analisis yang dilakukan
    :param use_fundamental: Boolean apakah analisis fundamental aktif
    :param use_universe_score: Boolean apakah Stock Universe Score digunakan
    """
    # Tentukan apakah ini laporan untuk satu saham atau perbandingan
    num_stocks = len(data['Symbol'].unique())
    is_comparison = num_stocks > 1
    
    # Judul laporan
    if is_comparison:
        report_title = f"Laporan Perbandingan {num_stocks} Saham"
    else:
        report_title = f"Laporan Analisis Saham {data['Symbol'].iloc[0]}"
    
    # Buat buffer untuk menyimpan PDF
    buffer = io.BytesIO()
    
    # Buat dokumen PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Siapkan style
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='Title',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=1,  # Center
        spaceAfter=12
    ))
    styles.add(ParagraphStyle(
        name='Subtitle',
        parent=styles['Heading2'],
        fontSize=14,
        alignment=1,  # Center
        spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        name='Normal_Center',
        parent=styles['Normal'],
        alignment=1  # Center
    ))
    
    # Konten laporan
    content = []
    
    # Judul dan tanggal
    content.append(Paragraph(report_title, styles['Title']))
    content.append(Paragraph(f"Tanggal: {datetime.now().strftime('%d %B %Y')}", styles['Normal_Center']))
    content.append(Spacer(1, 12))
    
    # Ringkasan tipe analisis
    analysis_desc = "Analisis Teknikal (RRG)"
    if analysis_type == "Fundamental":
        analysis_desc = "Analisis Fundamental"
    elif analysis_type == "Gabungan (Teknikal + Fundamental)":
        analysis_desc = "Analisis Gabungan (Teknikal + Fundamental)"
        if use_universe_score:
            analysis_desc += " + Stock Universe Score"
            
    content.append(Paragraph(f"Jenis Analisis: {analysis_desc}", styles['Normal']))
    content.append(Spacer(1, 12))
    
    # Fungsi untuk menambahkan plot sebagai gambar ke PDF
    def add_figure_to_pdf(fig, width=7*inch, height=5*inch, caption=None):
        # Simpan plot ke buffer
        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format='png', bbox_inches='tight')
        img_buffer.seek(0)
        
        # Buat gambar dan tambahkan ke konten
        img = Image(img_buffer)
        img.drawWidth = width
        img.drawHeight = height
        content.append(img)
        
        # Tambahkan caption jika ada
        if caption:
            content.append(Paragraph(caption, styles['Normal_Center']))
        
        content.append(Spacer(1, 12))
        plt.close(fig)
    
    # BAGIAN I: VISUALISASI
    content.append(Paragraph("I. VISUALISASI", styles['Heading2']))
    content.append(Spacer(1, 6))
    
    # 1. Visualisasi RRG untuk semua kasus
    if 'RS-Ratio' in data.columns and 'RS-Momentum' in data.columns:
        content.append(Paragraph("1. Relative Rotation Graph (RRG)", styles['Heading3']))
        
        # Buat plot RRG
        fig_rrg, ax_rrg = plt.subplots(figsize=(10, 7))
        
        # Extract unique stocks and their latest data
        latest_data = data.drop_duplicates('Symbol', keep='last')
        
        # Scatter plot for each stock
        scatter = ax_rrg.scatter(
            latest_data['RS-Ratio'], 
            latest_data['RS-Momentum'],
            s=100, 
            alpha=0.7
        )
        
        # Label each point
        for _, row in latest_data.iterrows():
            ax_rrg.annotate(
                row['Symbol'],
                (row['RS-Ratio'], row['RS-Momentum']),
                xytext=(5, 5),
                textcoords='offset points',
                fontsize=9
            )
        
        # Garis referensi
        ax_rrg.axhline(y=100, color='gray', linestyle='--', alpha=0.5)
        ax_rrg.axvline(x=100, color='gray', linestyle='--', alpha=0.5)
        
        # Tambahkan label kuadran
        ax_rrg.text(105, 105, "Leading", fontsize=10, ha='left', va='bottom')
        ax_rrg.text(105, 95, "Weakening", fontsize=10, ha='left', va='top')
        ax_rrg.text(95, 105, "Improving", fontsize=10, ha='right', va='bottom')
        ax_rrg.text(95, 95, "Lagging", fontsize=10, ha='right', va='top')
        
        # Styling
        ax_rrg.set_title('Relative Rotation Graph (RRG)', fontsize=14)
        ax_rrg.set_xlabel('RS-Ratio', fontsize=12)
        ax_rrg.set_ylabel('RS-Momentum', fontsize=12)
        ax_rrg.grid(True, alpha=0.3)
        
        # Tambahkan plot ke PDF
        add_figure_to_pdf(fig_rrg, caption="Posisi saham pada kuadran RRG")
    
    # 2. Visualisasi Fundamental dan Universe Score jika tersedia
    if use_fundamental and 'Fundamental_Score' in data.columns:
        if is_comparison:
            # Jika perbandingan, tambahkan visualisasi radar
            content.append(Paragraph("2. Perbandingan Metrik Utama", styles['Heading3']))
            
            # Buat radar chart untuk perbandingan
            fig_radar = plot_stock_comparison_radar(data)
            if fig_radar:  # Pastikan radar chart berhasil dibuat
                add_figure_to_pdf(fig_radar, caption="Radar Chart Perbandingan Metrik Utama")
            
            # Tambahkan bar chart untuk metrik kunci
            content.append(Paragraph("3. Perbandingan Skor", styles['Heading3']))
            fig_bars = plot_comparison_bars(data)
            if fig_bars:  # Pastikan bar chart berhasil dibuat
                add_figure_to_pdf(fig_bars, caption="Perbandingan Nilai Metrik Kunci")
        else:
            # Jika single stock, tambahkan visualisasi gauge chart
            content.append(Paragraph("2. Skor & Metrik Utama", styles['Heading3']))
            
            # Buat gauge charts untuk metrik utama
            fig_gauges = plot_single_stock_gauges(data)
            if fig_gauges:  # Pastikan gauge chart berhasil dibuat
                add_figure_to_pdf(fig_gauges, caption="Gauge Chart Metrik Utama")
    
    # BAGIAN II: TABEL DATA
    content.append(Paragraph("II. DATA NUMERIK", styles['Heading2']))
    content.append(Spacer(1, 6))
    
    # Pilih kolom untuk ditampilkan di tabel
    table_columns = ['Symbol', 'RS-Ratio', 'RS-Momentum', 'Quadrant']
    if use_fundamental:
        table_columns.extend(['Fundamental_Score'])
    if use_universe_score:
        table_columns.extend(['Universe_Score'])
    if 'Combined_Score' in data.columns:
        table_columns.extend(['Combined_Score', 'Combined_Recommendation'])
    
    # Tambahkan kolom fundamental jika tersedia
    fundamental_cols = ['returnOnEquity', 'returnOnAssets', 'profitMargins', 'earningsGrowth', 'debtToEquity']
    for col in fundamental_cols:
        if col in data.columns:
            table_columns.append(col)
    
    # Filter kolom yang tersedia
    available_cols = [col for col in table_columns if col in data.columns]
    
    # Buat data tabel
    table_data = [available_cols]  # Header
    
    # Format numerik
    format_dict = {
        'RS-Ratio': '{:.2f}',
        'RS-Momentum': '{:.2f}',
        'Fundamental_Score': '{:.1f}',
        'Universe_Score': '{:.1f}',
        'Combined_Score': '{:.1f}',
        'returnOnEquity': '{:.2%}',
        'returnOnAssets': '{:.2%}',
        'profitMargins': '{:.2%}',
        'earningsGrowth': '{:.2%}',
        'debtToEquity': '{:.2f}'
    }
    
    # Tambahkan baris data
    for _, row in data.iterrows():
        row_data = []
        for col in available_cols:
            val = row[col]
            if pd.notna(val) and col in format_dict:
                try:
                    formatted_val = format_dict[col].format(val)
                except:
                    formatted_val = str(val)
            else:
                formatted_val = str(val) if pd.notna(val) else "N/A"
            row_data.append(formatted_val)
        table_data.append(row_data)
    
    # Buat tabel
    if len(table_data) > 1:
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        content.append(table)
    
    # BAGIAN III: KESIMPULAN DAN REKOMENDASI
    content.append(Spacer(1, 12))
    content.append(Paragraph("III. KESIMPULAN DAN REKOMENDASI", styles['Heading2']))
    content.append(Spacer(1, 6))
    
    if is_comparison:
        # Untuk perbandingan, berikan ringkasan tiap saham
        content.append(Paragraph("Ringkasan Perbandingan:", styles['Heading3']))
        
        # Urutkan saham berdasarkan Combined_Score jika tersedia
        if 'Combined_Score' in data.columns:
            sorted_stocks = data.sort_values('Combined_Score', ascending=False)
        else:
            sorted_stocks = data
            
        # Buat tabel ringkasan perbandingan
        comparison_summary = []
        
        # Tambahkan rekomendasi untuk setiap saham
        for _, row in sorted_stocks.drop_duplicates('Symbol').iterrows():
            symbol = row['Symbol']
            
            summary = f"<b>{symbol}</b>: "
            
            if 'Combined_Recommendation' in row:
                summary += f"<b>{row['Combined_Recommendation']}</b> "
                
            if 'Combined_Score' in row:
                summary += f"(Skor: {row['Combined_Score']:.1f}) - "
                
            if 'Quadrant' in row:
                summary += f"Kuadran RRG: {row['Quadrant']}, "
                
            if 'Fundamental_Score' in row and pd.notna(row['Fundamental_Score']):
                summary += f"Fundamental: {row['Fundamental_Score']:.1f}, "
                
            if 'Universe_Score' in row and pd.notna(row['Universe_Score']):
                summary += f"Universe: {row['Universe_Score']:.1f}"
                
            content.append(Paragraph(summary, styles['Normal']))
            content.append(Spacer(1, 6))
    else:
        # Untuk single stock, berikan analisis mendalam
        symbol = data['Symbol'].iloc[0]
        
        content.append(Paragraph(f"Analisis {symbol}:", styles['Heading3']))
        
        # Dapatkan rekomendasi jika tersedia
        recommendation = "N/A"
        combined_score = 0
        if 'Combined_Recommendation' in data.columns:
            recommendation = data['Combined_Recommendation'].iloc[0]
            combined_score = data['Combined_Score'].iloc[0]
        
        # Buat ringkasan analisis
        summary = f"<b>Rekomendasi: {recommendation}</b> (Skor: {combined_score:.1f})<br/><br/>"
        
        # Tambahkan analisis RRG
        if 'Quadrant' in data.columns:
            quadrant = data['Quadrant'].iloc[0]
            rs_ratio = data['RS-Ratio'].iloc[0]
            rs_momentum = data['RS-Momentum'].iloc[0]
            
            rr_analysis = f"<b>Analisis Teknikal (RRG):</b><br/>"
            rr_analysis += f"Saham {symbol} berada pada kuadran <b>{quadrant}</b> dengan "
            rr_analysis += f"RS-Ratio {rs_ratio:.2f} dan RS-Momentum {rs_momentum:.2f}.<br/>"
            
            if quadrant == "Leading":
                rr_analysis += "Saham ini menunjukkan kekuatan relatif dan momentum positif. "
                rr_analysis += "Posisi di kuadran Leading mengindikasikan performa yang baik dibandingkan benchmark."
            elif quadrant == "Weakening":
                rr_analysis += "Saham ini memiliki kekuatan relatif tinggi namun momentum mulai menurun. "
                rr_analysis += "Perhatikan perkembangan momentum di periode mendatang."
            elif quadrant == "Lagging":
                rr_analysis += "Saham ini menunjukkan kekuatan relatif rendah dan momentum negatif. "
                rr_analysis += "Berhati-hatilah karena posisi di kuadran Lagging mengindikasikan underperformance."
            elif quadrant == "Improving":
                rr_analysis += "Saham ini memiliki kekuatan relatif rendah namun momentum mulai meningkat. "
                rr_analysis += "Perhatikan potensi pemulihan di periode mendatang."
            
            summary += rr_analysis + "<br/><br/>"
        
        # Tambahkan analisis fundamental
        if use_fundamental and 'Fundamental_Score' in data.columns:
            f_score = data['Fundamental_Score'].iloc[0]
            
            f_analysis = f"<b>Analisis Fundamental:</b><br/>"
            f_analysis += f"Skor fundamental {symbol} adalah <b>{f_score:.1f}</b> dari 100.<br/>"
            
            # Tambahkan detail metrik fundamental jika tersedia
            for metric in fundamental_cols:
                if metric in data.columns and pd.notna(data[metric].iloc[0]):
                    # Format nilai metrik
                    if metric in ['returnOnEquity', 'returnOnAssets', 'profitMargins', 'earningsGrowth']:
                        val = f"{data[metric].iloc[0]:.2%}"
                    else:
                        val = f"{data[metric].iloc[0]:.2f}"
                    
                    # Nama metrik yang lebih user-friendly
                    metric_name = {
                        'returnOnEquity': 'Return on Equity (ROE)',
                        'returnOnAssets': 'Return on Assets (ROA)',
                        'profitMargins': 'Profit Margin',
                        'earningsGrowth': 'Earnings Growth',
                        'debtToEquity': 'Debt to Equity'
                    }.get(metric, metric)
                    
                    f_analysis += f"- {metric_name}: {val}<br/>"
            
            summary += f_analysis + "<br/><br/>"
        
        # Tambahkan analisis Universe Score jika tersedia
        if use_universe_score and 'Universe_Score' in data.columns:
            u_score = data['Universe_Score'].iloc[0]
            
            u_analysis = f"<b>Stock Universe Score:</b><br/>"
            u_analysis += f"Skor Universe {symbol} adalah <b>{u_score:.1f}</b> dari 100.<br/>"
            u_analysis += "Stock Universe Score merepresentasikan kesehatan emiten berdasarkan laba 3 tahun terakhir, total return (dividen + capital gain), dan notasi khusus di bursa."
            
            summary += u_analysis + "<br/><br/>"
        
        # Tambahkan kesimpulan
        conclusion = "<b>Kesimpulan:</b><br/>"
        conclusion += f"Berdasarkan analisis gabungan, saham {symbol} mendapatkan rekomendasi <b>{recommendation}</b> "
        conclusion += f"dengan skor gabungan {combined_score:.1f} dari 100."
        
        # Tambahkan indikasi bobot
        if use_universe_score and use_fundamental:
            conclusion += "<br/><br/>Skor gabungan dihitung dengan bobot:<br/>"
            conclusion += "- 40% Stock Universe Score<br/>"
            conclusion += "- 30% Skor Fundamental<br/>"
            conclusion += "- 30% Skor RS-Momentum (Technical)"
        
        summary += conclusion
        
        content.append(Paragraph(summary, styles['Normal']))
    
    # BAGIAN IV: DISCLAIMER
    content.append(Spacer(1, 12))
    content.append(Paragraph("IV. DISCLAIMER", styles['Heading2']))
    content.append(Spacer(1, 6))
    
    disclaimer = """
    <i>Laporan ini dibuat secara otomatis berdasarkan data yang tersedia. Hasil analisis dan rekomendasi 
    hanya sebagai referensi dan bukan merupakan saran investasi. Investor disarankan untuk melakukan 
    riset mandiri dan berkonsultasi dengan penasihat keuangan sebelum mengambil keputusan investasi. 
    Performa masa lalu tidak menjamin hasil di masa depan.</i>
    """
    content.append(Paragraph(disclaimer, styles['Normal']))
    
    # Tambahkan footer
    content.append(Spacer(1, 12))
    content.append(Paragraph(f"Dibuat dengan Comprehensive Stock Analyzer | {datetime.now().strftime('%d %B %Y, %H:%M')}", styles['Normal_Center']))
    
    # Buat PDF
    doc.build(content)
    
    # Posisikan kursor di awal buffer
    buffer.seek(0)
    
    # Generate file name
    if is_comparison:
        filename = f"stock_comparison_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    else:
        filename = f"{data['Symbol'].iloc[0]}_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    
    # Download file
    st.download_button(
        label="📥 Download PDF Report",
        data=buffer,
        file_name=filename,
        mime="application/pdf",
        key="download_report"
    )

def plot_stock_comparison_radar(comparison_data):
    """
    Membuat radar chart untuk membandingkan beberapa saham berdasarkan metrik utama
    """
    # Metrik yang akan dibandingkan (pilih 5-7 metrik paling relevan)
    metrics = [
        'Universe_Score', 
        'Fundamental_Score', 
        'RS-Ratio', 
        'RS-Momentum'
    ]
    
    # Tambahkan metrik fundamental jika tersedia
    additional_metrics = [
        'returnOnEquity', 
        'profitMargins', 
        'returnOnAssets'
    ]
    
    for metric in additional_metrics:
        if metric in comparison_data.columns and not comparison_data[metric].isnull().all():
            metrics.append(metric)
    
    # Pastikan semua metrik ada di data
    available_metrics = [m for m in metrics if m in comparison_data.columns]
    
    # Jika kurang dari 3 metrik tersedia, tampilkan pesan error
    if len(available_metrics) < 3:
        return None
    
    # Normalisasi data untuk radar chart (semua nilai harus 0-1)
    normalized_data = comparison_data.copy()
    
    for metric in available_metrics:
        max_val = normalized_data[metric].max()
        min_val = normalized_data[metric].min()
        
        if max_val > min_val:
            normalized_data[metric] = (normalized_data[metric] - min_val) / (max_val - min_val)
        else:
            normalized_data[metric] = 0.5  # Jika tidak ada variasi, set ke 0.5
    
    # Set up radar chart
    from matplotlib.path import Path
    from matplotlib.spines import Spine
    from matplotlib.transforms import Affine2D
    from matplotlib.projections.polar import PolarAxes
    from matplotlib.projections import register_projection
    
    def radar_factory(num_vars, frame='circle'):
        """Create a radar chart with `num_vars` axes."""
        # Calculate evenly-spaced axis angles
        theta = np.linspace(0, 2*np.pi, num_vars, endpoint=False)

        class RadarAxes(PolarAxes):
            name = 'radar'
            
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.set_theta_zero_location('N')

            def fill(self, *args, closed=True, **kwargs):
                """Override fill so that line is closed by default"""
                return super().fill(closed=closed, *args, **kwargs)

            def plot(self, *args, **kwargs):
                """Override plot so that line is closed by default"""
                lines = super().plot(*args, **kwargs)
                for line in lines:
                    self._close_line(line)
                return lines

            def _close_line(self, line):
                x, y = line.get_data()
                if x[0] != x[-1]:
                    x = np.append(x, x[0])
                    y = np.append(y, y[0])
                    line.set_data(x, y)

            def set_varlabels(self, labels):
                self.set_thetagrids(np.degrees(theta), labels)

        register_projection(RadarAxes)
        return theta
    
    num_vars = len(available_metrics)
    theta = radar_factory(num_vars)
    
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='radar'))
    
    # Plot data
    colors = plt.cm.tab10(np.linspace(0, 1, len(normalized_data)))
    
    # Dapatkan data unik per saham
    unique_stocks = normalized_data.drop_duplicates('Symbol')
    
    for i, (_, row) in enumerate(unique_stocks.iterrows()):
        values = [row[metric] for metric in available_metrics]
        ax.plot(theta, values, color=colors[i], linewidth=2, label=row['Symbol'])
        ax.fill(theta, values, color=colors[i], alpha=0.1)
    
    # Tambahkan label dan styling
    ax.set_thetagrids(np.degrees(theta), [metric.replace('_', ' ').replace('return', 'ROE') for metric in available_metrics])
    plt.legend(loc='upper right')
    
    plt.title('Perbandingan Metrik Saham', size=15)
    
    return fig

def plot_comparison_bars(comparison_data):
    """
    Membuat bar chart untuk membandingkan metrik-metrik penting antara saham
    """
    # Metrik yang akan dibandingkan
    key_metrics = [
        'Universe_Score', 
        'Fundamental_Score', 
        'Combined_Score'
    ]
    
    # Metrik tambahan jika tersedia
    additional_metrics = [
        'returnOnEquity', 
        'profitMargins'
    ]
    
    # Tambahkan metrik tambahan jika tersedia
    for metric in additional_metrics:
        if metric in comparison_data.columns and not comparison_data[metric].isnull().all():
            key_metrics.append(metric)
    
    # Filter metrik yang tersedia
    available_metrics = [m for m in key_metrics if m in comparison_data.columns]
    
    # Jika tidak ada metrik tersedia, return None
    if len(available_metrics) == 0:
        return None
    
    # Buat subplot untuk setiap metrik
    num_metrics = len(available_metrics)
    fig, axes = plt.subplots(num_metrics, 1, figsize=(8, num_metrics * 1.5), constrained_layout=True)
    
    if num_metrics == 1:
        axes = [axes]  # Pastikan axes selalu list untuk iterasi
    
    # Dapatkan data unik per saham
    unique_stocks = comparison_data.drop_duplicates('Symbol')
    symbols = unique_stocks['Symbol'].tolist()
    
    # Warna untuk setiap saham
    colors = plt.cm.tab10(np.linspace(0, 1, len(symbols)))
    
    # Plot bar chart untuk setiap metrik
    for i, metric in enumerate(available_metrics):
        ax = axes[i]
        
        # Data untuk metrik ini
        values = [unique_stocks[unique_stocks['Symbol'] == symbol][metric].iloc[0] for symbol in symbols]
        
        # Plot bars
        bars = ax.bar(symbols, values, color=colors)
        
        # Tambahkan nilai di atas bars
        for bar, value in zip(bars, values):
            if pd.notna(value):  # Tambahkan pengecekan nilai NaN
                height = bar.get_height()
                format_str = '{:.2f}' if metric not in ['Universe_Score', 'Fundamental_Score', 'Combined_Score'] else '{:.0f}'
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.05 * max(values), 
                        format_str.format(value), ha='center', va='bottom')
        
        # Styling
        metric_label = metric.replace('_', ' ')
        if metric in ['returnOnEquity', 'returnOnAssets', 'profitMargins']:
            ax.set_ylabel(f"{metric_label} (%)")
            # Format y-axis sebagai persentase
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: '{:.0%}'.format(x)))
        else:
            ax.set_ylabel(metric_label)
        
        ax.set_title(f"{metric_label}")
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Atur batas y untuk konsistensi
        if metric in ['Universe_Score', 'Fundamental_Score', 'Combined_Score']:
            ax.set_ylim(0, 105)  # Sedikit lebih tinggi untuk ruang label
    
    plt.tight_layout()
    return fig

def plot_single_stock_gauges(data):
    """
    Membuat gauge charts untuk metrik utama satu saham
    """
    # Pastikan data hanya berisi satu saham
    if len(data['Symbol'].unique()) > 1:
        # Filter hanya baris pertama jika ada lebih dari satu saham
        data = data.iloc[[0]]
    
    # Tentukan metrik yang akan ditampilkan
    stock_metrics = []
    
    # Tambahkan metrik inti
    core_metrics = [
        ('Universe_Score', 'Universe Score', 100),
        ('Fundamental_Score', 'Fundamental Score', 100),
        ('Combined_Score', 'Combined Score', 100),
        ('RS-Ratio', 'RS-Ratio', 120),  # Nilai max RRG sekitar 120
        ('RS-Momentum', 'RS-Momentum', 120)
    ]
    
    for metric, label, max_val in core_metrics:
        if metric in data.columns and pd.notna(data[metric].iloc[0]):
            stock_metrics.append((metric, label, max_val))
    
    # Tambahkan metrik fundamental jika tersedia
    fund_metrics = [
        ('returnOnEquity', 'Return on Equity', 0.3),
        ('returnOnAssets', 'Return on Assets', 0.2),
        ('profitMargins', 'Profit Margin', 0.3),
        ('earningsGrowth', 'Earnings Growth', 0.3)
    ]
    
    for metric, label, max_val in fund_metrics:
        if metric in data.columns and pd.notna(data[metric].iloc[0]):
            stock_metrics.append((metric, label, max_val))
    
    # Kalau tidak ada metrik yang tersedia, return None
    if not stock_metrics:
        return None
    
    # Jumlah metrik yang ditampilkan
    n_metrics = len(stock_metrics)
    n_cols = min(3, n_metrics)  # Maksimal 3 kolom
    n_rows = (n_metrics + n_cols - 1) // n_cols  # Pembulatan ke atas untuk jumlah baris
    
    # Buat figure dengan subplot dalam grid
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(4*n_cols, 3*n_rows))
    
    # Flatten axes jika ada lebih dari satu subplot
    if n_metrics > 1:
        axes = axes.flatten()
    else:
        axes = [axes]
    
    # Buat gauge chart untuk setiap metrik
    for i, (metric, label, max_val) in enumerate(stock_metrics):
        ax = axes[i]
        
        value = data[metric].iloc[0]
        
        # Normalisasi nilai untuk gauge (0-100% dari max_val)
        if metric in ['returnOnEquity', 'returnOnAssets', 'profitMargins', 'earningsGrowth']:
            # Konversi nilai persen (0-1) ke persen dari max_val
            gauge_value = min(1, max(0, value / max_val))
            # Format display value sebagai persentase
            display_value = f"{value:.1%}"
        else:
            # Nilai lain (skor, rasio) - normalisasi ke range 0-1
            gauge_value = min(1, max(0, value / max_val))
            # Format display value sebagai angka biasa
            display_value = f"{value:.1f}"
        
        # Tentukan warna gauge berdasarkan nilai
        # Hijau untuk nilai tinggi, kuning untuk menengah, merah untuk rendah
        if gauge_value > 0.7:
            color = 'green'
        elif gauge_value > 0.4:
            color = 'orange'
        else:
            color = 'red'
            
        # Khusus untuk debt to equity, inversikan warnanya (nilai rendah lebih baik)
        if metric == 'debtToEquity':
            if gauge_value < 0.3:
                color = 'green'
            elif gauge_value < 0.6:
                color = 'orange'
            else:
                color = 'red'
        
        # Buat arc gauge
        theta = np.linspace(0, 180, 100)
        
        # Konversi ke radians
        theta = theta * np.pi / 180.0
        
        # Koordinat x dan y untuk arc
        x = np.cos(theta)
        y = np.sin(theta)
        
        # Buat arc background (abu-abu)
        ax.plot(x, y, 'lightgrey', linewidth=10)
        
        # Buat arc gauge berdasarkan nilai
        gauge_theta = np.linspace(0, 180 * gauge_value, 100)
        gauge_theta = gauge_theta * np.pi / 180.0
        gauge_x = np.cos(gauge_theta)
        gauge_y = np.sin(gauge_theta)
        
        ax.plot(gauge_x, gauge_y, color, linewidth=10)
        
        # Tambahkan nilai di tengah gauge
        ax.text(0, 0, display_value, fontsize=14, fontweight='bold', ha='center', va='center')
        
        # Tambahkan label di bawah gauge
        ax.text(0, -0.5, label, fontsize=12, ha='center', va='center')
        
        # Styling
        ax.set_xlim(-1.1, 1.1)
        ax.set_ylim(-0.6, 1.1)
        ax.set_aspect('equal')
        ax.axis('off')
    
    # Sembunyikan subplot yang tidak digunakan
    for i in range(n_metrics, len(axes)):
        axes[i].axis('off')
    
    plt.tight_layout()
    return fig

def add_report_button_to_app(app_file):
    """
    Menambahkan tombol Generate Report ke app.py
    """
    # Tambahkan import
    insert_import = "from report import create_and_download_report\n"
    
    # Temukan baris yang tepat untuk menambahkan tombol
    # Biasanya setelah menampilkan semua hasil analisis
    with open(app_file, 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    import_added = False
    report_button_added = False
    
    for line in lines:
        new_lines.append(line)
        
        # Tambahkan import di bagian awal file
        if 'import' in line and not import_added:
            new_lines.append(insert_import)
            import_added = True
        
        # Tambahkan tombol report di bagian yang tepat
        if '# Tambahkan catatan tentang data fundamental' in line and not report_button_added:
            report_button_code = """
    # Tambahkan tombol untuk generate report
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
            """
            new_lines.append(report_button_code)
            report_button_added = True
    
    # Tulis kembali ke file
    with open(app_file, 'w') as f:
        f.writelines(new_lines)
    
    return True