import streamlit as st
import pandas as pd
import plotly.express as px

# ==========================================
# 1. SETUP HALAMAN
# ==========================================
st.set_page_config(page_title="Dashboard EDA Risiko Kredit", layout="wide")

# ==========================================
# 2. LOAD DATA
# ==========================================
@st.cache_data
def load_data():
    df = pd.read_csv(r"D:\Koding Liburan\Full Dataset\prosperloandata_28_fitur_large.csv", low_memory=False)
    
    # Sederhanakan status pinjaman murni untuk eksplorasi
    df['Kategori_Kredit'] = df['LoanStatus'].apply(
        lambda x: 'Lancar' if x in ['Completed', 'Current', 'FinalPaymentInProgress'] else 'Bermasalah'
    )
    
    if 'ProsperRating (Alpha)' not in df.columns:
        rating_map = {1: 'HR', 2: 'E', 3: 'D', 4: 'C', 5: 'B', 6: 'A', 7: 'AA'}
        df['ProsperRating (Alpha)'] = df['ProsperRating (numeric)'].round().fillna(4).map(rating_map).fillna('C')
    else:
        df['ProsperRating (Alpha)'] = df['ProsperRating (Alpha)'].fillna('C')
        
    return df

st.title("📊 Exploratory Data Analysis: Profil Risiko Nasabah")
st.markdown("Dashboard ini bertujuan untuk membedah karakteristik nasabah dan menemukan justifikasi analitik sebelum masuk ke tahap pemodelan Machine Learning.")

df = load_data()

# ==========================================
# 3. SIDEBAR MENU
# ==========================================
menu = st.sidebar.radio(
    "Tahapan Eksplorasi:",
    [
        "Tinjauan Data (Overview)", 
        "Identifikasi Imbalanced Data", 
        "Profil Risiko Nasabah"
    ]
)

# ==========================================
# 4. KONTEN BERDASARKAN MENU
# ==========================================

if menu == "Tinjauan Data (Overview)":
    st.header("Tinjauan Dataset Mentah")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Riwayat Pinjaman", f"{len(df):,}")
    col2.metric("Total Fitur Tersedia", len(df.columns))
    col3.metric("Rata-rata Plafon", f"${df['LoanOriginalAmount'].mean():,.2f}")
    
    st.dataframe(df.head(10))
    st.subheader("Statistik Deskriptif Utama")
    st.dataframe(df.describe())
    
    st.success("💡 **Insight Eksplorasi Awal:**\nDataset ini berisi puluhan ribu data historis nasabah. Rentang data finansial (seperti gaji bulanan dan saldo kredit) sangat bervariasi. Perlu dilakukan analisis lebih dalam untuk melihat variabel mana yang berpotensi menyebabkan gagal bayar.")

elif menu == "Identifikasi Imbalanced Data":
    st.header("Identifikasi Imbalanced Data")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # GRAFIK 1: PIE CHART IMBALANCED DATA
        status_counts = df['Kategori_Kredit'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Jumlah']
        fig_pie = px.pie(status_counts, values='Jumlah', names='Status', 
                         title='Distribusi Target: Ketimpangan Nasabah Lancar vs Bermasalah',
                         color='Status', color_discrete_map={'Lancar':'#2ecc71', 'Bermasalah':'#e74c3c'},
                         hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)
        
        # KETERANGAN KATEGORI TARGET (TAMBAHAN BARU)
        st.markdown("""
        **📌 Keterangan Pemetaan Kategori:**
        * ✅ **Lancar:** Terdiri dari nasabah dengan status riil `Completed`, `Current`, dan `FinalPaymentInProgress`.
        * ❌ **Bermasalah:** Terdiri dari nasabah dengan status riil `Default`, `Chargedoff`, `Past Due`, `Late`, dll.
        """)
        
    with col2:
        # INSIGHT PENGANTAR KE SMOTE
        st.error("⚠️ **Temuan Kritis: Imbalanced Data**\n\nGrafik di samping menunjukkan bahwa porsi nasabah **Bermasalah** sangat kecil dibandingkan nasabah **Lancar**. \n\n**Dampak:** Jika data mentah ini langsung dimasukkan ke model prediksi, algoritma akan menjadi bias dan cenderung selalu menebak nasabah aman.")

elif menu == "Profil Risiko Nasabah":
    st.header("Profil Risiko Nasabah")
    tab1, tab2 = st.tabs(["Eksplorasi Rating Platform", "Eksplorasi Rasio Utang (DTI)"])
    
    with tab1:
        # GRAFIK 2: BAR CHART (RATING)
        df_rating = df.dropna(subset=['ProsperRating (Alpha)', 'Kategori_Kredit'])
        rating_order = ['HR', 'E', 'D', 'C', 'B', 'A', 'AA']
        rating_df = df_rating.groupby(['ProsperRating (Alpha)', 'Kategori_Kredit']).size().reset_index(name='Jumlah')
        
        fig_rating = px.bar(rating_df, x='ProsperRating (Alpha)', y='Jumlah', color='Kategori_Kredit',
                            barmode='group', category_orders={'ProsperRating (Alpha)': rating_order},
                            color_discrete_map={'Lancar':'#2ecc71', 'Bermasalah':'#e74c3c'}, 
                            title="Tingkat Gagal Bayar Berdasarkan Kategori Risiko (Rating)")
        st.plotly_chart(fig_rating, use_container_width=True)
        
        # KETERANGAN RATING (TAMBAHAN BARU)
        st.markdown("""
        **📌 Keterangan Tingkat Risiko (Prosper Rating):**
        * **HR (High Risk):** Risiko gagal bayar paling tinggi.
        * **E, D, C, B, A:** Tingkat risiko yang semakin menurun secara bertahap.
        * **AA:** Risiko gagal bayar paling rendah (Kualitas nasabah terbaik).
        """)
        
        st.success("💡 **Bivariate Insight - Kualitas Rating:**\nKorelasi yang sangat jelas terlihat di sini. Nasabah dengan rating terburuk (HR dan E) mendominasi angka kredit bermasalah. Fitur rating ini tervalidasi sebagai indikator yang sangat kuat untuk dimasukkan ke dalam fitur Machine Learning.")
        
    with tab2:
        # GRAFIK 3: BOX PLOT (DTI)
        dti_filtered = df[(df['DebtToIncomeRatio'] < 1.0) & (df['DebtToIncomeRatio'].notna())]
        fig_dti = px.box(dti_filtered, x='Kategori_Kredit', y='DebtToIncomeRatio', color='Kategori_Kredit',
                         color_discrete_map={'Lancar':'#2ecc71', 'Bermasalah':'#e74c3c'}, 
                         title="Komparasi Beban Utang (Debt-to-Income) Nasabah")
        st.plotly_chart(fig_dti, use_container_width=True)
        
        st.warning("💡 **Bivariate Insight - Beban Finansial:**\nMelalui observasi distribusi Box Plot, kelompok 'Bermasalah' secara konsisten memiliki median rasio beban utang terhadap gaji (DTI) yang lebih tinggi. Ini membuktikan bahwa persentase cicilan utang bulanan yang besar adalah ciri-ciri kuat dari profil berisiko.")