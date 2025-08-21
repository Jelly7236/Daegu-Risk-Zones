# app/modules/tab_analysis.py
from shiny import ui, reactive
from shinywidgets import output_widget, render_widget
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json, re

# =============== 사용자 기본값 ===============
ZOOM_LEFT_DEFAULT = 8.0
ZOOM_RIGHT_OFFSET = -0.5
CENTER_LEFT = {"lat": 35.9714, "lon": 128.6014}
LEFT_MAP_HEIGHT = 700

# 히스토그램(막대) 관련
HIST_FACET_WRAP = 3          # 3개 지표라 3으로
HIST_PANEL_HEIGHT = 200
HIST_PANEL_WIDTH = 500      # 가로폭 살짝 확대
BAR_COLOR = "#546e7a"

# =============== 경로 ===============
BASE = Path(__file__).resolve().parents[2]
CSV_PATH    = BASE / "Data/건축물대장_v0.6.csv"
GEO_GU      = BASE / "Data/시각화/대구_시군구_군위포함/대구_시군구_군위포함.geojson"
GEO_DONG    = BASE / "Data/시각화/대구_행정동/대구_행정동_군위포함.geojson"
FIRESTN_CSV = BASE / "Data/대구광역시_소방서_위치.csv"
HYDRANT_CSV = BASE / "Data/대구광역시_용수시설_위치.csv"

# =============== Shapely (선택) ===============
try:
    from shapely.geometry import shape, Point
    from shapely.prepared import prep
    SHAPELY_OK = True
except Exception:
    SHAPELY_OK = False

# =============== 헬퍼 ===============
def _safe_read_csv(path: Path, usecols=None) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, encoding="utf-8", usecols=usecols)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp949", usecols=usecols)

def norm_name(x):
    if pd.isna(x):
        return None
    s = str(x)
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[(){}\[\]-]", "", s)
    s = s.replace("ㆍ", "")
    return s

def _bbox_center_zoom_for_gu(gu_geojson: dict, key: str):
    west, south, east, north = 1e9, 1e9, -1e9, -1e9
    def upd(lon, lat):
        nonlocal west, south, east, north
        west = min(west, lon); south = min(south, lat)
        east = max(east, lon); north = max(north, lat)
    for ft in gu_geojson.get("features", []):
        props = ft.get("properties", {}) or {}
        if props.get("_key") != key:
            continue
        geom = ft.get("geometry") or {}
        gtype = geom.get("type"); coords = geom.get("coordinates")
        if not coords or not gtype: continue
        if gtype == "Polygon":
            for ring in coords:
                for lon, lat in ring: upd(lon, lat)
        elif gtype == "MultiPolygon":
            for poly in coords:
                for ring in poly:
                    for lon, lat in ring: upd(lon, lat)
        break
    if not (west < east and south < north):
        return {"lat": 35.8714, "lon": 128.6014}, 10.6, None
    center = {"lon": (west + east) / 2.0, "lat": (south + north) / 2.0}
    lon_span = max(1e-6, east - west); lat_span = max(1e-6, north - south)
    span = max(lon_span, lat_span)
    if span > 0.45:   zoom = 9.4
    elif span > 0.30: zoom = 9.8
    elif span > 0.20: zoom = 10.2
    elif span > 0.12: zoom = 10.6
    elif span > 0.08: zoom = 11.0
    else:             zoom = 11.4
    return center, zoom, (west, south, east, north)

def _zoom_offset(z: float, delta: float = -0.5) -> float:
    return max(4.0, min(16.0, z + delta))

def _load_points_csv_basic(path: Path):
    df = _safe_read_csv(path)
    if df.empty:
        return df
    cand_lat = ["위도", "lat", "LAT", "Latitude"]
    cand_lon = ["경도", "lon", "LON", "Longitude"]
    lat_col = next((c for c in cand_lat if c in df.columns), None)
    lon_col = next((c for c in cand_lon if c in df.columns), None)
    if not lat_col or not lon_col:
        return pd.DataFrame(columns=["위도", "경도"])
    out = df[[lat_col, lon_col]].rename(columns={lat_col: "위도", lon_col: "경도"}).copy()
    out["위도"] = pd.to_numeric(out["위도"], errors="coerce")
    out["경도"] = pd.to_numeric(out["경도"], errors="coerce")
    out = out.dropna(subset=["위도", "경도"])
    out = out[(out["위도"].between(30, 45)) & (out["경도"].between(120, 135))]
    return out

