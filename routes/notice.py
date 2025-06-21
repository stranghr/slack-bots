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

    # 1. 숫자만 들어오면 분 단위로 인식
    if re.fullmatch(r"\d{1,3}", input_str):
        minutes = int(input_str)
        return now + timedelta(minutes=minutes)

    # 2. HH:MM 형식
    if re.fullmatch(r"\d{1,2}:\d{2}", input_str):
        hour, minute = map(int, input_str.split(":"))
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target

    # 3. MMDDHHMM 형식
    if re.fullmatch(r"\d{8}", input_str):
        month = int(input_str[0:2])
        day = int(input_str[2:4])
        hour = int(input_str[4:6])
        minute = int(input_str[6:8])
        target = now.replace(month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target = target.replace(year=now.year + 1)  # 미래 기준
        return KST.localize(target)

    raise ValueError("지원되지 않는 시간 형식입니다.")

def send_scheduled_message(channel_id, message):
    slack_client.chat_postMessage(channel=channel_id, text=message)

def find_channel_by_partial_name(partial_name):
    try:
        response = slack_client.conversations_list(types="public_channel,private_channel", limit=1000)
        channels = response['channels']
        for ch in channels:
            if partial_name in ch['name']:  # 단순 포함 비교
                return ch['id']
    except Exception as e:
        print("채널 검색 오류:", e)
    return None



@noticesc_bp.route("/noticesc", methods=["POST"])
def schedule_notice():
    text = request.form.get("text", "").strip()
    user_channel = request.form.get("channel_id")
    user_id = request.form.get("user_id")

    try:
        parts = text.split(" ", 2)  # 채널 시간 메시지 or 시간 메시지

        if len(parts) < 2:
            return jsonify(response_type="ephemeral", text="⚠️ 형식: `/공지예약 [채널] [시간] [메시지]` 또는 `/공지예약 [시간] [메시지]`")

        # 채널이 포함되었는지 확인
        if len(parts) == 3:
            channel_input = parts[0].replace("#", "").replace("<", "").replace(">", "")
            time_str = parts[1]
            message = parts[2]

            channel_id = find_channel_by_partial_name(channel_input)
            if channel_id is None:
                return jsonify(response_type="ephemeral", text=f"⚠️ 채널 `{channel_input}` 을 찾을 수 없습니다.")
        else:
            channel_id = user_channel
            time_str = parts[0]
            message = parts[1]

        # 시간 파싱 및 미래 시간 보정
        try:
            # 시간 해석
            target_time = parse_smart_time(time_str)
        except ValueError as e:
            return jsonify(response_type="ephemeral", text=f"⚠️ 시간 형식 오류: {e}")

        # 예약 등록
        scheduler.add_job(
            send_scheduled_message,
            trigger="date",
            run_date=target_time,
            args=[channel_id, message]
        )

        formatted_time = target_time.strftime("%Y-%m-%d %H:%M")
        return jsonify(
            response_type="ephemeral",
            text=f"✅ {formatted_time} 에 공지 예약 완료 (채널: <#{channel_id}>)"
        )
    except Exception as e:
        return jsonify(response_type="ephemeral", text=f"⚠️ 예약 실패: {str(e)}")

__all__ = ["noticesc_bp"]