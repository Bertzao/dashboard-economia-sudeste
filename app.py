# -*- coding: utf-8 -*-
"""
============================================================================
STREAMLIT DASHBOARD: ECONOMIA REGIONAL E URBANA - SUDESTE DO BRASIL
============================================================================
Aplica os conceitos de Von Thünen, Weber, Christaller e Lösch de forma
interativa com gráficos Plotly e mapas Folium.
"""

import os
import json
import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import folium_static
import numpy as np

import config as cfg

# Configuração da página do Streamlit
st.set_page_config(
    page_title="Economia Regional - Região Sudeste",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS personalizada para visual Premium e Moderno
st.markdown("""
    <style>
    .main {
        background-color: #F8F9FA;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #E9ECEF;
    }
    .stMetric label {
        font-weight: 600;
        color: #495057 !important;
        font-size: 0.9rem !important;
    }
    .stMetric div[data-testid="stMetricValue"] {
        font-weight: 700;
        color: #212529 !important;
        font-size: 1.8rem !important;
    }
    div[data-testid="stSidebarUserContent"] {
        padding-top: 2rem;
    }
    h1, h2, h3 {
        font-family: 'Segoe UI', Arial, sans-serif;
    }
    .title-container {
        padding: 1.5rem;
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        color: white;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(30, 58, 138, 0.15);
    }
    </style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------
# 1. FUNÇÕES DE CARREGAMENTO DE DADOS (COM CACHE)
# --------------------------------------------------------------------------
CLEAN_DIR = os.path.join(cfg.BASE_DIR, "data_clean")

@st.cache_data
def carregar_municipios():
    caminho = os.path.join(CLEAN_DIR, "municipios_sudeste.gpkg")
    if os.path.exists(caminho):
        return gpd.read_file(caminho)
    return None

@st.cache_data
def carregar_pib_vab():
    caminho = os.path.join(CLEAN_DIR, "pib_vab_sudeste.parquet")
    if os.path.exists(caminho):
        return pd.read_parquet(caminho)
    return None

@st.cache_data
def carregar_cempre():
    caminho = os.path.join(CLEAN_DIR, "cempre_empregos_sudeste.parquet")
    if os.path.exists(caminho):
        return pd.read_parquet(caminho)
    return None

@st.cache_data
def carregar_demografia(tipo):
    if tipo == "hist":
        caminho = os.path.join(CLEAN_DIR, "historico_colonial_sudeste.parquet")
    else:
        caminho = os.path.join(CLEAN_DIR, f"pop_{tipo}_sudeste.parquet")
    if os.path.exists(caminho):
        return pd.read_parquet(caminho)
    return None

@st.cache_data
def carregar_camada_gpkg(nome):
    caminho = os.path.join(CLEAN_DIR, f"{nome}_sudeste.gpkg")
    if os.path.exists(caminho):
        return gpd.read_file(caminho)
    return None

@st.cache_data
def obter_geojson_sudeste():
    gdf = carregar_municipios()
    if gdf is not None:
        return json.loads(gdf.to_json())
    return None

@st.cache_data
def obter_geo_interface(nome):
    gdf = carregar_camada_gpkg(nome)
    if gdf is not None:
        return gdf.__geo_interface__
    return None

# Carregar dados principais
gdf_mun = carregar_municipios()
df_pib = carregar_pib_vab()
df_emp = carregar_cempre()

# --------------------------------------------------------------------------
# 2. MENU LATERAL DE FILTROS (SIDEBAR)
# --------------------------------------------------------------------------
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/0/05/Brazil_Region_Sudeste.svg", width=120)
st.sidebar.title("Filtros de Análise")

if df_pib is not None:
    # 1. Filtro de UF
    ufs_disponiveis = sorted(df_pib["SIGLA_UF"].unique())
    ufs_selecionadas = st.sidebar.multiselect(
        "Selecione as UFs:",
        options=ufs_disponiveis,
        default=ufs_disponiveis
    )
    if not ufs_selecionadas:
        ufs_selecionadas = ufs_disponiveis
        
    # 2. Filtro de Ano
    anos_disponiveis = sorted(df_pib["Ano"].unique())
    ano_selecionado = st.sidebar.slider(
        "Selecione o Ano de Referência (VAB/PIB):",
        min_value=int(min(anos_disponiveis)),
        max_value=int(max(anos_disponiveis)),
        value=int(max(anos_disponiveis))
    )
    
    # 3. Filtro de Setor
    setores_map = {
        "Agropecuária": "VAB_Agropecuaria",
        "Indústria": "VAB_Industria",
        "Serviços": "VAB_Servicos",
        "Adm. Pública": "VAB_Adm_Publica"
    }
    setor_selecionado = st.sidebar.selectbox(
        "Setor Econômico:",
        options=list(setores_map.keys())
    )
    col_setor = setores_map[setor_selecionado]
    
    # 4. Alternador de Métrica (VAB vs Empregos)
    metrica_selecionada = st.sidebar.radio(
        "Métrica para Análise de Especialização (QL):",
        options=["VAB Municipal (IBGE)", "Empregos (CEMPRE)"],
        index=0
    )
else:
    st.sidebar.error("Dados econômicos não encontrados no diretório data_clean/.")
    ufs_selecionadas = ["SP", "MG", "RJ", "ES"]
    ano_selecionado = 2021
    col_setor = "VAB_Industria"
    setor_selecionado = "Indústria"
    metrica_selecionada = "VAB Municipal (IBGE)"

# --------------------------------------------------------------------------
# 3. FILTRAGEM DOS DADOS EM TEMPO DE EXECUÇÃO
# --------------------------------------------------------------------------
if df_pib is not None:
    df_pib_filtrado = df_pib[(df_pib["SIGLA_UF"].isin(ufs_selecionadas)) & (df_pib["Ano"] == ano_selecionado)].copy()
else:
    df_pib_filtrado = pd.DataFrame()

# --------------------------------------------------------------------------
# 4. HEADER E TÍTULO PRINCIPAL
# --------------------------------------------------------------------------
st.markdown("""
    <div class="title-container">
        <h1 style='margin:0; font-size: 2.2rem;'>Economia Regional e Urbana do Sudeste do Brasil</h1>
        <p style='margin:5px 0 0 0; font-size: 1.1rem; opacity: 0.95;'>
            Análise Macroespacial, Logística e Teoria dos Modelos Clássicos de Localização
        </p>
    </div>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------
# 5. CÁLCULO DE KPIs DINÂMICOS
# --------------------------------------------------------------------------
if not df_pib_filtrado.empty:
    pib_total = df_pib_filtrado["PIB"].sum() * 1000 # Convertido para Reais (dados originais em mil)
    vab_setor = df_pib_filtrado[col_setor].sum() * 1000
    
    # Concentração IHH
    total_setor = df_pib_filtrado[col_setor].sum()
    if total_setor > 0:
        participacoes = df_pib_filtrado[col_setor] / total_setor
        ihh_val = ((participacoes * 100) ** 2).sum()
    else:
        ihh_val = 0
        
    # Empregos CEMPRE (filtrado por UFs)
    if df_emp is not None:
        df_emp_se = df_emp[df_emp["CD_MUN"].isin(df_pib_filtrado["CD_MUN"])].copy()
        col_emp_setor = "Emp_" + col_setor.replace("VAB_", "")
        emp_total = df_emp_se[col_emp_setor].sum()
    else:
        emp_total = 0
        
    # População total da área selecionada (Censo 2022 via modulo 2)
    df_idade = carregar_demografia("idade")
    if df_idade is not None:
        nome_para_sigla = {"São Paulo": "SP", "Rio de Janeiro": "RJ", "Minas Gerais": "MG", "Espírito Santo": "ES"}
        df_idade["SIGLA_UF"] = df_idade["UF"].map(nome_para_sigla)
        pop_total = df_idade[df_idade["SIGLA_UF"].isin(ufs_selecionadas)]["Total"].sum()
    else:
        pop_total = 0

    # Renderizar KPIs
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric(
            label=f"PIB Acumulado ({ano_selecionado})",
            value=f"R$ {pib_total / 1e12:.3f} Tri" if pib_total >= 1e12 else f"R$ {pib_total / 1e9:.1f} Bi"
        )
    with kpi2:
        st.metric(
            label="População Total (Censo 2022)",
            value=f"{pop_total / 1e6:.2f} Milhões" if pop_total > 0 else "N/D"
        )
    with kpi3:
        st.metric(
            label=f"IHH Espacial ({setor_selecionado})",
            value=f"{ihh_val:.1f}",
            help="Índice Hirschman-Herfindahl: <1500 desconcentrado, 1500-2500 moderado, >2500 altamente concentrado."
        )
    with kpi4:
        st.metric(
            label=f"Empregos Formais ({setor_selecionado})",
            value=f"{int(emp_total):,}".replace(",", ".") if emp_total > 0 else "N/D"
        )

st.write("")

# --------------------------------------------------------------------------
# 6. GUIAS DE NAVEGAÇÃO PRINCIPAL (TABS)
# --------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "👥 Demografia e Território", 
    "📈 Vocações Econômicas & Modelos", 
    "🚚 Logística & Meio Ambiente",
    "🕰 Evolução Histórica & Geopolítica"
])

