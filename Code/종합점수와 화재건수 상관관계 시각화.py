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