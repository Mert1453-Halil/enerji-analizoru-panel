import streamlit as st
import boto3
import pandas as pd
import time

# --- AWS KİMLİK BİLGİLERİN ---
AWS_ACCESS_KEY = st.secrets["AWS_ACCESS_KEY"]
AWS_SECRET_KEY = st.secrets["AWS_SECRET_KEY"]
REGION_NAME = st.secrets["REGION_NAME"]
ELEKTRIK_TARIFESI = 2.50 

dynamodb = boto3.resource(
    'dynamodb',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=REGION_NAME
)
table = dynamodb.Table('Enerji_Verileri')

st.set_page_config(page_title="Enerji Takip Sistemi | Login", layout="wide")

# --- KULLANICI / MÜŞTERİ VERİ TABANI ---
KULLANICILAR = {
    "admin": {"sifre": "admin123", "rol": "admin", "fabrika": "HEPSI"},
    "patron_a": {"sifre": "fabrikaA12", "rol": "patron", "fabrika": "Fabrika_A"},
    "patron_b": {"sifre": "fabrikaB34", "rol": "patron", "fabrika": "Fabrika_B"}
}

# Oturum Durumu Kontrolü
if "giris_yapildi" not in st.session_state:
    st.session_state.giris_yapildi = False
    st.session_state.kullanici = ""
    st.session_state.rol = ""
    st.session_state.fabrika = ""

# --- 1. KISIM: LOGIN (GİRİŞ EKRANI) ---
if not st.session_state.giris_yapildi:
    # Sayfayı ortalamak için boş sütunlar kullanıyoruz
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.write("### 🏢 ENERJİ TAKİP PORTALI")
        st.caption("Endüstriyel Akıllı Enerji Analizörü ve Raporlama Sistemi")
        
        # Giriş Form Kutusu
        with st.form(key="login_form"):
            st.markdown("##### 🔒 Müşteri Girişi")
            kullanici_adi = st.text_input("Kullanıcı Adı / E-posta", placeholder="Örn: patron_a")
            sifre = st.text_input("Şifre", type="password", placeholder="••••••••")
            
            submit_button = st.form_submit_button(label="Sisteme Giriş Yap")
            
            if submit_button:
                if kullanici_adi in KULLANICILAR and KULLANICILAR[kullanici_adi]["sifre"] == sifre:
                    st.session_state.giris_yapildi = True
                    st.session_state.kullanici = kullanici_adi
                    st.session_state.rol = KULLANICILAR[kullanici_adi]["rol"]
                    st.session_state.fabrika = KULLANICILAR[kullanici_adi]["fabrika"]
                    st.success("Giriş Başarılı! Yönlendiriliyorsunuz...")
                    time.sleep(1)
                    st.rerun()
                else:
                    # Linkteki errNum=3 mantığı: Hatalı giriş uyarısı tetikleniyor
                    st.error("❌ errNum=3: Hatalı Kullanıcı Adı veya Şifre! Lütfen bilgilerinizi kontrol edin.")

