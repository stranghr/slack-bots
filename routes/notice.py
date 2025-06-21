from flask import Blueprint, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from slack_sdk import WebClient
from datetime import datetime, timedelta
import pytz
import os
import re

noticesc_bp = Blueprint("notice", __name__)
scheduler = BackgroundScheduler()
scheduler.start()

slack_token = os.environ["SLACK_BOT_TOKEN"]
slack_client = WebClient(token=slack_token)

KST = pytz.timezone("Asia/Seoul")

def parse_smart_time(input_str: str) -> datetime:
    now = datetime.now(KST)

    if re.fullmatch(r"\d{1,3}", input_str):
        minutes = int(input_str)
        return now + timedelta(minutes=minutes)

    if re.fullmatch(r"\d{1,2}:\d{2}", input_str):
        hour, minute = map(int, input_str.split(":"))
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target

    if re.fullmatch(r"\d{8}", input_str):
        month = int(input_str[0:2])
        day = int(input_str[2:4])
        hour = int(input_str[4:6])
        minute = int(input_str[6:8])
        target = now.replace(month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target = target.replace(year=now.year + 1)
        return KST.localize(target)

    raise ValueError("지원되지 않는 시간 형식입니다.")

def send_scheduled_message(channel_id, message):
    slack_client.chat_postMessage(channel=channel_id, text=message)

def find_channel_by_partial_name(partial_name):
    try:
        response = slack_client.conversations_list()
        channel_id = None
        matched_channel = None
        for ch in response["channels"]:
            if partial_name in ch["name"]:
                channel_id = ch["id"]
                matched_channel = ch["name"]
                return matched_channel, channel_id
                break

        if not channel_id:
            return jsonify({"text": f"❗ 채널을 찾을 수 없습니다: `{partial_name}`"})

    except Exception as e:
        print("채널 검색 오류:", e)
    return None

@noticesc_bp.route("/noticesc", methods=["POST"])
def schedule_notice():
    text = request.form.get("text", "").strip()
    user_channel = request.form.get("channel_id")

    try:
        parts = text.split(" ", 2)

        if len(parts) < 2:
            return jsonify(response_type="ephemeral", text="❗ 형식 오류: `/예약공지 [시간] [메시지]` 또는 `/예약공지 [채널명] [시간] [메시지]`")

        # case 1: 채널명 + 시간 + 메시지
        if len(parts) == 3 and re.fullmatch(r"\d{1,3}|\d{1,2}:\d{2}|\d{8}", parts[1]):
            channel_input = parts[0].lstrip("#")
            time_str = parts[1]
            message = " ".join(parts[1:])

            mached_channel, channel_id = find_channel_by_partial_name(channel_input)
            if channel_id is None:
                return jsonify(response_type="ephemeral", text=f"❗ 채널 `{channel_input}` 을 찾을 수 없습니다.")
        else:
            # case 2: 시간 + 메시지 (현재 채널)
            time_str = parts[0]
            message = " ".join(parts[1:])
            channel_id = user_channel

        try:
            target_time = parse_smart_time(time_str)
        except ValueError as e:
            return jsonify(response_type="ephemeral", text=f"❗ 시간 형식 오류: {e}")

        scheduler.add_job(
            send_scheduled_message,
            trigger="date",
            run_date=target_time,
            args=[channel_id, message]
        )

        formatted_time = target_time.strftime("%Y-%m-%d %H:%M")
        return jsonify(
            response_type="ephemeral",
            text=f"✅ {formatted_time} 에 공지 예약 완료 (채널: <{mached_channel}>)"
        )

    except Exception as e:
        return jsonify(response_type="ephemeral", text=f"❗ 예약 실패: {str(e)}")

__all__ = ["noticesc_bp"]
