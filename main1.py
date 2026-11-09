from machine import Pin, PWM, time_pulse_us
import time


SERVO_PIN = 8
servo = PWM(Pin(SERVO_PIN), freq=50)
GOC_NHIN_THANG = 90   
GOC_NHIN_PHAI  = 10   
GOC_NHIN_TRAI  = 165  


TRIG_PIN = 9
ECHO_PIN = 10
trig = Pin(TRIG_PIN, Pin.OUT)
echo = Pin(ECHO_PIN, Pin.IN)


IN1 = Pin(38, Pin.OUT)
IN2 = Pin(37, Pin.OUT)
IN3 = Pin(36, Pin.OUT)
IN4 = Pin(35, Pin.OUT)

ENA = PWM(Pin(42), freq=1000)
ENB = PWM(Pin(41), freq=1000)

# TỐC ĐỘ ĐỘNG CƠ (Thang 0 - 65535)
TOC_DO_THANG = 40000  # Tốc độ đi thẳng
TOC_DO_RE    = 52000   # Tốc độ khi bẻ lái xoay xe

# THỜI GIAN & KHOẢNG CÁCH (Chuẩn hóa theo code Arduino)
NGUONG_VAT_CAN     = 25    # 25 cm (như frontDist > 25 trong Arduino)
THOI_GIAN_LUI      = 0.35  # 350ms lùi tạo khoảng trống xoay
THOI_GIAN_RE       = 0.55  # Thời gian rẽ bánh 
KHOANG_CACH_MAX    = 200   # Mặc định khi không có vật cản

# ================= 2. CÁC HÀM ĐIỀU KHIỂN ĐỘNG CƠ =================
def stop_car():
    """Dừng xe hoàn toàn"""
    ENA.duty_u16(0)
    ENB.duty_u16(0)
    IN1.value(0)
    IN2.value(0)
    IN3.value(0)
    IN4.value(0)

def forward():
    """Đi thẳng"""
    ENA.duty_u16(TOC_DO_THANG)
    ENB.duty_u16(TOC_DO_THANG)
    IN1.value(1)
    IN2.value(0)
    IN3.value(1)
    IN4.value(0)

def backward():
    """Lùi xe"""
    ENA.duty_u16(TOC_DO_THANG)
    ENB.duty_u16(TOC_DO_THANG)
    IN1.value(0)
    IN2.value(1)
    IN3.value(0)
    IN4.value(1)

def turn_left():
    """Quay xe sang Trái"""
    ENA.duty_u16(TOC_DO_RE)
    ENB.duty_u16(TOC_DO_RE)
    IN1.value(1)
    IN2.value(0)
    IN3.value(0)
    IN4.value(1)

def turn_right():
    """Quay xe sang Phải"""
    ENA.duty_u16(TOC_DO_RE)
    ENB.duty_u16(TOC_DO_RE)
    IN1.value(0)
    IN2.value(1)
    IN3.value(1)
    IN4.value(0)

# ================= 3. ĐIỀU KHIỂN SERVO =================
def set_angle(goc):
    duty = int(1638 + (goc / 180.0) * (8192 - 1638))
    servo.duty_u16(duty)

def dung_xung_servo():
    """Tắt xung để servo không nóng và không gừ"""
    servo.duty_u16(0)

# ================= 4. ĐO KHOẢNG CÁCH (getDistance) =================
def get_distance():
    trig.value(0)
    time.sleep_us(2)
    trig.value(1)
    time.sleep_us(10)
    trig.value(0)

    try:
        us = time_pulse_us(echo, 1, 25000)
        if us > 0:
            kc = (us * 0.034) / 2
            if 2.0 <= kc <= 400.0:
                return kc
    except Exception:
        pass
    return KHOANG_CACH_MAX

# ================= 5. HÀM QUÉT 2 BÊN (lookRight & lookLeft) =================
def look_right():
    set_angle(GOC_NHIN_PHAI)
    time.sleep(0.4)  # Chờ servo quay đến nơi và ổn định
    d = get_distance()
    print(f"   [>] Đo bên PHẢI: {d:.1f} cm")
    
    set_angle(GOC_NHIN_THANG)
    time.sleep(0.2)
    dung_xung_servo()
    return d

def look_left():
    set_angle(GOC_NHIN_TRAI)
    time.sleep(0.4)  # Chờ servo quay đến nơi và ổn định
    d = get_distance()
    print(f"   [<] Đo bên TRÁI: {d:.1f} cm")
    
    set_angle(GOC_NHIN_THANG)
    time.sleep(0.2)
    dung_xung_servo()
    return d

# ================= 6. KHỞI TẠO HỆ THỐNG =================
stop_car()
set_angle(GOC_NHIN_THANG)
time.sleep(1)
dung_xung_servo()
print("Xe đã sẵn sàng! Bắt đầu chạy...")

# ================= 7. VÒNG LẶP CHÍNH (Tương đương loop()) =================
while True:
    front_dist = get_distance()

    if front_dist > NGUONG_VAT_CAN:
        # Đường thoáng (> 25cm) -> Đi thẳng
        forward()
        time.sleep(0.05)
    else:
        # Gặp vật cản
        print(f"\n[!] Vật cản phía trước: {front_dist:.1f} cm (< {NGUONG_VAT_CAN}cm)")

        # 1. STOP
        stop_car()
        time.sleep(0.1)

        # 2. SMALL BACKWARD (Lùi đệm tạo khoảng trống xoay bánh)
        backward()
        time.sleep(THOI_GIAN_LUI)
        stop_car()
        time.sleep(0.1)

        # 3. SCAN RIGHT & LEFT (Theo đúng thứ tự code mẫu)
        right_dist = look_right()
        left_dist  = look_left()
        time.sleep(0.1)
# 4. DECIDE DIRECTION (Thêm tính năng phát hiện kẹt 2 bên <= 30cm)
        if right_dist <= 30 and left_dist <= 30:
            print(f"==> BỊ KẸT (Phải: {right_dist:.1f}cm, Trái: {left_dist:.1f}cm <= 30cm) -> LẬP TỨC QUAY ĐẦU")
            
            # Lùi thêm một đoạn dài hơn để tạo đủ không gian xoay
            backward()
            time.sleep(THOI_GIAN_LUI * 1.5)
            stop_car()
            time.sleep(0.1)
            
            # Rẽ với thời gian gấp đôi (hoặc x2.2) để xoay xe 180 độ
            turn_right() 
            time.sleep(THOI_GIAN_RE * 2.2) 
            
        elif right_dist > left_dist:
            print(f"==> Bên PHẢI thoáng hơn ({right_dist:.1f}cm > {left_dist:.1f}cm) -> RẼ PHẢI")
            turn_right()
            time.sleep(THOI_GIAN_RE)
            
        else:
            print(f"==> Bên TRÁI thoáng hơn ({left_dist:.1f}cm >= {right_dist:.1f}cm) -> RẼ TRÁI")
            turn_left()
            time.sleep(THOI_GIAN_RE)

        time.sleep(THOI_GIAN_RE)
        stop_car()
        time.sleep(0.1)


