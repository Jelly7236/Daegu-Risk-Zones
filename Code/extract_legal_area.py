import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

gdf_admin = gpd.read_file('../Data/시각화/대구_법정동/LSMD_ADM_SECT_UMD_27_202506.shp', encoding="cp949")
df_buildings = pd.read_csv('../Data/건축물대장_v0.5.csv')

geometry = [Point(xy) for xy in zip(df_buildings['경도'], df_buildings['위도'])]
gdf_buildings = gpd.GeoDataFrame(df_buildings, geometry=geometry, crs='EPSG:4326')

print(gdf_admin.crs)

# 좌표계가 다르면 통일
if gdf_admin.crs != gdf_buildings.crs:
    gdf_admin = gdf_admin.to_crs(gdf_buildings.crs)

gdf_buildings.rename(columns={'ADM_DR_NM':'행정동'}, inplace=True)

_reserved = ["index_right", "index_left"]

gdf_buildings = gdf_buildings.drop(columns=[c for c in _reserved if c in gdf_buildings.columns], errors="ignore")
gdf_admin     = gdf_admin.drop(columns=[c for c in _reserved if c in gdf_admin.columns], errors="ignore")

gdf_result = gpd.sjoin(
    gdf_buildings,
    gdf_admin[['geometry', 'EMD_NM']],  # geometry + 필요한 컬럼만 선택
    how='left',
    predicate='within'
)
gdf_result = gdf_result.drop(columns=[c for c in _reserved if c in gdf_result.columns], errors="ignore")

gdf_result.to_csv('../Data/건축물대장_v0.6.csv', index=False)
gdf_result.columns