# -*- coding: utf-8 -*-
"""
============================================================================
FUNÇÕES UTILITÁRIAS REUTILIZÁVEIS
Economia Regional e Urbana — Análise da Região Sudeste do Brasil
============================================================================
Funções genéricas de carregamento, filtragem e formatação que são usadas
por todos os módulos do projeto.
"""

import os
import warnings
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patheffects as pe
from matplotlib.patches import Patch
import numpy as np

import config as cfg

warnings.filterwarnings("ignore", category=FutureWarning)


# ==========================================================================
# 1. CARREGAMENTO GEOGRÁFICO
# ==========================================================================

def carregar_municipios_brasil(path=None):
    """
    Carrega o shapefile completo de municípios do Brasil.
    Define o CRS padrão (SIRGAS 2000) se necessário.

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame com todos os municípios do Brasil.
    """
    path = path or cfg.SHP_MUNICIPIOS
    try:
        gdf = gpd.read_file(path)
        if gdf.crs is None or str(gdf.crs) != cfg.CRS_PADRAO:
            gdf = gdf.set_crs(cfg.CRS_PADRAO, allow_override=True)
        print(f"  ✓ Shapefile carregado: {len(gdf)} municípios | CRS: {gdf.crs}")
        return gdf
    except Exception as e:
        print(f"  ✗ Erro ao carregar shapefile: {e}")
        raise


def carregar_municipios_sudeste(path=None):
    """
    Carrega e filtra o shapefile para apenas os municípios da região Sudeste.
    Filtro baseado na coluna CD_REGIAO == '3' (código IBGE da região Sudeste).

    Relevância para políticas públicas:
        A delimitação precisa da região é o primeiro passo para qualquer análise
        de planejamento territorial, permitindo identificar assimetrias entre
        estados (MG, ES, RJ, SP) e subsidiar a formulação de APLs regionais.

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame filtrado para a região Sudeste.
    """
    gdf = carregar_municipios_brasil(path)
    sudeste = gdf[gdf["CD_REGIAO"] == cfg.COD_REGIAO_SUDESTE].copy()
    sudeste = sudeste.reset_index(drop=True)
    print(f"  ✓ Filtro Sudeste: {len(sudeste)} municípios")
    for uf in cfg.SIGLAS_SUDESTE:
        n = len(sudeste[sudeste["SIGLA_UF"] == uf])
        print(f"      {uf}: {n} municípios")
    return sudeste


def carregar_shapefile_generico(path, nome="camada"):
    """
    Carrega qualquer shapefile, reprojetando para o CRS padrão SIRGAS 2000.
    Usado para camadas de infraestrutura (rodovias, ferrovias, etc.).

    Parameters
    ----------
    path : str
        Caminho do shapefile.
    nome : str
        Nome descritivo para mensagens de log.

    Returns
    -------
    geopandas.GeoDataFrame ou None
        GeoDataFrame carregado, ou None se houver erro.
    """
    try:
        gdf = gpd.read_file(path)
        if gdf.crs is not None and str(gdf.crs) != cfg.CRS_PADRAO:
            gdf = gdf.to_crs(cfg.CRS_PADRAO)
        elif gdf.crs is None:
            gdf = gdf.set_crs(cfg.CRS_PADRAO, allow_override=True)
        print(f"  ✓ {nome}: {len(gdf)} feições | CRS: {gdf.crs}")
        return gdf
    except Exception as e:
        print(f"  ✗ Erro ao carregar {nome}: {e}")
        return None


def clipar_para_sudeste(gdf, gdf_sudeste):
    """
    Recorta (clip) um GeoDataFrame para os limites da região Sudeste.
    Útil para filtrar camadas nacionais (rodovias, biomas, etc.).

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        GeoDataFrame a ser recortado.
    gdf_sudeste : geopandas.GeoDataFrame
        GeoDataFrame dos municípios do Sudeste (usado como máscara).

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame recortado.
    """
    try:
        # Dissolve para obter o contorno da região inteira
        mascara = gdf_sudeste.dissolve()
        recortado = gpd.clip(gdf, mascara)
        print(f"      → Recortado para Sudeste: {len(recortado)} feições")
        return recortado
    except Exception as e:
        print(f"      ✗ Erro no clip: {e}")
        return gdf


# ==========================================================================
# 2. CARREGAMENTO DE TABELAS SIDRA (EXCEL)
# ==========================================================================

