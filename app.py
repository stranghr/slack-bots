from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os
import random
import json
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)

# 여기에 당신의 Bot Token을 넣어주세요 (보안상 .env로 관리하는 것이 좋음)
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")  # <-- 여기에 당신 토큰 입력
client = WebClient(token=SLACK_BOT_TOKEN)

@app.route("/gongji-debug", methods=["POST"])
def gongji_debug():
    text = request.form.get("text", "")
    user_id = request.form.get("user_id", "")
    user_name = request.form.get("user_name", "")
    channel_id = request.form.get("channel_id", "")
    channel_name = request.form.get("channel_name", "")
    team_id = request.form.get("team_id", "")

    print("====== [DEBUG: /gongji-debug 요청 수신] ======")
    print(f"text: {text}")
    print(f"user_id: {user_id}")
    print(f"user_name: {user_name}")
    print(f"channel_id: {channel_id}")
    print(f"channel_name: {channel_name}")
    print(f"team_id: {team_id}")
    print("=============================================")

    return jsonify({"text": f"✅ 디버깅 성공! text='{text}', user={user_name}"}), 200

@app.route("/gongji", methods=["POST"])
def gongji():
    text = request.form.get("text", "")
    user_id = request.form.get("user_id", "")  # 멘션용
    user_name = request.form.get("user_name", "")  # 로그 또는 디버그용

    try:
        # 채널명과 메시지 분리
        parts = text.strip().split()
        if len(parts) < 2:
            return jsonify({"text": "❗ 형식 오류: `/공지 [채널명] [메시지내용]` 형식으로 입력하세요."})

        channel_name = parts[0].lstrip("#")
        message = " ".join(parts[1:])

        # 채널 ID 찾기
        response = client.conversations_list()
        channel_id = None
        matched_channel = None
        for ch in response["channels"]:
            if channel_name in ch["name"]:
                channel_id = ch["id"]
                matched_channel = ch["name"]
                break
        
        if not channel_id:
            return jsonify({"text": f"❗ 입력한 채널 이름에 해당하는 채널을 찾을 수 없습니다: `{channel_name}`"})

        # 메시지 작성: @user_id: 메시지
        formatted_message = f"<@{user_id}>: {message}"

        # 메시지 작성: @user_id: 메시지
        formatted_message = f"<@{user_id}>: {message}"

        # 메시지 작성: @user_id: 메시지
        formatted_message = f"<@{user_id}>: {message}"

        # 메시지 전송
        client.chat_postMessage(channel=channel_id, text=formatted_message)
        return jsonify({"text": f"✅ `#{matched_channel}` 채널에 공지를 보냈습니다."})

        # 메시지 전송
        client.chat_postMessage(channel=channel_id, text=message)
        return jsonify({"text": f"✅ `#{channel_name}` 채널에 공지를 보냈습니다: \"{message}\""})

    except SlackApiError as e:
        reason = e.response["error"]
        if reason == "not_in_channel":
            return jsonify({"text": "❗ 봇이 해당 채널에 초대되어 있지 않습니다. `/invite @공지봇`으로 초대한 후 다시 시도하세요."})
        return jsonify({"text": f"Slack API 오류({reason})로 인해 */공지*에 실패했습니다."})
    except Exception as e:
        return jsonify({"text": f"서버 오류: {str(e)}"})

def load_menu(filename):
    with open(filename, encoding="utf-8") as f:
        return json.load(f)

lunch_items = load_menu("lunch_items.json")
dinner_items = load_menu("dinner_items.json")
anju_items = load_menu("anju_items.json")


@app.route("/lunch", methods=["POST"])
def lunch():
    text = request.form.get("text", "").strip()  # 예: "한식" 또는 ""
    keyword = text.lower()

    # 필터링
    if keyword:
        filtered = [item for item in lunch_items if keyword in [t.lower() for t in item["tags"]]]
    else:
        filtered = lunch_items

    if not filtered:
        return jsonify({"text": f"❗ '{text}'에 해당하는 점심 메뉴가 없습니다."})

    selected = random.choice(filtered)
    return jsonify({"text": f"🍱 오늘의 점심 추천: *{selected['name']}*"})


@app.route("/dinner", methods=["POST"])
def dinner():
    text = request.form.get("text", "").strip()
    keyword = text.lower()

    if keyword:
        filtered = [item for item in dinner_items if keyword in [t.lower() for t in item["tags"]]]
    else:
        filtered = dinner_items

    if not filtered:
        return jsonify({"text": f"❗ '{text}'에 해당하는 저녁 메뉴가 없습니다."})

    selected = random.choice(filtered)
    return jsonify({"text": f"🍽️ 오늘의 저녁 추천: *{selected['name']}*"})


@app.route("/anju", methods=["POST"])
def anju():
    text = request.form.get("text", "").strip()
    keyword = text.lower()

    if keyword:
        filtered = [item for item in dinner_items if keyword in [t.lower() for t in item["tags"]]]
    else:
        filtered = dinner_items

    if not filtered:
        return jsonify({"text": f"❗ '{text}'에 해당하는 안주 메뉴가 없습니다."})

    selected = random.choice(filtered)
    return jsonify({"text": f"🍽️ 오늘의 술안주 추천: *{selected['name']}*"})

@app.route("/soju", methods=["POST"])
def joojong():
    try:
        alcohol_options = ["소주", "맥주", "소맥", "막걸리", "와인", "칵테일"]
        weights = [40, 25, 15, 10, 7, 3]  # 확률 가중치 (합계 100)

        selected = random.choices(alcohol_options, weights=weights, k=1)[0]

        return jsonify({
            "response_type": "in_channel",
            "text": f"🍶 오늘의 주종 추천은: *{selected}* 입니다!"
        })

    except Exception as e:
        return jsonify({"text": f"⚠️ 서버 오류: {str(e)}"})


if __name__ == "__main__":

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

    app.run(port=5000)

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