# ==========================================================================
# TAB 1: DEMOGRAFIA E TERRITÓRIO
# ==========================================================================
with tab1:
    st.header("Análise Demográfica e Ocupação do Solo")
    
    col1_1, col1_2 = st.columns([1, 1])
    
    with col1_1:
        st.subheader("Pirâmide Etária — Região Sudeste (2010 vs 2022)")
        df_raca = carregar_demografia("raca")
        
        if df_raca is not None:
            # Gráfico de barras da evolução populacional por UF
            df_se = df_raca[df_raca["UF"].isin([cfg.NOMES_UF[cfg.UFS_SUDESTE[u]] for u in ufs_selecionadas])].copy()
            fig_pop = go.Figure()
            fig_pop.add_trace(go.Bar(
                x=df_se["UF"], y=df_se["Pop_Total_2010"],
                name="2010", marker_color="#3B82F6"
            ))
            fig_pop.add_trace(go.Bar(
                x=df_se["UF"], y=df_se["Pop_Total_2022"],
                name="2022", marker_color="#EF4444"
            ))
            fig_pop.update_layout(
                barmode="group",
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis_title="População (Habitantes)",
                legend_title="Censo",
                margin=dict(l=40, r=40, t=20, b=40)
            )
            st.plotly_chart(fig_pop, use_container_width=True)
        else:
            st.info("Planilhas de demografia não disponíveis.")
            
        # Composição Cor/Raça
        st.subheader("Composição Étnico-Racial por UF (Censo 2022)")
        if df_raca is not None:
            df_se = df_raca[df_raca["UF"].isin([cfg.NOMES_UF[cfg.UFS_SUDESTE[u]] for u in ufs_selecionadas])].copy()
            racas = ["Pop_Branca_2022", "Pop_Preta_2022", "Pop_Parda_2022", "Pop_Amarela_2022", "Pop_Indigena_2022"]
            labels = ["Branca", "Preta", "Parda", "Amarela", "Indígena"]
            colors = ["#FFE0B2", "#5D4037", "#8D6E63", "#FFCA28", "#D84315"]
            
            df_prop = df_se.set_index("UF")[racas].div(df_se.set_index("UF")[racas].sum(axis=1), axis=0) * 100
            df_prop = df_prop.reset_index()
            
            fig_raca = go.Figure()
            for raca, label, color in zip(racas, labels, colors):
                fig_raca.add_trace(go.Bar(
                    x=df_prop["UF"], y=df_prop[raca],
                    name=label, marker_color=color
                ))
            fig_raca.update_layout(
                barmode="stack",
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis_title="Proporção (%)",
                margin=dict(l=40, r=40, t=20, b=40)
            )
            st.plotly_chart(fig_raca, use_container_width=True)
            
    with col1_2:
        st.subheader("Fragmentação Territorial e Áreas Municipais")
        # Mostrar gráfico de fragmentação
        # Contagem simulada/histórica do número de municípios por UF em 1970, 1991, 2022
        dados_frag = {
            "UF": ["MG", "ES", "RJ", "SP"],
            "1970": [722, 53, 64, 573],
            "1991": [756, 78, 70, 572],
            "2022": [853, 78, 92, 645]
        }
        df_frag = pd.DataFrame(dados_frag)
        df_frag = df_frag[df_frag["UF"].isin(ufs_selecionadas)].copy()
        
        fig_frag = go.Figure()
        fig_frag.add_trace(go.Bar(x=df_frag["UF"], y=df_frag["1970"], name="1970", marker_color="#5C6BC0"))
        fig_frag.add_trace(go.Bar(x=df_frag["UF"], y=df_frag["1991"], name="1991", marker_color="#26A69A"))
        fig_frag.add_trace(go.Bar(x=df_frag["UF"], y=df_frag["2022"], name="2022", marker_color="#EF5350"))
        
        fig_frag.update_layout(
            barmode="group",
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis_title="Quantidade de Municípios",
            title_text="Fragmentação Emancipatória Pós-1988",
            margin=dict(l=40, r=40, t=40, b=40)
        )
        st.plotly_chart(fig_frag, use_container_width=True)
        
        # População Tradicional
        st.subheader("Populações Tradicionais (Indígenas e Quilombolas)")
        df_trad = carregar_demografia("tradicional")
        if df_trad is not None:
            df_trad_se = df_trad[df_trad["UF"].isin([cfg.NOMES_UF[cfg.UFS_SUDESTE[u]] for u in ufs_selecionadas])].copy()
            fig_trad = go.Figure()
            fig_trad.add_trace(go.Bar(
                x=df_trad_se["UF"], y=df_trad_se["Pop_Indigena"],
                name="Indígena", marker_color="#8D6E63"
            ))
            fig_trad.add_trace(go.Bar(
                x=df_trad_se["UF"], y=df_trad_se["Pop_Quilombola"],
                name="Quilombola", marker_color="#5D4037"
            ))
            fig_trad.update_layout(
                barmode="group",
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis_title="População (Habitantes)",
                margin=dict(l=40, r=40, t=20, b=40)
            )
            st.plotly_chart(fig_trad, use_container_width=True)

