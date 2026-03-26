import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import io

# ─────────────────────────────────────────────
# 1. CONFIGURACIÓN Y ESTÉTICA DARK
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Expreso Diemar - Fleet Analytics",
    page_icon="🚛",
    layout="wide",
)

# CSS para fondo oscuro e imagen difuminada
# TIP: Cambiá el URL por el de tu foto de los 5 camiones en GitHub
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)), 
                    url("https://raw.githubusercontent.com/nicolascolonna23/ServiceDM/main/IMG_3101.jpg"); 
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

# ─────────────────────────────────────────────
# 2. CARGA DE DATOS (IMPORTANTE: Antes de la navegación)
# ─────────────────────────────────────────────
@st.cache_data(ttl=600)
def get_data():
    # Links de tus archivos (Asegurate que terminen en download=1)
    u1 = "https://expresodiemar-my.sharepoint.com/:x:/g/personal/nicolascolonna_expresodiemar_onmicrosoft_com/IQCCJG7r9T2JTb0eAdpQU1ggAcTn9ZELfjq58Xk9-eqj58o?download=1"
    u2 = "https://expresodiemar-my.sharepoint.com/:x:/g/personal/nicolascolonna_expresodiemar_onmicrosoft_com/IQAWlrsay0HVT622_ANLB-bWAfMlRi4IHHFMH6DJBzVW3BU?download=1"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    def download(url):
        r = requests.get(url, headers=headers)
        return pd.read_excel(io.BytesIO(r.content))

    df_tel = download(u1)
    df_con = download(u2)
    
    # Normalización de nombres (limpieza de tildes y espacios)
    for d in [df_tel, df_con]:
        d.columns = d.columns.str.strip().str.replace('í', 'i').str.replace('á', 'a')
        if 'FECHA' in d.columns:
            d['FECHA'] = pd.to_datetime(d['FECHA'], errors='coerce')
            
    df = pd.merge(df_tel, df_con, on=["FECHA", "DOMINIO"])
    
    # Cálculos base
    df['g_co2_km'] = (df['Emisiones (KG CO2)'] / df['DISTANCIA RECORRIDA TELEMETRIA']) * 1000
    return df

try:
    df_full = get_data()
except Exception as e:
    st.error(f"Error cargando datos: {e}")
    st.stop()

# ─────────────────────────────────────────────
# 3. SIDEBAR Y NAVEGACIÓN
# ─────────────────────────────────────────────
with st.sidebar:
    # Usamos el logo que subiste
    st.image("logo_diemar4.png", use_container_width=True)
    st.divider()
    
    portal = st.radio("Ir a:", ["📊 Desempeño de Flota", "🌿 Portal de Emisiones CO2"])
    
    st.divider()
    # Filtros globales
    marcas = ["Todas"] + sorted(df_full["MARCA"].dropna().unique().tolist())
    marca_sel = st.selectbox("🏭 Marca", marcas)

# Filtrado dinámico
df = df_full.copy()
if marca_sel != "Todas":
    df = df[df["MARCA"] == marca_sel]

# ─────────────────────────────────────────────
# 4. PORTALES (LÓGICA DE VISTA)
# ─────────────────────────────────────────────

if portal == "📊 Desempeño de Flota":
    st.title("🚛 Fleet Analytics - Expreso Diemar")
    
    # KPIs Rápidos
    c1, c2, c3 = st.columns(3)
    c1.metric("Kms Totales", f"{df['DISTANCIA RECORRIDA TELEMETRIA'].sum():,.0f}")
    c2.metric("Consumo Promedio", f"{df['Consumo c/ 100km TELEMETRIA'].mean():.2f} L/100")
    c3.metric("Litros Totales", f"{df['LITROS CONSUMIDOS'].sum():,.0f}")

    # Gráfico de Desvíos
    st.subheader("📍 Análisis de Eficiencia")
    fig = px.scatter(df, x="DISTANCIA RECORRIDA TELEMETRIA", y="LITROS CONSUMIDOS", 
                     color="DOMINIO", size="Ralenti (Lts)", hover_name="DOMINIO",
                     template="plotly_dark")
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

elif portal == "🌿 Portal de Emisiones CO2":
    st.title("🌿 Portal de Sustentabilidad")
    st.markdown("Seguimiento de Huella de Carbono por Unidad")

    # KPIs Emisiones
    c1, c2, c3 = st.columns(3)
    total_co2 = df['Emisiones (KG CO2)'].sum()
    c1.metric("Emisiones Totales", f"{total_co2:,.0f} kg CO2")
    
    km_tot = df['DISTANCIA RECORRIDA TELEMETRIA'].sum()
    eficiencia_co2 = (total_co2 / km_tot * 1000) if km_tot > 0 else 0
    c2.metric("Eficiencia gCO2/km", f"{eficiencia_co2:.1f} g")
    
    c3.metric("Unidad + Limpia", df.sort_values("g_co2_km").iloc[0]["DOMINIO"])

    st.divider()

    col_map, col_table = st.columns([1.5, 1])

    with col_map:
        fig_co2 = px.bar(df.sort_values("Emisiones (KG CO2)", ascending=False),
                         x="DOMINIO", y="Emisiones (KG CO2)", color="Emisiones (KG CO2)",
                         title="CO2 Total por Patente", color_continuous_scale="Reds",
                         template="plotly_dark")
        fig_co2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_co2, use_container_width=True)

    with col_table:
        st.subheader("Detalle por Unidad")
        df_em = df[['DOMINIO', 'MARCA', 'Emisiones (KG CO2)', 'g_co2_km']].sort_values("g_co2_km")
        st.dataframe(df_em.style.format({'g_co2_km': '{:.1f}', 'Emisiones (KG CO2)': '{:,.0f}'}), 
                     use_container_width=True)

# ─────────────────────────────────────────────
# 5. FOOTER
# ─────────────────────────────────────────────
st.divider()
st.caption("Fleet Analytics Expreso Diemar © 2026 - Conectado a SharePoint")
