import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACION Y ESTETICA
st.set_page_config(page_title="Expreso Diemar - Carbon Tracker", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.9), rgba(0, 0, 0, 0.9)),
                    url("https://raw.githubusercontent.com/nicolascolonna23/HuellaCarbonoDM/main/IMG_3101.jpg");
        background-size: cover; background-attachment: fixed;
    }
    .stMetric { background-color: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 10px; border-top: 4px solid #2e7d32; }
    h1, h2, h3, h4, span, p { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. CARGA DE DATOS
@st.cache_data(ttl=60)
def get_clean_data():
    base_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR35NkYPtJrOrdYHLGUH7GIW93s5cPAqQ0zEk5fP1c3gvErwbUW7HJ2OeWBYaBVsYKVmCf0yhLvs6eG/pub?output=csv"

    # gid=882343299  -> Emisiones/Telemetria: CO2, RALENTI (FUENTE PRINCIPAL - tiene todos los meses)
    # gid=1044040871 -> Combustible/KMS: KMS, MARCA (puede no tener todos los meses)
    df_emi = pd.read_csv(f"{base_url}&gid=882343299")
    df_kms = pd.read_csv(f"{base_url}&gid=1044040871")

    def normalizar(df):
        df.columns = df.columns.str.strip().str.upper().str.replace('Í', 'I').str.replace('Á', 'A')
        mapeo = {}
        for col in df.columns:
            if "DOMINIO" in col:
                mapeo[col] = "DOMINIO"
            elif "FECHA" in col:
                mapeo[col] = "FECHA"
            elif "DISTANCIA" in col or col == "KMS" or ("KM" in col and "CO2" not in col and "L/100" not in col):
                mapeo[col] = "KMS"
            elif "EMISIONES" in col or "CO2" in col:
                mapeo[col] = "CO2"
            elif "RALENTI" in col:
                mapeo[col] = "RALENTI"
            elif "MARCA" in col:
                mapeo[col] = "MARCA"
        df = df.rename(columns=mapeo)
        for col_num in ["KMS", "CO2", "RALENTI"]:
            if col_num in df.columns:
                df[col_num] = pd.to_numeric(
                    df[col_num].astype(str)
                               .str.replace('.', '', regex=False)
                               .str.replace(',', '.', regex=False),
                    errors='coerce'
                ).fillna(0)
        return df

    df_emi = normalizar(df_emi)
    df_kms = normalizar(df_kms)

    # Crear MES y normalizar DOMINIO en ambas hojas
    for d in [df_emi, df_kms]:
        if 'DOMINIO' in d.columns:
            d['DOMINIO'] = d['DOMINIO'].astype(str).str.replace(' ', '').str.upper()
        if 'FECHA' in d.columns:
            d['FECHA_DT'] = pd.to_datetime(d['FECHA'], dayfirst=True, errors='coerce')
            d['MES'] = d['FECHA_DT'].dt.strftime('%Y-%m')

    # Tabla de lookup MARCA por DOMINIO (para completar meses sin datos KMS)
    if 'MARCA' in df_kms.columns and 'DOMINIO' in df_kms.columns:
        marca_lookup = (df_kms[['DOMINIO', 'MARCA']]
                        .dropna(subset=['MARCA'])
                        .drop_duplicates('DOMINIO', keep='last'))
    else:
        marca_lookup = pd.DataFrame(columns=['DOMINIO', 'MARCA'])

    # FIX MERGE: LEFT JOIN desde emisiones para NO perder meses que faltan en KMS
    # Asi febrero 2026 (que existe en emisiones pero no en KMS) aparece igual
    cols_kms = [c for c in ['DOMINIO', 'MES', 'KMS'] if c in df_kms.columns]
    df = pd.merge(df_emi, df_kms[cols_kms], on=["DOMINIO", "MES"], how='left', suffixes=('', '_DROP'))
    df = df.loc[:, ~df.columns.str.contains('_DROP')]

    # Completar MARCA con el lookup (para meses que no tienen datos KMS)
    if 'MARCA' not in df.columns:
        df = df.merge(marca_lookup, on='DOMINIO', how='left')
    elif df['MARCA'].isna().all():
        df = df.drop(columns=['MARCA']).merge(marca_lookup, on='DOMINIO', how='left')
    else:
        df = df.merge(marca_lookup.rename(columns={'MARCA': 'MARCA_FILL'}), on='DOMINIO', how='left')
        df['MARCA'] = df['MARCA'].fillna(df['MARCA_FILL'])
        df = df.drop(columns=['MARCA_FILL'], errors='ignore')

    # Rellenar KMS sin datos con 0
    if 'KMS' in df.columns:
        df['KMS'] = df['KMS'].fillna(0)

    return df

try:
    df_master = get_clean_data()
except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    st.stop()

# 3. SIDEBAR
with st.sidebar:
    st.image("https://raw.githubusercontent.com/nicolascolonna23/HuellaCarbonoDM/main/logo_diemar4.png", width=200)
    meses = sorted(df_master["MES"].unique().tolist(), reverse=True)
    mes_sel = st.selectbox("Periodo", meses)
    if "MARCA" in df_master.columns:
        marcas = ["Todas"] + sorted(df_master["MARCA"].dropna().unique().tolist())
        marca_sel = st.selectbox("Marca", marcas)
    else:
        marca_sel = "Todas"

# 4. FILTRAR
df_filtrado = df_master[df_master["MES"] == mes_sel].copy()
if marca_sel != "Todas" and "MARCA" in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado["MARCA"] == marca_sel]

# 5. DASHBOARD
st.title(f"Reporte Operativo - {mes_sel}")

if not df_filtrado.empty:
    v_co2 = df_filtrado['CO2'].sum() if 'CO2' in df_filtrado.columns else 0
    v_kms = df_filtrado['KMS'].sum() if 'KMS' in df_filtrado.columns else 0
    v_ral = df_filtrado['RALENTI'].sum() if 'RALENTI' in df_filtrado.columns else 0
    intensidad = (v_co2 / v_kms * 1000) if v_kms > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CO2 TOTAL", f"{v_co2:,.0f} kg")
    c2.metric("KM TOTALES", f"{v_kms:,.0f} km")
    c3.metric("INTENSIDAD", f"{intensidad:.1f} g/km")
    c4.metric("RALENTI", f"{v_ral:,.0f} L")

    st.divider()

    col_a, col_b = st.columns([1.5, 1])
    with col_a:
        st.subheader("Emisiones por Patente")
        if 'CO2' in df_filtrado.columns and 'DOMINIO' in df_filtrado.columns:
            chart_data = df_filtrado.groupby("DOMINIO")["CO2"].sum().reset_index()
            fig_bar = px.bar(chart_data, x="DOMINIO", y="CO2",
                             labels={"CO2": "CO2 (kg)", "DOMINIO": "Patente"},
                             color="CO2", color_continuous_scale="Greens")
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig_bar, use_container_width=True)
    with col_b:
        if 'MARCA' in df_filtrado.columns and 'CO2' in df_filtrado.columns:
            st.subheader("Distribucion por Marca")
            fig_pie = px.pie(df_filtrado, values='CO2', names='MARCA', hole=0.4)
            fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()
    st.subheader("Detalle de Unidades")
    cols_mostrar = [c for c in ['DOMINIO', 'MARCA', 'FECHA', 'KMS', 'CO2', 'RALENTI'] if c in df_filtrado.columns]
    st.dataframe(df_filtrado[cols_mostrar], use_container_width=True)
else:
    st.warning("No hay datos para el periodo y filtro seleccionados.")

st.caption("Sincronizacion automatica activa con Google Sheets.")
