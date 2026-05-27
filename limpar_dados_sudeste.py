# -*- coding: utf-8 -*-
"""
============================================================================
SCRIPT ETL: LIMPEZA E PRÉ-PROCESSAMENTO DE DADOS DO SUDESTE
============================================================================
Este script realiza a carga síncrona dos arquivos originais do projeto
(Excel e Shapefiles nacionais), filtra os dados para a região Sudeste,
realiza os recortes espaciais (clip) e salva os arquivos limpos e compactados
nos formatos PARQUET (dados tabulares) e GEOPACKAGE (dados geográficos) 
dentro da pasta 'data_clean/'.

Objetivo: Garantir que o Dashboard carregue instantaneamente.
"""

import os
import time
import pandas as pd
import geopandas as gpd
import numpy as np

import config as cfg
import utils

CLEAN_DIR = os.path.join(cfg.BASE_DIR, "data_clean")
os.makedirs(CLEAN_DIR, exist_ok=True)
FORCE_REBUILD = True

def pre_processar_limites_e_municipios():
    """Carrega a malha municipal do Brasil, filtra o Sudeste e salva."""
    t0 = time.time()
    print("\n[ETL 1/5] Processando malha municipal do Sudeste...")
    caminho_out = os.path.join(CLEAN_DIR, "municipios_sudeste.gpkg")
    if not FORCE_REBUILD and os.path.exists(caminho_out) and os.path.getsize(caminho_out) > 0:
        print(f"  ✓ Malha municipal já existe: {caminho_out} (pulando).")
        return gpd.read_file(caminho_out)
        
    # Carregar municípios do Sudeste (já filtrados via utils)
    gdf_sudeste = utils.carregar_municipios_sudeste()
    
    # Garantir tipos e preencher vazios
    gdf_sudeste["CD_MUN"] = gdf_sudeste["CD_MUN"].astype(str)
    gdf_sudeste["CD_UF"] = gdf_sudeste["CD_UF"].astype(str)
    gdf_sudeste["AREA_KM2"] = pd.to_numeric(gdf_sudeste["AREA_KM2"], errors="coerce")
    
    # Reprojetar para EPSG:4326 (WGS 84) - ideal para Folium/Pydeck interativos
    gdf_sudeste = gdf_sudeste.to_crs("EPSG:4326")
    
    # Simplificar geometrias para carregamento web instantâneo
    print("  Simplificando geometrias dos municípios (redução de tamanho)...")
    gdf_sudeste["geometry"] = gdf_sudeste["geometry"].simplify(tolerance=0.003, preserve_topology=True)
    
    # Salvar em GeoPackage (rápido e robusto)
    gdf_sudeste.to_file(caminho_out, driver="GPKG")
    
    print(f"  ✓ Salvo: {caminho_out} ({len(gdf_sudeste)} municípios) | Tempo: {time.time() - t0:.1f}s")
    return gdf_sudeste

