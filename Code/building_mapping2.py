# %% 라이브러리 호출
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon
import folium
import branca.colormap as cm
# %% 정사각형 그리드 생성 함수
# ------------------------------
def generate_square_grid(polygon, cell_size_m=100):
    polygon_utm = gpd.GeoSeries([polygon], crs="EPSG:4326").to_crs(epsg=5186).geometry[0]
    minx, miny, maxx, maxy = polygon_utm.bounds

    x_coords = np.arange(minx, maxx, cell_size_m)
    y_coords = np.arange(miny, maxy, cell_size_m)

    squares = [
        Polygon([
            (x, y),
            (x + cell_size_m, y),
            (x + cell_size_m, y + cell_size_m),
            (x, y + cell_size_m)
        ])
        for x in x_coords for y in y_coords
    ]

    grid = gpd.GeoDataFrame(geometry=squares, crs="EPSG:5186")
    clipped = gpd.clip(grid, polygon_utm)
    return clipped.to_crs(epsg=4326)

# %% Polygon shapefile & 필터링
dnm_gdf = gpd.read_file("../Data/시각화/대구_행정동/대구_행정동_군위포함.shp").to_crs(epsg=4326)
cond1 = dnm_gdf['ADM_DR_NM'] == '하빈면'
cond2 = dnm_gdf['ADM_DR_NM'] == '가창면'
dnm_gdf_filtered = dnm_gdf[cond1|cond2]
daegu_polygon = dnm_gdf_filtered.union_all()

# %% 용수시설 & 필터링
hyd = pd.read_csv('../Data/소방용수시설_동추가.csv')
cond3 = hyd['ADM_NM'] == '하빈면'
cond4 = hyd['ADM_NM'] == '가창면'
hyd_filtered = hyd[cond3|cond4]
gdf_fire = gpd.GeoDataFrame(hyd_filtered, geometry=gpd.points_from_xy(hyd_filtered['경도'], hyd_filtered['위도']), crs='EPSG:4326')

# %% 소방서 & 필터링
df_station = pd.read_csv('../Data/대구광역시_소방서_위치.csv')
station_filtered = df_station[df_station['동이름'] == '가창'] # 하빈면은 없음
gdf_station = gpd.GeoDataFrame(station_filtered, geometry=gpd.points_from_xy(station_filtered['경도'], station_filtered['위도']), crs='EPSG:4326')


# %% 건물 데이터 (예: 건물높이, 건물나이 포함) & 필터링
building = pd.read_csv('../Data/건축물대장_v0.6.csv')
building.columns
cond5 = building['ADM_DR_NM'] == '가창면'
cond6 = building['ADM_DR_NM'] == '하빈면'
building_filtered = building[cond5|cond6]
gdf_building = gpd.GeoDataFrame(building_filtered,
    geometry=gpd.points_from_xy(building_filtered['경도'], building_filtered['위도']),
    crs='EPSG:4326')

# %% 그리드 생성
grid_cells = generate_square_grid(daegu_polygon, cell_size_m=100)

# %%용수시설 100m 버퍼 처리
gdf_fire_utm = gdf_fire.to_crs(epsg=5186)
fire_buffer_union = gdf_fire_utm.dissolve().buffer(100).to_crs(epsg=4326).union_all()

# %% 소방서 4km 버퍼 처리
gdf_station_utm = gdf_station.to_crs(epsg=5186)
station_buffer_union = gdf_station_utm.dissolve().buffer(4000).to_crs(epsg=4326).union_all()

# %% 그리드 필터링

# 용수시설 및 소방서 범위 밖 셀 추출
grid_cells = grid_cells.reset_index(drop=True)
grid_cells['cell_id'] = grid_cells.index

grid_outside_fire = grid_cells[~grid_cells.geometry.intersects(fire_buffer_union)]
final_cells = grid_outside_fire[~grid_outside_fire.geometry.intersects(station_buffer_union)]

# %% 건물 점수 계산 (ex. 주용도 + 나이)

# 건물 ↔ 셀 공간 조인
for _df in (gdf_building, final_cells):
    _df.drop(columns=[c for c in ("index_right", "index_left") if c in _df.columns],
             inplace=True, errors="ignore")
