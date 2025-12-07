import time
import lgpio

TRIG = 23   # GPIO 23 (핀 16)
ECHO = 24   # GPIO 24 (핀 18)
CHIP = 0    # 대부분 0번 칩

def setup():
    handle = lgpio.gpiochip_open(CHIP)
    lgpio.gpio_claim_output(handle, TRIG)
    lgpio.gpio_claim_input(handle, ECHO)
    return handle

def measure_distance(handle):
    # TRIG LOW
    lgpio.gpio_write(handle, TRIG, 0)
    time.sleep(0.000002)

    # TRIG HIGH (10us pulse)
    lgpio.gpio_write(handle, TRIG, 1)
    time.sleep(0.00001)
    lgpio.gpio_write(handle, TRIG, 0)

    # ECHO HIGH 기다리기
    start_timeout = time.time()
    while lgpio.gpio_read(handle, ECHO) == 0:
        pulse_start = time.time()
        if pulse_start - start_timeout > 0.1:
            return None

    # ECHO LOW 될 때까지 (pulse end)
    end_timeout = time.time()
    while lgpio.gpio_read(handle, ECHO) == 1:
        pulse_end = time.time()
        if pulse_end - end_timeout > 0.1:
            return None

    # 시간 차이 계산
    duration = pulse_end - pulse_start

    # 거리 계산
    distance = duration * 17150  # cm 단위
    return round(distance, 2)

def main():
    print("초음파 센서 테스트 시작!")
    print("TRIG=23, ECHO=24\n")

    handle = setup()

    try:
        while True:
            dist = measure_distance(handle)

            if dist is None:
                print("측정 실패…")
            else:
                print(f"거리: {dist} cm")

            time.sleep(0.3)

    except KeyboardInterrupt:
        print("\n종료!")

    finally:
        lgpio.gpiochip_close(handle)

if __name__ == "__main__":
    main()
