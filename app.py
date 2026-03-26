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
    
    # --- LIMPIEZA EXTREMA ---
    for d in [df_tel, df_con]:
        # 1. Columnas sin tildes ni espacios
        d.columns = d.columns.str.strip().str.replace('í', 'i').str.replace('á', 'a')
        
        # 2. Patentes (DOMINIO): Todo a mayúsculas y sin espacios
        if 'DOMINIO' in d.columns:
            d['DOMINIO'] = d['DOMINIO'].astype(str).str.strip().str.upper().str.replace(' ', '')
        
        # 3. Fechas: Solo la parte del día
        if 'FECHA' in d.columns:
            d['FECHA'] = pd.to_datetime(d['FECHA'], errors='coerce').dt.date
            
    # Unimos (Merge)
    df = pd.merge(df_tel, df_con, on=["FECHA", "DOMINIO"])
    
    if not df.empty:
        df['g_co2_km'] = (df['Emisiones (KG CO2)'] / df['DISTANCIA RECORRIDA TELEMETRIA']) * 1000
    
    return df
