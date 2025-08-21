import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

fire_df = pd.read_csv("../Raw Data/소방청_화재발생 정보.csv", encoding='cp949')

# 대구광역시 추출
cond1 = (fire_df['시도'] == '대구광역시')
daegu_fire_df = fire_df[cond1]
daegu_fire_df = daegu_fire_df[['화재발생년원일','시군구','화재유형','발화요인소분류','인명피해(명)소계','재산피해소계']]

daegu_fire_df['화재발생년원일'] = pd.to_datetime(daegu_fire_df['화재발생년원일'])


daegu_fire_by_type = daegu_fire_df.groupby('화재유형')[['시군구']].count().sort_values(by='시군구', ascending=False)
daegu_fire_by_type = daegu_fire_by_type.reset_index()
daegu_fire_by_type.rename(columns={'시군구': '화재건수'}, inplace=True)
daegu_fire_by_type


# 한글 폰트 설정 (윈도우 기준, mac은 'AppleGothic')
plt.rc('font', family='Malgun Gothic')

# 색상 지정: 건축,구조물만 진하게, 나머지는 연하게
color_map = ['#C62828' if x == '건축,구조물' else '#FFCDD2' for x in daegu_fire_by_type['화재유형']]

# 시각화
plt.figure(figsize=(10, 6))
sns.barplot(x='화재유형', y='화재건수', data=daegu_fire_by_type, palette=color_map)

plt.title('화재 유형별 대구화재 건수')
plt.xlabel('화재 유형')
plt.ylabel('화재 건수')
plt.xticks(rotation=0)

for i, v in enumerate(daegu_fire_by_type['화재건수']):
    try:
        val = float(v)
        plt.text(i, val + 50, str(v), ha='center', va='bottom', fontsize=12)
    except (ValueError, TypeError):
        # 숫자가 아니면 표시하지 않거나 0으로 처리
        pass

plt.tight_layout()
plt.show()


# 화재유형 건축,구조물 간추리고, 어디 구가 많은 화재가 일어나는지
daegu_building_fire_df = daegu_fire_df[daegu_fire_df['화재유형'] == '건축,구조물']
# daegu2
daegu_building_fire_by_gu = daegu_building_fire_df.groupby('시군구')[['화재유형']].count().sort_values(by='화재유형', ascending=False)
daegu_building_fire_by_gu = daegu_building_fire_by_gu.reset_index()
daegu_building_fire_by_gu.rename(columns={'화재유형': '화재건수'}, inplace=True)


daegu_population_df = pd.read_csv("../Data/동별인구.csv")
new_daegu_population_df = daegu_population_df[['군·구','등록인구 (명)','인구밀도 (명/㎢)','면적 (㎢)']]
new_by_gu = new_daegu_population_df.groupby('군·구').agg({
    '등록인구 (명)': 'sum',
    '인구밀도 (명/㎢)': 'mean',
    '면적 (㎢)': 'sum'
})
new_by_gu = new_by_gu.reset_index().rename(columns={'군·구': '시군구'})
new_by_gu

# 병합
merged = pd.merge(daegu_building_fire_by_gu,new_by_gu , how='left', on='시군구')
merged['화재건수/등록인구 (명)'] = merged['화재건수']/merged['등록인구 (명)'] * 100
merged['화재건수/인구밀도 (명/㎢)'] = merged['화재건수']/merged['인구밀도 (명/㎢)']
merged['화재건수/면적 (㎢)'] = merged['화재건수']/merged['면적 (㎢)']


merged =merged.sort_values(by='화재건수/인구밀도 (명/㎢)', ascending=False)
merged


#  인구밀도 대비 화재건수 발생 비율
si_list = merged['시군구']
values = merged['화재건수/인구밀도 (명/㎢)']

x = np.arange(len(si_list))
bar_width = 0.25

# 색상 지정: 군위군, 달성군 진하게, 나머지 연하게
colors = ['#AAAAAA'] * len(si_list)  # 모든 시군구 연한 회색
for idx, name in enumerate(si_list):
    if name in ['군위군', '달성군']:
        colors[idx] = '#1976D2'  # 진한 파란색 (원하는 색으로 변경 가능)

plt.figure(figsize=(14, 6))
bars = plt.bar(x, values, color=colors, width=bar_width, label='비율')

plt.xlabel('시군구')
plt.ylabel('화재건수/인구밀도 (명/㎢)')
plt.title('시군구별 인구밀도 대비 화재건수 비율 시각화')
plt.xticks(x, si_list, rotation=45)
plt.tight_layout()

# 막대 위에 숫자 표기
for bar in bars:
    height = bar.get_height()
    plt.annotate(f'{height:.3f}',
                 xy=(bar.get_x() + bar.get_width() / 2, height),
                 xytext=(0, 3), # 막대 위로 3pt 이동
                 textcoords="offset points",
                 ha='center', va='bottom', fontsize=10, color='black')

plt.show()


