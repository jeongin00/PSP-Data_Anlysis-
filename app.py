from flask import Flask, request, jsonify, render_template
import pandas as pd
import torch
import torch.nn as nn
import joblib
import requests
import datetime
from model import MLP

app = Flask(__name__)

# 🔹 1. 모델 및 인코더 불러오기
model = MLP(input_dim=5, hidden_dim=64, output_dim=6)
model.load_state_dict(torch.load("model.pt"))
model.eval()

label_encoders = joblib.load("label_encoders.pkl")

# 🔹 2. 혼잡도 데이터 불러오기
df_congestion = pd.read_csv("혼잡도변환.csv")  # 측정시간, 구, 혼잡도점수
# 지하철 데이터 로드
df_subway = pd.read_csv("지하철.csv")  # 요일, 역명 등 포함

# 🔹 3. 날씨 API 정보
API_KEY = "870149e3ea42fccbd6ec5dff14fd193e"
CITY = "Seoul"
WEATHER_URL = f"http://api.openweathermap.org/data/2.5/forecast?q={CITY}&appid={API_KEY}&units=metric&lang=kr"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json()
        gu = data["gu"]
        mbti = data["mbti"]
        day = data["day"]
        holiday = data["holiday"]
        date_str = data["date"]  # YYYY-MM-DD

        # 🔹 1. 혼잡도점수 조회
        score_row = df_congestion[(df_congestion["측정시간"] == day) & (df_congestion["구"] == gu)]
        if score_row.empty:
            return jsonify({"error": "혼잡도 정보 없음"}), 400
        congestion_score = float(score_row["혼잡도점수"].values[0])

        # 🔹 2. 날씨 상태 조회 (입력 날짜에서 가장 가까운 시간)
        weather_res = requests.get(WEATHER_URL)
        weather_data = weather_res.json()
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    
        weather_candidates = []

        for item in weather_data["list"]:
            dt = datetime.datetime.fromtimestamp(item["dt"])
            if dt.date() == target_date:
                if "main" in item and "temp" in item["main"]:
                    weather_candidates.append((
                        abs(dt.hour - 12),
                        item["weather"][0]["main"],
                        item["main"]["temp"]
                    ))

        if not weather_candidates:
            return jsonify({"error": f"{target_date} 날짜의 날씨 정보 없음"}), 400

        # 정오(12시)와 가장 가까운 시간 선택
        _, weather_status, temperature = sorted(weather_candidates, key=lambda x: x[0])[0]



        # 🔹 3. 인코딩
        le = label_encoders
        X = [
            le["측정시간"].transform([day])[0],
            le["구"].transform([gu])[0],
            congestion_score,
            le["MBTI"].transform([mbti])[0],
            le["날씨"].transform([weather_status])[0],
        ]
        X_tensor = torch.tensor([X], dtype=torch.float32)

        # 🔹 4. 예측
        with torch.no_grad():
            output = model(X_tensor)
            pred = output.argmax(dim=1).item()
            grade = le["등급"].inverse_transform([pred])[0]
            

        # 🔹 5. 지하철 혼잡도 분석
        station = data.get("station", "").strip()
        subway_row = df_subway[(df_subway["요일"] == day) & (df_subway["역명"] == station)]
        congestion_message = "혼잡도 정보 없음"
        if not subway_row.empty:
            # 시간대별 혼잡도 점수
            time_slots = ['새벽', '출근', '오전', '점심', '오후', '퇴근', '저녁', '심야']
            values = subway_row.iloc[0][time_slots].values.astype(float)

            min_idx = values.argmin()
            max_idx = values.argmax()

            congestion_message = (
                f"가장 한산한 시간대는 '{time_slots[min_idx]}', "
                f"가장 혼잡한 시간대는 '{time_slots[max_idx]}'입니다."
            )

        return jsonify({
            "grade": grade,
            "weather": weather_status,  # 예: "Clouds", "Clear", "Rain"
            "temperature": round(temperature, 1),  # 소수점 1자리
            "subway": congestion_message  # 🔹 지하철 혼잡도 결과
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400
@app.route("/stations")
def get_stations():
    try:
        # 지하철 CSV 로딩
        df_subway = pd.read_csv("지하철.csv")

        # 고유 역명 목록만 추출
        stations = df_subway["역명"].dropna().unique().tolist()
        return jsonify({"stations": stations})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
