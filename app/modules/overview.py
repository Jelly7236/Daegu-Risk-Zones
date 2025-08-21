# app/modules/overview.py
from shiny import ui, render
from shinywidgets import output_widget, render_widget
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# =========================
# 경로: app/modules 기준 → project 루트
BASE_DIR = Path(__file__).resolve().parents[2]  # project/
FIRE_CSV_PATH = BASE_DIR / "Raw Data" / "소방청_화재발생 정보.csv"
POP_CSV_PATH  = BASE_DIR / "Data" / "동별인구.csv"
# =========================

# ===== (A) 전국/대구 라인 그래프용 데모 데이터 (원하면 실제로 교체) =====
df_nat_year = pd.DataFrame({
    "연도":[2021,2021,2021,2022,2022,2022,2023,2023,2023,2024,2024,2024],
    "광역":["대구","서울","부산"]*4,
    "화재건수":[1200,2100,1500,1100,2000,1400,1150,2050,1450,1300,2200,1520],
})

# ===== (B) 실제 CSV 로딩 (대구 전체 기간 기준) =====
def _safe_read_csv(path: Path, **kwargs):
    try:
        return pd.read_csv(path, **kwargs)
    except UnicodeDecodeError:
        enc = kwargs.pop("encoding", None)
        alt = "cp949" if enc != "cp949" else "utf-8-sig"
        return pd.read_csv(path, encoding=alt, **kwargs)

_daegu_fire_all = None
_daegu_pop_by_gu = None
try:
    if FIRE_CSV_PATH.exists():
        fire_df = _safe_read_csv(FIRE_CSV_PATH, encoding="cp949")
        cond = (fire_df["시도"] == "대구광역시")
        daegu = fire_df.loc[
            cond,
            ["화재발생년원일","시군구","화재유형","발화요인소분류","인명피해(명)소계","재산피해소계"]
        ].copy()
        # 날짜 → 연도 (필요 시 다른 그래프에서 쓸 수 있도록 보존)
        daegu["화재발생년원일"] = pd.to_datetime(daegu["화재발생년원일"], errors="coerce")
        daegu["연도"] = daegu["화재발생년원일"].dt.year
        _daegu_fire_all = daegu.dropna(subset=["시군구", "화재유형"]).copy()

    if POP_CSV_PATH.exists():
        pop_df = _safe_read_csv(POP_CSV_PATH)
        pop_slim = pop_df[["군·구","등록인구 (명)","인구밀도 (명/㎢)","면적 (㎢)"]].copy()
        _daegu_pop_by_gu = (
            pop_slim.groupby("군·구")
                    .agg({"등록인구 (명)":"sum","인구밀도 (명/㎢)":"mean","면적 (㎢)":"sum"})
                    .reset_index()
                    .rename(columns={"군·구":"시군구"})
        )
except Exception as e:
    print(f"[overview] CSV 로딩 실패: {e}")

# ===== (C) 한글 폰트(가능하면 적용) =====
def _ensure_korean_font():
    try:
        import matplotlib
        for font_name in ["Malgun Gothic", "AppleGothic", "Noto Sans CJK KR", "Noto Sans KR"]:
            if font_name in {f.name for f in matplotlib.font_manager.fontManager.ttflist}:
                plt.rc("font", family=font_name); break
        plt.rcParams["axes.unicode_minus"] = False
    except Exception:
        pass

# ===== UI (연도 사이드바 제거) =====
def panel():
    return ui.nav_panel(
        "대구광역시 화재 현황",
        ui.layout_columns(
            # 1. 전국 평균(광역) vs 대구 (연도 전체 라인)
            ui.card(
                ui.card_header("전국 평균(광역) vs 대구 화재 건수"),
                ui.p("전국 평균은 각 연도의 광역시·도 평균"),
                output_widget("fig_nat_vs_daegu"),
            ),
            # 2. 대구 유형별 화재 건수 (전체 기간 합계)
            ui.card(
                ui.card_header("대구 유형별 화재 건수 (전체 기간)"),
                ui.output_plot("fig_daegu_type", height="380px"),
            ),
            # 3. 군·구별 인구 밀도 대비 화재건수 비율 (전체 기간)
            ui.card(
                ui.card_header("군·구별 인구 밀도 대비 화재건수 비율 (전체 기간)"),
                ui.p("대상: 화재유형=건축,구조물 / 값: 화재건수 ÷ 인구밀도"),
                ui.output_plot("fig_density_vs_fires_ratio", height="440px"),
            ),
            # 4. 군·구별 건물 수 대비 화재 비율 (데모)
            ui.card(
                ui.card_header("군·구별 건물 수 대비 화재 비율 (데모)"),
                ui.p("건물 1만동당 화재, 내림차순 정렬"),
                output_widget("fig_building_ratio"),
            ),
            col_widths=[6,6,12,12],
        )
    )