def pre_processar_demografia():
    """Processa dados de população por idade, raça e povos tradicionais e salva em Parquet."""
    t0 = time.time()
    print("\n[ETL 2/5] Processando dados demográficos (Censo 2022)...")
    
    # Definir nomes_sudeste no topo da função para evitar erros de escopo
    nomes_sudeste = list(cfg.NOMES_UF.values())
    
    # 1. População por Idade
    print("  Processando População por Grupo de Idade (Tabela 1209)...")
    try:
        df_raw = pd.read_excel(cfg.XLS_POP_IDADE, header=None)
        linha_anos = df_raw.iloc[3, :]
        
        # Identificar as colunas do Censo 2022 tratando floats (ex: 2022.0)
        cols_2022 = []
        for i, v in enumerate(linha_anos):
            if pd.notna(v):
                try:
                    ano_str = str(v).split('.')[0].strip()
                    if ano_str == "2022":
                        cols_2022.append(i)
                except Exception:
                    pass
                    
        if not cols_2022:
            raise ValueError("Ano 2022 não encontrado na Tabela 1209")
            
        inicio_2022 = cols_2022[0]
        
        # Mapeamento manual das 15 categorias oficiais da Tabela 1209 (Censo 2022)
        colunas_idade = [
            "Total", "0_a_4", "5_a_9", "10_a_14", "15_a_19", 
            "15_a_17", "18_e_19", "20_a_24", "25_a_29", "30_a_39", 
            "40_a_49", "50_a_59", "60_a_69", "70_anos_ou_mais", "Idade_ignorada"
        ]
        
        dados = []
        for idx in range(4, len(df_raw)):
            uf = df_raw.iloc[idx, 0]
            if pd.isna(uf) or "Fonte:" in str(uf):
                continue
            row = {"UF": str(uf).strip()}
            for offset, nome_col in enumerate(colunas_idade):
                col_idx = inicio_2022 + offset
                val = df_raw.iloc[idx, col_idx]
                
                # Tratar valores '...' como NaN/0
                if str(val).strip() == '...':
                    val = 0
                row[nome_col] = pd.to_numeric(val, errors="coerce")
            dados.append(row)
            
        df_idade = pd.DataFrame(dados)
        
        # Filtro Sudeste
        df_idade_se = df_idade[df_idade["UF"].isin(nomes_sudeste)].copy()
        
        caminho_idade = os.path.join(CLEAN_DIR, "pop_idade_sudeste.parquet")
        df_idade_se.to_parquet(caminho_idade, index=False)
        print(f"    ✓ Salvo: {caminho_idade}")
    except Exception as e:
        print(f"    ✗ Erro ao processar tabela 1209: {e}")
        
    # 2. População por Raça
    print("  Processando População por Cor/Raça (Tabela 9606)...")
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
                uf_atual = None
        df_raca = pd.DataFrame(dados)
        df_raca_se = df_raca[df_raca["UF"].isin(nomes_sudeste)].copy()
        
        caminho_raca = os.path.join(CLEAN_DIR, "pop_raca_sudeste.parquet")
        df_raca_se.to_parquet(caminho_raca, index=False)
        print(f"    ✓ Salvo: {caminho_raca}")
    except Exception as e:
        print(f"    ✗ Erro ao processar tabela 9606: {e}")
        
    # 3. Populações Tradicionais (Indígena e Quilombola)
    print("  Processando Populações Tradicionais...")
    try:
        resultados = []
        # Indigena (Tabela 8175)
        df_ind = pd.read_excel(cfg.XLS_POP_INDIGENA, header=None)
        for idx in range(6, len(df_ind)):
            uf = str(df_ind.iloc[idx, 0]).strip()
            if pd.notna(df_ind.iloc[idx, 0]) and "Fonte" not in uf:
                if uf in nomes_sudeste:
                    val = pd.to_numeric(df_ind.iloc[idx, 404], errors="coerce")
                    resultados.append({"UF": uf, "Pop_Indigena": val})
        df_trad = pd.DataFrame(resultados)
        
        # Quilombola (Tabela 8176)
        df_qui = pd.read_excel(cfg.XLS_POP_QUILOMB, header=None)
        qui_dict = {}
        for idx in range(6, len(df_qui)):
            uf = str(df_qui.iloc[idx, 0]).strip()
            if pd.notna(df_qui.iloc[idx, 0]) and "Fonte" not in uf:
                if uf in nomes_sudeste:
                    val = pd.to_numeric(df_qui.iloc[idx, 2], errors="coerce")
                    qui_dict[uf] = val
                    
        if not df_trad.empty:
            df_trad["Pop_Quilombola"] = df_trad["UF"].map(qui_dict)
        else:
            df_trad = pd.DataFrame([{"UF": k, "Pop_Quilombola": v} for k, v in qui_dict.items()])
            
        caminho_trad = os.path.join(CLEAN_DIR, "pop_tradicional_sudeste.parquet")
        df_trad.to_parquet(caminho_trad, index=False)
        print(f"    ✓ Salvo: {caminho_trad}")
    except Exception as e:
        print(f"    ✗ Erro ao processar populações tradicionais: {e}")
        
    print(f"  Tempo decorrido: {time.time() - t0:.1f}s")

