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
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #1565c0;
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
    
    # Filtro Dinámico de Fecha (basado en tu captura: Dic 2025 a Feb 2026)
    if not df.empty and 'FECHA_DT_tel' in df.columns:
        df = df[(df['FECHA_DT_tel'] >= '2025-12-01') & (df['FECHA_DT_tel'] <= '2026-02-28')].copy()

    return df

try:
    df_full = get_data()
except Exception as e:
    st.error(f"❌ Error crítico: {e}")
    st.stop()

# 3. SIDEBAR - FILTROS
with st.sidebar:
    st.image("logo_diemar4.png", use_container_width=True)
    st.divider()
    portal = st.radio("Sección:", ["📊 Desempeño", "⛽ Combustible", "🌿 Emisiones"])
    
    st.divider()
    if not df_full.empty:
        # Selector de Dominio múltiple
        patentes = sorted(df_full["DOMINIO"].unique().tolist())
        sel_patentes = st.multiselect("🚚 Patentes", patentes, default=patentes[:3])
        
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
    if portal == "⛽ Combustible":
        st.title("⛽ Análisis de Combustible — Power BI Style")
        
        # FILA 1: MÉTRICAS Y VELOCÍMETRO
        col_gauge, col_metrics = st.columns([1, 1.2])
        
        with col_gauge:
            prom_l100 = df['Consumo c/ 100km TELEMETRIA'].mean()
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = prom_l100,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Promedio L/100km", 'font': {'size': 20}},
                gauge = {
                    'axis': {'range': [None, 70], 'tickwidth': 1},
                    'bar': {'color': "#1565c0"},
                    'steps': [
                        {'range': [0, 32], 'color': "green"},
                        {'range': [32, 40], 'color': "yellow"},
                        {'range': [40, 70], 'color': "red"}]}))
            fig_gauge.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, height=300)
            st.plotly_chart(fig_gauge, use_container_width=True)

        with col_metrics:
            m1, m2 = st.columns(2)
            kms_mes = df['DISTANCIA RECORRIDA TELEMETRIA'].sum() / 3 # Promedio 3 meses
            lts_mes = df['LITROS CONSUMIDOS'].sum() / 3
            m1.metric("PROMEDIO KMS/MES", f"{(kms_mes/1000):.2f} mil")
            m2.metric("PROMEDIO LTS/MES", f"{(lts_mes/1000):.2f} mil")
            
            # Gráfico de Línea: Evolución Consumo
            df_line = df.groupby(df['FECHA_DT_tel'].dt.strftime('%Y-%m')).agg({'Consumo c/ 100km TELEMETRIA':'mean'}).reset_index()
            fig_line = px.line(df_line, x='FECHA_DT_tel', y='Consumo c/ 100km TELEMETRIA', 
                               title="Consumo por Año y Mes", markers=True, template="plotly_dark")
            fig_line.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=200)
            st.plotly_chart(fig_line, use_container_width=True)

        # FILA 2: RANKING Y TREEMAP
        st.divider()
        c_left, c_right = st.columns(2)
        
        with c_left:
            st.subheader("Suma de LITROS por DOMINIO")
            fig_bar = px.bar(df.groupby('DOMINIO')['LITROS CONSUMIDOS'].sum().reset_index().sort_values('LITROS CONSUMIDOS'),
                             x='LITROS CONSUMIDOS', y='DOMINIO', orientation='h', 
                             color='LITROS CONSUMIDOS', color_continuous_scale='Blues', template="plotly_dark")
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        with c_right:
            st.subheader("Distribución de Consumo (Treemap)")
            fig_tree = px.treemap(df, path=['MARCA', 'DOMINIO'], values='Consumo c/ 100km TELEMETRIA',
                                  color='Consumo c/ 100km TELEMETRIA', color_continuous_scale='RdYlGn_r',
                                  template="plotly_dark")
            fig_tree.update_layout(paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_tree, use_container_width=True)

    else:
        st.info("Seleccioná la pestaña '⛽ Combustible' para ver el nuevo diseño.")

# 5. FOOTER
st.divider()
st.caption("Fleet Analytics Expreso Diemar | Estilo Reporte Gerencial")