# ===== Server =====
def server(input, output, session):
    # --- (1) 전국 평균 vs 대구 (Plotly 라인; 데모 데이터)
    @render_widget
    def fig_nat_vs_daegu():
        d = df_nat_year.copy()
        nat = d.groupby("연도", as_index=False)["화재건수"].mean().rename(columns={"화재건수":"전국평균"})
        dg = d[d["광역"]=="대구"][["연도","화재건수"]].rename(columns={"화재건수":"대구"})
        m = pd.merge(nat, dg, on="연도", how="left")
        fig = px.line(m, x="연도", y=["전국평균","대구"], markers=True,
                      title="전국 평균(광역) vs 대구 화재 건수(연도별)")
        fig.update_layout(margin=dict(l=0,r=0,t=50,b=0))
        return fig

    # --- (2) 대구 유형별 화재 건수 (Matplotlib, 전체 기간 합계)
    @render.plot
    def fig_daegu_type():
        _ensure_korean_font()
        if _daegu_fire_all is None or _daegu_fire_all.empty:
            fig, ax = plt.subplots(figsize=(8,4)); ax.set_title("데이터 없음"); return fig

        g = (_daegu_fire_all.groupby("화재유형")[["시군구"]]
                           .count()
                           .sort_values(by="시군구", ascending=False)
                           .reset_index()
                           .rename(columns={"시군구":"화재건수"}))
        colors = ["#C62828" if x == "건축,구조물" else "#FFCDD2" for x in g["화재유형"]]

        fig, ax = plt.subplots(figsize=(8,6))
        bars = ax.bar(g["화재유형"], g["화재건수"], color=colors)
        ax.set_title("대구 화재 유형별 건수 (전체 기간)")
        ax.set_xlabel("화재 유형"); ax.set_ylabel("화재 건수")
        y_max = g["화재건수"].max(); ax.set_ylim(0, y_max * 1.15)
        for i, v in enumerate(g["화재건수"]):
            ax.text(i, v + y_max*0.03, str(int(v)), ha="center", va="bottom")
        fig.subplots_adjust(bottom=0.18)
        return fig

    # --- (3) 군·구별 인구 밀도 대비 화재건수 비율 (Matplotlib, 전체 기간)
    @render.plot
    def fig_density_vs_fires_ratio():
        _ensure_korean_font()
        if _daegu_fire_all is None or _daegu_fire_all.empty or _daegu_pop_by_gu is None:
            fig, ax = plt.subplots(figsize=(10,4)); ax.set_title("데이터 없음(화재/인구)"); return fig

        d_building = _daegu_fire_all[_daegu_fire_all["화재유형"] == "건축,구조물"].copy()
        fire_by_gu = (d_building.groupby("시군구")[["화재유형"]]
                                .count()
                                .reset_index()
                                .rename(columns={"화재유형":"화재건수"}))
        merged = pd.merge(fire_by_gu, _daegu_pop_by_gu, how="left", on="시군구")

        for c in ["등록인구 (명)", "인구밀도 (명/㎢)", "면적 (㎢)"]:
            merged[c] = merged[c].fillna(0)

        with np.errstate(divide="ignore", invalid="ignore"):
            merged["화재건수/인구밀도 (명/㎢)"] = np.where(
                merged["인구밀도 (명/㎢)"] > 0, merged["화재건수"]/merged["인구밀도 (명/㎢)"], 0.0
            )

        merged = merged.sort_values("화재건수/인구밀도 (명/㎢)", ascending=False)

        si_list = merged["시군구"].tolist()
        values  = merged["화재건수/인구밀도 (명/㎢)"].tolist()
        x = np.arange(len(si_list)); bar_width = 0.25

        colors = ["#AAAAAA"] * len(si_list)
        for idx, name in enumerate(si_list):
            if name in ["군위군", "달성군"]:
                colors[idx] = "#1976D2"

        fig, ax = plt.subplots(figsize=(14,6))
        bars = ax.bar(x, values, color=colors, width=bar_width, label="비율")
        ax.set_xlabel("시군구")
        ax.set_ylabel("화재건수/인구밀도 (명/㎢)")
        ax.set_title("시군구별 인구밀도 대비 화재건수 비율 (전체 기간)")
        ax.set_xticks(x); ax.set_xticklabels(si_list, rotation=45, ha="right")
        y_max = max(values) if values else 1; ax.set_ylim(0, y_max * 1.15)
        for bar in bars:
            h = bar.get_height()
            ax.annotate(f"{h:.3f}", xy=(bar.get_x()+bar.get_width()/2, h),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=10)
        fig.subplots_adjust(bottom=0.18)
        return fig

    # --- (4) 군·구별 건물 수 대비 화재 비율 (Plotly 데모)
    @render_widget
    def fig_building_ratio():
        # 데모 데이터 유지(원하면 실제 건물수 데이터로 교체)
        df = pd.DataFrame({
            "군·구":["중구","동구","서구","남구","북구","수성구","달서구","달성군"],
            "건물수":[19000,86000,43000,35000,110000,100000,145000,70000],
            "화재건수":[210,430,270,190,520,480,640,260],
        })
        df["건물1만동당_화재"] = df["화재건수"] / df["건물수"] * 10000.0
        df = df.sort_values("건물1만동당_화재", ascending=False)
        fig = px.bar(df, x="군·구", y="건물1만동당_화재",
                     text=df["건물1만동당_화재"].round(2),
                     hover_data={"화재건수":True,"건물수":True},
                     title="군·구별 건물 수 대비 화재 비율(전체 기간, 데모)")
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(margin=dict(l=0,r=0,t=50,b=0),
                          xaxis_title=None, yaxis_title="건물 1만동당 화재(건)")
        return fig
