# app/modules/tab_notes2.py
from shiny import ui, reactive, render
from shinywidgets import output_widget, render_widget
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from pathlib import Path

# ---------------- Paths ----------------
BASE = Path(__file__).resolve().parents[2]
FIRE_CSV   = BASE / "Raw Data/소방청_화재발생 정보.csv"
POP_CSV    = BASE / "Data/대구광역시_동별인구.csv"
BLDG_CSV   = BASE / "Data/건축물대장_v0.5.csv"
HYDRANT_CSV= BASE / "Data/대구광역시_용수시설_위치.csv"
FIRESTN_CSV= BASE / "Data/대구광역시_소방서_위치.csv"

# ---------------- Utils ----------------
def _read_csv_safe(path: Path, encs=("cp949","utf-8","utf-8-sig")):
    for enc in encs:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    # 마지막 시도: 인코딩 없이
    return pd.read_csv(path)

def _ylim_pad(ax, pad=0.15):
    # 현재 y max에 일정 비율 패딩
    ymin, ymax = ax.get_ylim()
    ymax_new = ymax if ymax > 0 else 1.0
    ax.set_ylim(0, ymax_new * (1 + pad))

# 거리 계산(하버사인) - 브로드캐스팅/청크 처리로 메모리 절약
def _nearest_distance_batch(lat_deg, lon_deg, ref_lat_deg, ref_lon_deg, chunk=2000):
    R = 6371000.0  # meters
    lat_rad = np.radians(lat_deg)
    lon_rad = np.radians(lon_deg)
    ref_lat = np.radians(ref_lat_deg).reshape(1, -1)   # (1, M)
    ref_lon = np.radians(ref_lon_deg).reshape(1, -1)
    N = len(lat_rad)
    out = np.full(N, np.nan, dtype=float)

    for i in range(0, N, chunk):
        j = min(i + chunk, N)
        la = lat_rad[i:j].reshape(-1, 1)               # (k,1)
        lo = lon_rad[i:j].reshape(-1, 1)
        dlat = ref_lat - la
        dlon = ref_lon - lo
        a = np.sin(dlat/2.0)**2 + np.cos(la) * np.cos(ref_lat) * np.sin(dlon/2.0)**2
        c = 2.0 * np.arcsin(np.sqrt(a))
        dist = R * c                                    # (k, M)
        out[i:j] = np.min(dist, axis=1)
    return out

# ---------------- Load data ----------------
fire_df = _read_csv_safe(FIRE_CSV)
pop_df  = _read_csv_safe(POP_CSV)
bldg_df = _read_csv_safe(BLDG_CSV)

# 한글 폰트(윈도우)
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

# 공통 전처리
# 1) 화재 유형 건수
cond_daegu = (fire_df["시도"] == "대구광역시")
df_fire = fire_df.loc[cond_daegu, ["화재발생년원일","시군구","화재유형","발화요인소분류","인명피해(명)소계","재산피해소계"]].copy()
df_fire["화재발생년원일"] = pd.to_datetime(df_fire["화재발생년원일"], errors="coerce")

fire_by_type = (
    df_fire.groupby("화재유형")[["시군구"]].count().rename(columns={"시군구":"화재건수"})
    .sort_values("화재건수", ascending=False).reset_index()
)

# 2) ‘건축,구조물’만 필터 → 군구별 건수
fire_building = df_fire[df_fire["화재유형"] == "건축,구조물"].copy()
fire_by_gu = (
    fire_building.groupby("시군구")[["화재유형"]].count()
    .rename(columns={"화재유형":"화재건수"})
    .sort_values("화재건수", ascending=False).reset_index()
)

# 3) 건물 수(군구)
#    - 주소에서 시군구 파싱(간단 규칙)
bldg_df["시군구"] = (
    bldg_df.get("대지위치","").astype(str).str.split().str[1]
    if "대지위치" in bldg_df.columns else np.nan
)
bldg_counts = (
    bldg_df.groupby("시군구")[["기타구조"]].count()
    .rename(columns={"기타구조":"건물수"}).sort_values("건물수", ascending=False).reset_index()
)

# 4) 면적(㎢) → 건물밀집도
area_by_gu = (
    pop_df.rename(columns={"군·구":"시군구"})
          .groupby("시군구")[["면적 (㎢)"]].sum().reset_index()
)

merged_bd = pd.merge(bldg_counts, fire_by_gu, on="시군구", how="inner")
merged_bd = pd.merge(area_by_gu, merged_bd, on="시군구", how="inner")
merged_bd["건물밀집도"] = merged_bd["건물수"] / merged_bd["면적 (㎢)"]
merged_bd["화재건수/건물밀집도"] = merged_bd["화재건수"] / merged_bd["건물밀집도"]
merged_bd = merged_bd.sort_values("화재건수/건물밀집도", ascending=False).reset_index(drop=True)

