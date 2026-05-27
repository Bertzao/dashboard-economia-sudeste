import os
import sys
import pandas as pd
import geopandas as gpd
import warnings

warnings.filterwarnings("ignore")

PROJETO_DIR = r"d:\Projeto"
EXPORT_DIR = os.path.join(PROJETO_DIR, "data_export")
os.makedirs(EXPORT_DIR, exist_ok=True)

# Bases Principais
SHP_MUNICIPIOS = os.path.join(PROJETO_DIR, "municipios e UF + população", "BR_Municipios_2025.shp")
CSV_PIB = os.path.join(PROJETO_DIR, "Atividade Econômica", "PIB dos Municípios - base de dados 2010-2023.xlsx")

# Bases Auxiliares (Uso do Solo e Infraestrutura)
SHP_BIOMAS = os.path.join(PROJETO_DIR, "Uso da terra", "lml_bioma_e250k_v20250911_A.shp")
SHP_UCS = os.path.join(PROJETO_DIR, "Uso da terra", "BR_UC_UF_Publicacao_CD2022", "BR_UC_UF_Publicacao_CD2022.shp")
SHP_POTENCIAL = os.path.join(PROJETO_DIR, "Uso da terra", "Potencialidade_agricola.shp")
SHP_RODOVIAS = os.path.join(PROJETO_DIR, "Infra", "2014 rodoviario", "eixo_rodoviario_estruturante_2014.shp")
SHP_FERROVIAS = os.path.join(PROJETO_DIR, "Infra", "BaseFerro", "BaseFerro.shp")

def processar_camada(path, mask_gdf, nome_saida, simplify_tol=0.01, colunas_manter=None, encoding="utf-8"):
    try:
        print(f"Processando {nome_saida} (recorte exato e simplificação)...")
        if not os.path.exists(path):
            print(f"Arquivo {path} não encontrado.")
            return
        
        # Leitura com máscara cuida automaticamente de bounding boxes e CRS!
        print(f"  Lendo e filtrando {nome_saida} do disco...")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            gdf = gpd.read_file(path, mask=mask_gdf, encoding=encoding)
        
        if gdf.empty:
            print(f"{nome_saida} não contém dados na área do Sudeste.")
            return
            
        # Converter para o mesmo CRS da máscara (EPSG:4326) para o Plotly
        if gdf.crs is None or gdf.crs != mask_gdf.crs:
            gdf = gdf.to_crs(mask_gdf.crs)
            
        # CLIP REAL: Aparar as arestas que a leitura mask possa ter deixado
        print(f"  Aparando arestas de {nome_saida}...")
        mask_poly = mask_gdf.unary_union
        gdf = gpd.clip(gdf, mask_poly)
        
        # Simplificar
        gdf["geometry"] = gdf["geometry"].simplify(tolerance=simplify_tol, preserve_topology=True)
        
        if colunas_manter:
            cols = [c for c in colunas_manter if c in gdf.columns] + ["geometry"]
            gdf = gdf[cols]
            
        saida = os.path.join(EXPORT_DIR, f"{nome_saida}.json")
        gdf.to_file(saida, driver="GeoJSON")
        print(f"Sucesso: {nome_saida} salvo!")
    except Exception as e:
        print(f"Erro ao processar {nome_saida}: {e}")