# --- 2. KISIM: İÇERİK (DASHBOARD EKRANI) ---
else:
    # Yan Menü Kontrolleri ve Güvenli Çıkış
    st.sidebar.markdown(f"### 👤 {st.session_state.kullanici.upper()}")
    st.sidebar.caption(f"Yetki: {st.session_state.rol.upper()}")
    
    if st.sidebar.button("🚪 Sistemden Çıkış Yap"):
        st.session_state.giris_yapildi = False
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Grafik Ayarları")
    veri_sayisi = st.sidebar.slider("Görselleştirilecek Kayıt Sayısı", 5, 50, 15)
    otomatik_yenileme = st.sidebar.checkbox("Canlı Veri Akışı Aktif", value=True)

    # Rol Yönetimi ve Fabrika Filtre Ayarı
    hedef_fabrika = st.session_state.fabrika
    if st.session_state.rol == "admin":
        hedef_fabrika = st.sidebar.selectbox("İzlenecek Fabrikayı Seçin", ["Fabrika_A", "Fabrika_B"])
        st.title(f"🏭 Merkez Yönetici Paneli")
        st.subheader(f"📊 {hedef_fabrika} Anlık Durum Raporu")
    else:
        st.title(f"🏭 {hedef_fabrika} Enerji Takip Portalı")

    placeholder = st.empty()

    while True:
        response = table.scan()
        items = response.get('Items', [])
        
        if items:
            df = pd.DataFrame(items)
            
            # IoT simülatöründen gelen 'fabrika' alanına göre tam filtreleme
            if 'fabrika' in df.columns:
                df = df[df['fabrika'] == hedef_fabrika]

            if not df.empty:
                df['zaman'] = pd.to_datetime(df['zaman'])
                df = df.sort_values(by='zaman')
                
                for col in ['voltaj', 'akim', 'guc', 'frekans', 'cos_phi', 'toplam_kwh']:
                    if col in df.columns:
                        df[col] = df[col].astype(float)

                with placeholder.container():
                    son_veri = df.iloc[-1]
                    
                    # Gösterge Kartları
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric(label="⚡ Voltaj (V)", value=f"{son_veri['voltaj']} V")
                    col2.metric(label="🔌 Akım (A)", value=f"{son_veri['akim']} A")
                    col3.metric(label="🔥 Aktif Güç (W)", value=f"{son_veri['guc']} W")
                    
                    frek_val = son_veri.get('frekans', 50.0)
                    col4.metric(label="🌀 Frekans (Hz)", value=f"{frek_val} Hz")
                    
                    st.markdown("---")
                    col_kwh, col_tl, col_cos = st.columns(3)
                    
                    kwh_val = son_veri.get('toplam_kwh', 0.0)
                    col_kwh.metric(label="📦 Toplam Enerji Tüketimi", value=f"{kwh_val:.2f} kWh")
                    
                    tahmini_fatura = kwh_val * ELEKTRIK_TARIFESI
                    col_tl.metric(label="💰 Dönemsel Maliyet Yükü", value=f"{tahmini_fatura:.2f} TL")
                    
                    cos_val = son_veri.get('cos_phi', 1.0)
                    col_cos.metric(label="📉 Güç Faktörü (Cos φ)", value=f"{cos_val}")

                    # Dinamik Alarm Bildirim Sahası
                    st.markdown("---")
                    if son_veri.get('UYARI_DURUMU', 'NORMAL') != "NORMAL":
                        st.error(f"🚨 SİSTEM ALARMI: {son_veri['UYARI_DURUMU']}")
                    else:
                        st.success("✅ Sistem Durumu: Kararlı (Tüm değerler nominal sınırlarda)")

                    # Trend Grafikleri
                    st.subheader("📊 Zaman Serisi Grafikleri")
                    tab1, tab2 = st.tabs(["Yük & Gerilim Grafiği", "Akım & Verimlilik Grafiği"])
                    
                    with tab1:
                        chart_data1 = df.tail(veri_sayisi).set_index('zaman')[['voltaj', 'guc']]
                        st.line_chart(chart_data1)
                    with tab2:
                        if 'cos_phi' in df.columns:
                            chart_data2 = df.tail(veri_sayisi).set_index('zaman')[['akim', 'cos_phi']]
                            st.line_chart(chart_data2)

                    # Profesyonel Ham Veri Tablosu (Log)
                    st.subheader("📋 Geçmiş Kayıt Günlüğü")
                    gosterilecek_sutunlar = ['zaman', 'voltaj', 'akim', 'guc', 'toplam_kwh', 'UYARI_DURUMU']
                    mevcut_sutunlar = [c for c in gosterilecek_sutunlar if c in df.columns]
                    st.dataframe(df[mevcut_sutunlar].iloc[::-1], width='stretch')
            else:
                st.warning(f"⚠️ {hedef_fabrika} adına kayıtlı canlı veri akışı henüz bulunmuyor.")
        else:
            st.warning("Veri tabanından veri okunamıyor...")
            
        if not otomatik_yenileme:
            break
        time.sleep(3)