# ---------------- UI ----------------
def panel():
    return ui.nav_panel(
        "부록2",
        ui.layout_column_wrap(
            1,
            ui.card(
                ui.card_header("대구광역시 화재 유형별 건수"),
                ui.output_plot("plt_fire_types")
            ),
            ui.card(
                ui.card_header("군구별 인구밀도 대비 화재건수 비율"),
                ui.output_plot("plt_ratio_density")
            ),
            ui.card(
                ui.card_header("군구별 ‘화재건수 대비 건물밀집도’ 비율"),
                ui.output_plot("plt_ratio_building_density")
            ),
            ui.card(
                ui.card_header("가장 가까운 소방서/소방용수시설 거리 분포"),
                ui.layout_columns(
                    output_widget("hist_station_dist"),
                    output_widget("hist_hydrant_dist"),
                    col_widths=[6,6]
                )
            ),
            gap="1.0rem"
        )
    )

# ---------------- Server ----------------
def server(input, output, session):
    # 1) 화재 유형별 건수 (막대, ‘건축,구조물’만 진하게)
    @render.plot
    def plt_fire_types():
        x = fire_by_type["화재유형"].values
        y = fire_by_type["화재건수"].values
        colors = ["#C62828" if t == "건축,구조물" else "#D3D3D3" for t in x]

        fig, ax = plt.subplots(figsize=(10,6))
        bars = ax.bar(x, y, color=colors, edgecolor="black")
        ax.set_title("대구광역시 화재 유형별 건수", fontsize=18, fontweight="bold")
        ax.set_xlabel("화재 유형", fontsize=14, fontweight="bold")
        ax.set_ylabel("화재 건수", fontsize=14, fontweight="bold")
        ax.set_xticks(range(len(x)))
        ax.set_xticklabels(x, rotation=0, fontsize=13)
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v,_: f"{int(v):,}"))

        # y축 상단 패딩
        _ylim_pad(ax, pad=0.15)

        # 라벨
        for b in bars:
            h = b.get_height()
            ax.text(b.get_x() + b.get_width()/2, h * 1.02, f"{int(h):,}",
                    ha="center", va="bottom", fontsize=12)
        fig.tight_layout()
        return fig

    # 2) 인구밀도 대비 화재건수 비율 (상위 2개 빨강)
    @render.plot
    def plt_ratio_density():
        # 원자료: fire_by_gu + 인구밀도(평균) 필요 → 기존 “부록1”에서 쓰던 로직이 있었다면 재사용 가능
        # 여기서는 인구밀도 열이 없을 수 있어, 있으면 사용/없으면 스킵 처리
        # (요청은 y축 패딩이 핵심이므로 값 존재 전제)
        # 예시로 면적/인구 파일에 "인구밀도 (명/㎢)"가 있다고 가정:
        if "인구밀도 (명/㎢)" in pop_df.columns:
            dens = (pop_df.rename(columns={"군·구":"시군구"})
                         .groupby("시군구")[["인구밀도 (명/㎢)"]].mean().reset_index())
            m = pd.merge(fire_by_gu, dens, on="시군구", how="left").dropna()
            m["화재건수/인구밀도 (명/㎢)"] = m["화재건수"] / m["인구밀도 (명/㎢)"]
            m = m.sort_values("화재건수/인구밀도 (명/㎢)", ascending=False).reset_index(drop=True)
            x = m["시군구"].values
            y = m["화재건수/인구밀도 (명/㎢)"].values
        else:
            # 인구밀도 데이터가 없다면 빈 그래프 반환
            fig, ax = plt.subplots(figsize=(10,3))
            ax.text(0.5, 0.5, "인구밀도 데이터가 없습니다.", ha="center", va="center")
            ax.axis("off")
            return fig

        colors = ["#d62728" if i in (0,1) else "#D3D3D3" for i in range(len(y))]

        fig, ax = plt.subplots(figsize=(10,6))
        bars = ax.bar(x, y, color=colors, edgecolor="black")
        for b in bars:
            h = b.get_height()
            ax.text(b.get_x()+b.get_width()/2, h*1.02, f"{h:.3f}", ha="center", va="bottom", fontsize=10)
        ax.set_title("대구광역시 군구별 인구밀도 대비 화재건수 비율", fontsize=18, fontweight="bold")
        ax.set_xlabel("시군구", fontsize=14, fontweight="bold")
        ax.set_ylabel("화재건수 / 인구밀도 (명/㎢)", fontsize=14, fontweight="bold")
        ax.set_xticklabels(x, rotation=0, fontsize=12)

        _ylim_pad(ax, pad=0.20)  # 조금 더 여유
        fig.tight_layout()
        return fig

    # 3) 화재건수 대비 건물밀집도 비율 (1등 빨강)
    @render.plot
    def plt_ratio_building_density():
        x = merged_bd["시군구"].values
        y = merged_bd["화재건수/건물밀집도"].values
        top_idx = int(np.argmax(y)) if len(y) else -1
        colors = ["#C62828" if i == top_idx else "#D3D3D3" for i in range(len(y))]

        fig, ax = plt.subplots(figsize=(10,6))
        bars = ax.bar(x, y, color=colors, edgecolor="black")
        for b in bars:
            h = b.get_height()
            ax.text(b.get_x()+b.get_width()/2, h*1.02, f"{h:.2f}", ha="center", va="bottom", fontsize=11)
        ax.set_xlabel("시군구", fontsize=16, fontweight="bold")
        ax.set_ylabel("화재건수 / 건물밀집도", fontsize=16, fontweight="bold")
        ax.set_title("대구광역시 구별 화재건수 대비 건물밀집도 비율", fontsize=20, fontweight="bold")
        ax.set_xticklabels(x, rotation=0, fontsize=14)
        ax.tick_params(axis="y", labelsize=14)

        _ylim_pad(ax, pad=0.18)
        fig.tight_layout()
        return fig

    # -------- Plotly: 최단거리 분포 2종 --------
    # 미리 데이터 준비(유효 좌표만)
    def _valid_latlon(df, lat_col="위도", lon_col="경도"):
        if lat_col not in df.columns or lon_col not in df.columns:
            return df.assign(**{lat_col: np.nan, lon_col: np.nan})
        out = df.copy()
        out[lat_col] = pd.to_numeric(out[lat_col], errors="coerce")
        out[lon_col] = pd.to_numeric(out[lon_col], errors="coerce")
        out = out.dropna(subset=[lat_col, lon_col])
        out = out[(out[lat_col].between(30,45)) & (out[lon_col].between(120,135))]
        return out

    hyd_df = _read_csv_safe(HYDRANT_CSV)
    stn_df = _read_csv_safe(FIRESTN_CSV)
    bldg_xy = _valid_latlon(bldg_df, "위도", "경도")
    hyd_xy  = _valid_latlon(hyd_df,  "위도", "경도")
    stn_xy  = _valid_latlon(stn_df,  "위도", "경도")

    # 거리가 이미 계산되어 있지 않다면 계산
    if "소방용수시설거리" not in bldg_xy.columns or bldg_xy["소방용수시설거리"].isna().all():
        if not hyd_xy.empty:
            bldg_xy["소방용수시설거리"] = _nearest_distance_batch(
                bldg_xy["위도"].to_numpy(), bldg_xy["경도"].to_numpy(),
                hyd_xy["위도"].to_numpy(),  hyd_xy["경도"].to_numpy(),
                chunk=1500
            )
    if "소방서거리" not in bldg_xy.columns or bldg_xy["소방서거리"].isna().all():
        if not stn_xy.empty:
            bldg_xy["소방서거리"] = _nearest_distance_batch(
                bldg_xy["위도"].to_numpy(), bldg_xy["경도"].to_numpy(),
                stn_xy["위도"].to_numpy(),  stn_xy["경도"].to_numpy(),
                chunk=1500
            )

    # NaN/무한 제거
    for c in ("소방서거리","소방용수시설거리"):
        if c in bldg_xy.columns:
            bldg_xy[c] = pd.to_numeric(bldg_xy[c], errors="coerce").replace([np.inf,-np.inf], np.nan)

    import plotly.express as px

    @render_widget
    def hist_station_dist():
        if "소방서거리" not in bldg_xy.columns or bldg_xy["소방서거리"].dropna().empty:
            import plotly.graph_objects as go
            return go.FigureWidget(go.Scatter(x=[], y=[], mode="markers", name="데이터 없음"))
        fig = px.histogram(
            bldg_xy.dropna(subset=["소방서거리"]),
            x="소방서거리", nbins=100, title="가장 가까운 소방서 거리 분포", marginal="box",
            template="plotly_white"
        )
        fig.update_layout(bargap=0.1, xaxis_title="거리(m)", yaxis_title="건물 수", margin=dict(l=10,r=10,t=40,b=10))
        return fig

    @render_widget
    def hist_hydrant_dist():
        if "소방용수시설거리" not in bldg_xy.columns or bldg_xy["소방용수시설거리"].dropna().empty:
            import plotly.graph_objects as go
            return go.FigureWidget(go.Scatter(x=[], y=[], mode="markers", name="데이터 없음"))
        fig = px.histogram(
            bldg_xy.dropna(subset=["소방용수시설거리"]),
            x="소방용수시설거리", nbins=100, title="가장 가까운 소방용수시설 거리 분포", marginal="box",
            template="plotly_white"
        )
        fig.update_layout(bargap=0.1, xaxis_title="거리(m)", yaxis_title="건물 수", margin=dict(l=10,r=10,t=40,b=10))
        return fig
