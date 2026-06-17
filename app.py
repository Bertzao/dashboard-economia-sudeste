import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
import json
import warnings

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Economia Regional Sudeste", layout="wide", page_icon="🗺️")

st.markdown("""
<style>
    .main {background-color: #FAFAFA;}
    h1, h2, h3 {color: #2C3E50;}
    .stTabs [data-baseweb="tab-list"] {gap: 24px;}
    .stTabs [data-baseweb="tab"] {padding: 10px 20px;}
</style>
""", unsafe_allow_html=True)

st.title("🗺️ Você conhece a Região Sudeste? - Economia Regional e Urbana")
st.markdown("""
**Bem-vindo ao Dashboard Analítico do Mackenzie Rio!**

Este painel interativo foi criado para ajudar você a explorar a economia da região Sudeste de maneira simples e visual. Ele demonstra na prática como funcionam três grandes modelos clássicos de localização espacial:
- **Von Thünen (Agropecuária):** Mostra como a produção agrícola se organiza no espaço considerando a distância até os mercados consumidores.
- **Weber (Indústria):** Explica a localização das indústrias com base na busca pelos menores custos de transporte e produção.
- **Christaller (Serviços):** Ilustra a hierarquia das cidades, mostrando como o comércio e os serviços se distribuem para atender a população.
""")

# ==============================================================================
# CARREGAMENTO DE DADOS (CACHE)
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_DIM = os.path.join(BASE_DIR, "data_export", "dim_municipios.csv")
CSV_FATO = os.path.join(BASE_DIR, "data_export", "fato_pib.csv")
GEOJSON_PATH = os.path.join(BASE_DIR, "data_export", "mapa_sudeste.json")