fire_df = pd.read_csv("../Raw Data/소방청_화재발생 정보.csv", encoding='cp949')
daegu_building_df = pd.read_csv("../Data/건축물대장_v0.5.csv")

# 전국 단위 (대구광역시 데이터 빼고) 
kor_fire_count = fire_df.groupby('시도')[['화재유형']].count()
kor_fire_count = kor_fire_count.reset_index()
kor_fire_count

kor_fire_count = kor_fire_count[kor_fire_count['시도'] != '대구광역시']
kor_fire_count = kor_fire_count.reset_index(drop=True)
result = kor_fire_count['화재유형'].sum() / len(g1)
# print(round(result))

# 대구  화재 데이터 추출
cond1 = (fire_df['시도'] == '대구광역시')
daegu_fire_df = fire_df[cond1]
daegu_fire_df = daegu_fire_df[['화재발생년원일','시군구','화재유형','발화요인소분류','인명피해(명)소계','재산피해소계']]
daegu_fire_df['화재발생년원일'] = pd.to_datetime(daegu_fire_df['화재발생년원일'])
# daegu_fire_df = daegu_fire_df[daegu_fire_df['화재유형'] == '건축,구조물']
# daegu_fire_df.info()


# 대구광역시 건물수 추출
daegu_building_df['시군구'] = daegu_building_df['대지위치'].str.split().str[1]
buildings_counts = daegu_building_df.groupby('시군구')[['기타구조']].count()
buildings_counts = buildings_counts.rename(columns={'기타구조': '건물수'})
buildings_counts = buildings_counts.sort_values(by='건물수', ascending=False).reset_index()
buildings_counts

# 대구광역시 화재정보 & 건물 수 데이터프레임 merge
merged_df = pd.merge(buildings_counts, daegu_fire_by_gu, on='시군구')
merged_df['화재건수/건물수'] = merged_df['화재건수'] / merged_df['건물수'] * 1000
merged_df = merged_df.sort_values(by='화재건수/건물수', ascending=False).reset_index(drop=True)
merged_df

# 건물 밀집 : 건물 수 / 면적
population_df = pd.read_csv("C:\\Users\\USER\\Desktop\\대구\\Daegu-Risk-Zones\\Data\\동별인구.csv")
population_df.columns
new_population = population_df[['군·구', '동·읍·면','면적 (㎢)']]
# new_population
area_by_gu = new_population.groupby('군·구')[['면적 (㎢)']].sum().reset_index()
# area_by_gu
area_by_gu = area_by_gu.rename(columns={'군·구': '시군구'})
area_by_gu

merged_df = pd.merge(area_by_gu, merged_df, on='시군구')
# merged_df['화재건수/건물수'] = merged_df['화재건수'] / merged_df['건물수'] * 1000
# merged_df = merged_df.sort_values(by='화재건수/건물수', ascending=False).reset_index(drop=True)


# 시군구별 화재건수/건물 수 비율 
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib import font_manager, rc
# 한글 폰트 설정 (Windows 예시)
font_path = "C:/Windows/Fonts/malgun.ttf"  # 맑은 고딕 폰트 경로
font_name = font_manager.FontProperties(fname=font_path).get_name()
rc('font', family=font_name)

# 값 기준으로 내림차순 정렬
merged_df = merged_df.sort_values(by='화재건수/건물수', ascending=False).reset_index(drop=True)

# 색상 리스트 만들기: 상위 3개 진한 초록, 나머진 연한 초록
colors = ['#006400' if i < 3 else '#90ee90' for i in range(len(merged_df))]

plt.figure(figsize=(10, 6))
sns.barplot(x='시군구', y='화재건수/건물수', data=merged_df, palette=colors)
plt.xlabel('시군구')
plt.ylabel('화재건수/건물수')
plt.title('시군구별 화재건수/건물수 비율 (상위 3개 강조)')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()


# 건물 밀집도 계산
merged_df['건물밀집도'] = merged_df['건물수'] / merged_df['면적 (㎢)']
merged_df

# 화재건수 / 건물 밀집도 계산
merged_df['화재건수/건물밀집도'] = merged_df['화재건수'] / merged_df['건물밀집도']
merged_df = merged_df.sort_values(by='화재건수/건물밀집도', ascending=False)
merged_df

merged_df = merged_df.sort_values(by='화재건수/건물밀집도', ascending=False).reset_index(drop=True)


# 대구광역시 군구별 화재건수/건물밀집도 비율
# 색상 리스트 만들기: 상위 3개 진한 초록, 나머진 연한 초록
colors = ['#006400' if i < 3 else '#90ee90' for i in range(len(merged_df))]

plt.figure(figsize=(10, 6))
sns.barplot(x='시군구', y='화재건수/건물밀집도', data=merged_df, palette=colors)
plt.xlabel('시군구')
plt.ylabel('화재건수/건물밀집도')
plt.title('시군구별 화재건수/건물밀집도 비율 (상위 3개 강조)')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()