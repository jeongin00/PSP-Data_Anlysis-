from flask import Flask, request, jsonify, render_template
import pandas as pd
import torch
import torch.nn as nn
import joblib
import requests
import datetime
from model import MLP
from collections import defaultdict
import os
import json

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

# MBTI 관련 초기화
male_pref = defaultdict(lambda: defaultdict(lambda: 0.5))
female_pref = defaultdict(lambda: defaultdict(lambda: 0.5))

# 기존 MBTI 데이터가 있다면 로드
if os.path.exists("mbti/prefs_male.json"):
    with open("mbti/prefs_male.json") as f:
        male_data = json.load(f)
        for k1 in male_data:
            for k2 in male_data[k1]:
                male_pref[k1][k2] = male_data[k1][k2]

if os.path.exists("mbti/prefs_female.json"):
    with open("mbti/prefs_female.json") as f:
        female_data = json.load(f)
        for k1 in female_data:
            for k2 in female_data[k1]:
                female_pref[k1][k2] = female_data[k1][k2]

def update_pref(user_mbti, target_mbti, gender, success):
    """
    success: 1~5 정수 (1=최악, 5=최고)
    """
    prefs = male_pref if gender == "MALE" else female_pref
    base = 0.1
    current = prefs[user_mbti][target_mbti]

    # 변화율 계산
    adjustment_factor = {
        5: +1.0,
        4: +0.5,
        3: 0.0,
        2: -0.5,
        1: -1.0
    }[success]

    dyn_adj = base * (1 - abs(current - 0.5)) * adjustment_factor
    new_weight = current + dyn_adj
    prefs[user_mbti][target_mbti] = round(min(0.8, max(0.2, new_weight)), 3)

    # 저장
    def to_dict(d): return {k: dict(v) for k, v in d.items()}
    if gender == "MALE":
        with open("mbti/prefs_male.json", "w") as f:
            json.dump(to_dict(prefs), f, indent=2)
    else:
        with open("mbti/prefs_female.json", "w") as f:
            json.dump(to_dict(prefs), f, indent=2)

def get_pref(user_mbti, target_mbti, gender):
    prefs = male_pref if gender == "MALE" else female_pref
    return prefs[user_mbti][target_mbti]

def calculate_match_success(m1, g1, m2, g2):
    p1 = get_pref(m1, m2, g1)
    p2 = get_pref(m2, m1, g2)
    return round(min(p1, p2), 2)

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
            
        return jsonify({
            "grade": grade,
            "weather": weather_status,  # 예: "Clouds", "Clear", "Rain"
            "temperature": round(temperature, 1),  # 소수점 1자리
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

@app.route("/congestion", methods=["POST"])
def congestion():
    data = request.get_json()
    station = (data.get("station") or "").strip()
    day = data.get("day")

    df = pd.read_csv("지하철.csv")
    row = df[(df["역명"] == station) & (df["요일"] == day)]

    if row.empty:
        return jsonify({"message": "혼잡도 정보 없음"})

    time_slots = ['6시이전', '06~09시', '09~12시', '12~13시', '13~16시', '16~19시', '19~22시', '22~24시']
    values = row.iloc[0][time_slots].values.astype(float)
    min_idx, max_idx = values.argmin(), values.argmax()

    return jsonify({
        "message": f"가장 한산한 시간대는 '{time_slots[min_idx]}', 가장 혼잡한 시간대는 '{time_slots[max_idx]}'입니다."
    })

@app.route("/mbti", methods=["GET", "POST"])
def mbti_match():
    if request.method == "POST":
        my_mbti = request.form.get("my_mbti")
        my_gender = request.form.get("my_gender")
        their_mbti = request.form.get("their_mbti")
        their_gender = request.form.get("their_gender")

        success = calculate_match_success(my_mbti, my_gender, their_mbti, their_gender)
        return render_template(
            "index.html",
            mbti_success=success,
            show_mbti_result=True,
            my_mbti=my_mbti,
            my_gender=my_gender,
            their_mbti=their_mbti,
            their_gender=their_gender
        )
    return render_template(
        "index.html",
        mbti_success=None,
        show_mbti_result=False,
        my_mbti="",
        my_gender="",
        their_mbti="",
        their_gender=""
    )

@app.route("/mbti/feedback", methods=["POST"])
def mbti_feedback():
    my_mbti = request.form["my_mbti"]
    my_gender = request.form["my_gender"]
    their_mbti = request.form["their_mbti"]
    their_gender = request.form["their_gender"]
    feedback_success = int(request.form["success"])

    # 양방향 가중치 업데이트
    update_pref(my_mbti, their_mbti, my_gender, feedback_success)
    update_pref(their_mbti, my_mbti, their_gender, feedback_success)

    return "<h3>피드백 감사합니다! 가중치가 반영되었습니다.</h3><a href='/'>← 돌아가기</a>"

if __name__ == "__main__":
    app.run(debug=True, port=5001)
