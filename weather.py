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
    # 1. 현재 날씨 및 예보 API 호출 (One Call API 3.0 또는 2.5 기준)
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&lang=kr"
    res = requests.get(url).json()
    
    # 추가 상세 예보를 위한 5일/3시간 예보 API 호출
    forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&lang=kr"
    forecast_res = requests.get(forecast_url).json()

    # 미세먼지 API 호출
    air_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={LAT}&lon={LON}&appid={API_KEY}"
    air_res = requests.get(air_url).json()

    return res, forecast_res, air_res

def format_message(current, forecast, air):
    # 시간 설정 (KST 기준)
    KST = timezone(timedelta(hours=9))
    now_kst = datetime.now(KST)
    date_str = now_kst.strftime("%Y-%m-%d (%A)")
    time_str = now_kst.strftime("%a, %d %b %Y %H:%M:%S GMT") # 이미지 스타일 맞춤

    # 기본 정보 파싱
    weather_desc = current['weather'][0]['description']
    temp = current['main']['temp']
    temp_max = current['main']['temp_max']
    temp_min = current['main']['temp_min']
    
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

    # 미세먼지 등급 (AQI 1: 좋음, 2: 양호, 3: 보통, 4: 나쁨, 5: 매우 나쁨)
    aqi = air['list'][0]['main']['aqi']
    aqi_text_map = {1: "좋음", 2: "양호", 3: "보통", 4: "나쁨", 5: "매우 나쁨"}
    dust_status = aqi_text_map.get(aqi, "보통")

    # 메시지 조합 (보내주신 이미지 레이아웃 반영)
    msg = f"""[Ulsan 오늘 날씨 ⛅]
{time_str}

📅 날짜: {date_str}
🌅 일출 : {sunrise}
🌇 일몰 : {sunset}
☁️ 현재 하늘 상태 : {weather_desc}

[🌡️ 기온 정보]
📍 현재 기온: {temp:.2f}°C
📊 최고/최저: {temp_max:.2f}°C / {temp_min:.2f}°C
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
    url = f"https://api.org/bot{TOKEN}/sendMessage" if False else f"https://api.telegram.org/bot{TOKEN}/sendMessage"
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
