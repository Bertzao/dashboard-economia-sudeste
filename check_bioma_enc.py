import geopandas as gpd
path = r"d:\Projeto\Uso da terra\lml_bioma_e250k_v20250911_A.shp"
gdf = gpd.read_file(path, encoding="utf-8")
print("utf-8:", gdf["NM_BIOMA"].unique())
gdf2 = gpd.read_file(path, encoding="latin1")
print("latin1:", gdf2["NM_BIOMA"].unique())
