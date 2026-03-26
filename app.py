import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import io

# 1. CONFIGURACIÓN Y ESTÉTICA DARK
st.set_page_config(
    page_title="Expreso Diemar - Fleet Analytics",
    page_icon="🚛",
    layout="wide",
)

# CSS para fondo oscuro e imagen de fondo
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)), 
                    url("https://raw.githubusercontent.com/nicolascolonna23/DetectorDesvios/main/IMG_3101.jpg"); 
        background-size: cover;
        background-attachment: fixed;
    }
    [data-testid="stSidebar"] {
        background-color: rgba(15, 15, 15, 0.95);
    }
    .stMetric {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    h1, h2, h3, h4, span, p {
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. CARGA Y CRUCE FLEXIBLE (ENFOCADO EN 2026)
@st.cache_data(ttl=600)
def get_data():
    u1 = "https://expresodiemar-my.sharepoint.com/:x:/g/personal/nicolascolonna_expresodiemar_onmicrosoft_com/IQCCJG7r9T2JTb0eAdpQU1ggAcTn9ZELfjq58Xk9-eqj58o?download=1"
    u2 = "https://expresodiemar-my.sharepoint.com/:x:/g/personal/nicolascolonna_expresodiemar_onmicrosoft_com/IQAWlrsay0HVT622_ANLB-bWAfMlRi4IHHFMH6DJBzVW3BU?download=1"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    def download(url):
        r = requests.get(url, headers=headers)
        return pd.read_excel(io.BytesIO(r.content))

    df_tel = download(u1)
    df_con = download(u2)
    
    # Limpieza de Dominios y Nombres
    for d in [df_tel, df_con]:
        d.columns = d.columns.str.strip().str.replace('í', 'i').str.replace('á', 'a')
        if 'DOMINIO' in d.columns:
            d['DOMINIO'] = d['DOMINIO'].astype(str).str.replace(' ', '').str.upper()
        if 'FECHA' in d.columns:
            d['FECHA_DT'] = pd.to_datetime(d['FECHA'], errors='coerce')

    # UNIÓN FLEXIBLE: Por Dominio
    df = pd.merge(df_tel, df_con, on="DOMINIO", suffixes=('_tel', '_con'))
    
    # Filtro estricto de Año 2026
    if not df.empty and 'FECHA_DT_tel' in df.columns:
        df = df[df['FECHA_DT_tel'].dt.year == 2026].copy()

    if not df.empty:
        # Cálculo de CO2 y eficiencia
        df['g_co2_km'] = (df['Emisiones (KG CO2)'] / df['DISTANCIA RECORRIDA TELEMETRIA']) * 1000
    
    return df

# Ejecutar carga
try:
    df_full = get_data()
except Exception as e:
    st.error(f"❌ Error crítico: {e}")
    st.stop()

# 3. SIDEBAR
with st.sidebar:
    st.image("logo_diemar4.png", use_container_width=True)
    st.divider()
    portal = st.radio("Sección:", ["📊 Desempeño de Flota", "🌿 Portal de Emisiones CO2"])
    
    st.divider()
    if not df_full.empty:
        marcas = ["Todas"] + sorted(df_full["MARCA"].dropna().unique().tolist())
        marca_sel = st.selectbox("🏭 Filtrar por Marca", marcas)
    else:
        marca_sel = "Todas"

# Filtrado dinámico
df = df_full.copy()
if marca_sel != "Todas":
    df = df[df["MARCA"] == marca_sel]

# 4. VISTAS
if df.empty:
    st.warning("⚠️ Sin datos coincidentes para 2026.")
else:
    if portal == "📊 Desempeño de Flota":
        st.title("🚛 Fleet Analytics 2026")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("🛣️ Km Totales", f"{df['DISTANCIA RECORRIDA TELEMETRIA'].sum():,.0f}")
        c2.metric("📊 L/100km Prom.", f"{df['Consumo c/ 100km TELEMETRIA'].mean():.2f}")
        c3.metric("⛽ Litros Totales", f"{df['LITROS CONSUMIDOS'].sum():,.0f}")

        st.subheader("📍 Eficiencia por Unidad")
        
        # --- LIMPIEZA PARA EL GRÁFICO (EVITA EL VALUEERROR) ---
        df_plot = df.copy()
        df_plot['Ralenti (Lts)'] = df_plot['Ralenti (Lts)'].fillna(0).clip(lower=0)
        # Si no hay datos de ralentí, usamos un tamaño base fijo de 10
        if df_plot['Ralenti (Lts)'].sum() == 0:
            df_plot['size_burbuja'] = 10
        else:
            df_plot['size_burbuja'] = df_plot['Ralenti (Lts)'] + 5 # +5 para que se vean

        fig = px.scatter(df_plot, 
                         x="DISTANCIA RECORRIDA TELEMETRIA", 
                         y="LITROS CONSUMIDOS", 
                         color="DOMINIO", 
                         size="size_burbuja", 
                         hover_name="DOMINIO",
                         hover_data=["Ralenti (Lts)", "Consumo c/ 100km TELEMETRIA"],
                         template="plotly_dark")
        
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

    elif portal == "🌿 Portal de Emisiones CO2":
        st.title("🌿 Sustentabilidad 2026")
        
        total_co2 = df['Emisiones (KG CO2)'].sum()
        c1, c2 = st.columns(2)
        c1.metric("Huella de Carbono Total", f"{total_co2:,.0f} kg CO2")
        
        km_tot = df['DISTANCIA RECORRIDA TELEMETRIA'].sum()
        ef_co2 = (total_co2 / km_tot * 1000) if km_tot > 0 else 0
        c2.metric("Promedio gCO2/km", f"{ef_co2:.1f} g")
        
        fig_co2 = px.bar(df.sort_values("Emisiones (KG CO2)", ascending=False),
                         x="DOMINIO", y="Emisiones (KG CO2)", color="Emisiones (KG CO2)",
                         template="plotly_dark", color_continuous_scale="Reds")
        fig_co2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_co2, use_container_width=True)

# 5. FOOTER
st.divider()
st.caption(f"Exclusivo 2026 | Registros procesados: {len(df)}")
