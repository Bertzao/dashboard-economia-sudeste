import pandas as pd
import os

dir_uso_terra = r"D:\Projeto\Uso da terra"

def inspect_excel(path, rows=5):
    try:
        df = pd.read_excel(path, nrows=rows)
        print(f"\n--- {os.path.basename(path)} ---")
        print("Columns:", list(df.columns))
        print("First row:", df.iloc[0].to_dict() if len(df) > 0 else "Empty")
    except Exception as e:
        print(f"Error reading {path}: {e}")

inspect_excel(os.path.join(dir_uso_terra, "tabela1612.xlsx"))
inspect_excel(os.path.join(dir_uso_terra, "Tabela_de_hierarquias.xlsx"))
inspect_excel(os.path.join(dir_uso_terra, "REGIC2018_Matriz_de_Ligacoes.xlsx"))
