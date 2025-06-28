import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os

# --- Konfigurasi File Data ---
DATA_FILE = 'data_produksi_harian.csv'
TARGET_PER_OPERASI_PER_HARI = 40 # kg (Ini untuk perhitungan kategori mitra)

# --- TARGET BARU UNTUK VISUALISASI ---
TARGET_HARIAN_TON = 84 # ton
TARGET_BULANAN_TON = 2500 # ton
KG_TO_TON_FACTOR = 1000 # 1 ton = 1000 kg

# --- Fungsi untuk Memuat atau Membuat Dataframe ---
def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        # Pastikan kolom 'Tanggal' adalah datetime
        df['Tanggal'] = pd.to_datetime(df['Tanggal'])
        return df
    return pd.DataFrame(columns=['Tanggal', 'Nama Mitra', 'Lokasi', 'Jumlah SPK', 'Jumlah Operasi', 'Jumlah Produksi'])

# --- Fungsi untuk Menyimpan Dataframe ---
def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# --- Fungsi untuk Menghitung Target Produksi (untuk Mitra) ---
def hitung_target_produksi(df_data, nama_mitra):
    # Mengambil data terbaru untuk mitra yang bersangkutan
    df_mitra = df_data[df_data['Nama Mitra'] == nama_mitra].copy()

    if df_mitra.empty:
        return 0 # Atau nilai default lain jika tidak ada data

    # Hitung rata-rata operasi dari data mitra
    rata_rata_operasi = df_mitra['Jumlah Operasi'].mean()

    # Hitung jumlah hari unik dari input data untuk mitra ini
    jumlah_hari = df_mitra['Tanggal'].nunique()

    target = TARGET_PER_OPERASI_PER_HARI * rata_rata_operasi * jumlah_hari
    return target

# --- Fungsi untuk Mengategorikan Mitra ---
def kategorikan_mitra(jumlah_produksi, target_produksi):
    if target_produksi == 0: # Hindari pembagian dengan nol jika target belum bisa dihitung
        return "Belum Ada Target"
    if jumlah_produksi >= target_produksi:
        return "Baik"
    elif jumlah_produksi >= (target_produksi * 0.75): # Contoh: Sedang jika mencapai 75% target
        return "Sedang"
    else:
        return "Buruk"

# --- Judul Aplikasi ---
st.title('Aplikasi Input Data Produksi Harian')

# --- Muat Data Awal ---
df = load_data()

# --- Bagian Input Data Satuan (tetap dipertahankan sebagai opsi) ---
st.header('Input Data Produksi Harian (Satuan)')

with st.form("input_form"):
    tanggal = st.date_input('Tanggal', value=datetime.now())
    nama_mitra = st.text_input('Nama Mitra')
    lokasi = st.text_input('Lokasi')
    jumlah_spk = st.number_input('Jumlah SPK', min_value=0, step=1)
    jumlah_operasi = st.number_input('Jumlah Operasi', min_value=0, step=1)
    jumlah_produksi = st.number_input('Jumlah Produksi (kg)', min_value=0.0, step=0.1)

    submitted_single = st.form_submit_button("Tambah Data Satuan")

    if submitted_single:
        if nama_mitra and lokasi:
            new_data = pd.DataFrame([{
                'Tanggal': pd.to_datetime(tanggal),
                'Nama Mitra': nama_mitra,
                'Lokasi': lokasi,
                'Jumlah SPK': jumlah_spk,
                'Jumlah Operasi': jumlah_operasi,
                'Jumlah Produksi': jumlah_produksi
            }])
            df = pd.concat([df, new_data], ignore_index=True)
            save_data(df)
            st.success('Data satuan berhasil ditambahkan!')
        else:
            st.error('Nama Mitra dan Lokasi tidak boleh kosong.')

st.markdown("---")

# --- Bagian Input Data Batch (Baru) ---
st.header('Input Data Produksi Harian (Batch via File)')

st.write("Unggah file CSV atau Excel yang berisi data produksi harian.")
st.markdown("""
    **Format Kolom yang Diharapkan:**
    `Tanggal`, `Nama Mitra`, `Lokasi`, `Jumlah SPK`, `Jumlah Operasi`, `Jumlah Produksi`
    (Pastikan nama kolom sesuai dan format tanggal konsisten, misalnya YYYY-MM-DD).
""")

