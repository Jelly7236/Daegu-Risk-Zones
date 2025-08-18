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
with open ("../Data/대구_시군구_군위포함.geojson", encoding='utf-8') as f:
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




#======================================
# 노령 인구 비율 시각화
#======================================

# 동별 노령인구 비율 시각화
import pandas as pd 
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
df = pd.read_csv("../Data/동별인구.csv")
new = df[['군·구', '동·읍·면', '고령자_비율','위도','경도']]

# 동별 고령자 비율 값
g2_by_dong = new.groupby(['동·읍·면'])[['고령자_비율']].sum()
g2_by_dong = g2_by_dong.sort_values(by='고령자_비율',ascending=False)
g2_by_dong.rename(columns={'고령자_비율': '고령자_평균비율'}, inplace=True)
g2_by_dong = g2_by_dong.reset_index()
# g2_by_dong.info()

import geopandas as gpd
gdf = gpd.read_file("../Data/대구_행정동_군위포함.shp")
print(gdf.crs)
gdf = gdf.to_crs(epsg=4326)
gdf.to_file("../Data/대구_행정동_군위포함.geojson", driver="GeoJSON")

import json
with open("../Data/대구_행정동_군위포함.geojson", encoding='utf-8') as f:
 geojson_data = json.load(f)
# print(geojson_data.keys())
# print(geojson_data['features'][0]['properties'])

# gdf 파일에 유천동이 없고 g2_by_dong 파일에 유천동이 있어 행 삭제
cond = (gdf['ADM_DR_CD'] == '유천동')
gdf[cond]
g2_by_dong.rename(columns={'동·읍·면': 'ADM_DR_NM'}, inplace=True)
cond = (g2_by_dong['ADM_DR_NM'] == '유천동')
g2_by_dong = g2_by_dong.drop(g2_by_dong[cond].index)

# 불로봉무동 이름 변경
g2_by_dong.loc[g2_by_dong['ADM_DR_NM'] == '불로봉무동', 'ADM_DR_NM'] = '불로·봉무동'


# 동별 노령인구 비율 시각화
fig = px.choropleth_mapbox(g2_by_dong,
 geojson=geojson_data,
 locations="ADM_DR_NM",
 featureidkey="properties.ADM_DR_NM",
 color="고령자_평균비율",
 color_continuous_scale="Greens",
 mapbox_style="carto-positron",
 center={"lat":35.87702415809577, "lon":128.58970500739858},
 zoom=10,                
opacity=0.7,               
title="대구광역시 동별 노인평균인구비율"  
)
fig.update_layout(margin={"r":0,"t":30,"l":0,"b":0}) 
fig.show() 


# ===================================
# 구별 고령자 비율 평균
g1_by_gu = new.groupby(['군·구'])[['고령자_비율']].mean()
g1_by_gu = g1_by_gu.reset_index()
g1_by_gu = g1_by_gu.sort_values(by='고령자_비율',ascending=False)
g1_by_gu.rename(columns={'군·구': 'SIGUNGU_NM', '고령자_비율': '고령자_평균비율',}, inplace=True)


import geopandas as gpd
gdf2 = gpd.read_file("../Data/대구광역시_시군구_군위포함.shp")
print(gdf2.crs)
gdf2 = gdf2.to_crs(epsg=4326)
gdf2.to_file("../Data/대구_시군구_군위포함.geojson", driver="GeoJSON")

import json
with open("../Data/대구_시군구_군위포함.geojson", encoding='utf-8') as f:
 geojson_data2 = json.load(f)
print(geojson_data2.keys())

print(geojson_data2['features'][0]['properties'])

# 구별 노령 인구 비율 시각화
fig = px.choropleth_mapbox(g1_by_gu,
 geojson=geojson_data2,
 locations="SIGUNGU_NM",
 featureidkey="properties.SIGUNGU_NM",
 color="고령자_평균비율",
 color_continuous_scale="Greens",
 mapbox_style="carto-positron",
 center={"lat":35.87702415809577, "lon":128.58970500739858},
 zoom=10,                
opacity=0.7,               
title="대구광역시 구별 노인평균인구비율"  
)
fig.update_layout(margin={"r":0,"t":30,"l":0,"b":0}) 
fig.show()