def preparar_dados():
    print("1. Lendo Shapefile...")
    gdf = gpd.read_file(SHP_MUNICIPIOS)
    if gdf.crs is None or gdf.crs.to_string() != "EPSG:4326":
        gdf = gdf.to_crs(epsg=4326)
        
    gdf_se = gdf[gdf["CD_REGIAO"] == "3"].copy()
    bbox_se = tuple(gdf_se.total_bounds) # (minx, miny, maxx, maxy)
    
    print("2. Processando camadas auxiliares com Máscara do Sudeste (Recorte Exato)...")
    # Usa a máscara (gdf_se) inteira para cortar a tesoura
    processar_camada(SHP_BIOMAS, gdf_se, "biomas_se", 0.02, ["NM_BIOMA"], encoding="latin1")
    processar_camada(SHP_UCS, gdf_se, "ucs_se", 0.01, ["NOME_UC1", "CATEGORI3"], encoding="latin1")
    processar_camada(SHP_RODOVIAS, gdf_se, "rodovias_se", 0.01, ["BR", "NM_TIPO_TR"], encoding="latin1")
    processar_camada(SHP_FERROVIAS, gdf_se, "ferrovias_se", 0.01, ["NOME"], encoding="latin1")
    
    # Potencial Agrícola é pesado.
    processar_camada(SHP_POTENCIAL, gdf_se, "potencial_agricola_se", 0.05, ["potenc_f"], encoding="latin1")
    
    print("3. Lendo Dados de PIB...")
    cols = [
        "Ano", "Código do Município", "Nome do Município", "Sigla da Unidade da Federação",
        "Valor adicionado bruto da Agropecuária, \na preços correntes\n(R$ 1.000)",
        "Valor adicionado bruto da Indústria,\na preços correntes\n(R$ 1.000)",
        "Valor adicionado bruto dos Serviços,\na preços correntes \n- exceto Administração, defesa, educação e saúde públicas e seguridade social\n(R$ 1.000)",
        "Valor adicionado bruto da Administração, defesa, educação e saúde públicas e seguridade social, \na preços correntes\n(R$ 1.000)",
        "Produto Interno Bruto, \na preços correntes\n(R$ 1.000)"
    ]
    df_pib = pd.read_excel(CSV_PIB, usecols=cols)
    
    rename_dict = {
        "Código do Município": "CD_MUN",
        "Nome do Município": "NM_MUN",
        "Sigla da Unidade da Federação": "SIGLA_UF",
        cols[4]: "VAB_Agropecuaria",
        cols[5]: "VAB_Industria",
        cols[6]: "VAB_Servicos",
        cols[7]: "VAB_Adm_Publica",
        cols[8]: "PIB"
    }
    df_pib = df_pib.rename(columns=rename_dict)
    
    df_pib_se = df_pib[df_pib["SIGLA_UF"].isin(["SP", "MG", "RJ", "ES"])].copy()
    df_pib_se["CD_MUN"] = df_pib_se["CD_MUN"].astype(str)
    
    print("4. Preparando Dimensão e Fatos...")
    dim = gdf_se[["CD_MUN", "NM_MUN", "SIGLA_UF", "CD_RGI", "NM_RGI", "CD_RGINT", "NM_RGINT", "CD_CONCURB", "NM_CONCURB", "AREA_KM2"]].copy()
    dim["Flag_Conurbacao"] = dim["CD_CONCURB"].apply(lambda x: "Conurbação" if pd.notna(x) else "Sem conurbação")
    dim.to_csv(os.path.join(EXPORT_DIR, "dim_municipios.csv"), sep=";", index=False, encoding="utf-8-sig")
    
    df_2021 = df_pib_se[df_pib_se["Ano"] == 2021].copy()
    vab_cols = ["VAB_Agropecuaria", "VAB_Industria", "VAB_Servicos", "VAB_Adm_Publica"]
    setor_labels = ["Agropecuária", "Indústria", "Serviços", "Adm. Pública"]
    
    for col in vab_cols:
        df_2021[col] = pd.to_numeric(df_2021[col], errors="coerce").fillna(0)
        
    vab_matrix = df_2021[vab_cols].values
    idx_max = vab_matrix.argmax(axis=1)
    df_2021["Setor_Dominante"] = [setor_labels[i] for i in idx_max]
    
    df_2021.to_csv(os.path.join(EXPORT_DIR, "fato_pib.csv"), sep=";", index=False, encoding="utf-8-sig")
    
    print("5. Gerando GeoJSON Base Municipal...")
    gdf_se["geometry"] = gdf_se["geometry"].simplify(tolerance=0.01, preserve_topology=True)
    gdf_json = gdf_se[["CD_MUN", "NM_MUN", "geometry"]].copy()
    gdf_json.to_file(os.path.join(EXPORT_DIR, "mapa_sudeste.json"), driver="GeoJSON")
    
    print("ETL Concluído!")

if __name__ == "__main__":
    preparar_dados()
