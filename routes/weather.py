from flask import Blueprint, request, jsonify
from slack_sdk import WebClient
from datetime import datetime, timedelta
import pytz
import os
import requests

weather_bp = Blueprint("weather", __name__)
slack_token = os.environ["SLACK_BOT_TOKEN"]
service_key = os.environ["KMA_SERVICE_KEY"]
slack_client = WebClient(token=slack_token)

KST = pytz.timezone("Asia/Seoul")

LOCATION_GRID = {
    "서울": (60, 127), "부산": (98, 76), "대전": (67, 100), "광주": (58, 74), "제주": (52, 38),
    "대구": (89, 90), "인천": (55, 124), "울산": (102, 84), "수원": (60, 121), "춘천": (73, 134),
    "강릉": (92, 131), "청주": (69, 106), "전주": (63, 89), "포항": (102, 95), "창원": (91, 77),
    "학교": (59, 125), "제작자": (61, 126), "합숙": None
}

SKY_CODE = {"1": "맑음 ☀️", "3": "구름많음 ⛅", "4": "흐림 ☁️"}
PTY_CODE = {"0": "없음", "1": "비", "2": "비/눈", "3": "눈", "4": "소나기"}
CATEGORY_LABELS = {
    "T1H": "기온", "TMP": "기온", "RN1": "1시간 강수량", "PTY": "강수형태",
    "SKY": "하늘상태", "REH": "습도", "LGT": "낙뢰"
}

def get_forecast_time(keyword):
    now = datetime.now(KST)
    if keyword == "내일":
        return now.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=1)
    elif keyword == "모레":
        return now.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=2)
    else:
        rounded = now.replace(minute=0, second=0, microsecond=0)
        return rounded + timedelta(hours=1)

def get_base_time(api_type, target_time):
    now = datetime.now(KST)
    base_date = now.strftime("%Y%m%d")

    if api_type == "초단기":
        if now.hour == 0:
            base_date = (now - timedelta(days=1)).strftime("%Y%m%d")
            base_time = "2300"
        else:
            base_time = f"{now.hour - 1:02}00"
    else:
        hour = now.hour
        if 3 <= hour < 6:
            base_time = "0200"
        elif 6 <= hour < 9:
            base_time = "0500"
        elif 9 <= hour < 12:
            base_time = "0800"
        elif 12 <= hour < 15:
            base_time = "1100"
        elif 15 <= hour < 18:
            base_time = "1400"
        elif 18 <= hour < 21:
            base_time = "1700"
        elif 21 <= hour < 24:
            base_time = "2000"
        else:
            base_time = "2300"
    return base_time, base_date

def fetch_weather(api_type, nx, ny, target_time):
    base_time, base_date = get_base_time(api_type, target_time)
    endpoint = "getUltraSrtFcst" if api_type == "초단기" else "getVilageFcst"
    url = f"http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/{endpoint}"
    params = {
        "serviceKey": service_key,
        "numOfRows": 1000,
        "pageNo": 1,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny
    }
    try:
        res = requests.get(url, params=params)
        items = res.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])
    except:
        return None, "", ""

    fcst_target = target_time.strftime("%Y%m%d%H%M")
    data = {key: None for key in CATEGORY_LABELS.keys()}

    for item in items:
        fcst_time = item.get("fcstDate", "") + item.get("fcstTime", "")
        cat = item.get("category")
        if fcst_time == fcst_target and cat in data:
            data[cat] = item.get("fcstValue")

    temp = data.get("T1H")
    sky = SKY_CODE.get(data.get("SKY", ""), "")
    pty = PTY_CODE.get(data.get("PTY", ""), "")
    return temp, sky, pty

@weather_bp.route("/weather", methods=["POST"])
def weather():
    text = request.form.get("text", "").strip()
    channel_id = request.form.get("channel_id")
    user_id = request.form.get("user_id")
    parts = text.split()

    time_keyword = "지금"
    location = "학교"

    for part in parts:
        if part in ["지금", "내일", "모레"]:
            time_keyword = part
        elif part in LOCATION_GRID:
            location = part

    if LOCATION_GRID.get(location) is None:
        slack_client.chat_postMessage(channel=channel_id, text=f"🔍 `{location}` 위치는 현재 미정입니다.")
        return jsonify({"text": "위치 미정"})

    target_time = get_forecast_time(time_keyword)
    delta = target_time - datetime.now(KST)
    api_type = "초단기" if delta <= timedelta(hours=6) else "단기"

    nx, ny = LOCATION_GRID[location]
    temp, sky, pty = fetch_weather(api_type, nx, ny, target_time)

    date_str = target_time.strftime("%Y-%m-%d %H:%M")
    message = f"📍 {location}, {date_str} 기준\n- 기온: {temp}℃\n- 날씨: {sky}\n- 강수: {pty}\n(문의자: <@{user_id}>)"
    slack_client.chat_postMessage(channel=channel_id, text=message)

    return jsonify({"response_type": "in_channel"})
