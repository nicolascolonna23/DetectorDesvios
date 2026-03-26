import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import io

# 1. CONFIGURACIÓN Y ESTÉTICA "ECO-DARK"
st.set_page_config(page_title="Expreso Diemar - Carbon Tracker", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.9), rgba(0, 0, 0, 0.9)), 
                    url("https://raw.githubusercontent.com/nicolascolonna23/DetectorDesvios/main/IMG_3101.jpg"); 
        background-size: cover; background-attachment: fixed;
    }
    .stMetric {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 15px; border-radius: 10px; border-top: 4px solid #2e7d32;
    }
    h1, h2, h3, h4, span, p { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. CARGA Y PROCESAMIENTO CON CRUCE TEMPORAL
@st.cache_data(ttl=600)
def get_data():
    u1 = "https://expresodiemar-my.sharepoint.com/:x:/g/personal/nicolascolonna_expresodiemar_onmicrosoft_com/IQCCJG7r9T2JTb0eAdpQU1ggAcTn9ZELfjq58Xk9-eqj58o?download=1" # Telemetría (Varios meses)
    u2 = "https://expresodiemar-my.sharepoint.com/:x:/g/personal/nicolascolonna_expresodiemar_onmicrosoft_com/IQAWlrsay0HVT622_ANLB-bWAfMlRi4IHHFMH6DJBzVW3BU?download=1" # Conducción (Solo Enero)
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    def download(url):
        r = requests.get(url, headers=headers)
        return pd.read_excel(io.BytesIO(r.content))

    df_tel = download(u1)
    df_con = download(u2)
    
    # Limpieza y Formato de Fechas en ambos Excels
    for d in [df_tel, df_con]:
        d.columns = d.columns.str.strip().str.replace('í', 'i').str.replace('á', 'a')
        if 'DOMINIO' in d.columns:
            d['DOMINIO'] = d['DOMINIO'].astype(str).str.replace(' ', '').str.upper()
        if 'FECHA' in d.columns:
            d['FECHA_DT'] = pd.to_datetime(d['FECHA'], errors='coerce')
            # Creamos una columna 'KEY_TIEMPO' con formato '2026-01' para el cruce
            d['KEY_TIEMPO'] = d['FECHA_DT'].dt.strftime('%Y-%m')

    # --- EL CRUCE CRÍTICO ---
    # Cruzamos por DOMINIO Y por KEY_TIEMPO (Mes y Año)
    # Esto asegura que si en Telemetría hay datos de Diciembre, no se mezclen con el CO2 de Enero.
    df = pd.merge(df_tel, df_con, on=["DOMINIO", "KEY_TIEMPO"], suffixes=('_tel', '_con'))
    
    return df

try:
    df = get_data()
except Exception as e:
    st.error(f"❌ Error en el cruce de datos: {e}"); st.stop()

# 3. SIDEBAR
with st.sidebar:
    st.image("logo_diemar4.png", use_container_width=True)
    st.title("🌿 Carbon Control")
    st.divider()
    
    # Solo mostramos los meses donde el cruce fue exitoso (donde hay coincidencia)
    meses_disponibles = sorted(df["KEY_TIEMPO"].unique().tolist())
    mes_sel = st.selectbox("📅 Mes con Datos de CO2", meses_disponibles)
    
    marca_sel = st.selectbox("🏭 Marca", ["Todas"] + sorted(df["MARCA"].unique().tolist()))

# Filtrar por selección
df_view = df[df["KEY_TIEMPO"] == mes_sel]
if marca_sel != "Todas":
    df_view = df_view[df_view["MARCA"] == marca_sel]

# 4. DASHBOARD DE EMISIONES REALES
st.title(f"🌿 Análisis de Emisiones — Período {mes_sel}")
st.info("Nota: Este dashboard solo muestra datos cruzados donde coinciden Patente y Mes en ambos reportes.")

if df_view.empty:
    st.warning("No se encontraron coincidencias para los filtros seleccionados.")
else:
    # --- MÉTRICAS ---
    c1, c2, c3, c4 = st.columns(4)
    
    co2_total = df_view['Emisiones (KG CO2)'].sum()
    km_totales = df_view['DISTANCIA RECORRIDA TELEMETRIA'].sum()
    intensidad = (co2_total / km_totales * 1000) if km_totales > 0 else 0
    lts_ralenti = df_view['Ralenti (Lts)'].sum()
    ahorro_co2_ralenti = lts_ralenti * 2.68

    c1.metric("CO₂ TOTAL (MES)", f"{co2_total:,.0f} kg")
    c2.metric("INTENSIDAD", f"{intensidad:.1f} g/km")
    c3.metric("CO₂ EVITABLE (Ralentí)", f"{ahorro_co2_ralenti:,.1f} kg")
    c4.metric("UNIDADES ANALIZADAS", len(df_view['DOMINIO'].unique()))

    st.divider()

    # --- GRÁFICOS ---
    col1, col2 = st.columns([1.5, 1])

    with col1:
        st.subheader("📊 Huella de Carbono por Patente (Datos Cruzados)")
        fig_bar = px.bar(df_view.sort_values("Emisiones (KG CO2)", ascending=False), 
                         x="DOMINIO", y="Emisiones (KG CO2)", color="Emisiones (KG CO2)",
                         color_continuous_scale="Reds", template="plotly_dark")
        fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.subheader("📉 Eficiencia g/km por Marca")
        # Calculamos el promedio de g/km por marca
        df_view['g_km'] = (df_view['Emisiones (KG CO2)'] / df_view['DISTANCIA RECORRIDA TELEMETRIA']) * 1000
        df_marca = df_view.groupby('MARCA')['g_km'].mean().reset_index()
        fig_marca = px.bar(df_marca, x='MARCA', y='g_km', color='MARCA', template="plotly_dark")
        fig_marca.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_marca, use_container_width=True)

    # --- TABLA TÉCNICA ---
    st.subheader("📋 Detalle de Emisiones Validado")
    st.dataframe(df_view[['DOMINIO', 'MARCA', 'DISTANCIA RECORRIDA TELEMETRIA', 'LITROS CONSUMIDOS', 'Emisiones (KG CO2)']], use_container_width=True)

# 5. FOOTER
st.divider()
st.caption(f"Validación Expreso Diemar | Cruze por Mes/Año/Patente exitoso.")