# ==========================================================================
# TAB 2: ECONOMIC ACTIVITY & CLASSICAL MODELS
# ==========================================================================
with tab2:
    st.header("Estrutura Produtiva e Vocações Regionais")
    
    if df_pib_filtrado.empty:
        st.warning("Selecione filtros válidos para calcular o Quociente Locacional.")
    else:
        # Calcular QL em tempo real
        df_ql = df_pib_filtrado.copy()
        setores = ["VAB_Agropecuaria", "VAB_Industria", "VAB_Servicos", "VAB_Adm_Publica"]
        df_ql["VAB_Total"] = df_ql[setores].sum(axis=1)
        
        totais_regiao = {s: df_ql[s].sum() for s in setores}
        vab_total_regiao = df_ql["VAB_Total"].sum()
        
        for s in setores:
            part_mun = df_ql[s] / df_ql["VAB_Total"]
            part_reg = totais_regiao[s] / vab_total_regiao
            df_ql[f"QL_{s}"] = (part_mun / part_reg).replace([np.inf, -np.inf], np.nan).fillna(0).round(4)
            
        # Determinar especialização
        df_ql["Setor_Dominante"] = df_ql[setores].idxmax(axis=1)
        df_ql["Setor_Dominante"] = df_ql["Setor_Dominante"].map({
            "VAB_Agropecuaria": "Agropecuária",
            "VAB_Industria": "Indústria",
            "VAB_Servicos": "Serviços",
            "VAB_Adm_Publica": "Adm. Pública"
        })
        
        col2_1, col2_2 = st.columns([1.2, 0.8])
        
        with col2_1:
            st.subheader("Mapa Coroplético de Especialização Regional")
            
            # Unir dados ao GeoDataFrame
            if gdf_mun is not None:
                # Filtrar os dados QL que serão plotados
                df_plot = df_ql[df_ql["Setor_Dominante"].notna()].copy()
                
                # Obter o GeoJSON completo e pré-carregado com cache
                geojson_dict = obter_geojson_sudeste()
                
                fig_mapa_econ = px.choropleth(
                    df_plot,
                    geojson=geojson_dict,
                    locations="CD_MUN",
                    featureidkey="properties.CD_MUN",
                    color="Setor_Dominante",
                    color_discrete_map={
                        "Agropecuária": "#4CAF50",
                        "Indústria": "#FF5722",
                        "Serviços": "#2196F3",
                        "Adm. Pública": "#9C27B0"
                    },
                    hover_name="NM_MUN",
                    hover_data={col_setor: ":.0f", f"QL_{col_setor}": ":.2f", "PIB": ":.0f"},
                    labels={"Setor_Dominante": "Vocação"},
                )
                
                fig_mapa_econ.update_geos(
                    fitbounds="locations",
                    visible=False
                )
                fig_mapa_econ.update_layout(
                    margin=dict(l=0, r=0, t=10, b=0),
                    height=500,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_mapa_econ, use_container_width=True)
            else:
                st.info("Shapefile de municípios não encontrado para renderização do mapa.")
                
        with col2_2:
            st.subheader(f"Especialização: Quociente Locacional (QL - {setor_selecionado})")
            st.write("Um **QL > 1** (área verde) indica que o município possui uma especialização maior que a média do Sudeste para o setor selecionado.")
            
            # Heatmap do QL para os top 20 municípios por PIB
            top20 = df_ql.nlargest(20, "PIB").copy()
            cols_ql = [f"QL_{s}" for s in setores]
            top20_ql = top20.set_index("NM_MUN")[cols_ql]
            top20_ql.columns = ["Agropecuária", "Indústria", "Serviços", "Adm. Pública"]
            
            fig_heatmap = px.imshow(
                top20_ql,
                labels=dict(x="Setores", y="Municípios", color="QL"),
                color_continuous_scale="RdYlGn",
                color_continuous_midpoint=1.0,
                aspect="auto"
            )
            fig_heatmap.update_layout(
                margin=dict(l=20, r=20, t=20, b=20),
                height=450
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)

        st.markdown("---")
        st.subheader("Modelos Espaciais Clássicos à Luz dos Dados Atuais")
        
        m1, m2, m3 = st.columns(3)
        
        with m1:
            st.markdown("### 🌾 Von Thünen (Agropecuária)")
            st.markdown(
                "O modelo prevê que culturas intensivas ficam próximas ao mercado e extensivas nas periferias. "
                "São Paulo (capital) funciona como o maior mercado do Sudeste."
            )
            # Calcular distância aproximada dos centroids dos municípios a SP (coordenadas SP: -23.55, -46.63)
            # Apenas ilustrativo com Plotly scatter plot (VAB Agro vs Distância)
            if gdf_mun is not None:
                gdf_mun_sp = gdf_mun.copy()
                centroids = gdf_mun_sp.geometry.centroid
                gdf_mun_sp["dist_sp"] = np.sqrt((centroids.x - (-46.63))**2 + (centroids.y - (-23.55))**2) * 111.12 # Km aproximado
                df_thunen = df_ql.merge(gdf_mun_sp[["CD_MUN", "dist_sp"]], on="CD_MUN", how="inner")
                
                fig_thunen = px.scatter(
                    df_thunen, x="dist_sp", y="VAB_Agropecuaria",
                    trendline="ols", log_y=True,
                    labels={"dist_sp": "Distância de São Paulo (km)", "VAB_Agropecuaria": "VAB Agropecuária (Log)"},
                    hover_name="NM_MUN"
                )
                fig_thunen.update_layout(plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=20, r=20, t=10, b=20), height=280)
                st.plotly_chart(fig_thunen, use_container_width=True)
                st.caption("Correlação negativa: quanto mais distante do polo consumidor central (SP), menor a concentração do valor agrícola agregado por área.")

        with m2:
            st.markdown("### 🏭 Weber (Indústria & Logística)")
            st.markdown(
                "A localização industrial ótima busca minimizar os custos de frete e transporte. "
                "No Sudeste, a atividade industrial concentra-se densamente nos eixos estruturantes (ex: Rodovia Presidente Dutra SP-RJ)."
            )
            # Barras do IHH setorial
            ihh_setores = {}
            for s in setores:
                t_setor = df_ql[s].sum()
                if t_setor > 0:
                    ihh_setores[s.replace("VAB_", "")] = ((df_ql[s] / t_setor * 100)**2).sum()
                    
            df_ihh_plot = pd.DataFrame({
                "Setor": list(ihh_setores.keys()),
                "IHH": list(ihh_setores.values())
            })
            fig_ihh = px.bar(
                df_ihh_plot, x="Setor", y="IHH",
                color="Setor",
                color_discrete_map={"Agropecuaria": "#4CAF50", "Industria": "#FF5722", "Servicos": "#2196F3", "Adm_Publica": "#9C27B0"},
                labels={"Setor": "Setor", "IHH": "Índice IHH"},
            )
            fig_ihh.update_layout(plot_bgcolor="rgba(0,0,0,0)", showlegend=False, margin=dict(l=20, r=20, t=10, b=20), height=280)
            st.plotly_chart(fig_ihh, use_container_width=True)
            st.caption("IHH Industrial alto indica forte concentração geográfica da produção nas zonas centrais e de corredor de transporte ( Weber).")

        with m3:
            st.markdown("### 🏛 Christaller (Lugares Centrais)")
            st.markdown(
                "Centros urbanos hierarquizam-se conforme o alcance de seus bens e serviços. "
                "Metrópoles (SP, RJ, BH) no topo, oferecendo serviços de alta complexidade e centralidade."
            )
            # Top 10 cidades por VAB de Serviços (Lugares Centrais de maior ordem)
            top10_serv = df_ql.nlargest(10, "VAB_Servicos")
            fig_chris = px.bar(
                top10_serv, x="NM_MUN", y="VAB_Servicos",
                color="SIGLA_UF",
                color_discrete_map={"SP": "#E91E63", "MG": "#2196F3", "RJ": "#FF9800", "ES": "#4CAF50"},
                labels={"NM_MUN": "Lugar Central", "VAB_Servicos": "VAB de Serviços"},
            )
            fig_chris.update_layout(plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=20, r=20, t=10, b=20), height=280)
            st.plotly_chart(fig_chris, use_container_width=True)
            st.caption("Hierarquização clara do VAB de Serviços, caracterizando as capitais estaduais como polos globais da rede urbana.")

