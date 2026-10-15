import os
import requests
from datetime import datetime, timezone, timedelta

# 환경 변수 로드
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_KEY = os.getenv("WEATHER_API_KEY")

# 울산 온산읍 좌표
LAT = 35.4261
LON = 129.3364
LOC_NAME = "울산 온산읍"

def get_weather_data(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=kr"
    res = requests.get(url).json()
    
    forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=kr"
    forecast_res = requests.get(forecast_url).json()

    air_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
    air_res = requests.get(air_url).json()

    return res, forecast_res, air_res

def get_custom_time_forecast(forecast_list, target_hour, label):
    """지정한 시간(target_hour)과 가장 가까운 예보를 찾아 라벨과 함께 반환"""
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
        return f"  • {label} : 정보 없음"

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

    return f"  {icon} {label} : {temp:.1f}°C (체감 {feels_like:.1f}°C) | 강수 {pop}%{tip}"

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
    
    return f"🌊 만조 시간 : {high1}, {high2}\n🐚
