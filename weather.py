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
    """울산 연안 기준 대략적인 조석(만조/간조) 정보 및 물때 계산"""
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
        item_time_utc = datetime.fromtimestamp(
