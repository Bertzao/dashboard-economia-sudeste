import geopandas as gpd
path = r"d:\Projeto\Uso da terra\Potencialidade_agricola.shp"
gdf = gpd.read_file(path, rows=50000) # Read a chunk to find unique values
print("Valores unicos de potenc_f:", gdf["potenc_f"].unique())
