def create_and_download_report(data, analysis_type, use_fundamental=False, use_universe_score=False):
    """
    Membuat laporan PDF berdasarkan hasil analisis
    
    :param data: DataFrame hasil analisis
    :param analysis_type: Jenis analisis yang dilakukan
    :param use_fundamental: Boolean apakah analisis fundamental aktif
    :param use_universe_score: Boolean apakah Stock Universe Score digunakan
    """
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    import matplotlib.pyplot as plt
    import io
    import base64
    from datetime import datetime
    from reportlab.platypus.flowables import HRFlowable
    
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
        rightMargin=36,  # Mengurangi margin untuk lebih banyak ruang
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    # Siapkan style
    styles = getSampleStyleSheet()
    
    # Tambahkan style baru hanya jika belum ada
    def add_style_if_not_exists(name, parent_style, **kwargs):
        if name not in styles:
            styles.add(ParagraphStyle(
                name=name,
                parent=styles[parent_style],
                **kwargs
            ))
    
    # Tambahkan style yang diperlukan dengan peningkatan ukuran font dan spasi
    add_style_if_not_exists(
        'CustomTitle',
        'Heading1',
        fontSize=24,  # Ukuran font lebih besar
        alignment=1,  # Center
        spaceAfter=16,
        textColor=colors.darkblue  # Warna font yang lebih menarik
    )
    
    add_style_if_not_exists(
        'Subtitle',
        'Heading2',
        fontSize=18,  # Ukuran font lebih besar
        alignment=1,  # Center
        spaceAfter=12,
        textColor=colors.darkblue
    )
    
    add_style_if_not_exists(
        'Heading3',
        'Heading3',
        fontSize=16,
        textColor=colors.darkblue,
        spaceAfter=10
    )
    
    add_style_if_not_exists(
        'Normal_Center',
        'Normal',
        fontSize=12,
        alignment=1  # Center
    )
    
    add_style_if_not_exists(
        'Normal_Bold',
        'Normal',
        fontSize=12,
        fontName='Helvetica-Bold'
    )
    
    add_style_if_not_exists(
        'TableHeader',
        'Normal',
        fontSize=12,
        fontName='Helvetica-Bold',
        textColor=colors.white,
        alignment=1
    )
    
    # Konten laporan
    content = []
    
    # Judul dan tanggal
    content.append(Paragraph(report_title, styles['CustomTitle']))
    content.append(HRFlowable(width="100%", thickness=2, color=colors.darkblue, spaceBefore=10, spaceAfter=10))
    content.append(Paragraph(f"Tanggal: {datetime.now().strftime('%d %B %Y')}", styles['Normal_Center']))
    content.append(Paragraph(f"Jenis Analisis: {analysis_type}", styles['Normal_Center']))
    if use_universe_score:
        content.append(Paragraph("Termasuk Stock Universe Score", styles['Normal_Center']))
    content.append(Spacer(1, 20))
    
    # Fungsi untuk menambahkan plot sebagai gambar ke PDF
    def add_figure_to_pdf(fig, width=7.5*inch, height=5*inch, caption=None, background_color="#f0f0f0"):
        """
        Menambahkan gambar ke PDF dengan background color
        """
        # Setel background color pada figure
        if background_color:
            fig.patch.set_facecolor(background_color)
            if hasattr(fig, 'axes'):
                for ax in fig.axes:
                    ax.set_facecolor(background_color)
        
        # Simpan plot ke buffer
        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format='png', bbox_inches='tight', facecolor=background_color, dpi=300)
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
    content.append(Paragraph("I. VISUALISASI", styles['Subtitle']))
    content.append(Spacer(1, 6))
    
    # 1. Visualisasi RRG untuk semua kasus
    if 'RS-Ratio' in data.columns and 'RS-Momentum' in data.columns:
        content.append(Paragraph("1. Relative Rotation Graph (RRG)", styles['Heading3']))
        
        # Buat plot RRG dengan grid dan background yang lebih jelas
        fig_rrg, ax_rrg = plt.subplots(figsize=(10, 7), facecolor='#f0f0f0')
        ax_rrg.set_facecolor('#f0f0f0')
        
        # Ekstrak unique stocks dan data terakhir
        latest_data = data.drop_duplicates('Symbol', keep='last')
        
        # Scatter plot untuk setiap saham
        scatter = ax_rrg.scatter(
            latest_data['RS-Ratio'], 
            latest_data['RS-Momentum'],
            s=150,  # Ukuran marker lebih besar 
            alpha=0.8,
            edgecolors='black'  # Menambahkan outline
        )
        
        # Label setiap titik
        for _, row in latest_data.iterrows():
            ax_rrg.annotate(
                row['Symbol'],
                (row['RS-Ratio'], row['RS-Momentum']),
                xytext=(7, 7),
                textcoords='offset points',
                fontsize=12,
                fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8)
            )
        
        # Buat area kuadran dengan warna latar
        ax_rrg.axhspan(100, ax_rrg.get_ylim()[1], xmin=0, xmax=0.5, alpha=0.1, color='blue')  # Improving
        ax_rrg.axhspan(100, ax_rrg.get_ylim()[1], xmin=0.5, xmax=1, alpha=0.1, color='green')  # Leading
        ax_rrg.axhspan(ax_rrg.get_ylim()[0], 100, xmin=0.5, xmax=1, alpha=0.1, color='yellow')  # Weakening
        ax_rrg.axhspan(ax_rrg.get_ylim()[0], 100, xmin=0, xmax=0.5, alpha=0.1, color='red')  # Lagging
        
        # Garis referensi yang lebih tegas
        ax_rrg.axhline(y=100, color='black', linestyle='-', alpha=0.5, linewidth=1.5)
        ax_rrg.axvline(x=100, color='black', linestyle='-', alpha=0.5, linewidth=1.5)
        
        # Tambahkan label kuadran dengan kotak background
        props = dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='gray')
        ax_rrg.text(105, 105, "Leading", fontsize=12, fontweight='bold', ha='left', va='bottom', bbox=props)
        ax_rrg.text(105, 95, "Weakening", fontsize=12, fontweight='bold', ha='left', va='top', bbox=props)
        ax_rrg.text(95, 105, "Improving", fontsize=12, fontweight='bold', ha='right', va='bottom', bbox=props)
        ax_rrg.text(95, 95, "Lagging", fontsize=12, fontweight='bold', ha='right', va='top', bbox=props)
        
        # Styling
        ax_rrg.set_title('Relative Rotation Graph (RRG)', fontsize=16, fontweight='bold')
        ax_rrg.set_xlabel('RS-Ratio', fontsize=14, fontweight='bold')
        ax_rrg.set_ylabel('RS-Momentum', fontsize=14, fontweight='bold')
        ax_rrg.grid(True, alpha=0.5, linestyle='--')
        ax_rrg.tick_params(axis='both', which='major', labelsize=12)
        
        # Tambahkan plot ke PDF
        add_figure_to_pdf(fig_rrg, caption="Posisi saham pada kuadran RRG", background_color="#f0f0f0")
        
        # Tambahkan page break setelah grafik RRG
        content.append(PageBreak())
    
    # 2. Visualisasi Fundamental dan Universe Score jika tersedia
    if use_fundamental and 'Fundamental_Score' in data.columns:
        if is_comparison:
            # Jika perbandingan, tambahkan visualisasi radar
            content.append(Paragraph("2. Perbandingan Metrik Utama", styles['Heading3']))
            
            # ... (kode untuk radar chart)
            
        else:
            # Jika single stock, tambahkan visualisasi gauges untuk metrik utama
            content.append(Paragraph("2. Skor & Metrik Utama", styles['Heading3']))
            
            # Buat gauge charts untuk metrik utama dengan background yang lebih jelas
            # ... (kode untuk gauge chart dengan perbaikan tampilan)
    
    # Tambahkan page break sebelum tabel data
    content.append(PageBreak())
    
    # BAGIAN II: TABEL DATA
    content.append(Paragraph("II. DATA NUMERIK", styles['Subtitle']))
    content.append(Spacer(1, 12))
    
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
    
    # Buat tabel dengan styling yang lebih baik
    if len(table_data) > 1:
        # Hitung lebar kolom berdasarkan jumlah kolom
        col_widths = [1.5*inch] + [(7.5*inch) / (len(available_cols)-1)] * (len(available_cols)-1)
        
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Style tabel yang lebih menarik dengan warna alternating
        table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBEFORE', (0, 0), (0, -1), 1, colors.black),
        ]
        
        # Alternating row colors
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                table_style.append(('BACKGROUND', (0, i), (-1, i), colors.lightgrey))
        
        # Highlighting quadrants
        if 'Quadrant' in available_cols:
            quadrant_col = available_cols.index('Quadrant')
            for i in range(1, len(table_data)):
                quadrant = table_data[i][quadrant_col]
                if quadrant == "Leading":
                    table_style.append(('BACKGROUND', (quadrant_col, i), (quadrant_col, i), colors.lightgreen))
                elif quadrant == "Weakening":
                    table_style.append(('BACKGROUND', (quadrant_col, i), (quadrant_col, i), colors.lightyellow))
                elif quadrant == "Lagging":
                    table_style.append(('BACKGROUND', (quadrant_col, i), (quadrant_col, i), colors.lightcoral))
                elif quadrant == "Improving":
                    table_style.append(('BACKGROUND', (quadrant_col, i), (quadrant_col, i), colors.lightblue))
        
        # Highlighting recommendations
        if 'Combined_Recommendation' in available_cols:
            rec_col = available_cols.index('Combined_Recommendation')
            for i in range(1, len(table_data)):
                rec = table_data[i][rec_col]
                if rec == "Strong Buy":
                    table_style.append(('BACKGROUND', (rec_col, i), (rec_col, i), colors.green))
                    table_style.append(('TEXTCOLOR', (rec_col, i), (rec_col, i), colors.white))
                elif rec == "Buy":
                    table_style.append(('BACKGROUND', (rec_col, i), (rec_col, i), colors.lightgreen))
                elif rec == "Hold":
                    table_style.append(('BACKGROUND', (rec_col, i), (rec_col, i), colors.lightgrey))
                elif rec == "Reduce":
                    table_style.append(('BACKGROUND', (rec_col, i), (rec_col, i), colors.lightyellow))
                elif rec == "Sell":
                    table_style.append(('BACKGROUND', (rec_col, i), (rec_col, i), colors.lightcoral))
        
        table.setStyle(TableStyle(table_style))
        content.append(table)
    
    # Page break sebelum kesimpulan
    content.append(PageBreak())
    
    # BAGIAN III: KESIMPULAN DAN REKOMENDASI
    content.append(Paragraph("III. KESIMPULAN DAN REKOMENDASI", styles['Subtitle']))
    content.append(Spacer(1, 12))
    
    if is_comparison:
        # Untuk perbandingan, berikan ringkasan tiap saham
        content.append(Paragraph("Ringkasan Perbandingan:", styles['Heading3']))
        
        # ... (kode untuk perbandingan)
        
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
        
        # Buat ringkasan analisis dengan formatting HTML yang lebih baik
        summary = f"<b>Rekomendasi: <font color='darkgreen'>{recommendation}</font></b> (Skor: {combined_score:.1f})<br/><br/>"
        
        # Tambahkan analisis RRG dengan penekanan visual
        if 'Quadrant' in data.columns:
            quadrant = data['Quadrant'].iloc[0]
            rs_ratio = data['RS-Ratio'].iloc[0]
            rs_momentum = data['RS-Momentum'].iloc[0]
            
            # Tentukan warna untuk quadrant
            quadrant_color = "black"
            if quadrant == "Leading":
                quadrant_color = "green"
            elif quadrant == "Weakening":
                quadrant_color = "orange"
            elif quadrant == "Lagging":
                quadrant_color = "red"
            elif quadrant == "Improving":
                quadrant_color = "blue"
            
            rr_analysis = f"<b>Analisis Teknikal (RRG):</b><br/>"
            rr_analysis += f"Saham {symbol} berada pada kuadran <b><font color='{quadrant_color}'>{quadrant}</font></b> dengan "
            rr_analysis += f"RS-Ratio {rs_ratio:.2f} dan RS-Momentum {rs_momentum:.2f}.<br/>"
            
            if quadrant == "Leading":
                rr_analysis += "Saham ini menunjukkan <b>kekuatan relatif dan momentum positif</b>. "
                rr_analysis += "Posisi di kuadran Leading mengindikasikan performa yang baik dibandingkan benchmark."
            elif quadrant == "Weakening":
                rr_analysis += "Saham ini memiliki <b>kekuatan relatif tinggi namun momentum mulai menurun</b>. "
                rr_analysis += "Perhatikan perkembangan momentum di periode mendatang."
            elif quadrant == "Lagging":
                rr_analysis += "Saham ini menunjukkan <b>kekuatan relatif rendah dan momentum negatif</b>. "
                rr_analysis += "Berhati-hatilah karena posisi di kuadran Lagging mengindikasikan underperformance."
            elif quadrant == "Improving":
                rr_analysis += "Saham ini memiliki <b>kekuatan relatif rendah namun momentum mulai meningkat</b>. "
                rr_analysis += "Perhatikan potensi pemulihan di periode mendatang."
            
            summary += rr_analysis + "<br/><br/>"
        
        # Tambahkan analisis fundamental
        if use_fundamental and 'Fundamental_Score' in data.columns:
            f_score = data['Fundamental_Score'].iloc[0]
            
            # Tentukan kategori dan warna untuk skor fundamental
            f_category = "Lemah"
            f_color = "red"
            if f_score > 70:
                f_category = "Kuat"
                f_color = "green"
            elif f_score > 40:
                f_category = "Rata-rata"
                f_color = "orange"
            
            f_analysis = f"<b>Analisis Fundamental:</b><br/>"
            f_analysis += f"Skor fundamental {symbol} adalah <b><font color='{f_color}'>{f_score:.1f}</font></b> dari 100 "
            f_analysis += f"(<font color='{f_color}'>{f_category}</font>).<br/>"
            
            # Tambahkan detail metrik fundamental jika tersedia
            f_analysis += "<table border='0' cellpadding='5'>"
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
                    
                    f_analysis += f"<tr><td><b>{metric_name}:</b></td><td>{val}</td></tr>"
            f_analysis += "</table>"
            
            summary += f_analysis + "<br/><br/>"
        
        # Tambahkan analisis Universe Score jika tersedia
        if use_universe_score and 'Universe_Score' in data.columns:
            u_score = data['Universe_Score'].iloc[0]
            
            # Tentukan kategori dan warna untuk universe score
            u_category = "Lemah"
            u_color = "red"
            if u_score > 70:
                u_category = "Kuat"
                u_color = "green"
            elif u_score > 40:
                u_category = "Rata-rata"
                u_color = "orange"
            
            u_analysis = f"<b>Stock Universe Score:</b><br/>"
            u_analysis += f"Skor Universe {symbol} adalah <b><font color='{u_color}'>{u_score:.1f}</font></b> dari 100 "
            u_analysis += f"(<font color='{u_color}'>{u_category}</font>).<br/>"
            u_analysis += "Stock Universe Score merepresentasikan kesehatan emiten berdasarkan laba 3 tahun terakhir, total return (dividen + capital gain), dan notasi khusus di bursa."
            
            summary += u_analysis + "<br/><br/>"
        
        # Tambahkan kesimpulan dengan kotak pembatas
        conclusion = "<div style='border:1px solid #aaa; padding:10px; background-color:#f8f8f8;'>"
        conclusion += "<b>Kesimpulan:</b><br/>"
        conclusion += f"Berdasarkan analisis gabungan, saham {symbol} mendapatkan rekomendasi <b><font color='darkgreen'>{recommendation}</font></b> "
        conclusion += f"dengan skor gabungan {combined_score:.1f} dari 100."
        
        # Tambahkan indikasi bobot
        if use_universe_score and use_fundamental:
            conclusion += "<br/><br/><b>Skor gabungan</b> dihitung dengan bobot:<br/>"
            conclusion += "- 40% Stock Universe Score<br/>"
            conclusion += "- 30% Skor Fundamental<br/>"
            conclusion += "- 30% Skor RS-Momentum (Technical)"
        conclusion += "</div>"
        
        summary += conclusion
        
        content.append(Paragraph(summary, styles['Normal']))
    
    # BAGIAN IV: DISCLAIMER
    content.append(Spacer(1, 20))
    content.append(HRFlowable(width="100%", thickness=1, color=colors.darkblue, spaceBefore=10, spaceAfter=10))
    content.append(Paragraph("IV. DISCLAIMER", styles['Heading3']))
    content.append(Spacer(1, 6))
    
    disclaimer = """
    <i>Laporan ini dibuat secara otomatis berdasarkan data yang tersedia. Hasil analisis dan rekomendasi 
    hanya sebagai referensi dan bukan merupakan saran investasi. Investor disarankan untuk melakukan 
    riset mandiri dan berkonsultasi dengan penasihat keuangan sebelum mengambil keputusan investasi. 
    Performa masa lalu tidak menjamin hasil di masa depan.</i>
    """
    content.append(Paragraph(disclaimer, styles['Normal']))
    
    # Tambahkan footer
    content.append(Spacer(1, 20))
    content.append(HRFlowable(width="100%", thickness=1, color=colors.darkblue, spaceBefore=5, spaceAfter=5))
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
