import streamlit as st
import boto3
import pandas as pd
from boto3.dynamodb.conditions import Attr
import time
from datetime import datetime, time as dt_time
import io
from sklearn.ensemble import IsolationForest 

# --- Sayfa Yapılandırması ---
st.set_page_config(page_title="Kürüm Mühendislik İzleme", layout="wide", page_icon="⚡")

# Estetik CSS Dokunuşları
st.markdown("""
    <style>
    [data-testid="stMetric"] {background-color: #f9f9f9; padding: 15px; border-radius: 10px; border-left: 5px solid #2E86C1; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);}
    th {background-color: #f0f2f6 !important; text-align: center !important;}
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_table():
    session = boto3.Session(
        aws_access_key_id=st.secrets["ACCESS_KEY"],
        aws_secret_access_key=st.secrets["SECRET_KEY"],
        region_name="us-east-1"
    )
    return session.resource('dynamodb').Table('Enerji_Verileri')

# --- Oturum Yönetimi ---
if "giris" not in st.session_state: st.session_state.giris = False

if not st.session_state.giris:
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
    
    periyot = st.sidebar.selectbox("📊 Grafik Çözünürlüğü:", 
                                   ["Anlık (Ham Veri)", "Saatlik", "Günlük", "Haftalık", "Aylık"])
    
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
    indirme_yeri = st.sidebar.empty()
    
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
                df['akim'] = pd.to_numeric(df['akim']) if 'akim' in df.columns else 0.0
                df['zaman'] = pd.to_datetime(df['zaman'])
                df['voltaj'] = pd.to_numeric(df['voltaj']) if 'voltaj' in df.columns else 0.0
                df = df.sort_values('zaman')
                
                mask = (df['zaman'].dt.date >= baslangic) & (df['zaman'].dt.date <= bitis)
                df = df.loc[mask]
                
                if not df.empty:
                    # Hata giderildi: unique key eklendi
                    csv = df.to_csv(index=False).encode('utf-8-sig')
                    indirme_yeri.download_button("📥 Seçili Veriyi İndir (CSV)", csv, f"{secili_fabrika}_rapor.csv", "text/csv", key=f"btn_{i}")
                    
                    # --- YZ Anomali Tespiti ---
                    if len(df) > 10:
                        model = IsolationForest(contamination=0.05)
                        df['anomaly'] = model.fit_predict(df[['guc', 'voltaj', 'akim']])
                        if df.iloc[-1]['anomaly'] == -1:
                            st.error(f"🚨 YZ Anomali Uyarısı: {df.iloc[-1]['zaman'].strftime('%H:%M:%S')} - Sıra dışı enerji aktivitesi tespit edildi!")

                    df_plot = df.set_index('zaman')
                    mapping = {"Saatlik": 'h', "Günlük": 'D', "Haftalık": 'W', "Aylık": 'ME'}
                    if periyot != "Anlık (Ham Veri)":
                        df_plot = df_plot.resample(mapping[periyot]).mean(numeric_only=True)
                    
                    anlik = df.iloc[-1]['guc']
                    onceki = df.iloc[-2]['guc'] if len(df) > 1 else anlik
                    vol = df.iloc[-1]['voltaj']
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Anlık Güç", f"{anlik} W", delta=f"{anlik - onceki} W")
                    c2.metric("Periyot Ort. Güç", f"{int(df_plot['guc'].mean())} W")
                    c3.metric("Anlık Voltaj", f"{vol:.2f} V")
                    c4.metric("Fabrika", "✅ Aktif")
                    
                    col_g1, col_g2 = st.columns(2)
                    col_g1.subheader(f"📈 Güç Geçmişi ({periyot})")
                    col_g1.line_chart(df_plot[['guc']])
                    col_g2.subheader(f"📉 Voltaj Geçmişi ({periyot})")
                    col_g2.line_chart(df_plot[['voltaj']])
                    
                    st.subheader("📋 Detaylı Veri Logu")
                    styled_df = df[['zaman', 'cihaz', 'guc', 'voltaj', 'akim', 'fabrika']].sort_values('zaman', ascending=False)
                    st.dataframe(styled_df.style.background_gradient(subset=['guc', 'akim'], cmap='Blues'), use_container_width=True)
                else:
                    st.warning("Bu tarih aralığında veri yok.")
            else:
                st.info("⏳ Veri akışı bekleniyor...")
        time.sleep(5)
