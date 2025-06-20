from flask import Blueprint, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os

gongji_bp = Blueprint("gongji", __name__)

# 슬랙 클라이언트 초기화
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
client = WebClient(token=SLACK_BOT_TOKEN)

@gongji_bp.route("/gongji", methods=["POST"])
def gongjiFunc():
    text = request.form.get("text", "")
    user_id = request.form.get("user_id", "")
    user_name = request.form.get("user_name", "")

    try:
        parts = text.strip().split()
        if len(parts) < 2:
            return jsonify({"text": "❗ 형식 오류: `/공지 [채널명] [메시지내용]` 형식으로 입력하세요."})

        channel_name = parts[0].lstrip("#")
        message = " ".join(parts[1:])

        # 채널 ID 탐색
        response = client.conversations_list()
        channel_id = None
        matched_channel = None
        for ch in response["channels"]:
            if channel_name in ch["name"]:
                channel_id = ch["id"]
                matched_channel = ch["name"]
                break

        if not channel_id:
            return jsonify({"text": f"❗ 채널을 찾을 수 없습니다: `{channel_name}`"})

        # 메시지 구성
        formatted_message = f"<@{user_id}>: {message}"

        # 전송
        client.chat_postMessage(channel=channel_id, text=formatted_message)

        return jsonify({"text": f"✅ `#{matched_channel}` 채널에 공지를 보냈습니다."})

    except SlackApiError as e:
        reason = e.response["error"]
        if reason == "not_in_channel":
            return jsonify({"text": "❗ 봇이 해당 채널에 없습니다. `/invite @공지봇` 후 다시 시도하세요."})
        return jsonify({"text": f"Slack API 오류({reason})로 인해 공지 실패."})

    except Exception as e:
        return jsonify({"text": f"서버 오류: {str(e)}"})

__all__ = ["gongji_bp"]
