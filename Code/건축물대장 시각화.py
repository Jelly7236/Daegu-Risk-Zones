# %% 라이브러리 호출
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
# %% check
# columns_to_check = ['Column14', 'Column15', 'Column60', 'Column61', 'Column67']
# %% 구/군 별 데이터 로드
df1 = pd.read_csv('../Raw Data/건축물대장/건축물대장_대구광역시_군위군.csv')
df2 = pd.read_csv('../Raw Data/건축물대장/건축물대장_대구광역시_남구.csv')
df3 = pd.read_csv('../Raw Data/건축물대장/건축물대장_대구광역시_달서구.csv')
df4 = pd.read_csv('../Raw Data/건축물대장/건축물대장_대구광역시_달성군.csv')
df5 = pd.read_csv('../Raw Data/건축물대장/건축물대장_대구광역시_동구.csv')
df6 = pd.read_csv('../Raw Data/건축물대장/건축물대장_대구광역시_북구.csv')
df7 = pd.read_csv('../Raw Data/건축물대장/건축물대장_대구광역시_서구.csv')
df8 = pd.read_csv('../Raw Data/건축물대장/건축물대장_대구광역시_수성구.csv')
df9 = pd.read_csv('../Raw Data/건축물대장/건축물대장_대구광역시_중구.csv')

# %% 구/군 컬럼 추가
df1['군/구'] = '군위군'
df2['군/구'] = '남구'
df3['군/구'] = '달서구'
df4['군/구'] = '달성군'
df5['군/구'] = '동구'
df6['군/구'] = '북구'
df7['군/구'] = '서구'
df8['군/구'] = '수성구'
df9['군/구'] = '중구'
# %% 구/군 별 데이터 통합
df_all = pd.concat([df1, df2, df3, df4, df5, df6, df7, df8, df9], ignore_index=True)
# %% 구조 분류 딕셔너리 정의
structure_map = {
    '목조 계열': ['일반목구조', '목구조', '트러스목구조', '통나무구조'],
    '조적식 구조': ['석구조', '벽돌구조', '블록구조', '시멘트블럭조', '흙벽돌조', '조적구조', '기타조적구조'],
    '콘크리트 계열': ['철근콘크리트구조','콘크리트구조','프리케스트콘크리트구조','보강콘크리트조','기타콘크리트구조','라멘조'],
    '철골 계열': ['일반철골구조','경량철골구조','강파이프구조','철파이프조','기타강구조','스틸하우스조','단일형강구조','철골구조','공업화박판강구조(PEB)','트러스구조',
    '철골콘크리트구조','철골철근콘크리트구조','철골철근콘크리트합성구조','기타철골철근콘크리트구조'],
    '조립식·판넬·기타': ['조립식판넬조', '컨테이너조'],
    '기타 / 특수 구조': ['막구조', '기타구조']
}
# %% 구조 분류
def map_structure_type(name):
    for group, items in structure_map.items():
        if name in items:
            return group
    return '미분류'
df_all['구조그룹'] = df_all['구조코드명'].apply(map_structure_type)
# %% 건축 자재별 분포 시각화
structure_counts = df_all['구조그룹'].value_counts()

# 도넛차트 그리기
fig = go.Figure(data=[go.Pie(
    labels=structure_counts.index,
    values=structure_counts.values,
    hole=0.4,
    textinfo='percent+label',
    hoverinfo='label+value+percent',
    insidetextorientation='radial'
)])

fig.update_layout(
    title_text='건축 자재별 건물 분포',
    annotations=[dict(text='', x=0.5, y=0.5, font_size=18, showarrow=False)],
    showlegend=True
)

fig.show()
# %% 주용도 분류 딕셔너리 정의
building_use = {
    '숙박/다중이용시설': ['숙박시설', '야영장시설', '관광휴게시설'],
    '공장/창고시설': ['공장','창고시설'],
    '교육/복지/의료/수련': ['노유자시설', '교육연구시설', '교육연구및복지시설', '의료시설', '수련시설'],
    '상업/판매/문화/업무/근린/생활편익':
    ['제2종근린생활시설',
    '근린생활시설',
    '제1종근린생활시설',
    '종교시설',
    '문화및집회시설',
    '운동시설',
    '업무시설',
    '판매시설',
    '위락시설',
    '판매및영업시설',
    '기타제1종근린생활시설',
    '생활편익시설',
    '소매점'],
    '기반시설':
    ['동물및식물관련시설',
    '위험물저장및처리시설',
    '자원순환관련시설',
    '분뇨.쓰레기처리시설',
    '방송통신시설',
    '자동차관련시설',
    '장례시설',
    '운수시설',
    '교정및군사시설',
    '국방,군사시설',
    '발전시설',
    '묘지관련시설'],
    '주거':
    ['단독주택',
    '공동주택',
    '다가구주택'],
    '행정/공공':
    '공공용시설',
}
# %% 주용도 분류
def use_type(name):
    if not isinstance(name, str):
        return '미분류'

    for group, items in building_use.items():
        if name in items:
            return group
    return '미분류'
