import streamlit as st
import boto3
import pandas as pd
import time

# --- AWS ŞİFRELERİNİ DOĞRUDAN KODA GÖMÜYORUZ (Secrets Kutusu Artık Devre Dışı) ---
# Lütfen yeni alacağın şifreleri bu tırnakların içine yaz:
AWS_ACCESS_KEY = "AKIASH3ZBYKXRMWZEV7N"
AWS_SECRET_KEY = "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"
REGION_NAME = "us-east-1"  # Frankfurt ise "eu-central-1" yap

ELEKTRIK_TARIFESI = 2.50 

# Güvenli Bağlantı İstasyonu
dynamodb = boto3.resource(
    'dynamodb',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=REGION_NAME
)
table = dynamodb.Table('Enerji_Verileri')

st.set_page_config(page_title="Enerji Takip Sistemi | Login", layout="wide")

# --- KULLANICI / MÜŞTERI VERI TABANI ---
KULLANICILAR = {
    "admin": {"sifre": "admin123", "rol": "admin", "fabrika": "HEPSI"},
    "patron_a": {"sifre": "fabrikaA12", "rol": "patron", "fabrika": "Fabrika_A"},
    "patron_b": {"sifre": "fabrikaB34", "rol": "patron", "fabrika": "Fabrika_B"}
}

if "giris_yapildi" not in st.session_state:
    st.session_state.giris_yapildi = False
    st.session_state.kullanici = ""
    st.session_state.rol = ""
    st.session_state.fabrika = ""

# --- 1. KISIM: LOGIN (GİRİŞ EKRANI) ---
if not st.session_state.giris_yapildi:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.write("### 🏢 ENERJİ TAKİP PORTALI")
        st.caption("Endüstriyel Akıllı Enerji Analizörü ve Raporlama Sistemi")
        
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
                    st.error("❌ Hatalı Kullanıcı Adı veya Şifre!")

# --- 2. KISIM: İÇERİK (DASHBOARD EKRANI) ---
else:
    st.sidebar.markdown(f"### 👤 {st.session_state.kullanici.upper()}")
    st.sidebar.caption(f"Yetki: {st.session_state.rol.upper()}")
    
    if st.sidebar.button("🚪 Sistemden Çıkış Yap"):
        st.session_state.giris_yapildi = False
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Grafik Ayarları")
    veri_sayisi = st.sidebar.slider("Görselleştirilecek Kayıt Sayısı", 5, 50, 15)
    otomatik_yenileme = st.sidebar.checkbox("Canlı Veri Akışı Aktif", value=True)

    hedef_fabrika = st.session_state.fabrika
    if st.session_state.rol == "admin":
        hedef_fabrika = st.sidebar.selectbox("İzlenecek Fabrikayı Seçin", ["Fabrika_A", "Fabrika_B"])
        st.title(f"🏭 Merkez Yönetici Paneli")
        st.subheader(f"📊 {hedef_fabrika} Anlık Durum Raporu")
    else:
        st.title(f"🏭 {hedef_fabrika} Enerji Takip Portalı")

    try:
        response = table.scan()
        items = response.get('Items', [])
        
        if items:
            df = pd.DataFrame(items)
            if 'fabrika' in df.columns:
                df = df[df['fabrika'] == hedef_fabrika]

            if not df.empty:
                df['zaman'] = pd.to_datetime(df['zaman'])
                df = df.sort_values(by='zaman')
                
                for col in ['voltaj', 'akim', 'guc', 'frekans', 'cos_phi', 'toplam_kwh']:
                    if col in df.columns:
                        df[col] = df[col].astype(float)

                son_veri = df.iloc[-1]
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric(label="⚡ Voltaj (V)", value=f"{son_veri['voltaj']:.1f} V")
                col2.metric(label="🔌 Akım (A)", value=f"{son_veri['akim']:.2f} A")
                col3.metric(label="🔥 Aktif Güç (W)", value=f"{son_veri['guc']:.1f} W")
                col4.metric(label="🌀 Frekans (Hz)", value=f"{son_veri.get('frekans', 50.0)} Hz")
                
                st.markdown("---")
                col_kwh, col_tl, col_cos = st.columns(3)
                kwh_val = son_veri.get('toplam_kwh', 0.0)
                col_kwh.metric(label="📦 Toplam Enerji Tüketimi", value=f"{kwh_val:.2f} kWh")
                col_tl.metric(label="💰 Dönemsel Maliyet Yükü", value=f"{kwh_val * ELEKTRIK_TARIFESI:.2f} TL")
                col_cos.metric(label="📉 Güç Faktörü (Cos φ)", value=f"{son_veri.get('cos_phi', 1.0):.2f}")

                st.markdown("---")
                if son_veri.get('UYARI_DURUMU', 'NORMAL') != "NORMAL":
                    st.error(f"🚨 SİSTEM ALARMI: {son_veri['UYARI_DURUMU']}")
                else:
                    st.success("✅ Sistem Durumu: Kararlı (Tüm değerler nominal sınırlarda)")

                st.subheader("📊 Zaman Serisi Grafikleri")
                tab1, tab2 = st.tabs(["Yük & Gerilim Grafiği", "Akım & Verimlilik Grafiği"])
                with tab1:
                    st.line_chart(df.tail(veri_sayisi).set_index('zaman')[['voltaj', 'guc']])
                with tab2:
                    if 'cos_phi' in df.columns:
                        st.line_chart(df.tail(veri_sayisi).set_index('zaman')[['akim', 'cos_phi']])

                st.subheader("📋 Geçmiş Kayıt Günlüğü")
                gosterilecek_sutunlar = ['zaman', 'voltaj', 'akim', 'guc', 'toplam_kwh', 'UYARI_DURUMU']
                mevcut_sutunlar = [c for c in gosterilecek_sutunlar if c in df.columns]
                st.dataframe(df[mevcut_sutunlar].iloc[::-1], use_container_width=True)
            else:
                st.warning(f"⚠️ {hedef_fabrika} adına kayıtlı canlı veri akışı henüz bulunmuyor.")
        else:
            st.warning("Veri tabanından veri okunamıyor...")
    except Exception as e:
        st.error(f"AWS Bağlantı Hatası: {str(e)}")

    if otomatik_yenileme:
        time.sleep(3)
        st.rerun()
