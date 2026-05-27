import json
path = r"d:\Projeto\data_export\potencial_agricola_se.json"
with open(path, "r", encoding="utf-8") as f:
    gj = json.load(f)
    
vals = set()
for feat in gj.get("features", []):
    prop = feat.get("properties", {})
    if "SIGLA_CL_1" in prop:
        vals.add(prop["SIGLA_CL_1"])
print("Valores de SIGLA_CL_1:", vals)