def _load_hydrants_csv(path: Path):
    df = _safe_read_csv(path)
    if df.empty:
        return df
    cand_lat = ["위도", "lat", "LAT", "Latitude"]
    cand_lon = ["경도", "lon", "LON", "Longitude"]
    cand_code = ["시설유형코드", "시설유형", "type_code", "코드"]
    lat_col = next((c for c in cand_lat if c in df.columns), None)
    lon_col = next((c for c in cand_lon if c in df.columns), None)
    code_col = next((c for c in cand_code if c in df.columns), None)
    if not lat_col or not lon_col:
        return pd.DataFrame(columns=["위도", "경도", "시설유형코드"])
    cols = [lat_col, lon_col] + ([code_col] if code_col else [])
    out = df[cols].copy()
    out = out.rename(columns={lat_col: "위도", lon_col: "경도"})
    if code_col:
        out = out.rename(columns={code_col: "시설유형코드"})
        out["시설유형코드"] = out["시설유형코드"].astype(str).str.extract(r"(\d+)").fillna("0")
    else:
        out["시설유형코드"] = "0"
    out["위도"] = pd.to_numeric(out["위도"], errors="coerce")
    out["경도"] = pd.to_numeric(out["경도"], errors="coerce")
    out = out.dropna(subset=["위도", "경도"])
    out = out[(out["위도"].between(30, 45)) & (out["경도"].between(120, 135))]
    return out

def _filter_points_in_poly(df: pd.DataFrame, poly, max_n: int):
    if df.empty or poly is None:
        return df
    if not SHAPELY_OK:
        minx, miny, maxx, maxy = poly.bounds
        sub = df[(df["경도"].between(minx, maxx)) & (df["위도"].between(miny, maxy))]
        return sub if len(sub) <= max_n else sub.sample(max_n, random_state=42)
    prepared = prep(poly)
    mask = df.apply(lambda r: prepared.covers(Point(r["경도"], r["위도"])), axis=1)
    sub = df[mask]
    return sub if len(sub) <= max_n else sub.sample(max_n, random_state=42)

def _build_border_lines_map(geojson: dict, key_name: str):
    out = {}
    for ft in geojson.get("features", []):
        props = ft.get("properties", {}) or {}
        k = props.get(key_name)
        geom = ft.get("geometry") or {}
        if not k or not geom:
            continue
        gtype = geom.get("type"); coords = geom.get("coordinates")
        lats, lons = [], []
        if gtype == "Polygon":
            for ring in coords:
                for lon, lat in ring:
                    lats.append(lat); lons.append(lon)
                lats.append(None); lons.append(None)
        elif gtype == "MultiPolygon":
            for poly in coords:
                for ring in poly:
                    for lon, lat in ring:
                        lats.append(lat); lons.append(lon)
                    lats.append(None); lons.append(None)
        if lats and lons:
            out[k] = (lats, lons)
    return out

def _detect_dong_gu_prop(gj_dong, df_gu_keys_norm: set):
    # 동 GeoJSON 안에서 "구 이름"처럼 보이는 속성 자동 탐색
    cand = [
        "SIGUNGU_NM","SGG_NM","SIG_KOR_NM","SIG_KOR","SIGUNGU","GU_NM","GU",
        "sigungu_nm","sgg_nm","sig_kor_nm","sig_kor","sigungu","gu_nm","gu"
    ]
    prop_keys = set()
    for ft in gj_dong.get("features", [])[:20]:
        prop_keys |= set((ft.get("properties") or {}).keys())
    cand += [k for k in prop_keys if k not in cand]

    best_key, best_overlap = None, -1
    for key in cand:
        vals = set()
        for ft in gj_dong.get("features", []):
            v = (ft.get("properties") or {}).get(key)
            nv = norm_name(v)
            if nv: vals.add(nv)
        overlap = len(vals & df_gu_keys_norm)
        if overlap > best_overlap:
            best_key, best_overlap = key, overlap
    return best_key if best_overlap > 0 else None

# =============== 데이터 로드/전처리 ===============
df = _safe_read_csv(CSV_PATH)
for col in ["종합점수", "구군", "ADM_DR_NM"]:
    if col not in df.columns:
        raise RuntimeError(f"CSV에 '{col}' 컬럼이 없습니다. (보유: {list(df.columns)[:30]})")

df["종합점수"] = pd.to_numeric(df["종합점수"], errors="coerce")
df["_key_gu"]   = df["구군"].map(norm_name)
df["_key_dong"] = df["ADM_DR_NM"].map(norm_name)

