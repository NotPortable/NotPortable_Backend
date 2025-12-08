import os
import re
import time
import requests
from datetime import datetime
from pathlib import Path

# 초음파 센서 임포트
try:
    import lgpio
    SENSOR_AVAILABLE = True
except ImportError:
    print("⚠️  lgpio 라이브러리 없음 - 센서 기능 비활성화")
    SENSOR_AVAILABLE = False

# API URL
API_BASE_URL = "http://localhost:8000/api"

# 로그 파일 경로
LOG_PATHS = {
    "neverball": os.path.expanduser("~/.neverball/Scores/easy.txt"),
    "supertux": os.path.expanduser("~/.local/share/supertux2/profile1/world1.stsg"),
    "etr": os.path.expanduser("~/.config/etr/highscore")
}

# 초음파 센서 GPIO 핀
TRIG_PIN = 23  # GPIO 23 (Physical Pin 16)
ECHO_PIN = 24  # GPIO 24 (Physical Pin 18)
ANOMALY_THRESHOLD = 10  # cm - 거리 변화 임계값

# 센서 상태 저장
sensor_state = {
    "enabled": SENSOR_AVAILABLE,
    "handle": None,
    "baseline_distance": None,
    "last_check_time": 0,
    "check_interval": 2.0  # 2초마다 체크
}

# 마지막 처리 시간
last_processed = {
    "neverball": None,
    "supertux": None,
    "etr": None
}

def init_sensor():
    """초음파 센서 초기화"""
    if not SENSOR_AVAILABLE:
        return False
    
    try:
        # GPIO 칩 열기
        handle = lgpio.gpiochip_open(0)
        sensor_state["handle"] = handle
        
        # 핀 설정
        lgpio.gpio_claim_output(handle, TRIG_PIN)
        lgpio.gpio_claim_input(handle, ECHO_PIN)
        
        print("✅ 초음파 센서 초기화 완료")
        print(f"   TRIG: GPIO{TRIG_PIN} (Physical Pin 16)")
        print(f"   ECHO: GPIO{ECHO_PIN} (Physical Pin 18)")
        
        # 안정화 대기
        time.sleep(0.5)
        
        # 기준 거리 측정 (3번 측정해서 평균)
        distances = []
        for i in range(3):
            dist = measure_distance()
            if dist:
                distances.append(dist)
            time.sleep(0.1)
        
        if distances:
            baseline = sum(distances) / len(distances)
            sensor_state["baseline_distance"] = baseline
            print(f"   기준 거리: {baseline:.2f}cm")
            return True
        else:
            print("⚠️  기준 거리 측정 실패")
            return False
            
    except Exception as e:
        print(f"❌ 센서 초기화 실패: {e}")
        sensor_state["enabled"] = False
        return False

def measure_distance():
    """거리 측정 (cm 단위)"""
    if not sensor_state["enabled"] or not sensor_state["handle"]:
        return None
    
    try:
        handle = sensor_state["handle"]
        
        # TRIG 신호 전송 (10μs 펄스)
        lgpio.gpio_write(handle, TRIG_PIN, 0)
        time.sleep(0.000002)
        lgpio.gpio_write(handle, TRIG_PIN, 1)
        time.sleep(0.00001)
        lgpio.gpio_write(handle, TRIG_PIN, 0)
        
        # ECHO 대기 (타임아웃 100ms)
        timeout_start = time.time()
        while lgpio.gpio_read(handle, ECHO_PIN) == 0:
            pulse_start = time.time()
            if pulse_start - timeout_start > 0.1:
                return None
        
        timeout_start = time.time()
        while lgpio.gpio_read(handle, ECHO_PIN) == 1:
            pulse_end = time.time()
            if pulse_end - timeout_start > 0.1:
                return None
        
        # 거리 계산: 거리 = (시간 * 음속) / 2
        # 음속 = 34300 cm/s, 왕복이므로 / 2
        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150
        distance = round(distance, 2)
        
        # 유효 범위 체크 (2cm ~ 400cm)
        if 2 <= distance <= 400:
            return distance
        else:
            return None
            
    except Exception as e:
        print(f"⚠️  거리 측정 오류: {e}")
        return None

