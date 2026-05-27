# -*- coding: utf-8 -*-
"""
============================================================================
MÓDULO 4.1 — QUOCIENTE LOCACIONAL POR EMPREGOS (CEMPRE / SIDRAPY)
Economia Regional e Urbana — Análise da Região Sudeste do Brasil
============================================================================
Extrai dados da Tabela 9528 do IBGE (Pessoal ocupado assalariado) agrupados
por Seção CNAE diretamente da API do SIDRA para calcular o QL de empregos.
"""

import os
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns
import sidrapy

import config as cfg
import utils

def baixar_empregos_cempre():
    """Baixa Pessoal Ocupado Assalariado (Var 2973) por Seção CNAE."""
    print("\n--- Baixando Empregos do CEMPRE via sidrapy ---")
    
    cache_path = os.path.join(cfg.OUTPUT_DIR, "cempre_empregos_secao.csv")
    if os.path.exists(cache_path):
        print("  Carregando do cache local...")
        df_se = pd.read_csv(cache_path, dtype={"Município (Código)": str})
    else:
        print("  Consultando API do IBGE (isso pode levar de 30s a 2 min)...")
        try:
            # IDs das 21 Seções (A a U) da CNAE 2.0
            ids_secoes = ["116830", "116880", "116910", "117296", "117307", "117329", "117363", 
                          "117484", "117543", "117555", "117608", "117666", "117673", "117714", 
                          "117774", "117788", "117810", "117838", "117861", "117888", "117892"]
            dfs = []
            for i, sec_id in enumerate(ids_secoes, 1):
                print(f"    Baixando Seção {i}/21...", end="\r")
                df_sec = sidrapy.get_table(
                    table_code="9528",
                    territorial_level="6",
                    ibge_territorial_code="in n3 31,32,33,35",
                    variables="2973",
                    classifications={"12762": sec_id},
                    period="last"
                )
                df_sec = df_sec.rename(columns=df_sec.iloc[0]).drop(df_sec.index[0])
                dfs.append(df_sec)
            print("\n  ✓ Dados obtidos com sucesso.")
            df_emprego = pd.concat(dfs, ignore_index=True)
            df_emprego.to_csv(cache_path, index=False)
            df_se = df_emprego.copy()
        except Exception as e:
            print(f"\n  ✗ Erro na API do SIDRA: {e}")
            return None

    # O SIDRA retorna dados em formato longo. Precisamos pivotar.
    # Colunas úteis pelo índice para evitar erro de string com acento:
    col_mun_cod = df_se.columns[5] # Município (Código)
    col_mun_nome = df_se.columns[6] # Município
    col_secao = df_se.columns[10] # Classificação Nacional de Atividades Econômicas (CNAE 2.0)
    col_valor = df_se.columns[4] # Valor

    # Substituir valores faltantes por 0 e converter para numérico
    df_se[col_valor] = pd.to_numeric(df_se[col_valor].replace(["-", "...", "..", "X"], 0), errors="coerce").fillna(0)

    # Pivotar tabela para que cada seção seja uma coluna
    df_pivot = df_se.pivot_table(
        index=[col_mun_cod, col_mun_nome],
        columns=col_secao,
        values=col_valor,
        aggfunc="sum"
    ).reset_index()

    # Mapear as seções para os 4 grandes setores
    # A = Agropecuária
    # B, C, D, E, F = Indústria
    # O = Administração Pública
    # G, H, I, J, K, L, M, N, P, Q, R, S, T, U = Serviços
    
    colunas_secoes = [c for c in df_pivot.columns if c not in [col_mun_cod, col_mun_nome]]
    
    # Iniciar variáveis zeradas
    df_pivot["Emp_Agropecuaria"] = 0
    df_pivot["Emp_Industria"] = 0
    df_pivot["Emp_Servicos"] = 0
    df_pivot["Emp_Adm_Publica"] = 0

    for col in colunas_secoes:
        letra = col.split(" ")[0].strip()
        if letra == "A":
            df_pivot["Emp_Agropecuaria"] += df_pivot[col]
        elif letra in ["B", "C", "D", "E", "F"]:
            df_pivot["Emp_Industria"] += df_pivot[col]
        elif letra == "O":
            df_pivot["Emp_Adm_Publica"] += df_pivot[col]
        elif letra in ["G", "H", "I", "J", "K", "L", "M", "N", "P", "Q", "R", "S", "T", "U"]:
            df_pivot["Emp_Servicos"] += df_pivot[col]

    df_pivot = df_pivot.rename(columns={col_mun_cod: "CD_MUN", col_mun_nome: "NM_MUN"})
    df_pivot["CD_MUN"] = df_pivot["CD_MUN"].astype(str)
    
    return df_pivot[["CD_MUN", "NM_MUN", "Emp_Agropecuaria", "Emp_Industria", "Emp_Servicos", "Emp_Adm_Publica"]].copy()

