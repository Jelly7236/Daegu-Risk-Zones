# app/modules/tab_proposal.py
from shiny import ui, reactive
from shinywidgets import output_widget, render_widget

import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import numpy as np
import json

# ================== 경로 ==================
BASE = Path(__file__).resolve().parents[2]

# 행정동(폴리곤) - shp
SHAPE_DONG = BASE / "Data/시각화/대구_행정동/대구_행정동_군위포함.shp"
# 소방용수시설 CSV (동명 포함본)
HYD_CSV    = BASE / "Data/소방용수시설_동추가.csv"
# 소방서 위치 CSV
FS_CSV     = BASE / "Data/대구광역시_소방서_위치.csv"
# 건축물 CSV (위도/경도, 주용도점수, 건물노후도점수 포함)
BLD_CSV    = BASE / "Data/건축물대장_v0.6.csv"

# 기본 후보(체크박스 목록)
AOI_VALUES = ["가창면", "하빈면", "소보면", "삼국유사면"]
AOI_LABELS = {
    "가창면": "달성군/가창면",
    "하빈면": "달성군/하빈면",
    "소보면": "군위군/소보면",
    "삼국유사면": "군위군/삼국유사면",
}

# 격자/버퍼 파라미터
CELL_SIZE_M = 100
BUF_HYDRANT = 100
BUF_STATION = 4000

# 점 레이어 스타일
HYD_COLOR = "#1976d2"  # 용수시설 파랑
FS_COLOR  = "#000000"  # 소방서 검정
HYD_MAX   = 8000
FS_MAX    = 200

# ================== 유틸 ==================
def _safe_read_csv(path: Path, usecols=None) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, encoding="utf-8", usecols=usecols)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp949", usecols=usecols)

def _safe_union(gdf: gpd.GeoDataFrame):
    try:
        return gdf.unary_union
    except Exception:
        return gdf.dissolve().geometry.iloc[0]

def _bbox_center_zoom(aoi_geom):
    if hasattr(aoi_geom, "bounds"):
        minx, miny, maxx, maxy = aoi_geom.bounds
    else:
        # 대구 근처 폴백
        minx = 128.4; maxx = 128.9
        miny = 35.7;  maxy = 36.0
    cx = (minx + maxx) / 2
    cy = (miny + maxy) / 2
    span = max(maxx - minx, maxy - miny)
    if   span > 0.45: zoom = 9.4
    elif span > 0.30: zoom = 9.8
    elif span > 0.20: zoom = 10.2
    elif span > 0.12: zoom = 10.6
    elif span > 0.08: zoom = 11.0
    else:             zoom = 11.4
    zoom -= 0.3  # 살짝 줌아웃
    return {"lat": cy, "lon": cx}, zoom

def _polys_to_lines(gdf: gpd.GeoDataFrame):
    lats, lons = [], []
    for geom in gdf.geometry:
        if geom is None:
            continue
        if geom.geom_type == "Polygon":
            rings = [geom.exterior] + list(geom.interiors)
        elif geom.geom_type == "MultiPolygon":
            rings = []
            for p in geom.geoms:
                rings += [p.exterior] + list(p.interiors)
        else:
            continue
        for ring in rings:
            xs, ys = ring.coords.xy
            lons.extend(xs); lats.extend(ys)
            lons.append(None); lats.append(None)
    return lats, lons

def _generate_square_grid(aoi_polygon, cell_size_m=CELL_SIZE_M):
    aoi_utm = gpd.GeoSeries([aoi_polygon], crs="EPSG:4326").to_crs(epsg=5186).geometry[0]
    minx, miny, maxx, maxy = aoi_utm.bounds
    xs = np.arange(minx, maxx, cell_size_m)
    ys = np.arange(miny, maxy, cell_size_m)
    from shapely.geometry import Polygon
    squares = [
        Polygon([(x, y), (x + cell_size_m, y), (x + cell_size_m, y + cell_size_m), (x, y + cell_size_m)])
        for x in xs for y in ys
    ]
    grid = gpd.GeoDataFrame(geometry=squares, crs="EPSG:5186")
    clipped = gpd.clip(grid, aoi_utm)
    return clipped.to_crs(epsg=4326)