with open(GEO_GU, "r", encoding="utf-8") as f:
    gj_gu = json.load(f)
with open(GEO_DONG, "r", encoding="utf-8") as f:
    gj_dong = json.load(f)

# 시군구 GeoJSON: _key
for feat in gj_gu.get("features", []):
    props = feat.get("properties", {}) or {}
    props["_key"] = norm_name(props.get("SIGUNGU_NM"))
    feat["properties"] = props

# ---- 동 GeoJSON: 구/동/콤보키 주입 (구속성 자동 탐지 + 폴백) ----
df_gu_keys_norm = set(df["_key_gu"].dropna().unique())
DONG_GU_PROP = _detect_dong_gu_prop(gj_dong, df_gu_keys_norm)
USE_COMBO = DONG_GU_PROP is not None

for feat in gj_dong.get("features", []):
    props = feat.get("properties", {}) or {}
    k_gu   = norm_name(props.get(DONG_GU_PROP)) if USE_COMBO else None
    k_dong = norm_name(props.get("ADM_DR_NM"))
    props["_key_dong"]  = k_dong
    props["_key_combo"] = f"{k_gu}|{k_dong}" if (USE_COMBO and k_gu and k_dong) else None
    feat["properties"] = props

# (Shapely용) 폴리곤 dict (구)
GU_GEOMS = {}
if SHAPELY_OK:
    try:
        for ft in gj_gu.get("features", []):
            props = ft.get("properties", {}) or {}
            k = props.get("_key")
            geom = ft.get("geometry")
            if k and geom:
                GU_GEOMS[k] = shape(geom)
    except Exception as e:
        print(f"[warn] GU 폴리곤 생성 실패: {e}")
        GU_GEOMS = {}

# 동 테두리 경로(키 선택)
DONG_KEY_FIELD = "_key_combo" if USE_COMBO else "_key_dong"
BORDER_LINES_DONG = _build_border_lines_map(gj_dong, DONG_KEY_FIELD)

# 좌측: 구/군별 평균
gu_avg = (
    df.dropna(subset=["_key_gu", "종합점수"])
      .groupby("_key_gu", as_index=False)["종합점수"]
      .mean()
      .rename(columns={"종합점수": "종합점수_평균"})
)
name_map_gu = (
    df[["구군", "_key_gu"]]
      .dropna().drop_duplicates()
      .groupby("_key_gu")["구군"].first().reset_index()
)
gu_avg = gu_avg.merge(name_map_gu, on="_key_gu", how="left")

# 포인트 데이터
def _load_points_dataframe():
    df_fs  = _load_points_csv_basic(FIRESTN_CSV)
    df_hyd = _load_hydrants_csv(HYDRANT_CSV)
    return df_fs, df_hyd

DF_FS, DF_HYD = _load_points_dataframe()

DEFAULT_GU = "중구" if "중구" in set(df["구군"].dropna().unique()) else df["구군"].dropna().iloc[0]

# =============== UI ===============
def panel():
    return ui.nav_panel(
        "분석 결과 및 현황",
        ui.layout_columns(
            ui.card(
                ui.card_header("구/군별 종합점수 평균"),
                ui.div(output_widget("map_gu_avg"), style="height: 100%;", class_="mx-auto",),
                style=f"height: 86vh; min-height: 500px;"
            ),
            ui.div(  # 오른쪽 컬럼: 지도 카드 + 히스토그램 카드
                ui.card(
                    ui.card_header("동별 종합점수 평균"),
                    ui.layout_sidebar(
                        ui.sidebar(
                            ui.input_checkbox("chk_fs", "소방서", value=True),
                            ui.div(
                                ui.input_checkbox_group(
                                    "hyd_types", "소방용수시설 유형",
                                    choices={
                                        "1": "지상식 소화전",
                                        "2": "지하식 소화전",
                                        "3": "급수탑",
                                        "4": "저수조",
                                        "5": "승하강식",
                                        "6": "비상소화장치",
                                    },
                                    selected=[],
                                ),
                            ),
                            ui.input_action_button("btn_apply", "적용", class_="btn-primary", style="background-color:#9e9e9e; border-color:#9e9e9e; color:#fff;"),
                            position="right",
                            title=None,
                        ),
                        output_widget("map_dong_avg")
                    ),
                ),
                ui.card(
                    ui.card_header("(선택 동) 건물별 각 점수 평균"),
                    ui.div(
                        output_widget("hist_scores"),
                        style="width:100%;"
                    ),
                ),
                class_="d-flex flex-column gap-3"
            ),
            col_widths=[6, 6]
        )
    )

