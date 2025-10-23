import pandas as pd
import numpy as np
import plotly.express as px
from scipy.stats import pearsonr, spearmanr

# 데이터 불러오기
df_population = pd.read_csv("../Data/동별인구.csv")
df_population_filter = df_population[['군·구', '동·읍·면', '고령자_비율','위도','경도']]

df_building = pd.read_csv("../Data/건축물대장_v0.5.csv")

# ==============================
# 2) 동별 고령자 평균비율
# ==============================
df_pop = (
    df_population_filter
    .groupby(['군·구','동·읍·면'], as_index=False)['고령자_비율'].mean()
    .rename(columns={'고령자_비율':'고령자_평균비율'})
)

# 행정동명 표준화(예외 처리)
df_pop['행정동명'] = df_pop['동·읍·면'].replace({'불로봉무동':'불로·봉무동'})

# ==============================
# 3) 행정동별 건물수
# ==============================
df_bld = (
    df_building
    .groupby('ADM_DR_NM', as_index=False)['건물노후도점수'].size()
    .rename(columns={'size':'건물수'})
)

# ==============================
# 4) 병합
# ==============================
df_m = (
    df_pop
    .assign(ADM_DR_NM=df_pop['행정동명'])
    .merge(df_bld, on='ADM_DR_NM', how='inner')
)

# 고령자 비율 퍼센트로 변환
if df_m['고령자_평균비율'].max() <= 1.0:
    df_m['고령자_평균비율(%)'] = df_m['고령자_평균비율'] * 100
else:
    df_m['고령자_평균비율(%)'] = df_m['고령자_평균비율']

# ==============================
# 5) 구/군별 상관계수 계산 함수
# ==============================
def safe_corr(x, y, method='pearson'):
    x = pd.Series(x).astype(float)
    y = pd.Series(y).astype(float)
    mask = x.notna() & y.notna() & np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < 3 or x.nunique() < 2 or y.nunique() < 2:
        return np.nan, np.nan, len(x)
    if method == 'pearson':
        r, p = pearsonr(x, y)
    else:
        r, p = spearmanr(x, y)
    return r, p, len(x)

rows = []
for gugu, g in df_m.groupby('군·구', dropna=False):
    r_p, p_p, n_p = safe_corr(g['건물수'], g['고령자_평균비율(%)'], 'pearson')
    r_s, p_s, n_s = safe_corr(g['건물수'], g['고령자_평균비율(%)'], 'spearman')
    rows.append({
        '군·구': gugu,
        'n': int(n_p),
        'pearson_r': r_p,
        'pearson_p': p_p,
        'spearman_rho': r_s,
        'spearman_p': p_s
    })

corr_df = pd.DataFrame(rows)

# ==============================
# 6) 피어슨 상관계수 시각화
# ==============================
corr_df_plot = corr_df.sort_values('pearson_r', na_position='last')

fig_corr_p = px.bar(
    corr_df_plot,
    x='pearson_r',
    y='군·구',
    orientation='h',
    color='pearson_r',
    color_continuous_scale='RdBu',
    range_color=(-1, 1),
    labels={'pearson_r': '피어슨 상관계수 r', '군·구': '구/군'},
    title='구/군별 상관계수 (피어슨) — 고령인구 비율 vs 건물수'
)
fig_corr_p.add_vline(x=0, line_width=1, line_dash='dash', line_color='gray')
fig_corr_p.update_layout(margin=dict(l=80, r=30, t=60, b=40))
fig_corr_p.show()

# ==============================
# 7) 스피어만 상관계수 시각화
# ==============================
corr_df_plot_s = corr_df.sort_values('spearman_rho', na_position='last')

fig_corr_s = px.bar(
    corr_df_plot_s,
    x='spearman_rho',
    y='군·구',
    orientation='h',
    color='spearman_rho',
    color_continuous_scale='RdBu',
    range_color=(-1, 1),
    labels={'spearman_rho': '스피어만 순위상관 ρ', '군·구': '구/군'},
    title='구/군별 상관계수 (스피어만) — 고령인구 비율 vs 건물수'
)
fig_corr_s.add_vline(x=0, line_width=1, line_dash='dash', line_color='gray')
fig_corr_s.update_layout(margin=dict(l=80, r=30, t=60, b=40))
fig_corr_s.show()

# ==============================
# 8) 요약 테이블 출력
# ==============================
print(corr_df[['군·구','n','pearson_r','pearson_p','spearman_rho','spearman_p']].round(4).to_string(index=False))

