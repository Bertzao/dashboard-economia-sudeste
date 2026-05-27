# -*- coding: utf-8 -*-
"""
============================================================================
MÓDULO 5 — HISTÓRICO COLONIAL E LIMITES TERRITORIAIS
Economia Regional e Urbana — Análise da Região Sudeste do Brasil
============================================================================

Objetivo:
    Analisar a formação histórica das Unidades da Federação da Região Sudeste,
    sua evolução territorial (1872 - 2022) e a "Path Dependence" (dependência 
    de trajetória), cruzando os ciclos econômicos coloniais com a 
    especialização econômica atual (VAB 2021).

Relevância para políticas públicas:
    Entender a origem estrutural da desigualdade inter-regional no Sudeste.
    São Paulo, herdeiro da infraestrutura do Ciclo do Café, consolidou o maior
    VAB industrial e de serviços. Minas Gerais, do Ciclo do Ouro à agropecuária 
    moderna, mantém fortes polos primário-exportadores.
"""

import os
# IMPORTANTE: Definir SHAPE_ENCODING antes de importar geopandas/pyogrio
# para que o GDAL leia os .dbf dos shapefiles históricos sem forçar UTF-8
os.environ['SHAPE_ENCODING'] = ''

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns

import config as cfg
import utils

# ==========================================================================
# 1. BANCO DE DADOS HISTÓRICO (HARDCODED)
# ==========================================================================

def criar_banco_historico():
    """
    Cria um banco de dados estruturado com o perfil colonial das UFs do Sudeste.
    """
    print("\n--- Criando Banco de Dados do Perfil Colonial ---")
    
    dados = [
        {
            "UF": "São Paulo",
            "Capitania_Original": "Capitania de São Vicente (1534)",
            "Ciclo_Colonial": "Bandeirantismo e Subsistência",
            "Ciclo_Imperio_Rep": "Ciclo do Café (Séc. XIX - XX)",
            "Heranca_Infra": "Ferrovias e acumulação de capital (Origem da industrialização)",
            "Path_Dependence": "Polo Industrial e Financeiro"
        },
        {
            "UF": "Minas Gerais",
            "Capitania_Original": "Capitania de São Paulo e Minas de Ouro (1709)",
            "Ciclo_Colonial": "Ciclo do Ouro e Diamantes (Séc. XVIII)",
            "Ciclo_Imperio_Rep": "Agropecuária de Subsistência e Leite",
            "Heranca_Infra": "Urbanização precoce, mercado interno e mineração",
            "Path_Dependence": "Extrativismo Mineral e Agroindústria"
        },
        {
            "UF": "Rio de Janeiro",
            "Capitania_Original": "Capitania de São Vicente (Sul) e São Tomé (1534)",
            "Ciclo_Colonial": "Cana-de-açúcar e Porto (Séc. XVII)",
            "Ciclo_Imperio_Rep": "Capital do Império e Ciclo do Café (Vale do Paraíba)",
            "Heranca_Infra": "Aparelhamento estatal, porto central e serviços burocráticos",
            "Path_Dependence": "Polo de Serviços e Petróleo"
        },
        {
            "UF": "Espírito Santo",
            "Capitania_Original": "Capitania do Espírito Santo (1534)",
            "Ciclo_Colonial": "Cana-de-açúcar (tardia e restrita)",
            "Ciclo_Imperio_Rep": "Expansão do Café",
            "Heranca_Infra": "Portos de exportação isolados",
            "Path_Dependence": "Exportação logística e mineração/siderurgia"
        }
    ]
    
    df_hist = pd.DataFrame(dados)
    print("  ✓ Banco de dados colonial criado com sucesso.")
    return df_hist


# ==========================================================================
# 2. MAPAS — DIVISÕES REGIONAIS HISTÓRICAS DO BRASIL
# ==========================================================================

