import pandas as pd

# 1. 주소 매핑 파일
addr_df = pd.read_csv("최종주소번호.csv")  # 컬럼: ID, 정제주소

# 2. 파일명 매핑
file_map = {
    "20240301.csv": "2024_삼일절.csv",
    "20240505.csv": "2024_어린이날.csv",
    "20240606.csv": "2024_현충일.csv",
    "20240815.csv": "2024_광복절.csv",
    "20241003.csv": "2024_개천절.csv",
    "20241009.csv": "2024_한글날.csv",
    "20241224.csv": "2024_크리스마스이브.csv",
    "20241225.csv": "2024_크리스마스.csv",
    "20240101.csv": "2024_신정.csv"
}

# 3. 날짜 → 기념일 이름 매핑
holiday_map = {
    "2024-03-01": "삼일절",
    "2024-05-05": "어린이날",
    "2024-06-06": "현충일",
    "2024-08-15": "광복절",
    "2024-10-03": "개천절",
    "2024-10-09": "한글날",
    "2024-12-24": "크리스마스이브",
    "2024-12-25": "크리스마스",
    "2024-01-01": "신정"
}

# 4. 결과 리스트
merged_2024 = []

# 5. 파일 반복 처리
for file, save_name in file_map.items():
    try:
        df = pd.read_csv(file, encoding='utf-8')
    except:
        df = pd.read_csv(file, encoding='cp949')

    # 필요 없는 컬럼 제거
    cols_to_drop = ["기관 명", "모델명", "서버타입", "사이트명", "날짜"]
    df = df.drop(columns=[col for col in cols_to_drop if col in df.columns])

    # 날짜 필터링
    date_str = file.replace(".csv", "")
    date_fmt = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    df["등록일자"] = df["등록일자"].astype(str)
    df = df[df["등록일자"].str.startswith(date_fmt)]

    # 주소 매핑
    df = pd.merge(df, addr_df, left_on="시리얼", right_on="ID", how="left")

    # 방문자수 정제
    df["방문자수"] = pd.to_numeric(df["방문자수"], errors="coerce")
    df = df.dropna(subset=["방문자수"])
    df["방문자수"] = df["방문자수"].astype(int)

    # 월일 및 기념일 컬럼 추가
    df["월일"] = pd.to_datetime(df["등록일자"]).dt.strftime("%Y-%m-%d")
    df["기념일"] = df["월일"].map(holiday_map)

    # 필요한 컬럼만 정리
    df = df[["정제주소", "월일", "기념일", "방문자수"]]

    # 주소+날짜+기념일 단위로 그룹화
    grouped = df.groupby(["정제주소", "월일", "기념일"], as_index=False)["방문자수"].sum()

    # 조건에 따라 저장 또는 통합
    if date_str == "20240101":
        grouped.to_csv("2024_신정.csv", index=False, encoding="utf-8-sig")
        print("✅ 완료: 2024_신정.csv 저장")
    else:
        merged_2024.append(grouped)

# 6. 2024 전체 통합 저장
final_df = pd.concat(merged_2024, ignore_index=True)
final_df = final_df.groupby(["정제주소", "월일", "기념일"], as_index=False)["방문자수"].sum()
final_df = final_df.sort_values(by="월일")

final_df.to_csv("2024_유동인구.csv", index=False, encoding="utf-8-sig")
print("✅ 완료: 2024_유동인구.csv 저장")
