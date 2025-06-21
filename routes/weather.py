from flask import Blueprint, request, jsonify
from slack_sdk import WebClient
from datetime import datetime, timedelta
import pytz
import os
import requests
import logging

weather_bp = Blueprint("weather", __name__)
slack_token  = os.environ["SLACK_BOT_TOKEN"]
service_key  = os.environ["KMA_SERVICE_KEY"]
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

def get_forecast_time(keyword: str) -> datetime:
    now = datetime.now(KST)
    if keyword == "내일":
        return now.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=1)
    elif keyword == "모레":
        return now.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=2)
    else:
        # "지금": 다음 정시
        rounded = now.replace(minute=0, second=0, microsecond=0)
        return rounded + timedelta(hours=1)

def get_base_time(api_type: int) -> (str, str):
    now = datetime.now(KST)
    base_date = now.strftime("%Y%m%d")

    if api_type == 1:  # 초단기예보
        if now.hour == 0:
            base_date = (now - timedelta(days=1)).strftime("%Y%m%d")
            base_time = "2300"
        else:
            base_time = f"{now.hour - 1:02}00"
    else:  # 단기예보
        h = now.hour
        if h < 3:
            base_date = (now - timedelta(days=1)).strftime("%Y%m%d")
            base_time = "2300"
        elif h < 6:
            base_time = "0200"
        elif h < 9:
            base_time = "0500"
        elif h < 12:
            base_time = "0800"
        elif h < 15:
            base_time = "1100"
        elif h < 18:
            base_time = "1400"
        elif h < 21:
            base_time = "1700"
        else:
            base_time = "2000"

    return base_time, base_date

def fetch_weather(api_type: int, nx: int, ny: int, target_time: datetime):
    """
    Returns (temp, precip_mm, sky) or (None, None, None) on error.
    - 초단기: T1H, RN1, SKY
    - 단기  : TMP, PCP, SKY
    """
    base_time, base_date = get_base_time(api_type)

    # API URL differ by forecast type
    if api_type == 1:
        url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst"
    else:
        url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"

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
        res = requests.get(url, params=params, timeout=5)
        res.raise_for_status()
        data_json = res.json()
    except Exception:
        logging.exception("Weather API error")
        return None, None, None

    items = data_json.get("response", {}) \
                     .get("body", {}) \
                     .get("items", {}) \
                     .get("item", [])

    needed = ["T1H","RN1","SKY"] if api_type == 1 else ["TMP","PCP","SKY"]
    data = {cat: None for cat in needed}
    target_str = target_time.strftime("%Y%m%d%H%M")

    for item in items:
        if item.get("fcstDate","") + item.get("fcstTime","") == target_str:
            cat = item.get("category")
            if cat in data:
                data[cat] = item.get("fcstValue")

    if api_type == 1:
        temp   = data.get("T1H")
        precip = data.get("RN1")
    else:
        temp   = data.get("TMP")
        precip = data.get("PCP")

    sky = SKY_CODE.get(data.get("SKY") or "", "")
    return temp, precip, sky

@weather_bp.route("/weather", methods=["POST"])
def weather():
    text       = request.form.get("text", "").strip()
    channel_id = request.form.get("channel_id")
    user_id    = request.form.get("user_id")
    parts      = text.split()

    time_keyword = "지금"
    location     = "학교"
    for part in parts:
        if part in ["지금","내일","모레"]:
            time_keyword = part
        elif part in LOCATION_GRID:
            location = part

    if LOCATION_GRID.get(location) is None:
        slack_client.chat_postMessage(
            channel=channel_id,
            text=f"🔍 `{location}` 위치는 현재 미정입니다."
        )
        return jsonify({"text":"위치 미정"})

    try:
        target_time = get_forecast_time(time_keyword)
        delta       = target_time - datetime.now(KST)
        api_type    = 1 if delta <= timedelta(hours=6) else 2

        nx, ny = LOCATION_GRID[location]
        temp, precip, sky = fetch_weather(api_type, nx, ny, target_time)

        if temp is None and precip is None:
            raise RuntimeError("기상 API 응답이 올바르지 않습니다")

        date_str = target_time.strftime("%Y-%m-%d %H:%M")
        message = (
            f"📍 {location}, {date_str} 기준\n"
            f"- 기온: {temp}℃\n"
            f"- 하늘상태: {sky}\n"
            f"- 강수량: {precip}mm\n"
            f"(문의자: <@{user_id}>)"
        )
        slack_client.chat_postMessage(channel=channel_id, text=message)
        return jsonify({"response_type":"in_channel"})

    except Exception as e:
        reason = str(e)
        logging.exception("Error in /weather handler")
        slack_client.chat_postMessage(
            channel=channel_id,
            text=f"{reason} 오류가 발생해 */날씨*에 실패했습니다."
        )
        return jsonify({
            "response_type": "ephemeral",
            "text": f"{reason} 오류가 발생해 */날씨*에 실패했습니다."
        })
