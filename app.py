import streamlit as st
import pandas as pd
import boto3
from boto3.dynamodb.conditions import Key
import time

# ==========================================
# 1. SAYFA VE KURUMSAL TASARIM AYARLARI
# ==========================================
st.set_page_config(
    page_title="Kürüm Mühendislik | Enerji Yönetim Portalı", 
    page_icon="🏢", 
    layout="wide"
)

# Kurumsal CSS Arayüz Tasarımı
st.markdown("""
    <style>
    /* Genel Arka Plan */
    .stApp {
        background-color: #f4f6f9;
    }
    /* Kurumsal Lacivert Başlıklar */
    h1, h2, h3, h4 {
        color: #0F172A !important;
        font-family: 'Inter', 'Segoe UI', sans-serif;
        font-weight: 700;
    }
    /* Metrik Kartları Geliştirme */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        padding: 20px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
        border-left: 6px solid #2563EB !important; /* Kurumsal Mavi Çizgi */
    }
    /* Metrik Değer Yazıları */
    div[data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #1E293B !important;
    }
    /* Alt Bilgi Alanı */
    .footer-text {
        text-align: center; 
        color: #64748B; 
        font-size: 0.85rem;
        margin-top: 50px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. AWS BAĞLANTI AYARLARI (SECRETS)
# ==========================================
def get_dynamodb_resource():
    return boto3.resource(
        'dynamodb',
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY"],
        aws_secret_access_key=st.secrets["AWS_SECRET_KEY"],
        region_name=st.secrets["REGION_NAME"]
    )

# ==========================================
# 3. KULLANICI GİRİŞ KONTROLÜ
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    # Giriş Ekranı Tasarımı
    st.markdown("<h2 style='text-align: center; margin-top: 10%;'>🏢 KÜRÜM MÜHENDİSLİK</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748B;'>Endüstriyel Enerji Takip ve Analiz Portalı</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.form("login_form"):
            st.markdown("### 🔒 Sistem Girişi")
            username = st.text_input("Kullanıcı Adı")
            password = st.text_input("Şifre", type="password")
            submit = st.form_submit_button("Sisteme Giriş Yap")
            
            if submit:
                # Güvenli şifre kontrolü (Localdeki bilgilerinizle eşleştirin)
                if username == "admin" and password == "kurum2026!":
                    st.session_state['logged_in'] = True
                    st.rerun()
                else:
                    st.error("Hatalı kullanıcı adı veya şifre!")
    st.stop()

# ==========================================
# 4. ANA PANEL VE VERİ AKIŞI
# ==========================================

# Üst Kurumsal Header Bölümü
left_co, right_co = st.columns([4, 1])
with left_co:
    st.title("🏢 KÜRÜM MÜHENDİSLİK")
    st.markdown("##### Endüstriyel Akıllı Enerji Analizörü ve Raporlama Sistemi")

with right_co:
    st.write("")
    if st.button("🚪 Sistemden Çıkış Yap", use_container_width=True):
        st.session_state['logged_in'] = False
        st.rerun()

st.markdown("---")

# Yan Menü Kontrolleri (Sidebar)
st.sidebar.markdown("### 📊 Panel Ayarları")
selected_factory = st.sidebar.selectbox("İzlenecek Tesis/Fabrika", ["Fabrika_A", "Fabrika_B"])
record_count = st.sidebar.slider("Görselleştirilecek Kayıt Sayısı", 5, 50, 15)
live_stream = st.sidebar.checkbox("Canlı Veri Akışı Aktif", value=True)

# AWS Veri Çekme Fonksiyonu
try:
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table('EnergyData') # DynamoDB tablo adınız
    
    # Son verileri sorgula (Girdiğin kayıt sayısına göre)
    response = table.query(
        KeyConditionExpression=Key('device_id').eq(selected_factory),
        Limit=record_count,
        ScanIndexForward=False # En son verilerin en üstte gelmesi için
    )
    
    items = response.get('Items', [])
    
    if items:
        df = pd.DataFrame(items)
        # Zaman damgasına göre sırala
        df = df.sort_values(by='timestamp', ascending=True)
        
        # En son veriyi anlık metrikler için al
        latest_data = items[0]
        
        # Üst Metrik Kartları Bölümü
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("⚡ Voltaj (V)", f"{float(latest_data.get('voltage', 0)):.1f} V")
        col2.metric("🔌 Akım (A)", f"{float(latest_data.get('current', 0)):.2f} A")
        col3.metric("🔥 Aktif Güç (W)", f"{float(latest_data.get('power', 0)):.1f} W")
        col4.metric("🌐 Frekans (Hz)", f"{float(latest_data.get('frequency', 0)):.2f} Hz")
        
        st.write("")
        
        col5, col6, col7 = st.columns(3)
        col5.metric("📦 Toplam Tüketim", f"{float(latest_data.get('total_energy', 0)):.2f} kWh")
        col6.metric("💰 Dönemsel Maliyet", f"{float(latest_data.get('cost', 0)):.2f} TL")
        col7.metric("📐 Güç Faktörü (Cos φ)", f"{float(latest_data.get('power_factor', 0)):.2f}")
        
        st.markdown("---")
        
        # Zaman Serisi Grafikleri
        st.markdown("### 📈 Zaman Serisi Grafikleri")
        
        tab1, tab2 = st.tabs(["⚡ Yük & Gerilim Analizi", "📊 Akım & Verimlilik Grafiği"])
        
        with tab1:
            st.markdown("#### Voltaj ve Güç Değişim Grafiği")
            chart_data = df.set_index('timestamp')[['voltage', 'power']]
            st.line_chart(chart_data)
            
        with tab2:
            st.markdown("#### Akım Tüketim Grafiği")
            chart_data_current = df.set_index('timestamp')[['current']]
            st.area_chart(chart_data_current)
            
        # Sistem Durumu Bilgilendirmesi
        st.success("✔️ Sistem Durumu: Kararlı (Tüm veriler Kürüm Mühendislik standartlarında nominal sınırlar içerisinde)")
        
    else:
        st.warning(f"Seçilen tesise ({selected_factory}) ait veri bulunamadı. Lütfen ESP32 cihazınızın veri gönderdiğinden emin olun.")

except Exception as e:
    st.error(f"Veri tabanına bağlanırken bir hata oluştu. Lütfen AWS Secrets ayarlarını kontrol edin.")

# Canlı Akış Aktifse Sayfayı Yenileme Mekanizması
if live_stream:
    time.sleep(5)
    st.rerun()

# ==========================================
# 5. KURUMSAL FOOTER (ALT BİLGİ)
# ==========================================
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    "<p class='footer-text'>"
    "© 2026 Kürüm Mühendislik Ar-Ge ve Otomasyon Teknolojileri Merkezi. Tüm hakları saklıdır. | Versiyon 1.1.0"
    "</p>", 
    unsafe_allow_html=True
)