# ================== 고정 데이터 로드(전역) ==================
DONG_ALL = gpd.read_file(SHAPE_DONG).to_crs(epsg=4326)

HYD_ALL = _safe_read_csv(HYD_CSV)
HYD_G_ALL = (
    gpd.GeoDataFrame(
        HYD_ALL,
        geometry=gpd.points_from_xy(HYD_ALL["경도"], HYD_ALL["위도"]),
        crs="EPSG:4326",
    ) if not HYD_ALL.empty else gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
)

FS_ALL = _safe_read_csv(FS_CSV)
if not FS_ALL.empty:
    lat_col = next((c for c in ["위도","lat","LAT"] if c in FS_ALL.columns), None)
    lon_col = next((c for c in ["경도","lon","LON"] if c in FS_ALL.columns), None)
else:
    lat_col = lon_col = None
FS_G_ALL = (
    gpd.GeoDataFrame(
        FS_ALL, geometry=gpd.points_from_xy(FS_ALL[lon_col], FS_ALL[lat_col]), crs="EPSG:4326"
    ) if (not FS_ALL.empty and lat_col and lon_col) else gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
)

BLD_ALL = _safe_read_csv(BLD_CSV)
if not BLD_ALL.empty:
    for c in ["주용도점수","건물노후도점수"]:
        if c in BLD_ALL.columns:
            BLD_ALL[c] = pd.to_numeric(BLD_ALL[c], errors="coerce")
BLD_G_ALL = (
    gpd.GeoDataFrame(
        BLD_ALL,
        geometry=gpd.points_from_xy(BLD_ALL["경도"], BLD_ALL["위도"]),
        crs="EPSG:4326",
    ) if (not BLD_ALL.empty and "경도" in BLD_ALL.columns and "위도" in BLD_ALL.columns)
      else gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
)

# ================== 코어 계산 ==================
def _compute_grid_score(aoi_geom, bld_g: gpd.GeoDataFrame,
                        hyd_g: gpd.GeoDataFrame, fs_g: gpd.GeoDataFrame):
    # 1) 격자
    grid = _generate_square_grid(aoi_geom, CELL_SIZE_M).reset_index(drop=True)
    grid["cell_id"] = grid.index

    # 2) 버퍼(용수 100m, 소방서 4km)
    def _buffer_union(gseries: gpd.GeoSeries, dist_m: float):
        if gseries.empty:
            return None
        try:
            buf = gseries.to_crs(epsg=5186).buffer(dist_m).to_crs(epsg=4326)
            return buf.unary_union
        except Exception:
            buf = gseries.to_crs(epsg=5186).buffer(dist_m).to_crs(epsg=4326)
            return buf.dissolve().geometry.iloc[0]

    hyd_union = _buffer_union(hyd_g.geometry, BUF_HYDRANT) if (hyd_g is not None and not hyd_g.empty) else None
    fs_union  = _buffer_union(fs_g.geometry,  BUF_STATION) if (fs_g is not None and not fs_g.empty) else None

    # 3) 버퍼 외부 셀만 유지
    mask = pd.Series(True, index=grid.index)
    if hyd_union is not None:
        mask &= ~grid.intersects(hyd_union)
    if fs_union is not None:
        mask &= ~grid.intersects(fs_union)
    final_cells = grid.loc[mask].copy()

    if bld_g.empty or final_cells.empty:
        final_cells["score_sum"] = 0.0
        return final_cells

    # 4) 건물-셀 조인 후 점수합
    for _df in (bld_g, final_cells):
        _df.drop(columns=[c for c in ("index_right", "index_left") if c in _df.columns],
                 inplace=True, errors="ignore")

    bld_in_cell = gpd.sjoin(bld_g, final_cells, how="inner", predicate="within")
    bld_in_cell["score"] = bld_in_cell["주용도점수"].fillna(0) + bld_in_cell["건물노후도점수"].fillna(0)
    cell_score = bld_in_cell.groupby("cell_id")["score"].sum().reset_index()
    cell_score.columns = ["cell_id", "score_sum"]

    out = final_cells.merge(cell_score, on="cell_id", how="left")
    out["score_sum"] = out["score_sum"].fillna(0.0)
    return out

