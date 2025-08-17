import pandas as pd

df_building_original = pd.read_csv("../Data/건축물대장_통합.csv")

# 위경도 결측치
(df_building_original["위도"].isna() & df_building_original["경도"].isna()).sum()

# 결측치만 정제
df_building_filter = df_building_original.loc[df_building_original["위도"].isna() & df_building_original["경도"].isna(), :]

# 구조코드명별 퍼센트
df_building_grouped = (df_building_filter
                       .groupby('구조코드명', dropna=False)
                       .size()
                       .rename('수')
                       .reset_index())

df_building_grouped['퍼센트'] = (df_building_grouped['수'] / len(df_building_filter) * 100).round(2)
df_building_grouped = df_building_grouped.sort_values(['수','구조코드명'], ascending=[False, True], ignore_index=True)

df_building_grouped

