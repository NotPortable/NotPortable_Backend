import os
import re
import time
import requests
from datetime import datetime
from pathlib import Path

# API URL
API_BASE_URL = "http://localhost:8000/api"

# 로그 파일 경로
LOG_PATHS = {
    "neverball": os.path.expanduser("~/.neverball/easy.txt"),
    "supertux": "/home/jungwoo/.local/share/supertux2/profile/world1.stsg",
    "etr": os.path.expanduser("~/.config/etr/highscore")
}

# 마지막 처리 위치 저장
last_positions = {
    "neverball": 0,
    "supertux": 0,
    "etr": 0
}

def parse_neverball_log(filepath):
    """Neverball 로그 파싱"""
    if not os.path.exists(filepath):
        return []
    
    logs = []
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # 새로운 라인만 처리
    global last_positions
    new_lines = lines[last_positions["neverball"]:]
    last_positions["neverball"] = len(lines)
    
    for line in new_lines:
        # 예시: "jeonggoo 107 10000 187 05:23"
        match = re.match(r'(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d:]+)', line.strip())
        if match:
            username, level, score, coins, time = match.groups()
            logs.append({
                "username": username,
                "level": int(level),
                "score": int(score),
                "coins": int(coins),
                "time": time,
                "is_anomaly": False  # C 코드에서 설정
            })
    
    return logs

def parse_supertux_log(filepath):
    """SuperTux 로그 파싱"""
    if not os.path.exists(filepath):
        return []
    
    logs = []
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    global last_positions
    new_lines = lines[last_positions["supertux"]:]
    last_positions["supertux"] = len(lines)
    
    for line in new_lines:
        # 예시: "jeonggoo world1-3 156 2 142.8"
        match = re.match(r'(\S+)\s+([\w-]+)\s+(\d+)\s+(\d+)\s+([\d.]+)', line.strip())
        if match:
            username, level, coins, secrets, time = match.groups()
            logs.append({
                "username": username,
                "level": level,
                "coins": int(coins),
                "secrets": int(secrets),
                "time": float(time),
                "is_anomaly": False
            })
    
    return logs

def parse_etr_log(filepath):
    """ETR 로그 파싱"""
    if not os.path.exists(filepath):
        return []
    
    logs = []
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    global last_positions
    new_lines = lines[last_positions["etr"]:]
    last_positions["etr"] = len(lines)
    
    for line in new_lines:
        # 예시: "jeonggoo Easy_Run 8562 23 02:15.32"
        match = re.match(r'(\S+)\s+([\w_]+)\s+(\d+)\s+(\d+)\s+([\d:.]+)', line.strip())
        if match:
            username, course, score, herring, time = match.groups()
            logs.append({
                "username": username,
                "course": course.replace('_', ' '),
                "score": int(score),
                "herring": int(herring),
                "time": time,
                "is_anomaly": False
            })
    
    return logs

def send_to_api(game, logs):
    """API로 로그 전송"""
    for log in logs:
        try:
            response = requests.post(f"{API_BASE_URL}/{game}/log", json=log)
            if response.status_code == 200:
                print(f"✅ [{game}] {log['username']} 기록 저장 완료")
            else:
                print(f"❌ [{game}] API 오류: {response.text}")
        except Exception as e:
            print(f"❌ [{game}] 전송 실패: {e}")

def main():
    """메인 루프"""
    print("🎮 NotPortable 로그 파서 시작...")
    print(f"📁 Neverball: {LOG_PATHS['neverball']}")
    print(f"📁 SuperTux: {LOG_PATHS['supertux']}")
    print(f"📁 ETR: {LOG_PATHS['etr']}")
    print(f"🔄 10초마다 로그 확인 중...\n")
    
    while True:
        try:
            # Neverball 로그 처리
            neverball_logs = parse_neverball_log(LOG_PATHS["neverball"])
            if neverball_logs:
                send_to_api("neverball", neverball_logs)
            
            # SuperTux 로그 처리
            supertux_logs = parse_supertux_log(LOG_PATHS["supertux"])
            if supertux_logs:
                send_to_api("supertux", supertux_logs)
            
            # ETR 로그 처리
            etr_logs = parse_etr_log(LOG_PATHS["etr"])
            if etr_logs:
                send_to_api("etr", etr_logs)
            
            # 10초 대기
            time.sleep(10)
            
        except KeyboardInterrupt:
            print("\n\n👋 로그 파서 종료")
            break
        except Exception as e:
            print(f"⚠️  오류 발생: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()