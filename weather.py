import os
import requests
from datetime import datetime, timezone, timedelta

# 환경 변수 로드
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_KEY = os.getenv("WEATHER_API_KEY")

# 울산 좌표 (OpenWeatherMap용)
LAT = 35.5384
LON = 129.3114
CITY_NAME = "Ulsan"

def get_weather_data():
    # 1. 현재 날씨 API
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&lang=kr"
    res = requests.get(url).json()
    
    # 2. 5일/3시간 단위 예보 API (오늘 하루 전체 최저/최고 기온 계산용)
    forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&lang=kr"
    forecast_res = requests.get(forecast_url).json()

    # 3. 미세먼지 API
    air_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={LAT}&lon={LON}&appid={API_KEY}"
    air_res = requests.get(air_url).json()

    return res, forecast_res, air_res

def format_message(current, forecast, air):
    # 시간 설정 (KST 기준)
    KST = timezone(timedelta(hours=9))
    now_kst = datetime.now(KST)
    date_str = now_kst.strftime("%Y-%m-%d (%A)")
    today_date_str = now_kst.strftime("%Y-%m-%d")
    time_str = now_kst.strftime("%a, %d %b %Y %H:%M:%S GMT")

    # 기본 정보 파싱
    weather_desc = current['weather'][0]['description']
    temp = current['main']['temp']
    
    # [수정] 오늘 하루 3시간 간격 예보 데이터에서 정확한 최저/최고 기온 추출
    today_temps = []
    for item in forecast.get('list', []):
        # 데이터의 UTC 시간을 KST로 변환하여 오늘 날짜에 해당하는 항목만 골라냄
        item_time_utc = datetime.fromtimestamp(item['dt'], timezone.utc)
        item_time_kst = item_time_utc.astimezone(KST)
        
        if item_time_kst.strftime("%Y-%m-%d") == today_date_str:
            today_temps.append(item['main']['temp_min'])
            today_temps.append(item['main']['temp_max'])
            # 각 시간대별 대표 기온도 포함해서 정확도 높임
            today_temps.append(item['main']['temp'])

    if today_temps:
        temp_min = min(today_temps)
        temp_max = max(today_temps)
    else:
        # 혹시 데이터가 없을 경우 현재 기온 기반 대체
        temp_min = current['main']['temp_min']
        temp_max = current['main']['temp_max']

    # 일출/일몰 시간 변환
    sunrise = datetime.fromtimestamp(current['sys']['sunrise'], KST).strftime("%H:%M")
    sunset = datetime.fromtimestamp(current['sys']['sunset'], KST).strftime("%H:%M")

    # 바람 및 대기
    pressure = current['main']['pressure']
    humidity = current['main']['humidity']
    wind_speed = current['wind']['speed']
    wind_deg = current['wind'].get('deg', 0)
    
    # 풍향 각도를 방위로 변환
    dirs = ["북풍", "북북동풍", "북동풍", "동북동풍", "동풍", "동남동풍", "남동풍", "남남동풍", 
            "남풍", "남남서풍", "남서풍", "서남서풍", "서풍", "서북서풍", "북서풍", "북북서풍"]
    wind_dir_str = dirs[int((wind_deg + 11.25) / 22.5) % 16]

    # 미세먼지 등급
    aqi = air['list'][0]['main']['aqi']
    aqi_text_map = {1: "좋음", 2: "양호", 3: "보통", 4: "나쁨", 5: "매우 나쁨"}
    dust_status = aqi_text_map.get(aqi, "보통")

    # 메시지 조합 (최저/최고 순서 반영)
    msg = f"""[Ulsan 오늘 날씨 ⛅]
{time_str}

📅 날짜: {date_str}
🌅 일출 : {sunrise}
🌇 일몰 : {sunset}
☁️ 현재 하늘 상태 : {weather_desc}

[🌡️ 기온 정보]
📍 현재 기온: {temp:.2f}°C
📊 오늘 최저/최고: {temp_min:.2f}°C / {temp_max:.2f}°C
🔄 어제와 비교: 📈 비슷해요

[🥪 아침/점심/저녁]
  🌅 아침 예보
  ☀️ 점심 예보
  🌙 저녁 예보

[🔬 바람과 바다]
🗜️ 기압 : {pressure} hPa
💧 대기습도 : {humidity} %
💨 풍속 : {wind_speed} m/s
🧭 풍향 : {wind_deg}° ({wind_dir_str})

😷 미세먼지: ({dust_status})"""

    return msg

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    cur, fore, air = get_weather_data()
    message = format_message(cur, fore, air)
    send_telegram(message)
