import os
import requests
from datetime import datetime, timezone, timedelta

# 환경 변수 로드
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_KEY = os.getenv("WEATHER_API_KEY")

# 조회할 지역 리스트 (울산광역시)
LOCATIONS = [
    {"name": "울산광역시", "lat": 35.4261, "lon": 129.3364},
    ]

def get_weather_data(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=kr"
    res = requests.get(url).json()
    
    forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=kr"
    forecast_res = requests.get(forecast_url).json()

    air_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
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
    """상세한 물때 설명과 조석 정보를 반환"""
    KST = timezone(timedelta(hours=9))
    now_kst = datetime.now(KST)
    
    base_date = datetime(2026, 1, 1, tzinfo=KST)
    diff_days = (now_kst - base_date).days
    
    tide_water_num = (diff_days % 15) + 1
    
    # 물때별 상세 설명 및 특징
    tide_details = {
        1: "1물 - 조류가 느리기 시작하며 물 빠짐이 완만함",
        2: "2물 - 조류가 서서히 빨라지며 활동하기 무난함",
        3: "3물 - 물살과 조류가 적당하여 낚시 및 해루질 최적기",
        4: "4물 - 조류 흐름이 원활하고 활성도가 좋아짐",
        5: "5물 - 조류가 제법 강해지기 시작하는 단계",
        6: "6물 - 조류가 빨라지고 물의 드나듦이 뚜렷함",
        7: "7물 - 사리(대조기) 시작, 조류가 매우 강하고 물골 주의",
        8: "8물 - 사리 기간, 물살이 가장 거세고 수위 변화 큼",
        9: "9물 - 사리 직후로 여전히 조류가 빠른 상태",
        10: "10물 - 조류가 점차 꺾이고 느려지기 시작함",
        11: "11물 - 물살이 약해지고 잔잔해지는 과정",
        12: "12물 - 조류가 완만해져 초보자 활동에 좋음",
        13: "13물(조금) - 조차(만조와 간조의 차이)가 가장 작고 물살이 느림",
        14: "14물(무시) - 조류 흐름이 거의 없어 바다가 잔잔함",
        15: "15물(조금 직후) - 물살이 다시 살아나기 시작하는 시점"
    }
    
    tide_desc_text = tide_details.get(tide_water_num, "일반 물때")
    
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
    
    return f"🌊 만조 시간 : {high1}, {high2}\n🐚 간조 시간 : {low1}, {low2}\n📈 물때 정보 : {tide_desc_text}"

def format_message(loc_name, current, forecast, air):
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
        f"[{loc_name} 오늘 날씨 ⛅]",
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
        f"😷 미세먼지: ({dust_status})"
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
        f"[{loc_name} 바다 정보]",
        f"{tide_summary}",
        "",
        
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
    combined_message = ""
    for idx, loc in enumerate(LOCATIONS):
        cur, fore, air = get_weather_data(loc["lat"], loc["lon"])
        msg = format_message(loc["name"], cur, fore, air)
        
        combined_message += msg
        if idx < len(LOCATIONS) - 1:
            combined_message += "\n\n" + "="*25 + "\n\n"  # 지역 간 경계선 추가

    send_telegram(combined_message)
