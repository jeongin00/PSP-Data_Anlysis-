"""
import pandas as pd

# ✅ 1. CSV 파일 불러오기
df = pd.read_csv("요일별지하철.csv")  # 파일명 바꿔주세요

# ✅ 2. 시간대 묶기
df["새벽"] = df["06시 이전"] + df["06시-07시"]
df["출근"] = df["07시-08시"] + df["08시-09시"]
df["오전"] = df["09시-10시"] + df["10시-11시"] + df["11시-12시"]
df["점심"] = df["12시-13시"] + df["13시-14시"]
df["오후"] = df["14시-15시"] + df["15시-16시"] + df["16시-17시"]
df["퇴근"] = df["17시-18시"] + df["18시-19시"]
df["저녁"] = df["19시-20시"] + df["20시-21시"]
df["심야"] = df["21시-22시"] + df["22시-23시"] + df["23시-24시"] + df["24시 이후"]

# ✅ 3. 기존 시간대 컬럼 제거
original_cols = [
    "06시 이전", "06시-07시", "07시-08시", "08시-09시", "09시-10시", "10시-11시", "11시-12시",
    "12시-13시", "13시-14시", "14시-15시", "15시-16시", "16시-17시",
    "17시-18시", "18시-19시", "19시-20시", "20시-21시",
    "21시-22시", "22시-23시", "23시-24시", "24시 이후"
]
df.drop(columns=original_cols, inplace=True)

# ✅ 4. 결과 저장
df.to_csv("시간대_묶음_결과.csv", index=False)
"""
import pandas as pd

# ✅ 1. 데이터 로드
df = pd.read_csv("요일별지하철.csv")  # 여기에 파일명 넣으세요

# ✅ 2. 시간대 그룹핑 정의
group_map = {
    "새벽": ["06시 이전", "06시-07시"],
    "출근": ["07시-08시", "08시-09시"],
    "오전": ["09시-10시", "10시-11시", "11시-12시"],
    "점심": ["12시-13시", "13시-14시"],
    "오후": ["14시-15시", "15시-16시", "16시-17시"],
    "퇴근": ["17시-18시", "18시-19시"],
    "저녁": ["19시-20시", "20시-21시"],
    "심야": ["21시-22시", "22시-23시", "23시-24시", "24시 이후"]
}

# ✅ 3. 그룹핑된 시간대 합산
for group, columns in group_map.items():
    df[group] = df[columns].sum(axis=1)

# ✅ 4. 정규화 대상 컬럼
group_cols = list(group_map.keys())

# ✅ 5. 전체 데이터 기준 정규화 (0~10, 소수점 1자리)
all_values = df[group_cols].values.flatten()
global_min = all_values.min()
global_max = all_values.max()

for col in group_cols:
    df[col] = (((df[col] - global_min) / (global_max - global_min)) * 10).round(1)

# ✅ 6. 불필요한 기존 시간대 컬럼 제거
raw_time_cols = [c for cols in group_map.values() for c in cols]
df.drop(columns=raw_time_cols, inplace=True)

# ✅ 7. 저장
df.to_csv("최종_시간대정규화_0to10.csv", index=False)
