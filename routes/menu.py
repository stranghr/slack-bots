from flask import Blueprint, request, jsonify
import json
import random
import os




menu_bp = Blueprint("menu", __name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")

def load_menu(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, encoding="utf-8") as f:
        return json.load(f)

lunch_items = load_menu("lunch_items.json")
dinner_items = load_menu("dinner_items.json")
anju_items = load_menu("anju_items.json")


@menu_bp.route("/lunch", methods=["POST"])
def lunch():
    text = request.form.get("text", "").strip().lower()

    if text:
        filtered = [item for item in lunch_items if text in [t.lower() for t in item["tags"]]]
        if not filtered:
            return jsonify({"text": f"❗ '{text}'에 해당하는 점심 메뉴가 없습니다."})
    else:
        filtered = lunch_items

    selected = random.choice(filtered)
    return jsonify({
        "text": f"🍱 오늘의 점심 추천: *{selected['name']}*" if text else f"🍱 태그 없이 전체 메뉴 중 추천된 점심: *{selected['name']}*"
    })


@menu_bp.route("/dinner", methods=["POST"])
def dinner():
    text = request.form.get("text", "").strip().lower()

    if text:
        filtered = [item for item in dinner_items if text in [t.lower() for t in item["tags"]]]
        if not filtered:
            return jsonify({"text": f"❗ '{text}'에 해당하는 저녁 메뉴가 없습니다."})
    else:
        filtered = dinner_items

    selected = random.choice(filtered)
    return jsonify({
        "text": f"🍽️ 오늘의 저녁 추천: *{selected['name']}*" if text else f"🍽️ 태그 없이 전체 메뉴 중 추천된 저녁: *{selected['name']}*"
    })


@menu_bp.route("/anju", methods=["POST"])
def anju():
    text = request.form.get("text", "").strip().lower()

    if text:
        filtered = [item for item in anju_items if text in [t.lower() for t in item["tags"]]]
        if not filtered:
            return jsonify({"text": f"❗ '{text}'에 해당하는 안주 메뉴가 없습니다."})
    else:
        filtered = anju_items

    selected = random.choice(filtered)
    return jsonify({
        "text": f"🍢 오늘의 안주 추천: *{selected['name']}*" if text else f"🍢 태그 없이 전체 메뉴 중 추천된 안주: *{selected['name']}*"
    })
