import pandas as pd
import numpy as np
import plotly.express as px
# %% 데이터 로드
df = pd.read_csv('../Data/건축물대장_v0.5.csv')
hyd = pd.read_csv('../Data/대구광역시_용수시설_위치.csv')
#firestn = pd.read_csv('대구광역시_소방서_위치데이터.csv', encoding='cp949')
# %%
hydrant_lats = np.radians(hyd["위도"].values)
hydrant_lons = np.radians(hyd["경도"].values)
# %% 거리계산 함수 정의
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
# %% min({소화전거리(m)})
df['소방용수시설거리'] = df.apply(
    lambda row: haversine_min_distance(row["위도"], row["경도"], hydrant_lats, hydrant_lons),
    axis=1
)
# %%
df['소방용수시설거리'].head()
# %% 소방서 데이터
firestation = pd.read_csv('../Data/대구광역시_소방서_위치.csv')
firestation.head()
# %% min({소방서거리(m)})
station_lats = np.radians(firestation["위도"].values)
station_lons = np.radians(firestation["경도"].values)
df["소방서거리"] = df.apply(
    lambda row: haversine_min_distance(row["위도"], row["경도"], station_lats, station_lons),
    axis=1
)

# %% 소방서거리, 소화전거리 분포 시각화

# 소방서거리 분포
fig1 = px.histogram(df, x="소방서거리", nbins=100, title="가장 가까운 소방서 거리 분포", marginal="box")
fig1.update_layout(
    bargap=0.1,
    xaxis_title="거리(m)",
    yaxis_title="건물 수",
    template='plotly_white'
)

fig1.show()

# 소화전거리 분포
fig2 = px.histogram(df, x="소방용수시설거리", nbins=100, title="가장 가까운 소방용수시설 거리 분포", marginal="box")
fig2.update_layout(
    bargap=0.1,
    xaxis_title="거리(m)",
    yaxis_title="건물 수",
    template='plotly_white'
)

fig2.show()