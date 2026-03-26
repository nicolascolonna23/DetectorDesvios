import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import io

# 1. CONFIGURACIÓN Y ESTÉTICA
st.set_page_config(page_title="Expreso Diemar - Fleet Analytics", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)), 
                    url("https://raw.githubusercontent.com/nicolascolonna23/DetectorDesvios/main/IMG_3101.jpg"); 
        background-size: cover;
        background-attachment: fixed;
    }
    [data-testid="stSidebar"] { background-color: rgba(15, 15, 15, 0.95); }
    .stMetric { background-color: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1); }
    h1, h2, h3, h4, span, p { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNCIÓN DE CARGA CON DIAGNÓSTICO
@st.cache_data(ttl=300)
def get_data():
    # Tus links de SharePoint
    u1 = "https://expresodiemar-my.sharepoint.com/:x:/g/personal/nicolascolonna_expresodiemar_onmicrosoft_com/IQCCJG7r9T2JTb0eAdpQU1ggAcTn9ZELfjq58Xk9-eqj58o?download=1"
    u2 = "https://expresodiemar-my.sharepoint.com/:x:/g/personal/nicolascolonna_expresodiemar_onmicrosoft_com/IQAWlrsay0HVT622_ANLB-bWAfMlRi4IHHFMH6DJBzVW3BU?download=1"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    def download(url):
        r = requests.get(url, headers=headers)
        return pd.read_excel(io.BytesIO(r.content))

    df_tel = download(u1) # Telemetría
    df_con = download(u2) # Conducción/Extra
    
    # Limpieza de columnas
    for d in [df_tel, df_con]:
        d.columns = d.columns.str.strip().str.replace('í', 'i').str.replace('á', 'a')
        if 'DOMINIO' in d.columns:
            d['DOMINIO'] = d['DOMINIO'].astype(str).str.replace(' ', '').str.upper()
        if 'FECHA' in d.columns:
            d['FECHA'] = pd.to_datetime(d['FECHA'], errors='coerce').dt.date

    # --- PANEL DE DIAGNÓSTICO EN SIDEBAR ---
    with st.sidebar:
        st.divider()
        st.subheader("🔍 Diagnóstico de Datos")
        st.write(f"📊 **Excel Telemetría:** {len(df_tel)} filas")
        st.write(f"📊 **Excel Conducción:** {len(df_con)} filas")
        
        if not df_tel.empty and not df_con.empty:
            st.info(f"Ejemplo Patente Tel: {df_tel['DOMINIO'].iloc[0]}")
            st.info(f"Ejemplo Patente Con: {df_con['DOMINIO'].iloc[0]}")
            st.info(f"Ejemplo Fecha Tel: {df_tel['FECHA'].iloc[0]}")
            st.info(f"Ejemplo Fecha Con: {df_con['FECHA'].iloc[0]}")

    # Cruce de datos
    df = pd.merge(df_tel, df_con, on=["FECHA", "DOMINIO"])
    
    if not df.empty:
        df['g_co2_km'] = (df['Emisiones (KG CO2)'] / df['DISTANCIA RECORRIDA TELEMETRIA']) * 1000
    
    return df

# Ejecución
try:
    df_full = get_data()
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

# 3. NAVEGACIÓN
with st.sidebar:
    st.image("logo_diemar4.png", use_container_width=True)
    portal = st.radio("Sección:", ["📊 Desempeño", "🌿 Emisiones"])
    marcas = ["Todas"] + sorted(df_full["MARCA"].dropna().unique().tolist()) if not df_full.empty else ["Todas"]
    marca_sel = st.selectbox("Filtrar Marca:", marcas)

df = df_full.copy()
if marca_sel != "Todas":
    df = df[df["MARCA"] == marca_sel]

# 4. VISTAS
if df.empty:
    st.warning("⚠️ Sin coincidencias. Revisá el 'Diagnóstico' en la barra lateral.")
else:
    if portal == "📊 Desempeño":
        st.title("Desempeño de Flota")
        c1, c2 = st.columns(2)
        c1.metric("Km Totales", f"{df['DISTANCIA RECORRIDA TELEMETRIA'].sum():,.0f}")
        c2.metric("Litros Totales", f"{df['LITROS CONSUMIDOS'].sum():,.0f}")
        st.plotly_chart(px.scatter(df, x="DISTANCIA RECORRIDA TELEMETRIA", y="LITROS CONSUMIDOS", color="DOMINIO", template="plotly_dark"), use_container_width=True)
    else:
        st.title("Portal de Emisiones")
        st.metric("Total CO2", f"{df['Emisiones (KG CO2)'].sum():,.0f} kg")
        st.plotly_chart(px.bar(df, x="DOMINIO", y="Emisiones (KG CO2)", template="plotly_dark"), use_container_width=True)