building_with_cell = gpd.sjoin(gdf_building, final_cells, how='inner', predicate='within')

# 점수 계산
building_with_cell['score'] = building_with_cell['주용도점수'] + building_with_cell['건물노후도점수']
cell_score = building_with_cell.groupby('cell_id')['score'].sum().reset_index()
cell_score.columns = ['cell_id', 'score_sum']

# 점수 결과 병합
final_cells_with_score = final_cells.merge(cell_score, on='cell_id', how='left')
final_cells_with_score['score_sum'] = final_cells_with_score['score_sum'].fillna(0)


# %% 점수가 0보다 큰 셀만 필터링

visible_cells = final_cells_with_score[final_cells_with_score['score_sum'] > 0]


# %%folium 지도 시각화

m = folium.Map(location=[35.85, 128.6], zoom_start=13, tiles='CartoDB positron')

# 컬러맵
max_score = visible_cells['score_sum'].max()
colormap = cm.linear.YlOrRd_09.scale(0, max_score)
colormap.caption = '셀별 건물 용도점수+나이점수 합계'

# GeoJson 추가
folium.GeoJson(
    visible_cells,
    name='위험지역 점수',
    style_function=lambda feature: {
        'fillColor': colormap(feature['properties']['score_sum']),
        'color': 'black',
        'weight': 0.3,
        'fillOpacity': 0.6
    },
    tooltip=folium.GeoJsonTooltip(fields=['score_sum'], aliases=['용도점수+나이점수 합계'])
).add_to(m)
# %% 소방용수시설 표시(시설번호 혹은 종류, 종류 코드 표기 가능)

# 소방용수시설
for _, row in gdf_fire.iterrows():
    folium.CircleMarker(
        location=[row['위도'], row['경도']],
        radius=3,  # 원의 반지름 (픽셀 단위)
        popup=row['시설번호'],
        color='blue',
        fill=True,
        fill_color='blue',
        fill_opacity=1
    ).add_to(m) # 소방용수시설 표시

# %% 소방용수시설 버퍼(100m) 표시
fire_buffer = gdf_fire.to_crs(epsg=5186).buffer(100).to_crs(epsg=4326)

# GeoDataFrame으로 묶기
fire_buffer_gdf = gpd.GeoDataFrame(geometry=fire_buffer, crs='EPSG:4326')

# 지도에 추가
folium.GeoJson(
    fire_buffer_gdf,
    name='소방용수시설 100m 범위',
    style_function=lambda x: {
        'fillColor': 'blue',
        'color': 'blue',
        'weight': 1,
        'fillOpacity': 0.1
    }
).add_to(m)

# %% 소방서 표시
for idx, row in gdf_station.iterrows():
    folium.Marker(
        location=[row['위도'], row['경도']],
        popup=row.get('소방서명', '119안전센터명'),
        icon=folium.Icon(color='red', icon='fire', prefix='fa')
    ).add_to(m)

# %% 소방서 버퍼(4000m) 표시
station_buffer = gdf_station.to_crs(epsg=5186).buffer(4000).to_crs(epsg=4326)
station_buffer_gdf = gpd.GeoDataFrame(geometry=station_buffer, crs='EPSG:4326')

# 지도에 추가
folium.GeoJson(
    station_buffer_gdf,
    name='소방서 4km 범위',
    style_function=lambda x: {
        'fillColor': 'red',
        'color': 'red',
        'weight': 1,
        'fillOpacity': 0.1
    }
).add_to(m)
# %% 행정동 짙은 경계 추가
folium.GeoJson(
    dnm_gdf,
    name='행정동 경계',
    style_function=lambda feature: {
        'fillOpacity': 0,       # 내부는 투명
        'color': 'black',       # 경계선 색상
        'weight': 2,            # 선 두께 (더 두껍게)
        'dashArray': '3, 6'     # 점선 스타일 (선택사항)
    },
    tooltip=folium.GeoJsonTooltip(fields=['ADM_DR_NM'], aliases=['행정동'])  # 이름 표시
).add_to(m)
# %% 컬러맵 범례 (한 번만)
colormap.add_to(m)


# %%지도 출력 또는 저장

# Jupyter 환경이면 그냥 m 출력
m

# %% 저장
m.save('위험지역_용도+노후화_지도.html')

