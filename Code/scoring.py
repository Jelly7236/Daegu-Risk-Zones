from datetime import date
import math, re
import numpy as np
import pandas as pd

def _parse_year(value):
    if value is None:
        return None

    # float NaN 처리
    if isinstance(value, float) and math.isnan(value):
        return None

    # 이미 숫자면 처리
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)

    # 문자열 처리
    s = str(value).strip()
    if s == "":
        return None

    # '1985.0', '1985', '+1985', '1,985.0' 같은 숫자 문자열 처리
    s_num = s.replace(",", "")
    if re.fullmatch(r"[+-]?\d+(\.\d+)?", s_num):
        try:
            return int(float(s_num))
        except Exception:
            return None

    # 날짜/텍스트 안에 포함된 4자리 연도 추출 (예: '1985-01-01')
    m = re.search(r"(\d{4})", s)
    if m:
        return int(m.group(1))

    return None

def aging_score(value):
    year = _parse_year(value)
    if year is None:
        return 0

    current_year = date.today().year
    age = current_year - year

    # 미래 연도/비정상 값
    if age < 0 or year < 1800:
        return 0

    if age >= 40:
        return 5
    elif age >= 30:
        return 4
    elif age >= 20:
        return 3
    elif age >= 10:
        return 2
    elif age >= 0:
        return 1
    else:
        return 0


def _parse_floor_count(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (int, float)):
        n = int(float(value))
        return n if n >= 0 else None

    s = str(value).strip()
    if s == "":
        return None

    # 숫자만/소수 형태
    s_num = s.replace(",", "")
    if re.fullmatch(r"[+-]?\d+(\.\d+)?", s_num):
        try:
            n = int(float(s_num))
            return n if n >= 0 else None
        except Exception:
            return None

    # 문자열에 포함된 정수 추출 (예: '지상 12층')
    m = re.search(r"(-?\d+)", s)
    if m:
        n = int(m.group(1))
        return n if n >= 0 else None

    return None

def aboveground_floors_score(value):
    floors = _parse_floor_count(value)
    if floors is None:
        return 0

    if floors >= 30:
        return 5
    elif floors >= 20:
        return 4
    elif floors >= 10:
        return 3
    elif floors >= 5:
        return 2
    elif floors >= 1:
        return 1
    else:  # 0층
        return 0