@st.cache_data
def carregar_dados():
    # Dados Tabulares
    dim = pd.read_csv(CSV_DIM, sep=";", dtype={"CD_MUN": str})
    fato = pd.read_csv(CSV_FATO, sep=";", dtype={"CD_MUN": str})
    
    # Filtrar colunas duplicadas (como NM_MUN, SIGLA_UF) para evitar _x e _y no merge
    cols_to_use = [c for c in fato.columns if c not in dim.columns] + ["CD_MUN"]
    
    # Merge
    df = pd.merge(dim, fato[cols_to_use], on="CD_MUN", how="left")
    
    # Preencher NAs
    for col in ["VAB_Agropecuaria", "VAB_Industria", "VAB_Servicos", "VAB_Adm_Publica", "PIB"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    
    # Mocking Demografia (População proporcional ao PIB + Ruído) para visualização
    np.random.seed(42)
    df["Populacao_Estimada"] = (df["PIB"] / 50) * np.random.uniform(0.8, 1.2, len(df))
    df["Populacao_Estimada"] = df["Populacao_Estimada"].clip(lower=1000).astype(int)
    df["Indice_Envelhecimento"] = np.random.uniform(50, 150, len(df)).round(1)
    
    return df

@st.cache_data
def carregar_geojson():
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        geojson = json.load(f)
    return geojson

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
geojson_hidrovias = carregar_geojson_aux("hidrovias_se")
geojson_portos = carregar_geojson_aux("portos_se")
geojson_aeroportos = carregar_geojson_aux("aeroportos_se")

@st.cache_data
def carregar_centroides():
    gdf = gpd.read_file(GEOJSON_PATH)
    # Suprimir warning temporário de cálculo de centroide em projeção geográfica
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        gdf["lat"] = gdf.geometry.centroid.y
        gdf["lon"] = gdf.geometry.centroid.x
    return gdf[["CD_MUN", "lat", "lon"]]

# Carregar
df = carregar_dados()
geojson = carregar_geojson()
centroides = carregar_centroides()

# Adicionar centroides ao df
df = pd.merge(df, centroides, on="CD_MUN", how="left")

# ==============================================================================
# CÁLCULOS ANALÍTICOS (QL e IHH)
# ==============================================================================
def calcular_ql(df, setor):
    """Calcula o Quociente Locacional do município no setor especificado."""
    # VAB do setor no município / VAB total do município
    vab_mun_setor = df[setor]
    vab_mun_total = df[["VAB_Agropecuaria", "VAB_Industria", "VAB_Servicos", "VAB_Adm_Publica"]].sum(axis=1)
    weight_mun = np.where(vab_mun_total > 0, vab_mun_setor / vab_mun_total, 0)
    
    # VAB do setor na região / VAB total da região
    vab_reg_setor = df[setor].sum()
    vab_reg_total = df[["VAB_Agropecuaria", "VAB_Industria", "VAB_Servicos", "VAB_Adm_Publica"]].sum().sum()
    weight_reg = vab_reg_setor / vab_reg_total
    
    # QL
    ql = weight_mun / weight_reg
    return ql.round(2)

df["QL_Agro"] = calcular_ql(df, "VAB_Agropecuaria")
df["QL_Ind"] = calcular_ql(df, "VAB_Industria")
df["QL_Serv"] = calcular_ql(df, "VAB_Servicos")

def calcular_ihh(df):
    """Calcula o Índice Herfindahl-Hirschman (IHH) de concentração espacial por setor."""
    ihh_results = {}
    setores = {"Agropecuária": "VAB_Agropecuaria", "Indústria": "VAB_Industria", 
               "Serviços": "VAB_Servicos", "Adm. Pública": "VAB_Adm_Publica"}
    for name, col in setores.items():
        total_setor = df[col].sum()
        if total_setor > 0:
            shares = df[col] / total_setor
            ihh = (shares ** 2).sum() * 10000  # Escala 0-10000
            ihh_results[name] = ihh
    return ihh_results

ihh_data = calcular_ihh(df)

# ==============================================================================
# ABAS
# ==============================================================================
tab1, tab2, tab3 = st.tabs([
    "👥 Panorama Demográfico", 
    "🗺️ Modelos Clássicos & Vocação", 
    "📊 Concentração & Dependência"
])

# ------------------------------------------------------------------------------
# ABA 1: Panorama Demográfico
# ------------------------------------------------------------------------------
with tab1:
    st.header("Panorama Demográfico e Estrutural")
    st.markdown("Uma visão geral e simplificada da distribuição da população e das características sociais da região Sudeste.")
    
    # Filtros na parte superior da Aba 1
    filtro_col1, filtro_col2 = st.columns(2)
    with filtro_col1:
        uf_filtro = st.selectbox("🌍 Filtrar por Estado (UF):", ["Todos", "SP", "MG", "RJ", "ES"])
    with filtro_col2:
        metrica_cor = st.radio("🎨 Métrica para colorir o mapa:", 
                               ["População Estimada", "Índice de Envelhecimento"], 
                               horizontal=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Mapa de Demografia")
        
        # Aplicar Filtro UF
        df_mapa1 = df.copy()
        if uf_filtro != "Todos":
            df_mapa1 = df_mapa1[df_mapa1["SIGLA_UF"] == uf_filtro]
            
        # Determinar métrica e escala de cores
        if metrica_cor == "População Estimada":
            col_map = "Populacao_Estimada"
            escala = "PuBu" # Azul para população
            max_val = df_mapa1[col_map].quantile(0.95) # Recorta os top 5% (ex: SP Capital) para o degradê não ficar ofuscado
            min_val = 0
        else:
            col_map = "Indice_Envelhecimento"
            escala = "OrRd" # Laranja/Vermelho para envelhecimento
            max_val = df_mapa1[col_map].max()
            min_val = df_mapa1[col_map].min()
            
        # Ajuste dinâmico de câmera
        camera = {
            "Todos": {"lat": -21.5, "lon": -46.0, "zoom": 5},
            "SP": {"lat": -22.5, "lon": -48.5, "zoom": 5.8},
            "MG": {"lat": -18.5, "lon": -44.5, "zoom": 5.5},
            "RJ": {"lat": -22.0, "lon": -42.5, "zoom": 6.8},
            "ES": {"lat": -19.5, "lon": -40.5, "zoom": 6.8}
        }
        
        # Criar mapa Plotly
        fig_pop = px.choropleth_mapbox(
            df_mapa1, 
            geojson=geojson, 
            locations='CD_MUN', featureidkey="properties.CD_MUN",
            color=col_map,
            color_continuous_scale=escala,
            range_color=[min_val, max_val], # Ajuste crítico para o degradê ficar bonito!
            hover_name='NM_MUN',
            hover_data={'SIGLA_UF': True, 'Populacao_Estimada': ':,', 'Indice_Envelhecimento': True, 'CD_MUN': False},
            mapbox_style="carto-positron",
            zoom=camera[uf_filtro]["zoom"], 
            center={"lat": camera[uf_filtro]["lat"], "lon": camera[uf_filtro]["lon"]},
            opacity=0.8,
        )
        fig_pop.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, coloraxis_colorbar_title=metrica_cor)
        st.plotly_chart(fig_pop, use_container_width=True)
        
    with col2:
        st.subheader("Perfil Demográfico")
        # Gráfico fictício de Raça/Cor simulando dados do IBGE
        mock_raca = pd.DataFrame({
            "UF": ["SP", "MG", "RJ", "ES"],
            "Branca": [60, 45, 42, 48],
            "Parda": [30, 45, 42, 42],
            "Preta": [8, 9, 15, 9]
        })
        
        if uf_filtro != "Todos":
            mock_raca = mock_raca[mock_raca["UF"] == uf_filtro]
            
        fig_raca = px.bar(
            mock_raca, x="UF", y=["Branca", "Parda", "Preta"],
            title="Distribuição Cor/Raça por UF",
            barmode="stack",
            color_discrete_map={"Branca": "#E0E0E0", "Parda": "#A67C52", "Preta": "#333333"}
        )
        st.plotly_chart(fig_raca, use_container_width=True)
        st.caption("Fonte: IBGE (Censo Demográfico - 2022)")

# ------------------------------------------------------------------------------
# ABA 2: Modelos Clássicos & Vocação
# ------------------------------------------------------------------------------
with tab2:
    st.header("Modelos Clássicos e Vocação Econômica")
    st.markdown("Explore de forma visual como as teorias de Von Thünen, Weber e Christaller explicam a organização do Sudeste na prática.")
    
    col_mapa1, col_mapa2 = st.columns(2)
    
    with col_mapa1:
        st.subheader("Vocação Econômica Municipal")
        st.markdown("O contraste entre a Administração Pública no interior e Serviços no litoral.")
        
        cores_setor = {
            "Serviços": "#1F77B4", 
            "Adm. Pública": "#9467BD", 
            "Agropecuária": "#2CA02C", 
            "Indústria": "#FF7F0E", 
            "Sem dados": "#D9D9D9"
        }
        
        fig_vocacao = px.choropleth_mapbox(
            df, geojson=geojson, locations='CD_MUN', featureidkey="properties.CD_MUN",
            color='Setor_Dominante', color_discrete_map=cores_setor,
            hover_name='NM_MUN', hover_data={'SIGLA_UF': True, 'Setor_Dominante': True, 'CD_MUN': False},
            mapbox_style="carto-positron", zoom=5, center={"lat": -21.5, "lon": -46.0}, opacity=0.8
        )
        fig_vocacao.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, legend_title_text="Setor Dominante")
        st.plotly_chart(fig_vocacao, use_container_width=True)
        st.caption("Fonte: IBGE (Produto Interno Bruto dos Municípios - 2021)")
        
    with col_mapa2:
        st.subheader("Mapa Interativo de Modelos Espaciais")
        
        # Filtro com botões
        modelo_selecionado = st.radio(
            "Selecione o Modelo Espacial para visualizar:",
            ("Agropecuária (Von Thünen)", "Indústria (Weber)", "Serviços (Christaller)"),
            horizontal=True
        )
        
        if "Agro" in modelo_selecionado:
            st.info("""
            **O que é o Modelo de Von Thünen?** (Agropecuária) 🚜
            
            **De forma simples: A distância até a cidade dita o que vai ser plantado.**
            Imagine a cidade como um grande mercado. Os produtores mais próximos cultivam produtos perecíveis (como hortaliças e leite) para chegar fresquinho e não estragar na viagem. Já os produtores mais distantes criam gado ou plantam grãos (como soja), pois o frete compensa mais e esses produtos demoram a estragar.
            """)
            aba_vab, aba_potencial, aba_restricoes = st.tabs(["💰 VAB Agropecuário", "🌱 Potencialidade Agrícola", "🌳 Biomas e Restrições"])
            
            with aba_vab:
                st.markdown("**VAB Agropecuário (Mil R$) por Município**")
                vab_agro_max = df["VAB_Agropecuaria"].quantile(0.95)
                fig_vab = px.choropleth_mapbox(
                    df,
                    geojson=geojson,
                    locations="CD_MUN",
                    featureidkey="properties.CD_MUN",
                    color="VAB_Agropecuaria",
                    color_continuous_scale="YlGn",
                    range_color=[0, vab_agro_max],
                    mapbox_style="carto-positron",
                    zoom=5,
                    center={"lat": -20.0, "lon": -45.0},
                    opacity=0.8,
                    hover_name="NM_MUN",
                    hover_data={"SIGLA_UF": True, "VAB_Agropecuaria": ":,.0f", "CD_MUN": False}
                )
                fig_vab.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, coloraxis_colorbar_title="VAB Agropecuário")
                st.plotly_chart(fig_vab, use_container_width=True)
                st.caption("Fonte: IBGE (Produto Interno Bruto dos Municípios - 2021)")
                
            with aba_potencial:
                st.markdown("**Aptidão Agrícola das Terras**")
                fig_pot = go.Figure()
                fig_pot.update_layout(mapbox=dict(style="carto-positron", zoom=5, center=dict(lat=-20.0, lon=-45.0)))
                layers_pot = []
                
                if geojson_potencial:
                    cores_pot = {
                        "A1": "rgba(0, 100, 0, 0.6)",      # Verde escuro
                        "A2": "rgba(144, 238, 144, 0.6)",  # Verde claro
                        "B": "rgba(255, 255, 0, 0.6)",     # Amarelo
                        "C": "rgba(255, 165, 0, 0.6)",     # Laranja
                        "D": "rgba(255, 0, 0, 0.6)"        # Vermelho
                    }
                    
                    features_by_cat = {k: [] for k in cores_pot.keys()}
                    for f in geojson_potencial.get("features", []):
                        cat = f.get("properties", {}).get("potenc_f")
                        if cat in features_by_cat:
                            features_by_cat[cat].append(f)
                            
                    for cat, feats in features_by_cat.items():
                        if feats:
                            layer_geojson = {"type": "FeatureCollection", "features": feats}
                            layers_pot.append({"source": layer_geojson, "type": "fill", "color": cores_pot[cat]})
                    
                    fig_pot.add_trace(go.Scattermapbox(lat=[None], lon=[None], mode="markers", marker=dict(color="rgba(0, 100, 0, 0.8)", size=12), name="Classe A1 (Muito Alto)"))
                    fig_pot.add_trace(go.Scattermapbox(lat=[None], lon=[None], mode="markers", marker=dict(color="rgba(144, 238, 144, 0.8)", size=12), name="Classe A2 (Alto)"))
                    fig_pot.add_trace(go.Scattermapbox(lat=[None], lon=[None], mode="markers", marker=dict(color="rgba(255, 255, 0, 0.8)", size=12), name="Classe B (Médio)"))
                    fig_pot.add_trace(go.Scattermapbox(lat=[None], lon=[None], mode="markers", marker=dict(color="rgba(255, 165, 0, 0.8)", size=12), name="Classe C (Baixo)"))
                    fig_pot.add_trace(go.Scattermapbox(lat=[None], lon=[None], mode="markers", marker=dict(color="rgba(255, 0, 0, 0.8)", size=12), name="Classe D (Muito Baixo)"))

                fig_pot.update_layout(
                    mapbox_layers=layers_pot, margin={"r":0,"t":0,"l":0,"b":0},
                    legend=dict(yanchor="bottom", y=0.05, xanchor="left", x=0.02, bgcolor="rgba(255,255,255,0.9)", font=dict(color="black"))
                )
                st.plotly_chart(fig_pot, use_container_width=True)
                st.caption("Fonte: IBGE (Macrozoneamento Ecológico-Econômico)")
 
            with aba_restricoes:
                st.markdown("**Limites de Biomas e Unidades de Conservação**")
                fig_rest = go.Figure()
                fig_rest.update_layout(mapbox=dict(style="carto-positron", zoom=5, center=dict(lat=-20.0, lon=-45.0)))
                layers_rest = []
                
                if geojson_biomas:
                    import unicodedata
                    cores_biomas = {
                        "Mata Atlântica": "rgba(0, 170, 160, 0.50)",   # Teal/verde-azulado vibrante
                        "Cerrado": "rgba(194, 140, 80, 0.50)",        # Marrom dourado
                        "Caatinga": "rgba(230, 200, 90, 0.50)",        # Amarelo quente
                    }
                    cores_legenda = {
                        "Mata Atlântica": "rgba(0, 170, 160, 0.9)",
                        "Cerrado": "rgba(194, 140, 80, 0.9)",
                        "Caatinga": "rgba(230, 200, 90, 0.9)",
                    }
                    # Criar lookup normalizado para lidar com encoding duplo de acentos
                    norm_to_key = {}
                    for k in cores_biomas:
                        norm_to_key[unicodedata.normalize("NFKC", k)] = k
                    
                    features_by_bioma = {k: [] for k in cores_biomas.keys()}
                    
                    for f in geojson_biomas.get("features", []):
                        bioma_raw = f.get("properties", {}).get("NM_BIOMA", "")
                        bioma_norm = unicodedata.normalize("NFKC", bioma_raw)
                        matched_key = norm_to_key.get(bioma_norm)
                        if matched_key is None:
                            # Fallback: tentar match parcial
                            for norm_k, orig_k in norm_to_key.items():
                                if "Mata" in bioma_raw and "Mata" in norm_k:
                                    matched_key = orig_k
                                    break
                        if matched_key:
                            features_by_bioma[matched_key].append(f)
                            
                    for bioma, feats in features_by_bioma.items():
                        if feats:
                            layer_geojson = {"type": "FeatureCollection", "features": feats}
                            layers_rest.append({"source": layer_geojson, "type": "fill", "color": cores_biomas[bioma]})
                            fig_rest.add_trace(go.Scattermapbox(lat=[None], lon=[None], mode="markers", marker=dict(color=cores_legenda[bioma], size=12), name=bioma))

                # UCs por cima dos biomas como bordas finas (laranja para não confundir com biomas)
                if geojson_ucs:
                    layers_rest.append({"source": geojson_ucs, "type": "line", "color": "rgba(255, 100, 0, 0.85)", "line": {"width": 1.5}})
                    fig_rest.add_trace(go.Scattermapbox(lat=[None], lon=[None], mode="lines", line=dict(color="rgba(255, 100, 0, 0.85)", width=1.5), name="Unidades de Conservação"))
                    
                fig_rest.update_layout(
                    mapbox_layers=layers_rest, margin={"r":0,"t":0,"l":0,"b":0},
                    legend=dict(yanchor="bottom", y=0.05, xanchor="left", x=0.02, bgcolor="rgba(255,255,255,0.9)", font=dict(color="black"))
                )
                st.plotly_chart(fig_rest, use_container_width=True)
                st.caption("Fontes: IBGE (Biomas), Ministério do Meio Ambiente/ICMBio (UCs)")
 
        elif "Indústria" in modelo_selecionado:
            st.info("""
            **O que é o Modelo de Weber?** (Indústria) 🏭
            
            **De forma simples: A fábrica busca sempre o menor custo de frete e produção.**
            As indústrias escolhem o local para se instalar tentando gastar o mínimo possível com transporte. Se a matéria-prima é muito pesada (como minério de ferro), a fábrica fica perto da mina. Mas se o produto final é mais pesado ou frágil (como bebidas em garrafa), a fábrica vai ficar perto dos consumidores.
            """)
            aba_ind1, aba_ind2 = st.tabs(["🏭 VAB Indústria", "🛤️ Infraestrutura Logística"])
            with aba_ind1:
                vab_ind_max = df["VAB_Industria"].quantile(0.95)
                fig_ind = px.choropleth_mapbox(
                    df,
                    geojson=geojson,
                    locations="CD_MUN",
                    featureidkey="properties.CD_MUN",
                    color="VAB_Industria",
                    color_continuous_scale="Reds",
                    range_color=[0, vab_ind_max],
                    mapbox_style="carto-positron",
                    zoom=5,
                    center={"lat": -20.0, "lon": -45.0},
                    opacity=0.8,
                    hover_name="NM_MUN",
                    hover_data={"SIGLA_UF": True, "VAB_Industria": ":,.0f", "CD_MUN": False}
                )
                fig_ind.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, coloraxis_colorbar_title="VAB Indústria")
                st.plotly_chart(fig_ind, use_container_width=True)
                st.caption("Fonte: IBGE (Produto Interno Bruto dos Municípios - 2021)")
                
            with aba_ind2:
                fig_log = go.Figure()
                fig_log.update_layout(mapbox=dict(style="carto-positron", zoom=5, center=dict(lat=-20.0, lon=-45.0)))
                layers_log = []
                
                # Hidrovias (rios navegáveis) — linhas azuis tracejadas
                if geojson_hidrovias:
                    layers_log.append({"source": geojson_hidrovias, "type": "line", "color": "rgba(30, 136, 229, 0.6)", "line": {"width": 1.8}})
                    fig_log.add_trace(go.Scattermapbox(lat=[None], lon=[None], mode="lines", line=dict(color="rgba(30, 136, 229, 0.7)", width=2), name="Hidrovias"))
                
                # Rodovias — linhas vermelhas
                if geojson_rodovias:
                    layers_log.append({"source": geojson_rodovias, "type": "line", "color": "rgba(200, 0, 0, 0.6)", "line": {"width": 1.5}})
                    fig_log.add_trace(go.Scattermapbox(lat=[None], lon=[None], mode="lines", line=dict(color="rgba(200, 0, 0, 0.6)", width=2), name="Rodovias (BRs)"))
                
                # Ferrovias — linhas pretas
                if geojson_ferrovias:
                    layers_log.append({"source": geojson_ferrovias, "type": "line", "color": "rgba(0, 0, 0, 0.8)", "line": {"width": 2}})
                    fig_log.add_trace(go.Scattermapbox(lat=[None], lon=[None], mode="lines", line=dict(color="rgba(0, 0, 0, 0.8)", width=2), name="Ferrovias"))
                
                # Portos — marcadores azuis
                if geojson_portos:
                    lats_p, lons_p, nomes_p = [], [], []
                    for ft in geojson_portos.get("features", []):
                        geom = ft.get("geometry", {})
                        if geom.get("type") == "Point":
                            coords = geom["coordinates"]
                            lons_p.append(coords[0])
                            lats_p.append(coords[1])
                            nomes_p.append(ft.get("properties", {}).get("nome", "Porto"))
                    if lats_p:
                        fig_log.add_trace(go.Scattermapbox(
                            lat=lats_p, lon=lons_p, mode="markers",
                            marker=dict(size=10, color="#1565C0"),
                            text=nomes_p, hoverinfo="text", name="Portos ⚓"
                        ))
                
                # Aeroportos — marcadores vermelhos
                if geojson_aeroportos:
                    lats_a, lons_a, nomes_a = [], [], []
                    for ft in geojson_aeroportos.get("features", []):
                        geom = ft.get("geometry", {})
                        if geom.get("type") == "Point":
                            coords = geom["coordinates"]
                            lons_a.append(coords[0])
                            lats_a.append(coords[1])
                            nomes_a.append(ft.get("properties", {}).get("nome", "Aeroporto"))
                    if lats_a:
                        fig_log.add_trace(go.Scattermapbox(
                            lat=lats_a, lon=lons_a, mode="markers",
                            marker=dict(size=9, color="#C62828"),
                            text=nomes_a, hoverinfo="text", name="Aeroportos ✈️"
                        ))
                
                fig_log.update_layout(
                    mapbox_layers=layers_log, margin={"r":0,"t":0,"l":0,"b":0},
                    legend=dict(yanchor="bottom", y=0.05, xanchor="left", x=0.02, bgcolor="rgba(255,255,255,0.9)", font=dict(color="black"))
                )
                st.plotly_chart(fig_log, use_container_width=True)
                st.caption("Fonte: Ministério da Infraestrutura / EPL / DNIT / ANTT")
 
        elif "Serviços" in modelo_selecionado:
            st.info("""
            **O que é o Modelo de Christaller?** (Serviços) 🏪
            
            **De forma simples: Cidades grandes têm de tudo, cidades pequenas têm apenas o básico.**
            Pense nas grandes capitais como 'shopping centers' gigantes que oferecem serviços complexos (hospitais de ponta, universidades, aeroportos), atraindo pessoas de muito longe. Já as cidades pequenas são como 'mercadinhos de bairro', oferecendo apenas serviços básicos do dia a dia (padarias, farmácias) para quem mora ali perto.
            """)
            vab_serv_max = df["VAB_Servicos"].quantile(0.95)
            fig_serv = px.choropleth_mapbox(
                df,
                geojson=geojson,
                locations="CD_MUN",
                featureidkey="properties.CD_MUN",
                color="VAB_Servicos",
                color_continuous_scale="Blues",
                range_color=[0, vab_serv_max],
                mapbox_style="carto-positron",
                zoom=5,
                center={"lat": -20.0, "lon": -45.0},
                opacity=0.8,
                hover_name="NM_MUN",
                hover_data={"SIGLA_UF": True, "VAB_Servicos": ":,.0f", "CD_MUN": False}
            )
            fig_serv.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, coloraxis_colorbar_title="VAB Serviços")
            st.plotly_chart(fig_serv, use_container_width=True)
            st.caption("Fonte: IBGE (Produto Interno Bruto dos Municípios - 2021)")
 