df_all['주용도그룹'] = df_all['주용도코드명'].apply(use_type)
# %% 용도별 분포 시각화
use_group_counts = df_all['주용도그룹'].value_counts()
use_group_ratio = use_group_counts / use_group_counts.sum()

# 2% 미만은 기타로 묶기
threshold = 0.02
labels = []
values = []
etc_total = 0

for label, ratio in use_group_ratio.items():
    if ratio >= threshold:
        labels.append(label)
        values.append(use_group_counts[label])
    else:
        etc_total += use_group_counts[label]

# 기타 항목 추가
if etc_total > 0:
    labels.append('기타')
    values.append(etc_total)

# 도넛 차트 생성
fig1 = go.Figure(data=[go.Pie(
    labels=labels,
    values=values,
    hole=0.3,  # 도넛 중앙 구멍 작게 = 도넛 자체 크게
    textinfo='percent+label',
    hoverinfo='label+value+percent',
    insidetextorientation='radial'
)])

# 레이아웃 조정
fig1.update_layout(
    title_text='주용도그룹 분포 (2% 미만 기타로 통합)',
    annotations=[dict(text='주용도', x=0.5, y=0.5, font_size=20, showarrow=False)],
    showlegend=True,
    height=600,  # 높이 늘려서 크게 보기
    width=700
)

fig1.show()
# %% 용도, 자재 교차 분석 시각화
cross_tab = pd.crosstab(df_all['주용도그룹'], df_all['구조그룹'])
fig2 = go.Figure()
for 구조 in cross_tab.columns:
    fig2.add_trace(go.Bar(
        x=cross_tab.index,
        y=cross_tab[구조],
        name=구조
    ))

# 레이아웃 설정
fig2.update_layout(
    barmode='stack',  # 스택형 막대
    title='주용도그룹 vs 구조그룹 분포 (스택형 막대 그래프)',
    xaxis_title='주용도그룹',
    yaxis_title='건물 수',
    legend_title='구조그룹',
    template='plotly_white'
)

fig2.show()
# %% 비상용 승강기 수 분포 시각화
cond_elevator = df_all['지상층수'] >= 5
emergency = df_all[cond_elevator]
# 결측치 0으로 대치
emergency['비상용승강기수'] = emergency['비상용승강기수'].fillna(0).astype(int)

# 5개 이상은 '5개 이상'으로 범주화
def categorize_elevators(x):
    return str(x) if x < 5 else '5개 이상'

emergency['비상용승강기_그룹'] = emergency['비상용승강기수'].apply(categorize_elevators)

# 그룹별 건물 수 집계
grouped = emergency['비상용승강기_그룹'].value_counts().sort_index().reset_index()
grouped.columns = ['비상용승강기수', '건물수']

# 파이차트 시각화 (파이 크기 크게 설정)
fig = px.pie(grouped,
             names='비상용승강기수',
             values='건물수',
             title='지상 5층 이상 건물의 비상용 승강기 수 분포',
             width=700, height=700,  # 파이 크기 조절
             color_discrete_sequence=px.colors.sequential.Magma)

# 퍼센트와 라벨 모두 표시
fig.update_traces(textinfo='percent+label',
                  textfont_size=16,
                  pull=[0.03]*len(grouped))  # 조각 약간 분리(선택)