# =============== Server ===============
def server(input, output, session):
    clicked_gu = reactive.Value(DEFAULT_GU)
    selected_dong_key = reactive.Value(None)  # 콤보 또는 동키(폴백)

    # 사이드바 적용 상태
    applied = reactive.Value({
        "show_fs": True,
        "hyd_types": set(),
    })

    @reactive.effect
    @reactive.event(input.btn_apply)
    def _apply_sidebar():
        applied.set({
            "show_fs": bool(input.chk_fs()),
            "hyd_types": set(input.hyd_types() or []),
        })

    # 좌측 지도
    @render_widget
    def map_gu_avg():
        if gu_avg.empty:
            return px.scatter(title="데이터 없음")

        df_left = gu_avg.rename(columns={"_key_gu": "_key"})
        vmin = float(df_left["종합점수_평균"].min())
        vmax = float(df_left["종합점수_평균"].max())
        white_to_red = [[0.0, "#ffffff"], [1.0, "#ff0000"]]

        base = px.choropleth_mapbox(
            df_left,
            geojson=gj_gu,
            locations="_key",
            featureidkey="properties._key",
            color="종합점수_평균",
            color_continuous_scale=white_to_red,
            range_color=(vmin, vmax),
            mapbox_style="open-street-map",
            center=CENTER_LEFT,
            zoom=ZOOM_LEFT_DEFAULT,
            hover_name="구군",
            hover_data={"종합점수_평균":":.2f"},
            labels={"종합점수_평균": "종합점수 평균"},
        )
        base.update_layout(
            height=LEFT_MAP_HEIGHT,
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=0, xanchor="center", x=0.5)
        )

        figw = go.FigureWidget(base)

        if len(figw.data) > 0:
            base_trace = figw.data[0]
            base_trace.showlegend = False

            def _on_click(trace, points, state):
                if not points.point_inds: return
                idx = points.point_inds[0]
                try:
                    loc = trace.locations[idx]  # _key(구)
                except Exception:
                    return
                row = gu_avg.loc[gu_avg["_key_gu"] == loc]
                if not row.empty:
                    clicked_gu.set(row.iloc[0]["구군"])
                    selected_dong_key.set(None)  # 구 변경 시 동 초기화

            # 호버 하이라이트(검은색)
            hover_outline = go.Choroplethmapbox(
                geojson=gj_gu,
                locations=[], z=[], zmin=0, zmax=1,
                colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                featureidkey="properties._key",
                showscale=False, hoverinfo="skip",
                marker=dict(line=dict(width=3, color="#000000")),
                name="hover_gu",
                showlegend=False
            )
            figw.add_trace(hover_outline)

            def _overlay_idx():
                for i, tr in enumerate(figw.data):
                    if getattr(tr, "name", "") == "hover_gu":
                        return i
                return None

            def _on_hover(trace, points, state):
                oi = _overlay_idx()
                if oi is None: return
                if points.point_inds:
                    idx = points.point_inds[0]
                    try:
                        loc = trace.locations[idx]
                    except Exception:
                        return
                    figw.data[oi].locations = [loc]
                    figw.data[oi].z = [1]

            def _on_unhover(trace, points, state):
                oi = _overlay_idx()
                if oi is None: return
                figw.data[oi].locations = []
                figw.data[oi].z = []

            try:
                base_trace.on_click(_on_click)
                base_trace.on_hover(_on_hover)
                base_trace.on_unhover(_on_unhover)
                figw.layout.transition = dict(duration=150, easing="cubic-in-out")
            except Exception as e:
                print(f"[warn] 이벤트 바인딩 실패: {e}")

        return figw

    # 우측: 선택 구의 동별 평균 (+ 콤보키 or 단일키)
    @reactive.Calc
    def dong_avg_sel():
        sel = clicked_gu.get()
        d = df[df["구군"] == sel].copy()
        if d.empty:
            keycol = "_key_combo" if USE_COMBO else "_key_dong"
            return pd.DataFrame(columns=[keycol, "종합점수_평균", "동", "구군"])

        avg = (
            d.dropna(subset=["_key_dong", "종합점수"])
             .groupby("_key_dong", as_index=False)["종합점수"]
             .mean()
             .rename(columns={"종합점수": "종합점수_평균"})
        )
        name_map = (
            d[["ADM_DR_NM", "_key_dong"]]
              .dropna().drop_duplicates()
              .groupby("_key_dong")["ADM_DR_NM"].first().reset_index()
              .rename(columns={"ADM_DR_NM": "동"})
        )
        avg = avg.merge(name_map, on="_key_dong", how="left")
        if USE_COMBO:
            k_gu = norm_name(sel)
            avg["_key_combo"] = avg["_key_dong"].map(lambda kd: f"{k_gu}|{kd}" if kd else None)
        avg["구군"] = sel
        return avg

    # 우측 뷰 + 폴리곤(구)
    @reactive.Calc
    def right_view_and_polys():
        sel_gu = clicked_gu.get()
        sel_key = norm_name(sel_gu)
        center, zoom, bbox = _bbox_center_zoom_for_gu(gj_gu, sel_key)
        zoom = _zoom_offset(zoom, ZOOM_RIGHT_OFFSET)
        gu_poly = GU_GEOMS.get(sel_key) if (SHAPELY_OK and sel_key in GU_GEOMS) else None
        return center, zoom, bbox, gu_poly

    # 구가 바뀌면 기본 동 자동 지정
    @reactive.effect
    def _ensure_default_dong():
        dd = dong_avg_sel()
        keycol = "_key_combo" if USE_COMBO else "_key_dong"
        if selected_dong_key.get() is None and not dd.empty and keycol in dd.columns:
            selected_dong_key.set(dd.iloc[0][keycol])

    # 우측 지도
    @render_widget
    def map_dong_avg():
        dd = dong_avg_sel()
        if dd.empty:
            return px.scatter(title=f"선택 구/군 데이터 없음: {clicked_gu.get()}")

        vmin = float(dd["종합점수_평균"].min())
        vmax = float(dd["종합점수_평균"].max())
        white_to_red = [[0.0, "#ffffff"], [1.0, "#ff0000"]]
        center, zoom, bbox, gu_poly = right_view_and_polys()

        keycol = "_key_combo" if USE_COMBO else "_key_dong"
        feature_key = f"properties.{keycol}"

        base = px.choropleth_mapbox(
            dd,
            geojson=gj_dong,
            locations=keycol,
            featureidkey=feature_key,
            color="종합점수_평균",
            color_continuous_scale=white_to_red,
            range_color=(vmin, vmax),
            mapbox_style="open-street-map",
            center=center,
            zoom=zoom,
            hover_name="동",
            hover_data={"종합점수_평균":":.2f"},
            labels={"종합점수_평균": "종합점수 평균"},
        )
        base.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=0, xanchor="center", x=0.5)
        )

        figw = go.FigureWidget(base)
        base_trace = figw.data[0] if len(figw.data) else None
        if base_trace is not None:
            base_trace.showlegend = False

        # 사이드바 적용 상태
        opts = applied.get()
        show_fs   = bool(opts.get("show_fs", True))
        sel_types = set(opts.get("hyd_types", set()))
        HYD_COLOR = "#1976d2"
        MAX_FS  = 800
        MAX_HYD = 6000

        # 포인트는 '선택 구' 폴리곤 기준
        if sel_types and not DF_HYD.empty:
            hyd_f = DF_HYD[DF_HYD["시설유형코드"].isin(sel_types)]
            sub = _filter_points_in_poly(hyd_f, gu_poly, MAX_HYD) if gu_poly is not None else hyd_f
            if not sub.empty:
                figw.add_scattermapbox(
                    lat=sub["위도"], lon=sub["경도"], mode="markers",
                    marker=dict(size=5, color=HYD_COLOR),
                    name="소방용수시설",
                    hoverinfo="skip", hovertemplate=None,
                    showlegend=True
                )
        if show_fs and not DF_FS.empty:
            sub = _filter_points_in_poly(DF_FS, gu_poly, MAX_FS) if gu_poly is not None else DF_FS
            if not sub.empty:
                figw.add_scattermapbox(
                    lat=sub["위도"], lon=sub["경도"], mode="markers",
                    marker=dict(size=11, color="#000000"),   # 검은색, 소방용수시설보다 위
                    name="소방서",
                    hoverinfo="skip", hovertemplate=None,
                    showlegend=True
                )
        # 최상단 하이라이트 경계선(검은색)
        border_line = go.Scattermapbox(
            lat=[], lon=[], mode="lines",
            line=dict(width=3, color="#000000"),
            name="border_top",
            hoverinfo="skip",
            showlegend=False
        )
        figw.add_trace(border_line)

        # 콜백(동 하이라이트/클릭)
        if base_trace is not None:
            def _border_idx():
                for i, tr in enumerate(figw.data):
                    if getattr(tr, "name", "") == "border_top":
                        return i
                return None

            def _on_hover(trace, points, state):
                bi = _border_idx()
                if bi is None: return
                if points.point_inds:
                    idx = points.point_inds[0]
                    try:
                        loc_key = trace.locations[idx]   # combo 또는 동 단일키
                    except Exception:
                        return
                    lats_lons = BORDER_LINES_DONG.get(loc_key)
                    if lats_lons:
                        lats, lons = lats_lons
                        with figw.batch_update():
                            figw.data[bi].lat = lats
                            figw.data[bi].lon = lons

            def _on_unhover(trace, points, state):
                bi = _border_idx()
                if bi is None: return
                with figw.batch_update():
                    figw.data[bi].lat = []
                    figw.data[bi].lon = []

            def _on_click(trace, points, state):
                if not points.point_inds: return
                idx = points.point_inds[0]
                try:
                    loc_key = trace.locations[idx]
                except Exception:
                    return
                selected_dong_key.set(loc_key)

            try:
                base_trace.on_hover(_on_hover)
                base_trace.on_unhover(_on_unhover)
                base_trace.on_click(_on_click)
                figw.layout.transition = dict(duration=150, easing="cubic-in-out")
            except Exception as e:
                print(f"[warn] 이벤트 바인딩 실패: {e}")

        figw.update_layout(legend=dict(orientation="h", yanchor="bottom", y=0, xanchor="center", x=0.5))
        return figw

    # ---- 히스토그램(선택 동) — 배경 흰색, 최대값 빨간 막대, 나머지 회색 ----
    @render_widget
    def hist_scores():
        sel_key = selected_dong_key.get()
        if sel_key is None:
            return px.scatter(title="오른쪽 지도에서 동(읍/면)을 클릭해 주세요.")
    
        if USE_COMBO:
            try:
                k_gu, k_dong = sel_key.split("|", 1)
            except ValueError:
                return px.scatter(title="선택 동 키 형식이 올바르지 않습니다.")
            d = df[(df["_key_gu"] == k_gu) & (df["_key_dong"] == k_dong)].copy()
        else:
            k_dong = sel_key
            k_gu = norm_name(clicked_gu.get())
            d = df[(df["_key_gu"] == k_gu) & (df["_key_dong"] == k_dong)].copy()
    
        if d.empty:
            return px.scatter(title="선택 동 데이터 없음")
    
        # 표시할 5개 지표
        wanted = ["건물노후도점수", "주용도점수", "구조점수", "소방서거리점수", "소방용수시설거리점수"]
        cols = [c for c in wanted if c in d.columns]
        if not cols:
            return px.scatter(title="요청한 지표 컬럼이 없습니다.")
    
        for c in cols:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    
        mean_df = pd.DataFrame({"지표": cols, "평균": [float(d[c].mean()) for c in cols]})
        # 색상: 최대값만 빨강, 나머지 회색
        MAX_COLOR   = "#e53935"
        OTHER_COLOR = "#9e9e9e"
        max_val = float(mean_df["평균"].max()) if len(mean_df) else 0.0
        bar_colors = [MAX_COLOR if float(v) == max_val else OTHER_COLOR for v in mean_df["평균"]]
    
        fig = px.bar(
            mean_df,
            x="지표", y="평균",
            text="평균",
            category_orders={"지표": cols},
        )
    
        # 막대 스타일 & 라벨
        fig.update_traces(
            marker_color=bar_colors,
            marker_line=dict(width=0.6, color="#455a64"),
            texttemplate="%{text:.2f}",
            textposition="outside",
            cliponaxis=False,
        )
    
        # 배경/여백/간격(여유롭게)
        y_max = max(1e-6, max_val * 1.25)
        fig.update_yaxes(range=[0, y_max], automargin=True)
        fig.update_xaxes(automargin=True)
        fig.update_layout(
            title=None,
            showlegend=False,
            bargap=0.22,
            margin=dict(l=12, r=18, t=0, b=0),
            height=HIST_PANEL_HEIGHT,
            autosize=True,
            plot_bgcolor="white",   # ← 그래프 바탕 흰색
            paper_bgcolor="white",  # ← 캔버스 배경 흰색
        )
        return fig
    
