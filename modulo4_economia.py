# -*- coding: utf-8 -*-
"""
============================================================================
MÓDULO 4 — ATIVIDADE ECONÔMICA E MODELOS CLÁSSICOS DE LOCALIZAÇÃO
Economia Regional e Urbana — Região Sudeste do Brasil
============================================================================
Core do projeto: processa dados de VAB municipal (API SIDRA), calcula
métricas de concentração (QL, IHH) e gera mapas à luz dos modelos de
Von Thünen, Weber, Christaller e Lösch.
"""

import os, json, time
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import seaborn as sns
import requests

import config as cfg
import utils


# ==========================================================================
# 1. DOWNLOAD DE VAB MUNICIPAL VIA API SIDRA
# ==========================================================================

def carregar_vab_municipal():
    """
    Carrega dados de VAB municipal a partir da planilha oficial do IBGE
    (PIB dos Municípios - base de dados 2010-2023.xlsx), substituindo
    a instabilidade da API SIDRA.
    """
    print("\n--- Carregando VAB Municipal (Planilha IBGE) ---")
    caminho = cfg.XLS_PIB_MUNICIPIOS
    
    if not os.path.exists(caminho):
        print(f"  ✗ Planilha não encontrada: {caminho}")
        return None
        
    print("  Processando arquivo Excel... (pode levar alguns segundos)")
    df_pib = pd.read_excel(caminho, sheet_name=0)
    
    # Mapeando colunas por índice para evitar problemas com strings longas/acentos
    COL_ANO      = df_pib.columns[0]
    COL_SIGLA_UF = df_pib.columns[4]
    COL_CD_MUN   = df_pib.columns[6]
    COL_NM_MUN   = df_pib.columns[7]
    COL_VAB_AGRO = df_pib.columns[32]
    COL_VAB_IND  = df_pib.columns[33]
    COL_VAB_SERV = df_pib.columns[34]
    COL_VAB_ADM  = df_pib.columns[35]
    COL_PIB      = df_pib.columns[38] # Produto Interno Bruto a preços correntes
    
    # Buscar o ano mais recente com dados de VAB preenchidos
    anos_com_vab = df_pib.dropna(subset=[COL_VAB_AGRO])[COL_ANO].unique()
    ano_ref = int(max(anos_com_vab))
    print(f"  Ano de referência: {ano_ref}")
    
    # Filtrar apenas Sudeste e ano de referência
    mask = (df_pib[COL_SIGLA_UF].isin(["SP", "MG", "RJ", "ES"])) & (df_pib[COL_ANO] == ano_ref)
    df_se = df_pib[mask].copy()
    
    # Renomear para o padrão esperado no Módulo 4
    df_se = df_se.rename(columns={
        COL_CD_MUN: "CD_MUN",
        COL_NM_MUN: "NM_MUN",
        COL_ANO: "Ano",
        COL_VAB_AGRO: "VAB_Agropecuaria",
        COL_VAB_IND:  "VAB_Industria",
        COL_VAB_SERV: "VAB_Servicos",
        COL_VAB_ADM:  "VAB_Adm_Publica",
        COL_PIB:      "PIB"
    })
    
    df_se["CD_MUN"] = df_se["CD_MUN"].astype(str)
    
    # Preencher NaN com 0
    cols_vab = ["VAB_Agropecuaria", "VAB_Industria", "VAB_Servicos", "VAB_Adm_Publica", "PIB"]
    for c in cols_vab:
        df_se[c] = pd.to_numeric(df_se[c], errors="coerce").fillna(0)
        
    print(f"  ✓ {len(df_se)} municípios carregados com VAB")
    return df_se


# ==========================================================================
# 2. PROCESSAMENTO DE TABELAS SIDRA (UF)
# ==========================================================================