fig.show()
# %% 사용승인일 이상값 탐색(보충 필요)
df_all['사용승인일_길이'] = df_all['사용승인일'].astype(str).str.len()
df_all['사용승인일_길이'].unique()
cond = df_all['사용승인일_길이'] == 9
df_all[cond]['사용승인일'].unique()
df_year = df_all.copy()
cond_y9 = df_year['사용승인일_길이'] == 9
df_year.loc[cond_y9, '사용승인일'] = '19' + df_year.loc[cond_y9, '사용승인일'].astype(str)
cond_y11 = df_year['사용승인일'] == '191979100.0'
df_year[cond_y11]
df_year.loc[cond_y11, '사용승인일'] = df_year.loc[cond_y11, '사용승인일'].str[2:]
df_year['사용승인일_길이'] = df_year['사용승인일'].astype(str).str.len()
cond_drop = df_year['사용승인일_길이'].isin([2, 3, 5])
df_year = df_year[~cond_drop]
df_year.loc[:, '사용승인일'] = df_year['사용승인일'].astype(str).str.strip()
# %% 사용승인일(년도) 추출
df_year.loc[:, '사용승인일(년도)'] = df_year['사용승인일'].astype(str).str[:4]
df_year['사용승인일(년도)'] = df_year['사용승인일(년도)'].astype(str).str.strip()
df_year['사용승인일(년도)'].replace('', pd.NA, inplace=True)
df_year['사용승인일(년도)'] = pd.to_numeric(df_year['사용승인일(년도)'], errors='coerce').astype('Int64')
# %% 승인연도 필터링, 연령 계산 
cleaned_year = df_year.dropna(subset='사용승인일(년도)')
filltered_year = cleaned_year[cleaned_year['사용승인일(년도)'] >= 1800]
filltered_year['연령'] = 2025 - filltered_year['사용승인일(년도)']
# %% 건축물 연령 분포 시각화
bins = list(range(0, 101, 10)) + [float('inf')]
labels = [f"{i}~{i+10}년" for i in range(0, 100, 10)] + ["100년 이상"]

filltered_year['연령대'] = pd.cut(filltered_year['연령'], bins=bins, labels=labels, right=False)
# 연령대별 건물 수 집계
age_group_counts = filltered_year['연령대'].value_counts().sort_index()
# Plotly로 막대 그래프 시각화

fig5 = px.bar(
    x=age_group_counts.index,
    y=age_group_counts.values,
    labels={'x': '연령대', 'y': '건물 수'},
    title='노후화 구간별 건물 수 분포 (10년 단위)',
    text=age_group_counts.values,
    color=age_group_counts.values,
    color_continuous_scale='Viridis'
)

fig5.update_layout(
    xaxis_title="노후화 구간",
    yaxis_title="건물 수",
    uniformtext_minsize=8,
    uniformtext_mode='hide',
    bargap=0.3
)

fig5.show()
# %% 40년 이상은 한 범주로 처리한 것
bins = [0, 10, 20, 30, 40, float('inf')]
labels = ['0~10년', '10~20년', '20~30년', '30~40년', '40년 이상']

# 2. 구간화
filltered_year['연령대'] = pd.cut(filltered_year['연령'], bins=bins, labels=labels, right=False)

# 3. 집계
age_group_counts = filltered_year['연령대'].value_counts(sort=False)

# 4. 시각화
fig6 = px.bar(
    x=age_group_counts.index,
    y=age_group_counts.values,
    labels={'x': '연령대', 'y': '건물 수'},
    title='노후화 구간별 건물 수 분포 (40년 이상 묶음)',
    text=age_group_counts.values,
    color=age_group_counts.values,
    color_continuous_scale='Viridis'
)

fig6.update_layout(
    xaxis_title="노후화 구간",
    yaxis_title="건물 수",
    uniformtext_minsize=8,
    uniformtext_mode='hide',
    bargap=0.3
)

fig6.show()
# %% 용도, 노후화 교차
bins = [0, 10, 20, 30, 40, float('inf')]
labels = ['0~10년', '10~20년', '20~30년', '30~40년', '40년 이상']
filltered_year['연령대'] = pd.cut(filltered_year['연령'], bins=bins, labels=labels, right=False)

# 2. 교차표 생성: 주용도그룹 × 연령대
cross_tab = pd.crosstab(filltered_year['주용도그룹'], filltered_year['연령대'])

# 3. Plotly로 교차 막대그래프 (그룹별 스택)
fig7 = px.bar(
    cross_tab,
    x=cross_tab.index,
    y=cross_tab.columns,
    labels={'value': '건물 수', '주용도그룹': '주용도 그룹', '연령대': '연령대'},
    title='주용도 그룹별 연령대별 건물 수',
    barmode='stack'  # 누적 막대
)

fig7.update_layout(
    xaxis_title='주용도 그룹',
    yaxis_title='건물 수',
    legend_title='연령대',
    bargap=0.2
)

fig7.show()
# %%
