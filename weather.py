import os
import requests

# GitHub Actions 환경 변수에서 지역 가져오기 (없으면 Ulsan)
city = os.getenv("INPUT_CITY", "Ulsan")

# 예시: OpenWeatherMap API 호출 및 기존 이미지 형태의 메시지 조합
# ... 날씨 데이터 파싱 코드 ...

message = f"[{city} 오늘 날씨 ⛅]\n..." # 사용자가 보여주신 양식 적용

# 텔레그램 전송
token = os.getenv("TELEGRAM_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")
url = f"https://api.telegram.org/bot{token}/sendMessage"
requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})
