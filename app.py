import streamlit as st
import boto3
import pandas as pd
from boto3.dynamodb.conditions import Attr
import time
from datetime import datetime, time as dt_time

# --- Sayfa Yapılandırması ---
st.set_page_config(page_title="Kürüm Mühendislik İzleme", layout="wide", page_icon="⚡")

# --- AWS Ayarları ---
ACCESS_KEY = "AKIASH3ZBYKXQQQAG44E"
SECRET_KEY = "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"
REGION = "us-east-1"

@st.cache_resource
def get_table():
    session = boto3.Session(aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, region_name=REGION)
    return session.resource('dynamodb').Table('Enerji_Verileri')

# --- Oturum Yönetimi ---
if "giris" not in st.session_state: st.session_state.giris = False

if not st.session_state.giris:
    # Logon varsa buraya st.image("logo.png") ekleyebilirsin
    st.markdown("<h1 style='text-align: center; color: #2E86C1;'>𝓚𝓤̈𝓡𝓤̈𝓜 𝓘̇𝓩𝓛𝓔𝓜𝓔 𝓢𝓘̇𝓢𝓣𝓔𝓜𝓛𝓔𝓡𝓘̇</h1>", unsafe_allow_html=True)
    st.subheader("🔑 Giriş Portalı")
    user = st.text_input("Kullanıcı Adı")
    pw = st.text_input("Şifre", type="password")
    if st.button("🚀 Giriş Yap"):
        if (user == "Özdemir Kamer Kürüm" and pw == "7652044") or (user == "Halil Mert Kürüm" and pw == "hmk1634"):
            st.session_state.giris = True
            st.session_state.kullanici = user
            st.rerun()
        else: st.error("⚠️ Hatalı Giriş!")
else:
    # --- Sidebar ---
    st.sidebar.markdown("## ⚙️ 𝓚𝓤̈𝓡𝓤̈𝓜 𝓘̇𝓩𝓛𝓔𝓜𝓔")
    secili_fabrika = st.sidebar.selectbox("🏭 Fabrika:", ["Bursa_Fabrika", "İstanbul_Fabrika", "Ankara_Fabrika"])
    
    st.sidebar.subheader("📅 Tarih Filtresi")
    baslangic = st.sidebar.date_input("Başlangıç", datetime.now())
    bitis = st.sidebar.date_input("Bitiş", datetime.now())
    
    # --- Admin Yetkileri ---
    if st.session_state.kullanici == "Özdemir Kamer Kürüm":
        st.sidebar.markdown("---")
        st.sidebar.subheader("🧨 Admin Veri Yönetimi")
        saat_bas = st.sidebar.time_input("Silme Başlangıç Saati", dt_time(0, 0))
        saat_bit = st.sidebar.time_input("Silme Bitiş Saati", dt_time(23, 59))
        
        if st.sidebar.button("🗑️ Seçili Aralığı Temizle"):
            table = get_table()
            items = table.scan(FilterExpression=Attr('fabrika').eq(secili_fabrika))['Items']
            for item in items:
                zaman = pd.to_datetime(item['zaman'])
                if saat_bas <= zaman.time() <= saat_bit:
                    table.delete_item(Key={'cihaz': item['cihaz'], 'zaman': item['zaman']})
            st.sidebar.success("Arşiv temizlendi!")
            st.rerun()

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Oturumu Kapat"):
        st.session_state.giris = False
        st.rerun()

    # --- Ana Dashboard ---
    st.title(f"⚡ {secili_fabrika} - Enerji & Voltaj İzleme")
    placeholder = st.empty()
    table = get_table()
    
    for i in range(100):
        with placeholder.container():
            response = table.scan(FilterExpression=Attr('fabrika').eq(secili_fabrika))
            items = response.get('Items', [])
            
            if items:
                df = pd.DataFrame(items)
                df['guc'] = pd.to_numeric(df['guc'])
                df['zaman'] = pd.to_datetime(df['zaman'])
                
                # Voltaj kontrolü (Hata almamak için)
                if 'voltaj' in df.columns:
                    df['voltaj'] = pd.to_numeric(df['voltaj'])
                else:
                    df['voltaj'] = 0.0
                
                df = df.sort_values('zaman')
                
                # Tarih Filtresi
                mask = (df['zaman'].dt.date >= baslangic) & (df['zaman'].dt.date <= bitis)
                df = df.loc[mask]
                
                if not df.empty:
                    anlik = df.iloc[-1]['guc']
                    onceki = df.iloc[-2]['guc'] if len(df) > 1 else anlik
                    vol = df.iloc[-1]['voltaj']
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Anlık Güç", f"{anlik} W", delta=f"{anlik - onceki} W")
                    c2.metric("Ortalama Güç", f"{int(df['guc'].mean())} W")
                    c3.metric("Anlık Voltaj", f"{vol:.2f} V")
                    c4.metric("Fabrika", "✅ Aktif")
                    
                    # Grafikler
                    col_g1, col_g2 = st.columns(2)
                    col_g1.subheader("📈 Güç Geçmişi")
                    col_g1.line_chart(df.set_index('zaman')[['guc']])
                    col_g2.subheader("📉 Voltaj Geçmişi")
                    col_g2.line_chart(df.set_index('zaman')[['voltaj']])
                    
                    st.subheader("📋 Detaylı Veri Logu")
                    st.dataframe(df[['zaman', 'cihaz', 'guc', 'voltaj', 'akim', 'fabrika']].sort_values('zaman', ascending=False), use_container_width=True)
                else:
                    st.warning("Bu tarih aralığında veri yok.")
            else:
                st.info("⏳ Veri akışı bekleniyor...")
        time.sleep(5)