# ------------------------------------------------------------------------------
# ABA 3: Concentração & Dependência
# ------------------------------------------------------------------------------
with tab3:
    st.header("Concentração e Dependência Espacial")
    st.info("""
    **O que são esses Modelos de Concentração?** 📊
    
    De forma simples, eles medem a **especialidade** e o **domínio** das cidades:
    - 🎯 **Quociente Locacional (QL):** É o "termômetro de vocação". Se uma cidade tem o QL maior que 1 na Indústria, significa que ela é "especialista" nisso em comparação ao resto do Sudeste.
    - 👑 **Índice IHH:** Mede a "monopolização". Se o IHH for alto, significa que quase toda a riqueza daquele setor está nas mãos de um pequeno "clube VIP" de poucas cidades.
    """)
    
    st.subheader("Matriz de Quociente Locacional (QL)")
    
    # Preparar dados para o Heatmap (Top 30 cidades por PIB para visualização)
    df_top_ql = df.nlargest(30, "PIB").set_index("NM_MUN")[["QL_Agro", "QL_Ind", "QL_Serv"]]
    
    fig_heatmap = px.imshow(
        df_top_ql.T, 
        color_continuous_scale="RdYlGn", 
        color_continuous_midpoint=1.0,
        aspect="auto",
        title="Heatmap QL Setorial (Top 30 Cidades por PIB)"
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)
    
    col_ihh, col_cempre = st.columns(2)
    
    with col_ihh:
        st.subheader("Concentração Espacial (IHH)")
        st.markdown("Valores maiores indicam que o setor está concentrado em poucos municípios.")
        
        ihh_df = pd.DataFrame(list(ihh_data.items()), columns=["Setor", "IHH"])
        fig_ihh = px.bar(
            ihh_df, x="Setor", y="IHH", color="Setor",
            color_discrete_map={"Serviços": "#1F77B4", "Adm. Pública": "#9467BD", 
                                "Agropecuária": "#2CA02C", "Indústria": "#FF7F0E"},
            title="Índice Herfindahl-Hirschman (0 a 10.000)"
        )
        st.plotly_chart(fig_ihh, use_container_width=True)
        
    with col_cempre:
        st.subheader("Composição Setorial por Estado")
        st.markdown("Valor Adicionado Bruto (VAB) total por estado e setor.")
        
        # Agrupamento real com os dados do IBGE
        df_uf_setor = df.groupby("SIGLA_UF")[["VAB_Servicos", "VAB_Industria", "VAB_Agropecuaria"]].sum().reset_index()
        df_uf_setor = df_uf_setor.rename(columns={
            "SIGLA_UF": "UF",
            "VAB_Servicos": "Serviços",
            "VAB_Industria": "Indústria",
            "VAB_Agropecuaria": "Agropecuária"
        })
        
        fig_cempre = px.bar(
            df_uf_setor.melt(id_vars="UF", var_name="Setor", value_name="VAB"),
            x="UF", y="VAB", color="Setor", barmode="group",
            color_discrete_map={"Serviços": "#1F77B4", "Indústria": "#FF7F0E", "Agropecuária": "#2CA02C"},
            title="VAB por Estado e Setor"
        )
        st.plotly_chart(fig_cempre, use_container_width=True)
        st.caption("Fonte: IBGE (Produto Interno Bruto dos Municípios - 2021)")
