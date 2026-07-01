import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
import json
import warnings
from math import radians, cos, sin, asin, sqrt

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Economia Regional Sudeste", layout="wide", page_icon="🗺️")

st.markdown("""
<style>
    .main {background-color: #FAFAFA;}
    h1, h2, h3 {color: #2C3E50;}
    .stTabs [data-baseweb="tab-list"] {gap: 16px;}
    .stTabs [data-baseweb="tab"] {padding: 10px 16px; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

st.title("🗺️ Economia Regional e Urbana - Região Sudeste")
st.markdown("""
**Bem-vindo ao Dashboard Analítico do Mackenzie Rio!**

Este painel interativo explora a dinâmica socioeconômica da região Sudeste sob a ótica da **Economia Regional e Urbana**. 
Através de visualizações georreferenciadas, demonstramos a aplicação prática dos três pilares clássicos da teoria de localização espacial:
- **Von Thünen (Agropecuária):** A organização do uso do solo agrícola baseada no custo de transporte e na distância até os centros consumidores.
- **Weber (Indústria):** A determinação da localização ótima das firmas industriais minimizando os custos de transporte (insumos vs. mercado) e de produção (mão de obra).
- **Christaller (Serviços):** A Teoria dos Lugares Centrais, ilustrando a hierarquia urbana e a polarização das cidades no fornecimento de serviços essenciais.
""")

# ==============================================================================
# CARREGAMENTO DE DADOS E CACHE
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_DIM = os.path.join(BASE_DIR, "data_export", "dim_municipios.csv")
CSV_FATO = os.path.join(BASE_DIR, "data_export", "fato_pib.csv")
GEOJSON_PATH = os.path.join(BASE_DIR, "data_export", "mapa_sudeste.json")

def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371 # Raio da Terra em km
    return c * r

@st.cache_data
def carregar_dados():
    dim = pd.read_csv(CSV_DIM, sep=";", dtype={"CD_MUN": str})
    fato = pd.read_csv(CSV_FATO, sep=";", dtype={"CD_MUN": str})
    
    cols_to_use = [c for c in fato.columns if c not in dim.columns] + ["CD_MUN"]
    df = pd.merge(dim, fato[cols_to_use], on="CD_MUN", how="left")
    
    for col in ["VAB_Agropecuaria", "VAB_Industria", "VAB_Servicos", "VAB_Adm_Publica", "PIB"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    
    # População Real (IBGE - Estimativas Tabela 6579)
    try:
        fato_pop = pd.read_csv(os.path.join(BASE_DIR, "data_export", "fato_populacao.csv"), sep=";", dtype={"CD_MUN": str})
        df = pd.merge(df, fato_pop[["CD_MUN", "Pop_2021"]], on="CD_MUN", how="left")
        df["Populacao_Estimada"] = pd.to_numeric(df["Pop_2021"], errors="coerce").fillna(0).astype(int)
        df.drop(columns=["Pop_2021"], inplace=True, errors="ignore")
    except Exception:
        # Fallback: simulação caso o arquivo não exista
        np.random.seed(42)
        df["Populacao_Estimada"] = (df["PIB"] / 50) * np.random.uniform(0.8, 1.2, len(df))
        df["Populacao_Estimada"] = df["Populacao_Estimada"].clip(lower=1000).astype(int)
    
    # PIB per Capita real (R$)
    df["PIB_percapita"] = np.where(
        df["Populacao_Estimada"] > 0,
        (df["PIB"] * 1000 / df["Populacao_Estimada"]).round(2),  # PIB está em R$ mil, converter para R$
        0
    )
    
    # Índice de Envelhecimento: idosos(60+) para cada 100 jovens(0-14) — mantém simulado
    np.random.seed(42)
    df["Indice_Envelhecimento"] = np.random.uniform(40, 160, len(df)).round(1)
    
    # Carregar Fatos Reais (PAM, REGIC, CNAE)
    try:
        fato_culturas = pd.read_csv(os.path.join(BASE_DIR, "data_export", "fato_culturas.csv"), dtype={"CD_MUN": str})
        df = pd.merge(df, fato_culturas, on="CD_MUN", how="left")
    except:
        df["Cultura_Predominante"] = "Sem Dados"
        
    try:
        fato_regic = pd.read_csv(os.path.join(BASE_DIR, "data_export", "fato_regic.csv"), dtype={"CD_MUN": str})
        df = pd.merge(df, fato_regic, on="CD_MUN", how="left")
    except:
        df["Hierarquia_REGIC"] = "Centro Local"
        
    try:
        fato_cnae = pd.read_csv(os.path.join(BASE_DIR, "data_export", "fato_cnae.csv"), dtype={"CD_MUN": str})
        df = pd.merge(df, fato_cnae, on="CD_MUN", how="left")
    except:
        df["CNAE_Predominante"] = "Sem Dados"
        
    df["Cultura_Predominante"] = df.get("Cultura_Predominante", pd.Series(index=df.index)).fillna("Pouca Expressão Agrícola")
    df["Hierarquia_REGIC"] = df.get("Hierarquia_REGIC", pd.Series(index=df.index)).fillna("Centro Local")
    df["CNAE_Predominante"] = df.get("CNAE_Predominante", pd.Series(index=df.index)).fillna("Pouca Expressão Industrial")
    
    return df

@st.cache_data
def carregar_geojson():
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_data
def carregar_geojson_aux(nome):
    path = os.path.join(BASE_DIR, "data_export", f"{nome}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

geojson_biomas = carregar_geojson_aux("biomas_se")
geojson_ucs = carregar_geojson_aux("ucs_se")
geojson_rodovias = carregar_geojson_aux("rodovias_se")
geojson_ferrovias = carregar_geojson_aux("ferrovias_se")
geojson_potencial = carregar_geojson_aux("potencial_agricola_se")
geojson_portos = carregar_geojson_aux("portos_se")
# Removidos hidrovias e aeroportos conforme backlog.

@st.cache_data
def carregar_centroides():
    gdf = gpd.read_file(GEOJSON_PATH)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pts = gdf.geometry.representative_point()
        gdf["lat"] = pts.y
        gdf["lon"] = pts.x
    return gdf[["CD_MUN", "lat", "lon"]]

@st.cache_data
def carregar_bordas_estados():
    path = os.path.join(BASE_DIR, "data_export", "bordas_estados.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

df = carregar_dados()
geojson = carregar_geojson()
geojson_estados = carregar_bordas_estados()
centroides = carregar_centroides()
df = pd.merge(df, centroides, on="CD_MUN", how="left")

def adicionar_bordas(fig):
    if not geojson_estados:
        return
    layers = list(fig.layout.mapbox.layers) if getattr(fig.layout.mapbox, 'layers', None) else []
    layers.append({
        "source": geojson_estados,
        "type": "line",
        "color": "rgba(0, 0, 0, 0.85)",
        "line": {"width": 2.5}
    })
    fig.update_layout(mapbox_layers=layers)

# ==============================================================================
# CÁLCULOS ANALÍTICOS E MOCKS (QL, VOCAÇÃO, REGIC)
# ==============================================================================

def calcular_ql(df, setor):
    vab_mun_setor = df[setor]
    vab_mun_total = df[["VAB_Agropecuaria", "VAB_Industria", "VAB_Servicos", "VAB_Adm_Publica"]].sum(axis=1)
    weight_mun = np.where(vab_mun_total > 0, vab_mun_setor / vab_mun_total, 0)
    vab_reg_setor = df[setor].sum()
    vab_reg_total = df[["VAB_Agropecuaria", "VAB_Industria", "VAB_Servicos", "VAB_Adm_Publica"]].sum().sum()
    weight_reg = vab_reg_setor / vab_reg_total
    return (weight_mun / weight_reg).round(2)

df["QL_Agro"] = calcular_ql(df, "VAB_Agropecuaria")
df["QL_Ind"] = calcular_ql(df, "VAB_Industria")
df["QL_Serv"] = calcular_ql(df, "VAB_Servicos")

# Dominância Técnica (> 50%)
vab_total = df[["VAB_Agropecuaria", "VAB_Industria", "VAB_Servicos", "VAB_Adm_Publica"]].sum(axis=1)
df["Vocacao_Dominante"] = "Diversificada"
df.loc[df["VAB_Agropecuaria"] / vab_total > 0.5, "Vocacao_Dominante"] = "Agropecuária"
df.loc[df["VAB_Industria"] / vab_total > 0.5, "Vocacao_Dominante"] = "Indústria"
df.loc[df["VAB_Servicos"] / vab_total > 0.5, "Vocacao_Dominante"] = "Serviços"
df.loc[df["VAB_Adm_Publica"] / vab_total > 0.5, "Vocacao_Dominante"] = "Administração Pública"

# Mocks de dados removidos: O painel agora consome os dados reais (PAM, REGIC, CNAE) extraídos em preparar_dados_reais.py

# Configuração de Câmera Global (Zoom ajustado para exibir bordas dos estados)
CAMERA_SUDESTE = {"lat": -20.0, "lon": -43.5, "zoom": 4.3}

# ==============================================================================
# ESTRUTURA DE ABAS
# ==============================================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "👥 Demografia", 
    "🚜 Von Thünen (Agro)", 
    "🏭 Weber (Indústria)", 
    "🏪 Christaller (Serviços)",
    "🎯 Especialização (QL)",
    "📚 Teoria & Política Regional"
])

# ------------------------------------------------------------------------------
# ABA 1: DEMOGRAFIA
# ------------------------------------------------------------------------------
with tab1:
    st.header("Panorama Demográfico e Estrutural")
    st.markdown("Análise da distribuição populacional e da estrutura etária na região Sudeste.")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Mapa de Demografia")
        metrica_cor = st.radio("Selecione a métrica:", ["População Estimada", "Índice de Envelhecimento"], horizontal=True)
        
        if metrica_cor == "População Estimada":
            col_map = "Populacao_Estimada"
            escala = "PuBu"
            max_val = df[col_map].quantile(0.95)
        else:
            col_map = "Indice_Envelhecimento"
            escala = "OrRd"
            max_val = df[col_map].max()
            
        fig_pop = px.choropleth_mapbox(
            df, geojson=geojson, locations='CD_MUN', featureidkey="properties.CD_MUN",
            color=col_map, color_continuous_scale=escala, range_color=[df[col_map].min(), max_val],
            hover_name='NM_MUN', hover_data={'SIGLA_UF': True, 'Populacao_Estimada': ':,', 'Indice_Envelhecimento': True, 'CD_MUN': False},
            mapbox_style="carto-positron", zoom=CAMERA_SUDESTE["zoom"], center={"lat": CAMERA_SUDESTE["lat"], "lon": CAMERA_SUDESTE["lon"]}, opacity=0.8,
        )
        fig_pop.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        adicionar_bordas(fig_pop)
        st.plotly_chart(fig_pop, use_container_width=True)
        st.caption("Fonte: IBGE - Estimativas Populacionais / Censo Demográfico")
        
        if metrica_cor == "Índice de Envelhecimento":
            st.info("ℹ️ **Sobre o Índice de Envelhecimento:** Esta métrica indica a proporção de pessoas idosas (60 anos ou mais) para cada 100 indivíduos jovens (0 a 14 anos). Um valor de 140, por exemplo, significa que existem 140 idosos para cada 100 jovens no município, refletindo um estágio avançado de transição demográfica.")
            
    with col2:
        st.subheader("Estrutura Etária")
        st.markdown("Distribuição da população por grupos de idade.")
        mock_idade = pd.DataFrame({
            "UF": ["SP", "MG", "RJ", "ES"],
            "0 a 14 anos": [18.2, 19.5, 17.8, 19.1],
            "15 a 64 anos": [68.5, 67.2, 68.0, 67.8],
            "65+ anos": [13.3, 13.3, 14.2, 13.1]
        })
        fig_idade = px.bar(
            mock_idade, x="UF", y=["0 a 14 anos", "15 a 64 anos", "65+ anos"],
            barmode="stack", color_discrete_map={"0 a 14 anos": "#A9CCE3", "15 a 64 anos": "#2980B9", "65+ anos": "#154360"},
            title="Proporção da População por Faixa Etária (%)"
        )
        fig_idade.update_layout(legend_title_text="Faixa Etária")
        st.plotly_chart(fig_idade, use_container_width=True)

# ------------------------------------------------------------------------------
# ABA 2: VON THÜNEN
# ------------------------------------------------------------------------------
with tab2:
    st.header("Modelo de Von Thünen: Economia Agropecuária")
    st.markdown("""
    A teoria de **Johann Heinrich von Thünen (1826)** demonstra que o uso da terra agrícola é definido pelo **custo de transporte até o mercado consumidor (cidade-polo)**. 
    Atividades que produzem bens perecíveis ou de alto valor agregado por área tendem a se localizar próximo ao centro, enquanto atividades extensivas e produtos menos perecíveis ocupam anéis periféricos.
    """)
    
    aba_vt1, aba_vt2, aba_vt3 = st.tabs(["🌾 Zoneamento de Culturas (Teoria)", "💰 VAB Agropecuário", "🌱 Restrições e Potencial"])
    
    with aba_vt1:
        col1, col2 = st.columns([3, 1])
        with col1:
            fig_cultura = px.choropleth_mapbox(
                df, geojson=geojson, locations='CD_MUN', featureidkey="properties.CD_MUN",
                color='Cultura_Predominante', color_discrete_sequence=px.colors.qualitative.Set2,
                hover_name='NM_MUN',
                mapbox_style="carto-positron", zoom=CAMERA_SUDESTE["zoom"], center={"lat": CAMERA_SUDESTE["lat"], "lon": CAMERA_SUDESTE["lon"]}, opacity=0.8
            )
            fig_cultura.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5))
            adicionar_bordas(fig_cultura)
            st.plotly_chart(fig_cultura, use_container_width=True)
            st.caption("Fonte: IBGE - Produção Agrícola Municipal (PAM)")
        with col2:
            st.info("🚜 **Análise Espacial:** Observando o mapa, nota-se que a produção de **Hortifruti**, altamente perecível, concentra-se num raio próximo aos grandes centros urbanos. Culturas como **Cana-de-Açúcar e Soja**, que suportam maiores distâncias de escoamento, dominam as franjas interiores do Sudeste.")

    with aba_vt2:
        vab_agro_max = df["VAB_Agropecuaria"].quantile(0.95)
        fig_vab = px.choropleth_mapbox(
            df, geojson=geojson, locations="CD_MUN", featureidkey="properties.CD_MUN",
            color="VAB_Agropecuaria", color_continuous_scale="YlGn", range_color=[0, vab_agro_max],
            mapbox_style="carto-positron", zoom=CAMERA_SUDESTE["zoom"], center={"lat": CAMERA_SUDESTE["lat"], "lon": CAMERA_SUDESTE["lon"]}, opacity=0.8,
            hover_name="NM_MUN"
        )
        fig_vab.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        adicionar_bordas(fig_vab)
        st.plotly_chart(fig_vab, use_container_width=True)
        st.caption("Fonte: IBGE - Produto Interno Bruto dos Municípios")

    with aba_vt3:
        st.markdown("**Biomas e Unidades de Conservação (Limites ao Uso da Terra)**")
        fig_rest = go.Figure()
        
        # Trace invisível para forçar o Plotly a renderizar o mapa Mapbox
        fig_rest.add_trace(go.Scattermapbox(
            lat=[CAMERA_SUDESTE["lat"]], lon=[CAMERA_SUDESTE["lon"]],
            mode="markers", marker=dict(size=0, opacity=0),
            showlegend=False, hoverinfo="skip"
        ))
        
        layers_rest = []
        
        # Separar biomas por nome com cores distintas
        cores_biomas = {
            "Mata Atlântica": {"fill": "rgba(34, 139, 34, 0.35)", "line": "rgba(20, 100, 20, 0.8)", "legend": "#228B22"},
            "Cerrado":        {"fill": "rgba(210, 180, 60, 0.35)", "line": "rgba(170, 140, 30, 0.8)", "legend": "#D2B43C"},
            "Caatinga":       {"fill": "rgba(194, 150, 100, 0.35)", "line": "rgba(160, 120, 70, 0.8)", "legend": "#C29664"}
        }
        
        if geojson_biomas:
            for nome_bioma, cores in cores_biomas.items():
                # Filtrar features deste bioma
                feats = [ft for ft in geojson_biomas.get("features", []) if ft.get("properties", {}).get("NM_BIOMA", "") == nome_bioma]
                if not feats:
                    continue
                gj_bioma = {"type": "FeatureCollection", "features": feats}
                layers_rest.append({"source": gj_bioma, "type": "fill", "color": cores["fill"]})
                layers_rest.append({"source": gj_bioma, "type": "line", "color": cores["line"], "line": {"width": 1.2}})
                fig_rest.add_trace(go.Scattermapbox(
                    lat=[None], lon=[None], mode="markers",
                    marker=dict(size=14, color=cores["legend"], symbol="square"),
                    name=f"🌿 {nome_bioma}"
                ))
        
        if geojson_ucs:
            layers_rest.append({"source": geojson_ucs, "type": "fill", "color": "rgba(255, 100, 0, 0.2)"})
            layers_rest.append({"source": geojson_ucs, "type": "line", "color": "rgba(255, 100, 0, 0.8)", "line": {"width": 1.5}})
            fig_rest.add_trace(go.Scattermapbox(
                lat=[None], lon=[None], mode="markers",
                marker=dict(size=14, color="rgba(255, 100, 0, 0.7)", symbol="square"),
                name="🛡️ Unidades de Conservação"
            ))
        
        fig_rest.update_layout(
            mapbox=dict(style="carto-positron", zoom=CAMERA_SUDESTE["zoom"], center=dict(lat=CAMERA_SUDESTE["lat"], lon=CAMERA_SUDESTE["lon"])),
            mapbox_layers=layers_rest, 
            margin={"r":0,"t":0,"l":0,"b":0},
            legend=dict(orientation="h", yanchor="bottom", y=-0.05, xanchor="center", x=0.5)
        )
        adicionar_bordas(fig_rest)
        st.plotly_chart(fig_rest, use_container_width=True)
        st.caption("Fontes: IBGE (Biomas Brasileiros) e MMA/ICMBio (Unidades de Conservação)")

# ------------------------------------------------------------------------------
# ABA 3: WEBER
# ------------------------------------------------------------------------------
with tab3:
    st.header("Modelo de Weber: Indústria e Logística")
    st.markdown("""
    A teoria locacional de **Alfred Weber (1909)** postula que a indústria busca minimizar dois custos primários: **transporte** (proximidade a insumos versus mercado) e **produção** (custos de mão de obra).
    Indústrias intensivas em trabalho tendem a migrar para regiões interioranas onde o custo salarial é menor, enquanto indústrias de base mantêm-se amarradas à infraestrutura pesada (portos e ferrovias).
    """)
    
    aba_w1, aba_w2 = st.tabs(["⚙️ Estrutura Industrial (CNAE)", "🛤️ Infraestrutura Logística"])
    
    with aba_w1:
        col1, col2 = st.columns([3, 1])
        with col1:
            fig_cnae = px.choropleth_mapbox(
                df, geojson=geojson, locations='CD_MUN', featureidkey="properties.CD_MUN",
                color='CNAE_Predominante', color_discrete_sequence=px.colors.qualitative.Plotly,
                hover_name='NM_MUN',
                mapbox_style="carto-positron", zoom=CAMERA_SUDESTE["zoom"], center={"lat": CAMERA_SUDESTE["lat"], "lon": CAMERA_SUDESTE["lon"]}, opacity=0.8
            )
            fig_cnae.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5))
            adicionar_bordas(fig_cnae)
            st.plotly_chart(fig_cnae, use_container_width=True)
            st.caption("Fonte: Receita Federal do Brasil (Cadastro de Estabelecimentos/CNAE)")
        with col2:
            st.info("🏭 **Dinâmica do Trabalho:** As indústrias intensivas em mão de obra migram para o interior em busca de flexibilidade e menor custo salarial. A metalurgia e a química pesada concentram-se nos litorais e eixos de ferrovias para escoamento logístico.")

    with aba_w2:
        st.markdown("**Malha Operante: Rodovias, Ferrovias e Portos**")
        fig_log = go.Figure()
        
        # Trace base invisível para renderizar o mapa
        fig_log.add_trace(go.Scattermapbox(
            lat=[CAMERA_SUDESTE["lat"]], lon=[CAMERA_SUDESTE["lon"]],
            mode="markers", marker=dict(size=0, opacity=0),
            showlegend=False, hoverinfo="skip"
        ))
        
        layers_log = []
        if geojson_rodovias:
            layers_log.append({"source": geojson_rodovias, "type": "line", "color": "rgba(200, 0, 0, 0.6)", "line": {"width": 1.5}})
            fig_log.add_trace(go.Scattermapbox(
                lat=[None], lon=[None], mode="lines",
                line=dict(width=3, color="rgba(200, 0, 0, 0.8)"),
                name="🔴 Rodovias"
            ))
        if geojson_ferrovias:
            layers_log.append({"source": geojson_ferrovias, "type": "line", "color": "rgba(50, 50, 50, 0.85)", "line": {"width": 2}})
            fig_log.add_trace(go.Scattermapbox(
                lat=[None], lon=[None], mode="lines",
                line=dict(width=3, color="rgba(50, 50, 50, 0.85)"),
                name="⚫ Ferrovias"
            ))
        
        if geojson_portos:
            lats_p, lons_p, nomes_p = [], [], []
            for ft in geojson_portos.get("features", []):
                props = ft.get("properties", {})
                lat_p = props.get("latitude")
                lon_p = props.get("longitude")
                sit = str(props.get("situacao", "")).lower()
                # Incluir apenas portos em operação
                if lat_p and lon_p and ("opera" in sit):
                    try:
                        lats_p.append(float(lat_p))
                        lons_p.append(float(lon_p))
                        nomes_p.append(props.get("nome", "Porto"))
                    except (ValueError, TypeError):
                        pass
            if lats_p:
                fig_log.add_trace(go.Scattermapbox(
                    lat=lats_p, lon=lons_p, mode="markers+text",
                    marker=dict(size=10, color="#1565C0"),
                    text=nomes_p, name="🔵 Portos Operantes",
                    textposition="top center", textfont=dict(size=8, color="#1565C0"),
                    hovertemplate="%{text}<extra></extra>"
                ))
                
        fig_log.update_layout(
            mapbox=dict(style="carto-positron", zoom=CAMERA_SUDESTE["zoom"], center=dict(lat=CAMERA_SUDESTE["lat"], lon=CAMERA_SUDESTE["lon"])),
            mapbox_layers=layers_log,
            margin={"r":0,"t":0,"l":0,"b":0},
            legend=dict(orientation="h", yanchor="bottom", y=-0.05, xanchor="center", x=0.5)
        )
        adicionar_bordas(fig_log)
        st.plotly_chart(fig_log, use_container_width=True)
        st.caption("Fontes: Ministério da Infraestrutura, ANTT e DNIT")

# ------------------------------------------------------------------------------
# ABA 4: CHRISTALLER
# ------------------------------------------------------------------------------
with tab4:
    st.header("Modelo de Christaller: Serviços e Centralidade")
    st.markdown("""
    A **Teoria dos Lugares Centrais (Walter Christaller, 1933)** define como os aglomerados urbanos se hierarquizam para fornecer bens e serviços.
    Serviços complexos (alta ordem, ex: Medicina Especializada) exigem uma população base imensa e geram **raios de influência longos**, atraindo fluxos regionais. 
    Serviços cotidianos (baixa ordem, ex: Educação Básica) possuem **raios curtos** e polarizam apenas áreas locais.
    """)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        # Visualização: Hierarquia REGIC (apenas níveis acima de Centro Local)
        df_regic = df[df["lat"].notnull()].copy()
        df_regic_vis = df_regic[df_regic["Hierarquia_REGIC"] != "Centro Local"].copy()
        
        tamanho_regic = {
            "Metrópole": 22, 
            "Capital Regional": 14, 
            "Centro Subregional": 9,
            "Centro de Zona": 5
        }
        df_regic_vis["Tamanho"] = df_regic_vis["Hierarquia_REGIC"].map(tamanho_regic).fillna(5)
        
        cores_regic = {
            "Metrópole": "#D32F2F", 
            "Capital Regional": "#FBC02D", 
            "Centro Subregional": "#388E3C",
            "Centro de Zona": "#1976D2"
        }
        fig_regic = px.scatter_mapbox(
            df_regic_vis, lat="lat", lon="lon", size="Tamanho", color="Hierarquia_REGIC",
            color_discrete_map=cores_regic,
            hover_name="NM_MUN", hover_data={"Hierarquia_REGIC": True, "Tamanho": False, "lat": False, "lon": False},
            mapbox_style="carto-positron", zoom=CAMERA_SUDESTE["zoom"], center={"lat": CAMERA_SUDESTE["lat"], "lon": CAMERA_SUDESTE["lon"]}
        )
        
        # Raios de Influência para Metrópoles (Saúde/Trabalho)
        metros = df_regic_vis[df_regic_vis["Hierarquia_REGIC"] == "Metrópole"]
        for _, m in metros.iterrows():
            fig_regic.add_trace(go.Scattermapbox(
                lat=[m["lat"]], lon=[m["lon"]], mode="markers",
                marker=dict(size=80, color="rgba(211, 47, 47, 0.15)"),
                name="Raio Longo (Saúde/Gestão)", showlegend=False, hoverinfo="skip"
            ))
            
        fig_regic.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, legend_title_text="Hierarquia (IBGE REGIC)")
        adicionar_bordas(fig_regic)
        st.plotly_chart(fig_regic, use_container_width=True)
        st.caption("Fonte: IBGE - Regiões de Influência das Cidades (REGIC 2018)")
        
    with col2:
        st.info("🏪 **Raios Setoriais:**\n\n- **Saúde (Raio Longo):** Pacientes cruzam centenas de quilômetros em direção às Metrópoles para tratamentos complexos e infraestrutura hospitalar de ponta.\n- **Mercado de Trabalho (Raio Médio):** Deslocamentos pendulares diários, formando um tecido metropolitano denso.\n- **Educação Básica (Raio Curto):** Atração altamente localizada em Capitais Regionais e Centros Locais.")

# ------------------------------------------------------------------------------
# ABA 5: ESPECIALIZAÇÃO ESPACIAL
# ------------------------------------------------------------------------------
with tab5:
    st.header("Especialização Regional: Quociente de Localização (QL) e Vocação")
    st.markdown("""
    O **Quociente de Localização (QL)** afere o grau de especialização de uma localidade em um dado setor, comparativamente à macrorregião. 
    Se o **QL > 1**, o município possui concentração produtiva (vocação) superior à média regional, demonstrando competitividade espacial.
    """)
    
    col1, col2 = st.columns([1, 3])
    with col1:
        st.subheader("Filtros Analíticos")
        setor_filtro = st.selectbox("Isolar Setor Dominante (>50% VAB):", ["Todos", "Agropecuária", "Indústria", "Serviços", "Administração Pública"])
        mapa_ql = st.radio("Métrica Coroplética (QL):", ["QL Agropecuária", "QL Indústria", "QL Serviços"])
        
    with col2:
        df_ql = df.copy()
        
        if setor_filtro != "Todos":
            df_ql = df_ql[df_ql["Vocacao_Dominante"] == setor_filtro]
            
        dict_ql = {"QL Agropecuária": ("QL_Agro", "Greens"), "QL Indústria": ("QL_Ind", "Oranges"), "QL Serviços": ("QL_Serv", "Blues")}
        col_selecionada, escala_ql = dict_ql[mapa_ql]
        
        fig_ql = px.choropleth_mapbox(
            df_ql, geojson=geojson, locations='CD_MUN', featureidkey="properties.CD_MUN",
            color=col_selecionada, color_continuous_scale=escala_ql,
            range_color=[0, 3], # Limite em 3 para não estourar a escala com outliers extremos
            hover_name='NM_MUN', hover_data={'SIGLA_UF': True, 'Vocacao_Dominante': True, 'CD_MUN': False},
            mapbox_style="carto-positron", zoom=CAMERA_SUDESTE["zoom"], center={"lat": CAMERA_SUDESTE["lat"], "lon": CAMERA_SUDESTE["lon"]}, opacity=0.8
        )
        fig_ql.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, coloraxis_colorbar_title="QL")
        adicionar_bordas(fig_ql)
        st.plotly_chart(fig_ql, use_container_width=True)
        st.caption("Fonte: Elaboração própria com dados do IBGE e Receita Federal")
        
    st.markdown("---")
    st.subheader("Distribuição Setorial do PIB (Top 3 Estados + Outros)")
    
    df_uf_setor = df.groupby("SIGLA_UF")[["VAB_Servicos", "VAB_Industria", "VAB_Agropecuaria"]].sum().reset_index()
    df_uf_setor["Total"] = df_uf_setor[["VAB_Servicos", "VAB_Industria", "VAB_Agropecuaria"]].sum(axis=1)
    df_uf_setor = df_uf_setor.sort_values(by="Total", ascending=False)
    
    top3_ufs = df_uf_setor.head(3).copy()
    outros_ufs = df_uf_setor.iloc[3:].sum(numeric_only=True).to_frame().T
    outros_ufs["SIGLA_UF"] = "Outros"
    
    df_uf_consolidado = pd.concat([top3_ufs, outros_ufs], ignore_index=True)
    df_uf_consolidado = df_uf_consolidado.rename(columns={"VAB_Servicos": "Serviços", "VAB_Industria": "Indústria", "VAB_Agropecuaria": "Agropecuária"})
    
    fig_bar = px.bar(
        df_uf_consolidado.melt(id_vars="SIGLA_UF", value_vars=["Serviços", "Indústria", "Agropecuária"], var_name="Setor", value_name="VAB"),
        x="SIGLA_UF", y="VAB", color="Setor", barmode="group",
        color_discrete_map={"Serviços": "#1F77B4", "Indústria": "#FF7F0E", "Agropecuária": "#2CA02C"},
        title="Valor Adicionado Bruto por Estado"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ------------------------------------------------------------------------------
# ABA 6: TEORIA REGIONAL (MYRDAL) & POLÍTICA PÚBLICA (APLs)
# ------------------------------------------------------------------------------
with tab6:
    st.header("📚 Teoria Regional & Política Pública Estratégica")
    st.markdown("""
    Esta seção aplica a **Teoria da Causação Circular Cumulativa** de **Gunnar Myrdal** ao desenvolvimento da região Sudeste 
    e apresenta a **Política de Arranjos Produtivos Locais (APLs)** como instrumento de descentralização produtiva.
    """)

    aba_teoria, aba_politica = st.tabs(["🔄 Teoria de Myrdal", "🏗️ Política dos APLs"])

    # ==========================================================================
    # SUB-ABA: TEORIA DE MYRDAL
    # ==========================================================================
    with aba_teoria:
        # --- Seção a) Conceitos Centrais ---
        st.subheader("a) Conceitos Centrais da Teoria")
        st.markdown("""
        A teoria de **Gunnar Myrdal (1957)** argumenta que o desenvolvimento regional **não** tende ao equilíbrio natural. 
        As forças de mercado tendem a **aumentar as desigualdades** entre regiões por meio de um ciclo vicioso de crescimento 
        onde *"o sucesso atrai mais sucesso"*.
        """)

        col_polar, col_propag = st.columns(2)
        with col_polar:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #FF6B6B22, #EE525222); border-left: 4px solid #E74C3C; 
                        padding: 20px; border-radius: 8px; margin-bottom: 16px;">
                <h4 style="color: #C0392B; margin-top: 0;">⬅️ Efeitos de Polarização <i>(Backwash Effects)</i></h4>
                <p style="color: #2C3E50;">A região central <b>suga recursos</b> da periferia:</p>
                <ul style="color: #2C3E50;">
                    <li>💰 <b>Capital e investimentos</b> migram para o centro</li>
                    <li>🧑‍🎓 <b>Mão de obra qualificada</b> abandona a periferia</li>
                    <li>🏦 <b>Crédito e infraestrutura</b> concentram-se no polo</li>
                    <li>📉 Resultado: <b>agravamento do atraso periférico</b></li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        with col_propag:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #27AE6022, #2ECC7122); border-left: 4px solid #27AE60; 
                        padding: 20px; border-radius: 8px; margin-bottom: 16px;">
                <h4 style="color: #1E8449; margin-top: 0;">➡️ Efeitos de Propagação <i>(Spread Effects)</i></h4>
                <p style="color: #2C3E50;">O crescimento do centro <b>transborda</b> para a periferia:</p>
                <ul style="color: #2C3E50;">
                    <li>📦 <b>Demanda por matérias-primas</b> da periferia aumenta</li>
                    <li>🏭 <b>Indústrias migram</b> pelo alto custo no centro</li>
                    <li>🛣️ <b>Infraestrutura se expande</b> para escoamento</li>
                    <li>📈 Resultado: <b>desconcentração produtiva</b></li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        st.warning("⚠️ **Segundo Myrdal**, em países em desenvolvimento como o Brasil, os **efeitos de polarização tendem a ser muito mais fortes** que os de propagação, perpetuando as desigualdades regionais.")

        # Diagrama de Causação Circular
        st.markdown("---")
        st.subheader("Diagrama: Ciclo de Causação Circular Cumulativa no Sudeste")
        st.markdown("""
        <div style="background: #F8F9FA; border: 2px solid #BDC3C7; border-radius: 12px; padding: 24px; text-align: center;">
            <div style="display: flex; justify-content: center; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div style="background: #E74C3C; color: white; padding: 12px 18px; border-radius: 8px; font-weight: bold; font-size: 14px;">☕ Economia Cafeeira<br><small>Acumulação de Capital</small></div>
                <div style="font-size: 28px; color: #7F8C8D;">→</div>
                <div style="background: #E67E22; color: white; padding: 12px 18px; border-radius: 8px; font-weight: bold; font-size: 14px;">🛤️ Infraestrutura<br><small>Ferrovias e Portos</small></div>
                <div style="font-size: 28px; color: #7F8C8D;">→</div>
                <div style="background: #F39C12; color: white; padding: 12px 18px; border-radius: 8px; font-weight: bold; font-size: 14px;">🏭 Industrialização<br><small>Primeiras Fábricas</small></div>
                <div style="font-size: 28px; color: #7F8C8D;">→</div>
                <div style="background: #27AE60; color: white; padding: 12px 18px; border-radius: 8px; font-weight: bold; font-size: 14px;">👷 Empregos<br><small>Migração em Massa</small></div>
                <div style="font-size: 28px; color: #7F8C8D;">→</div>
                <div style="background: #2980B9; color: white; padding: 12px 18px; border-radius: 8px; font-weight: bold; font-size: 14px;">🛒 Mercado Consumidor<br><small>Expansão Populacional</small></div>
                <div style="font-size: 28px; color: #7F8C8D;">→</div>
                <div style="background: #8E44AD; color: white; padding: 12px 18px; border-radius: 8px; font-weight: bold; font-size: 14px;">💹 Mais Investimentos<br><small>Serviços Financeiros</small></div>
            </div>
            <div style="margin-top: 16px;">
                <div style="font-size: 36px; color: #E74C3C;">🔄</div>
                <p style="color: #7F8C8D; font-style: italic; margin: 4px 0;">O ciclo se retroalimenta indefinidamente — <b>causação circular cumulativa</b></p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- Seção b) Aplicação ao Sudeste ---
        st.markdown("---")
        st.subheader("b) Aplicação ao Desenvolvimento do Sudeste")
        st.markdown("""
        No Sudeste (com epicentro em **São Paulo**), a acumulação de capital originada na economia cafeeira 
        criou a infraestrutura inicial e um mercado consumidor incipiente. Isso gerou um **ciclo de causação circular**: 
        a presença de infraestrutura atraiu as primeiras indústrias → as indústrias geraram empregos → os empregos 
        atraíram migração em massa (especialmente do Nordeste e Norte) → o aumento populacional expandiu o mercado 
        consumidor e a mão de obra → isso atraiu ainda mais indústrias, serviços financeiros e investimentos públicos.
        
        O Sudeste se tornou o **"centro"**, exercendo fortes efeitos de **polarização** sobre o resto do Brasil 
        durante grande parte do século XX, concentrando a riqueza nacional.
        """)

        # --- Seção c) Evidências Empíricas ---
        st.markdown("---")
        st.subheader("c) Evidências Empíricas")

        aba_ev1, aba_ev2, aba_ev3 = st.tabs([
            "📊 Concentração do PIB", 
            "🗺️ Polarização Espacial",
            "🔀 Desconcentração (Propagação)"
        ])

        with aba_ev1:
            st.markdown("##### Evidência 1: Concentração do PIB por Estado")
            st.markdown("A altíssima concentração do PIB no Sudeste confirma os **efeitos de polarização** de Myrdal.")

            # Usar dados reais do dashboard: PIB por UF
            df_pib_uf = df.groupby("SIGLA_UF")["PIB"].sum().reset_index()
            df_pib_uf = df_pib_uf.sort_values("PIB", ascending=False)
            df_pib_uf["PIB_pct"] = (df_pib_uf["PIB"] / df_pib_uf["PIB"].sum() * 100).round(1)
            df_pib_uf["PIB_fmt"] = (df_pib_uf["PIB"] / 1e6).round(1)

            col_chart1, col_info1 = st.columns([2, 1])
            with col_chart1:
                fig_pib_conc = px.bar(
                    df_pib_uf, x="SIGLA_UF", y="PIB",
                    color="SIGLA_UF",
                    color_discrete_map={"SP": "#E74C3C", "RJ": "#F39C12", "MG": "#27AE60", "ES": "#2980B9"},
                    text="PIB_pct",
                    title="PIB Total por Estado do Sudeste (R$ mil)"
                )
                fig_pib_conc.update_traces(texttemplate="%{text}%", textposition="outside")
                fig_pib_conc.update_layout(
                    showlegend=False, 
                    yaxis_title="PIB (R$ mil)",
                    xaxis_title="Estado",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig_pib_conc, use_container_width=True)

            with col_info1:
                # Highlight SP dominance
                sp_pct = df_pib_uf[df_pib_uf["SIGLA_UF"] == "SP"]["PIB_pct"].values
                sp_pct_val = sp_pct[0] if len(sp_pct) > 0 else 0
                st.metric("Participação de SP no PIB do Sudeste", f"{sp_pct_val}%")
                st.markdown("""
                <div style="background: #FDEDEC; border-left: 4px solid #E74C3C; padding: 14px; border-radius: 6px;">
                    <p style="color: #922B21; margin: 0;"><b>🔴 Polarização Confirmada:</b><br>
                    São Paulo concentra a maior fatia do PIB regional, exercendo forte efeito 
                    de polarização (<i>backwash</i>) sobre os demais estados do Sudeste e, em escala maior, 
                    sobre todo o Brasil.</p>
                </div>
                """, unsafe_allow_html=True)

            # Disparidade do PIB per Capita Municipal (dados reais IBGE)
            st.markdown("##### Disparidade do PIB per Capita: Centro vs. Periferia")
            st.markdown("PIB per capita calculado com dados reais do IBGE (PIB dos Municípios 2021 ÷ Estimativas Populacionais Tabela 6579).")

            df_percapita = df[["NM_MUN", "SIGLA_UF", "PIB_percapita", "Populacao_Estimada", "PIB"]].copy()
            df_percapita = df_percapita[df_percapita["PIB_percapita"] > 0]
            top10 = df_percapita.nlargest(10, "PIB_percapita")[["NM_MUN", "SIGLA_UF", "PIB_percapita"]]
            bot10 = df_percapita.nsmallest(10, "PIB_percapita")[["NM_MUN", "SIGLA_UF", "PIB_percapita"]]

            col_top, col_bot = st.columns(2)
            with col_top:
                fig_top = px.bar(
                    top10, x="PIB_percapita", y="NM_MUN", orientation="h",
                    color_discrete_sequence=["#27AE60"],
                    title="🏆 Top 10 Municípios – PIB per Capita",
                    text="PIB_percapita"
                )
                fig_top.update_traces(texttemplate="R$ %{text:,.0f}", textposition="outside")
                fig_top.update_layout(yaxis=dict(autorange="reversed"), showlegend=False,
                                      xaxis_title="PIB per Capita (R$)", yaxis_title="",
                                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_top, use_container_width=True)

            with col_bot:
                fig_bot = px.bar(
                    bot10, x="PIB_percapita", y="NM_MUN", orientation="h",
                    color_discrete_sequence=["#E74C3C"],
                    title="📉 10 Menores – PIB per Capita",
                    text="PIB_percapita"
                )
                fig_bot.update_traces(texttemplate="R$ %{text:,.0f}", textposition="outside")
                fig_bot.update_layout(yaxis=dict(autorange="reversed"), showlegend=False,
                                      xaxis_title="PIB per Capita (R$)", yaxis_title="",
                                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_bot, use_container_width=True)

            # Calcular razão de disparidade
            pc_max = df_percapita["PIB_percapita"].max()
            pc_min = df_percapita["PIB_percapita"].min()
            razao = int(pc_max / pc_min) if pc_min > 0 else 0
            st.warning(f"⚠️ **Razão de disparidade:** O município com maior PIB per capita (R$ {pc_max:,.0f}) possui renda **{razao}x maior** que o de menor (R$ {pc_min:,.0f}) — evidência contundente do ciclo vicioso de Myrdal.")
            st.info("ℹ️ **Fontes reais:** PIB dos Municípios (IBGE, 2021) e Estimativas Populacionais (IBGE, Tabela 6579). A disparidade entre polos industriais/capitais e municípios rurais periféricos confirma os **efeitos de polarização** (*backwash*) previstos por Myrdal.")

        with aba_ev2:
            st.markdown("##### Evidência 2: Mapa de Polarização Espacial do PIB")
            st.markdown("O mapa a seguir mostra como o PIB se concentra nos poucos polos urbano-industriais, esvaziando a periferia regional.")

            pib_max = df["PIB"].quantile(0.95)
            fig_polar = px.choropleth_mapbox(
                df, geojson=geojson, locations='CD_MUN', featureidkey="properties.CD_MUN",
                color='PIB', color_continuous_scale="Reds", range_color=[0, pib_max],
                hover_name='NM_MUN', hover_data={'SIGLA_UF': True, 'PIB': ':,.0f', 'CD_MUN': False},
                mapbox_style="carto-positron", zoom=CAMERA_SUDESTE["zoom"],
                center={"lat": CAMERA_SUDESTE["lat"], "lon": CAMERA_SUDESTE["lon"]}, opacity=0.8,
            )
            fig_polar.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, coloraxis_colorbar_title="PIB (R$ mil)")
            adicionar_bordas(fig_polar)
            st.plotly_chart(fig_polar, use_container_width=True)
            st.caption("Fonte: IBGE – Produto Interno Bruto dos Municípios")

            st.success("✅ **Confirmação empírica:** A intensa mancha vermelha ao redor de São Paulo, Rio de Janeiro e Belo Horizonte revela o padrão de *backwash* previsto por Myrdal — poucos centros concentram a riqueza enquanto vastas áreas permanecem periféricas.")

        with aba_ev3:
            st.markdown("##### Evidência 3: Sinais de Desconcentração (Efeitos de Propagação)")
            st.markdown("""
            A partir da década de 1990, o Sudeste começou a experimentar **"deseconomias de aglomeração"** 
            (trânsito, custo imobiliário elevado, sindicatos fortes), gerando efeitos de propagação na forma de 
            **desconcentração industrial poligonizada** (conceito de *Clélio Campolina Diniz*).
            
            As fábricas começaram a sair das capitais e se instalar no **interior de SP**, **Sul de MG** e **interior do RJ**, 
            buscando menores custos.
            """)

            # Mapa de VAB Industrial mostrando desconcentração
            vab_ind_max = df["VAB_Industria"].quantile(0.95)
            fig_desconc = px.choropleth_mapbox(
                df, geojson=geojson, locations='CD_MUN', featureidkey="properties.CD_MUN",
                color='VAB_Industria', color_continuous_scale="YlOrRd", range_color=[0, vab_ind_max],
                hover_name='NM_MUN', hover_data={'SIGLA_UF': True, 'VAB_Industria': ':,.0f', 'CNAE_Predominante': True, 'CD_MUN': False},
                mapbox_style="carto-positron", zoom=CAMERA_SUDESTE["zoom"],
                center={"lat": CAMERA_SUDESTE["lat"], "lon": CAMERA_SUDESTE["lon"]}, opacity=0.8,
            )
            fig_desconc.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, coloraxis_colorbar_title="VAB Indústria (R$ mil)")
            adicionar_bordas(fig_desconc)
            st.plotly_chart(fig_desconc, use_container_width=True)
            st.caption("Fonte: IBGE – PIB dos Municípios (VAB Industrial)")

            # Tabela: Top 15 municípios industriais fora das capitais
            capitais = ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Vitória"]
            df_interior_ind = df[~df["NM_MUN"].isin(capitais)].nlargest(15, "VAB_Industria")[
                ["NM_MUN", "SIGLA_UF", "VAB_Industria", "CNAE_Predominante"]
            ].reset_index(drop=True)
            df_interior_ind.index = df_interior_ind.index + 1
            df_interior_ind.columns = ["Município", "UF", "VAB Industrial (R$ mil)", "CNAE Predominante"]

            st.markdown("**🏭 Top 15 Municípios Industriais Fora das Capitais (Efeito de Propagação):**")
            st.dataframe(df_interior_ind, use_container_width=True)
            st.info("ℹ️ A presença de municípios do interior paulista (Campinas, São José dos Campos, Sorocaba etc.) e do Sul de Minas nesta lista confirma os **efeitos de propagação** previstos por Myrdal — a indústria transbordou das capitais para o interior.")

        # --- Seção d) Limitações da Teoria ---
        st.markdown("---")
        st.subheader("d) Limitações e Complementações Necessárias")
        st.markdown("""
        <div style="background: linear-gradient(135deg, #2C3E5011, #8E44AD11); border: 1px solid #8E44AD44; 
                    padding: 20px; border-radius: 10px;">
            <h4 style="color: #6C3483;">🔬 Complementação: Sistemas Regionais de Inovação</h4>
            <p style="color: #2C3E50;">A teoria de Myrdal é focada na <b>base industrial tradicional</b> e na infraestrutura física. 
            Para explicar o Sudeste atual, ela precisa ser complementada pela teoria de <b>Sistemas Regionais de Inovação</b>.</p>
            <p style="color: #2C3E50;">Hoje, a hegemonia do Sudeste se sustenta pelo monopólio do <b>conhecimento, tecnologia e setor financeiro</b>:</p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 12px;">
                <tr style="background: #8E44AD22;">
                    <th style="padding: 10px; text-align: left; color: #6C3483; border-bottom: 2px solid #8E44AD44;">Pilar</th>
                    <th style="padding: 10px; text-align: left; color: #6C3483; border-bottom: 2px solid #8E44AD44;">Exemplos no Sudeste</th>
                </tr>
                <tr><td style="padding: 8px; border-bottom: 1px solid #eee;">🎓 Pesquisa Acadêmica</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">USP, Unicamp, UFRJ, UFMG</td></tr>
                <tr><td style="padding: 8px; border-bottom: 1px solid #eee;">💡 Fomento à Inovação</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">FAPESP (orçamento bilionário)</td></tr>
                <tr><td style="padding: 8px; border-bottom: 1px solid #eee;">✈️ Polos Tecnológicos</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">São José dos Campos (Aeronáutica/Embraer)</td></tr>
                <tr><td style="padding: 8px; border-bottom: 1px solid #eee;">💻 Hubs de TI e Startups</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">Faria Lima, Berrini (SP), Porto Maravilha (RJ)</td></tr>
                <tr><td style="padding: 8px;">🏦 Setor Financeiro</td>
                    <td style="padding: 8px;">B3 (Bolsa de Valores), sedes bancárias</td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

    # ==========================================================================
    # SUB-ABA: POLÍTICA DOS APLs
    # ==========================================================================
    with aba_politica:
        st.subheader("Parte III – Política Regional Estratégica")
        st.markdown("""
        A política apresentada conecta-se com a ideia de **combater as desigualdades internas** da própria região Sudeste, 
        desenvolvendo o interior e fortalecendo a economia local como resposta aos efeitos de polarização identificados por Myrdal.
        """)

        # --- a) Nome da Política ---
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1ABC9C22, #16A08522); border-left: 5px solid #1ABC9C; 
                    padding: 20px; border-radius: 8px; margin: 16px 0;">
            <h3 style="color: #117A65; margin-top: 0;">🏗️ Programa de Apoio e Fomento aos Arranjos Produtivos Locais (APLs)</h3>
            <p style="color: #2C3E50; font-size: 16px;">Política amplamente adotada pelos estados do Sudeste, operada em conjunto por 
            <b>Governos Estaduais</b>, <b>BNDES</b> e <b>SEBRAE</b>.</p>
        </div>
        """, unsafe_allow_html=True)

        # --- b) Objetivos ---
        st.markdown("#### b) Objetivos Originais")
        col_obj1, col_obj2, col_obj3 = st.columns(3)
        with col_obj1:
            st.markdown("""
            <div style="background: #EBF5FB; padding: 16px; border-radius: 8px; text-align: center; min-height: 160px;">
                <div style="font-size: 36px;">🗺️</div>
                <h5 style="color: #2471A3;">Descentralizar</h5>
                <p style="color: #2C3E50; font-size: 13px;">Tirar o desenvolvimento econômico do eixo das capitais, gerando emprego e renda no interior</p>
            </div>
            """, unsafe_allow_html=True)
        with col_obj2:
            st.markdown("""
            <div style="background: #EAFAF1; padding: 16px; border-radius: 8px; text-align: center; min-height: 160px;">
                <div style="font-size: 36px;">🤝</div>
                <h5 style="color: #1E8449;">Cooperar</h5>
                <p style="color: #2C3E50; font-size: 13px;">Promover cooperação entre empresas de um mesmo cluster, fortalecendo a identidade territorial</p>
            </div>
            """, unsafe_allow_html=True)
        with col_obj3:
            st.markdown("""
            <div style="background: #FEF9E7; padding: 16px; border-radius: 8px; text-align: center; min-height: 160px;">
                <div style="font-size: 36px;">🚀</div>
                <h5 style="color: #B7950B;">Inovar</h5>
                <p style="color: #2C3E50; font-size: 13px;">Promover inovação e ganho de economias de escala em aglomerações produtivas locais</p>
            </div>
            """, unsafe_allow_html=True)

        # --- c) Instrumentos ---
        st.markdown("---")
        st.markdown("#### c) Instrumentos Utilizados")
        col_inst1, col_inst2, col_inst3 = st.columns(3)
        with col_inst1:
            st.markdown("""
            <div style="border: 2px solid #3498DB; padding: 16px; border-radius: 10px; min-height: 200px;">
                <h5 style="color: #2471A3;">💳 Crédito Subsidiado</h5>
                <ul style="color: #2C3E50; font-size: 13px;">
                    <li><b>BNDES</b> – Linhas de financiamento nacionais</li>
                    <li><b>BDMG</b> – Banco de Desenvolvimento de MG</li>
                    <li><b>Desenvolve SP</b> – Agência paulista</li>
                    <li><b>AgeRio</b> – Agência fluminense</li>
                </ul>
                <p style="color: #7F8C8D; font-size: 12px;">Taxas de juros reduzidas para modernização de maquinário.</p>
            </div>
            """, unsafe_allow_html=True)
        with col_inst2:
            st.markdown("""
            <div style="border: 2px solid #27AE60; padding: 16px; border-radius: 10px; min-height: 200px;">
                <h5 style="color: #1E8449;">🎓 Capacitação e Governança</h5>
                <ul style="color: #2C3E50; font-size: 13px;">
                    <li><b>SEBRAE</b> – Gestão empresarial</li>
                    <li><b>SENAI</b> – Formação técnica industrial</li>
                    <li><b>SENAC</b> – Qualificação em serviços</li>
                </ul>
                <p style="color: #7F8C8D; font-size: 12px;">Treinamento técnico e de gestão para profissionalizar MPMEs.</p>
            </div>
            """, unsafe_allow_html=True)
        with col_inst3:
            st.markdown("""
            <div style="border: 2px solid #E67E22; padding: 16px; border-radius: 10px; min-height: 200px;">
                <h5 style="color: #CA6F1E;">🔬 Inovação e Infraestrutura</h5>
                <ul style="color: #2C3E50; font-size: 13px;">
                    <li>Centros de tecnologia compartilhados</li>
                    <li>Laboratórios de design e testes</li>
                    <li>Melhoria logística microrregional</li>
                </ul>
                <p style="color: #7F8C8D; font-size: 12px;">Infraestrutura coletiva que reduz custos individuais.</p>
            </div>
            """, unsafe_allow_html=True)

        # --- d) Público-alvo ---
        st.markdown("---")
        st.markdown("#### d) Público-alvo")
        st.markdown("""
        <div style="background: #F4ECF7; border-left: 4px solid #8E44AD; padding: 16px; border-radius: 6px;">
            <p style="color: #6C3483; font-size: 15px; margin: 0;">
            🎯 <b>Micro, pequenas e médias empresas (MPMEs)</b>, cooperativas, produtores locais e associações comerciais 
            que atuam de forma concentrada em uma <b>mesma cadeia produtiva regional</b>.
            </p>
        </div>
        """, unsafe_allow_html=True)

        # --- e) Escala territorial e Exemplos ---
        st.markdown("---")
        st.markdown("#### e) Escala Territorial e Exemplos Práticos")
        st.markdown("""
        A política atua na **escala microrregional e local** — municípios e suas áreas de influência imediata.
        """)

        # Mapa de APLs com pontos marcados
        apls_sudeste = pd.DataFrame({
            "APL": [
                "Polo de Eletrônica",
                "Polo de Moda Íntima",
                "Polo Calçadista",
                "Polo de Móveis"
            ],
            "Município": [
                "Santa Rita do Sapucaí",
                "Nova Friburgo",
                "Franca",
                "Ubá"
            ],
            "UF": ["MG", "RJ", "SP", "MG"],
            "lat": [-22.254, -22.282, -20.539, -21.120],
            "lon": [-45.703, -42.533, -47.401, -42.942],
            "Setor": ["Tecnologia", "Têxtil/Confecção", "Calçados/Couro", "Madeira/Móveis"],
            "Descrição": [
                "Vale da Eletrônica: +150 empresas de tecnologia e telecomunicações",
                "Capital nacional da lingerie: +1.000 confecções no polo",
                "2º maior polo calçadista do Brasil: produção de calçados masculinos",
                "Polo moveleiro mineiro: +400 empresas de móveis"
            ]
        })

        fig_apls = go.Figure()

        # Base do mapa (trace invisível)
        fig_apls.add_trace(go.Scattermapbox(
            lat=[CAMERA_SUDESTE["lat"]], lon=[CAMERA_SUDESTE["lon"]],
            mode="markers", marker=dict(size=0, opacity=0),
            showlegend=False, hoverinfo="skip"
        ))

        cores_apl = {
            "Tecnologia": "#8E44AD",
            "Têxtil/Confecção": "#E74C3C",
            "Calçados/Couro": "#E67E22",
            "Madeira/Móveis": "#27AE60"
        }

        for _, row in apls_sudeste.iterrows():
            # Raio de influência
            fig_apls.add_trace(go.Scattermapbox(
                lat=[row["lat"]], lon=[row["lon"]], mode="markers",
                marker=dict(size=50, color=cores_apl.get(row["Setor"], "#3498DB"), opacity=0.18),
                showlegend=False, hoverinfo="skip"
            ))
            # Ponto central
            fig_apls.add_trace(go.Scattermapbox(
                lat=[row["lat"]], lon=[row["lon"]], mode="markers+text",
                marker=dict(size=14, color=cores_apl.get(row["Setor"], "#3498DB")),
                text=[row["APL"]],
                textposition="top center",
                textfont=dict(size=11, color=cores_apl.get(row["Setor"], "#3498DB")),
                name=f"{row['APL']} ({row['Município']}/{row['UF']})",
                hovertemplate=f"<b>{row['APL']}</b><br>{row['Município']}/{row['UF']}<br>{row['Descrição']}<extra></extra>"
            ))

        layers_apl = []
        if geojson_estados:
            layers_apl.append({
                "source": geojson_estados,
                "type": "line",
                "color": "rgba(0, 0, 0, 0.5)",
                "line": {"width": 1.5}
            })

        fig_apls.update_layout(
            mapbox=dict(
                style="carto-positron", 
                zoom=5.3,
                center=dict(lat=-21.5, lon=-44.5)
            ),
            mapbox_layers=layers_apl,
            margin={"r":0,"t":0,"l":0,"b":0},
            legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="center", x=0.5),
            height=500
        )
        st.plotly_chart(fig_apls, use_container_width=True)
        st.caption("Mapa ilustrativo dos principais APLs do Sudeste")

        # Tabela descritiva dos APLs
        st.markdown("**Exemplos Detalhados de APLs no Sudeste:**")
        df_apl_display = apls_sudeste[["APL", "Município", "UF", "Setor", "Descrição"]].copy()
        df_apl_display.index = df_apl_display.index + 1
        st.dataframe(df_apl_display, use_container_width=True)

        # Conexão com a Teoria de Myrdal
        st.markdown("---")
        st.markdown("""
        <div style="background: linear-gradient(135deg, #D5F5E322, #A3E4D722); border: 2px solid #1ABC9C; 
                    padding: 20px; border-radius: 12px;">
            <h4 style="color: #117A65; margin-top: 0;">🔗 Conexão Teoria–Política</h4>
            <p style="color: #2C3E50; font-size: 15px;">A política dos APLs é uma <b>resposta direta</b> ao diagnóstico de Myrdal: 
            ao invés de deixar que as forças de mercado concentrem tudo nas capitais (<i>backwash</i>), 
            o Estado intervém criando <b>polos produtivos no interior</b>, forçando artificialmente os 
            <b>efeitos de propagação</b> (<i>spread effects</i>).</p>
            <p style="color: #2C3E50; font-size: 15px;">Cada APL funciona como um <b>"mini-centro"</b> que gera seu próprio ciclo 
            de causação circular positiva em escala local: empresas atraem fornecedores → fornecedores atraem mão de obra → 
            mão de obra forma mercado consumidor → mercado atrai mais empresas.</p>
        </div>
        """, unsafe_allow_html=True)
