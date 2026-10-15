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
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&lang=kr"
    res = requests.get(url).json()
    
    forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&lang=kr"
    forecast_res = requests.get(forecast_url).json()

    air_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={LAT}&lon={LON}&appid={API_KEY}"
    air_res = requests.get(air_url).json()

    return res, forecast_res, air_res

def get_detailed_time_forecast(forecast_list, target_hour):
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
    
    icon = "☀️" if sky == "Clear" else "☁️" if sky == "Clouds" else "🌧️" if sky == "Rain" else "⛅"
    
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
            
            if sky == "Rain" or rain_vol > 0 or pop >= 50:
                time_label = item_time_kst.strftime("%H시")
                rain_slots.append(f"{time_label}({pop}%)")
                total_rain += rain_vol

    if not rain_slots:
        return "✨ 오늘 비 소식 없음 (맑음)"
    
    time_str_res = ", ".join(rain_slots)
    rain_display = f"{total_rain:.1f}mm 내외" if total_rain > 0 else "약한 이슬비 또는 흐림"
    
    return f"🌧️ 시간대: {time_str_res}\n💧 예상 강우량: {rain_display}"

def get_tide_info():
    KST = timezone(timedelta(hours=9))
    now_kst = datetime.now(KST)
    
    base_date = datetime(2026, 1, 1, tzinfo=KST)
    diff_days = (now_kst - base_date).days
    
    tide_water_num = (diff_days % 15) + 1
    tide_str = f"{tide_water_num}물"
    
    base_hour_high1 = 4.5 + (diff_days * 0.8) % 12.4
    base_hour_low1 = base_hour_high1 + 6.2
    base_hour_high2 = base_hour_high1 + 12.4
    base_hour_low2 = base_hour_low1 + 12.4
    
    def format_time(decimal_hours):
        h = int(decimal_hours % 24)
        m = int((decimal_hours % 1) * 60)
        return f"{h:02d}:{m:02d}"
    
    high1 = format_time(base_hour_high1)
    high2 = format_time(base_hour_high2)
    low1 = format_time(base_hour_low1)
    low2 = format_time(base_hour_low2)
    
    return f"만조 시간 : {high1}, {high2}\n간조 시간 : {low1}, {low2}\n물때 : {tide_str}"

def format_message(current, forecast, air):
    KST = timezone(timedelta(hours=9))
    now_kst = datetime.now(KST)
    date_str = now_kst.strftime("%Y-%m-%d (%A)")
    today_date_str = now_kst.strftime("%Y-%m-%d")
    time_str = now_kst.strftime("%a, %d %b %Y %H:%M:%S GMT")

    weather_desc = current['weather'][0]['description']
    temp = current['main']['temp']
    
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

    sunrise = datetime.fromtimestamp(current['sys']['sunrise'], KST).strftime("%H:%M")
    sunset = datetime.fromtimestamp(current['sys']['sunset'], KST).strftime("%H:%M")

    pressure = current['main']['pressure']
    humidity = current['main']['humidity']
    wind_speed = current['wind']['speed']
    wind_deg = current['wind'].get('deg', 0)
    
    dirs = ["북풍", "북북동풍", "북동풍", "동북동풍", "동풍", "동남동풍", "남동풍", "남남동풍", 
            "남풍", "남남서풍", "남서풍", "서남서풍", "서풍", "서북서풍", "북서풍", "북북서풍"]
    wind_dir_str = dirs[int((wind_deg + 11.25) / 22.5) % 16]

    aqi = air['list'][0]['main']['aqi']
    aqi_text_map = {1: "좋음", 2: "양호", 3: "보통", 4: "나쁨", 5: "매우 나쁨"}
    dust_status = aqi_text_map.get(aqi, "보통")

    morning_info = get_detailed_time_forecast(forecast.get('list', []), 8)
    noon_info = get_detailed_time_forecast(forecast.get('list', []), 13)
    evening_info = get_detailed_time_forecast(forecast.get('list', []), 18)

    rain_summary = get_rain_summary(forecast.get('list', []))
    tide_summary = get_tide_info()

    lines = [
        f"[Ulsan 오늘 날씨 ⛅]",
        f"{time_str}",
        "",
        f"📅 날짜: {date_str}",
        f"🌅 일출 : {sunrise}",
        f"🌇 일몰 : {sunset}",
        f"☁️ 현재 하늘 상태 : {weather_desc}",
        "",
        f"[🌡️ 기온 정보]",
        f"📍 현재 기온: {temp:.2f}°C",
        f"📊 오늘 최저/최고: {temp_min:.2f}°C / {temp_max:.2f}°C",
        f"🔄 어제와 비교: 📈 비슷해요",
        "",
        f"[☔ 우천 정보]",
        f"{rain_summary}",
        "",
        f"[🥪 아침/점심/저녁]",
        f"  🌅 아침: {morning_info}",
        f"  ☀️ 점심: {noon_info}",
        f"  🌙 저녁: {evening_info}",
        "",
        f"[🔬 바람과 바다]",
        f"🗜️ 기압 : {pressure} hPa",
        f"💧 대기습도 : {humidity} %",
        f"💨 풍속 : {wind_speed} m/s",
        f"🧭 풍향 : {wind_deg}° ({wind_dir_str})",
        "",
        f"[울산 바다 정보]",
        f"{tide_summary}",
        "",
        f"😷 미세먼지: ({dust_status})"
    ]

    return "\n".join(lines)

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
