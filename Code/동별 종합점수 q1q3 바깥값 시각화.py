# -*- coding: utf-8 -*-
import csv, json, re
import numpy as np
import pandas as pd
import plotly.express as px
from pathlib import Path

# ================== 경로 ==================
csv_path = Path("../Data/건축물대장_v0.5.csv")
geojson_path = Path("../Data/시각화/대구_행정동/대구_행정동_군위포함.geojson")
out_html = Path("./동평균_Q1Q3_전체_폴리곤_색칠.html")
# ========================================

# ========== 1) CSV 로드 (구분자 자동 감지) ==========
with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
    sample = "".join([next(f) for _ in range(50)])
dialect = csv.Sniffer().sniff(sample, delimiters=[",", "\t", ";", "|"])
sep = dialect.delimiter

df = pd.read_csv(csv_path, sep=sep, engine="python", encoding="utf-8")
# (선택) 군위군 제외
df = df.loc[~(df["대지위치"].str.contains("군위군", na=False)), :]

with open(geojson_path, "r", encoding="utf-8") as f:
    gj = json.load(f)

# 점수 숫자화
score_col = "종합점수"
if score_col not in df.columns:
    raise RuntimeError("CSV에 '종합점수' 컬럼이 없습니다.")
df[score_col] = pd.to_numeric(df[score_col], errors="coerce")

# ========== 2) 이름 정규화 및 _key 심기 ==========
def norm_name(x):
    if pd.isna(x): return None
    s = str(x)
    s = re.sub(r"\s+", "", s)          # 공백 제거
    s = re.sub(r"[(){}\[\]-]", "", s)  # 괄호/하이픈 제거
    s = s.replace("ㆍ", "")
    return s

CSV_KEY = "ADM_DR_NM"  # CSV 동명
GJ_KEY  = "ADM_DR_NM"  # GeoJSON 동명 (파일에 맞게)

if CSV_KEY not in df.columns:
    raise RuntimeError(f"CSV에 '{CSV_KEY}' 컬럼이 없습니다.")
if not gj.get("features"):
    raise RuntimeError("GeoJSON features가 비어 있습니다.")

df["_key"] = df[CSV_KEY].map(norm_name)
for feat in gj["features"]:
    props = feat.get("properties", {}) or {}
    props["_key"] = norm_name(props.get(GJ_KEY))
    feat["properties"] = props

# (선택) 매칭 진단
df_keys = set(df["_key"].dropna().unique())
gj_keys = {feat["properties"].get("_key") for feat in gj["features"] if feat.get("properties")}
print(f"[매칭진단] CSV만 있는 동 수: {len(df_keys - gj_keys)}, GeoJSON만 있는 동 수: {len(gj_keys - df_keys)}")

# ========== 3) 동별 평균 계산 ==========
# hover용 원본 동명 매핑
name_map = (df[[CSV_KEY, "_key"]]
            .dropna()
            .drop_duplicates()
            .groupby("_key")[CSV_KEY]
            .first()
            .reset_index()
            .rename(columns={CSV_KEY: "행정동명"}))

df_mean = (df.dropna(subset=["_key", score_col])
             .groupby("_key", as_index=False)[score_col]
             .mean()
             .rename(columns={score_col: "동별_평균점수"}))

df_mean = df_mean.merge(name_map, on="_key", how="left")

# ========== 4) Q1/Q3 계산 (동별 평균 분포 기준) ==========
Q1 = df_mean["동별_평균점수"].quantile(0.25)
Q3 = df_mean["동별_평균점수"].quantile(0.75)
print(f"[분위수] Q1={Q1:.4f}, Q3={Q3:.4f}")

# 구간 라벨링: Q1 밖(녹), Q1~Q3(연회색), Q3 밖(빨)
df_mean["구간"] = np.select(
    [df_mean["동별_평균점수"] < Q1, df_mean["동별_평균점수"] > Q3],
    ["Q1밖(낮음)", "Q3밖(높음)"],
    default="Q1~Q3"
)

# ========== 5) Choropleth (세 구간 모두 색칠) ==========
color_map = {
    "Q1밖(낮음)": "#2ecc71",  # green
    "Q1~Q3":     "#e0e0e0",  # light gray
    "Q3밖(높음)": "#e74c3c",  # red
}

fig = px.choropleth_mapbox(
    df_mean,                      # 전체(세 구간)
    geojson=gj,
    locations="_key",
    featureidkey="properties._key",
    color="구간",
    color_discrete_map=color_map,
    category_orders={"구간": ["Q1밖(낮음)", "Q1~Q3", "Q3밖(높음)"]},
    hover_name="행정동명",
    hover_data={"동별_평균점수":":.2f", "구간": True},
    mapbox_style="open-street-map",
    opacity=0.88,
    center={"lat": 35.8714, "lon": 128.6014},  # 대구 중심 근처
    zoom=9,
)

fig.update_layout(
    margin=dict(l=0, r=0, t=40, b=0),
    title=f"동별 평균 종합점수 Q1~Q3 포함 색칠 (Q1={Q1:.2f}, Q3={Q3:.2f})",
    legend_title_text="구간"
)

# (선택) 모든 행정동 경계선도 함께 보이게 하고 싶으면 아래 주석 해제
# import plotly.graph_objects as go
# for i, feat in enumerate(gj["features"]):
#     props = feat.get("properties", {}) or {}
#     props["__fid"] = i
#     feat["properties"] = props
# border_trace = go.Choroplethmapbox(
#     geojson=gj,
#     locations=[feat["properties"]["__fid"] for feat in gj["features"]],
#     z=[0]*len(gj["features"]),
#     featureidkey="properties.__fid",
#     showscale=False,
#     marker=dict(opacity=0.0, line=dict(width=1.2, color="#202020")),
#     hoverinfo="skip"
# )
# fig.add_trace(border_trace)

fig.write_html(out_html)
print(f"[저장 완료] {out_html.resolve()}")
# fig.show()
