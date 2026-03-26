import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import io

# 1. CONFIGURACIÓN Y ESTÉTICA DARK
st.set_page_config(page_title="Expreso Diemar - Fleet Analytics", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.9), rgba(0, 0, 0, 0.9)), 
                    url("https://raw.githubusercontent.com/nicolascolonna23/DetectorDesvios/main/IMG_3101.jpg"); 
        background-size: cover; background-attachment: fixed;
    }
    [data-testid="stSidebar"] { background-color: rgba(10, 10, 10, 0.98); }
    .stMetric { background-color: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 10px; border-left: 5px solid #1565c0; }
    h1, h2, h3, h4, span, p { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. CARGA DE DATOS
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
    
    for d in [df_tel, df_con]:
        d.columns = d.columns.str.strip().str.replace('í', 'i').str.replace('á', 'a')
        if 'DOMINIO' in d.columns:
            d['DOMINIO'] = d['DOMINIO'].astype(str).str.replace(' ', '').str.upper()
        if 'FECHA' in d.columns:
            d['FECHA_DT'] = pd.to_datetime(d['FECHA'], errors='coerce')
            d['MES'] = d['FECHA_DT'].dt.strftime('%B %Y')

    df = pd.merge(df_tel, df_con, on="DOMINIO", suffixes=('_tel', '_con'))
    return df

try:
    df_full = get_data()
except Exception as e:
    st.error(f"❌ Error: {e}"); st.stop()

# 3. SIDEBAR
with st.sidebar:
    st.image("logo_diemar4.png", use_container_width=True)
    portal = st.radio("Sección:", ["📊 Desempeño", "⛽ Combustible & Costos", "🌿 Emisiones"])
    st.divider()
    meses = ["Todos"] + sorted(df_full["MES_tel"].dropna().unique().tolist())
    mes_sel = st.selectbox("📅 Mes", meses)
    marcas = ["Todas"] + sorted(df_full["MARCA"].dropna().unique().tolist())
    marca_sel = st.selectbox("🏭 Marca", marcas)

df = df_full.copy()
if mes_sel != "Todos": df = df[df["MES_tel"] == mes_sel]
if marca_sel != "Todas": df = df[df["MARCA"] == marca_sel]

# 4. VISTAS
if df.empty:
    st.warning("⚠️ Sin datos.")
else:
    if portal == "📊 Desempeño":
        st.title("📊 Desempeño de Flota")
        c1, c2, c3 = st.columns(3)
        c1.metric("Km Totales", f"{df['DISTANCIA RECORRIDA TELEMETRIA'].sum():,.0f}")
        c2.metric("L/100km Promedio", f"{df['Consumo c/ 100km TELEMETRIA'].mean():.2f}")
        c3.metric("Litros Totales", f"{df['LITROS CONSUMIDOS'].sum():,.0f}")

        st.subheader("📍 Eficiencia: Consumo vs Distancia")
        df_plot = df.copy()
        # ARREGLO DE ESCALA: Limpieza de nulos y negativos para evitar error
        df_plot['Ralenti (Lts)'] = df_plot['Ralenti (Lts)'].fillna(0).clip(lower=0)
        df_plot['size_burbuja'] = df_plot['Ralenti (Lts)'] + 5
        
        fig = px.scatter(df_plot, x="DISTANCIA RECORRIDA TELEMETRIA", y="LITROS CONSUMIDOS", 
                         color="DOMINIO", size="size_burbuja", hover_name="DOMINIO",
                         template="plotly_dark")
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

    elif portal == "⛽ Combustible & Costos":
        st.title("⛽ Control de Costos y Ralentí")
        precio_gasoil = 1250 # Podés cambiar este valor según el precio actual
        ral_tot = df['Ralenti (Lts)'].sum()
        perdida_dinero = ral_tot * precio_gasoil

        c1, c2, c3 = st.columns(3)
        c1.metric("Litros en Ralentí", f"{ral_tot:,.0f} L")
        c2.metric("Dinero Perdido (Ralentí)", f"${perdida_dinero:,.0f}", delta="Pérdida Crítica", delta_color="inverse")
        c3.metric("Kms/Mes Promedio", f"{(df['DISTANCIA RECORRIDA TELEMETRIA'].sum()/1000):.1f} mil")

        st.divider()
        st.subheader("Ranking de Desperdicio por Patente")
        fig_cost = px.bar(df.sort_values("Ralenti (Lts)", ascending=False), 
                          x="DOMINIO", y="Ralenti (Lts)", color="Ralenti (Lts)",
                          title="Litros Perdidos con Motor en Marcha", color_continuous_scale="Oranges")
        fig_cost.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_cost, use_container_width=True)

    elif portal == "🌿 Emisiones":
        st.title("🌿 Portal de Sustentabilidad")
        total_co2 = df['Emisiones (KG CO2)'].sum()
        st.metric("CO2 Total (kg)", f"{total_co2:,.0f}")
        fig_co2 = px.bar(df.sort_values("Emisiones (KG CO2)", ascending=False),
                         x="DOMINIO", y="Emisiones (KG CO2)", color="Emisiones (KG CO2)",
                         template="plotly_dark", color_continuous_scale="Reds")
        fig_co2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_co2, use_container_width=True)

st.divider()
st.caption(f"Fleet Analytics Expreso Diemar | Datos procesados: {len(df)} filas.")