# ==========================================================================
# TAB 3: LOGÍSTICA E MEIO AMBIENTE
# ==========================================================================
with tab3:
    st.header("Infraestrutura de Transporte e Cobertura Natural")
    
    st.write(
        "Esta seção sobrepõe as malhas estruturantes de transporte do Sudeste (rodovias, ferrovias, portos e aeroportos) "
        "com a distribuição natural dos biomas (Cerrado, Mata Atlântica) e Unidades de Conservação."
    )
    
    # Criar mapa interativo Folium
    col3_1, col3_2 = st.columns([1.5, 0.5])
    
    with col3_2:
        st.subheader("Controle de Camadas")
        st.markdown("Selecione quais infraestruturas e biomas deseja plotar sobre o mapa básico do Sudeste:")
        
        # Checkboxes de camadas
        show_rodovias = st.checkbox("Rodovias Estruturantes", value=True)
        show_ferrovias = st.checkbox("Ferrovias", value=True)
        show_ucs = st.checkbox("Unidades de Conservação", value=False)
        show_biomas = st.checkbox("Biomas (Fundo)", value=False)
        show_portos = st.checkbox("Portos & Aeroportos", value=True)
        
    with col3_1:
        # Gerar o mapa Folium
        m = folium.Map(location=[-21.5, -45.0], zoom_start=6, tiles="cartodbpositron")
        
        # 1. Plotar biomas (se selecionado)
        if show_biomas:
            gdf_biomas = carregar_camada_gpkg("biomas")
            if gdf_biomas is not None:
                # Filtrar feições vazias
                gdf_biomas = gdf_biomas[gdf_biomas.geometry.notna()].copy()
                colors_bioma = {"Cerrado": "#8B4513", "Mata Atlântica": "#228B22", "Caatinga": "#DAA520"}
                for idx, row in gdf_biomas.iterrows():
                    b_nome = row.get("nom_bioma", row.get("bioma", ""))
                    cor = "#CCCCCC"
                    for k, v in colors_bioma.items():
                        if k.lower() in str(b_nome).lower():
                            cor = v
                    folium.GeoJson(
                        row.geometry,
                        style_function=lambda x, cor=cor: {"fillColor": cor, "color": cor, "weight": 0.5, "fillOpacity": 0.15}
                    ).add_to(m)
                    
        # 2. Plotar UCs
        if show_ucs:
            geo_ucs = obter_geo_interface("ucs")
            if geo_ucs is not None:
                folium.GeoJson(
                    geo_ucs,
                    name="Unidades de Conservação",
                    style_function=lambda x: {"fillColor": "#2E7D32", "color": "#1B5E20", "weight": 0.8, "fillOpacity": 0.4}
                ).add_to(m)
                
        # 3. Plotar Rodovias
        if show_rodovias:
            geo_rods = obter_geo_interface("rodovias")
            if geo_rods is not None:
                folium.GeoJson(
                    geo_rods,
                    name="Rodovias",
                    style_function=lambda x: {"color": "#D32F2F", "weight": 1.2, "opacity": 0.8}
                ).add_to(m)
                
        # 4. Plotar Ferrovias
        if show_ferrovias:
            geo_ferrs = obter_geo_interface("ferrovias")
            if geo_ferrs is not None:
                folium.GeoJson(
                    geo_ferrs,
                    name="Ferrovias",
                    style_function=lambda x: {"color": "#212121", "weight": 1.5, "dashArray": "5, 5", "opacity": 0.9}
                ).add_to(m)
                
        # 5. Plotar Portos e Aeroportos
        if show_portos:
            gdf_aeros = carregar_camada_gpkg("aeroportos")
            gdf_portos = carregar_camada_gpkg("portos")
            
            if gdf_aeros is not None:
                for idx, row in gdf_aeros.iterrows():
                    geom = row.geometry
                    if geom.geom_type == 'Point':
                        folium.Marker(
                            location=[geom.y, geom.x],
                            icon=folium.Icon(color="red", icon="plane", prefix="fa"),
                            popup=f"Aeroporto: {row.get('nome', 'N/D')}"
                        ).add_to(m)
                        
            if gdf_portos is not None:
                for idx, row in gdf_portos.iterrows():
                    geom = row.geometry
                    if geom.geom_type == 'Point':
                        folium.Marker(
                            location=[geom.y, geom.x],
                            icon=folium.Icon(color="blue", icon="anchor", prefix="fa"),
                            popup=f"Porto: {row.get('nome', 'N/D')}"
                        ).add_to(m)
                        
        # Renderizar mapa no Streamlit
        folium_static(m, width=800, height=550)