def _definir_regionalizacoes():
    """
    Define as 4 divisões regionais oficiais do Brasil (1913, 1938, 1942, 1969).
    Mapeia SIGLA_UF → Nome da Região para cada período.
    
    Nota: Para períodos anteriores, estados que não existiam (TO, MS, AP, RO, RR)
    são agrupados na UF-mãe da época (GO, MT, PA, AM).
    """
    
    # ---- 1913 — Delgado de Carvalho (5 regiões) ----
    # SP no "Brasil Meridional", MG/ES/RJ no "Brasil Oriental"
    div_1913 = {
        # Brasil Setentrional (Amazônia)
        "AM": "Brasil Setentrional", "PA": "Brasil Setentrional", "AC": "Brasil Setentrional",
        "AP": "Brasil Setentrional", "RR": "Brasil Setentrional", "RO": "Brasil Setentrional",
        # Brasil Norte-Oriental
        "MA": "Brasil Norte-Oriental", "PI": "Brasil Norte-Oriental",
        "CE": "Brasil Norte-Oriental", "RN": "Brasil Norte-Oriental",
        "PB": "Brasil Norte-Oriental", "PE": "Brasil Norte-Oriental",
        "AL": "Brasil Norte-Oriental",
        # Brasil Central
        "MT": "Brasil Central", "MS": "Brasil Central",
        "GO": "Brasil Central", "TO": "Brasil Central",
        "DF": "Brasil Central",
        # Brasil Oriental (MG, ES, RJ + BA, SE)
        "SE": "Brasil Oriental", "BA": "Brasil Oriental",
        "MG": "Brasil Oriental", "ES": "Brasil Oriental", "RJ": "Brasil Oriental",
        # Brasil Meridional (SP + Sul)
        "SP": "Brasil Meridional", "PR": "Brasil Meridional",
        "SC": "Brasil Meridional", "RS": "Brasil Meridional",
    }
    
    # ---- 1938 — Anuário Estatístico / Min. Agricultura (5 regiões) ----
    # MG no "Centro", ES no "Este", SP/RJ no "Sul"
    div_1938 = {
        # Norte
        "AC": "Norte", "AM": "Norte", "PA": "Norte", "MA": "Norte", "PI": "Norte",
        "AP": "Norte", "RR": "Norte", "RO": "Norte",
        # Nordeste
        "CE": "Nordeste", "RN": "Nordeste", "PB": "Nordeste",
        "PE": "Nordeste", "AL": "Nordeste",
        # Centro (MG + Centro-Oeste)
        "MG": "Centro", "GO": "Centro", "MT": "Centro",
        "TO": "Centro", "MS": "Centro", "DF": "Centro",
        # Este
        "SE": "Este", "BA": "Este", "ES": "Este",
        # Sul (SP, RJ + Sul)
        "RJ": "Sul", "SP": "Sul",
        "PR": "Sul", "SC": "Sul", "RS": "Sul",
    }
    
    # ---- 1942 — 1ª divisão oficial IBGE (7 regiões) ----
    # MG/ES/RJ no "Leste Meridional", SP no "Sul"
    div_1942 = {
        # Norte
        "AM": "Norte", "PA": "Norte", "AC": "Norte",
        "AP": "Norte", "RR": "Norte", "RO": "Norte",
        # Nordeste Ocidental
        "MA": "Nordeste Ocidental", "PI": "Nordeste Ocidental",
        # Nordeste Oriental
        "CE": "Nordeste Oriental", "RN": "Nordeste Oriental",
        "PB": "Nordeste Oriental", "PE": "Nordeste Oriental",
        "AL": "Nordeste Oriental",
        # Leste Setentrional
        "BA": "Leste Setentrional", "SE": "Leste Setentrional",
        # Leste Meridional (MG, ES, RJ)
        "MG": "Leste Meridional", "ES": "Leste Meridional", "RJ": "Leste Meridional",
        # Centro-Oeste
        "GO": "Centro-Oeste", "MT": "Centro-Oeste",
        "TO": "Centro-Oeste", "MS": "Centro-Oeste", "DF": "Centro-Oeste",
        # Sul (SP + Sul)
        "SP": "Sul", "PR": "Sul", "SC": "Sul", "RS": "Sul",
    }
    
    # ---- 1969 — Divisão atual IBGE (5 regiões) ----
    # Primeira vez que SP, MG, ES, RJ ficam juntos no "Sudeste"
    div_1969 = {
        # Norte
        "AC": "Norte", "AM": "Norte", "PA": "Norte",
        "AP": "Norte", "RR": "Norte", "RO": "Norte", "TO": "Norte",
        # Nordeste
        "MA": "Nordeste", "PI": "Nordeste", "CE": "Nordeste",
        "RN": "Nordeste", "PB": "Nordeste", "PE": "Nordeste",
        "AL": "Nordeste", "SE": "Nordeste", "BA": "Nordeste",
        # Centro-Oeste
        "GO": "Centro-Oeste", "MT": "Centro-Oeste",
        "MS": "Centro-Oeste", "DF": "Centro-Oeste",
        # Sudeste (TODOS JUNTOS pela primeira vez!)
        "MG": "Sudeste", "ES": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
        # Sul
        "PR": "Sul", "SC": "Sul", "RS": "Sul",
    }
    
    return {
        "1913": {
            "mapa": div_1913,
            "titulo": "Divisão de 1913\n(Delgado de Carvalho)",
            "subtitulo": "SP = Meridional | MG, ES, RJ = Oriental",
        },
        "1938": {
            "mapa": div_1938,
            "titulo": "Divisão de 1938\n(Anuário Estatístico)",
            "subtitulo": "MG = Centro | ES = Este | SP, RJ = Sul",
        },
        "1942": {
            "mapa": div_1942,
            "titulo": "Divisão de 1942\n(1ª Oficial — IBGE)",
            "subtitulo": "MG, ES, RJ = Leste Meridional | SP = Sul",
        },
        "1969": {
            "mapa": div_1969,
            "titulo": "Divisão de 1969\n(Atual — IBGE)",
            "subtitulo": "SP, MG, ES, RJ = SUDESTE",
        },
    }


