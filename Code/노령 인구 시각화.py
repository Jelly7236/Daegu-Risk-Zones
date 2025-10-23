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
gdf = gpd.read_file("../Data/시각화/대구_행정동/대구_행정동_군위포함.shp")
print(gdf.crs)
gdf = gdf.to_crs(epsg=4326)

import json
with open("../Data/시각화/대구_행정동/대구_행정동_군위포함.geojson", encoding='utf-8') as f:
 geojson_data = json.load(f)

g2_by_dong.rename(columns={'동·읍·면': 'ADM_DR_NM'}, inplace=True)

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
gdf2 = gpd.read_file("../Data/시각화/대구_시군구_군위포함/대구광역시_시군구_군위포함.shp")
print(gdf2.crs)
gdf2 = gdf2.to_crs(epsg=4326)
# gdf2.to_file("../Data/대구_시군구_군위포함.geojson", driver="GeoJSON")

import json
with open("../Data/시각화/대구_시군구_군위포함/대구_시군구_군위포함.geojson", encoding='utf-8') as f:
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