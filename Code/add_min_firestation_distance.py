import pandas as pd
import numpy as np

# 데이터 불러오기
df_building = pd.read_csv('../Data/건축물대장_v0.2.csv')
df_hydrant = pd.read_csv('../Data/대구광역시_소방장치_위치.csv')
df_firestation = pd.read_csv('../Data/대구광역시_소방서_위치.csv')

# 거리계산 함수 정의
def haversine_min_distance(lat1, lon1, hy_lats, hy_lons):
    R = 6371000  # 지구 반지름 (m)
    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    
    dlat = hy_lats - lat1
    dlon = hy_lons - lon1
    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(hy_lats) * np.sin(dlon / 2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    distances = R * c
    return distances.min()

# 위경도 라디안화
hydrant_lats = np.radians(df_hydrant["위도"].values)
hydrant_lons = np.radians(df_hydrant["경도"].values)
station_lats = np.radians(df_firestation["위도"].values)
station_lons = np.radians(df_firestation["경도"].values)

# 소화전거리 계산 및 추가
df_building['소화전거리'] = df_building.apply(
    lambda row: haversine_min_distance(row["위도"], row["경도"], hydrant_lats, hydrant_lons),
    axis=1
)
# 소방서거리 계산 및 추가
df_building["소방서거리"] = df_building.apply(
    lambda row: haversine_min_distance(row["위도"], row["경도"], station_lats, station_lons),
    axis=1
)

# 결과 저장
df_building.to_csv('../Data/건축물대장_v0.3.csv', index=False)