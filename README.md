# RRG Analyzer - Relative Rotation Graph

Aplikasi web untuk menganalisis saham menggunakan metode Relative Rotation Graph (RRG).

## Tentang Aplikasi

RRG Analyzer memungkinkan pengguna untuk:
- Menganalisis kinerja relatif saham terhadap benchmark
- Memvisualisasikan posisi saham dalam kuadran RRG
- Mendapatkan rekomendasi tindakan berdasarkan posisi saham

## Cara Menggunakan

1. Masukkan simbol benchmark (contoh: ^JKSE untuk IHSG)
2. Masukkan daftar saham yang ingin dianalisis
3. Sesuaikan parameter seperti periode data, RS-Ratio, dan RS-Momentum
4. Klik "Jalankan Analisis" untuk melihat hasil

## Interpretasi Kuadran RRG

- **Leading (Kanan Atas)**: Saham dengan kekuatan relatif dan momentum positif. Rekomendasi: Hold/Buy
- **Weakening (Kanan Bawah)**: Saham dengan kekuatan relatif tinggi tapi momentum menurun. Rekomendasi: Hold/Take Profit
- **Lagging (Kiri Bawah)**: Saham dengan kekuatan relatif rendah dan momentum negatif. Rekomendasi: Sell/Cut Loss
- **Improving (Kiri Atas)**: Saham dengan kekuatan relatif rendah tapi momentum meningkat. Rekomendasi: Accumulate/Buy Carefully

## Teknologi yang Digunakan

- Python
- Streamlit
- Pandas
- Matplotlib
- yfinance
