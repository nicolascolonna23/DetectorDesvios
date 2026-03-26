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
    [data-testid="stSidebar"] { background-color: rgba(10, 15, 10, 0.98); }
    .stMetric {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 15px; border-radius: 10px; border-top: 4px solid #2e7d32;
    }
    h1, h2, h3, h4, span, p { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. CARGA Y CRUCE POR MES/AÑO/PATENTE
@st.cache_data(ttl=600)
def get_data():
    u1 = "https://expresodiemar-my.sharepoint.com/:x:/g/personal/nicolascolonna_expresodiemar_onmicrosoft_com/IQCCJG7r9T2JTb0eAdpQU1ggAcTn9ZELfjq58Xk9-eqj58o?download=1" # Telemetría
    u2 = "https://expresodiemar-my.sharepoint.com/:x:/g/personal/nicolascolonna_expresodiemar_onmicrosoft_com/IQAWlrsay0HVT622_ANLB-bWAfMlRi4IHHFMH6DJBzVW3BU?download=1" # Conducción (CO2/Ralentí)
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
            d['KEY_TIEMPO'] = d['FECHA_DT'].dt.strftime('%Y-%m') # Ejemplo: '2026-01'

    # UNIÓN: Solo si coinciden Patente Y Mes/Año
    df = pd.merge(df_tel, df_con, on=["DOMINIO", "KEY_TIEMPO"], suffixes=('_tel', '_con'))
    return df

try:
    df_master = get_data()
except Exception as e:
    st.error(f"❌ Error en el cruce: {e}"); st.stop()

# 3. SIDEBAR
with st.sidebar:
    st.image("logo_diemar4.png", use_container_width=True)
    st.divider()
    meses_cruzados = sorted(df_master["KEY_TIEMPO"].unique().tolist())
    mes_sel = st.selectbox("📅 Período de Análisis", meses_cruzados)
    marcas = ["Todas"] + sorted(df_master["MARCA"].unique().tolist())
    marca_sel = st.selectbox("🏭 Filtrar Marca", marcas)

# Lógica de comparación
df_actual = df_master[df_master["KEY_TIEMPO"] == mes_sel]
# Intentamos buscar el mes anterior en los datos cruzados
idx_actual = meses_cruzados.index(mes_sel)
df_previo = df_master[df_master["KEY_TIEMPO"] == meses_cruzados[idx_actual-1]] if idx_actual > 0 else pd.DataFrame()

if marca_sel != "Todas":
    df_actual = df_actual[df_actual["MARCA"] == marca_sel]
    df_previo = df_previo[df_previo["MARCA"] == marca_sel]

# 4. DASHBOARD DE EMISIONES
st.title(f"🌿 Centro de Sustentabilidad — {mes_sel}")

if df_actual.empty:
    st.warning("Sin datos para este período.")
else:
    # --- MÉTRICAS PRINCIPALES ---
    c1, c2, c3, c4 = st.columns(4)
    
    # CO2 e Incremento/Descenso
    co2_now = df_actual['Emisiones (KG CO2)'].sum()
    co2_prev = df_previo['Emisiones (KG CO2)'].sum() if not df_previo.empty else 0
    delta_co2 = ((co2_now - co2_prev) / co2_prev * 100) if co2_prev > 0 else 0
    c1.metric("CO₂ EMITIDO (MES)", f"{co2_now:,.0f} kg", 
              delta=f"{delta_co2:.1f}%" if co2_prev > 0 else None, delta_color="inverse")

    # Intensidad g/km
    kms = df_actual['DISTANCIA RECORRIDA TELEMETRIA'].sum()
    intensidad = (co2_now / kms * 1000) if kms > 0 else 0
    c2.metric("INTENSIDAD DE CARBONO", f"{intensidad:.1f} g/km", help="Gramos de CO2 por cada km recorrido.")

    # Ahorro Ralentí (2.68 kg CO2 por litro diésel)
    lts_ral = df_actual['Ralenti (Lts)'].sum()
    co2_evitable = lts_ral * 2.68
    c3.metric("CO₂ EVITABLE (RALENTÍ)", f"{co2_evitable:,.1f} kg", delta="Reducible", delta_color="off")

    # Árboles (Cálculo recuperado)
    arboles_necesarios = co2_now / 20
    c4.metric("COMPENSACIÓN", f"{int(arboles_necesarios)} Árboles", help="Árboles necesarios por 1 año para absorber este CO2.")

    st.divider()

    # --- GRÁFICOS ---
    col_l, col_r = st.columns([1.5, 1])

    with col_l:
        st.subheader("📊 Ranking de Emisiones por Patente")
        fig_bar = px.bar(df_actual.sort_values("Emisiones (KG CO2)", ascending=False), 
                         x="DOMINIO", y="Emisiones (KG CO2)", color="Emisiones (KG CO2)",
                         color_continuous_scale="Reds", template="plotly_dark")
        fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_r:
        st.subheader("📉 Distribución CO₂ por Marca")
        fig_pie = px.pie(df_actual, values='Emisiones (KG CO2)', names='MARCA', 
                         hole=0.4, color_discrete_sequence=px.colors.sequential.Greens_r)
        fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- TABLA DE DETALLE ---
    st.subheader("📋 Auditoría Ambiental de Flota")
    df_actual['g_CO2_km'] = (df_actual['Emisiones (KG CO2)'] / df_actual['DISTANCIA RECORRIDA TELEMETRIA']) * 1000
    st.dataframe(df_actual[['DOMINIO', 'MARCA', 'DISTANCIA RECORRIDA TELEMETRIA', 'Emisiones (KG CO2)', 'g_CO2_km']]
                 .sort_values('g_CO2_km', ascending=False), use_container_width=True)

# 5. FOOTER
st.divider()
st.caption("Fleet Carbon Analysis | Expreso Diemar | Datos cruzados por Mes/Año/Dominio")
