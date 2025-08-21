import pandas as pd

df_buildings = pd.read_csv('../Data/건축물대장_v0.6.csv')

df_buildings_grouped = df_buildings.groupby('EMD_NM')[['건물노후도점수', '지상층수점수', 
                                                       '지하층수점수', '주용도점수', '구조점수', 
                                                       '비상용승강기점수', '소방서거리점수', 
                                                       '소방용수시설거리점수']].mean().reset_index()

df_buildings_grouped.to_csv('../Data/건축물대장_회귀분석용.csv')