import pandas as pd
import numpy as np
import re

df_building_original = pd.read_csv("../Data/건축물대장_v0.1.csv")

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


# 사용승인년도 결측치 중 구조코드명별 퍼센트
df_building_filter = df_building_original.loc[df_building_original["사용승인년도"].isna(), :]

df_building_grouped = (df_building_filter
                       .groupby('구조코드명', dropna=False)
                       .size()
                       .rename('수')
                       .reset_index())

df_building_grouped['퍼센트'] = (df_building_grouped['수'] / len(df_building_filter) * 100).round(2)
df_building_grouped = df_building_grouped.sort_values(['수','구조코드명'], ascending=[False, True], ignore_index=True)

df_building_grouped

# 사용승인년도 결측치 중 일반목구조가 전체 일반목구조에 어느정도 해당하는지
original_wooden_structure = ((df_building_original["구조코드명"] == "일반목구조") & (df_building_original["위도"] != np.nan)).sum()
filter_wooden_structure = df_building_grouped.loc[df_building_grouped["구조코드명"] == "일반목구조", "수"][2]
(filter_wooden_structure / original_wooden_structure * 100).round(2)

# 대지위치에서 '구/군' 추출
def extract_gu_gun(addr: str):
    if pd.isna(addr):
        return np.nan
    s = str(addr).strip()
    # 공백 기준 토큰화 후 앞쪽에서 '구/군'으로 끝나는 첫 토큰을 반환
    for tok in re.split(r"\s+", s):
        tok_clean = re.sub(r"[^가-힣A-Za-z0-9]", "", tok)  # 특수문자 제거
        if tok_clean.endswith(("구", "군")):
            return tok_clean
    # 토큰으로 못 찾았으면, 문자열 전체에서 백업 탐색
    m = re.search(r"([가-힣A-Za-z]+(?:구|군))", s)
    return m.group(1) if m else np.nan

df = df_building_original.copy()
df["구군"] = df["대지위치"].map(extract_gu_gun).fillna("미상")

# 구군별 결측치 비율 계산
mask = df["구조코드명"].isna()
by_gu_gun = (
    df.assign(결측=mask)
      .groupby("구군", dropna=False)["결측"]
      .agg(수="sum", 전체="count")
      .assign(퍼센트=lambda x: (x["수"] / x["전체"] * 100).round(2))
      .sort_values(["수", "구군"], ascending=[False, True])
      .reset_index()
)
by_gu_gun

mask = df["기타구조"].isna()
by_gu_gun = (
    df.assign(결측=mask)
      .groupby("구군", dropna=False)["결측"]
      .agg(수="sum", 전체="count")
      .assign(퍼센트=lambda x: (x["수"] / x["전체"] * 100).round(2))
      .sort_values(["수", "구군"], ascending=[False, True])
      .reset_index()
)
by_gu_gun

mask = df["사용승인년도"].isna()
by_gu_gun = (
    df.assign(결측=mask)
      .groupby("구군", dropna=False)["결측"]
      .agg(수="sum", 전체="count")
      .assign(퍼센트=lambda x: (x["수"] / x["전체"] * 100).round(2))
      .sort_values(["수", "구군"], ascending=[False, True])
      .reset_index()
)
by_gu_gun

mask = (df["위도"].isna() & df["경도"].isna())
by_gu_gun = (
    df.assign(결측=mask)
      .groupby("구군", dropna=False)["결측"]
      .agg(수="sum", 전체="count")
      .assign(퍼센트=lambda x: (x["수"] / x["전체"] * 100).round(2))
      .sort_values(["수", "구군"], ascending=[False, True])
      .reset_index()
)
by_gu_gun

df_building_original = df_building_original.dropna(subset=["구조코드명"])

# 결측치 제거
df_building_original = df_building_original.dropna()
df_building_original.to_csv("../Data/건축물대장_v0.2.csv", index=False, encoding="utf-8-sig")