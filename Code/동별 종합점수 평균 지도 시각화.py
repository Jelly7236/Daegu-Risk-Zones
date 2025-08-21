import json, re
import pandas as pd
import plotly.express as px
from pathlib import Path
import numpy as np

# 경로
csv_path = Path("../Data/건축물대장_v0.6.csv")
geojson_path = Path("../Data/시각화/대구_행정동/대구_행정동_군위포함.geojson")

# 1) 데이터 로드
df = pd.read_csv(csv_path)
df.loc[df["ADM_DR_NM"].isna(), "대지위치"]
with open(geojson_path, "r", encoding="utf-8") as f:
    gj = json.load(f)

df["종합점수"] = pd.to_numeric(df["종합점수"], errors="coerce")

# 2) 정규화 함수
def norm_name(x):
    if pd.isna(x): return None
    s = str(x)
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[(){}\[\]-]", "", s)
    s = s.replace("ㆍ", "")
    return s

# 3) 컬럼
CSV_KEY = "ADM_DR_NM"   # CSV의 구군명
GJ_KEY  = "ADM_DR_NM"      # GeoJSON의 행정동명 (보통 소문자)

# 4) 키 만들기 (정규화)
df["_key"] = df[CSV_KEY].map(norm_name)
for feat in gj["features"]:
    props = feat.get("properties", {}) or {}
    props["_key"] = norm_name(props.get(GJ_KEY))
    feat["properties"] = props

# 5) 동별 평균 계산
df_avg = (
    df.dropna(subset=["_key"])
      .groupby("_key", as_index=False)["종합점수"]
      .mean()
      .rename(columns={"종합점수": "종합점수_평균"})
)

# 6) 색상 스케일 (하양→빨강)
white_to_red = [
    [0.0, "#ffffff"],
    [1.0, "#ff0000"]
]
vmin = float(df_avg["종합점수_평균"].min())
vmax = float(df_avg["종합점수_평균"].max())

# 7) 시각화
fig = px.choropleth_mapbox(
    df_avg,
    geojson=gj,
    locations="_key",                   # DF의 키
    featureidkey="properties._key",     # GeoJSON의 키
    color="종합점수_평균",
    color_continuous_scale=white_to_red,
    range_color=(vmin, vmax),
    mapbox_style="open-street-map",
    opacity=0.75,
    center={"lat": 35.8714, "lon": 128.6014},
    zoom=9,
    hover_name="_key",
    hover_data={"종합점수_평균":":.2f"}
)
fig.update_layout(margin=dict(l=0,r=0,t=40,b=0), title="동별 점수평균 지도 시각화")
fig.show()
