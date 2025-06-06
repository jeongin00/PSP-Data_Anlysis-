"""
import pandas as pd

# CSV 불러오기
df = pd.read_csv("지하철데이터.csv", encoding="cp949")  # 파일명에 맞게 수정하세요

# 시간대 컬럼
time_cols = df.columns[6:]

# 승차/하차 합산을 위해 groupby
df_sum = (
    df.groupby(["날짜", "호선", "역명"])[time_cols]
    .sum()
    .reset_index()
)

# 요일 컬럼 추가 (한글 요일: 월, 화, 수...)
df_sum["요일"] = pd.to_datetime(df_sum["날짜"]).dt.day_name(locale="ko_KR")

# 열 순서 정리
cols = ["날짜", "요일", "호선", "역명"] + list(time_cols)
df_sum = df_sum[cols]

# 저장
df_sum.to_csv("지하철_요일별_혼잡합산.csv", index=False, encoding="utf-8-sig")

print("✅ 지하철 혼잡도 요일별 합산 완료")
"""

import pandas as pd

# CSV 파일 로드
df = pd.read_csv("지하철_요일_평균혼잡도.csv", encoding="utf-8-sig")

# 시간대 컬럼 추출
time_cols = df.columns[3:]  # 요일, 호선, 역명 제외

# 시간대 수치를 반올림 → 정수형으로 변환
df[time_cols] = df[time_cols].round(0).astype(int)

# 요일 순서 강제 정렬
weekday_order = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
df['요일'] = pd.Categorical(df['요일'], categories=weekday_order, ordered=True)

# 정렬
df = df.sort_values(by=['요일', '호선', '역명'])

# 저장
df.to_csv("요일_호선_역명_혼잡도_평균_정렬.csv", index=False, encoding="utf-8-sig")

print("✅ 요일 정렬 및 정수 반올림 완료. 파일 저장됨.")