def _paleta_regioes():
    """Cores harmônicas para cada nome de região histórica."""
    return {
        # 1913
        "Brasil Setentrional":  "#A5D6A7",  # verde claro
        "Brasil Norte-Oriental": "#FFCC80", # laranja claro
        "Brasil Central":       "#CE93D8",  # roxo claro
        "Brasil Oriental":      "#90CAF9",  # azul claro
        "Brasil Meridional":    "#EF9A9A",  # vermelho claro
        # 1938
        "Norte":                "#A5D6A7",
        "Nordeste":             "#FFCC80",
        "Centro":               "#CE93D8",
        "Este":                 "#80DEEA",  # ciano
        "Sul":                  "#EF9A9A",
        # 1942
        "Nordeste Ocidental":   "#FFE082",  # amarelo
        "Nordeste Oriental":    "#FFCC80",
        "Leste Setentrional":   "#80DEEA",
        "Leste Meridional":     "#90CAF9",
        "Centro-Oeste":         "#CE93D8",
        # 1969
        "Sudeste":              "#64B5F6",  # azul destaque
    }


def mapa_evolucao_limites():
    """
    Gera um painel 2×2 mostrando as 4 divisões regionais oficiais do Brasil
    (1913, 1938, 1942, 1969).
    
    Demonstra como os estados que hoje formam o Sudeste estavam em regiões
    DIFERENTES até 1969: SP era 'Meridional/Sul', enquanto MG/ES/RJ eram
    'Oriental/Leste/Este'. A criação do 'Sudeste' como região unificada
    é um evento relativamente recente na história político-administrativa.
    """
    print("\n--- Mapa: Divisões Regionais Históricas do Brasil ---")
    
    regionalizacoes = _definir_regionalizacoes()
    paleta = _paleta_regioes()
    
    # Carregar o shapefile atual e dissolver por UF
    gdf_br = utils.carregar_municipios_brasil()
    gdf_uf = gdf_br.dissolve(by="SIGLA_UF").reset_index()
    
    # UFs do atual Sudeste (para destaque visual)
    ufs_sudeste = {"SP", "MG", "ES", "RJ"}
    
    fig, axes = plt.subplots(2, 2, figsize=(18, 16))
    axes = axes.flatten()
    
    for i, (ano, info) in enumerate(regionalizacoes.items()):
        ax = axes[i]
        mapa_regioes = info["mapa"]
        
        # Atribuir cor a cada UF conforme sua região no período
        gdf_plot = gdf_uf.copy()
        gdf_plot["Regiao"] = gdf_plot["SIGLA_UF"].map(mapa_regioes).fillna("Outros")
        gdf_plot["Cor"] = gdf_plot["Regiao"].map(paleta).fillna("#E0E0E0")
        
        # Plotar todos os estados
        for _, row in gdf_plot.iterrows():
            sigla = row["SIGLA_UF"]
            is_sudeste = sigla in ufs_sudeste
            
            gpd.GeoDataFrame([row], geometry="geometry", crs=gdf_uf.crs).plot(
                ax=ax,
                color=row["Cor"],
                edgecolor="#333" if is_sudeste else "#999",
                linewidth=1.5 if is_sudeste else 0.5,
            )
        
        # Rótulos — apenas UFs do Sudeste (destaque) + outras com fonte menor
        for _, row in gdf_plot.iterrows():
            c = row.geometry.centroid
            sigla = row["SIGLA_UF"]
            is_sudeste = sigla in ufs_sudeste
            
            if is_sudeste:
                ax.annotate(
                    sigla, xy=(c.x, c.y), ha="center", va="center",
                    fontsize=11, fontweight="bold", color="#1A237E",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.85, ec="#1A237E", lw=0.8),
                )
            else:
                ax.annotate(
                    sigla, xy=(c.x, c.y), ha="center", va="center",
                    fontsize=7, color="#555",
                )
        
        # Legenda com as regiões deste período
        regioes_unicas = sorted(set(mapa_regioes.values()))
        patches = []
        from matplotlib.patches import Patch
        for reg in regioes_unicas:
            cor = paleta.get(reg, "#E0E0E0")
            patches.append(Patch(facecolor=cor, edgecolor="#333", label=reg))
        
        ax.legend(handles=patches, title="Regiões", loc="lower left",
                  fontsize=8, title_fontsize=9, frameon=True, fancybox=True,
                  framealpha=0.9)
        
        ax.set_title(info["titulo"], fontsize=14, fontweight="bold", pad=10)
        
        # Subtítulo com classificação dos estados do Sudeste
        ax.text(0.5, -0.02, info["subtitulo"], transform=ax.transAxes,
                ha="center", va="top", fontsize=10, fontstyle="italic", color="#D32F2F")
        
        ax.set_axis_off()
    
    fig.suptitle(
        "Evolução das Divisões Regionais do Brasil (1913 – 1969)\n"
        "A Região Sudeste só surge como unidade na divisão de 1969",
        fontsize=17, fontweight="bold", y=0.98
    )
    plt.tight_layout(rect=[0, 0.02, 1, 0.94])
    utils.salvar_mapa(fig, "mapa_evolucao_historica", "modulo5")


