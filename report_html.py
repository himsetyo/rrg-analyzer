# report_html.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge
import matplotlib.patches as mpatches
import io
import base64
import numpy as np
from datetime import datetime

def create_html_report(data, analysis_type, use_fundamental=False, use_universe_score=False):
    """
    Membuat laporan HTML dari hasil analisis
    
    :param data: DataFrame hasil analisis
    :param analysis_type: Jenis analisis yang dilakukan
    :param use_fundamental: Boolean apakah analisis fundamental aktif
    :param use_universe_score: Boolean apakah Stock Universe Score digunakan
    :return: String HTML dan filename
    """
    # Cek apakah ini analisis perbandingan atau saham tunggal
    num_stocks = len(data['Symbol'].unique())
    is_comparison = num_stocks > 1
    
    # Siapkan nama file
    if is_comparison:
        filename = f"stock_comparison_report_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
    else:
        filename = f"{data['Symbol'].iloc[0]}_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
    
    # Generate plots sebagai base64 images
    rrg_plot_base64 = create_rrg_plot_base64(data)
    
    # Jika perbandingan, buat radar chart dan bar chart
    radar_chart_base64 = ""
    bar_chart_base64 = ""
    if is_comparison and num_stocks <= 5:  # Batasi untuk 5 saham
        radar_chart_base64 = create_radar_chart_base64(data)
        bar_chart_base64 = create_bar_chart_base64(data)
    
    # Jika saham tunggal, buat gauge charts
    gauge_charts_base64 = ""
    if not is_comparison:
        gauge_charts_base64 = create_gauge_charts_base64(data, use_fundamental, use_universe_score)
    
    # Generate HTML content
    html_content = generate_html_content(
        data, 
        analysis_type, 
        use_fundamental, 
        use_universe_score,
        is_comparison,
        rrg_plot_base64,
        radar_chart_base64,
        bar_chart_base64,
        gauge_charts_base64
    )
    
    return html_content, filename

def create_rrg_plot_base64(data):
    """Create RRG plot and convert to base64"""
    # Create RRG plot
    plt.figure(figsize=(10, 7), facecolor='#f5f5f5')
    ax = plt.gca()
    ax.set_facecolor('#f5f5f5')
    
    # Extract unique stocks and data
    latest_data = data.drop_duplicates('Symbol', keep='last')
    
    # Determine limits
    x_min, x_max = 80, 120
    y_min, y_max = 80, 120
    
    # Add quadrant backgrounds
    ax.add_patch(plt.Rectangle((100, 100), x_max-100, y_max-100, alpha=0.1, color='green', zorder=0))  # Leading
    ax.add_patch(plt.Rectangle((100, y_min), x_max-100, 100-y_min, alpha=0.1, color='yellow', zorder=0))  # Weakening
    ax.add_patch(plt.Rectangle((x_min, y_min), 100-x_min, 100-y_min, alpha=0.1, color='red', zorder=0))  # Lagging
    ax.add_patch(plt.Rectangle((x_min, 100), 100-x_min, y_max-100, alpha=0.1, color='blue', zorder=0))  # Improving
    
    # Plot points
    for i, (_, row) in enumerate(latest_data.iterrows()):
        color = plt.cm.tab10(i % 10)
        plt.scatter(row['RS-Ratio'], row['RS-Momentum'], s=150, alpha=0.8, color=color, edgecolors='black', linewidth=1)
        plt.annotate(
            row['Symbol'],
            (row['RS-Ratio'], row['RS-Momentum']),
            xytext=(7, 7),
            textcoords='offset points',
            fontsize=12,
            fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='white', edgecolor='gray', alpha=0.8)
        )
    
    # Add center lines
    plt.axhline(y=100, color='black', linestyle='-', alpha=0.5)
    plt.axvline(x=100, color='black', linestyle='-', alpha=0.5)
    
    # Add quadrant labels
    props = dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='gray')
    plt.text(115, 115, "Leading", fontsize=12, fontweight='bold', ha='center', va='center', bbox=props)
    plt.text(115, 85, "Weakening", fontsize=12, fontweight='bold', ha='center', va='center', bbox=props)
    plt.text(85, 115, "Improving", fontsize=12, fontweight='bold', ha='center', va='center', bbox=props)
    plt.text(85, 85, "Lagging", fontsize=12, fontweight='bold', ha='center', va='center', bbox=props)
    
    # Set limits and labels
    plt.xlim(x_min, x_max)
    plt.ylim(y_min, y_max)
    plt.xlabel('RS-Ratio', fontsize=14, fontweight='bold')
    plt.ylabel('RS-Momentum', fontsize=14, fontweight='bold')
    plt.title('Relative Rotation Graph (RRG)', fontsize=16, fontweight='bold')
    plt.grid(True, alpha=0.3)
    
    # Convert to base64
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', bbox_inches='tight', dpi=300)
    plt.close()
    img_buf.seek(0)
    img_base64 = base64.b64encode(img_buf.read()).decode('utf-8')
    
    return img_base64

