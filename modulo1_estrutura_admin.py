# -*- coding: utf-8 -*-
"""
============================================================================
MÓDULO 1 — APRESENTAÇÃO DA REGIÃO E ESTRUTURA POLÍTICO-ADMINISTRATIVA
Economia Regional e Urbana — Análise da Região Sudeste do Brasil
============================================================================

Objetivo:
    Apresentar a região Sudeste do Brasil, sua composição político-
    -administrativa (4 UFs, ~1.668 municípios), e a hierarquia territorial
    definida pelo IBGE (Regiões Geográficas Intermediárias e Imediatas).

Relevância para políticas públicas:
    A compreensão da estrutura administrativa é pré-requisito para a
    formulação de políticas de desenvolvimento regional. A análise da
    heterogeneidade territorial (municípios com áreas de 3 km² a 40.000 km²)
    evidencia a necessidade de estratégias diferenciadas por porte.

Fontes:
    - IBGE, Malha Municipal 2025 (Shapefile BR_Municipios_2025.shp)
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

import config as cfg
import utils


# ==========================================================================
# 1. CARREGAMENTO DE DADOS
# ==========================================================================

def carregar_dados():
    """
    Carrega e prepara o GeoDataFrame dos municípios da região Sudeste.

    Returns
    -------
    gdf_sudeste : geopandas.GeoDataFrame
        Municípios do Sudeste com geometrias válidas.
    """
    print("\n" + "=" * 60)
    print("MÓDULO 1 — ESTRUTURA POLÍTICO-ADMINISTRATIVA")
    print("=" * 60)

    gdf = utils.carregar_municipios_sudeste()

    # Garantir tipos corretos para joins futuros
    gdf["CD_MUN"] = gdf["CD_MUN"].astype(str)
    gdf["CD_UF"] = gdf["CD_UF"].astype(str)
    gdf["AREA_KM2"] = pd.to_numeric(gdf["AREA_KM2"], errors="coerce")

    return gdf


# ==========================================================================
# 2. ESTATÍSTICAS DESCRITIVAS
# ==========================================================================

def gerar_estatisticas(gdf):
    """
    Gera um resumo estatístico da região Sudeste por UF.

    Essas estatísticas são fundamentais para contextualizar a análise:
    - Número de municípios indica a fragmentação administrativa
    - Área total e média revelam a heterogeneidade territorial
    - O desvio-padrão da área evidencia a desigualdade no recorte municipal
      (relevante para Christaller — municípios maiores tendem a ser menos centrais)

    Returns
    -------
    pandas.DataFrame
        Tabela resumo com métricas por UF.
    """
    print("\n--- Estatísticas Descritivas ---")

    stats = gdf.groupby("SIGLA_UF").agg(
        Municipios=("CD_MUN", "count"),
        Area_Total_km2=("AREA_KM2", "sum"),
        Area_Media_km2=("AREA_KM2", "mean"),
        Area_Mediana_km2=("AREA_KM2", "median"),
        Menor_Municipio_km2=("AREA_KM2", "min"),
        Maior_Municipio_km2=("AREA_KM2", "max"),
    ).round(2)

    # Adicionar nome completo da UF
    stats["Nome_UF"] = stats.index.map(
        lambda s: cfg.NOMES_UF.get(
            [k for k, v in cfg.UFS_SUDESTE.items() if v == s][0]
            if s in cfg.UFS_SUDESTE.values()
            else cfg.NOMES_UF.get(cfg.UFS_SUDESTE.get(s, ""), s),
            s
        )
    )

    # Corrigir mapeamento
    mapa_nome = {v: cfg.NOMES_UF[v] for v in cfg.NOMES_UF}
    stats["Nome_UF"] = stats.index.map(
        lambda s: mapa_nome.get(cfg.UFS_SUDESTE.get(s, ""), s)
    )

    print(stats.to_string())
    return stats


# ==========================================================================
# 3. MAPA 1 — LIMITES ESTADUAIS E MUNICIPAIS
# ==========================================================================

def mapa_limites_estaduais(gdf):
    """
    Gera mapa base da região Sudeste com:
    - Polígonos municipais em cores suaves por UF
    - Limites estaduais destacados em preto
    - Rótulos das siglas de UF

    Este mapa serve como referência cartográfica para todos os demais módulos.
    """
    print("\n--- Mapa: Limites Estaduais e Municipais ---")

    fig, ax = utils.criar_figura_mapa(figsize=(14, 11))

    # Plotar municípios com cor por UF
    for sigla, cor in cfg.CORES_UF.items():
        subset = gdf[gdf["SIGLA_UF"] == sigla]
        subset.plot(
            ax=ax,
            color=cor,
            edgecolor="white",
            linewidth=0.15,
            alpha=0.6,
        )

    # Limites estaduais (dissolve por UF)
    uf_dissolve = gdf.dissolve(by="SIGLA_UF")
    uf_dissolve.boundary.plot(
        ax=ax, color="#222222", linewidth=1.5
    )

    # Rótulos de UF
    utils.adicionar_rotulos_uf(ax, gdf)

    # Legenda
    legend_handles = [
        Patch(facecolor=cor, edgecolor="#333", label=f"{sigla} — {cfg.NOMES_UF[cfg.UFS_SUDESTE[sigla]]}")
        for sigla, cor in cfg.CORES_UF.items()
    ]
    ax.legend(
        handles=legend_handles,
        title="Unidades da Federação",
        loc="lower left",
        fontsize=9, title_fontsize=10,
        frameon=True, fancybox=True, shadow=True,
        framealpha=0.9,
    )

    utils.formatar_eixos_mapa(
        ax, titulo="Região Sudeste — Limites Estaduais e Municipais",
        mostrar_eixos=True
    )

    # Nota de rodapé
    ax.annotate(
        "Fonte: IBGE, Malha Municipal 2025 | CRS: SIRGAS 2000 (EPSG:4674)",
        xy=(0.5, -0.02), xycoords="axes fraction",
        ha="center", fontsize=7, color="#666666"
    )

    utils.salvar_mapa(fig, "mapa_limites_estaduais_municipais", "modulo1")


# ==========================================================================
# 4. MAPA 2 — CHOROPLETH DE ÁREA MUNICIPAL
# ==========================================================================

def mapa_area_municipal(gdf):
    """
    Gera choropleth da área (km²) dos municípios.

    A área municipal é uma proxy para a densidade de ocupação territorial.
    Municípios menores (típicos de SP e RJ) indicam maior fragmentação
    administrativa e, geralmente, maior urbanização — conceito central
    no modelo de Christaller (hierarquia de lugares centrais).

    Municípios extensos (norte de MG) sugerem menor integração urbana
    e maior dependência de atividades agropecuárias — diretamente
    relacionado ao modelo de Von Thünen (anéis de uso do solo).
    """
    print("\n--- Mapa: Área Municipal (Choropleth) ---")

    fig, ax = utils.criar_figura_mapa(figsize=(14, 11))

    gdf.plot(
        column="AREA_KM2",
        ax=ax,
        cmap=cfg.CMAP_AREA,
        scheme="quantiles",
        k=7,
        edgecolor="#AAAAAA",
        linewidth=0.1,
        legend=True,
        legend_kwds={
            "title": "Área (km²)",
            "loc": "lower left",
            "fontsize": 8,
            "title_fontsize": 9,
            "frameon": True,
            "fancybox": True,
            "shadow": True,
        },
    )

    # Limites estaduais
    uf_dissolve = gdf.dissolve(by="SIGLA_UF")
    uf_dissolve.boundary.plot(ax=ax, color="#333333", linewidth=1.2)

    utils.adicionar_rotulos_uf(ax, gdf)

    utils.formatar_eixos_mapa(
        ax,
        titulo="Área dos Municípios do Sudeste (km²)\n"
               "Municípios menores → maior urbanização | "
               "Maiores → matriz agropecuária",
        mostrar_eixos=True,
    )

    ax.annotate(
        "Classificação: Quantis (7 classes) | Fonte: IBGE, Malha Municipal 2025",
        xy=(0.5, -0.02), xycoords="axes fraction",
        ha="center", fontsize=7, color="#666666"
    )

    utils.salvar_mapa(fig, "mapa_choropleth_area_municipal", "modulo1")


# ==========================================================================
# 5. MAPA 3 — REGIÕES GEOGRÁFICAS INTERMEDIÁRIAS
# ==========================================================================

def mapa_regioes_intermediarias(gdf):
    """
    Gera mapa das Regiões Geográficas Intermediárias (IBGE, 2017).

    As Regiões Intermediárias substituíram as Mesorregiões e representam
    a escala de organização e articulação das Regiões Imediatas.
    Cada Intermediária é articulada por uma ou mais metrópoles/capitais regionais.

    Relevância para o modelo de Christaller:
        As Intermediárias representam o 2º nível da hierarquia urbana
        brasileira, onde os centros polarizam um conjunto de municípios
        ao redor — exatamente como previsto na teoria dos Lugares Centrais.
    """
    print("\n--- Mapa: Regiões Geográficas Intermediárias ---")

    fig, ax = utils.criar_figura_mapa(figsize=(14, 11))

    # Usar uma paleta com muitas cores distintas
    n_regioes = gdf["CD_RGINT"].nunique()
    cmap = plt.cm.get_cmap("tab20", n_regioes)

    gdf.plot(
        column="CD_RGINT",
        ax=ax,
        cmap=cmap,
        edgecolor="white",
        linewidth=0.1,
        categorical=True,
        alpha=0.7,
    )

    # Limites estaduais
    uf_dissolve = gdf.dissolve(by="SIGLA_UF")
    uf_dissolve.boundary.plot(ax=ax, color="#222222", linewidth=1.5)

    # Limites das intermediárias
    rgint_dissolve = gdf.dissolve(by="CD_RGINT")
    rgint_dissolve.boundary.plot(ax=ax, color="#555555", linewidth=0.6)

    # Rótulos com nome de cada Região Intermediária no centróide
    if "NM_RGINT" in gdf.columns:
        rgint_labels = gdf.dissolve(by="CD_RGINT", aggfunc="first")
        for idx, row in rgint_labels.iterrows():
            centroid = row.geometry.representative_point()
            nome = row.get("NM_RGINT", "")
            if nome:
                ax.annotate(
                    nome,
                    xy=(centroid.x, centroid.y),
                    fontsize=5, fontweight="bold",
                    ha="center", va="center",
                    color="#111111",
                    bbox=dict(boxstyle="round,pad=0.15", fc="white",
                              ec="none", alpha=0.65),
                )

    utils.adicionar_rotulos_uf(ax, gdf)

    # Legenda descritiva
    legend_handles = [
        Patch(facecolor="#66BB6A", edgecolor="#555", alpha=0.7,
              label=f"{n_regioes} Regiões Intermediárias"),
        Patch(facecolor="#E0E0E0", edgecolor="#222", linewidth=1.5,
              label="Limite Estadual"),
        Line2D([0], [0], color="#555555", linewidth=0.8,
               label="Limite da Região Intermediária"),
    ]
    ax.legend(
        handles=legend_handles,
        title="Regiões Geográficas Intermediárias",
        loc="lower left",
        fontsize=8, title_fontsize=9,
        frameon=True, fancybox=True, shadow=True,
        framealpha=0.9,
    )

    utils.formatar_eixos_mapa(
        ax,
        titulo="Regiões Geográficas Intermediárias — Sudeste\n"
               "Cada cor representa uma região articulada por um polo urbano (Christaller)",
        mostrar_eixos=True,
    )

    ax.annotate(
        f"{n_regioes} Regiões Intermediárias | Fonte: IBGE, Divisão Regional 2017",
        xy=(0.5, -0.02), xycoords="axes fraction",
        ha="center", fontsize=7, color="#666666"
    )

    utils.salvar_mapa(fig, "mapa_regioes_intermediarias", "modulo1")


# ==========================================================================
# 6. MAPA 4 — REGIÕES GEOGRÁFICAS IMEDIATAS
# ==========================================================================

def mapa_regioes_imediatas(gdf):
    """
    Gera mapa das Regiões Geográficas Imediatas (IBGE, 2017).

    As Regiões Imediatas substituíram as Microrregiões e representam
    a escala local de articulação, centrada em cidades que exercem
    funções de gestão imediata (comércio, saúde, educação).

    Relevância para o modelo de Christaller/Lösch:
        As Imediatas são a materialização empírica dos "lugares centrais"
        de menor ordem: cidades que oferecem bens e serviços de alcance
        local, polarizando municípios vizinhos. O mapa permite identificar
        visualmente os "hexágonos" de Lösch — áreas de mercado sobrepostas.
    """
    print("\n--- Mapa: Regiões Geográficas Imediatas ---")

    fig, ax = utils.criar_figura_mapa(figsize=(14, 11))

    n_regioes = gdf["CD_RGI"].nunique()
    cmap = plt.cm.get_cmap("Set3", min(n_regioes, 12))

    gdf.plot(
        column="CD_RGI",
        ax=ax,
        cmap="Pastel1",
        edgecolor="white",
        linewidth=0.05,
        categorical=True,
        alpha=0.65,
    )

    # Limites estaduais
    uf_dissolve = gdf.dissolve(by="SIGLA_UF")
    uf_dissolve.boundary.plot(ax=ax, color="#222222", linewidth=1.5)

    # Limites das imediatas
    rgi_dissolve = gdf.dissolve(by="CD_RGI")
    rgi_dissolve.boundary.plot(ax=ax, color="#888888", linewidth=0.3)

    # Rótulos com nome de cada Região Imediata no centróide
    if "NM_RGI" in gdf.columns:
        rgi_labels = gdf.dissolve(by="CD_RGI", aggfunc="first")
        for idx, row in rgi_labels.iterrows():
            centroid = row.geometry.representative_point()
            nome = row.get("NM_RGI", "")
            if nome:
                ax.annotate(
                    nome,
                    xy=(centroid.x, centroid.y),
                    fontsize=3.5, fontweight="bold",
                    ha="center", va="center",
                    color="#222222",
                    bbox=dict(boxstyle="round,pad=0.1", fc="white",
                              ec="none", alpha=0.55),
                )

    utils.adicionar_rotulos_uf(ax, gdf)

    # Legenda descritiva
    legend_handles = [
        Patch(facecolor="#FFCDD2", edgecolor="#888", alpha=0.65,
              label=f"{n_regioes} Regiões Imediatas"),
        Patch(facecolor="#E0E0E0", edgecolor="#222", linewidth=1.5,
              label="Limite Estadual"),
        Line2D([0], [0], color="#888888", linewidth=0.5,
               label="Limite da Região Imediata"),
    ]
    ax.legend(
        handles=legend_handles,
        title="Regiões Geográficas Imediatas",
        loc="lower left",
        fontsize=8, title_fontsize=9,
        frameon=True, fancybox=True, shadow=True,
        framealpha=0.9,
    )

    utils.formatar_eixos_mapa(
        ax,
        titulo="Regiões Geográficas Imediatas — Sudeste\n"
               "Cada região é polarizada por um centro local (Lösch)",
        mostrar_eixos=True,
    )

    ax.annotate(
        f"{n_regioes} Regiões Imediatas | Fonte: IBGE, Divisão Regional 2017",
        xy=(0.5, -0.02), xycoords="axes fraction",
        ha="center", fontsize=7, color="#666666"
    )

    utils.salvar_mapa(fig, "mapa_regioes_imediatas", "modulo1")


# ==========================================================================
# 7. MAPA 5 — CONURBAÇÕES
# ==========================================================================

def mapa_conurbacoes(gdf):
    """
    Gera mapa destacando as conurbações (aglomerações urbanas contínuas).

    A coluna CD_CONCURB identifica municípios que formam manchas urbanas
    contínuas com seus vizinhos. São relevantes porque:

    - Indicam integração funcional entre municípios (pendularidade)
    - São candidatos naturais a Arranjos Produtivos Locais (APLs)
    - No modelo de Christaller, as conurbações representam a fusão
      de centros de mesma hierarquia
    """
    print("\n--- Mapa: Conurbações ---")

    fig, ax = utils.criar_figura_mapa(figsize=(14, 11))

    # Base: todos os municípios em cinza claro
    gdf.plot(ax=ax, color="#E0E0E0", edgecolor="white", linewidth=0.1)

    # Destacar municípios com conurbação
    conurb = gdf[gdf["CD_CONCURB"].notna()].copy()
    if len(conurb) > 0:
        # Atribuir cores únicas por conurbação
        codigos_conurb = sorted(conurb["CD_CONCURB"].unique())
        n_conurb = len(codigos_conurb)
        cmap_conurb = plt.cm.get_cmap("Set2", max(n_conurb, 3))
        cor_por_conurb = {cod: mcolors.to_hex(cmap_conurb(i))
                         for i, cod in enumerate(codigos_conurb)}
        conurb["_cor"] = conurb["CD_CONCURB"].map(cor_por_conurb)

        conurb.plot(
            column="CD_CONCURB",
            ax=ax,
            cmap="Set2",
            edgecolor="#555",
            linewidth=0.3,
            categorical=True,
            alpha=0.8,
        )

        # Rótulos das conurbações (nome da coluna NM_CONCURB se existir)
        col_nome_conurb = "NM_CONCURB" if "NM_CONCURB" in conurb.columns else None
        conurb_dissolve = conurb.dissolve(by="CD_CONCURB", aggfunc="first")
        for idx, row in conurb_dissolve.iterrows():
            centroid = row.geometry.representative_point()
            if col_nome_conurb and row.get(col_nome_conurb):
                nome = row[col_nome_conurb]
            else:
                nome = str(idx)
            ax.annotate(
                nome,
                xy=(centroid.x, centroid.y),
                fontsize=5, fontweight="bold",
                ha="center", va="center",
                color="#111",
                bbox=dict(boxstyle="round,pad=0.15", fc="white",
                          ec="none", alpha=0.7),
            )
    else:
        n_conurb = 0
        codigos_conurb = []

    # Limites estaduais
    uf_dissolve = gdf.dissolve(by="SIGLA_UF")
    uf_dissolve.boundary.plot(ax=ax, color="#222", linewidth=1.3)

    utils.adicionar_rotulos_uf(ax, gdf)

    if not isinstance(n_conurb, int):
        n_conurb = gdf["CD_CONCURB"].nunique()
    n_mun_conurb = len(conurb)

    # Legenda
    legend_handles = [
        Patch(facecolor="#E0E0E0", edgecolor="white",
              label="Sem conurbação"),
        Patch(facecolor="#66C2A5", edgecolor="#555", alpha=0.8,
              label=f"Conurbação ({n_conurb} aglomerações,\n"
                    f"{n_mun_conurb} municípios)"),
        Patch(facecolor="white", edgecolor="#222", linewidth=1.3,
              label="Limite Estadual"),
    ]
    ax.legend(
        handles=legend_handles,
        title="Conurbações Urbanas",
        loc="lower left",
        fontsize=8, title_fontsize=9,
        frameon=True, fancybox=True, shadow=True,
        framealpha=0.9,
    )

    utils.formatar_eixos_mapa(
        ax,
        titulo=f"Conurbações na Região Sudeste\n"
               f"{n_conurb} aglomerações urbanas contínuas "
               f"({n_mun_conurb} municípios)",
        mostrar_eixos=True,
    )

    ax.annotate(
        "Municípios cinza = sem conurbação | Coloridos = conurbações | "
        "Fonte: IBGE 2025",
        xy=(0.5, -0.02), xycoords="axes fraction",
        ha="center", fontsize=7, color="#666666"
    )

    utils.salvar_mapa(fig, "mapa_conurbacoes", "modulo1")


# ==========================================================================
# 8. GRÁFICO 6 — FRAGMENTAÇÃO EMANCIPATÓRIA MUNICIPAL
# ==========================================================================

def grafico_fragmentacao_emancipatoria():
    """
    Gera gráfico comparando o número de municípios do Sudeste em 1970, 1991
    e 2022 (malha atual), evidenciando o fenômeno de fragmentação
    emancipatória pós-Constituição de 1988.

    Após 1988, houve um "boom" na criação de novos municípios, motivado
    pela busca de autonomia administrativa e acesso a repasses federais
    (Fundo de Participação dos Municípios — FPM).

    Fontes: IBGE, Malhas Municipais 1970, 1991 e 2025.
    """
    import os

    print("\n--- Gráfico: Fragmentação Emancipatória Municipal ---")

    base = os.path.join(cfg.BASE_DIR, "municipios e UF + população")

    UFS_COD = {"31": "MG", "32": "ES", "33": "RJ", "35": "SP"}
    UFS_NOME = {"MG": "Minas Gerais", "ES": "Espírito Santo",
                "RJ": "Rio de Janeiro", "SP": "São Paulo"}

    # --- Carregar e contar municípios por UF em cada período ---

    # 1970
    shp_1970 = os.path.join(base, "05-malha municipal 1970.shp")
    gdf70 = gpd.read_file(shp_1970)
    gdf70["CD_UF"] = gdf70["codigo"].astype(str).str[:2]
    gdf70_se = gdf70[gdf70["CD_UF"].isin(UFS_COD.keys())]
    cont_1970 = gdf70_se.groupby("CD_UF").size().rename("1970")
    cont_1970.index = cont_1970.index.map(UFS_COD)

    # 1991
    shp_1991 = os.path.join(base, "05-malha municipal 1991.shp")
    gdf91 = gpd.read_file(shp_1991)
    gdf91["CD_UF"] = gdf91["BR91POLY_I"].astype(str).str[:2]
    gdf91_se = gdf91[gdf91["CD_UF"].isin(UFS_COD.keys())]
    cont_1991 = gdf91_se.groupby("CD_UF").size().rename("1991")
    cont_1991.index = cont_1991.index.map(UFS_COD)

    # 2025 (proxy para malha atual / pós-2022)
    shp_2025 = os.path.join(base, "BR_Municipios_2025.shp")
    gdf25 = gpd.read_file(shp_2025)
    gdf25_se = gdf25[gdf25["SIGLA_UF"].isin(UFS_COD.values())]
    cont_2025 = gdf25_se.groupby("SIGLA_UF").size().rename("2022")

    # Consolidar tabela
    import pandas as pd
    df = pd.DataFrame({"1970": cont_1970, "1991": cont_1991, "2022": cont_2025})
    df = df.loc[["MG", "ES", "RJ", "SP"]]
    df["Cresc_Pct"] = ((df["2022"] / df["1970"] - 1) * 100).round(1)

    total_70 = df["1970"].sum()
    total_91 = df["1991"].sum()
    total_22 = df["2022"].sum()

    print(f"  Municípios: 1970={total_70} → 1991={total_91} → 2022={total_22}")
    print(f"  Crescimento total: +{total_22 - total_70} municípios "
          f"({((total_22/total_70 - 1)*100):.1f}%)")

    # --- Gráfico combinado ---
    fig, axes = plt.subplots(1, 2, figsize=(16, 8),
                             gridspec_kw={"width_ratios": [2.2, 1]})
    fig.patch.set_facecolor("#FAFAFA")

    # ---- Painel esquerdo: Barras agrupadas por UF ----
    ax1 = axes[0]
    ax1.set_facecolor("#F5F5F5")

    ufs = df.index.tolist()
    x = np.arange(len(ufs))
    w = 0.25

    cores = ["#5C6BC0", "#26A69A", "#EF5350"]
    labels_anos = ["1970", "1991", "2022"]

    for i, (ano, cor) in enumerate(zip(labels_anos, cores)):
        ax1.bar(x + (i - 1) * w, df[ano], w, label=ano, color=cor,
                edgecolor="white", linewidth=0.8, alpha=0.9, zorder=3)

    # Valores sobre as barras
    for i, ano in enumerate(labels_anos):
        for j, v in enumerate(df[ano]):
            ax1.text(x[j] + (i - 1) * w, v + 8, str(v),
                     ha="center", va="bottom", fontsize=9, fontweight="bold",
                     color=cores[i])

    # Anotações de crescimento %
    for j, uf in enumerate(ufs):
        pct = df.loc[uf, "Cresc_Pct"]
        val_max = df.loc[uf, "2022"]
        ax1.annotate(
            f"+{pct:.0f}%",
            xy=(x[j] + w, val_max + 25),
            fontsize=8, fontweight="bold", color="#C62828",
            ha="center",
            bbox=dict(boxstyle="round,pad=0.2", fc="#FFEBEE",
                      ec="#EF9A9A", alpha=0.8),
        )

    ax1.set_xticks(x)
    ax1.set_xticklabels([f"{uf}\n{UFS_NOME[uf]}" for uf in ufs], fontsize=10)
    ax1.set_ylabel("Número de Municípios", fontsize=11, fontweight="bold")
    ax1.set_title(
        "Fragmentação Emancipatória Municipal — Sudeste\n"
        "Número de municípios por UF (1970 / 1991 / 2022)",
        fontsize=13, fontweight="bold", pad=15
    )
    ax1.legend(title="Ano", fontsize=9, title_fontsize=10, loc="upper left",
               frameon=True, fancybox=True, shadow=True, framealpha=0.9)
    ax1.grid(axis="y", alpha=0.3, linestyle="--", zorder=0)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    ax1.annotate(
        "Fonte: IBGE, Malhas Municipais 1970, 1991 e 2025 | Elaboração própria",
        xy=(0.5, -0.08), xycoords="axes fraction",
        ha="center", fontsize=7, color="#888888"
    )

    # ---- Painel direito: Evolução temporal do total ----
    ax2 = axes[1]
    ax2.set_facecolor("#F5F5F5")

    anos = [1970, 1991, 2022]
    totais = [total_70, total_91, total_22]

    ax2.fill_between(anos, totais, alpha=0.15, color="#5C6BC0", zorder=2)
    ax2.plot(anos, totais, "o-", color="#5C6BC0", markersize=10, linewidth=2.5,
             markerfacecolor="white", markeredgecolor="#5C6BC0",
             markeredgewidth=2.5, zorder=3)

    for a, t in zip(anos, totais):
        ax2.annotate(
            f"{t:,}".replace(",", "."),
            xy=(a, t), xytext=(0, 15),
            textcoords="offset points",
            ha="center", fontsize=11, fontweight="bold", color="#283593",
            bbox=dict(boxstyle="round,pad=0.3", fc="white",
                      ec="#5C6BC0", alpha=0.9),
        )

    # Faixa pós-Constituição 1988
    ax2.axvspan(1988, 2022, alpha=0.08, color="#EF5350", zorder=1)
    ax2.annotate(
        "Pós-Constituição\nde 1988",
        xy=(2005, min(totais) + (max(totais) - min(totais)) * 0.15),
        ha="center", fontsize=8, fontstyle="italic", color="#C62828",
        bbox=dict(boxstyle="round,pad=0.3", fc="#FFEBEE",
                  ec="#EF9A9A", alpha=0.7),
    )
    ax2.axvline(1988, color="#EF5350", linestyle="--", linewidth=1.2,
                alpha=0.6, zorder=1)

    # Seta com incremento
    delta_91_22 = total_22 - total_91
    ax2.annotate(
        f"+{delta_91_22} mun.\n(boom emancipatório)",
        xy=(1991, total_91),
        xytext=(2002, total_91 - 50),
        fontsize=8, fontweight="bold", color="#C62828",
        arrowprops=dict(arrowstyle="->", color="#C62828", lw=1.3),
        bbox=dict(boxstyle="round,pad=0.3", fc="#FFF3E0",
                  ec="#FFAB91", alpha=0.8),
    )

    ax2.set_xticks(anos)
    ax2.set_xlabel("Ano", fontsize=10)
    ax2.set_ylabel("Total de Municípios no Sudeste", fontsize=10,
                   fontweight="bold")
    ax2.set_title(
        "Evolução do Total de\nMunicípios no Sudeste",
        fontsize=12, fontweight="bold", pad=10
    )
    ax2.grid(axis="y", alpha=0.3, linestyle="--")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.set_ylim(min(totais) * 0.9, max(totais) * 1.08)

    plt.tight_layout(pad=2)

    utils.salvar_mapa(fig, "grafico_fragmentacao_emancipatoria", "modulo1")


# ==========================================================================
# EXECUÇÃO PRINCIPAL
# ==========================================================================

def executar_modulo1():
    """Executa todas as análises e mapas do Módulo 1."""
    gdf = carregar_dados()
    stats = gerar_estatisticas(gdf)
    mapa_limites_estaduais(gdf)
    mapa_area_municipal(gdf)
    mapa_regioes_intermediarias(gdf)
    mapa_regioes_imediatas(gdf)
    mapa_conurbacoes(gdf)
    grafico_fragmentacao_emancipatoria()
    print("\n✓ Módulo 1 concluído! Mapas salvos em output/modulo1/")
    return gdf


if __name__ == "__main__":
    executar_modulo1()