def _make_grid_map(final_cells_with_score: gpd.GeoDataFrame,
                   aoi_layer: gpd.GeoDataFrame,
                   center: dict, zoom: float,
                   hyd_g: gpd.GeoDataFrame | None = None,
                   fs_g: gpd.GeoDataFrame | None = None) -> go.FigureWidget:
    if final_cells_with_score.empty:
        return px.scatter(title="표시할 격자 데이터가 없습니다.")

    grid_json = json.loads(final_cells_with_score.to_json())

    # 흰→빨강
    white_to_red = [
        [0.00, "#ffffff"],
        [0.20, "#ffe5e5"],
        [0.40, "#ffb3b3"],
        [0.60, "#ff8080"],
        [0.80, "#ff4d4d"],
        [1.00, "#c62828"],
    ]
    vmax = float(final_cells_with_score["score_sum"].max() or 0.0)

    fig = px.choropleth_mapbox(
        final_cells_with_score,
        geojson=grid_json,
        locations="cell_id",
        featureidkey="properties.cell_id",
        color="score_sum",
        color_continuous_scale=white_to_red,
        range_color=(0, vmax),
        mapbox_style="open-street-map",
        opacity=0.9,
        center=center,
        zoom=zoom,
        hover_data={"score_sum":":.2f"},
    )
    fig.update_traces(
        selector=dict(type="choroplethmapbox"),
        marker_line_width=0.7,
        marker_line_color="#e6e6e6"
    )

    # AOI 경계(검은 실선)
    lat_bd, lon_bd = _polys_to_lines(aoi_layer)
    fig.add_scattermapbox(
        lat=lat_bd, lon=lon_bd, mode="lines",
        line=dict(width=2, color="#111111"),
        hoverinfo="skip", name="경계", showlegend=False
    )

    # ── 점 레이어: AOI 내부만 표시 ─────────────────────────────
    if hyd_g is not None and not hyd_g.empty:
        hyd_sub = hyd_g[hyd_g.within(_safe_union(aoi_layer))]
        if len(hyd_sub) > HYD_MAX:
            hyd_sub = hyd_sub.sample(HYD_MAX, random_state=42)
        fig.add_scattermapbox(
            lat=hyd_sub.geometry.y, lon=hyd_sub.geometry.x,
            mode="markers",
            marker=dict(size=5, color=HYD_COLOR),
            name="소방용수시설",
            hoverinfo="skip", hovertemplate=None,
            showlegend=True
        )

    if fs_g is not None and not fs_g.empty:
        fs_sub = fs_g[fs_g.within(_safe_union(aoi_layer))]
        if len(fs_sub) > FS_MAX:
            fs_sub = fs_sub.sample(FS_MAX, random_state=42)
        fig.add_scattermapbox(
            lat=fs_sub.geometry.y, lon=fs_sub.geometry.x,
            mode="markers",
            marker=dict(size=11, color=FS_COLOR),
            name="소방서",
            hoverinfo="skip", hovertemplate=None,
            showlegend=True
        )
    # ─────────────────────────────────────────────────────────

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=0, xanchor="center", x=0.5),
        coloraxis_colorbar=dict(title="격자 점수", thickness=12, x=1.02, xanchor="left", y=0.5),
    )
    return go.FigureWidget(fig)

