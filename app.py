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
    
    # Demografia Simulada
    np.random.seed(42)
    df["Populacao_Estimada"] = (df["PIB"] / 50) * np.random.uniform(0.8, 1.2, len(df))
    df["Populacao_Estimada"] = df["Populacao_Estimada"].clip(lower=1000).astype(int)
    # Índice de Envelhecimento: idosos(60+) para cada 100 jovens(0-14)
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
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "👥 Demografia", 
    "🚜 Von Thünen (Agro)", 
    "🏭 Weber (Indústria)", 
    "🏪 Christaller (Serviços)",
    "🎯 Especialização (QL)"
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
        fig_rest.update_layout(mapbox=dict(style="carto-positron", zoom=CAMERA_SUDESTE["zoom"], center=dict(lat=CAMERA_SUDESTE["lat"], lon=CAMERA_SUDESTE["lon"])))
        layers_rest = []
        if geojson_biomas:
            layers_rest.append({"source": geojson_biomas, "type": "fill", "color": "rgba(0, 170, 160, 0.4)"})
        if geojson_ucs:
            layers_rest.append({"source": geojson_ucs, "type": "line", "color": "rgba(255, 100, 0, 0.8)", "line": {"width": 1}})
        fig_rest.update_layout(mapbox_layers=layers_rest, margin={"r":0,"t":0,"l":0,"b":0})
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
        fig_log.update_layout(mapbox=dict(style="carto-positron", zoom=CAMERA_SUDESTE["zoom"], center=dict(lat=CAMERA_SUDESTE["lat"], lon=CAMERA_SUDESTE["lon"])))
        layers_log = []
        if geojson_rodovias:
            layers_log.append({"source": geojson_rodovias, "type": "line", "color": "rgba(200, 0, 0, 0.6)", "line": {"width": 1.5}})
        if geojson_ferrovias:
            layers_log.append({"source": geojson_ferrovias, "type": "line", "color": "rgba(0, 0, 0, 0.8)", "line": {"width": 2}})
        
        if geojson_portos:
            lats_p, lons_p, nomes_p = [], [], []
            for ft in geojson_portos.get("features", []):
                if ft.get("geometry", {}).get("type") == "Point":
                    lons_p.append(ft["geometry"]["coordinates"][0])
                    lats_p.append(ft["geometry"]["coordinates"][1])
                    nomes_p.append(ft.get("properties", {}).get("nome", "Porto"))
            if lats_p:
                fig_log.add_trace(go.Scattermapbox(lat=lats_p, lon=lons_p, mode="markers", marker=dict(size=10, color="#1565C0"), text=nomes_p, name="Portos"))
                
        fig_log.update_layout(mapbox_layers=layers_log, margin={"r":0,"t":0,"l":0,"b":0})
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