def carregar_pia():
    """Carrega Tabela 1849 — PIA (unidades industriais por UF)."""
    print("\n--- Carregando PIA (Tabela 1849) ---")
    df = utils.carregar_tabela_sidra(cfg.XLS_PIA, skiprows=5, nome="PIA")
    if df is None:
        return None
    # Coluna 0 = UF, colunas 1+ = anos (2007..2023), valor = Total
    df.columns = ["UF"] + [f"Ind_{2007+i}" for i in range(len(df.columns)-1)]
    return utils.filtrar_sudeste_uf(df, 0)


def carregar_pam():
    """Carrega Tabela 5457 — PAM (área plantada por UF)."""
    print("\n--- Carregando PAM (Tabela 5457) ---")
    df = utils.carregar_tabela_sidra(cfg.XLS_PAM, skiprows=5, nome="PAM")
    if df is None:
        return None
    df.columns = ["UF"] + [f"Agri_{1974+i}" for i in range(len(df.columns)-1)]
    return utils.filtrar_sudeste_uf(df, 0)


def carregar_pas():
    """Carrega Tabela 3940 — PAS (empresas de serviços por UF)."""
    print("\n--- Carregando PAS (Tabela 3940) ---")
    df = utils.carregar_tabela_sidra(cfg.XLS_PAS, skiprows=5, nome="PAS")
    if df is None:
        return None
    df.columns = ["UF"] + [f"Serv_{2007+i}" for i in range(len(df.columns)-1)]
    return utils.filtrar_sudeste_uf(df, 0)


# ==========================================================================
# 3. CÁLCULO DE MÉTRICAS DE CONCENTRAÇÃO
# ==========================================================================

def calcular_quociente_locacional(df_vab):
    """
    Calcula o Quociente Locacional (QL) para cada setor em cada município.

    QL = (VAB_setor_i_mun_j / VAB_total_mun_j) /
         (VAB_setor_i_regiao / VAB_total_regiao)

    Interpretação:
      QL > 1 → município é ESPECIALIZADO no setor (potencial APL)
      QL = 1 → participação proporcional à média regional
      QL < 1 → município NÃO é especializado no setor

    Relevância para políticas públicas:
      O QL identifica vocações produtivas locais, subsidiando a
      criação de Arranjos Produtivos Locais (APLs) e políticas de
      desenvolvimento endógeno. Municípios com QL alto em indústria
      são candidatos a clusters industriais (Weber).
    """
    print("\n--- Calculando Quociente Locacional (QL) ---")

    if df_vab is None or len(df_vab) == 0:
        return None

    setores = ["VAB_Agropecuaria", "VAB_Industria", "VAB_Servicos", "VAB_Adm_Publica"]
    setores_disp = [s for s in setores if s in df_vab.columns]

    if not setores_disp:
        print("  ✗ Colunas de VAB não encontradas")
        return None

    df = df_vab.copy()

    # VAB total do município
    df["VAB_Total"] = df[setores_disp].sum(axis=1)

    # Totais regionais
    totais_regiao = {s: df[s].sum() for s in setores_disp}
    vab_total_regiao = df["VAB_Total"].sum()

    # Calcular QL para cada setor
    for setor in setores_disp:
        part_mun = df[setor] / df["VAB_Total"]
        part_regiao = totais_regiao[setor] / vab_total_regiao
        df[f"QL_{setor}"] = (part_mun / part_regiao).replace(
            [np.inf, -np.inf], np.nan
        ).round(4)

    print(f"  ✓ QL calculado para {len(setores_disp)} setores, {len(df)} municípios")
    return df


def calcular_ihh(df_vab, setor="VAB_Industria"):
    """
    Calcula o Índice de Hirschman-Herfindahl (IHH) para um setor.

    IHH = Σ (s_i)²  onde s_i = participação do município i no setor

    Interpretação:
      IHH próximo de 0 → setor desconcentrado (muitos municípios)
      IHH próximo de 1 → setor altamente concentrado (poucos municípios dominam)

    Relevância:
      O IHH mede o grau de concentração espacial da atividade econômica.
      Alto IHH industrial sugere economias de aglomeração (Marshall/Weber).
      Políticas de desconcentração produtiva visam reduzir o IHH.
    """
    print(f"\n--- Calculando IHH para {setor} ---")

    if df_vab is None or setor not in df_vab.columns:
        return None

    total_setor = df_vab[setor].sum()
    if total_setor == 0:
        return 0

    participacoes = df_vab[setor] / total_setor
    # Multiplicar por 100 antes de elevar ao quadrado converte a escala para 0 a 10.000 (padrão IHH)
    ihh = ((participacoes * 100) ** 2).sum()

    print(f"  ✓ IHH ({setor}): {ihh:.2f}")
    return ihh