def create_radar_chart_base64(data):
    """Create radar chart for comparison and convert to base64"""
    # Skip if less than 2 stocks
    if len(data['Symbol'].unique()) < 2:
        return ""
    
    # Prepare metrics for radar chart
    metrics = ['Universe_Score', 'Fundamental_Score', 'RS-Ratio', 'RS-Momentum']
    fundamental_metrics = ['returnOnEquity', 'returnOnAssets', 'profitMargins', 'earningsGrowth']
    
    for metric in fundamental_metrics:
        if metric in data.columns and not data[metric].isna().all():
            metrics.append(metric)
    
    # Ensure all metrics exist
    metrics = [m for m in metrics if m in data.columns]
    
    if len(metrics) < 3:
        return ""  # Not enough metrics
    
    # Prepare data
    latest_data = data.drop_duplicates('Symbol', keep='last')
    
    # Create radar chart
    n = len(metrics)
    angles = np.linspace(0, 2*np.pi, n, endpoint=False).tolist()
    angles += angles[:1]  # Close the loop
    
    fig, ax = plt.subplots(figsize=(10, 8), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor('#f5f5f5')
    ax.set_facecolor('#f5f5f5')
    
    # Normalize data to 0-1 scale for radar
    norm_data = latest_data.copy()
    for metric in metrics:
        max_val = norm_data[metric].max()
        min_val = norm_data[metric].min()
        if max_val > min_val:
            norm_data[metric] = (norm_data[metric] - min_val) / (max_val - min_val)
        else:
            norm_data[metric] = 0.5
    
    # Plot each stock
    for i, (_, row) in enumerate(norm_data.iterrows()):
        values = [row[m] for m in metrics]
        values += values[:1]  # Close the loop
        
        color = plt.cm.tab10(i % 10)
        ax.plot(angles, values, linewidth=2, linestyle='solid', label=row['Symbol'], color=color)
        ax.fill(angles, values, color=color, alpha=0.1)
    
    # Set labels and styling
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([m.replace('_', ' ') for m in metrics], fontsize=10)
    
    # Add legend
    plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
    
    plt.title('Radar Chart: Perbandingan Metrik', fontsize=16, fontweight='bold')
    
    # Convert to base64
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', bbox_inches='tight', dpi=300)
    plt.close()
    img_buf.seek(0)
    img_base64 = base64.b64encode(img_buf.read()).decode('utf-8')
    
    return img_base64

def create_bar_chart_base64(data):
    """Create bar chart for key metrics and convert to base64"""
    # Determine metrics to compare
    key_metrics = ['Universe_Score', 'Fundamental_Score', 'Combined_Score']
    
    # Ensure all metrics exist
    key_metrics = [m for m in key_metrics if m in data.columns]
    
    if not key_metrics:
        return ""  # No key metrics available
    
    # Get unique stocks
    latest_data = data.drop_duplicates('Symbol', keep='last')
    symbols = latest_data['Symbol'].tolist()
    
    # Create bar chart
    n_metrics = len(key_metrics)
    fig, axes = plt.subplots(n_metrics, 1, figsize=(10, n_metrics * 2.5), constrained_layout=True)
    fig.patch.set_facecolor('#f5f5f5')
    
    if n_metrics == 1:
        axes = [axes]
    
    for i, metric in enumerate(key_metrics):
        ax = axes[i]
        ax.set_facecolor('#f5f5f5')
        
        # Get values
        values = [latest_data[latest_data['Symbol'] == sym][metric].iloc[0] for sym in symbols]
        
        # Create bars with colorful style
        bars = ax.bar(symbols, values, color=plt.cm.tab10(range(len(symbols))))
        
        # Add value labels
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width()/2, 
                bar.get_height() + 2, 
                f"{val:.1f}", 
                ha='center', va='bottom',
                fontweight='bold'
            )
        
        # Styling
        ax.set_title(f"{metric.replace('_', ' ')}", fontsize=14, fontweight='bold')
        ax.set_ylim(0, max(values) * 1.2)
        ax.grid(axis='y', alpha=0.3)
        
        # Add target lines for score metrics
        if metric in ['Universe_Score', 'Fundamental_Score', 'Combined_Score']:
            ax.axhline(y=80, color='green', linestyle='--', alpha=0.5)
            ax.axhline(y=50, color='orange', linestyle='--', alpha=0.5)
            ax.axhline(y=30, color='red', linestyle='--', alpha=0.5)
    
    # Convert to base64
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', bbox_inches='tight', dpi=300)
    plt.close()
    img_buf.seek(0)
    img_base64 = base64.b64encode(img_buf.read()).decode('utf-8')
    
    return img_base64

