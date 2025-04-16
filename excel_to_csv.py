import pandas as pd
import os
import tempfile
import re

def extract_tickers_from_excel(excel_file):
    """
    Mengekstrak daftar ticker dari file Excel Bloomberg.
    
    Args:
        excel_file: Path ke file Excel
    
    Returns:
        List ticker yang ditemukan
    """
    try:
        # Baca beberapa baris awal untuk menemukan header
        df = pd.read_excel(excel_file, header=None, nrows=15)
        
        # Cari baris yang berisi ticker (biasanya di baris ke-2 atau ke-3)
        tickers = []
        for i, row in df.iterrows():
            # Asumsikan ticker dalam format seperti 'BBCA IJ Equity', 'LQ45 Index', dll.
            for cell in row:
                if isinstance(cell, str) and (' IJ Equity' in cell or ' Index' in cell):
                    tickers.append(cell)
                    
        return tickers
    except Exception as e:
        print(f"Error saat mengekstrak ticker: {str(e)}")
        return []

def convert_excel_to_csv(excel_file, output_dir=None):
    """
    Mengkonversi file Excel Bloomberg ke beberapa file CSV.
    
    Args:
        excel_file: Path ke file Excel
        output_dir: Direktori untuk menyimpan file CSV (jika None, menggunakan direktori temp)
    
    Returns:
        Dictionary dengan {ticker: csv_path}
    """
    # Gunakan tempdir jika output_dir tidak disediakan
    use_temp = output_dir is None
    if use_temp:
        output_dir = tempfile.mkdtemp()
    
    # Hasil akan disimpan di sini
    csv_files = {}
    
    try:
        # Baca file Excel
        df = pd.read_excel(excel_file, header=None)
        
        # Cari baris data
        data_start_row = None
        date_col = 0
        
        # Cari baris yang berisi data tanggal
        for i, row in df.iterrows():
            if isinstance(row[0], pd.Timestamp) or (isinstance(row[0], str) and re.match(r'\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}', row[0])):
                data_start_row = i
                break
                
        if data_start_row is None:
            raise ValueError("Tidak dapat menemukan baris data tanggal dalam file Excel")
        
        # Ambil baris header untuk ticker
        ticker_row = df.iloc[data_start_row-1]
        
        # Proses setiap ticker
        for col in range(0, len(ticker_row), 5):
            ticker = ticker_row[col]
            
            # Lewati kolom kosong
            if not isinstance(ticker, str):
                continue
                
            # Pastikan ini adalah ticker valid
            if not (' IJ Equity' in ticker or ' Index' in ticker):
                continue
                
            # Kolom untuk OHLCV
            cols = {
                'Open': col,
                'High': col + 1,
                'Low': col + 2,
                'Close': col + 3,
                'Volume': col + 4
            }
            
            # Ekstrak data untuk ticker ini
            ticker_data = df.iloc[data_start_row:, [date_col] + list(cols.values())]
            ticker_data.columns = ['Date'] + list(cols.keys())
            
            # Konversi kolom Date
            ticker_data['Date'] = pd.to_datetime(ticker_data['Date'])
            
            # Format ulang Date ke MM/DD/YYYY untuk kompatibilitas
            ticker_data['Date'] = ticker_data['Date'].dt.strftime('%m/%d/%Y')
            
            # Tambahkan kolom Ticker
            clean_ticker = ticker.split(' ')[0] if ' ' in ticker else ticker
            ticker_data.insert(0, 'Ticker', clean_ticker)
            
            # Simpan ke CSV
            csv_path = os.path.join(output_dir, f"{clean_ticker}.csv")
            ticker_data.to_csv(csv_path, index=False)
            
            # Simpan path file CSV
            csv_files[ticker] = csv_path
            
        return csv_files, output_dir
            
    except Exception as e:
        print(f"Error saat mengkonversi Excel ke CSV: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}, output_dir

if __name__ == "__main__":
    # Contoh penggunaan
    import sys
    
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
        tickers = extract_tickers_from_excel(excel_file)
        print(f"Ticker ditemukan: {tickers}")
        
        csv_files, output_dir = convert_excel_to_csv(excel_file)
        print(f"File CSV tersimpan di: {output_dir}")
        for ticker, path in csv_files.items():
            print(f"  {ticker}: {path}")
    else:
        print("Gunakan: python excel_to_csv.py path/to/excel_file.xlsx")