def pre_processar_infraestrutura_e_ambiente(gdf_sudeste):
    """Carrega shapefiles nacionais de infra e biomas, recorta para o Sudeste e salva."""
    t0 = time.time()
    print("\n[ETL 3/5] Processando camadas de infraestrutura e meio ambiente (Clips)...")
    
    # Dissolver municípios do Sudeste para obter máscara de recorte
    mascara = gdf_sudeste.dissolve().to_crs("EPSG:4674") # CRS original das camadas
    
    infra_camadas = {
        "rodovias": (cfg.SHP_RODOVIAS, "Rodovias Estruturantes"),
        "ferrovias": (cfg.SHP_FERROVIAS, "Ferrovias"),
        "aeroportos": (cfg.SHP_AEROPORTOS, "Aeroportos"),
        "portos": (cfg.SHP_PORTOS, "Portos"),
        "hidrovias": (cfg.SHP_HIDROVIAS, "Hidrovias"),
    }
    
    for nome, (path, desc) in infra_camadas.items():
        caminho_out = os.path.join(CLEAN_DIR, f"{nome}_sudeste.gpkg")
        if not FORCE_REBUILD and os.path.exists(caminho_out) and os.path.getsize(caminho_out) > 0:
            print(f"  ✓ {desc}: já existe (pulando clip).")
            continue
            
        print(f"  Processando {desc}...")
        gdf = utils.carregar_shapefile_generico(path, desc)
        if gdf is not None:
            # Recortar
            recortado = gpd.clip(gdf, mascara)
            # Reprojetar para EPSG:4326 para mapas interativos
            recortado = recortado.to_crs("EPSG:4326")
            
            # Simplificar geometrias para carregamento web instantâneo
            print(f"    Simplificando geometria de {desc} (redução de tamanho)...")
            recortado["geometry"] = recortado["geometry"].simplify(tolerance=0.002, preserve_topology=True)
            
            recortado.to_file(caminho_out, driver="GPKG")
            print(f"    ✓ Salvo: {caminho_out} ({len(recortado)} feições)")
            
    amb_camadas = {
        "biomas": (cfg.SHP_BIOMAS, "Biomas"),
        "ucs": (cfg.SHP_UCS, "Unidades de Conservação"),
        "potencial_agri": (cfg.SHP_POTENCIALIDADE_AGRICOLA, "Potencialidade Agrícola"),
    }
    
    for nome, (path, desc) in amb_camadas.items():
        caminho_out = os.path.join(CLEAN_DIR, f"{nome}_sudeste.gpkg")
        if not FORCE_REBUILD and os.path.exists(caminho_out) and os.path.getsize(caminho_out) > 0:
            print(f"  ✓ {desc}: já existe (pulando clip).")
            continue
            
        print(f"  Processando {desc}...")
        gdf = utils.carregar_shapefile_generico(path, desc)
        if gdf is not None:
            recortado = gpd.clip(gdf, mascara)
            recortado = recortado.to_crs("EPSG:4326")
            
            # Simplificar geometrias para carregamento web instantâneo
            print(f"    Simplificando geometria de {desc} (redução de tamanho)...")
            recortado["geometry"] = recortado["geometry"].simplify(tolerance=0.003, preserve_topology=True)
            
            recortado.to_file(caminho_out, driver="GPKG")
            print(f"    ✓ Salvo: {caminho_out} ({len(recortado)} feições)")
            
    print(f"  Tempo decorrido: {time.time() - t0:.1f}s")

def pre_processar_economia():
    """Filtra a planilha do PIB municipal (2010-2023) para o Sudeste e salva em Parquet."""
    t0 = time.time()
    print("\n[ETL 4/5] Processando PIB e VAB Municipal (IBGE)...")
    
    caminho = cfg.XLS_PIB_MUNICIPIOS
    if not os.path.exists(caminho):
        print(f"  ✗ Planilha de PIB não encontrada em: {caminho}")
        return
        
    print("  Lendo planilha Excel... (isso pode demorar de 10s a 30s)")
    df_pib = pd.read_excel(caminho, sheet_name=0)
    
    COL_ANO      = df_pib.columns[0]   # Ano
    COL_SIGLA_UF = df_pib.columns[4]   # Sigla UF
    COL_CD_MUN   = df_pib.columns[6]   # CD_MUN
    COL_NM_MUN   = df_pib.columns[7]   # NM_MUN
    COL_VAB_AGRO = df_pib.columns[32]  # VAB Agropecuária
    COL_VAB_IND  = df_pib.columns[33]  # VAB Indústria
    COL_VAB_SERV = df_pib.columns[34]  # VAB Serviços
    COL_VAB_ADM  = df_pib.columns[35]  # VAB Adm Pública
    COL_PIB      = df_pib.columns[38]  # PIB
    
    # Filtrar apenas Sudeste (SP, MG, RJ, ES) - todos os anos de 2010 a 2023
    print("  Filtrando estados do Sudeste...")
    mask = df_pib[COL_SIGLA_UF].isin(["SP", "MG", "RJ", "ES"])
    df_se = df_pib[mask].copy()
    
    # Renomear para o padrão
    df_se = df_se.rename(columns={
        COL_CD_MUN: "CD_MUN",
        COL_NM_MUN: "NM_MUN",
        COL_ANO: "Ano",
        COL_SIGLA_UF: "SIGLA_UF",
        COL_VAB_AGRO: "VAB_Agropecuaria",
        COL_VAB_IND:  "VAB_Industria",
        COL_VAB_SERV: "VAB_Servicos",
        COL_VAB_ADM:  "VAB_Adm_Publica",
        COL_PIB:      "PIB"
    })
    
    df_se["CD_MUN"] = df_se["CD_MUN"].astype(str)
    
    # Converter colunas numéricas
    cols_numericas = ["VAB_Agropecuaria", "VAB_Industria", "VAB_Servicos", "VAB_Adm_Publica", "PIB"]
    for c in cols_numericas:
        df_se[c] = pd.to_numeric(df_se[c], errors="coerce").fillna(0)
        
    # Salvar em Parquet
    caminho_out = os.path.join(CLEAN_DIR, "pib_vab_sudeste.parquet")
    df_se[["CD_MUN", "NM_MUN", "Ano", "SIGLA_UF", "VAB_Agropecuaria", "VAB_Industria", "VAB_Servicos", "VAB_Adm_Publica", "PIB"]].to_parquet(caminho_out, index=False)
    
    print(f"  ✓ Salvo: {caminho_out} ({len(df_se)} linhas) | Tempo: {time.time() - t0:.1f}s")