# ================== Shiny 탭 ==================
def panel():
    return ui.nav_panel(
        "제안",
        ui.layout_sidebar(
            ui.sidebar(
                ui.h6("면 선택 (한 번에 1개)"),
                ui.input_checkbox_group(
                    "aoi", None,
                    choices=AOI_LABELS,          # ← 여기만 교체
                    selected=[AOI_VALUES[0]],    # ← 기본 선택
                ),
                ui.input_action_button("btn_apply_aoi", "적용", class_="btn-secondary"),
                ui.help_text("체크박스는 한 번에 하나만 선택됩니다."),
                position="left",
                title=None,
            ),
            ui.card(
                ui.card_header("취약지역 격자 (흰→빨강) + 소방서/용수시설"),
                output_widget("map_proposal")
            )
        )
    )

def server(input, output, session):
    # --- 체크박스 단일 선택 강제 ---
    current_aoi = reactive.Value([AOI_VALUES[0]])  # 내부 상태(항상 길이 1)
    applied_aoi = reactive.Value([AOI_VALUES[0]])  # '적용' 눌렀을 때 고정되는 값

    @reactive.effect
    @reactive.event(input.aoi)
    def _enforce_single():
        vals = input.aoi() or []
        prev = current_aoi.get() or []
        if len(vals) == 0:
            # 비워지면 이전 선택으로 되돌림
            session.send_input_message("aoi", {"value": prev})
            return
        if len(vals) > 1:
            # 이전과의 차집합 = 방금 체크한 것
            newly = [v for v in vals if v not in prev]
            picked = newly[-1] if newly else vals[-1]
            session.send_input_message("aoi", {"value": [picked]})
            current_aoi.set([picked])
        else:
            current_aoi.set(vals)

    @reactive.effect
    @reactive.event(input.btn_apply_aoi)
    def _apply_aoi():
        applied_aoi.set(current_aoi.get())

    # --- 선택된 AOI 레이어/지오메트리 ---
    @reactive.Calc
    def aoi_layer():
        names = applied_aoi.get() or [AOI_VALUES[0]]
        g = DONG_ALL[DONG_ALL["ADM_DR_NM"].isin(names)].copy()
        return g

    @reactive.Calc
    def aoi_geom():
        g = aoi_layer()
        return _safe_union(g) if not g.empty else None

    @reactive.Calc
    def center_zoom():
        geom = aoi_geom()
        return _bbox_center_zoom(geom) if geom is not None else ({"lat": 35.87, "lon": 128.60}, 10.0)

    # --- AOI 필터된 포인트/건물 ---
    @reactive.Calc
    def hyd_sel():
        g = aoi_layer()
        if HYD_G_ALL.empty or g.empty:
            return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
        # ADM_NM 이 있으면 이름 기준, 없으면 공간기반
        if "ADM_NM" in HYD_G_ALL.columns:
            names = applied_aoi.get() or [AOI_VALUES[0]]
            return HYD_G_ALL[HYD_G_ALL["ADM_NM"].isin(names)].copy()
        geom = _safe_union(g)
        return HYD_G_ALL[HYD_G_ALL.within(geom)].copy()

    @reactive.Calc
    def fs_sel():
        g = aoi_layer()
        if FS_G_ALL.empty or g.empty:
            return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
        geom = _safe_union(g)
        return FS_G_ALL[FS_G_ALL.within(geom)].copy()

    @reactive.Calc
    def bld_sel():
        g = aoi_layer()
        if BLD_G_ALL.empty or g.empty:
            return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
        names = applied_aoi.get() or [AOI_VALUES[0]]
        if "ADM_DR_NM" in BLD_G_ALL.columns:
            return BLD_G_ALL[BLD_G_ALL["ADM_DR_NM"].isin(names)].copy()
        geom = _safe_union(g)
        return BLD_G_ALL[BLD_G_ALL.within(geom)].copy()

    @reactive.Calc
    def grid_scores():
        geom = aoi_geom()
        if geom is None:
            return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
        return _compute_grid_score(geom, bld_sel(), hyd_sel(), fs_sel())

    # --- 지도 렌더 ---
    @render_widget
    def map_proposal():
        cells = grid_scores()
        aoi = aoi_layer()
        center, zoom = center_zoom()
        return _make_grid_map(cells, aoi, center, zoom, hyd_g=hyd_sel(), fs_g=fs_sel())
