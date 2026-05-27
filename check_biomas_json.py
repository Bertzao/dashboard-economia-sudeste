import json
import os

path = r"d:\Projeto\data_export\biomas_se.json"
if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        features = data.get("features", [])
        print(f"Total features: {len(features)}")
        if features:
            print("Propriedades da primeira feature:", features[0].get("properties"))
            
        biomas = set()
        for feat in features:
            props = feat.get("properties", {})
            if "NM_BIOMA" in props:
                biomas.add(props["NM_BIOMA"])
        print("Biomas no JSON:", biomas)
else:
    print("biomas_se.json não existe!")
