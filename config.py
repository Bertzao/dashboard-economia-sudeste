# -*- coding: utf-8 -*-
"""
============================================================================
CONFIGURAÇÕES CENTRAIS DO PROJETO
Economia Regional e Urbana — Análise da Região Sudeste do Brasil
============================================================================
Define caminhos de dados, parâmetros de CRS, paletas de cores e constantes
reutilizadas em todos os módulos.
"""

import os
import sys

# Forçar UTF-8 no Windows (evita erros com caracteres Unicode)
os.environ["PYTHONUTF8"] = "1"
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import matplotlib as mpl
import matplotlib.pyplot as plt

# ==========================================================================
# 1. DIRETÓRIO RAIZ DO PROJETO
# ==========================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ==========================================================================
# 2. CAMINHOS DOS DADOS
# ==========================================================================

# --- Shapefiles ---
SHP_MUNICIPIOS = os.path.join(BASE_DIR, "municipios e UF + população",
                              "BR_Municipios_2025.shp")

# --- Infraestrutura logística ---
INFRA_DIR = os.path.join(BASE_DIR, "Infra")
SHP_RODOVIAS = os.path.join(INFRA_DIR, "2014 rodoviario",
                            "eixo_rodoviario_estruturante_2014.shp")
SHP_RODOVIAS_FULL = os.path.join(INFRA_DIR, "2014 rodoviario",
                                  "rodovia_2014.shp")
SHP_FERROVIAS = os.path.join(INFRA_DIR, "BaseFerro", "BaseFerro.shp")
SHP_AEROPORTOS = os.path.join(INFRA_DIR, "BaseAero", "BaseAero.shp")
SHP_PORTOS = os.path.join(INFRA_DIR, "BaseHidroPortos", "BaseHidroPortos.shp")
SHP_HIDROVIAS = os.path.join(INFRA_DIR, "fc_hidro_hidrovia_antaq.shp")

# --- Meio ambiente e uso do solo ---
USO_DIR = os.path.join(BASE_DIR, "Uso da terra")
SHP_BIOMAS = os.path.join(USO_DIR, "lml_bioma_e250k_v20250911_A.shp")
SHP_UCS = os.path.join(USO_DIR, "BR_UC_UF_Publicacao_CD2022",
                       "BR_UC_UF_Publicacao_CD2022.shp")
SHP_POTENCIAL_AGRI = os.path.join(USO_DIR, "Potencialidade_agricola.shp")
SHP_POTENCIALIDADE_AGRICOLA = os.path.join(USO_DIR, "Potencialidade_agricola.shp")

# --- Planilhas populacionais (SIDRA/Censo) ---
POP_DIR = os.path.join(BASE_DIR, "populaçao")
XLS_POP_IDADE = os.path.join(POP_DIR, "sidra_populacao_por_idade.xlsx")     # Pop por grupo de idade
XLS_POP_RACA = os.path.join(POP_DIR, "sidra_populacao_por_raca.xlsx")       # Pop por cor/raça
XLS_POP_INDIGENA = os.path.join(POP_DIR, "sidra_populacao_indigena.xlsx")   # Pop indígena
XLS_POP_QUILOMB = os.path.join(POP_DIR, "sidra_populacao_quilombola.xlsx")  # Pop quilombola

# --- Planilhas de atividade econômica (SIDRA) ---
ECON_DIR = os.path.join(BASE_DIR, "Atividade Econômica")
XLS_PAM = os.path.join(ECON_DIR, "sidra_pam_lavouras.xlsx")          # PAM – Lavouras
XLS_PIA = os.path.join(ECON_DIR, "sidra_pia_industria.xlsx")         # PIA – Indústria
XLS_PAS = os.path.join(ECON_DIR, "sidra_pas_servicos.xlsx")          # PAS – Serviços
XLS_PAS_DET = os.path.join(ECON_DIR, "sidra_pas_detalhado_cnae.xlsx")# PAS detalhado CNAE
XLS_COMERCIO = os.path.join(ECON_DIR, "sidra_pac_comercio.xlsx")     # Comércio
XLS_CONSTRUCAO = os.path.join(ECON_DIR, "sidra_paic_construcao.xlsx")# Construção civil
XLS_EMPRESAS = os.path.join(ECON_DIR, "sidra_empresas_cnae.xlsx")    # Empresas CNAE
XLS_EXTRACAO = os.path.join(ECON_DIR, "sidra_extracao_vegetal.xlsx") # Extração vegetal
XLS_PIA_PROD = os.path.join(ECON_DIR, "sidra_pia_produto.xlsx")      # PIA Produto
XLS_PIB_MUNICIPIOS = os.path.join(ECON_DIR,
    "PIB dos Municípios - base de dados 2010-2023.xlsx")       # PIB Municipal IBGE