def _parse_basement_floor_count(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None

    # 숫자형 바로 처리
    if isinstance(value, (int, float)):
        try:
            n = int(float(value))
            return abs(n) if n != 0 else 0
        except Exception:
            return None

    # 문자열 처리
    s = str(value).strip()
    if s == "":
        return None

    # 'B3' / 'B3F' / 'b 3' 형태
    m = re.fullmatch(r"[Bb]\s*(\d+)\s*[Ff]?", s)
    if m:
        return int(m.group(1))

    # '지하3층' / '지하 2' 형태
    m = re.search(r"지하\s*(\d+)", s)
    if m:
        return int(m.group(1))

    # 일반 숫자 추출(음수 포함) → 절대값
    m = re.search(r"(-?\d+)", s.replace(",", ""))
    if m:
        try:
            return abs(int(m.group(1)))
        except Exception:
            return None

    return None

def basement_floors_score(value):
    floors = _parse_basement_floor_count(value)
    if floors is None:
        return 0

    if floors >= 3:
        return 3
    elif floors >= 2:
        return 2
    elif floors >= 1:
        return 1
    else:
        return 0

MAIN_USE_SCORE_MAP = {
    # 9.0 — 숙박/다중이용시설
    '숙박시설': 9.0,
    '야영장시설': 9.0,
    '관광휴게시설': 9.0,

    # 8.0 — 공장/창고시설
    '공장': 8.0,
    '창고시설': 8.0,

    # 7.0 — 교육/복지/의료/수련
    '노유자시설': 7.0,
    '교육연구시설': 7.0,
    '교육연구및복지시설': 7.0,
    '의료시설': 7.0,
    '수련시설': 7.0,

    # 5.0 — 상업/판매/문화/업무/근린/생활편익
    '제2종근린생활시설': 5.0,
    '근린생활시설': 5.0,
    '제1종근린생활시설': 5.0,
    '종교시설': 5.0,
    '문화및집회시설': 5.0,
    '운동시설': 5.0,
    '업무시설': 5.0,
    '판매시설': 5.0,
    '위락시설': 5.0,
    '판매및영업시설': 5.0,
    '기타제1종근린생활시설': 5.0,
    '생활편익시설': 5.0,
    '소매점': 5.0,

    # 4.0 — 교정/군사/운수/환경·처리/통신/자동차/장례/발전/묘지 등 기반시설
    '동물및식물관련시설': 4.0,
    '위험물저장및처리시설': 4.0,
    '자원순환관련시설': 4.0,
    '분뇨.쓰레기처리시설': 4.0,
    '방송통신시설': 4.0,
    '자동차관련시설': 4.0,
    '장례시설': 4.0,
    '운수시설': 4.0,
    '교정및군사시설': 4.0,
    '국방,군사시설': 4.0,
    '발전시설': 4.0,
    '묘지관련시설': 4.0,

    # 2.0 — 주거
    '단독주택': 2.0,
    '공동주택': 2.0,
    '다가구주택': 2.0,

    # 1.0 — 행정/공공
    '공공용시설': 1.0,
}

def main_use_score_exact(value) -> float:
    if value is None:
        return 0.0

    # float NaN 처리
    if isinstance(value, float) and math.isnan(value):
        return 0.0

    s = str(value).strip()
    if s == "" or s.lower() == "nan":
        return 0.0

    return MAIN_USE_SCORE_MAP.get(s, 0.0)

STRUCTURE_SCORE_MAP = {
    # 콘크리트 계열 (0.0)
    '철근콘크리트구조': 0.0,
    '콘크리트구조': 0.0,
    '프리케스트콘크리트구조': 0.0,
    '보강콘크리트조': 0.0,
    '기타콘크리트구조': 0.0,
    '라멘조': 0.0,

    # 철골 계열 (2.0)
    '일반철골구조': 2.0,
    '경량철골구조': 2.0,
    '강파이프구조': 2.0,
    '철파이프조': 2.0,
    '기타강구조': 2.0,
    '스틸하우스조': 2.0,
    '단일형강구조': 2.0,
    '철골구조': 2.0,
    '공업화박판강구조(PEB)': 2.0,
    '트러스구조': 2.0,
    # 철골+콘크리트 복합은 '철골 계열'로 분류
    '철골콘크리트구조': 2.0,
    '철골철근콘크리트구조': 2.0,
    '철골철근콘크리트합성구조': 2.0,
    '기타철골철근콘크리트구조': 2.0,

    # 목조 계열 (5.0)
    '일반목구조': 5.0,
    '목구조': 5.0,
    '통나무구조': 5.0,
    '트러스목구조': 5.0,

    # 조적식 구조 (4.0)
    '벽돌구조': 4.0,
    '블록구조': 4.0,
    '시멘트블럭조': 4.0,
    '조적구조': 4.0,
    '기타조적구조': 4.0,
    '석구조': 4.0,
    '흙벽돌조': 4.0,

    # 조립식/판넬/컨테이너 (3.0)
    '조립식판넬조': 3.0,
    '컨테이너조': 3.0,

    # 기타/특수 (1.0)
    '막구조': 1.0,
    '기타구조': 1.0,
}

def structure_score(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, float) and math.isnan(value):  # NaN
        return 0.0

    s = str(value).strip()
    if not s or s.lower() == "nan":
        return 0.0

    # 1) 정확 매핑 우선
    if s in STRUCTURE_SCORE_MAP:
        return STRUCTURE_SCORE_MAP[s]

    # 2) 키워드 기반(미지정 라벨 대비)
    if ('목' in s) or ('통나무' in s):
        return 5.0
    if ('조적' in s) or ('벽돌' in s) or ('블록' in s) or ('석' in s):
        return 4.0
    if ('조립' in s) or ('판넬' in s) or ('컨테이너' in s):
        return 3.0
    if ('철골' in s) or ('강구조' in s) or ('스틸' in s) or ('파이프' in s):
        return 2.0
    if ('막' in s) or ('특수' in s):
        return 1.0
    if ('콘크리트' in s) or ('라멘' in s):
        return 0.0

    # 기본값
    return 0.0

def _parse_nonneg_int_count(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (int, float)):
        n = int(float(value))
        return n if n >= 0 else None

    s = str(value).strip()
    if s == "" or s.lower() == "nan":
        return None

    m = re.search(r"(\d+)", s.replace(",", ""))
    if m:
        n = int(m.group(1))
        return n if n >= 0 else None
    return None

def emergency_elevator_score(value) -> float:
    n = _parse_nonneg_int_count(value)
    if n is None:
        return 0.0

    if n == 0:
        return 5.0
    elif n == 1:
        return 4.0
    elif n == 2:
        return 3.0
    elif n == 3:
        return 2.0
    elif n == 4:
        return 1.0
    else:  # 5대 이상
        return 0.0
    
def firestation_distance_score(dist_m, cap_over_max=True, invalid_to_nan=True):
    arr = np.asarray(dist_m, dtype=float)

    # 음수/이상치 처리
    if invalid_to_nan:
        arr = np.where(arr < 0, np.nan, arr)

    default_val = 5.0 if cap_over_max else np.nan
    scores = np.select(
        [arr < 1000, arr < 3000, arr < 5000, arr < 7000, arr < 9000],
        [1.0,        2.0,        3.0,        4.0,        5.0],
        default=default_val
    )

    # 입력 타입 유지해서 반환
    if np.isscalar(dist_m):
        return float(scores.item())
    if isinstance(dist_m, pd.Series):
        return pd.Series(scores, index=dist_m.index, name=getattr(dist_m, "name", None))
    return scores

def hydrant_distance_score(dist_m, cap_over_max=True, invalid_to_nan=True):
    arr = np.asarray(dist_m, dtype=float)

    # 이상치 처리
    if invalid_to_nan:
        arr = np.where(arr < 0, np.nan, arr)

    default_val = 5.0 if cap_over_max else np.nan
    scores = np.select(
        [arr <= 30, arr <= 60, arr <= 90, arr <= 120, arr <= 150],
        [1.0,       2.0,       3.0,       4.0,        5.0],
        default=default_val
    )

    # NaN 입력은 그대로 NaN 유지
    scores = np.where(np.isnan(arr), np.nan, scores)

    # 입력 타입 유지
    if np.isscalar(dist_m):
        return float(np.asarray(scores).item())
    if isinstance(dist_m, pd.Series):
        return pd.Series(scores, index=dist_m.index, name=getattr(dist_m, "name", None))
    return scores

# 점수 산정
df = pd.read_csv("../Data/건축물대장_소화전_소방서거리.csv")
df["건물노후도점수"] = df["사용승인년도"].apply(aging_score)
df["지상층수점수"] = df["지상층수"].apply(aboveground_floors_score)
df["지하층수점수"] = df["지하층수"].apply(basement_floors_score)
df["주용도점수"] = df["주용도코드명"].apply(main_use_score_exact)
df["구조점수"] = df["구조코드명"].apply(structure_score)
df["비상용승강기점수"] = df["비상용승강기수"].apply(emergency_elevator_score)
df["소방서거리점수"] = df["소방서거리"].apply(firestation_distance_score)
df["소화전거리점수"] = df["소화전거리"].apply(hydrant_distance_score)
df["종합점수"] = df["건물노후도점수"] + df["지상층수점수"] + df["지하층수점수"] + df["주용도점수"] + df["구조점수"] + df["비상용승강기점수"] + df["소방서거리점수"] + df["소화전거리점수"]

df.to_csv("../Data/건축물대장_통합_점수.csv")