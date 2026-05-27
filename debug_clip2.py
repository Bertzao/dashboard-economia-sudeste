import geopandas as gpd
import os

PROJETO_DIR = r"d:\Projeto"
SHP_MUNICIPIOS = os.path.join(PROJETO_DIR, "municipios e UF + população", "BR_Municipios_2025.shp")
SHP_BIOMAS = os.path.join(PROJETO_DIR, "Uso da terra", "lml_bioma_e250k_v20250911_A.shp")

# 1. Load mask
print("Lendo mask")
gdf_mun = gpd.read_file(SHP_MUNICIPIOS)
gdf_se = gdf_mun[gdf_mun["CD_REGIAO"] == "3"].copy()
if gdf_se.crs is None or gdf_se.crs.to_string() != "EPSG:4326":
    gdf_se = gdf_se.to_crs(epsg=4326)
mask_poly = gdf_se.unary_union
print("Mask bbox:", mask_poly.bounds)

# 2. Load Biomas
print("Lendo biomas")
bbox = tuple(gdf_se.total_bounds)
gdf_bioma = gpd.read_file(SHP_BIOMAS, bbox=bbox)
print("Biomas original bbox:", gdf_bioma.total_bounds)

if gdf_bioma.crs is None or gdf_bioma.crs != gdf_se.crs:
    gdf_bioma = gdf_bioma.to_crs(gdf_se.crs)

# 3. Clip
print("Clipping")
gdf_bioma_clipped = gpd.clip(gdf_bioma, mask_poly)
print("Biomas clipped bbox:", gdf_bioma_clipped.total_bounds)

