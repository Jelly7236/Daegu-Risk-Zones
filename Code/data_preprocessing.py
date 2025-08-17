import pandas as pd
import numpy as np

df_building_original = pd.read_csv("../Data/건축물대장_통합.csv")

# 결측치 확인
df_building_original["대지위치"].isna().sum()
df_building_original["지상층수"].isna().sum()
df_building_original["높이(m)"].isna().sum()
df_building_original["구조코드명"].isna().sum()
df_building_original["기타구조"].isna().sum()
df_building_original["사용승인년도"].isna().sum()
df_building_original["위도"].isna().sum()
df_building_original["경도"].isna().sum()
(df_building_original["위도"].isna() & df_building_original["경도"].isna()).sum()


# 위경도 결측치 중 구조코드명별 퍼센트
df_building_filter = df_building_original.loc[df_building_original["위도"].isna() & df_building_original["경도"].isna(), :]

df_building_grouped = (df_building_filter
                       .groupby('구조코드명', dropna=False)
                       .size()
                       .rename('수')
                       .reset_index())

df_building_grouped['퍼센트'] = (df_building_grouped['수'] / len(df_building_filter) * 100).round(2)
df_building_grouped = df_building_grouped.sort_values(['수','구조코드명'], ascending=[False, True], ignore_index=True)

df_building_grouped

# 위경도 결측치 중 일반목구조가 전체 일반목구조에 어느정도 해당하는지
original_wooden_structure = ((df_building_original["구조코드명"] == "일반목구조") & (df_building_original["위도"] != np.nan)).sum()
filter_wooden_structure = df_building_grouped.loc[df_building_grouped["구조코드명"] == "일반목구조", "수"][0]
(filter_wooden_structure / original_wooden_structure * 100).round(2)