def create_gauge_charts_base64(data, use_fundamental, use_universe_score):
    """Create gauge charts for single stock metrics and convert to base64"""
    
    # Extract key metrics
    single_row = data.iloc[0]
    metrics = []
    
    # Add core metrics
    if 'RS-Ratio' in single_row:
        metrics.append(('RS-Ratio', single_row['RS-Ratio'], 120))
    if 'RS-Momentum' in single_row:
        metrics.append(('RS-Momentum', single_row['RS-Momentum'], 120))
    if use_fundamental and 'Fundamental_Score' in single_row:
        metrics.append(('Fundamental Score', single_row['Fundamental_Score'], 100))
    if use_universe_score and 'Universe_Score' in single_row:
        metrics.append(('Universe Score', single_row['Universe_Score'], 100))
    if 'Combined_Score' in single_row:
        metrics.append(('Combined Score', single_row['Combined_Score'], 100))
    
    # If no metrics, return empty
    if not metrics:
        return ""
    
    # Determine layout
    n_metrics = len(metrics)
    cols = min(3, n_metrics)
    rows = (n_metrics + cols - 1) // cols
    
    fig, axes = plt.subplots(rows, cols, figsize=(4*cols, 3*rows))
    fig.patch.set_facecolor('#f5f5f5')
    
    # Make sure axes is always a 2D array
    if n_metrics == 1:
        axes = np.array([[axes]])
    elif rows == 1:
        axes = axes.reshape(1, -1)
    
    # Create gauges
    for i, (metric_name, value, max_val) in enumerate(metrics):
        row, col = i // cols, i % cols
        ax = axes[row, col]
        ax.set_facecolor('#f5f5f5')
        
        # Calculate angle and color based on value
        angle = np.pi * value / max_val
        if value / max_val > 0.7:
            color = 'green'
        elif value / max_val > 0.4:
            color = 'orange'
        else:
            color = 'red'
        
        # Draw gauge
        ax.add_patch(plt.Circle((0.5, 0), 0.4, fill=False, color='gray'))
        ax.add_patch(Wedge((0.5, 0), 0.4, 0, angle*180/np.pi, color=color, alpha=0.8))
        
        # Add value text
        ax.text(0.5, 0, f"{value:.1f}", ha='center', va='center', fontsize=15, fontweight='bold')
        
        # Add title
        ax.text(0.5, -0.5, metric_name, ha='center', va='center', fontsize=12)
        
        # Set invisible axis
        ax.set_xlim(0, 1)
        ax.set_ylim(-0.6, 0.4)
        ax.axis('off')
    
    # Hide unused axes
    for i in range(n_metrics, rows*cols):
        row, col = i // cols, i % cols
        axes[row, col].axis('off')
    
    plt.tight_layout()
    
    # Convert to base64
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', bbox_inches='tight', dpi=300)
    plt.close()
    img_buf.seek(0)
    img_base64 = base64.b64encode(img_buf.read()).decode('utf-8')
    
    return img_base64

