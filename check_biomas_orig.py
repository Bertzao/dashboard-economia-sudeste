import geopandas as gpd
path = r"d:\Projeto\Uso da terra\lml_bioma_e250k_v20250911_A.shp"
print("Lendo Biomas...")
gdf = gpd.read_file(path, rows=5)
print("Colunas:", gdf.columns)
print("Valores:\n", gdf.head())