# ==========================================================================
# 3. PATH DEPENDENCE: HERANÇA COLONIAL VS VAB ATUAL
# ==========================================================================

def grafico_path_dependence(df_hist):
    """
    Cruza o banco de dados histórico com o VAB extraído da planilha oficial
    'PIB dos Municípios - base de dados 2010-2023' (IBGE) para demonstrar
    a "Path Dependence" — como a herança colonial moldou a estrutura
    econômica atual de cada UF do Sudeste.
    """
    print("\n--- Gráfico: Path Dependence (Colônia vs Economia Atual) ---")
    
    # ---- Carregar planilha oficial do IBGE ----
    caminho = cfg.XLS_PIB_MUNICIPIOS
    if not os.path.exists(caminho):
        print(f"  ✗ Planilha não encontrada: {caminho}")
        return
    
    print("  Carregando PIB dos Municípios (IBGE)... (pode levar alguns segundos)")
    df_pib = pd.read_excel(caminho, sheet_name=0)
    
    # Colunas por índice (os nomes têm quebras de linha e acentos complexos)
    COL_ANO      = df_pib.columns[0]   # Ano
    COL_SIGLA_UF = df_pib.columns[4]   # Sigla da Unidade da Federação
    COL_CD_MUN   = df_pib.columns[6]   # Código do Município
    COL_NM_MUN   = df_pib.columns[7]   # Nome do Município
    COL_VAB_AGRO = df_pib.columns[32]  # VAB Agropecuária
    COL_VAB_IND  = df_pib.columns[33]  # VAB Indústria
    COL_VAB_SERV = df_pib.columns[34]  # VAB Serviços (exceto Adm Pública)
    COL_VAB_ADM  = df_pib.columns[35]  # VAB Administração Pública
    COL_VAB_TOT  = df_pib.columns[36]  # VAB Total
    
    # Usar o ano mais recente com VAB preenchido (2022/2023 não têm VAB)
    anos_com_vab = df_pib.dropna(subset=[COL_VAB_AGRO])[COL_ANO].unique()
    ano_ref = int(max(anos_com_vab))
    print(f"  Ano de referência (mais recente com VAB): {ano_ref}")
    
    # Filtrar: Sudeste + ano de referência
    mask = (df_pib[COL_SIGLA_UF].isin(["SP", "MG", "RJ", "ES"])) & (df_pib[COL_ANO] == ano_ref)
    df_se = df_pib[mask].copy()
    print(f"  Municípios Sudeste ({ano_ref}): {len(df_se)}")
    
    # Agregar VAB por UF
    df_uf = df_se.groupby(COL_SIGLA_UF).agg({
        COL_VAB_AGRO: "sum",
        COL_VAB_IND:  "sum",
        COL_VAB_SERV: "sum",
        COL_VAB_ADM:  "sum",
        COL_VAB_TOT:  "sum",
    }).reset_index()
    
    # Renomear para nomes curtos
    df_uf = df_uf.rename(columns={
        COL_SIGLA_UF: "SIGLA_UF",
        COL_VAB_AGRO: "VAB_Agro",
        COL_VAB_IND:  "VAB_Ind",
        COL_VAB_SERV: "VAB_Serv",
        COL_VAB_ADM:  "VAB_Adm",
        COL_VAB_TOT:  "VAB_Total",
    })
    
    # Traduzir Sigla para Nome completo
    sigla_nome = {s: cfg.NOMES_UF[cfg.UFS_SUDESTE[s]] for s in cfg.SIGLAS_SUDESTE}
    df_uf["UF"] = df_uf["SIGLA_UF"].map(sigla_nome)
    
    # Merge com banco histórico colonial
    df_merged = pd.merge(df_hist, df_uf, on="UF", how="inner")
    
    # Calcular percentuais setoriais
    df_merged["Perc_Ind"]  = (df_merged["VAB_Ind"]  / df_merged["VAB_Total"]) * 100
    df_merged["Perc_Serv"] = (df_merged["VAB_Serv"] / df_merged["VAB_Total"]) * 100
    df_merged["Perc_Agro"] = (df_merged["VAB_Agro"] / df_merged["VAB_Total"]) * 100
    df_merged["Perc_Adm"]  = (df_merged["VAB_Adm"]  / df_merged["VAB_Total"]) * 100
    
    # Ordenar por VAB Total descendente
    df_merged = df_merged.sort_values(by="VAB_Total", ascending=False)
    
    # ---- Gráficos ----
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    
    # Gráfico 1: VAB Total Absoluto
    sns.barplot(data=df_merged, x="UF", y="VAB_Total", ax=axes[0],
                palette="viridis", legend=False, hue="UF")
    axes[0].set_title(f"VAB Total por UF ({ano_ref}) — Reflexo do Ciclo do Café",
                      fontsize=14, fontweight="bold")
    axes[0].set_ylabel("VAB Total (R$ Mil)")
    axes[0].set_xlabel("")
    
    # Anotação do Ciclo Imperial/Republicano
    for i, row in df_merged.reset_index().iterrows():
        ciclo = row["Ciclo_Imperio_Rep"]
        axes[0].text(i, row["VAB_Total"] * 0.5, ciclo.replace(" ", "\n", 3),
                     ha="center", va="center", color="white", fontsize=10, fontweight="bold")

    # Gráfico 2: Composição Setorial (%)
    df_perc = df_merged[["UF", "Perc_Agro", "Perc_Ind", "Perc_Serv", "Perc_Adm"]].set_index("UF")
    df_perc.plot(kind="bar", stacked=True, ax=axes[1],
                 color=["#81C784", "#E57373", "#64B5F6", "#BA68C8"])
    
    axes[1].set_title(f"Estrutura Setorial ({ano_ref}) — Path Dependence",
                      fontsize=14, fontweight="bold")
    axes[1].set_ylabel("% do VAB Total")
    axes[1].set_xlabel("")
    axes[1].legend(["Agropecuária", "Indústria", "Serviços", "Adm. Pública"],
                   title="Setores", fontsize=9)
    axes[1].set_ylim(0, 115)
    
    # Anotação da Herança Infra no gráfico 2
    for i, row in df_merged.reset_index().iterrows():
        heranca = row["Heranca_Infra"]
        axes[1].text(i, 105, heranca.replace(" ", "\n", 4),
                     ha="center", va="bottom", fontsize=7, color="#555", rotation=45)

    sns.despine()
    plt.tight_layout()
    utils.salvar_mapa(fig, "grafico_path_dependence", "modulo5")
    
    # Salvar tabela em CSV
    caminho_csv = os.path.join(cfg.OUTPUT_DIR, "modulo5", "tabela_colonial_vab.csv")
    df_merged.to_csv(caminho_csv, index=False, encoding="utf-8")
    print(f"  ✓ Tabela histórica salva em {caminho_csv}")