uploaded_file = st.file_uploader("Pilih File CSV atau Excel", type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_batch = pd.read_csv(uploaded_file)
        else: # Asumsi .xlsx
            df_batch = pd.read_excel(uploaded_file)

        # Validasi kolom
        expected_columns = ['Tanggal', 'Nama Mitra', 'Lokasi', 'Jumlah SPK', 'Jumlah Operasi', 'Jumlah Produksi']
        if not all(col in df_batch.columns for col in expected_columns):
            st.error(f"Kolom dalam file tidak sesuai. Pastikan ada kolom: {', '.join(expected_columns)}")
        else:
            # Pastikan kolom 'Tanggal' adalah datetime
            df_batch['Tanggal'] = pd.to_datetime(df_batch['Tanggal'])

            # Gabungkan data batch dengan data yang sudah ada
            df = pd.concat([df, df_batch], ignore_index=True)
            save_data(df)
            st.success(f'Data dari file "{uploaded_file.name}" berhasil ditambahkan ({len(df_batch)} baris)!')
            st.dataframe(df_batch) # Tampilkan data yang baru diunggah
    except Exception as e:
        st.error(f"Terjadi kesalahan saat membaca file: {e}. Pastikan format file benar dan kolom sesuai.")

st.markdown("---")

# --- Bagian Tampilan Data ---
st.header('Data Produksi Tersimpan')
if not df.empty:
    st.dataframe(df.sort_values(by='Tanggal', ascending=False).reset_index(drop=True))
else:
    st.info('Belum ada data produksi yang tersimpan.')

st.markdown("---")

# --- Visualisasi Data ---
st.header('Visualisasi Produksi Harian & Capaian Target')

if not df.empty:
    # Agregasi data untuk grafik
    df_agg_daily = df.groupby('Tanggal')['Jumlah Produksi'].sum().reset_index()

    # Konversi Jumlah Produksi dari kg ke ton
    df_agg_daily['Jumlah Produksi (Ton)'] = df_agg_daily['Jumlah Produksi'] / KG_TO_TON_FACTOR

    # --- Grafik Total Produksi Harian vs Target Harian ---
    fig_daily_prod = px.line(df_agg_daily, x='Tanggal', y='Jumlah Produksi (Ton)',
                             title='Total Produksi Harian vs Target Harian',
                             labels={'Tanggal': 'Tanggal', 'Jumlah Produksi (Ton)': 'Total Produksi (Ton)'})

    # Tambahkan garis target harian
    fig_daily_prod.add_hline(y=TARGET_HARIAN_TON, line_dash="dot",
                             annotation_text=f"Target Harian: {TARGET_HARIAN_TON} Ton",
                             annotation_position="top right",
                             line_color="red")
    st.plotly_chart(fig_daily_prod)

    # --- Persentase Produksi dari Target Bulanan ---
    st.subheader('Capaian Target Bulanan')
    total_produksi_keseluruhan_kg = df['Jumlah Produksi'].sum()
    total_produksi_keseluruhan_ton = total_produksi_keseluruhan_kg / KG_TO_TON_FACTOR

    persentase_capaian_bulanan = (total_produksi_keseluruhan_ton / TARGET_BULANAN_TON) * 100

    st.metric(label=f"Total Produksi Keseluruhan (hingga saat ini)", value=f"{total_produksi_keseluruhan_ton:,.2f} Ton")
    st.metric(label=f"Target Bulanan", value=f"{TARGET_BULANAN_TON:,.0f} Ton")
    st.metric(label=f"Persentase Capaian Target Bulanan", value=f"{persentase_capaian_bulanan:,.2f}%")

    if persentase_capaian_bulanan >= 100:
        st.success("Target bulanan telah tercapai!")
    elif persentase_capaian_bulanan >= 75:
        st.warning("Menuju target bulanan, terus tingkatkan!")
    else:
        st.info("Perlu lebih banyak usaha untuk mencapai target bulanan.")

    st.markdown("---")

    # Visualisasi Produksi per Mitra (tetap seperti sebelumnya)
    df_agg_mitra = df.groupby('Nama Mitra')['Jumlah Produksi'].sum().reset_index()
    fig_mitra_prod = px.bar(df_agg_mitra, x='Nama Mitra', y='Jumlah Produksi',
                            title='Total Produksi per Mitra',
                            labels={'Nama Mitra': 'Nama Mitra', 'Jumlah Produksi': 'Total Produksi (kg)'})
    st.plotly_chart(fig_mitra_prod)
else:
    st.info('Tidak ada data untuk divisualisasikan.')

st.markdown("---")

# --- Kategori Mitra ---
st.header('Kategori Status Mitra')

if not df.empty:
    # Agregasi data untuk menghitung total produksi per mitra
    df_mitra_status = df.groupby('Nama Mitra').agg(
        Total_Produksi=('Jumlah Produksi', 'sum'),
        Rata_rata_Operasi=('Jumlah Operasi', 'mean'),
        Jumlah_Hari_Data=('Tanggal', 'nunique')
    ).reset_index()

    # Hitung target produksi dan kategori untuk setiap mitra
    df_mitra_status['Target Produksi'] = df_mitra_status.apply(
        lambda row: TARGET_PER_OPERASI_PER_HARI * row['Rata_rata_Operasi'] * row['Jumlah_Hari_Data'],
        axis=1
    )
    df_mitra_status['Status'] = df_mitra_status.apply(
        lambda row: kategorikan_mitra(row['Total_Produksi'], row['Target Produksi']),
        axis=1
    )

    st.dataframe(df_mitra_status[['Nama Mitra', 'Total_Produksi', 'Target Produksi', 'Status']])

    # Visualisasi Status Mitra (Opsional, bisa berupa pie chart atau bar chart per status)
    status_counts = df_mitra_status['Status'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Jumlah Mitra']

    fig_status = px.bar(status_counts, x='Status', y='Jumlah Mitra',
                        color='Status',
                        title='Distribusi Status Mitra',
                        labels={'Status': 'Status Mitra', 'Jumlah Mitra': 'Jumlah Mitra'})
    st.plotly_chart(fig_status)

else:
    st.info('Tidak ada data untuk mengategorikan mitra.')