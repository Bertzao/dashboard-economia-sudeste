import geopandas as gpd
import os

EXPORT_DIR = r"d:\Projeto\data_export"
for f in ["biomas_se.json", "ucs_se.json", "rodovias_se.json", "ferrovias_se.json", "mapa_sudeste.json"]:
    path = os.path.join(EXPORT_DIR, f)
    if os.path.exists(path):
        gdf = gpd.read_file(path)
        print(f"{f} bbox: {gdf.total_bounds}")
