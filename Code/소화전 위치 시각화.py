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

loc_119 = pd.read_csv("../Data/대구_소방서_위치.csv")
loc_fire = pd.read_csv("../Data/대구_소방장치_위치.csv")




# 대구광역시 구별 소방 안전센터 시각화 
import json
with open ("../Data/시각화/대구_시군구_군위포함/대구_시군구_군위포함.geojson", encoding='utf-8') as f:
    geojson_data = json.load(f)
# print(geojson_data.keys())

# 구별 소방 안전센터 scatter_mapbox
fig = px.scatter_mapbox(
    loc_119, lat="위도", lon="경도", color="구이름",
    hover_name="119안전센터명",
    hover_data={"위도": False, "경도": False, "구이름": True, "동이름": True},
    zoom=11,
    height=650,
)
fig.update_traces(marker=dict(size=15))

# 구별 소방 긴급구조 비상 소화장치 scatter mapbox
fig.add_trace(go.Scattermapbox(
    lat=loc_fire["위도"],
    lon=loc_fire["경도"],
    mode="markers",
    marker=go.scattermapbox.Marker(size=5, color="blue"),
    name="소화장치",
    hovertemplate="<b>구:</b> %{customdata[0]}<br><b>동:</b> %{customdata[1]}<extra></extra>",
    customdata=loc_fire[["구이름", "동이름"]].values,
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
    margin={"r":0, "t":30, "l":0, "b":0},
)
fig.show()

