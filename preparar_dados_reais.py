import pandas as pd
import numpy as np
import os
import glob
import unicodedata

def remove_accents(input_str):
    if not isinstance(input_str, str): return ""
    return ''.join(c for c in unicodedata.normalize('NFD', input_str)
                  if unicodedata.category(c) != 'Mn')

print("Iniciando o Pipeline de Preparação de Dados...")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data_export")
DIR_USO_TERRA = r"D:\Projeto\Uso da terra"
DIR_MEI = r"C:\Users\herbe\PycharmProjects\pythonProject2\MEI"

dim_mun = pd.read_csv(os.path.join(DATA_DIR, "dim_municipios.csv"), sep=";", dtype={"CD_MUN": str})

# ---------------------------------------------------------
# 1. VON THÜNEN - Culturas Agrícolas (tabela1612.xlsx)
# ---------------------------------------------------------
print("Processando PAM (Von Thünen)...")
try:
    df_pam = pd.read_excel(os.path.join(DIR_USO_TERRA, "tabela1612.xlsx"), skiprows=4)
    # A primeira coluna é o CD_MUN. Vamos renomeá-la.
    df_pam = df_pam.rename(columns={"Unnamed: 0": "CD_MUN"})
    df_pam = df_pam.dropna(subset=["CD_MUN"])
    df_pam["CD_MUN"] = df_pam["CD_MUN"].astype(str)
    
    # Filtro apenas pro Sudeste
    df_pam = df_pam[df_pam["CD_MUN"].isin(dim_mun["CD_MUN"])]
    
    # As colunas de culturas começam do índice 3 (Total) em diante. Vamos excluir o Total.
    colunas_culturas = [c for c in df_pam.columns[3:] if "Unnamed" not in c and c != "Total"]
    
    def get_top_crop(row):
        max_val = 0
        best_crop = "Pouca Expressão Agrícola"
        for c in colunas_culturas:
            val = row[c]
            if pd.notnull(val) and str(val).strip() != '-' and str(val).strip() != '...':
                try:
                    v = float(val)
                    if v > max_val:
                        max_val = v
                        best_crop = c
                except:
                    pass
        if max_val == 0:
            return "Pouca Expressão Agrícola"
        return best_crop

    df_pam["Cultura_Predominante"] = df_pam.apply(get_top_crop, axis=1)
    df_pam[["CD_MUN", "Cultura_Predominante"]].to_csv(os.path.join(DATA_DIR, "fato_culturas.csv"), index=False)
    print("-> fato_culturas.csv exportado com sucesso!")
except Exception as e:
    print(f"Erro ao processar PAM: {e}")

# ---------------------------------------------------------
# 2. CHRISTALLER - REGIC (Tabela_de_hierarquias.xlsx)
# ---------------------------------------------------------
print("Processando REGIC (Christaller)...")
try:
    df_regic = pd.read_excel(os.path.join(DIR_USO_TERRA, "Tabela_de_hierarquias.xlsx"))
    df_regic = df_regic.rename(columns={"COD_CIDADE": "CD_MUN"})
    df_regic["CD_MUN"] = df_regic["CD_MUN"].astype(str)
    
    # Mapeamento numérico da REGIC 2018 para texto (aproximado)
    # 1 a 3 = Metrópoles (1A, 1B, 1C)
    # 4 a 6 = Capitais Regionais (2A, 2B, 2C)
    # 7 a 8 = Centros Subregionais (3A, 3B)
    # 9 a 10 = Centros de Zona (4A, 4B)
    # 11 = Centro Local
    def map_hierarquia(cod):
        if pd.isnull(cod): return "Centro Local"
        cod = int(cod)
        if cod <= 3: return "Metrópole"
        if cod <= 6: return "Capital Regional"
        if cod <= 8: return "Centro Subregional"
        if cod <= 10: return "Centro de Zona"
        return "Centro Local"
        
    df_regic["Hierarquia_REGIC"] = df_regic[2018].apply(map_hierarquia)
    
    # Filter Sudeste
    df_regic = df_regic[df_regic["CD_MUN"].isin(dim_mun["CD_MUN"])]
    df_regic[["CD_MUN", "Hierarquia_REGIC"]].to_csv(os.path.join(DATA_DIR, "fato_regic.csv"), index=False)
    print("-> fato_regic.csv exportado com sucesso!")
except Exception as e:
    print(f"Erro ao processar REGIC: {e}")

# ---------------------------------------------------------
# 3. WEBER - Cadastro de Empresas CNAE (RFB)
# ---------------------------------------------------------
print("Processando CNAE (Weber)... Isso pode levar alguns minutos (10GB+ de arquivos)")

