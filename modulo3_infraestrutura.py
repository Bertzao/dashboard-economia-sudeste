# -*- coding: utf-8 -*-
"""
============================================================================
MÓDULO 3 — INFRAESTRUTURA, USO DO SOLO E MEIO AMBIENTE
Economia Regional e Urbana — Análise da Região Sudeste do Brasil
============================================================================

Objetivo:
    Carregar e sobrepor múltiplas camadas geográficas para gerar mapas
    integrados de infraestrutura logística e meio ambiente.

Camadas geográficas:
    1. Polígonos municipais (base)
    2. Linhas: rodovias estruturantes, ferrovias, hidrovias
    3. Pontos: aeroportos, portos
    4. Polígonos: biomas, unidades de conservação

Relevância para os modelos clássicos:
    - Weber: a infraestrutura de transportes (rodovias, ferrovias, portos)
      é o principal determinante dos custos de transporte na função de
      localização industrial. Regiões com melhor dotação logística atraem
      indústrias orientadas ao mercado/matéria-prima.
    - Von Thünen: a acessibilidade viária determina os anéis de uso do
      solo agrícola — culturas perecíveis próximas à infraestrutura de
      escoamento, extensivas em áreas remotas.

Fontes:
    - Min. dos Transportes, Base Cartográfica 2014
    - IBGE, Biomas 2025
    - ICMBio/IBGE, Unidades de Conservação (Censo 2022)
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

import config as cfg
import utils


# ==========================================================================
# 1. CARREGAMENTO DE CAMADAS DE INFRAESTRUTURA
# ==========================================================================

def carregar_camadas_infra(gdf_sudeste):
    """
    Carrega todas as camadas de infraestrutura logística e recorta
    para a extensão da região Sudeste.

    Cada camada é reprojetada para SIRGAS 2000 (EPSG:4674) antes do clip,
    garantindo compatibilidade nas sobreposições geográficas.

    Parameters
    ----------
    gdf_sudeste : geopandas.GeoDataFrame
        GeoDataFrame dos municípios do Sudeste (usado como máscara de clip).

    Returns
    -------
    dict
        Dicionário {nome_camada: GeoDataFrame_recortado}.
    """
    print("\n--- Carregando camadas de infraestrutura ---")

    camadas = {}

    # Rodovias estruturantes
    gdf = utils.carregar_shapefile_generico(cfg.SHP_RODOVIAS, "Rodovias Estruturantes")
    if gdf is not None:
        camadas["rodovias"] = utils.clipar_para_sudeste(gdf, gdf_sudeste)

    # Ferrovias
    gdf = utils.carregar_shapefile_generico(cfg.SHP_FERROVIAS, "Ferrovias")
    if gdf is not None:
        camadas["ferrovias"] = utils.clipar_para_sudeste(gdf, gdf_sudeste)

    # Aeroportos
    gdf = utils.carregar_shapefile_generico(cfg.SHP_AEROPORTOS, "Aeroportos")
    if gdf is not None:
        camadas["aeroportos"] = utils.clipar_para_sudeste(gdf, gdf_sudeste)

    # Portos
    gdf = utils.carregar_shapefile_generico(cfg.SHP_PORTOS, "Portos")
    if gdf is not None:
        camadas["portos"] = utils.clipar_para_sudeste(gdf, gdf_sudeste)

    # Hidrovias
    gdf = utils.carregar_shapefile_generico(cfg.SHP_HIDROVIAS, "Hidrovias")
    if gdf is not None:
        camadas["hidrovias"] = utils.clipar_para_sudeste(gdf, gdf_sudeste)

    return camadas


# ==========================================================================
# 2. CARREGAMENTO DE CAMADAS AMBIENTAIS
# ==========================================================================

def carregar_camadas_ambientais(gdf_sudeste):
    """
    Carrega as camadas de biomas e unidades de conservação, recortando
    para a região Sudeste.

    Os biomas presentes no Sudeste são:
    - Mata Atlântica (predominante no litoral e serras)
    - Cerrado (predominante no interior de MG, norte de SP)
    - Caatinga (pequena porção no norte de MG)

    Relevância para políticas públicas:
        As Unidades de Conservação impõem restrições ao uso do solo que
        devem ser consideradas no planejamento de APLs e na localização
        de empreendimentos (modelo de Weber com restrições ambientais).

    Returns
    -------
    dict
        Dicionário {nome_camada: GeoDataFrame_recortado}.
    """
    print("\n--- Carregando camadas ambientais ---")

    camadas = {}

    # Biomas
    gdf = utils.carregar_shapefile_generico(cfg.SHP_BIOMAS, "Biomas")
    if gdf is not None:
        camadas["biomas"] = utils.clipar_para_sudeste(gdf, gdf_sudeste)

    # Unidades de Conservação
    gdf = utils.carregar_shapefile_generico(cfg.SHP_UCS, "Unidades de Conservação")
    if gdf is not None:
        camadas["ucs"] = utils.clipar_para_sudeste(gdf, gdf_sudeste)

    # Potencialidade Agrícola
    gdf = utils.carregar_shapefile_generico(cfg.SHP_POTENCIALIDADE_AGRICOLA, "Potencialidade Agrícola")
    if gdf is not None:
        camadas["potencial_agri"] = utils.clipar_para_sudeste(gdf, gdf_sudeste)

    return camadas


# ==========================================================================
# 3. MAPA INTEGRADO DE INFRAESTRUTURA LOGÍSTICA
# ==========================================================================

def mapa_infraestrutura_logistica(gdf_sudeste, camadas_infra):
    """
    Gera mapa integrado com todas as camadas de infraestrutura logística
    sobrepostas ao mapa base dos municípios.

    Este mapa é central para a análise weberiana: permite visualizar
    a dotação de infraestrutura de cada região e identificar:
    - Corredores logísticos (rodovias + ferrovias convergentes)
    - Nós intermodais (onde portos/aeroportos conectam diferentes modais)
    - Áreas com escassez de infraestrutura (potencial desvantagem locacional)

    A concentração de infraestrutura no eixo SP–RJ (Via Dutra, Santos–SP)
    explica a gravitação industrial observada na região, confirmando
    a hipótese de Weber sobre minimização do custo de transporte.
    """
    print("\n--- Mapa: Infraestrutura Logística Integrada ---")

    fig, ax = utils.criar_figura_mapa(figsize=(16, 12))

    # Base: municípios
    gdf_sudeste.plot(
        ax=ax, color="#F0F0F0", edgecolor="#CCCCCC", linewidth=0.1
    )

    # Limites estaduais
    uf_dissolve = gdf_sudeste.dissolve(by="SIGLA_UF")
    uf_dissolve.boundary.plot(ax=ax, color="#333333", linewidth=1.3)

    # Camadas de infraestrutura
    legend_elements = []

    # Rodovias
    if "rodovias" in camadas_infra and len(camadas_infra["rodovias"]) > 0:
        camadas_infra["rodovias"].plot(
            ax=ax, color=cfg.COR_RODOVIAS, linewidth=0.8, alpha=0.7
        )
        legend_elements.append(
            Line2D([0], [0], color=cfg.COR_RODOVIAS, linewidth=2,
                   label="Rodovias Estruturantes")
        )

    # Ferrovias
    if "ferrovias" in camadas_infra and len(camadas_infra["ferrovias"]) > 0:
        camadas_infra["ferrovias"].plot(
            ax=ax, color=cfg.COR_FERROVIAS, linewidth=1.0,
            linestyle="--", alpha=0.8
        )
        legend_elements.append(
            Line2D([0], [0], color=cfg.COR_FERROVIAS, linewidth=2,
                   linestyle="--", label="Ferrovias")
        )

    # Hidrovias
    if "hidrovias" in camadas_infra and len(camadas_infra["hidrovias"]) > 0:
        camadas_infra["hidrovias"].plot(
            ax=ax, color=cfg.COR_HIDROVIAS, linewidth=1.0, alpha=0.6
        )
        legend_elements.append(
            Line2D([0], [0], color=cfg.COR_HIDROVIAS, linewidth=2,
                   label="Hidrovias")
        )

    # Aeroportos
    if "aeroportos" in camadas_infra and len(camadas_infra["aeroportos"]) > 0:
        camadas_infra["aeroportos"].plot(
            ax=ax, color=cfg.COR_AEROPORTOS, marker="*",
            markersize=60, alpha=0.9, zorder=5
        )
        legend_elements.append(
            Line2D([0], [0], marker="*", color="w",
                   markerfacecolor=cfg.COR_AEROPORTOS, markersize=12,
                   label="Aeroportos")
        )

    # Portos
    if "portos" in camadas_infra and len(camadas_infra["portos"]) > 0:
        camadas_infra["portos"].plot(
            ax=ax, color=cfg.COR_PORTOS, marker="^",
            markersize=60, alpha=0.9, zorder=5
        )
        legend_elements.append(
            Line2D([0], [0], marker="^", color="w",
                   markerfacecolor=cfg.COR_PORTOS, markersize=12,
                   label="Portos")
        )

    # Rótulos de UF
    utils.adicionar_rotulos_uf(ax, gdf_sudeste)

    # Legenda
    ax.legend(
        handles=legend_elements,
        title="Infraestrutura Logística",
        loc="lower left",
        fontsize=9, title_fontsize=10,
        frameon=True, fancybox=True, shadow=True, framealpha=0.9,
    )

    utils.formatar_eixos_mapa(
        ax,
        titulo="Infraestrutura Logística Integrada — Região Sudeste\n"
               "Modelo de Weber: custos de transporte determinam a localização industrial",
    )

    ax.annotate(
        "Fontes: Min. Transportes (2014), ANTAQ | CRS: SIRGAS 2000",
        xy=(0.5, -0.02), xycoords="axes fraction",
        ha="center", fontsize=7, color="#666"
    )

    utils.salvar_mapa(fig, "mapa_infraestrutura_logistica", "modulo3")


# ==========================================================================
# 4. MAPA DE BIOMAS E UNIDADES DE CONSERVAÇÃO
# ==========================================================================

def mapa_biomas_e_ucs(gdf_sudeste, camadas_amb):
    """
    Gera mapa dos biomas brasileiros na região Sudeste com sobreposição
    das Unidades de Conservação.

    Os biomas influenciam diretamente:
    - O potencial agrícola (Von Thünen): Mata Atlântica vs Cerrado
    - As restrições ambientais para localização industrial (Weber)
    - A vocação econômica regional (APLs agrícolas × industriais)
    """
    print("\n--- Mapa: Biomas e Unidades de Conservação ---")

    fig, ax = utils.criar_figura_mapa(figsize=(16, 12))

    # Cores dos biomas brasileiros
    cores_biomas = {
        "Amazônia": "#006400",
        "Caatinga": "#DAA520",
        "Cerrado": "#8B4513",
        "Mata Atlântica": "#228B22",
        "Pampa": "#90EE90",
        "Pantanal": "#4682B4",
    }

    # Plotar biomas
    if "biomas" in camadas_amb and len(camadas_amb["biomas"]) > 0:
        biomas = camadas_amb["biomas"]

        # Identificar coluna de nome do bioma
        col_nome = None
        for c in biomas.columns:
            if c.upper() in ["BIOMA", "NM_BIOMA", "NOME", "NM"]:
                col_nome = c
                break
        if col_nome is None:
            # Tentar encontrar coluna que não seja geometry
            cols_texto = [c for c in biomas.columns
                          if c != "geometry" and biomas[c].dtype == object]
            if cols_texto:
                col_nome = cols_texto[0]

        if col_nome:
            for bioma_nome, cor in cores_biomas.items():
                subset = biomas[biomas[col_nome].str.contains(
                    bioma_nome, case=False, na=False
                )]
                if len(subset) > 0:
                    subset.plot(ax=ax, color=cor, alpha=0.35, edgecolor=cor,
                                linewidth=0.5)
        else:
            biomas.plot(ax=ax, cmap="Set3", alpha=0.35)

    # Limites municipais suaves
    gdf_sudeste.boundary.plot(ax=ax, color="#AAAAAA", linewidth=0.05)

    # Limites estaduais
    uf_dissolve = gdf_sudeste.dissolve(by="SIGLA_UF")
    uf_dissolve.boundary.plot(ax=ax, color="#333333", linewidth=1.3)

    # Unidades de conservação (hachurado)
    if "ucs" in camadas_amb and len(camadas_amb["ucs"]) > 0:
        camadas_amb["ucs"].plot(
            ax=ax, facecolor="none", edgecolor="#2E7D32",
            linewidth=0.5, hatch="///", alpha=0.6
        )

    # Rótulos
    utils.adicionar_rotulos_uf(ax, gdf_sudeste)

    # Legenda
    legend_handles = []
    for bioma_nome, cor in cores_biomas.items():
        if "biomas" in camadas_amb and col_nome:
            if camadas_amb["biomas"][col_nome].str.contains(
                bioma_nome, case=False, na=False
            ).any():
                legend_handles.append(
                    Patch(facecolor=cor, alpha=0.5, label=bioma_nome)
                )
    legend_handles.append(
        Patch(facecolor="none", edgecolor="#2E7D32", hatch="///",
              label="Unidades de Conservação")
    )

    ax.legend(
        handles=legend_handles,
        title="Cobertura Natural",
        loc="lower left",
        fontsize=9, title_fontsize=10,
        frameon=True, fancybox=True, shadow=True, framealpha=0.9,
    )

    utils.formatar_eixos_mapa(
        ax,
        titulo="Biomas e Unidades de Conservação — Região Sudeste\n"
               "Restrições ambientais influenciam o modelo de localização (Weber/Von Thünen)",
    )

    ax.annotate(
        "Fontes: IBGE Biomas 2025, ICMBio/IBGE UC (Censo 2022)",
        xy=(0.5, -0.02), xycoords="axes fraction",
        ha="center", fontsize=7, color="#666"
    )

    utils.salvar_mapa(fig, "mapa_biomas_ucs", "modulo3")


# ==========================================================================
# 4.5. MAPA DE POTENCIALIDADE AGRÍCOLA
# ==========================================================================

def mapa_potencial_agricola(gdf_sudeste, camadas_amb):
    """
    Gera o mapa de terras agricultáveis (Aptidão Agrícola) do Sudeste.
    Essencial para o modelo de Von Thünen.
    """
    print("\n--- Mapa: Potencialidade Agrícola ---")
    if "potencial_agri" not in camadas_amb or len(camadas_amb["potencial_agri"]) == 0:
        print("  ✗ Camada de potencial agrícola não disponível")
        return

    fig, ax = utils.criar_figura_mapa(figsize=(16, 12))
    
    gdf_agri = camadas_amb["potencial_agri"]
    
    # Mapeamento de cores para as classes (A1, A2, B, C, D)
    cores_classes = {
        "A1": "#1B5E20", # Boa (Verde Escuro)
        "A2": "#4CAF50", # Boa a Regular (Verde Médio)
        "B": "#8BC34A",  # Regular (Verde Claro)
        "C": "#FFC107",  # Restrita (Amarelo)
        "D": "#FF5722",  # Inapta (Laranja/Vermelho)
    }
    
    # Plotar as classes
    for classe, cor in cores_classes.items():
        subset = gdf_agri[gdf_agri["potenc_f"] == classe]
        if len(subset) > 0:
            subset.plot(ax=ax, color=cor, alpha=0.8, edgecolor="none")
            
    # Limites estaduais
    uf_dissolve = gdf_sudeste.dissolve(by="SIGLA_UF")
    uf_dissolve.boundary.plot(ax=ax, color="#333333", linewidth=1.5)
    
    # Legenda
    legend_handles = []
    for classe, cor in cores_classes.items():
        if (gdf_agri["potenc_f"] == classe).any():
            legend_handles.append(Patch(facecolor=cor, label=f"Classe {classe}"))
            
    ax.legend(
        handles=legend_handles, title="Aptidão Agrícola",
        loc="lower left", fontsize=10, title_fontsize=11, framealpha=0.9
    )
    
    utils.formatar_eixos_mapa(ax, "Potencialidade Agrícola das Terras — Região Sudeste\nModelo de Von Thünen")
    utils.salvar_mapa(fig, "mapa_potencialidade_agricola", "modulo3")


# ==========================================================================
# 5. MAPA INTEGRADO COMPLETO (INFRA + AMBIENTE)
# ==========================================================================

def mapa_integrado_completo(gdf_sudeste, camadas_infra, camadas_amb):
    """
    Gera mapa final integrando infraestrutura logística sobre biomas,
    permitindo a análise conjunta de:
    - Corredores logísticos sobre diferentes biomas
    - Conflitos potenciais entre infraestrutura e conservação
    - Oportunidades para APLs baseados em vocação natural + acessibilidade

    Este mapa sintetiza as dimensões de oferta (infraestrutura) e
    restrição (ambiente) que moldam a localização das atividades econômicas.
    """
    print("\n--- Mapa: Integrado Completo (Infra + Ambiente) ---")

    fig, ax = utils.criar_figura_mapa(figsize=(18, 13))

    # Biomas como fundo
    cores_biomas = {
        "Amazônia": "#006400", "Caatinga": "#DAA520",
        "Cerrado": "#8B4513", "Mata Atlântica": "#228B22",
        "Pampa": "#90EE90", "Pantanal": "#4682B4",
    }

    if "biomas" in camadas_amb and len(camadas_amb["biomas"]) > 0:
        biomas = camadas_amb["biomas"]
        cols_texto = [c for c in biomas.columns
                      if c != "geometry" and biomas[c].dtype == object]
        col_nome = cols_texto[0] if cols_texto else None

        if col_nome:
            for bioma_nome, cor in cores_biomas.items():
                subset = biomas[biomas[col_nome].str.contains(
                    bioma_nome, case=False, na=False
                )]
                if len(subset) > 0:
                    subset.plot(ax=ax, color=cor, alpha=0.2)

    # Municípios (bordas suaves)
    gdf_sudeste.boundary.plot(ax=ax, color="#CCCCCC", linewidth=0.05)

    # Limites estaduais
    uf_dissolve = gdf_sudeste.dissolve(by="SIGLA_UF")
    uf_dissolve.boundary.plot(ax=ax, color="#222222", linewidth=1.5)

    # UCs
    if "ucs" in camadas_amb and len(camadas_amb["ucs"]) > 0:
        camadas_amb["ucs"].plot(
            ax=ax, facecolor="none", edgecolor="#2E7D32",
            linewidth=0.3, hatch="//", alpha=0.4
        )

    # Infraestrutura
    legend_elements = []

    if "rodovias" in camadas_infra and len(camadas_infra["rodovias"]) > 0:
        camadas_infra["rodovias"].plot(
            ax=ax, color=cfg.COR_RODOVIAS, linewidth=0.7, alpha=0.7
        )
        legend_elements.append(
            Line2D([0], [0], color=cfg.COR_RODOVIAS, lw=2, label="Rodovias")
        )

    if "ferrovias" in camadas_infra and len(camadas_infra["ferrovias"]) > 0:
        camadas_infra["ferrovias"].plot(
            ax=ax, color=cfg.COR_FERROVIAS, linewidth=0.8,
            linestyle="--", alpha=0.7
        )
        legend_elements.append(
            Line2D([0], [0], color=cfg.COR_FERROVIAS, lw=2,
                   ls="--", label="Ferrovias")
        )

    if "aeroportos" in camadas_infra and len(camadas_infra["aeroportos"]) > 0:
        camadas_infra["aeroportos"].plot(
            ax=ax, color=cfg.COR_AEROPORTOS, marker="*",
            markersize=50, alpha=0.9, zorder=5
        )
        legend_elements.append(
            Line2D([0], [0], marker="*", color="w",
                   markerfacecolor=cfg.COR_AEROPORTOS, ms=12, label="Aeroportos")
        )

    if "portos" in camadas_infra and len(camadas_infra["portos"]) > 0:
        camadas_infra["portos"].plot(
            ax=ax, color=cfg.COR_PORTOS, marker="^",
            markersize=50, alpha=0.9, zorder=5
        )
        legend_elements.append(
            Line2D([0], [0], marker="^", color="w",
                   markerfacecolor=cfg.COR_PORTOS, ms=12, label="Portos")
        )

    # Legendas de biomas
    for bioma_nome, cor in cores_biomas.items():
        if "biomas" in camadas_amb and col_nome:
            if camadas_amb["biomas"][col_nome].str.contains(
                bioma_nome, case=False, na=False
            ).any():
                legend_elements.append(
                    Patch(facecolor=cor, alpha=0.4, label=bioma_nome)
                )

    legend_elements.append(
        Patch(facecolor="none", edgecolor="#2E7D32", hatch="//",
              label="Unid. Conservação")
    )

    utils.adicionar_rotulos_uf(ax, gdf_sudeste)

    ax.legend(
        handles=legend_elements,
        title="Camadas",
        loc="lower left",
        fontsize=8, title_fontsize=9,
        frameon=True, fancybox=True, shadow=True, framealpha=0.9,
        ncol=2,
    )

    utils.formatar_eixos_mapa(
        ax,
        titulo="Mapa Integrado: Infraestrutura Logística × Biomas × Conservação\n"
               "Sudeste — Base para análise dos modelos de Weber e Von Thünen",
    )

    utils.salvar_mapa(fig, "mapa_integrado_infra_ambiente", "modulo3")


# ==========================================================================
# EXECUÇÃO PRINCIPAL
# ==========================================================================

def executar_modulo3(gdf_sudeste=None):
    """Executa todas as análises e mapas do Módulo 3."""
    print("\n" + "=" * 60)
    print("MÓDULO 3 — INFRAESTRUTURA, USO DO SOLO E MEIO AMBIENTE")
    print("=" * 60)

    if gdf_sudeste is None:
        gdf_sudeste = utils.carregar_municipios_sudeste()

    # Carregar camadas
    camadas_infra = carregar_camadas_infra(gdf_sudeste)
    camadas_amb = carregar_camadas_ambientais(gdf_sudeste)

    # Gerar mapas
    mapa_infraestrutura_logistica(gdf_sudeste, camadas_infra)
    mapa_biomas_e_ucs(gdf_sudeste, camadas_amb)
    mapa_potencial_agricola(gdf_sudeste, camadas_amb)
    mapa_integrado_completo(gdf_sudeste, camadas_infra, camadas_amb)

    print("\n✓ Módulo 3 concluído! Mapas salvos em output/modulo3/")


if __name__ == "__main__":
    executar_modulo3()
