import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

gdf_admin = gpd.read_file('../Data/시각화/대구_행정동/대구_행정동_군위포함.shp')
df_buildings = pd.read_csv('../Data/건축물대장_v0.3.csv')

geometry = [Point(xy) for xy in zip(df_buildings['경도'], df_buildings['위도'])]
gdf_buildings = gpd.GeoDataFrame(df_buildings, geometry=geometry, crs='EPSG:4326')

print(gdf_admin.crs)

# 좌표계가 다르면 통일
if gdf_admin.crs != gdf_buildings.crs:
    gdf_admin = gdf_admin.to_crs(gdf_buildings.crs)

gdf_result = gpd.sjoin(gdf_buildings, gdf_admin, how='left', predicate='within')
gdf_result.to_csv('../Data/건축물대장_v0.4.csv', index=False)

# 건물 공간 분포 시각화
import geopandas as gpd
import pandas as pd
import folium
from folium.plugins import MarkerCluster

# -----------------------------
# 1. GeoDataFrame 로드
# -----------------------------
# (1) 읍면동 shapefile
gdf_admin = gpd.read_file("../Data/시각화/대구_행정동/대구_행정동_군위포함.shp")

# (2) 건물 데이터 CSV -> GeoDataFrame
df = pd.read_csv('../Data/건축물대장_통합_점수.csv')  # lon, lat, 점수, 건물ID 등 포함
from shapely.geometry import Point
geometry = [Point(xy) for xy in zip(df['경도'], df['위도'])]
gdf_buildings = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')

# -----------------------------
# 2. 행정동과 건물 spatial join (건물이 속한 읍면동 찾기)
# -----------------------------
# shapefile 좌표계 통일
gdf_admin = gdf_admin.to_crs(epsg=4326)
gdf_buildings = gdf_buildings.to_crs(epsg=4326)

# 공간조인: 건물이 속한 읍면동 정보 추가
gdf_buildings = gpd.sjoin(gdf_buildings, gdf_admin[['ADM_DR_NM', 'geometry']], how='left', predicate='within')

# -----------------------------
# 3. 지도 시각화
# -----------------------------
# 지도 중심
map_center = [gdf_buildings.geometry.y.mean(), gdf_buildings.geometry.x.mean()]
m = folium.Map(location=map_center, zoom_start=12)

# (1) 행정동 경계 (choropleth 배경)
folium.GeoJson(
    gdf_admin,
    name='읍면동 경계',
    style_function=lambda x: {
        'fillColor': '#00000000',
        'color': 'blue',
        'weight': 1,
        'fillOpacity': 0.1
    },
    tooltip=folium.GeoJsonTooltip(fields=['ADM_DR_NM'], aliases=['읍면동'])
).add_to(m)

# (2) 건물 위치 마커 (점수 + 속성 팝업)
marker_cluster = MarkerCluster().add_to(m)

for idx, row in gdf_buildings.iterrows():
    popup_text = f"""
    <b>건물ID:</b> {row.get('건물ID', 'N/A')}<br>
    <b>종합점수:</b> {row.get('종합점수', 'N/A')}<br>
    <b>읍면동:</b> {row.get('ADM_DR_NM', 'N/A')}
    """
    folium.Marker(
        location=[row.geometry.y, row.geometry.x],
        popup=popup_text,
        icon=folium.Icon(color='green', icon='home', prefix='fa')
    ).add_to(marker_cluster)

# -----------------------------
# 4. 지도 저장 또는 표시
# -----------------------------
m.save("건물_읍면동_지도.html")
m