def carregar_tabela_sidra(path, skiprows=4, col_localidade=0,
                          encoding=None, nome="tabela"):
    """
    Parser genérico para planilhas do SIDRA/IBGE.

    As planilhas do SIDRA possuem cabeçalhos complexos com múltiplas linhas
    de metadados. Esta função pula essas linhas e identifica a coluna de
    localidade (UF ou município) para facilitar filtros posteriores.

    Parameters
    ----------
    path : str
        Caminho do arquivo Excel.
    skiprows : int
        Número de linhas de cabeçalho a pular.
    col_localidade : int
        Índice da coluna que contém o nome da UF/município.
    nome : str
        Nome descritivo para mensagens de log.

    Returns
    -------
    pandas.DataFrame ou None
        DataFrame limpo, ou None se houver erro.
    """
    try:
        df = pd.read_excel(path, header=None, skiprows=skiprows)

        # Remover linhas de rodapé (Fonte: IBGE...)
        col0 = df.iloc[:, col_localidade].astype(str)
        mask_fonte = col0.str.contains("Fonte:", na=False, case=False)
        if mask_fonte.any():
            idx_fonte = mask_fonte.idxmax()
            df = df.iloc[:idx_fonte].copy()

        print(f"  ✓ {nome}: {df.shape[0]} linhas × {df.shape[1]} colunas")
        return df
    except Exception as e:
        print(f"  ✗ Erro ao carregar {nome}: {e}")
        return None


def filtrar_sudeste_uf(df, col_localidade=0):
    """
    Filtra um DataFrame para apenas as UFs da região Sudeste.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame com coluna de UF.
    col_localidade : int
        Índice da coluna que contém o nome da UF.

    Returns
    -------
    pandas.DataFrame
        DataFrame filtrado.
    """
    nomes_sudeste = list(cfg.NOMES_UF.values())
    mask = df.iloc[:, col_localidade].isin(nomes_sudeste)
    resultado = df[mask].copy()
    print(f"      → Filtro Sudeste: {len(resultado)} linhas")
    return resultado


# ==========================================================================
# 3. FORMATAÇÃO E SALVAMENTO DE MAPAS
# ==========================================================================

def criar_figura_mapa(nrows=1, ncols=1, figsize=None):
    """
    Cria uma figura matplotlib com fundo estilizado para mapas geográficos.

    Parameters
    ----------
    nrows, ncols : int
        Número de subplots.
    figsize : tuple
        Tamanho da figura em polegadas.

    Returns
    -------
    fig, ax : matplotlib.figure.Figure, matplotlib.axes.Axes
    """
    if figsize is None:
        figsize = (14, 10) if ncols == 1 else (16, 8 * nrows)
    fig, ax = plt.subplots(nrows, ncols, figsize=figsize)
    return fig, ax


def formatar_eixos_mapa(ax, titulo="", mostrar_eixos=True):
    """
    Aplica formatação visual padrão aos eixos de um mapa.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Eixo do mapa.
    titulo : str
        Título do mapa.
    mostrar_eixos : bool
        Se False, remove rótulos de lat/lon.
    """
    ax.set_title(titulo, fontsize=14, fontweight="bold", pad=15)
    if not mostrar_eixos:
        ax.set_axis_off()
    else:
        ax.set_xlabel("Longitude", fontsize=9)
        ax.set_ylabel("Latitude", fontsize=9)
        ax.tick_params(labelsize=8)


def adicionar_rotulos_uf(ax, gdf_sudeste):
    """
    Adiciona rótulos das siglas de UF no centróide de cada estado.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Eixo do mapa.
    gdf_sudeste : geopandas.GeoDataFrame
        GeoDataFrame dos municípios do Sudeste.
    """
    dissolve_uf = gdf_sudeste.dissolve(by="SIGLA_UF")
    for sigla, row in dissolve_uf.iterrows():
        centroid = row.geometry.centroid
        ax.annotate(
            sigla,
            xy=(centroid.x, centroid.y),
            fontsize=13, fontweight="bold",
            ha="center", va="center",
            color="#333333",
            path_effects=[
                pe.withStroke(linewidth=3, foreground="white")
            ],
        )


def salvar_mapa(fig, nome, modulo="modulo1"):
    """
    Salva uma figura como PNG na pasta de saída do módulo correspondente.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        Figura a salvar.
    nome : str
        Nome do arquivo (sem extensão).
    modulo : str
        Nome da subpasta ('modulo1', 'modulo2', etc.).
    """
    caminho = os.path.join(cfg.OUTPUT_DIR, modulo, f"{nome}.png")
    fig.savefig(caminho, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ Mapa salvo: {caminho}")


# ==========================================================================
# 4. FUNÇÕES AUXILIARES GERAIS
# ==========================================================================

def formatar_numero_br(valor):
    """Formata número no padrão brasileiro (1.234.567,89)."""
    if pd.isna(valor):
        return "—"
    try:
        valor = float(valor)
        if valor == int(valor):
            return f"{int(valor):,.0f}".replace(",", ".")
        return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(valor)


def criar_legenda_custom(ax, labels_cores, titulo="Legenda", loc="lower right"):
    """
    Cria uma legenda personalizada com patches coloridos.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
    labels_cores : dict
        Dicionário {label: cor}.
    titulo : str
        Título da legenda.
    loc : str
        Posição da legenda.
    """
    patches = [Patch(facecolor=cor, label=label, edgecolor="#333")
               for label, cor in labels_cores.items()]
    ax.legend(
        handles=patches, title=titulo, loc=loc,
        fontsize=8, title_fontsize=9,
        frameon=True, fancybox=True, shadow=True,
        framealpha=0.9
    )