# ==========================================================================
# 4. EMPRESAS (CEMPRE) POR SETORES
# ==========================================================================

def grafico_empresas_setores():
    """
    Gera um gráfico do número de empresas/unidades locais por área:
    Agropecuária, Indústria, Serviços e Administração Pública.
    Usa os dados do Cadastro Central de Empresas (CEMPRE).
    """
    print("\n--- Gráfico: Número de Empresas por Setores (CEMPRE) ---")
    
    caminho = cfg.XLS_EMPRESAS
    if not os.path.exists(caminho):
        print(f"  ✗ Planilha não encontrada: {caminho}")
        return
        
    print("  Carregando dados do CEMPRE...")
    # Lendo pulando as 4 primeiras linhas de cabeçalho
    df = pd.read_excel(caminho, skiprows=4)
    
    # A primeira coluna (Unnamed: 0) tem os nomes dos Estados
    df = df.rename(columns={df.columns[0]: "UF"})
    
    # Filtrar apenas os estados do Sudeste
    ufs_sudeste = ["São Paulo", "Rio de Janeiro", "Minas Gerais", "Espírito Santo"]
    df_se = df[df["UF"].isin(ufs_sudeste)].copy()
    
    if df_se.empty:
        print("  ✗ Nenhum dado do Sudeste encontrado na tabela.")
        return
        
    # Limpar dados (substituir '-' ou '...' por 0)
    for col in df_se.columns[2:]:
        df_se[col] = pd.to_numeric(df_se[col].replace(["-", "...", ".."], 0), errors="coerce").fillna(0)
        
    # Mapear as colunas pelas suas posições (CNAE seções)
    # 3: A (Agropecuária)
    # 4 a 8: B, C, D, E, F (Indústria e Construção)
    # 9 a 16 e 18 a 23: Serviços
    # 17: O (Administração Pública)
    col_agro = df_se.columns[3]
    cols_ind = df_se.columns[4:9]
    cols_serv = list(df_se.columns[9:17]) + list(df_se.columns[18:24])
    col_adm = df_se.columns[17]
    
    df_se["Agropecuária"] = df_se[col_agro]
    df_se["Indústria"] = df_se[cols_ind].sum(axis=1)
    df_se["Serviços"] = df_se[cols_serv].sum(axis=1)
    df_se["Adm. Pública"] = df_se[col_adm]
    
    # Derreter para formato longo (seaborn hue)
    df_long = df_se.melt(id_vars="UF", 
                         value_vars=["Agropecuária", "Indústria", "Serviços", "Adm. Pública"],
                         var_name="Setor", value_name="Num_Empresas")
                         
    # Ordenar UFs por total de empresas (opcional) para melhor visualização
    # SP, MG, RJ, ES
    ordem_uf = ["São Paulo", "Minas Gerais", "Rio de Janeiro", "Espírito Santo"]
    
    # Configurar gráfico
    fig, ax = plt.subplots(figsize=(14, 7))
    
    cores = ["#4CAF50", "#FF5722", "#2196F3", "#9C27B0"] # Cores padrão dos setores no projeto
    sns.barplot(data=df_long, x="UF", y="Num_Empresas", hue="Setor", 
                ax=ax, palette=cores, order=ordem_uf, 
                edgecolor="white", linewidth=1.2)
                
    # Adicionar os rótulos de dados
    for p in ax.patches:
        height = p.get_height()
        if height > 0:
            ax.annotate(f"{int(height):,}".replace(",", "."), 
                        (p.get_x() + p.get_width() / 2., height),
                        ha="center", va="bottom", fontsize=8, color="#333", 
                        xytext=(0, 4), textcoords="offset points", fontweight="bold", rotation=45)
                        
    ax.set_title("Número de Empresas/Unidades Locais por Setor (CEMPRE)", 
                 fontsize=15, fontweight="bold", pad=15)
    ax.set_ylabel("Quantidade de Empresas", fontsize=11, fontweight="bold")
    ax.set_xlabel("")
    
    # Formatar eixo Y para milhares (K)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: f"{int(x/1000)}k" if x >= 1000 else f"{int(x)}"))
    
    ax.legend(title="Setores", fontsize=10, title_fontsize=11)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    
    sns.despine(left=True)
    
    # Adicionando a fonte para trabalho acadêmico
    fig.text(0.5, 0.01, "Fonte: IBGE - Cadastro Central de Empresas (CEMPRE)", 
             ha="center", va="center", fontsize=9, fontstyle="italic", color="#555555")
             
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    utils.salvar_mapa(fig, "grafico_empresas_setores_cempre", "modulo5")
    print("  ✓ Gráfico de empresas gerado com sucesso.")


# ==========================================================================
# EXECUÇÃO PRINCIPAL
# ==========================================================================

def executar_modulo5():
    """Executa o módulo 5."""
    print("\n" + "=" * 60)
    print("MÓDULO 5 — HISTÓRICO COLONIAL E LIMITES TERRITORIAIS")
    print("=" * 60)
    
    # Garantir que a pasta exista
    os.makedirs(os.path.join(cfg.OUTPUT_DIR, "modulo5"), exist_ok=True)
    
    mapa_evolucao_limites()
    
    df_hist = criar_banco_historico()
    grafico_path_dependence(df_hist)
    grafico_empresas_setores()
    
    print("\n✓ Módulo 5 concluído! Saídas salvas em output/modulo5/")

if __name__ == "__main__":
    executar_modulo5()
