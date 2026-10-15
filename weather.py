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
    
    # 2. 5일/3시간 단위 예보 API (최저/최고 기온 및 시간대별 예보용)
    forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&lang=kr"
    forecast_res = requests.get(forecast_url).json()

    # 3. 미세먼지 API
    air_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={LAT}&lon={LON}&appid={API_KEY}"
    air_res = requests.get(air_url).json()

    return res, forecast_res, air_res

def get_detailed_time_forecast(forecast_list, target_hour):
    """지정한 시간대와 가장 가까운 예보를 찾아 기온, 체감온도, 하늘상태, 강수확률 및 가이드를 반환"""
    KST = timezone(timedelta(hours=9))
    today_str = datetime.now(KST).strftime("%Y-%m-%d")
    
    selected_item = None
    min_diff = 999
    
    for item in forecast_list:
        item_time = datetime.fromtimestamp(item['dt'], timezone.utc).astimezone(KST)
        if item_time.strftime("%Y-%m-%d") == today_str:
            diff = abs(item_time.hour - target_hour)
            if diff < min_diff:
                min_diff = diff
                selected_item = item

    if not selected_item:
        return "정보 없음"

    temp = selected_item['main']['temp']
    feels_like = selected_item['main']['feels_like']
    pop = int(selected_item.get('pop', 0) * 100)
    sky = selected_item['weather'][0]['main']
    
    # 날씨 이모지
    icon = "☀️" if sky == "Clear" else "☁️" if sky == "Clouds" else "🌧️" if sky == "Rain" else "⛅"
    
    # 행동 가이드 팁
    tip = ""
    if pop >= 60 or sky == "Rain":
        tip = " — 🌂 우산 필수"
    elif temp < 15:
        tip = " — 🧥 겉옷 챙기세요"
    elif temp > 26:
        tip = " — 🕶️ 더위 주의"
    else:
        tip = " — ✨ 활동하기 좋아요"

    return f"{icon} {temp:.1f}°C (체감 {feels_like:.1f}°C) | 강수 {pop}%{tip}"

def get_rain_summary(forecast_list):
    """오늘 하루 중 비가 오는 시간대와 예상 강우량을 요약"""
    KST = timezone(timedelta(hours=9))
    today_str = datetime.now(KST).strftime("%Y-%m-%d")
    
    rain_slots = []
    total_rain = 0.0
    
    for item in forecast_list:
        item_time_utc = datetime.fromtimestamp(item['dt'], timezone.utc)
        item_time_kst = item_time_utc.astimezone(KST)
        
        if item_time_kst.strftime("%Y-%m-%d") == today_str:
            sky = item['weather'][0]['main']
            rain_vol = item.get('rain', {}).get('3h', 0.0)
            pop = int(item.get('pop', 0) * 100)
            
            # 비가 오거나 강수 확률이 50% 이상인 경우 포착
            if sky == "Rain" or rain_vol > 0 or pop >= 50:
                time_label = item_time_kst.strftime("%H시")
                rain_slots.append(f"{time_label}({pop}%)")
                total_rain += rain_vol

    if not rain_slots:
        return "✨ 오늘 비 소식 없음 (맑음)"
    
    time_str_res = ", ".join(rain_slots)
    # 강수량 측정값이 0이지만 확률이 높은 경우 보정
    rain_display = f"{total_rain:.1f}mm 내외" if total_rain > 0 else "약한 이슬비 또는 흐림"
    
    return f"🌧️ 시간대: {time_str_res}\n💧 예상 강우량: {rain_display}"

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
    
    # 오늘 하루 최저/최고 기온 추출
    today_temps = []
    for item in forecast.get('list', []):
        item_time_utc = datetime.fromtimestamp(item['dt'], timezone.utc)
        item_time_kst = item_time_utc.astimezone(KST)
        
        if item_time_kst.strftime("%Y-%m-%d") == today_date_str:
            today_temps.append(item['main']['temp_min'])
            today_temps.append(item['main']['temp_max'])
            today_temps.append(item['main']['temp'])

    if today_temps:
        temp_min = min(today_temps)
        temp_max = max(today_temps)
    else:
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

    # 시간대별 상세 정보 생성 (아침 8시, 점심 13시, 저녁 18시 기준)
    morning_info = get_detailed_time_forecast(forecast.get('list', []), 8)
    noon_info = get_detailed_time_forecast(forecast.get('list', []), 13)
    evening_info = get_detailed_time_forecast(forecast.get('list', []), 18)

    # 우천 정보 요약 생성
    rain_summary = get_rain_summary(forecast.get('list', []))

    # 최종 메시지 조합
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

[☔ 우천 정보]
{rain_summary}

[🥪 아침/점심/저녁]
  🌅 아침: {morning_info}
  ☀️ 점심: {noon_info}
  🌙 저녁: {evening_info}

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