# 3.1 Construir de/para Município RFB (TOM) -> CD_MUN IBGE
try:
    df_rfb_mun = pd.read_csv(os.path.join(DIR_MEI, "F.K03200$Z.D60314.MUNICCSV"), sep=";", encoding="latin1", header=None, names=["TOM", "NM_MUN"])
    df_rfb_mun["TOM"] = df_rfb_mun["TOM"].astype(str).str.zfill(4)
    df_rfb_mun["NOME_NORM"] = df_rfb_mun["NM_MUN"].apply(lambda x: remove_accents(str(x).upper().strip()))
    
    dim_mun_norm = dim_mun.copy()
    dim_mun_norm["NOME_NORM"] = dim_mun_norm["NM_MUN"].apply(lambda x: remove_accents(str(x).upper().strip()))
    
    # Vamos criar um dicionário mapping {UF_TOM: CD_MUN} mas o arquivo de município da receita não tem UF.
    # O Join no loop terá que ser feito por TOM, depois olhamos pra UF.
except Exception as e:
    print(f"Erro ao carregar F.K03200$Z.D60314.MUNICCSV: {e}")

# Dicionário de Divisões Industriais (10 a 33 da CNAE 2.0)
cnae_ind = {
    '10': 'Alimentos', '11': 'Bebidas', '12': 'Fumo', '13': 'Têxtil', '14': 'Vestuário',
    '15': 'Couro e Calçados', '16': 'Madeira', '17': 'Papel e Celulose', '18': 'Impressão',
    '19': 'Coque e Derivados Petróleo', '20': 'Químicos', '21': 'Farmacêuticos',
    '22': 'Borracha e Plástico', '23': 'Minerais Não Metálicos', '24': 'Metalurgia',
    '25': 'Produtos de Metal', '26': 'Equipamentos de Informática', '27': 'Aparelhos Elétricos',
    '28': 'Máquinas e Equipamentos', '29': 'Veículos Automotores', '30': 'Outros Equipamentos de Transporte',
    '31': 'Móveis', '32': 'Produtos Diversos', '33': 'Manutenção'
}

estab_files = glob.glob(os.path.join(DIR_MEI, "*.ESTABELE"))
mun_cnae_counts = {}

col_indices = {
    "SIT_CADASTRAL": 5,
    "CNAE": 11,
    "UF": 19,
    "TOM": 20
}

try:
    for fpath in estab_files:
        print(f"Lendo chunk de: {os.path.basename(fpath)}")
        chunk_iter = pd.read_csv(fpath, sep=";", encoding="latin1", header=None, chunksize=500000, dtype=str)
        for chunk in chunk_iter:
            # Filtro Ativa (Sit_Cad == '02') e UF Sudeste
            c = chunk[(chunk[col_indices["SIT_CADASTRAL"]] == '02') & (chunk[col_indices["UF"]].isin(["SP", "MG", "RJ", "ES"]))]
            if len(c) == 0: continue
            
            c = c.dropna(subset=[col_indices["CNAE"], col_indices["TOM"]])
            c["DIVISAO"] = c[col_indices["CNAE"]].str[:2]
            
            # Filtrar apenas Indústria (10 a 33)
            c = c[c["DIVISAO"].isin(cnae_ind.keys())]
            
            # Contabilizar (TOM, UF, DIVISAO)
            grouped = c.groupby([col_indices["TOM"], col_indices["UF"], "DIVISAO"]).size().reset_index(name="COUNT")
            for _, row in grouped.iterrows():
                key = (str(row[col_indices["TOM"]]).zfill(4), str(row[col_indices["UF"]]))
                div = row["DIVISAO"]
                count = row["COUNT"]
                
                if key not in mun_cnae_counts:
                    mun_cnae_counts[key] = {}
                if div not in mun_cnae_counts[key]:
                    mun_cnae_counts[key][div] = 0
                mun_cnae_counts[key][div] += count

    print("Processamento finalizado. Consolidando resultados...")
    
    # Criar de/para de CD_MUN IBGE a partir da relação TOM+UF
    rfb_to_ibge = {}
    for _, row in df_rfb_mun.iterrows():
        matches = dim_mun_norm[dim_mun_norm["NOME_NORM"] == row["NOME_NORM"]]
        for _, m_row in matches.iterrows():
            # A chave é TOM + UF IBGE
            rfb_to_ibge[(row["TOM"], m_row["SIGLA_UF"])] = m_row["CD_MUN"]

    # Extrair CNAE Dominante
    resultados = []
    for (tom, uf), cnaes in mun_cnae_counts.items():
        cd_mun = rfb_to_ibge.get((tom, uf))
        if cd_mun:
            best_div = max(cnaes, key=cnaes.get)
            resultados.append({
                "CD_MUN": cd_mun,
                "CNAE_Predominante": cnae_ind[best_div]
            })
            
    df_cnae = pd.DataFrame(resultados)
    df_cnae.to_csv(os.path.join(DATA_DIR, "fato_cnae.csv"), index=False)
    print("-> fato_cnae.csv exportado com sucesso!")
except Exception as e:
    print(f"Erro ao processar CNAE: {e}")

print("Pipeline Concluído!")