# ==========================================================================
# 4. MAPAS — MODELOS CLÁSSICOS
# ==========================================================================

def mapa_von_thunen(gdf_sudeste, df_vab):
    """
    Mapa de Von Thünen: distribuição do VAB Agropecuário.

    O modelo de Von Thünen prevê que o uso do solo agrícola se organiza
    em anéis concêntricos ao redor do mercado central:
    - Anel 1 (próximo): horticultura, leite — perecíveis
    - Anel 2: cereais, grãos
    - Anel 3: pecuária extensiva
    - Anel 4: floresta/extrativismo

    São Paulo (maior mercado consumidor) funciona como o "centro"
    do modelo. Municípios próximos a SP tendem a ter agricultura
    intensiva; distantes, agricultura extensiva.
    """
    print("\n--- Mapa: Von Thünen (VAB Agropecuário) ---")

    if df_vab is None or "VAB_Agropecuaria" not in df_vab.columns:
        print("  ✗ Dados de VAB Agropecuário não disponíveis")
        return

    gdf = gdf_sudeste.merge(df_vab[["CD_MUN", "VAB_Agropecuaria"]],
                             on="CD_MUN", how="left")

    fig, ax = utils.criar_figura_mapa(figsize=(15, 11))

    gdf.plot(
        column="VAB_Agropecuaria", ax=ax,
        cmap=cfg.CMAP_SETORIAL["agropecuaria"],
        scheme="quantiles", k=7,
        edgecolor="#CCC", linewidth=0.05,
        missing_kwds={"color": "#F5F5F5", "edgecolor": "#CCC", "linewidth": 0.05},
        legend=True,
        legend_kwds={"title": "VAB Agropecuário\n(Mil R$)", "loc": "lower left",
                     "fontsize": 7, "title_fontsize": 8, "framealpha": 0.9},
    )

    # Limites estaduais
    gdf_sudeste.dissolve(by="SIGLA_UF").boundary.plot(
        ax=ax, color="#333", linewidth=1.2
    )

    # Marcar São Paulo como "centro de mercado" (Von Thünen)
    sp_centroid = gdf_sudeste[gdf_sudeste["NM_MUN"] == "São Paulo"]
    if len(sp_centroid) > 0:
        c = sp_centroid.geometry.values[0].centroid
        ax.plot(c.x, c.y, marker="*", color="#E91E63", markersize=18, zorder=10)
        ax.annotate("São Paulo\n(Centro de\nMercado)", xy=(c.x, c.y),
                     xytext=(c.x + 1.5, c.y + 1),
                     fontsize=9, fontweight="bold", color="#E91E63",
                     arrowprops=dict(arrowstyle="->", color="#E91E63"))

    utils.adicionar_rotulos_uf(ax, gdf_sudeste)
    utils.formatar_eixos_mapa(
        ax, titulo="Modelo de Von Thünen — VAB Agropecuário Municipal\n"
                   "Anéis de uso do solo: intensivo (próximo ao mercado) → extensivo (distante)"
    )
    utils.salvar_mapa(fig, "mapa_von_thunen_agropecuario", "modulo4")


