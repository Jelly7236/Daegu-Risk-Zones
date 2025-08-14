import os
import time
import json
import math
import requests
import pandas as pd

df_building_original = pd.read_csv("./Raw Data/건축물대장/건축물대장_대구광역시_종합.csv", sep=None, engine="python")

df_building_filter = df_building_original[["대지위치", "지상층수", "지하층수", "높이(m)", "구조코드명", "기타구조", "주용도코드명", "비상용승강기수"]]
df_building_filter["사용승인년도"] = df_building_original["사용승인일"].str.slice(start=0, stop=4)

df_building_filter1 = df_building_filter.loc[50001:100000, :]

df_building_filter1.to_csv("./건축물대장.csv")


KAKAO_REST_KEY = "f939970b0ab002e6aa011535f5388344"
KAKAO_URL = "https://dapi.kakao.com/v2/local/search/address.json"
HEADERS = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}

REQUEST_INTERVAL = 0.15
CACHE_PATH = "./kakao_geocode_cache.json"

# =========================
# 2) 캐시 로드/세이브
# =========================
def load_cache(path=CACHE_PATH):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache(cache, path=CACHE_PATH):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
    except:
        pass

cache = load_cache()

# =========================
# 3) 카카오 지오코딩 함수
# =========================
def kakao_geocode(address):
    if not isinstance(address, str) or not address.strip():
        return None

    addr = address.strip()
    if addr in cache:
        return cache[addr]

    params = {"query": addr}
    try:
        r = requests.get(KAKAO_URL, headers=HEADERS, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            docs = data.get("documents", [])
            if docs:
                d0 = docs[0]
                lon, lat = float(d0["x"]), float(d0["y"])
                result = {"lat": lat, "lon": lon}
            else:
                result = None
        else:
            result = None
    except:
        result = None

    cache[addr] = result
    save_cache(cache)
    time.sleep(REQUEST_INTERVAL)
    return result

# =========================
# 4) CSV 불러오기
# =========================
df_building_original = pd.read_csv(
    "./Raw Data/건축물대장/건축물대장_대구광역시_종합.csv",
    sep=None, engine="python"
)

df_building_filter = df_building_original[[
    "대지위치", "지상층수", "지하층수", "높이(m)", "구조코드명", "기타구조", "주용도코드명", "비상용승강기수"
]].copy()

df_building_filter["사용승인년도"] = df_building_original["사용승인일"].astype(str).str.slice(0, 4)

df_building_filter1 = df_building_filter.loc[50001:60000, :].copy()

# =========================
# 5) 좌표 변환 적용
# =========================
df_building_filter1["위도"] = None
df_building_filter1["경도"] = None

for i, addr in enumerate(df_building_filter1["대지위치"].dropna().unique(), 1):
    geo = kakao_geocode(addr)
    if geo:
        df_building_filter1.loc[df_building_filter1["대지위치"] == addr, "위도"] = geo["lat"]
        df_building_filter1.loc[df_building_filter1["대지위치"] == addr, "경도"] = geo["lon"]
    if i % 500 == 0:
        print(f"{i} / {len(df_building_filter1['대지위치'].dropna().unique())} 처리 완료")

# =========================
# 6) 저장
# =========================
df_building_filter1.to_csv(
    "./Data/건축물대장1_6.csv",
    index=False, encoding="utf-8-sig"
)
print("저장 완료")

# 합칠 파일 경로 리스트
files = [
    "./Raw Data/건축물대장_위도경도포함/건축물2_좌표.csv",
    "./Raw Data/건축물대장_위도경도포함/건축물대장1_1.csv",
    "./Raw Data/건축물대장_위도경도포함/건축물대장1_2.csv",
    "./Raw Data/건축물대장_위도경도포함/건축물대장1_3.csv",
    "./Raw Data/건축물대장_위도경도포함/건축물대장1_4.csv",
    "./Raw Data/건축물대장_위도경도포함/건축물대장1_5.csv",
    "./Raw Data/건축물대장_위도경도포함/건축물대장1_6.csv",
    "./Raw Data/건축물대장_위도경도포함/대구_건축물대장_2(6~80000).csv",
    "./Raw Data/건축물대장_위도경도포함/대구_건축물대장_all.csv",
    "./Raw Data/건축물대장_위도경도포함/건축물대장(30000~49999).csv"
]

# 뽑을 컬럼 목록
columns_to_keep = [
    "대지위치", "지상층수", "지하층수", "높이(m)", "구조코드명", "기타구조",
    "주용도코드명", "비상용승강기수", "사용승인년도", "위도", "경도"
]

dfs = []

for file in files:
    # CSV 읽기
    df = pd.read_csv(file, encoding="utf-8")
    
    # 지정한 컬럼만 선택 (없으면 건너뜀)
    existing_cols = [col for col in columns_to_keep if col in df.columns]
    df = df[existing_cols]
    
    dfs.append(df)

# 합치기
merged_df = pd.concat(dfs, ignore_index=True)

# 저장
merged_df.to_csv("건축물대장_통합.csv", index=False, encoding="utf-8-sig")