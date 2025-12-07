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
    "neverball": os.path.expanduser("~/.neverball/Scores/easy.txt"),
    "supertux": os.path.expanduser("~/.local/share/supertux2/profile1/world1.stsg"),
    "etr": os.path.expanduser("~/.config/etr/highscore")
}

# 마지막 처리 시간
last_processed = {
    "neverball": None,
    "supertux": None,
    "etr": None
}

def parse_neverball_log(filepath):
    """
    Neverball 로그 파싱
    형식: 2695 11 jungwooD
         (시간ms) (코인수) (사용자명)
    """
    if not os.path.exists(filepath):
        print(f"⚠️  Neverball 로그 파일 없음: {filepath}")
        return []
    
    logs = []
    current_level = "Unknown"
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            
            # 레벨 정보 추출
            if line.startswith('level'):
                # level 2 1 map-easy/easy.sol
                parts = line.split()
                if len(parts) >= 4:
                    current_level = parts[3].split('/')[-1].replace('.sol', '')
            
            # 점수 라인 파싱: 시간(ms) 코인수 사용자명
            # 예: 2695 11 jungwooD
            match = re.match(r'^(\d+)\s+(\d+)\s+(\S+)$', line)
            if match:
                time_ms, coins, username = match.groups()
                
                # 사용자 이름이 있고, Hard/Medium/Easy가 아닌 경우만
                if username not in ['Hard', 'Medium', 'Easy']:
                    time_sec = int(time_ms) / 100.0  # 센티초를 초로 변환
                    minutes = int(time_sec // 60)
                    seconds = int(time_sec % 60)
                    time_str = f"{minutes:02d}:{seconds:02d}"
                    
                    logs.append({
                        "username": username,
                        "level": 1,  # 레벨은 나중에 추가 가능
                        "score": int(time_ms),
                        "coins": int(coins),
                        "time": time_str,
                        "is_anomaly": False
                    })
        
        print(f"📖 Neverball: {len(logs)}개 기록 발견")
        return logs
    
    except Exception as e:
        print(f"❌ Neverball 파싱 오류: {e}")
        return []

def parse_supertux_log(filepath):
    """
    SuperTux 로그 파싱
    Lisp 형식에서 statistics 추출
    """
    if not os.path.exists(filepath):
        print(f"⚠️  SuperTux 로그 파일 없음: {filepath}")
        return []
    
    logs = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 레벨 이름 추출
        level_pattern = r'\("([^"]+\.stl)"\s+\(perfect\s+[^)]+\)\s+\("statistics"[^)]+\(coins-collected\s+(\d+)\)[^)]+\(secrets-found\s+(\d+)\)[^)]+\(time-needed\s+([\d.]+)\)'
        matches = re.finditer(level_pattern, content, re.DOTALL)
        
        # 사용자명 추출 (worldmap-sprite 근처 또는 기본값)
        username_match = re.search(r'\(tux', content)
        username = "Player"  # 기본값
        
        for match in matches:
            level_name, coins, secrets, time = match.groups()
            level_name = level_name.replace('.stl', '')
            
            logs.append({
                "username": username,
                "level": level_name,
                "coins": int(coins),
                "secrets": int(secrets),
                "time": float(time),
                "is_anomaly": False
            })
        
        print(f"📖 SuperTux: {len(logs)}개 기록 발견")
        return logs
    
    except Exception as e:
        print(f"❌ SuperTux 파싱 오류: {e}")
        return []

def parse_etr_log(filepath):
    """
    ETR 로그 파싱
    형식: *[group] default [course] bunny_hill [plyr] gyumin [pts] 443 [herr] 23 [time] 30.7
    """
    if not os.path.exists(filepath):
        print(f"⚠️  ETR 로그 파일 없음: {filepath}")
        return []
    
    logs = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        for line in lines:
            # *[group] default [course] bunny_hill [plyr] gyumin [pts] 443 [herr] 23 [time] 30.7
            course_match = re.search(r'\[course\]\s+(\S+)', line)
            plyr_match = re.search(r'\[plyr\]\s+(\S+)', line)
            pts_match = re.search(r'\[pts\]\s+(\d+)', line)
            herr_match = re.search(r'\[herr\]\s+(\d+)', line)
            time_match = re.search(r'\[time\]\s+([\d.]+)', line)
            
            if all([course_match, plyr_match, pts_match, herr_match, time_match]):
                course = course_match.group(1).replace('_', ' ')
                username = plyr_match.group(1)
                score = int(pts_match.group(1))
                herring = int(herr_match.group(1))
                time_sec = float(time_match.group(1))
                
                minutes = int(time_sec // 60)
                seconds = time_sec % 60
                time_str = f"{minutes:02d}:{seconds:05.2f}"
                
                logs.append({
                    "username": username,
                    "course": course,
                    "score": score,
                    "herring": herring,
                    "time": time_str,
                    "is_anomaly": False
                })
        
        print(f"📖 ETR: {len(logs)}개 기록 발견")
        return logs
    
    except Exception as e:
        print(f"❌ ETR 파싱 오류: {e}")
        return []

def send_to_api(game, logs):
    """API로 로그 전송"""
    success_count = 0
    for log in logs:
        try:
            response = requests.post(f"{API_BASE_URL}/{game}/log", json=log)
            if response.status_code == 200:
                success_count += 1
            else:
                print(f"❌ [{game}] API 오류: {response.status_code}")
        except Exception as e:
            print(f"❌ [{game}] 전송 실패: {e}")
    
    if success_count > 0:
        print(f"✅ [{game}] {success_count}개 기록 저장 완료")

def main():
    """메인 루프"""
    print("🎮 NotPortable 로그 파서 시작...")
    print(f"📁 Neverball: {LOG_PATHS['neverball']}")
    print(f"📁 SuperTux: {LOG_PATHS['supertux']}")
    print(f"📁 ETR: {LOG_PATHS['etr']}")
    print(f"🔄 10초마다 로그 확인 중...\n")
    
    # 처음 실행시 모든 로그 파싱
    print("=" * 50)
    print("첫 실행: 모든 로그 파싱 중...")
    print("=" * 50)
    
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
    
    print("\n" + "=" * 50)
    print("초기 로딩 완료! 이제 10초마다 새 로그 확인...")
    print("=" * 50 + "\n")
    
    # 이후 새 로그만 감시 (파일 수정 시간 체크)
    last_modified = {
        "neverball": os.path.getmtime(LOG_PATHS["neverball"]) if os.path.exists(LOG_PATHS["neverball"]) else 0,
        "supertux": os.path.getmtime(LOG_PATHS["supertux"]) if os.path.exists(LOG_PATHS["supertux"]) else 0,
        "etr": os.path.getmtime(LOG_PATHS["etr"]) if os.path.exists(LOG_PATHS["etr"]) else 0
    }
    
    while True:
        try:
            # 파일 수정 확인 후 파싱
            for game, path in LOG_PATHS.items():
                if os.path.exists(path):
                    current_mtime = os.path.getmtime(path)
                    if current_mtime > last_modified[game]:
                        print(f"\n🔄 {game} 로그 파일 변경 감지!")
                        last_modified[game] = current_mtime
                        
                        if game == "neverball":
                            logs = parse_neverball_log(path)
                        elif game == "supertux":
                            logs = parse_supertux_log(path)
                        elif game == "etr":
                            logs = parse_etr_log(path)
                        
                        if logs:
                            send_to_api(game, logs)
            
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