def mapa_weber(gdf_sudeste, df_vab):
    """
    Mapa de Weber: distribuição do VAB Industrial.

    O modelo de Weber prevê que a localização industrial ótima minimiza
    os custos de transporte, considerando:
    - Proximidade às fontes de matéria-prima
    - Proximidade ao mercado consumidor
    - Disponibilidade de mão-de-obra

    Municípios com alto VAB industrial no Sudeste tendem a se concentrar
    ao longo dos eixos rodoviários (Via Dutra SP-RJ, BR-381 SP-BH),
    confirmando a hipótese weberiana de minimização de custo de transporte.
    """
    print("\n--- Mapa: Weber (VAB Industrial) ---")

    if df_vab is None or "VAB_Industria" not in df_vab.columns:
        print("  ✗ Dados de VAB Industrial não disponíveis")
        return

    gdf = gdf_sudeste.merge(df_vab[["CD_MUN", "VAB_Industria"]],
                             on="CD_MUN", how="left")

    fig, ax = utils.criar_figura_mapa(figsize=(15, 11))

    gdf.plot(
        column="VAB_Industria", ax=ax,
        cmap=cfg.CMAP_SETORIAL["industria"],
        scheme="quantiles", k=7,
        edgecolor="#CCC", linewidth=0.05,
        missing_kwds={"color": "#F5F5F5", "edgecolor": "#CCC", "linewidth": 0.05},
        legend=True,
        legend_kwds={"title": "VAB Indústria\n(Mil R$)", "loc": "lower left",
                     "fontsize": 7, "title_fontsize": 8, "framealpha": 0.9},
    )

    gdf_sudeste.dissolve(by="SIGLA_UF").boundary.plot(
        ax=ax, color="#333", linewidth=1.2
    )

    utils.adicionar_rotulos_uf(ax, gdf_sudeste)
    utils.formatar_eixos_mapa(
        ax, titulo="Modelo de Weber — VAB Industrial Municipal\n"
                   "Concentração ao longo dos corredores logísticos (minimização de custo de transporte)"
    )
    utils.salvar_mapa(fig, "mapa_weber_industrial", "modulo4")


def mapa_christaller(gdf_sudeste, df_vab):
    """
    Mapa de Christaller: Lugares Centrais (VAB Serviços).

    O modelo de Christaller prevê uma hierarquia de centros urbanos
    baseada na oferta de bens e serviços:
    - Nível 1: Metrópoles (SP, RJ, BH) — serviços de alta complexidade
    - Nível 2: Capitais regionais (Campinas, Vitória)
    - Nível 3: Centros sub-regionais (Ribeirão Preto, Juiz de Fora)
    - Nível 4: Centros locais

    O VAB de Serviços é proxy direta para essa hierarquia: quanto
    maior, mais serviços complexos o município oferece.
    """
    print("\n--- Mapa: Christaller (Lugares Centrais — VAB Serviços) ---")

    if df_vab is None or "VAB_Servicos" not in df_vab.columns:
        print("  ✗ Dados de VAB Serviços não disponíveis")
        return

    gdf = gdf_sudeste.merge(df_vab[["CD_MUN", "VAB_Servicos"]],
                             on="CD_MUN", how="left")

    fig, ax = utils.criar_figura_mapa(figsize=(15, 11))

    gdf.plot(
        column="VAB_Servicos", ax=ax,
        cmap=cfg.CMAP_SETORIAL["servicos"],
        scheme="quantiles", k=7,
        edgecolor="#CCC", linewidth=0.05,
        missing_kwds={"color": "#F5F5F5", "edgecolor": "#CCC", "linewidth": 0.05},
        legend=True,
        legend_kwds={"title": "VAB Serviços\n(Mil R$)", "loc": "lower left",
                     "fontsize": 7, "title_fontsize": 8, "framealpha": 0.9},
    )

    gdf_sudeste.dissolve(by="SIGLA_UF").boundary.plot(
        ax=ax, color="#333", linewidth=1.2
    )

    # Destacar top 10 municípios (Lugares Centrais de maior ordem)
    top10 = gdf.nlargest(10, "VAB_Servicos")
    for _, row in top10.iterrows():
        c = row.geometry.centroid
        ax.plot(c.x, c.y, "o", color="#E91E63", markersize=8, zorder=10)
        ax.annotate(row["NM_MUN"], xy=(c.x, c.y), xytext=(5, 5),
                     textcoords="offset points", fontsize=6,
                     fontweight="bold", color="#333",
                     bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7))

    utils.adicionar_rotulos_uf(ax, gdf_sudeste)
    utils.formatar_eixos_mapa(
        ax, titulo="Modelo de Christaller — Lugares Centrais (VAB Serviços)\n"
                   "Top 10 centros marcados: hierarquia urbana por oferta de serviços"
    )
    utils.salvar_mapa(fig, "mapa_christaller_servicos", "modulo4")


