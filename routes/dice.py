from flask import Blueprint, request, jsonify
import random
import re


dice_bp = Blueprint("dice", __name__)
soju_bp = Blueprint("soju", __name__)  

@soju_bp.route("/soju", methods=["POST"])
def recommend_drink():
    try:
        alcohol_options = ["소주", "맥주", "소맥", "막걸리", "와인", "칵테일"]
        weights = [40, 25, 15, 10, 7, 3]

        selected = random.choices(alcohol_options, weights=weights, k=1)[0]
        return jsonify({
            "response_type": "in_channel",
            "text": f"🍶 오늘의 주종 추천: *{selected}*"
        })
    except Exception as e:
        return jsonify({"text": f"⚠️ 오류 발생: {str(e)}"})


@dice_bp.route("/dice", methods=["POST"])
def roll_dice():
    text = request.form.get("text", "").strip()

    try:
        # 기본값: 1~6
        low, high = 1, 6

        # 사용자가 범위를 입력한 경우 처리
        if text:
            match = re.match(r"(\d+)\s*-\s*(\d+)", text)
            if match:
                low, high = int(match.group(1)), int(match.group(2))
                if low >= high or high - low > 1000000:
                    return jsonify({"text": "❗ 유효한 범위 (예: 1-100)를 입력하세요."})
            else:
                return jsonify({"text": "❗ 범위는 '1-100'처럼 입력해야 합니다."})

        result = random.randint(low, high)
        return jsonify({
            "response_type": "in_channel",
            "text": f"🎲 주사위 굴림 결과: *{low} ~ {high} ➜ {result}*"
        })

    except Exception as e:
        return jsonify({"text": f"⚠️ 오류 발생: {str(e)}"})

__all__ = ["dice_bp", "soju_bp"]