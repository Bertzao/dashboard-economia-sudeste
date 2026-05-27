# -*- coding: utf-8 -*-
"""
==============================================================================
DASHBOARD ESTÁTICO DE ECONOMIA REGIONAL (SUDESTE)
==============================================================================
Gera uma única imagem consolidada (grid 3x3) com os 9 mapas geográficos.
"""

import os
import sys
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Patch
import numpy as np

# Configurar encoding UTF-8 no Windows
os.environ["PYTHONUTF8"] = "1"
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ==============================================================================
# CAMINHOS DOS DADOS
# ==============================================================================
PROJETO_DIR = r"d:\Projeto"
PBI_DIR = r"d:\Projeto_PowerBI"
OUTPUT_DIR = os.path.join(PROJETO_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SHP_MUNICIPIOS = os.path.join(PROJETO_DIR, "municipios e UF + população", "BR_Municipios_2025.shp")
CSV_DIM = os.path.join(PBI_DIR, "data_export", "cadastros", "dim_municipios_enriquecido.csv")
CSV_FATO = os.path.join(PBI_DIR, "data_export", "fatos", "fato_pib_vab_com_setor.csv")

# ==============================================================================
# 1. CARREGAMENTO E PREPARAÇÃO
# ==============================================================================
def carregar_dados():
    print("Carregando Shapefile...")
    gdf = gpd.read_file(SHP_MUNICIPIOS)
    gdf_se = gdf[gdf["CD_REGIAO"] == "3"].copy()
    gdf_se["CD_MUN"] = gdf_se["CD_MUN"].astype(str)
    
    print("Carregando Dados Tabulares...")
    dim = pd.read_csv(CSV_DIM, sep=";", dtype={"CD_MUN": str})
    fato = pd.read_csv(CSV_FATO, sep=";", dtype={"CD_MUN": str})
    
    # Filtrar fato para o último ano com dados válidos (2021)
    fato_2021 = fato[fato["Ano"] == 2021].copy()
    
    # Fazer os merges
    print("Mesclando bases...")
    df_merged = pd.merge(dim, fato_2021, on="CD_MUN", how="left")
    
    # Precisamos remover colunas duplicadas que já existem no GeoDataFrame para evitar _x e _y
    cols_to_use = [c for c in df_merged.columns if c not in gdf_se.columns] + ["CD_MUN"]
    df_merged = df_merged[cols_to_use]
    
    # Merge final com a geometria
    gdf_final = gdf_se.merge(df_merged, on="CD_MUN", how="left")
    
    # Converter numéricos
    for col in ["AREA_KM2", "VAB_Agropecuaria", "VAB_Industria", "VAB_Servicos"]:
        if col in gdf_final.columns:
            gdf_final[col] = pd.to_numeric(gdf_final[col], errors="coerce").fillna(0)
            
    # Garantir Flag_Conurbacao
    if "Flag_Conurbacao" not in gdf_final.columns:
        gdf_final["Flag_Conurbacao"] = gdf_final["CD_CONCURB"].apply(lambda x: "Conurbação" if pd.notna(x) else "Sem conurbação")
        
    return gdf_final

# ==============================================================================
# 2. FUNÇÕES AUXILIARES DE ESTILIZAÇÃO
# ==============================================================================
def style_ax(ax, title):
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.set_axis_off()

def plot_estados_contorno(ax, gdf):
    # Dissolve por estado para criar as bordas grossas
    uf_dissolve = gdf.dissolve(by="SIGLA_UF")
    uf_dissolve.boundary.plot(ax=ax, color="#111111", linewidth=1.2, zorder=2)

def custom_legend(ax, handles_dict, title, loc="lower right"):
    patches = [Patch(facecolor=c, edgecolor="#333", label=l) for l, c in handles_dict.items()]
    ax.legend(handles=patches, title=title, loc=loc, fontsize=7, title_fontsize=8, framealpha=0.9)

# ==============================================================================
# 3. LÓGICA DE PLOTAGEM POR MAPA
# ==============================================================================

def plot_mapa_area(ax, gdf):
    gdf.plot(column="AREA_KM2", ax=ax, cmap="YlGn", scheme="quantiles", k=7, 
             edgecolor="none", legend=True, legend_kwds={"loc": "lower right", "fontsize": 6, "fmt": "{:.0f}"})
    plot_estados_contorno(ax, gdf)
    style_ax(ax, "1. Área Municipal (km²)\nVerde escuro = Extenso / Agro")

def plot_mapa_estados(ax, gdf):
    cores_uf = {"MG": "#6BAED6", "ES": "#74C476", "RJ": "#FDB863", "SP": "#F06292"}
    for uf, cor in cores_uf.items():
        gdf[gdf["SIGLA_UF"] == uf].plot(ax=ax, color=cor, edgecolor="none")
    plot_estados_contorno(ax, gdf)
    custom_legend(ax, cores_uf, "Unidades da Federação", "lower right")
    style_ax(ax, "2. Limites Estaduais e Municipais")

def plot_mapa_imediatas(ax, gdf):
    gdf.plot(column="CD_RGI", ax=ax, cmap="Pastel1", edgecolor="#999", linewidth=0.1, categorical=True)
    plot_estados_contorno(ax, gdf)
    style_ax(ax, f"3. Regiões Geográficas Imediatas\n({gdf['CD_RGI'].nunique()} Regiões Locais)")

def plot_mapa_intermediarias(ax, gdf):
    gdf.plot(column="CD_RGINT", ax=ax, cmap="tab20", edgecolor="white", linewidth=0.2, categorical=True)
    # Limites das intermediárias
    rgint_dissolve = gdf.dissolve(by="CD_RGINT")
    rgint_dissolve.boundary.plot(ax=ax, color="#444", linewidth=0.5, zorder=2)
    plot_estados_contorno(ax, gdf)
    style_ax(ax, f"4. Regiões Geográficas Intermediárias\n({gdf['CD_RGINT'].nunique()} Polos Regionais)")

def plot_mapa_conurbacoes(ax, gdf):
    # Fundo cinza
    gdf.plot(ax=ax, color="#E0E0E0", edgecolor="white", linewidth=0.1)
    # Conurbações
    conurb = gdf[gdf["Flag_Conurbacao"] == "Conurbação"]
    if not conurb.empty:
        conurb.plot(column="CD_CONCURB", ax=ax, cmap="Set2", categorical=True, edgecolor="#555", linewidth=0.2)
    plot_estados_contorno(ax, gdf)
    leg = {"Conurbação": "#66C2A5", "Sem conurbação": "#E0E0E0"}
    custom_legend(ax, leg, "Aglomeração Urbana", "lower right")
    style_ax(ax, "5. Conurbações\n(Integração Funcional)")

def plot_mapa_setor_dominante(ax, gdf):
    cores_setor = {"Serviços": "#1F77B4", "Adm. Pública": "#9467BD", 
                   "Agropecuária": "#2CA02C", "Indústria": "#FF7F0E", "Sem dados": "#D9D9D9"}
    
    # Se a coluna não existir, usar cinza
    if "Setor_Dominante" not in gdf.columns:
        gdf["Setor_Dominante"] = "Sem dados"
        
    for setor, cor in cores_setor.items():
        subset = gdf[gdf["Setor_Dominante"] == setor]
        if not subset.empty:
            subset.plot(ax=ax, color=cor, edgecolor="none")
            
    plot_estados_contorno(ax, gdf)
    
    # Legenda apenas com setores presentes
    presentes = {k: v for k, v in cores_setor.items() if k in gdf["Setor_Dominante"].unique()}
    custom_legend(ax, presentes, "Setor Dominante (VAB)", "lower right")
    style_ax(ax, "6. Vocação Econômica Municipal")

def plot_mapa_von_thunen(ax, gdf):
    gdf.plot(column="VAB_Agropecuaria", ax=ax, cmap="YlGn", scheme="quantiles", k=7, 
             edgecolor="none", legend=True, legend_kwds={"loc": "lower right", "fontsize": 6})
    
    # Ponto de São Paulo
    sp = gdf[gdf["CD_MUN"] == "3550308"]
    if not sp.empty:
        sp.centroid.plot(ax=ax, color="#E91E63", markersize=30, zorder=3)
        
    plot_estados_contorno(ax, gdf)
    style_ax(ax, "7. Von Thünen: VAB Agropecuário\n(Distância de SP Central)")

def plot_mapa_weber(ax, gdf):
    gdf.plot(column="VAB_Industria", ax=ax, cmap="OrRd", scheme="quantiles", k=7, 
             edgecolor="none", legend=True, legend_kwds={"loc": "lower right", "fontsize": 6})
    plot_estados_contorno(ax, gdf)
    style_ax(ax, "8. Weber: VAB Industrial\n(Corredores Logísticos)")

def plot_mapa_christaller(ax, gdf):
    # Fundo serviços
    gdf.plot(column="VAB_Servicos", ax=ax, cmap="PuBu", scheme="quantiles", k=7, 
             edgecolor="none", legend=True, legend_kwds={"loc": "lower right", "fontsize": 6})
    
    # Top 10 cidades por serviços
    top10 = gdf.nlargest(10, "VAB_Servicos")
    if not top10.empty:
        # Calcular centroides para os pontos
        centroids = top10.geometry.centroid
        centroids.plot(ax=ax, color="#E91E63", markersize=15, alpha=0.8, zorder=3)
        
    plot_estados_contorno(ax, gdf)
    style_ax(ax, "9. Christaller: VAB Serviços\n(Lugares Centrais Top 10)")

# ==============================================================================
# 4. ORQUESTRAÇÃO DO DASHBOARD
# ==============================================================================
def gerar_dashboard():
    gdf = carregar_dados()
    
    print("Desenhando o dashboard...")
    plt.rcParams.update({"font.family": "sans-serif"})
    fig, axes = plt.subplots(3, 3, figsize=(24, 20))
    fig.patch.set_facecolor("#FAFAFA")
    
    # Título Geral
    fig.suptitle("DASHBOARD DE ECONOMIA REGIONAL E URBANA — SUDESTE DO BRASIL", 
                 fontsize=24, fontweight="bold", y=0.96)
    
    axes_flat = axes.flatten()
    
    # Mapeamento funções -> eixos
    funcs = [
        plot_mapa_area,
        plot_mapa_estados,
        plot_mapa_imediatas,
        plot_mapa_intermediarias,
        plot_mapa_conurbacoes,
        plot_mapa_setor_dominante,
        plot_mapa_von_thunen,
        plot_mapa_weber,
        plot_mapa_christaller
    ]
    
    for ax, func in zip(axes_flat, funcs):
        try:
            func(ax, gdf)
        except Exception as e:
            print(f"Erro ao plotar {func.__name__}: {e}")
            ax.set_title(f"Erro: {func.__name__}")
            ax.set_axis_off()

    # Rodapé
    fig.text(0.5, 0.02, "Fonte dos Dados: IBGE (Malhas Municipais 2025, Contas Regionais 2021) | Elaboração Própria", 
             ha="center", fontsize=12, color="#666666")

    # Ajuste de layout
    plt.tight_layout(rect=[0.02, 0.03, 0.98, 0.95], w_pad=2, h_pad=2)
    
    saida_png = os.path.join(OUTPUT_DIR, "dashboard_sudeste_consolidado.png")
    print(f"Salvando imagem em alta resolução: {saida_png}")
    fig.savefig(saida_png, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    
    print("Concluído com sucesso!")

if __name__ == "__main__":
    gerar_dashboard()
