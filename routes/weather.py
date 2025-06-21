from flask import Blueprint, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from slack_sdk import WebClient
from datetime import datetime, timedelta
import pytz
import os
import re
import requests
import xml.etree.ElementTree as ET

weather_bp = Blueprint("weather", __name__)
scheduler = BackgroundScheduler()
scheduler.start()

slack_token = os.environ["SLACK_BOT_TOKEN"]
service_key = os.environ["KMA_SERVICE_KEY"]  # 기상청 API 키
slack_client = WebClient(token=slack_token)

KST = pytz.timezone("Asia/Seoul")

# 장소명 → 격자 좌표
LOCATION_GRID = {
    "서울": (60, 127),
    "부산": (98, 76),
    "대전": (67, 100),
    "광주": (58, 74),
    "제주": (52, 38),
    "대구": (89, 90),
    "인천": (55, 124),
    "울산": (102, 84),
    "수원": (60, 121),
    "춘천": (73, 134),
    "강릉": (92, 131),
    "청주": (69, 106),
    "전주": (63, 89),
    "포항": (102, 95),
    "창원": (91, 77),
    "학교": (59, 125),  # 관악구 (예시)
    "제작자": (61, 126),  # 강남구 (예시)
    "합숙": None  # 미정 처리
}

# 시간 표현 해석 → datetime 객체

def parse_time_expression(text):
    now = datetime.now(KST)
    text = text.replace("시", ":")  # '18시' → '18:'

    if match := re.fullmatch(r"(\d{1,3})분", text):
        return now + timedelta(minutes=int(match.group(1)))
    elif match := re.fullmatch(r"(\d{1,2})시간", text):
        return now + timedelta(hours=int(match.group(1)))
    elif text == "내일":
        return now.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=1)
    elif text == "모레":
        return now.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=2)
    elif match := re.fullmatch(r"(\d{8})", text):
        return datetime.strptime(match.group(1), "%Y%m%d").replace(tzinfo=KST, hour=12)
    elif match := re.fullmatch(r"(\d{4})", text):
        year = now.year
        return datetime.strptime(f"{year}{match.group(1)}", "%Y%m%d").replace(tzinfo=KST, hour=12)
    elif match := re.fullmatch(r"(\d{2}):(\d{2})", text):
        hour, minute = match.groups()
        return now.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
    elif match := re.fullmatch(r"(\d{1,2})일", text):
        return now.replace(day=int(match.group(1)), hour=12, minute=0, second=0, microsecond=0)
    elif match := re.fullmatch(r"(\d{1,2})일(\d{2})", text):
        return now.replace(day=int(match.group(1)), hour=int(match.group(2)), minute=0, second=0, microsecond=0)
    elif match := re.fullmatch(r"(\d{1,2})일(\d{2}):(\d{2})", text):
        return now.replace(day=int(match.group(1)), hour=int(match.group(2)), minute=int(match.group(3)), second=0, microsecond=0)
    else:
        raise ValueError("지원하지 않는 시간 형식입니다.")

# 예보 API 선택
def select_api(target_time):
    now = datetime.now(KST)
    delta = target_time - now
    if delta.total_seconds() < 0:
        return None
    elif delta <= timedelta(hours=6):
        return "초단기"
    elif delta <= timedelta(days=3):
        return "단기"
    else:
        return None

# 기상청 API 요청
CATEGORY_LABELS = {
    "T1H": "기온", "TMP": "기온",
    "PTY": "강수형태", "SKY": "하늘상태"
}
SKY_CODE = {"1": "맑음 ☀️", "3": "구름많음 ⛅", "4": "흐림 ☁️"}
PTY_CODE = {"0": "없음", "1": "비", "2": "비/눈", "3": "눈", "4": "소나기"}

def fetch_weather(api_type, nx, ny, target_time):
    def get_base_time(target_time):
        if api_type == "초단기":
            base_minute = 30 if target_time.minute >= 30 else 0
            base_time_dt = target_time.replace(minute=base_minute, second=0, microsecond=0) - timedelta(minutes=40)
            return base_time_dt.strftime("%H%M"), base_time_dt
        else:
            candidate_hours = [2, 5, 8, 11, 14, 17, 20, 23]
            selected_hour = max([h for h in candidate_hours if h <= target_time.hour], default=23)
            base_time_dt = target_time.replace(hour=selected_hour, minute=0, second=0, microsecond=0)
            if target_time < base_time_dt + timedelta(minutes=10):
                selected_hour = max([h for h in candidate_hours if h < selected_hour], default=23)
                base_time_dt = base_time_dt.replace(hour=selected_hour)
            return base_time_dt.strftime("%H%M"), base_time_dt

    base_date = target_time.strftime("%Y%m%d")
    base_time, base_time_dt = get_base_time(target_time)

    url_base = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/"
    endpoint = "getUltraSrtFcst" if api_type == "초단기" else "getVilageFcst"
    url = url_base + endpoint
    params = {
        "serviceKey": service_key,
        "numOfRows": 100,
        "pageNo": 1,
        "dataType": "XML",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny
    }

    res = requests.get(url, params=params)
    root = ET.fromstring(res.content)
    items = root.findall(".//item")

    data = {cat: None for cat in ["T1H", "TMP", "SKY", "PTY"]}
    nearest_diff = timedelta.max
    fallback_data = {}

    for item in items:
        fcst_date = item.findtext("fcstDate")
        fcst_time = item.findtext("fcstTime")
        cat = item.findtext("category")
        value = item.findtext("fcstValue")
        if not (fcst_date and fcst_time and cat in data):
            continue

        fcst_dt = datetime.strptime(fcst_date + fcst_time, "%Y%m%d%H%M").replace(tzinfo=KST)
        diff = abs(fcst_dt - target_time)
        if diff < nearest_diff:
            nearest_diff = diff
            fallback_data[cat] = value

        if fcst_dt == target_time:
            data[cat] = value

    for k in data:
        if data[k] is None and fallback_data.get(k):
            data[k] = fallback_data[k]

    temp = data.get("T1H") or data.get("TMP")
    sky = SKY_CODE.get(data.get("SKY", ""), "")
    pty = PTY_CODE.get(data.get("PTY", ""), "")

    return temp, sky, pty
