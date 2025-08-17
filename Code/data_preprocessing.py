import pandas as pd

df_building_original = pd.read_csv("../Data/건축물대장_통합.csv")

# 위경도 결측치
(df_building_original["위도"].isna() & df_building_original["경도"].isna()).sum()

# 결측치만 정제
df_building_filter = df_building_original.loc[df_building_original["위도"].isna() & df_building_original["경도"].isna(), :]

# 구조코드명별 퍼센트
total = len(df_building_filter)
summary = (df_building_filter['구조코드명']
           .value_counts(dropna=False)
           .rename_axis('구조코드명')
           .reset_index(name='수')
           .assign(퍼센트=lambda d: (d['수'] / total * 100).round(2))
           .sort_values(['수','구조코드명'], ascending=[False, True], ignore_index=True))
summary