def check_anomaly():
    """현재 거리와 기준 거리 비교하여 이상 감지"""
    if not sensor_state["enabled"] or sensor_state["baseline_distance"] is None:
        return False
    
    # 체크 간격 확인 (너무 자주 체크하지 않도록)
    current_time = time.time()
    if current_time - sensor_state["last_check_time"] < sensor_state["check_interval"]:
        return False
    
    sensor_state["last_check_time"] = current_time
    
    # 현재 거리 측정
    current_distance = measure_distance()
    if current_distance is None:
        return False
    
    # 거리 변화 계산
    baseline = sensor_state["baseline_distance"]
    distance_change = abs(current_distance - baseline)
    
    # 임계값 초과 여부
    if distance_change > ANOMALY_THRESHOLD:
        print(f"🚨 이상 감지! 거리 변화: {distance_change:.2f}cm")
        print(f"   기준: {baseline:.2f}cm → 현재: {current_distance:.2f}cm")
        return True
    
    return False

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
    seen_records = set()  # 중복 체크용
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            
            # 레벨 정보 추출
            if line.startswith('level'):
                parts = line.split()
                if len(parts) >= 4:
                    current_level = parts[3].split('/')[-1].replace('.sol', '')
            
            # 점수 라인 파싱
            match = re.match(r'^(\d+)\s+(\d+)\s+(\S+)$', line)
            if match:
                time_ms, coins, username = match.groups()
                
                if username not in ['Hard', 'Medium', 'Easy']:
                    time_sec = int(time_ms) / 100.0
                    minutes = int(time_sec // 60)
                    seconds = int(time_sec % 60)
                    time_str = f"{minutes:02d}:{seconds:02d}"
                    
                    # 중복 체크 (username, score, coins 조합으로)
                    record_key = (username, int(time_ms), int(coins))
                    if record_key in seen_records:
                        continue
                    seen_records.add(record_key)
                    
                    # 센서로 이상 감지
                    is_anomaly = check_anomaly()
                    
                    logs.append({
                        "username": username,
                        "level": 1,
                        "score": int(time_ms),
                        "coins": int(coins),
                        "time": time_str,
                        "is_anomaly": is_anomaly
                    })
        
        print(f"📖 Neverball: {len(logs)}개 기록 발견")
        return logs
    
    except Exception as e:
        print(f"❌ Neverball 파싱 오류: {e}")
        return []

def parse_supertux_log(filepath):
    """SuperTux 로그 파싱 (Lisp 형식)"""
    if not os.path.exists(filepath):
        print(f"⚠️  SuperTux 로그 파일 없음: {filepath}")
        return []
    
    logs = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        level_pattern = r'\("([^"]+\.stl)"\s+\(perfect\s+[^)]+\)\s+\("statistics"[^)]+\(coins-collected\s+(\d+)\)[^)]+\(secrets-found\s+(\d+)\)[^)]+\(time-needed\s+([\d.]+)\)'
        matches = re.finditer(level_pattern, content, re.DOTALL)
        
        # 사용자 이름 가져오기 (C 런처에서 저장한 파일)
        username = "Player"
        username_file = "/tmp/supertux_username.txt"
        if os.path.exists(username_file):
            try:
                with open(username_file, 'r') as f:
                    saved_name = f.read().strip()
                    if saved_name:
                        username = saved_name
                        print(f"   👤 사용자: {username}")
            except:
                pass
        
        for match in matches:
            level_name, coins, secrets, time = match.groups()
            level_name = level_name.replace('.stl', '')
            
            # 센서로 이상 감지
            is_anomaly = check_anomaly()
            
            logs.append({
                "username": username,
                "level": level_name,
                "coins": int(coins),
                "secrets": int(secrets),
                "time": float(time),
                "is_anomaly": is_anomaly
            })
        
        if logs:
            print(f"📖 SuperTux: {len(logs)}개 기록 발견 (사용자: {username})")
        return logs
    
    except Exception as e:
        print(f"❌ SuperTux 파싱 오류: {e}")
        return []

def parse_etr_log(filepath):
    """ETR 로그 파싱"""
    if not os.path.exists(filepath):
        print(f"⚠️  ETR 로그 파일 없음: {filepath}")
        return []
    
    logs = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        for line in lines:
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
                
                # 센서로 이상 감지
                is_anomaly = check_anomaly()
                
                logs.append({
                    "username": username,
                    "course": course,
                    "score": score,
                    "herring": herring,
                    "time": time_str,
                    "is_anomaly": is_anomaly
                })
        
        print(f"📖 ETR: {len(logs)}개 기록 발견")
        return logs
    
    except Exception as e:
        print(f"❌ ETR 파싱 오류: {e}")
        return []

def send_to_api(game, logs):
    """API로 로그 전송"""
    success_count = 0
    anomaly_count = 0
    
    for log in logs:
        try:
            response = requests.post(f"{API_BASE_URL}/{game}/log", json=log)
            if response.status_code == 200:
                success_count += 1
                if log.get('is_anomaly'):
                    anomaly_count += 1
            else:
                print(f"❌ [{game}] API 오류: {response.status_code}")
        except Exception as e:
            print(f"❌ [{game}] 전송 실패: {e}")
    
    if success_count > 0:
        status = f"✅ [{game}] {success_count}개 기록 저장 완료"
        if anomaly_count > 0:
            status += f" (🚨 이상 데이터 {anomaly_count}개)"
        print(status)

def cleanup_sensor():
    """센서 정리"""
    if sensor_state["enabled"] and sensor_state["handle"]:
        try:
            lgpio.gpiochip_close(sensor_state["handle"])
            print("✅ 센서 정리 완료")
        except:
            pass

def main():
    """메인 루프"""
    print("🎮 NotPortable 로그 파서 with 초음파 센서")
    print("=" * 60)
    print(f"📁 Neverball: {LOG_PATHS['neverball']}")
    print(f"📁 SuperTux: {LOG_PATHS['supertux']}")
    print(f"📁 ETR: {LOG_PATHS['etr']}")
    print("=" * 60)
    
    # 초음파 센서 초기화
    if SENSOR_AVAILABLE:
        print("\n🔌 초음파 센서 연결 중...")
        print("   하드웨어 연결:")
        print("   - VCC  → Pin 2  (5V)")
        print("   - GND  → Pin 6  (GND)")
        print("   - TRIG → Pin 16 (GPIO 23)")
        print("   - ECHO → Pin 18 (GPIO 24)")
        print()
        
        if init_sensor():
            print(f"✅ 이상 감지 임계값: {ANOMALY_THRESHOLD}cm\n")
        else:
            print("⚠️  센서 없이 계속 진행...\n")
    else:
        print("\n⚠️  센서 비활성화 - lgpio 설치 필요:")
        print("   sudo apt install python3-lgpio\n")
    
    print("🔄 10초마다 로그 확인 중...\n")
    
    # 처음 실행시 모든 로그 파싱
    print("=" * 60)
    print("첫 실행: 모든 로그 파싱 중...")
    print("=" * 60)
    
    neverball_logs = parse_neverball_log(LOG_PATHS["neverball"])
    if neverball_logs:
        send_to_api("neverball", neverball_logs)
    
    supertux_logs = parse_supertux_log(LOG_PATHS["supertux"])
    if supertux_logs:
        send_to_api("supertux", supertux_logs)
    
    etr_logs = parse_etr_log(LOG_PATHS["etr"])
    if etr_logs:
        send_to_api("etr", etr_logs)
    
    print("\n" + "=" * 60)
    print("초기 로딩 완료! 새 로그 감시 시작...")
    print("=" * 60 + "\n")
    
    # 파일 수정 시간 추적
    last_modified = {
        "neverball": os.path.getmtime(LOG_PATHS["neverball"]) if os.path.exists(LOG_PATHS["neverball"]) else 0,
        "supertux": os.path.getmtime(LOG_PATHS["supertux"]) if os.path.exists(LOG_PATHS["supertux"]) else 0,
        "etr": os.path.getmtime(LOG_PATHS["etr"]) if os.path.exists(LOG_PATHS["etr"]) else 0
    }
    
    try:
        while True:
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
            
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n\n👋 로그 파서 종료")
        cleanup_sensor()
    except Exception as e:
        print(f"\n⚠️  오류 발생: {e}")
        cleanup_sensor()

if __name__ == "__main__":
    main()