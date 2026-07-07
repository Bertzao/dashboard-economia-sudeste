import pandas as pd
import os

dir_uso_terra = r"D:\Projeto\Uso da terra"

try:
    df = pd.read_excel(os.path.join(dir_uso_terra, "tabela1612.xlsx"), skiprows=4, nrows=5)
    print("tabela1612 columns:", list(df.columns))
    print(df.head())
except Exception as e:
    print(e)
