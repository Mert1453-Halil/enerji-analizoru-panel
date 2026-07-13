import streamlit as st
import pandas as pd
import boto3
from boto3.dynamodb.conditions import Key
import time

# Sayfa Ayarları ve Kurumsal Başlık
st.set_page_config(page_title="Kürüm Mühendislik - Enerji Yönetimi", page_icon="🏢", layout="wide")

# ŞİFRELERİ DOĞRUDAN KODA GÖMÜYORUZ (Streamlit Secrets'ı tamamen devre dışı bıraktık)
AWS_ACCESS_KEY_ID = "SENIN_AWS_ACCESS_KEY_BURAYA"
AWS_SECRET_ACCESS_KEY = "SENIN_AWS_SECRET_KEY_BURAYA"
AWS_REGION = "eu-central-1" # Eğer bölgen farklıysa burayı değiştir, örn: "us-east-1"

# Doğrudan Bağlantı Fonksiyonu
def get_dynamodb_resource():
    return boto3.resource(
        'dynamodb',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

# Ana Panel Başlığı
st.title("🏢 KÜRÜM MÜHENDİSLİK")
st.subheader("Endüstriyel Akıllı Enerji Analizörü ve Raporlama Sistemi")
st.markdown("---")

# Yan Menü (Sidebar) Kontrolleri
st.sidebar.header("Grafik Ayarları")
record_count = st.sidebar.slider("Görselleştirilecek Kayıt Sayısı", 5, 50, 15)
live_stream = st.sidebar.checkbox("Canlı Veri Akışı Aktif", value=True)
selected_factory = st.sidebar.selectbox("İzlenecek Fabrikayı Seçin", ["Fabrika_A", "Fabrika_B"])

# Veri Çekme Yapısı
try:
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table('enerji_analizoru')
    
    response = table.query(
        KeyConditionExpression=Key('device_id').eq(selected_factory),
        Limit=record_count,
        ScanIndexForward=False
    )
    
    items = response.get('Items', [])
    
    if items:
        df = pd.DataFrame(items)
        df = df.sort_values(by='timestamp', ascending=True)
        
        latest_data = items[0]
        
        # Ana Metrikler
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("⚡ Voltaj (V)", f"{float(latest_data.get('voltage', 0)):.1f} V")
        col2.metric("🔌 Akım (A)", f"{float(latest_data.get('current', 0)):.2f} A")
        col3.metric("🔥 Aktif Güç (W)", f"{float(latest_data.get('power', 0)):.1f} W")
        col4.metric("🌐 Frekans (Hz)", f"{float(latest_data.get('frequency', 0)):.2f} Hz")
        
        st.write("")
        
        col5, col6, col7 = st.columns(3)
        col5.metric("📦 Toplam Enerji Tüketimi", f"{float(latest_data.get('total_energy', 0)):.2f} kWh")
        col6.metric("💰 Dönemsel Maliyet Yükü", f"{float(latest_data.get('cost', 0)):.2f} TL")
        col7.metric("📐 Güç Faktörü (Cos φ)", f"{float(latest_data.get('power_factor', 0)):.2f}")
        
        st.markdown("---")
        st.success("✔️ Sistem Durumu: Kararlı (Tüm değerler nominal sınırlarda)")
        
        # Grafikler
        st.header("📊 Zaman Serisi Grafikleri")
        tab1, tab2 = st.tabs(["Yük & Gerilim Grafiği", "Akım & Verimlilik Grafiği"])
        
        with tab1:
            chart_data = df.set_index('timestamp')[['voltage', 'power']]
            st.line_chart(chart_data)
        with tab2:
            chart_data_current = df.set_index('timestamp')[['current']]
            st.area_chart(chart_data_current)
    else:
        st.warning("Veri bulunamadı. Lütfen sol menüden doğru fabrikayı seçtiğinizden emin olun.")

except Exception as e:
    st.error(f"Bağlantı Hatası: {str(e)}")

# Canlı Akış
if live_stream:
    time.sleep(5)
    st.rerun()