# ==========================================================================
# TAB 4: EVOLUÇÃO HISTÓRICA & GEOPOLÍTICA
# ==========================================================================
with tab4:
    st.header("Evolução Histórico-Territorial e Path Dependence")
    
    col4_1, col4_2 = st.columns([1, 1])
    
    with col4_1:
        st.subheader("Divisões Regionais Oficiais do Brasil (Evolução IBGE)")
        st.markdown(
            "Veja como os estados do Sudeste pertenciam a regiões separadas na geopolítica nacional de outrora. "
            "A unificação sob a região 'Sudeste' só se consolidou na divisão de **1969**."
        )
        
        hist_div = st.selectbox(
            "Selecione o Ano da Divisão Regional Histórica:",
            options=["1913 (Delgado de Carvalho)", "1938 (Anuário Estatístico)", "1942 (1ª Oficial IBGE)", "1969 (Atual IBGE)"]
        )
        
        # Mostrar imagem de mapa de evolução de acordo com a seleção
        if "1913" in hist_div:
            st.info("💡 Divisão de 1913: São Paulo pertencia à região 'Meridional', enquanto Minas, Rio e Espírito Santo pertenciam ao 'Oriental'.")
        elif "1938" in hist_div:
            st.info("💡 Divisão de 1938: Minas no 'Centro', Espírito Santo no 'Este', e São Paulo/Rio no 'Sul'.")
        elif "1942" in hist_div:
            st.info("💡 Divisão de 1942: Minas, Rio e Espírito Santo eram o 'Leste Meridional' e São Paulo pertencia ao 'Sul'.")
        else:
            st.info("💡 Divisão de 1969: Pela primeira vez, os quatro estados se unem formalmente na atual Região Sudeste.")
            
        st.image("output/modulo5/mapa_evolucao_historica.png", caption="Evolução Oficial das Divisões Regionais do Brasil")
        
    with col4_2:
        st.subheader("Path Dependence: Herança Colonial vs VAB Atual")
        st.markdown(
            "Esta visualização comprova como a especialização econômica contemporânea está enraizada nos "
            "ciclos produtivos coloniais e na infraestrutura herdada (ex: ferrovias do Ciclo do Café)."
        )
        
        df_hist_parquet = carregar_demografia("hist")
        if df_hist_parquet is not None:
            # Gráfico de barras da composição setorial atual herdada
            st.dataframe(df_hist_parquet.set_index("UF"))
        else:
            st.info("Tabela de herança histórica não encontrada.")
            
        st.image("output/modulo5/grafico_path_dependence.png", caption="Cruze Histórico: Ciclo Colonial vs VAB Setorial Atual")

# --------------------------------------------------------------------------
# RODAPÉ
# --------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #6C757D; font-size: 0.8rem;'>"
    "Dashboard desenvolvido para a disciplina de Economia Regional e Urbana | "
    "Dados: IBGE Censo 2022, PAM, PIA, PAS, CEMPRE (2010-2023)"
    "</p>",
    unsafe_allow_html=True
)