def calcular_ql_empregos(df_emp):
    """Calcula o Quociente Locacional baseado nos empregos."""
    print("\n--- Calculando Quociente Locacional (Empregos) ---")
    
    if df_emp is None:
        return None
        
    setores = ["Emp_Agropecuaria", "Emp_Industria", "Emp_Servicos", "Emp_Adm_Publica"]
    df = df_emp.copy()
    
    df["Emp_Total"] = df[setores].sum(axis=1)
    
    totais_regiao = {s: df[s].sum() for s in setores}
    emp_total_regiao = df["Emp_Total"].sum()
    
    for setor in setores:
        part_mun = df[setor] / df["Emp_Total"]
        part_regiao = totais_regiao[setor] / emp_total_regiao
        df[f"QL_{setor}"] = (part_mun / part_regiao).replace([float("inf"), -float("inf")], 0).fillna(0).round(4)
        
    return df

def heatmap_ql_emprego(df_emp):
    """Gera heatmap do QL por setor focado em empregos."""
    print("\n--- Heatmap: QL Setorial (Empregos) ---")
    
    cols_ql = [c for c in df_emp.columns if c.startswith("QL_")]
    top = df_emp.nlargest(30, "Emp_Total").copy()
    
    top = top.set_index("NM_MUN")[cols_ql]
    top.columns = [c.replace("QL_Emp_", "").replace("_", " ") for c in top.columns]
    
    fig, ax = plt.subplots(figsize=(10, 12))
    sns.heatmap(top, ax=ax, cmap="RdYlGn", center=1, annot=True,
                fmt=".2f", linewidths=0.5, linecolor="#EEE",
                cbar_kws={"label": "Quociente Locacional (QL de Empregos)", "shrink": 0.8})
                
    ax.set_title("Quociente Locacional por Empregos — Top 30 Municípios\n"
                 "QL > 1 (verde) = especializado | QL < 1 (vermelho) = não especializado",
                 fontsize=12, fontweight="bold")
    ax.set_ylabel("")
    ax.tick_params(labelsize=8)
    
    plt.tight_layout()
    utils.salvar_mapa(fig, "heatmap_ql_empregos", "modulo4_1")

def mapa_especializacao_emprego(gdf_sudeste, df_emp):
    """Mapa de especialização baseado no QL de Empregos."""
    print("\n--- Mapa: Especialização por Empregos ---")
    
    setores = ["Emp_Agropecuaria", "Emp_Industria", "Emp_Servicos", "Emp_Adm_Publica"]
    df = df_emp.copy()
    
    # Evitar municípios sem emprego reportado
    df = df[df["Emp_Total"] > 0].copy()
    
    # Determinar o setor com o MAIOR QL no município
    cols_ql = [f"QL_{s}" for s in setores]
    df["Setor_Dominante"] = df[cols_ql].idxmax(axis=1)
    df["Setor_Dominante"] = df["Setor_Dominante"].map({
        "QL_Emp_Agropecuaria": "Agropecuária",
        "QL_Emp_Industria": "Indústria",
        "QL_Emp_Servicos": "Serviços",
        "QL_Emp_Adm_Publica": "Adm. Pública"
    })
    
    gdf = gdf_sudeste.merge(df[["CD_MUN", "Setor_Dominante"]], on="CD_MUN", how="left")
    fig, ax = utils.criar_figura_mapa(figsize=(15, 11))
    
    cores_setor = {
        "Agropecuária": "#4CAF50",
        "Indústria": "#FF5722",
        "Serviços": "#2196F3",
        "Adm. Pública": "#9C27B0"
    }
    
    for setor, cor in cores_setor.items():
        subset = gdf[gdf["Setor_Dominante"] == setor]
        if len(subset) > 0:
            subset.plot(ax=ax, color=cor, edgecolor="#CCC", linewidth=0.05, alpha=0.8)
            
    gdf_sudeste.dissolve(by="SIGLA_UF").boundary.plot(ax=ax, color="#333", linewidth=1.2)
    utils.adicionar_rotulos_uf(ax, gdf_sudeste)
    
    from matplotlib.patches import Patch
    legend_handles = [Patch(facecolor=c, label=s, edgecolor="#333") for s, c in cores_setor.items()]
    ax.legend(handles=legend_handles, title="Vocação por Emprego (Maior QL)",
              loc="lower left", fontsize=9, title_fontsize=10, frameon=True, shadow=True, framealpha=0.9)
              
    utils.formatar_eixos_mapa(ax, titulo="Especialização Municipal (Mão de Obra) — Maior QL de Empregos")
    utils.salvar_mapa(fig, "mapa_especializacao_empregos", "modulo4_1")

def executar_modulo4_1(gdf_sudeste=None):
    print("\n" + "=" * 60)
    print("MÓDULO 4.1 — QUOCIENTE LOCACIONAL POR EMPREGOS (CEMPRE)")
    print("=" * 60)
    
    os.makedirs(os.path.join(cfg.OUTPUT_DIR, "modulo4_1"), exist_ok=True)
    
    if gdf_sudeste is None:
        gdf_sudeste = utils.carregar_municipios_sudeste()
        gdf_sudeste["CD_MUN"] = gdf_sudeste["CD_MUN"].astype(str)
        
    df_emp = baixar_empregos_cempre()
    if df_emp is not None:
        df_emp = calcular_ql_empregos(df_emp)
        heatmap_ql_emprego(df_emp)
        mapa_especializacao_emprego(gdf_sudeste, df_emp)
        
    print("\n✓ Módulo 4.1 concluído! Mapas salvos em output/modulo4_1/")

if __name__ == "__main__":
    executar_modulo4_1()