def generate_html_content(
    data, 
    analysis_type, 
    use_fundamental, 
    use_universe_score,
    is_comparison,
    rrg_plot_base64,
    radar_chart_base64,
    bar_chart_base64,
    gauge_charts_base64
):
    """Generate complete HTML report"""
    
    # Determine title
    if is_comparison:
        symbols = ', '.join(data['Symbol'].unique())
        title = f"Laporan Perbandingan: {symbols}"
    else:
        symbol = data['Symbol'].iloc[0]
        title = f"Laporan Analisis Saham: {symbol}"
    
    # Create HTML structure
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>
            /* CSS Styling */
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 20px;
                background-color: #f8f9fa;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                box-shadow: 0 0 15px rgba(0,0,0,0.1);
                border-radius: 8px;
            }}
            h1, h2, h3, h4 {{
                color: #2c3e50;
                margin-top: 25px;
            }}
            h1 {{
                text-align: center;
                padding-bottom: 15px;
                border-bottom: 2px solid #3498db;
                margin-bottom: 30px;
            }}
            .header-info {{
                text-align: center;
                margin-bottom: 30px;
                color: #555;
            }}
            .row {{
                display: flex;
                flex-wrap: wrap;
                margin: 0 -15px;
            }}
            .col {{
                flex: 1;
                padding: 0 15px;
                min-width: 300px;
            }}
            .chart-container {{
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                margin-bottom: 30px;
                padding: 20px;
                text-align: center;
            }}
            .chart-title {{
                margin-top: 0;
                color: #3498db;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
            }}
            img {{
                max-width: 100%;
                height: auto;
                border-radius: 4px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            th, td {{
                padding: 12px 15px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background-color: #3498db;
                color: white;
                font-weight: 500;
            }}
            tr:nth-child(even) {{
                background-color: #f2f2f2;
            }}
            .stock-card {{
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 20px;
                padding: 20px;
                border-left: 5px solid #3498db;
            }}
            .stock-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }}
            .stock-header h3 {{
                margin: 0;
                color: #2c3e50;
            }}
            .recommendation {{
                padding: 5px 10px;
                border-radius: 4px;
                font-weight: bold;
                color: white;
            }}
            .strong-buy {{ background-color: #27ae60; }}
            .buy {{ background-color: #2ecc71; }}
            .hold {{ background-color: #f39c12; }}
            .reduce {{ background-color: #e67e22; }}
            .sell {{ background-color: #e74c3c; }}
            .metrics {{
                display: flex;
                flex-wrap: wrap;
                gap: 15px;
                margin-bottom: 15px;
            }}
            .metric {{
                flex: 1;
                min-width: 120px;
                background-color: #f8f9fa;
                padding: 10px;
                border-radius: 4px;
                text-align: center;
            }}
            .metric-value {{
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
            }}
            .metric-name {{
                font-size: 12px;
                color: #7f8c8d;
                margin-top: 5px;
            }}
            .footer {{
                text-align: center;
                margin-top: 50px;
                padding-top: 20px;
                border-top: 1px solid #eee;
                color: #7f8c8d;
                font-size: 0.9em;
            }}
            @media print {{
                body {{ 
                    background-color: white !important;
                    padding: 0 !important;
                }}
                .container {{
                    box-shadow: none !important;
                    padding: 0 !important;
                }}
                .page-break {{ page-break-before: always; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{title}</h1>
            <div class="header-info">
                <p>Tanggal Analisis: {datetime.now().strftime('%d %B %Y')}</p>
                <p>Jenis Analisis: {analysis_type}</p>
                {f"<p>Termasuk Stock Universe Score</p>" if use_universe_score else ""}
            </div>
    """
    
    # Add RRG visualization
    if rrg_plot_base64:
        html += f"""
            <div class="chart-container">
                <h2 class="chart-title">Relative Rotation Graph (RRG)</h2>
                <img src="data:image/png;base64,{rrg_plot_base64}" alt="RRG Visualization">
            </div>
        """
    
    # Add comparison visualizations if applicable
    if is_comparison:
        if radar_chart_base64:
            html += f"""
                <div class="chart-container">
                    <h2 class="chart-title">Radar Chart: Perbandingan Metrik</h2>
                    <img src="data:image/png;base64,{radar_chart_base64}" alt="Radar Chart Comparison">
                </div>
            """
        
        if bar_chart_base64:
            html += f"""
                <div class="chart-container">
                    <h2 class="chart-title">Perbandingan Skor Utama</h2>
                    <img src="data:image/png;base64,{bar_chart_base64}" alt="Bar Chart Comparison">
                </div>
            """
        
        # Add comparison table
        html += """
            <h2>Tabel Perbandingan</h2>
            <table>
                <thead>
                    <tr>
        """
        
        # Table headers
        for col in data.columns:
            if col in ['Symbol', 'RS-Ratio', 'RS-Momentum', 'Quadrant', 'Fundamental_Score', 
                      'Universe_Score', 'Combined_Score', 'Combined_Recommendation'] or col in data.columns:
                html += f"<th>{col.replace('_', ' ')}</th>"
        
        html += """
                    </tr>
                </thead>
                <tbody>
        """
        
        # Table rows
        for _, row in data.drop_duplicates('Symbol').iterrows():
            html += "<tr>"
            for col in data.columns:
                if col in ['Symbol', 'RS-Ratio', 'RS-Momentum', 'Quadrant', 'Fundamental_Score', 
                          'Universe_Score', 'Combined_Score', 'Combined_Recommendation'] or col in data.columns:
                    value = row[col]
                    
                    # Format values
                    if col in ['RS-Ratio', 'RS-Momentum']:
                        formatted_val = f"{value:.2f}"
                    elif col in ['Fundamental_Score', 'Universe_Score', 'Combined_Score']:
                        formatted_val = f"{value:.1f}"
                    elif col in ['returnOnEquity', 'returnOnAssets', 'profitMargins', 'earningsGrowth']:
                        formatted_val = f"{value:.2%}"
                    elif col == 'Combined_Recommendation':
                        class_name = value.lower().replace(' ', '-')
                        formatted_val = f'<span class="recommendation {class_name}">{value}</span>'
                    else:
                        formatted_val = str(value)
                    
                    html += f"<td>{formatted_val}</td>"
            html += "</tr>"
        
        html += """
                </tbody>
            </table>
            
            <div class="page-break"></div>
            <h2>Ringkasan Perbandingan</h2>
            <div class="row">
        """
        
        # Add stock cards for comparison
        for _, row in data.drop_duplicates('Symbol').iterrows():
            symbol = row['Symbol']
            recommendation = row.get('Combined_Recommendation', 'N/A')
            rec_class = recommendation.lower().replace(' ', '-') if recommendation != 'N/A' else ''
            
            html += f"""
                <div class="col">
                    <div class="stock-card">
                        <div class="stock-header">
                            <h3>{symbol}</h3>
                            <span class="recommendation {rec_class}">{recommendation}</span>
                        </div>
                        <div class="metrics">
            """
            
            # Add key metrics
            for metric in ['Combined_Score', 'Universe_Score', 'Fundamental_Score', 'RS-Ratio', 'RS-Momentum']:
                if metric in row and pd.notna(row[metric]):
                    metric_name = metric.replace('_', ' ')
                    
                    if metric in ['Combined_Score', 'Universe_Score', 'Fundamental_Score']:
                        formatted_val = f"{row[metric]:.1f}/100"
                    else:
                        formatted_val = f"{row[metric]:.2f}"
                    
                    html += f"""
                            <div class="metric">
                                <div class="metric-value">{formatted_val}</div>
                                <div class="metric-name">{metric_name}</div>
                            </div>
                    """
            
            html += f"""
                        </div>
                        <p><strong>Quadrant:</strong> {row.get('Quadrant', 'N/A')}</p>
                    </div>
                </div>
            """
        
        html += """
            </div>
        """
    else:
        # Single stock analysis
        symbol = data['Symbol'].iloc[0]
        row = data.iloc[0]
        
        # Add gauge charts if available
        if gauge_charts_base64:
            html += f"""
                <div class="chart-container">
                    <h2 class="chart-title">Metrik Utama</h2>
                    <img src="data:image/png;base64,{gauge_charts_base64}" alt="Gauge Charts">
                </div>
            """
        
        # Add detailed stock card
        recommendation = row.get('Combined_Recommendation', 'N/A')
        rec_class = recommendation.lower().replace(' ', '-') if recommendation != 'N/A' else ''
        
        html += f"""
            <h2>Analisis Detail</h2>
            <div class="stock-card">
                <div class="stock-header">
                    <h3>{symbol}</h3>
                    <span class="recommendation {rec_class}">{recommendation}</span>
                </div>
                
                <div class="metrics">
        """
        
        # Add all available metrics
        for metric in ['Combined_Score', 'Universe_Score', 'Fundamental_Score', 'RS-Ratio', 'RS-Momentum']:
            if metric in row and pd.notna(row[metric]):
                metric_name = metric.replace('_', ' ')
                
                if metric in ['Combined_Score', 'Universe_Score', 'Fundamental_Score']:
                    formatted_val = f"{row[metric]:.1f}/100"
                else:
                    formatted_val = f"{row[metric]:.2f}"
                
                html += f"""
                        <div class="metric">
                            <div class="metric-value">{formatted_val}</div>
                            <div class="metric-name">{metric_name}</div>
                        </div>
                """
        
        html += """
                </div>
                
                <h3>Analisis Teknikal (RRG)</h3>
        """
        
        # Add RRG analysis text
        if 'Quadrant' in row:
            quadrant = row['Quadrant']
            rs_ratio = row['RS-Ratio']
            rs_momentum = row['RS-Momentum']
            
            quadrant_explanations = {
                'Leading': f"Saham {symbol} berada pada kuadran <strong>Leading</strong> dengan RS-Ratio {rs_ratio:.2f} dan RS-Momentum {rs_momentum:.2f}. Saham ini menunjukkan <strong>kekuatan relatif dan momentum positif</strong>. Posisi di kuadran Leading mengindikasikan performa yang baik dibandingkan benchmark.",
                'Weakening': f"Saham {symbol} berada pada kuadran <strong>Weakening</strong> dengan RS-Ratio {rs_ratio:.2f} dan RS-Momentum {rs_momentum:.2f}. Saham ini memiliki <strong>kekuatan relatif tinggi namun momentum mulai menurun</strong>. Perhatikan perkembangan momentum di periode mendatang.",
                'Lagging': f"Saham {symbol} berada pada kuadran <strong>Lagging</strong> dengan RS-Ratio {rs_ratio:.2f} dan RS-Momentum {rs_momentum:.2f}. Saham ini menunjukkan <strong>kekuatan relatif rendah dan momentum negatif</strong>. Berhati-hatilah karena posisi di kuadran Lagging mengindikasikan underperformance.",
                'Improving': f"Saham {symbol} berada pada kuadran <strong>Improving</strong> dengan RS-Ratio {rs_ratio:.2f} dan RS-Momentum {rs_momentum:.2f}. Saham ini memiliki <strong>kekuatan relatif rendah namun momentum mulai meningkat</strong>. Perhatikan potensi pemulihan di periode mendatang."
            }
            
            html += f"<p>{quadrant_explanations.get(quadrant, '')}</p>"
        
        # Add fundamental analysis if available
        if use_fundamental and 'Fundamental_Score' in row:
            f_score = row['Fundamental_Score']
            
            html += f"""
                <h3>Analisis Fundamental</h3>
                <p>Skor fundamental {symbol} adalah <strong>{f_score:.1f}</strong> dari 100.</p>
                <table>
                    <tr>
                        <th>Metrik</th>
                        <th>Nilai</th>
                    </tr>
            """
            
            # Add fundamental metrics
            fundamental_metrics = [
                ('returnOnEquity', 'Return on Equity (ROE)'),
                ('returnOnAssets', 'Return on Assets (ROA)'),
                ('profitMargins', 'Profit Margin'),
                ('earningsGrowth', 'Earnings Growth'),
                ('debtToEquity', 'Debt to Equity')
            ]
            
            for col, label in fundamental_metrics:
                if col in row and pd.notna(row[col]):
                    if col in ['returnOnEquity', 'returnOnAssets', 'profitMargins', 'earningsGrowth']:
                        formatted_val = f"{row[col]:.2%}"
                    else:
                        formatted_val = f"{row[col]:.2f}"
                    
                    html += f"""
                        <tr>
                            <td>{label}</td>
                            <td>{formatted_val}</td>
                        </tr>
                    """
            
            html += """
                </table>
            """
        
        # Add universe score analysis if available
        if use_universe_score and 'Universe_Score' in row:
            u_score = row['Universe_Score']
            
            html += f"""
                <h3>Stock Universe Score</h3>
                <p>Skor Universe {symbol} adalah <strong>{u_score:.1f}</strong> dari 100.</p>
                <p>Stock Universe Score merepresentasikan kesehatan emiten berdasarkan laba 3 tahun terakhir, total return (dividen + capital gain), dan notasi khusus di bursa.</p>
            """
        
        # Add conclusion
        if 'Combined_Score' in row:
            html += f"""
                <div class="page-break"></div>
                <h3>Kesimpulan</h3>
                <p>Berdasarkan analisis gabungan, saham {symbol} mendapatkan rekomendasi <strong>{recommendation}</strong> dengan skor gabungan {row['Combined_Score']:.1f} dari 100.</p>
            """
            
            # Add weighting explanation
            if use_universe_score and use_fundamental:
                html += """
                <p><strong>Skor gabungan</strong> dihitung dengan bobot:</p>
                <ul>
                    <li>40% Stock Universe Score</li>
                    <li>30% Skor Fundamental</li>
                    <li>30% Skor RS-Momentum (Technical)</li>
                </ul>
                """
        
        html += """
            </div>
        """
    
    # Add disclaimer and footer
    html += """
            <div class="page-break"></div>
            <h2>Disclaimer</h2>
            <p><em>Laporan ini dibuat secara otomatis berdasarkan data yang tersedia. Hasil analisis dan rekomendasi 
            hanya sebagai referensi dan bukan merupakan saran investasi. Investor disarankan untuk melakukan 
            riset mandiri dan berkonsultasi dengan penasihat keuangan sebelum mengambil keputusan investasi. 
            Performa masa lalu tidak menjamin hasil di masa depan.</em></p>
            
            <div class="footer">
                <p>Dibuat dengan Comprehensive Stock Analyzer | &copy; 2025</p>
                <p>Generated on: """ + datetime.now().strftime('%d %B %Y, %H:%M:%S') + """</p>
            </div>
        </div>
        
        <script>
            // Add print button
            document.addEventListener('DOMContentLoaded', function() {
                const container = document.querySelector('.container');
                const printBtn = document.createElement('button');
                printBtn.innerHTML = '🖨️ Save as PDF';
                printBtn.style.display = 'block';
                printBtn.style.margin = '20px auto';
                printBtn.style.padding = '10px 20px';
                printBtn.style.backgroundColor = '#3498db';
                printBtn.style.color = 'white';
                printBtn.style.border = 'none';
                printBtn.style.borderRadius = '4px';
                printBtn.style.cursor = 'pointer';
                printBtn.style.fontSize = '16px';
                
                printBtn.addEventListener('click', function() {
                    window.print();
                });
                
                container.insertBefore(printBtn, container.firstChild);
            });
        </script>
    </body>
    </html>
    """
    
    return html