XLS_PIB = os.path.join(USO_DIR,
    "Produto interno bruto a preços correntes, impostos, líquidos de "
    "subsídios, sobre produtos a preços correntes.xlsx")

# ==========================================================================
# 3. DIRETÓRIO DE SAÍDA (MAPAS E FIGURAS)
# ==========================================================================
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
for mod in ["modulo1", "modulo2", "modulo3", "modulo4", "modulo4_1", "modulo5"]:
    os.makedirs(os.path.join(OUTPUT_DIR, mod), exist_ok=True)

# ==========================================================================
# 4. SISTEMA DE REFERÊNCIA DE COORDENADAS (CRS)
# ==========================================================================
# SIRGAS 2000 — padrão oficial do Brasil
CRS_PADRAO = "EPSG:4674"
# CRS projetado para cálculos de área/distância (metros)
CRS_PROJETADO = "EPSG:5880"   # SIRGAS 2000 / Brazil Polyconic

# ==========================================================================
# 5. FILTROS GEOGRÁFICOS — REGIÃO SUDESTE
# ==========================================================================
COD_REGIAO_SUDESTE = "3"
UFS_SUDESTE = {"MG": "31", "ES": "32", "RJ": "33", "SP": "35"}
SIGLAS_SUDESTE = list(UFS_SUDESTE.keys())
NOMES_UF = {
    "31": "Minas Gerais",
    "32": "Espírito Santo",
    "33": "Rio de Janeiro",
    "35": "São Paulo",
}

# ==========================================================================
# 6. API SIDRA — VAB MUNICIPAL
# ==========================================================================
SIDRA_BASE_URL = "https://apisidra.ibge.gov.br/values"
SIDRA_VAB_TABLE = "5938"
SIDRA_VAB_VARS = {
    "37":   "PIB",
    "513":  "VAB_Agropecuaria",
    "517":  "VAB_Industria",
    "6575": "VAB_Servicos",
    "525":  "VAB_Adm_Publica",
}

# ==========================================================================
# 7. PALETA DE CORES E ESTILOS VISUAIS
# ==========================================================================

# Cores por UF (identidade visual)
CORES_UF = {
    "MG": "#2196F3",   # Azul
    "ES": "#4CAF50",   # Verde
    "RJ": "#FF9800",   # Laranja
    "SP": "#E91E63",   # Rosa/Magenta
}

# Paletas para mapas coropléticos
CMAP_POPULACAO = "YlOrRd"
CMAP_ECONOMIA = "PuBuGn"
CMAP_AREA = "YlGn"
CMAP_ENVELHECIMENTO = "RdYlBu_r"
CMAP_QL = "RdYlGn"
CMAP_SETORIAL = {
    "agropecuaria": "YlGn",
    "industria":    "OrRd",
    "servicos":     "PuBu",
    "adm_publica":  "BuPu",
}

# Cores de camadas de infraestrutura
COR_RODOVIAS = "#D32F2F"
COR_FERROVIAS = "#212121"
COR_AEROPORTOS = "#C62828"
COR_PORTOS = "#1565C0"
COR_HIDROVIAS = "#0288D1"

# ==========================================================================
# 8. CONFIGURAÇÃO GLOBAL DO MATPLOTLIB
# ==========================================================================
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "Arial", "DejaVu Sans"],
    "font.size": 10,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "figure.facecolor": "white",
    "axes.facecolor": "#F5F5F5",
    "axes.edgecolor": "#CCCCCC",
    "axes.grid": False,
})

# ==========================================================================
# 9. VERIFICAÇÃO DE INTEGRIDADE DOS CAMINHOS
# ==========================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("VERIFICAÇÃO DE CAMINHOS DE DADOS")
    print("=" * 60)
    paths = {
        "Shapefile Municípios": SHP_MUNICIPIOS,
        "Rodovias Estruturantes": SHP_RODOVIAS,
        "Ferrovias": SHP_FERROVIAS,
        "Aeroportos": SHP_AEROPORTOS,
        "Portos": SHP_PORTOS,
        "Biomas": SHP_BIOMAS,
        "Unidades de Conservação": SHP_UCS,
        "Pop. por Idade": XLS_POP_IDADE,
        "Pop. por Raça": XLS_POP_RACA,
        "PAM (Agricultura)": XLS_PAM,
        "PIA (Indústria)": XLS_PIA,
        "PAS (Serviços)": XLS_PAS,
        "Empresas CNAE": XLS_EMPRESAS,
    }
    for nome, caminho in paths.items():
        status = "✓" if os.path.exists(caminho) else "✗ NÃO ENCONTRADO"
        print(f"  {status}  {nome}")
        if not os.path.exists(caminho):
            print(f"         → {caminho}")
    print("=" * 60)
