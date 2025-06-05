from flask import Flask, request, render_template, jsonify
from collections import defaultdict
import os
import json
from collections import defaultdict
app = Flask(__name__)

# 초기 가중치 저장소 (0.5 기본값)
male_pref = defaultdict(lambda: defaultdict(lambda: 0.5))
female_pref = defaultdict(lambda: defaultdict(lambda: 0.5))

# 기존 데이터가 있다면 로드
if os.path.exists("prefs_male.json"):
    with open("prefs_male.json") as f:
        male_data = json.load(f)
        for k1 in male_data:
            for k2 in male_data[k1]:
                male_pref[k1][k2] = male_data[k1][k2]

if os.path.exists("prefs_female.json"):
    with open("prefs_female.json") as f:
        female_data = json.load(f)
        for k1 in female_data:
            for k2 in female_data[k1]:
                female_pref[k1][k2] = female_data[k1][k2]

def update_pref(user_mbti, target_mbti, gender, sucess):
    """
    sucess: 1~5 정수 (1=최악, 5=최고)
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
    }[sucess]

    dyn_adj = base * (1 - abs(current - 0.5)) * adjustment_factor
    new_weight = current + dyn_adj
    prefs[user_mbti][target_mbti] = round(min(0.8, max(0.2, new_weight)), 3)

    # 저장
    def to_dict(d): return {k: dict(v) for k, v in d.items()}
    if gender == "MALE":
        with open("prefs_male.json", "w") as f:
            json.dump(to_dict(prefs), f, indent=2)
    else:
        with open("prefs_female.json", "w") as f:
            json.dump(to_dict(prefs), f, indent=2)



def get_pref(user_mbti, target_mbti, gender):
    prefs = male_pref if gender == "MALE" else female_pref
    return prefs[user_mbti][target_mbti]

def calculate_match_score(m1, g1, m2, g2):
    p1 = get_pref(m1, m2, g1)
    p2 = get_pref(m2, m1, g2)
    return round(min(p1, p2), 2)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        my_mbti = request.form.get("my_mbti")
        my_gender = request.form.get("my_gender")
        their_mbti = request.form.get("their_mbti")
        their_gender = request.form.get("their_gender")

        score = calculate_match_score(my_mbti, my_gender, their_mbti, their_gender)
        return render_template("index.html", score=score, show_result=True)

    return render_template("index.html", show_result=False)

@app.route("/feedback", methods=["POST"])
def feedback():
    my_mbti = request.form["my_mbti"]
    my_gender = request.form["my_gender"]
    their_mbti = request.form["their_mbti"]
    their_gender = request.form["their_gender"]
    feedback_score  = int(request.form["success"]) 

    # 양방향 가중치 업데이트
    update_pref(my_mbti, their_mbti, my_gender,  feedback_score )
    update_pref(their_mbti, my_mbti, their_gender,  feedback_score )

    return "<h3>피드백 감사합니다! 가중치가 반영되었습니다.</h3><a href='/'>← 돌아가기</a>"

if __name__ == "__main__":
    app.run(debug=True)