def heatmap_ql_setorial(df_vab):
    """
    Gera heatmap do Quociente Locacional por setor × top municípios.

    Permite identificar visualmente quais municípios são especializados
    em quais setores — base empírica para a discussão de APLs.
    """
    print("\n--- Heatmap: QL Setorial ---")

    if df_vab is None:
        return

    cols_ql = [c for c in df_vab.columns if c.startswith("QL_")]
    if not cols_ql:
        print("  ✗ Colunas de QL não encontradas")
        return

    # Top 30 municípios por PIB
    if "PIB" in df_vab.columns:
        top = df_vab.nlargest(30, "PIB").copy()
    else:
        top = df_vab.nlargest(30, "VAB_Total").copy()

    top = top.set_index("NM_MUN")[cols_ql]
    top.columns = [c.replace("QL_VAB_", "").replace("_", " ") for c in top.columns]

    fig, ax = plt.subplots(figsize=(10, 12))

    sns.heatmap(
        top, ax=ax, cmap="RdYlGn", center=1, annot=True,
        fmt=".2f", linewidths=0.5, linecolor="#EEE",
        cbar_kws={"label": "Quociente Locacional (QL)", "shrink": 0.8},
    )

    ax.set_title("Quociente Locacional por Setor — Top 30 Municípios (PIB)\n"
                 "QL > 1 (verde) = especializado | QL < 1 (vermelho) = não especializado",
                 fontsize=12, fontweight="bold")
    ax.set_ylabel("")
    ax.tick_params(labelsize=8)

    plt.tight_layout()
    utils.salvar_mapa(fig, "heatmap_ql_setorial", "modulo4")


def grafico_ihh_setores(df_vab):
    """
    Gera gráfico de barras do IHH por setor econômico, permitindo
    comparar o grau de concentração espacial entre agropecuária,
    indústria e serviços.
    """
    print("\n--- Gráfico: IHH por Setor ---")

    if df_vab is None:
        return

    setores = {
        "Agropecuária": "VAB_Agropecuaria",
        "Indústria": "VAB_Industria",
        "Serviços": "VAB_Servicos",
        "Adm. Pública": "VAB_Adm_Publica",
    }

    ihhs = {}
    for nome, col in setores.items():
        if col in df_vab.columns:
            ihhs[nome] = calcular_ihh(df_vab, col)

    if not ihhs:
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    cores = ["#4CAF50", "#FF5722", "#2196F3", "#9C27B0"]
    bars = ax.bar(ihhs.keys(), ihhs.values(), color=cores[:len(ihhs)],
                   edgecolor="white", linewidth=1.5)

    max_val = max(ihhs.values()) if ihhs else 1
    for bar, val in zip(bars, ihhs.values()):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + (max_val * 0.015),
                f"{val:.0f}", ha="center", va="bottom", fontsize=11, fontweight="bold")

    ax.set_ylabel("IHH (Índice de Hirschman-Herfindahl)", fontsize=12)
    ax.set_title("Concentração Espacial por Setor — Sudeste\n"
                 "IHH alto → concentrado | IHH baixo → desconcentrado",
                 fontsize=13, fontweight="bold")
    ax.set_facecolor("#F5F5F5")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    utils.salvar_mapa(fig, "grafico_ihh_setores", "modulo4")


