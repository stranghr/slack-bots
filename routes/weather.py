# weather.py
import os
import datetime
import requests
from flask import Blueprint, request, jsonify

weather_bp = Blueprint('weather', __name__)

# 사전 지정된 지역명→기상청 그리드 좌표 맵
LOCATION_MAP = {
    "학교": {"nx": 55, "ny": 127},
    "서울": {"nx": 60, "ny": 127},
    "부산": {"nx": 98, "ny": 76},
    # … 필요에 따라 추가
}

# 기상청 서비스 키는 환경 변수로 관리
SERVICE_KEY = os.environ["KMA_SERVICE_KEY"]

# 단기예보 발표 시각 리스트
RELEASE_TIMES = ["0200", "0500", "0800", "1100", "1400", "1700", "2000", "2300"]

def get_base_datetime(target_dt=None):
    """현재(또는 target_dt) 기준, 가장 최근 발표시각(base_time)과 날짜(base_date)를 반환."""
    if target_dt is None:
        target_dt = datetime.datetime.now()
    hhmm = target_dt.strftime("%H%M")
    datestr = target_dt.strftime("%Y%m%d")
    past = [t for t in RELEASE_TIMES if t <= hhmm]
    if not past:
        # 02시 이전이면 전날 23시 발표 사용
        prev_date = (target_dt - datetime.timedelta(days=1)).strftime("%Y%m%d")
        return prev_date, "2300"
    return datestr, past[-1]

def call_short_term_forecast(base_date, base_time, nx, ny):
    """기상청 단기예보 API 호출 (getVilageFcst)."""
    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
    params = {
        "serviceKey": SERVICE_KEY,
        "pageNo": "1",
        "numOfRows": "1000",
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": str(nx),
        "ny": str(ny),
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json()

def extract_weather(json_data, fcst_date, fcst_time):
    """예보 데이터에서 기온(TMP)과 하늘상태(SKY)를 추출."""
    items = json_data['response']['body']['items']['item']
    tmp = next((i['fcstValue'] for i in items
                if i['category']=="TMP" and i['fcstDate']==fcst_date and i['fcstTime']==fcst_time), None)
    sky_code = next((i['fcstValue'] for i in items
                     if i['category']=="SKY" and i['fcstDate']==fcst_date and i['fcstTime']==fcst_time), None)
    sky_map = {"1":"맑음", "3":"구름많음", "4":"흐림"}
    return tmp, sky_map.get(sky_code, "알수없음")

@weather_bp.route("/weather", methods=["POST"])
def slack_weather():
    text = request.form.get("text", "").strip()
    now = datetime.datetime.now()

    # 기본 처리
    if text == "":
        loc, when = "학교", "오늘"
        fcst_dt = now
    elif text in ("내일", "모레"):
        days = {"내일":1, "모레":2}[text]
        loc, when = "학교", text
        fcst_dt = now + datetime.timedelta(days=days)
    elif text in LOCATION_MAP:
        loc, when = text, "오늘"
        fcst_dt = now
    else:
        return jsonify(
            response_type="ephemeral",
            text=f"지원하지 않는 입력입니다: `{text}`\n사용법: `/날씨 [지역명|내일|모레]`"
        )

    base_date, base_time = get_base_datetime(now)
    fcst_date = fcst_dt.strftime("%Y%m%d")

    # 조회 시각 결정
    if when == "오늘":
        fcst_time = fcst_dt.strftime("%H00")
    else:
        fcst_time = "1400"

    coords = LOCATION_MAP[loc]
    data = call_short_term_forecast(base_date, base_time, coords["nx"], coords["ny"])
    tmp, sky = extract_weather(data, fcst_date, fcst_time)

    message = (
        f"*{loc} {when} {fcst_time}시 예보*\n"
        f"> 기온: {tmp}℃\n"
        f"> 날씨: {sky}"
    )
    return jsonify(response_type="in_channel", text=message)
