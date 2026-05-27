import geopandas as gpd
path = r"d:\Projeto\Uso da terra\Potencialidade_agricola.shp"
print("Lendo 5 linhas...")
gdf = gpd.read_file(path, rows=5)
print("Colunas:", gdf.columns)
print("Valores:\n", gdf.head())
