import streamlit as st
pip install setuptools

st.title("RRG Analyzer - Diagnostic Mode")
st.write("Jika Anda bisa melihat halaman ini, berarti deployment dasar berhasil!")

try:
    import pandas as pd
    st.success("✅ pandas berhasil diimpor")
except Exception as e:
    st.error(f"❌ Error mengimpor pandas: {e}")

try:
    import numpy as np
    st.success("✅ numpy berhasil diimpor")
except Exception as e:
    st.error(f"❌ Error mengimpor numpy: {e}")

try:
    import matplotlib.pyplot as plt
    st.success("✅ matplotlib berhasil diimpor")
except Exception as e:
    st.error(f"❌ Error mengimpor matplotlib: {e}")

try:
    import yfinance as yf
    st.success("✅ yfinance berhasil diimpor")
except Exception as e:
    st.error(f"❌ Error mengimpor yfinance: {e}")

st.write("Versi Streamlit:", st.__version__)
