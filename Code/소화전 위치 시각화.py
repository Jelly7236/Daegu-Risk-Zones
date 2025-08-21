# 대구광역시 119안전센터 및 소화장치 위치 시각화

# 데이터 출처
# 대구광역시_소방 긴급구조 비상 소화장치 현황
# https://www.data.go.kr/data/15117284/fileData.do

# 소방청_119안전센터 현황
# https://www.data.go.kr/data/15065056/fileData.do

import pandas as pd 
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

loc_119 = pd.read_csv("../Data/대구광역시_소방서_위치.csv")
loc_fire = pd.read_csv("../Data/대구광역시_용수시설_위치.csv")




# 대구광역시 구별 소방 안전센터 시각화 
import json
with open ("../Data/시각화/대구_시군구_군위포함/대구_시군구_군위포함.geojson", encoding='utf-8') as f:
    geojson_data = json.load(f)
# print(geojson_data.keys())

import plotly.graph_objects as go

fig = go.Figure()
# 119안전센터(빨간점)
fig.add_trace(go.Scattermapbox(
    lat=loc_119["위도"],
    lon=loc_119["경도"],
    mode="markers",
    marker=go.scattermapbox.Marker(size=15, color="red"),
    name="119안전센터",  # 범례에 표시됨
    hovertemplate="<b>구:</b> %{customdata[0]}<br><b>동:</b> %{customdata[1]}<extra></extra>",
    customdata=loc_119[["구이름", "동이름"]].values,
))
fig.update_traces(marker=dict(size=15))

# 구별 소방 긴급구조 비상 소화장치 scatter mapbox
fig.add_trace(go.Scattermapbox(
    lat=loc_fire["위도"],
    lon=loc_fire["경도"],
    mode="markers",
    marker=go.scattermapbox.Marker(size=3, color="blue"),
    name="소화장치",
    hovertemplate="<b>소재지지번주소:</b> %{customdata}<extra></extra>",
    customdata=loc_fire["소재지지번주소"].values,
))

fig.update_layout(
    mapbox_style="carto-positron",
    mapbox_layers=[
        {
            "sourcetype": "geojson",
            "source": geojson_data,
            "type": "line",
            "color": "green",
            "line": {"width": 1},
        }
    ],
    mapbox_center={"lat": 35.8714, "lon": 128.6014},
    # zoom 값을 높이면 더 '줌인'됩니다. 지역에 따라 10~12 정도가 적당합니다.
    mapbox_zoom=11,
    margin={"r":0, "t":30, "l":0, "b":0},
)
fig.show()