def pre_processar_empregos_e_historico():
    """Pré-calcula os empregos do CEMPRE (cache local) e cria a tabela colonial."""
    t0 = time.time()
    print("\n[ETL 5/5] Processando empregos (CEMPRE) e histórico colonial...")
    
    # 1. Empregos do CEMPRE
    cache_path = os.path.join(cfg.OUTPUT_DIR, "cempre_empregos_secao.csv")
    if os.path.exists(cache_path):
        print("  Carregando empregos do cache local...")
        df_se = pd.read_csv(cache_path, dtype={"Município (Código)": str})
        
        col_mun_cod = df_se.columns[5] # CD
        col_mun_nome = df_se.columns[6] # Nome
        col_secao = df_se.columns[10] # Seção CNAE
        col_valor = df_se.columns[4] # Valor ocupados
        
        df_se[col_valor] = pd.to_numeric(df_se[col_valor].replace(["-", "...", "..", "X"], 0), errors="coerce").fillna(0)
        
        df_pivot = df_se.pivot_table(
            index=[col_mun_cod, col_mun_nome],
            columns=col_secao,
            values=col_valor,
            aggfunc="sum"
        ).reset_index()
        
        df_pivot["Emp_Agropecuaria"] = 0
        df_pivot["Emp_Industria"] = 0
        df_pivot["Emp_Servicos"] = 0
        df_pivot["Emp_Adm_Publica"] = 0
        
        for col in df_pivot.columns:
            if col in [col_mun_cod, col_mun_nome]:
                continue
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
        
        df_emp = df_pivot[["CD_MUN", "NM_MUN", "Emp_Agropecuaria", "Emp_Industria", "Emp_Servicos", "Emp_Adm_Publica"]].copy()
        
        # Salvar em Parquet
        caminho_emp = os.path.join(CLEAN_DIR, "cempre_empregos_sudeste.parquet")
        df_emp.to_parquet(caminho_emp, index=False)
        print(f"    ✓ Salvo: {caminho_emp}")
    else:
        print("  ⚠ Cache do CEMPRE não encontrado em output/. Execute modulo4_1_emprego.py uma vez primeiro.")
        
    # 2. Histórico Colonial
    print("  Gerando dados coloniais históricos...")
    dados_coloniais = [
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
    df_hist = pd.DataFrame(dados_coloniais)
    caminho_hist = os.path.join(CLEAN_DIR, "historico_colonial_sudeste.parquet")
    df_hist.to_parquet(caminho_hist, index=False)
    print(f"    ✓ Salvo: {caminho_hist}")
    
    print(f"  Tempo decorrido: {time.time() - t0:.1f}s")

if __name__ == "__main__":
    t_start = time.time()
    print("=" * 60)
    print("INICIANDO PIPELINE ETL DE OTIMIZAÇÃO DOS DADOS")
    print("=" * 60)
    
    gdf_se = pre_processar_limites_e_municipios()
    pre_processar_demografia()
    pre_processar_infraestrutura_e_ambiente(gdf_se)
    pre_processar_economia()
    pre_processar_empregos_e_historico()
    
    print("=" * 60)
    print(f"PIPELINE ETL CONCLUÍDO COM SUCESSO EM {time.time() - t_start:.1f} SEGUNDOS!")
    print("=" * 60)
