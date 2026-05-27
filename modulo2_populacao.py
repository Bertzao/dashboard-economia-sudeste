# -*- coding: utf-8 -*-
"""
============================================================================
MÓDULO 2 — ESTRUTURA POPULACIONAL
Economia Regional e Urbana — Análise da Região Sudeste do Brasil
============================================================================

Objetivo:
    Analisar a distribuição e composição da população na região Sudeste,
    com foco em:
    - População total e densidade demográfica por UF
    - Estrutura etária e índice de envelhecimento
    - Composição por cor/raça
    - Presença de populações tradicionais (indígena e quilombola)

Relevância para políticas públicas:
    A estrutura demográfica determina a demanda por serviços públicos
    e a oferta de mão-de-obra. O envelhecimento populacional impacta
    diretamente a produtividade regional e a dependência fiscal.
    No modelo de Christaller, cidades com maior população tendem a
    oferecer serviços de maior ordem hierárquica.

Fontes:
    - IBGE, Censo Demográfico 2022 (Tabelas SIDRA 1209, 9606, 8175, 8176)
    - IBGE, Malha Municipal 2025
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Patch
import seaborn as sns

import config as cfg
import utils


# ==========================================================================
# 1. CARREGAMENTO E PROCESSAMENTO DOS DADOS POPULACIONAIS
# ==========================================================================

def carregar_populacao_por_idade():
    """
    Carrega a Tabela SIDRA 1209 — População por grupos de idade.
    Estrutura: UF × grupos de idade (0-4, 5-9, ..., 80+) × censos históricos.

    O cabeçalho possui 5 linhas de metadados:
    - Linha 0: título da tabela
    - Linha 1: variável
    - Linha 2: rótulos de dimensões
    - Linha 3: ano (1872, 1890, ..., 2022)
    - Linha 4: grupos de idade (Total, 0-4, 5-9, ...)

    Para este projeto, focaremos nos dados do Censo 2022.

    Returns
    -------
    pandas.DataFrame
        Colunas: UF, Total, 0_4, 5_9, ..., 80_mais
    """
    print("\n--- Carregando população por grupo de idade (Tabela 1209) ---")

    try:
        df_raw = pd.read_excel(cfg.XLS_POP_IDADE, header=None)

        # Identificar as colunas do Censo 2022
        # Linha 3 contém os anos; procurar a última ocorrência de 2022
        linha_anos = df_raw.iloc[3, :]
        cols_2022 = [i for i, v in enumerate(linha_anos) if str(v).strip() == "2022"]

        if not cols_2022:
            print("  ✗ Ano 2022 não encontrado na tabela 1209")
            return None

        # Linha 4 contém os grupos de idade para 2022
        inicio_2022 = cols_2022[0]
        linha_grupos = df_raw.iloc[4, inicio_2022:]

        # Encontrar até onde vão os grupos de 2022
        # (até o próximo ano ou fim da tabela)
        grupos_2022 = []
        for i in range(inicio_2022, len(df_raw.columns)):
            val = df_raw.iloc[4, i]
            if pd.notna(val):
                grupos_2022.append((i, str(val).strip()))
            else:
                break

        # Dados: linhas 5 em diante (excluir 'Brasil' e 'Fonte:')
        dados = []
        for idx in range(5, len(df_raw)):
            uf = df_raw.iloc[idx, 0]
            if pd.isna(uf) or "Fonte:" in str(uf):
                continue
            row = {"UF": str(uf).strip()}
            for col_idx, grupo_nome in grupos_2022:
                val = df_raw.iloc[idx, col_idx]
                nome_limpo = grupo_nome.replace(" ", "_").replace("anos", "").strip("_")
                row[nome_limpo] = pd.to_numeric(val, errors="coerce")
            dados.append(row)

        df = pd.DataFrame(dados)
        print(f"  ✓ Tabela 1209: {len(df)} UFs, {len(df.columns)-1} grupos de idade")
        return df

    except Exception as e:
        print(f"  ✗ Erro ao carregar tabela 1209: {e}")
        return None


def carregar_populacao_por_raca():
    """
    Carrega a Tabela SIDRA 9606 — População por cor/raça, sexo e idade.
    Foco: totais por UF, Censo 2022.

    Returns
    -------
    pandas.DataFrame
        Colunas: UF, Pop_Total_2022, Pop_Homens_2022, Pop_Mulheres_2022
    """
    print("\n--- Carregando população por cor/raça (Tabela 9606) ---")

    try:
        df_raw = pd.read_excel(cfg.XLS_POP_RACA, header=None)

        dados = []
        uf_atual = None

        for idx in range(6, len(df_raw)):
            col0 = df_raw.iloc[idx, 0]
            col1 = df_raw.iloc[idx, 1]

            if pd.notna(col0) and "Fonte:" not in str(col0):
                uf_atual = str(col0).strip()

            if uf_atual and str(col1).strip() == "Total":
                # Tabela 9606 (1)
                # Colunas 2022:
                # 20=Total, 23=Branca, 26=Preta, 29=Amarela, 32=Parda, 35=Indígena
                
                # Valores 2010 (para evolução, caso precise):
                # 2=Total, 5=Branca, etc.
                row = {
                    "UF": uf_atual,
                    "Pop_Total_2010": pd.to_numeric(df_raw.iloc[idx, 2], errors="coerce"),
                    "Pop_Total_2022": pd.to_numeric(df_raw.iloc[idx, 20], errors="coerce"),
                    "Pop_Branca_2022": pd.to_numeric(df_raw.iloc[idx, 23], errors="coerce"),
                    "Pop_Preta_2022": pd.to_numeric(df_raw.iloc[idx, 26], errors="coerce"),
                    "Pop_Amarela_2022": pd.to_numeric(df_raw.iloc[idx, 29], errors="coerce"),
                    "Pop_Parda_2022": pd.to_numeric(df_raw.iloc[idx, 32], errors="coerce"),
                    "Pop_Indigena_2022": pd.to_numeric(df_raw.iloc[idx, 35], errors="coerce"),
                }
                dados.append(row)
                uf_atual = None  # Reset para evitar duplicatas

        df = pd.DataFrame(dados)
        print(f"  ✓ Tabela 9606: {len(df)} UFs com composição racial carregada")
        return df

    except Exception as e:
        print(f"  ✗ Erro ao carregar tabela 9606: {e}")
        return None


def carregar_populacao_tradicional():
    """
    Carrega dados de populações tradicionais (etnias):
    - Tabela 8175: População indígena
    - Tabela 8176: População quilombola
    """
    print("\n--- Carregando populações tradicionais (Indígena e Quilombola) ---")
    resultados = []
    
    # UFs do Sudeste
    ufs_alvo = [cfg.NOMES_UF[s] for s in cfg.UFS_SUDESTE.values()]

    # 1. População Indígena (Tabela 8175)
    try:
        df_ind = pd.read_excel(cfg.XLS_POP_INDIGENA, header=None)
        # O total de 2022 está na coluna 404, e os nomes das UFs na coluna 0
        for idx in range(6, len(df_ind)):
            uf = str(df_ind.iloc[idx, 0]).strip()
            if pd.notna(df_ind.iloc[idx, 0]) and "Fonte" not in uf:
                if uf in ufs_alvo:
                    val = pd.to_numeric(df_ind.iloc[idx, 404], errors="coerce")
                    resultados.append({"UF": uf, "Pop_Indigena": val})
        print(f"  ✓ Tabela 8175: População indígena carregada")
    except Exception as e:
        print(f"  ✗ Erro na tabela 8175: {e}")

    df_trad = pd.DataFrame(resultados)

    # 2. População Quilombola (Tabela 8176)
    try:
        df_qui = pd.read_excel(cfg.XLS_POP_QUILOMB, header=None)
        # O total de 2022 está na coluna 2, e os nomes das UFs na coluna 0
        qui_dict = {}
        for idx in range(6, len(df_qui)):
            uf = str(df_qui.iloc[idx, 0]).strip()
            if pd.notna(df_qui.iloc[idx, 0]) and "Fonte" not in uf:
                if uf in ufs_alvo:
                    val = pd.to_numeric(df_qui.iloc[idx, 2], errors="coerce")
                    qui_dict[uf] = val
        
        # Merge com indígena
        if not df_trad.empty:
            df_trad["Pop_Quilombola"] = df_trad["UF"].map(qui_dict)
        else:
            df_trad = pd.DataFrame([{"UF": k, "Pop_Quilombola": v} for k, v in qui_dict.items()])
            
        print(f"  ✓ Tabela 8176: População quilombola carregada")
    except Exception as e:
        print(f"  ✗ Erro na tabela 8176: {e}")

    return df_trad if not df_trad.empty else None


def calcular_indice_envelhecimento(df_idade):
    """
    Calcula o Índice de Envelhecimento por UF.

    Índice de Envelhecimento = (Pop 60+ / Pop 0-14) × 100

    Um IE > 100 indica que há mais idosos que jovens — fenômeno de
    transição demográfica avançada, típico de estados mais urbanizados.

    Relevância para políticas públicas:
        Regiões envelhecidas demandam mais serviços de saúde e previdência.
        Do ponto de vista econômico (Weber), a mão-de-obra disponível
        diminui, elevando o custo do fator trabalho para indústrias.

    Parameters
    ----------
    df_idade : pandas.DataFrame
        DataFrame com grupos de idade por UF.

    Returns
    -------
    pandas.DataFrame
        DataFrame com colunas: UF, Pop_Jovem, Pop_Idosa, Indice_Envelhecimento
    """
    print("\n--- Calculando Índice de Envelhecimento ---")

    resultados = []
    for _, row in df_idade.iterrows():
        uf = row["UF"]
        total = pd.to_numeric(row.get("Total", 0), errors="coerce") or 0

        # Somar jovens e idosos usando os nomes reais das colunas
        pop_jovem = 0
        pop_idosa = 0

        for col in row.index:
            if col in ["UF", "Total"]:
                continue
            val = pd.to_numeric(row.get(col, 0), errors="coerce") or 0
            col_lower = col.lower()
            # Jovens: 0 a 4, 5 a 9, 10 a 14
            if any(x in col_lower for x in ["0_a_4", "5_a_9", "10_a_14"]):
                pop_jovem += val
            # Idosos: 60+ (60 a 69, 70 ou mais, etc.)
            elif any(x in col_lower for x in ["60", "70", "80", "90", "100"]):
                pop_idosa += val

        ie = (pop_idosa / pop_jovem * 100) if pop_jovem > 0 else 0

        resultados.append({
            "UF": uf,
            "Pop_Total": total,
            "Pop_Jovem_0_14": pop_jovem,
            "Pop_Idosa_60_mais": pop_idosa,
            "Indice_Envelhecimento": round(ie, 2),
        })

    df_ie = pd.DataFrame(resultados)
    print(df_ie[df_ie["UF"].isin(cfg.NOMES_UF.values())].to_string(index=False))
    return df_ie


# ==========================================================================
# 2. MERGE COM DADOS GEOGRÁFICOS
# ==========================================================================

def merge_pop_geo(gdf_sudeste, df_pop):
    """
    Faz o join entre dados populacionais (nível UF) e os polígonos municipais.
    Como os dados populacionais são por UF, o merge é feito pela sigla da UF.
    A população é atribuída ao nível estadual (dissolve dos municípios).

    Parameters
    ----------
    gdf_sudeste : geopandas.GeoDataFrame
        GeoDataFrame dos municípios do Sudeste.
    df_pop : pandas.DataFrame
        DataFrame com dados populacionais por UF.

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame dissolve por UF com dados populacionais.
    """
    print("\n--- Merge população × geometria ---")

    # Criar mapeamento UF nome → sigla
    nome_para_sigla = {v: k for k, v in zip(
        cfg.SIGLAS_SUDESTE,
        [cfg.NOMES_UF[cfg.UFS_SUDESTE[s]] for s in cfg.SIGLAS_SUDESTE]
    )}

    df_pop = df_pop.copy()
    df_pop["SIGLA_UF"] = df_pop["UF"].map(nome_para_sigla)
    df_pop_sudeste = df_pop[df_pop["SIGLA_UF"].notna()].copy()

    # Dissolve dos municípios por UF
    gdf_uf = gdf_sudeste.dissolve(by="SIGLA_UF", aggfunc={"AREA_KM2": "sum"})
    gdf_uf = gdf_uf.reset_index()

    # Merge
    gdf_merged = gdf_uf.merge(df_pop_sudeste, on="SIGLA_UF", how="left")

    # Calcular densidade
    if "Pop_Total" in gdf_merged.columns:
        gdf_merged["Densidade_hab_km2"] = (
            gdf_merged["Pop_Total"] / gdf_merged["AREA_KM2"]
        ).round(2)

    print(f"  ✓ Merge realizado: {len(gdf_merged)} UFs")
    return gdf_merged


# ==========================================================================
# 3. MAPAS — POPULAÇÃO
# ==========================================================================

def mapa_populacao_por_uf(gdf_sudeste, df_pop):
    """
    Gera mapa choropleth da população total por UF do Sudeste.

    No modelo de Christaller, a população é determinante para a
    classificação hierárquica das cidades. São Paulo, como metrópole
    nacional, está no topo da hierarquia de Christaller.
    """
    print("\n--- Mapa: População Total por UF ---")

    gdf_merged = merge_pop_geo(gdf_sudeste, df_pop)

    fig, axes = plt.subplots(1, 2, figsize=(18, 9))

    # Mapa 1: População Total
    gdf_merged.plot(
        column="Pop_Total",
        ax=axes[0],
        cmap=cfg.CMAP_POPULACAO,
        edgecolor="#333",
        linewidth=1.5,
        legend=True,
        legend_kwds={"label": "População (hab)", "shrink": 0.7},
    )
    for _, row in gdf_merged.iterrows():
        c = row.geometry.centroid
        pop_fmt = utils.formatar_numero_br(row.get("Pop_Total", 0))
        axes[0].annotate(
            f"{row['SIGLA_UF']}\n{pop_fmt}",
            xy=(c.x, c.y), ha="center", va="center",
            fontsize=10, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
        )
    utils.formatar_eixos_mapa(axes[0], "População Total por UF (Censo 2022)")

    # Mapa 2: Densidade Demográfica
    if "Densidade_hab_km2" in gdf_merged.columns:
        gdf_merged.plot(
            column="Densidade_hab_km2",
            ax=axes[1],
            cmap="OrRd",
            edgecolor="#333",
            linewidth=1.5,
            legend=True,
            legend_kwds={"label": "hab/km²", "shrink": 0.7},
        )
        for _, row in gdf_merged.iterrows():
            c = row.geometry.centroid
            dens = f"{row.get('Densidade_hab_km2', 0):.1f}"
            axes[1].annotate(
                f"{row['SIGLA_UF']}\n{dens} hab/km²",
                xy=(c.x, c.y), ha="center", va="center",
                fontsize=10, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
            )
        utils.formatar_eixos_mapa(axes[1], "Densidade Demográfica por UF (hab/km²)")

    fig.suptitle(
        "Estrutura Populacional da Região Sudeste — Censo 2022",
        fontsize=16, fontweight="bold", y=1.02
    )

    plt.tight_layout()
    utils.salvar_mapa(fig, "mapa_populacao_uf", "modulo2")


def mapa_envelhecimento(gdf_sudeste, df_ie):
    """
    Gera mapa do Índice de Envelhecimento por UF.

    IE = (Pop ≥60 / Pop 0-14) × 100

    Valores altos indicam transição demográfica avançada.
    RJ e SP tendem a ter IE mais elevados (urbanização, queda de natalidade).
    MG e ES, com regiões rurais extensas, podem ter IE mais variável.

    Relevância para Weber:
        O envelhecimento reduz a disponibilidade de mão-de-obra,
        aumentando o "custo do fator trabalho" na função weberiana
        de localização industrial.
    """
    print("\n--- Mapa: Índice de Envelhecimento ---")

    gdf_merged = merge_pop_geo(gdf_sudeste, df_ie)

    fig, ax = utils.criar_figura_mapa(figsize=(14, 11))

    if "Indice_Envelhecimento" in gdf_merged.columns:
        gdf_merged.plot(
            column="Indice_Envelhecimento",
            ax=ax,
            cmap=cfg.CMAP_ENVELHECIMENTO,
            edgecolor="#333",
            linewidth=1.5,
            legend=True,
            legend_kwds={"label": "Índice de Envelhecimento (%)", "shrink": 0.7},
        )

        for _, row in gdf_merged.iterrows():
            c = row.geometry.centroid
            ie_val = row.get("Indice_Envelhecimento", 0)
            ax.annotate(
                f"{row['SIGLA_UF']}\nIE: {ie_val:.1f}%",
                xy=(c.x, c.y), ha="center", va="center",
                fontsize=11, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.85),
            )

    utils.formatar_eixos_mapa(
        ax,
        titulo="Índice de Envelhecimento por UF — Sudeste (Censo 2022)\n"
               "IE = (Pop ≥ 60 / Pop 0-14) × 100 | IE > 100 → mais idosos que jovens",
    )

    ax.annotate(
        "Fonte: IBGE, Censo Demográfico 2022 (Tabela SIDRA 1209)",
        xy=(0.5, -0.02), xycoords="axes fraction",
        ha="center", fontsize=7, color="#666666"
    )

    utils.salvar_mapa(fig, "mapa_indice_envelhecimento", "modulo2")


def grafico_piramide_etaria(df_raca):
    """
    Gera pirâmides etárias comparativas 2010 × 2022 para a região Sudeste.

    A pirâmide permite visualizar a transição demográfica em curso:
    estreitamento da base (menos jovens) e alargamento do topo (mais idosos).
    """
    print("\n--- Gráfico: Comparativo Populacional 2010 × 2022 ---")

    if df_raca is None:
        print("  ✗ Dados de raça/sexo não disponíveis")
        return

    # Filtrar apenas UFs do Sudeste
    nomes = list(cfg.NOMES_UF.values())
    df_se = df_raca[df_raca["UF"].isin(nomes)].copy()

    if len(df_se) == 0:
        print("  ✗ Nenhuma UF do Sudeste encontrada nos dados")
        return

    fig, ax = plt.subplots(figsize=(12, 7))

    x = np.arange(len(df_se))
    width = 0.35

    bars_2010 = ax.bar(x - width/2, df_se["Pop_Total_2010"] / 1e6,
                        width, label="2010", color="#42A5F5", edgecolor="white")
    bars_2022 = ax.bar(x + width/2, df_se["Pop_Total_2022"] / 1e6,
                        width, label="2022", color="#EF5350", edgecolor="white")

    ax.set_xticks(x)
    ax.set_xticklabels(df_se["UF"], fontsize=11, fontweight="bold")
    ax.set_ylabel("População (milhões)", fontsize=12)
    ax.set_title("Evolução Populacional — Sudeste (2010 × 2022)",
                 fontsize=14, fontweight="bold")
    ax.legend(fontsize=11)

    # Adicionar valores nas barras
    for bar in bars_2010:
        h = bar.get_height()
        ax.annotate(f"{h:.1f}M", xy=(bar.get_x() + bar.get_width()/2, h),
                    ha="center", va="bottom", fontsize=8)
    for bar in bars_2022:
        h = bar.get_height()
        ax.annotate(f"{h:.1f}M", xy=(bar.get_x() + bar.get_width()/2, h),
                    ha="center", va="bottom", fontsize=8)

    ax.set_facecolor("#F5F5F5")
    fig.patch.set_facecolor("white")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    utils.salvar_mapa(fig, "grafico_evolucao_populacional", "modulo2")


def grafico_composicao_racial(df_raca):
    """
    Gera gráfico de barras empilhadas 100% da composição étnico-racial
    por UF do Sudeste, permitindo comparação visual da estrutura.
    """
    print("\n--- Gráfico: Composição Étnico-Racial (Cor ou Raça) ---")

    if df_raca is None or df_raca.empty:
        print("  ✗ Dados de cor/raça não disponíveis")
        return

    nomes = list(cfg.NOMES_UF.values())
    df_se = df_raca[df_raca["UF"].isin(nomes)].copy()

    if len(df_se) == 0:
        return

    racas = ["Pop_Branca_2022", "Pop_Preta_2022", "Pop_Parda_2022", "Pop_Amarela_2022", "Pop_Indigena_2022"]
    labels = ["Branca", "Preta", "Parda", "Amarela", "Indígena"]
    colors = ["#FFE0B2", "#5D4037", "#8D6E63", "#FFCA28", "#D84315"]

    # Calcular proporções
    df_se_prop = df_se.set_index("UF")[racas].div(df_se.set_index("UF")[racas].sum(axis=1), axis=0) * 100

    fig, ax = plt.subplots(figsize=(10, 6))
    
    bottom = np.zeros(len(df_se_prop))
    for i, raca in enumerate(racas):
        # Usar .values para não herdar o index do pandas no bottom
        ax.bar(df_se_prop.index, df_se_prop[raca], bottom=bottom, label=labels[i], color=colors[i], edgecolor="white")
        
        # Adicionar porcentagens para fatias maiores que 3%
        for j, val in enumerate(df_se_prop[raca]):
            if val > 3:
                ax.text(j, bottom[j] + val/2, f"{val:.1f}%", ha="center", va="center", color="black", fontsize=9, fontweight="bold")
        
        bottom += df_se_prop[raca].values

    ax.set_ylabel("Proporção (%)", fontsize=12)
    ax.set_title("Composição Populacional por Cor/Raça — Sudeste (Censo 2022)", fontsize=14, fontweight="bold")
    
    # Legenda fora do gráfico
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=11)
    
    ax.set_facecolor("#F5F5F5")
    fig.patch.set_facecolor("white")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    
    plt.tight_layout()
    utils.salvar_mapa(fig, "grafico_composicao_racial", "modulo2")


def grafico_populacao_tradicional(df_trad):
    """
    Gera gráfico de barras para as populações tradicionais (Indígena e Quilombola).
    Relevância: Mostra a diversidade étnica e a necessidade de políticas 
    territoriais específicas para povos tradicionais na região Sudeste.
    """
    print("\n--- Gráfico: Populações Tradicionais (Indígena e Quilombola) ---")

    if df_trad is None or df_trad.empty:
        print("  ✗ Dados de populações tradicionais não disponíveis")
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(len(df_trad))
    width = 0.35

    bars_ind = ax.bar(x - width/2, df_trad.get("Pop_Indigena", 0),
                       width, label="Indígena", color="#8D6E63", edgecolor="white")
    bars_qui = ax.bar(x + width/2, df_trad.get("Pop_Quilombola", 0),
                       width, label="Quilombola", color="#5D4037", edgecolor="white")

    ax.set_xticks(x)
    ax.set_xticklabels(df_trad["UF"], fontsize=11, fontweight="bold")
    ax.set_ylabel("População (habitantes)", fontsize=12)
    ax.set_title("Populações Tradicionais (Indígenas e Quilombolas) por UF — Censo 2022",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=11)

    # Adicionar valores nas barras
    for bar in bars_ind:
        h = bar.get_height()
        if h > 0:
            ax.annotate(f"{int(h):,}".replace(",", "."), 
                        xy=(bar.get_x() + bar.get_width()/2, h),
                        ha="center", va="bottom", fontsize=9)
    for bar in bars_qui:
        h = bar.get_height()
        if h > 0:
            ax.annotate(f"{int(h):,}".replace(",", "."), 
                        xy=(bar.get_x() + bar.get_width()/2, h),
                        ha="center", va="bottom", fontsize=9)

    ax.set_facecolor("#F5F5F5")
    fig.patch.set_facecolor("white")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    utils.salvar_mapa(fig, "grafico_populacao_tradicional", "modulo2")


# ==========================================================================
# EXECUÇÃO PRINCIPAL
# ==========================================================================

def executar_modulo2(gdf_sudeste=None):
    """Executa todas as análises e mapas do Módulo 2."""
    print("\n" + "=" * 60)
    print("MÓDULO 2 — ESTRUTURA POPULACIONAL")
    print("=" * 60)

    if gdf_sudeste is None:
        gdf_sudeste = utils.carregar_municipios_sudeste()

    # Carregar dados
    df_idade = carregar_populacao_por_idade()
    df_raca = carregar_populacao_por_raca()
    df_trad = carregar_populacao_tradicional()

    # Calcular índice de envelhecimento
    df_ie = None
    if df_idade is not None:
        df_ie = calcular_indice_envelhecimento(df_idade)

    # Gerar mapas e gráficos
    if df_ie is not None:
        mapa_populacao_por_uf(gdf_sudeste, df_ie)
        mapa_envelhecimento(gdf_sudeste, df_ie)

    if df_raca is not None:
        grafico_piramide_etaria(df_raca)
        grafico_composicao_racial(df_raca)

    if df_trad is not None:
        grafico_populacao_tradicional(df_trad)

    print("\n✓ Módulo 2 concluído! Mapas salvos em output/modulo2/")


if __name__ == "__main__":
    executar_modulo2()
