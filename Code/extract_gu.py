import pandas as pd


df = pd.read_csv("../Data/건축물대장_v0.5.csv", encoding="utf-8-sig")

df["구군"] = df["대지위치"].str.extract(r"(달서구|달성군|동구|북구|서구|수성구|중구|남구|군위군)")

df.to_csv("../Data/건축물대장_v0.6.csv", index=False, encoding="utf-8-sig")