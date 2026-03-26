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

st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.9), rgba(0, 0, 0, 0.9)), 
                    url("https://raw.githubusercontent.com/nicolascolonna23/DetectorDesvios/main/IMG_3101.jpg"); 
        background-size: cover;
        background-attachment: fixed;
    }
    [data-testid="stSidebar"] { background-color: rgba(10, 10, 10, 0.98); }
    .stMetric {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #1565c0;
    }
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

    df = pd.merge(df_tel, df_con, on="DOMINIO", suffixes=('_tel', '_con'))
    
    # Rango de fechas: Diciembre 2025 a Febrero 2026
    if not df.empty and 'FECHA_DT_tel' in df.columns:
        df = df[(df['FECHA_DT_tel'] >= '2025-12-01') & (df['FECHA_DT_tel'] <= '2026-02-28')].copy()

    return df

try:
    df_full = get_data()
except Exception as e:
    st.error(f"❌ Error crítico: {e}")
    st.stop()

# 3. SIDEBAR - NAVEGACIÓN Y FILTROS
with st.sidebar:
    st.image("logo_diemar4.png", use_container_width=True)
    st.divider()
    portal = st.radio("Sección:", ["📊 Desempeño", "⛽ Combustible", "🌿 Emisiones"])
    
    st.divider()
    if not df_full.empty:
        patentes = sorted(df_full["DOMINIO"].unique().tolist())
        sel_patentes = st.multiselect("🚚 Patentes", patentes)
        
        marcas = ["Todas"] + sorted(df_full["MARCA"].dropna().unique().tolist())
        marca_sel = st.selectbox("🏭 Marca", marcas)

df = df_full.copy()
if sel_patentes:
    df = df[df["DOMINIO"].isin(sel_patentes)]
if marca_sel != "Todas":
    df = df[df["MARCA"] == marca_sel]

# 4. VISTAS
if df.empty:
    st.warning("⚠️ Sin datos para los filtros seleccionados.")
else:
    # --- PESTAÑA 1: DESEMPEÑO ---
    if portal == "📊 Desempeño":
        st.title("🚛 Fleet Analytics - Desempeño General")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Km Totales", f"{df['DISTANCIA RECORRIDA TELEMETRIA'].sum():,.0f}")
        c2.metric("L/100km Promedio", f"{df['Consumo c/ 100km TELEMETRIA'].mean():.2f}")
        c3.metric("Litros Totales", f"{df['LITROS CONSUMIDOS'].sum():,.0f}")

        st.subheader("📍 Dispersión: Consumo vs Distancia")
        df_plot = df.copy()
        df_plot['size_burbuja'] = df_plot['Ralenti (Lts)'].fillna(0).clip(lower=0) + 5
        fig = px.scatter(df_plot, x="DISTANCIA RECORRIDA TELEMETRIA", y="LITROS CONSUMIDOS", 
                         color="DOMINIO", size="size_burbuja", hover_name="DOMINIO",
                         template="plotly_dark")
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

    # --- PESTAÑA 2: COMBUSTIBLE ---
    elif portal == "⛽ Combustible":
        st.title("⛽ Control de Combustible")
        
        m1, m2, m3 = st.columns(3)
        lts_tot = df['LITROS CONSUMIDOS'].sum()
        ral_tot = df['Ralenti (Lts)'].sum()
        m1.metric("Consumo Total (Lts)", f"{lts_tot:,.0f}")
        m2.metric("Ralentí Total (Lts)", f"{ral_tot:,.0f}")
        m3.metric("Kms Promedio/Mes", f"{(df['DISTANCIA RECORRIDA TELEMETRIA'].sum()/3000):.1f} mil")

        st.divider()
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("Ranking Consumo por Unidad")
            fig_bar = px.bar(df.groupby('DOMINIO')['LITROS CONSUMIDOS'].sum().reset_index().sort_values('LITROS CONSUMIDOS'),
                             x='LITROS CONSUMIDOS', y='DOMINIO', orientation='h', 
                             color='LITROS CONSUMIDOS', color_continuous_scale='Blues', template="plotly_dark")
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_right:
            st.subheader("Evolución L/100km")
            df_line = df.groupby(df['FECHA_DT_tel'].dt.strftime('%Y-%m')).agg({'Consumo c/ 100km TELEMETRIA':'mean'}).reset_index()
            fig_line = px.line(df_line, x='FECHA_DT_tel', y='Consumo c/ 100km TELEMETRIA', 
                               markers=True, template="plotly_dark")
            fig_line.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_line, use_container_width=True)

    # --- PESTAÑA 3: EMISIONES ---
    elif portal == "🌿 Emisiones":
        st.title("🌿 Portal de Sustentabilidad")
        
        e1, e2, e3 = st.columns(3)
        total_co2 = df['Emisiones (KG CO2)'].sum()
        km_tot = df['DISTANCIA RECORRIDA TELEMETRIA'].sum()
        e1.metric("CO2 Total (kg)", f"{total_co2:,.0f}")
        e2.metric("Eficiencia (gCO2/km)", f"{(total_co2/km_tot*1000):.1f}" if km_tot > 0 else "0")
        e3.metric("Camiones Analizados", len(df['DOMINIO'].unique()))

        st.divider()
        st.subheader("Huella de Carbono por Patente")
        fig_co2 = px.bar(df.sort_values("Emisiones (KG CO2)", ascending=False),
                         x="DOMINIO", y="Emisiones (KG CO2)", color="Emisiones (KG CO2)",
                         template="plotly_dark", color_continuous_scale="Reds")
        fig_co2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_co2, use_container_width=True)

# 5. FOOTER
st.divider()
st.caption(f"Fleet Analytics Expreso Diemar | Datos procesados: {len(df)} registros.")