def mapa_especializacao_municipal(gdf_sudeste, df_vab):
    """
    Mapa temático: setor dominante em cada município.

    Identifica a vocação econômica predominante de cada município
    (agropecuária, indústria, serviços ou administração pública),
    colorindo-os de acordo. Permite visualizar a distribuição espacial
    das atividades — base para discussão de Lösch (áreas de mercado).
    """
    print("\n--- Mapa: Especialização Municipal ---")

    if df_vab is None:
        return

    setores = ["VAB_Agropecuaria", "VAB_Industria", "VAB_Servicos", "VAB_Adm_Publica"]
    setores_disp = [s for s in setores if s in df_vab.columns]

    if not setores_disp:
        return

    df = df_vab.copy()
    df["Setor_Dominante"] = df[setores_disp].idxmax(axis=1)
    df["Setor_Dominante"] = df["Setor_Dominante"].map({
        "VAB_Agropecuaria": "Agropecuária",
        "VAB_Industria": "Indústria",
        "VAB_Servicos": "Serviços",
        "VAB_Adm_Publica": "Adm. Pública",
    })

    gdf = gdf_sudeste.merge(df[["CD_MUN", "Setor_Dominante"]], on="CD_MUN", how="left")

    fig, ax = utils.criar_figura_mapa(figsize=(15, 11))

    cores_setor = {
        "Agropecuária": "#4CAF50",
        "Indústria": "#FF5722",
        "Serviços": "#2196F3",
        "Adm. Pública": "#9C27B0",
    }

    for setor, cor in cores_setor.items():
        subset = gdf[gdf["Setor_Dominante"] == setor]
        if len(subset) > 0:
            subset.plot(ax=ax, color=cor, edgecolor="#CCC", linewidth=0.05, alpha=0.8)

    # Sem classificação
    sem = gdf[gdf["Setor_Dominante"].isna()]
    if len(sem) > 0:
        sem.plot(ax=ax, color="#EEEEEE", edgecolor="#CCC", linewidth=0.05)

    gdf_sudeste.dissolve(by="SIGLA_UF").boundary.plot(ax=ax, color="#333", linewidth=1.2)
    utils.adicionar_rotulos_uf(ax, gdf_sudeste)

    legend_handles = [Patch(facecolor=c, label=s, edgecolor="#333")
                      for s, c in cores_setor.items()]
    ax.legend(handles=legend_handles, title="Setor Dominante (VAB)",
              loc="lower left", fontsize=9, title_fontsize=10,
              frameon=True, fancybox=True, shadow=True, framealpha=0.9)

    # Contagem
    contagem = gdf["Setor_Dominante"].value_counts()
    texto = " | ".join([f"{s}: {n}" for s, n in contagem.items()])

    utils.formatar_eixos_mapa(
        ax, titulo="Vocação Econômica Municipal — Setor Dominante (VAB)\n"
                   f"{texto}"
    )
    utils.salvar_mapa(fig, "mapa_especializacao_municipal", "modulo4")


# ==========================================================================
# EXECUÇÃO PRINCIPAL
# ==========================================================================

def executar_modulo4(gdf_sudeste=None):
    """Executa todas as análises e mapas do Módulo 4."""
    print("\n" + "=" * 60)
    print("MÓDULO 4 — ATIVIDADE ECONÔMICA E MODELOS CLÁSSICOS")
    print("=" * 60)

    if gdf_sudeste is None:
        gdf_sudeste = utils.carregar_municipios_sudeste()
        gdf_sudeste["CD_MUN"] = gdf_sudeste["CD_MUN"].astype(str)

    # 1. Carregar VAB municipal da planilha
    df_vab = carregar_vab_municipal()

    if df_vab is not None:
        # 2. Calcular métricas
        df_vab = calcular_quociente_locacional(df_vab)

        # 3. Gerar mapas dos modelos clássicos
        mapa_von_thunen(gdf_sudeste, df_vab)
        mapa_weber(gdf_sudeste, df_vab)
        mapa_christaller(gdf_sudeste, df_vab)
        mapa_especializacao_municipal(gdf_sudeste, df_vab)

        # 4. Gráficos de concentração
        heatmap_ql_setorial(df_vab)
        grafico_ihh_setores(df_vab)

    print("\n✓ Módulo 4 concluído! Mapas salvos em output/modulo4/")


if __name__ == "__main__":
    executar_modulo4()
