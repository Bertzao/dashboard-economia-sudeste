import geopandas as gpd
import os

PROJETO_DIR = r"d:\Projeto"
SHP_MUNICIPIOS = os.path.join(PROJETO_DIR, "municipios e UF + população", "BR_Municipios_2025.shp")

gdf = gpd.read_file(SHP_MUNICIPIOS)
print("Colunas disponíveis:", gdf.columns)
print("Valores em CD_REGIAO:", gdf["CD_REGIAO"].unique() if "CD_REGIAO" in gdf.columns else "Coluna Ausente")
if "CD_REGIAO" in gdf.columns:
    print("Municipios na regiao 3:", len(gdf[gdf["CD_REGIAO"] == "3"]))
    print("Municipios na regiao 'Sudeste':", len(gdf[gdf["CD_REGIAO"] == "Sudeste"]))
else:
    print("Verificando SIGLA_UF:", gdf["SIGLA_UF"].unique() if "SIGLA_UF" in gdf.columns else "Coluna Ausente")

