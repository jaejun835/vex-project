#region VEXcode Generated Robot Configuration
from vex import *
import urandom
import math

# 브레인은 기본으로 정의되어 있어야 함
brain=Brain()

# 로봇 설정 코드


# 회전 센서 초기화가 끝날 때까지 기다림
wait(30, MSEC)


# 실행할 때마다 난수 시작값이 달라지도록 설정
def initializeRandomSeed():
    wait(100, MSEC)
    random = brain.battery.voltage(MV) + brain.battery.current(CurrentUnits.AMP) * 100 + brain.timer.system_high_res()
    urandom.seed(int(random))
      
# 난수 시작값 설정 
initializeRandomSeed()


def play_vexcode_sound(sound_name):
    # VEXcode에서 V5 소리를 쉽게 재생하도록 돕고
    # 어떤 동작인지 분명하게 보여주는 보조 함수.
    print("VEXPlaySound:" + sound_name)
    wait(5, MSEC)

# REPL 머리글 중간에 출력하지 않도록 잠깐 기다림
wait(200, MSEC)
# 콘솔에 남은 REPL 표시를 지움
print("\033[2J")

#endregion VEXcode Generated Robot Configuration
from vex import *

brain = Brain()
controller = Controller(PRIMARY)

# X-drive는 일단 왼쪽 반전과 오른쪽 기본 방향으로 설정
# 장착 후 낮은 속도로 바퀴별 방향을 확인하기, 현재 방향은 임시 설정
# 초록색 카트리지를 쓰므로 기어비는 18:1로 맞춤
left_front = Motor(Ports.PORT1, GearSetting.RATIO_18_1, True)
left_rear = Motor(Ports.PORT3, GearSetting.RATIO_18_1, True)
right_front = Motor(Ports.PORT2, GearSetting.RATIO_18_1, False)
right_rear = Motor(Ports.PORT4, GearSetting.RATIO_18_1, False)
drive_motors = [left_front, left_rear, right_front, right_rear]
DRIVE_TORQUE = 100

for motor in drive_motors:
    motor.set_stopping(HOLD)
    motor.set_max_torque(DRIVE_TORQUE, PERCENT)

# 데드존이 0이라 작은 입력도 그대로 통과함.
DEADZONE = 0
# 최고속도는 100%로 고정
speed_limit = 100

# 집게 5번, 리프트 왼쪽 도르레 6번, 오른쪽 도르레 7번
# 집게 회전용 별도 모터는 아직 지정하지 않음
LIFT_PORT_1 = Ports.PORT6
LIFT_PORT_2 = Ports.PORT7
CLAW_PORT = Ports.PORT5
WRIST_PORT = None

# 측정 때 확인한 도르레 방향을 그대로 사용
# 두 모터 모두 각도가 감소하는 REVERSE 방향이 리프트 상승
LIFT_LEFT_REVERSED = False
LIFT_RIGHT_REVERSED = True
# 집게도 REVERSE로 열리고, FORWARD로 닫힘
CLAW_REVERSED = False
WRIST_REVERSED = False

# 리프트는 빨간색 카트리지 사용, 집게와 회전축은 실제 카트리지를 확인하고 변경하기
LIFT_GEARS = GearSetting.RATIO_36_1
CLAW_GEARS = GearSetting.RATIO_18_1 ########################### !!확실하지 않아서 점검 필요!! #################################
WRIST_GEARS = GearSetting.RATIO_18_1

# 리프트는 아래쪽 기준에서 A를 눌러 두 모터를 0영점으로 등록
# 집게는 측정 당시 -59도였던 실제 위치에서 X를 눌러 기준 등록 ########################## 다시 측정 및 검토 필요 ################################
LIFT_LOWER_LIMIT = 0
LIFT_UPPER_LIMIT = -1400
# A를 누르기 전에는 양쪽 도르레 모두 조작을 막음
lift_ready = False
CLAW_CLOSED_LIMIT = -59
CLAW_OPEN_LIMIT = -388
# 시작할 때는 집게 위치를 모르므로, X로 기준을 확인하기 전까지 조작 금지
claw_ready = False
WRIST_MAX_DEG = None

# 포트, 방향, 이동 범위와 시작 위치를 확인한 기구만 True로 변경
LIFT_ENABLED = True
CLAW_ENABLED = True
WRIST_ENABLED = False

# 리프트는 사용자가 상승을 확인한 속도/토크 100% 설정
# 끝에서 정지 지연이 생길 수 있어 -1400도 한계는 실제 기구에서 검증 필요
LIFT_SPEED = 100
CLAW_SPEED = 40
WRIST_SPEED = 15

# 막힌 상태에서 과하게 미는 힘을 줄이기 위한 토크 제한
# 이 수치가 기어에 안전하다는 보장은 없으므로 기구에 맞춰 확인해야 함
LIFT_TORQUE = 100
CLAW_TORQUE = 30
WRIST_TORQUE = 20


def apply_deadzone(value):
    # abs는 부호를 뺀 크기로 전진과 후진의 작은 입력을 같이 걸러냄
    return 0 if abs(value) < DEADZONE else value


def command_motor(motor, speed):
    # 0이면 stop을 써야 설정한 BRAKE/HOLD 방식으로 멈춤
    if speed == 0:
        motor.stop()
    else:
        motor.spin(FORWARD, speed, PERCENT)


def create_motors(ports, gears, reversed_direction, torque, stopping):
    # 미설정 기구가 있어도 주행은 쓸 수 있도록 빈 목록을 반환함
    if any(port is None for port in ports):
        return []
    motors = []
    for port in ports:
        motor = Motor(port, gears, reversed_direction)
        motor.set_max_torque(torque, PERCENT)
        motor.set_stopping(stopping)
        motors.append(motor)
    return motors


# 리프트와 회전축은 버튼을 놓으면 현재 위치를 유지하려고 힘을 줌
# HOLD도 전원이 꺼지면 무게를 지탱하지 못하므로 기계적 지지가 필요함
lift_left = Motor(LIFT_PORT_1, LIFT_GEARS, LIFT_LEFT_REVERSED)
lift_right = Motor(LIFT_PORT_2, LIFT_GEARS, LIFT_RIGHT_REVERSED)
lift_motors = [lift_left, lift_right]
for motor in lift_motors:
    motor.set_max_torque(LIFT_TORQUE, PERCENT)
    motor.set_stopping(HOLD)
# 집게는 일단 BRAKE 사용하지만 물체를 계속 잡아주는 힘은 확실하지 않기 때문에 #################################### 검토 필요 ##########################################
claw_motors = create_motors(
    [CLAW_PORT], CLAW_GEARS, CLAW_REVERSED, CLAW_TORQUE, BRAKE
)
wrist_motors = create_motors(
    [WRIST_PORT], WRIST_GEARS, WRIST_REVERSED, WRIST_TORQUE, HOLD
)


def set_reference(motors, enabled, maximum):
    # 현재 위치를 0이라고 기록할 뿐, 실제 원점을 찾아 움직이지는 않음
    # 프로그램을 실행할 때마다 기구를 정해둔 기준 위치에 놓아야 함
    if enabled and maximum is not None and maximum > 0:
        for motor in motors:
            motor.set_position(0, DEGREES)


# 리프트와 집게는 시작 위치를 자동으로 영점 처리하지 않음
# 각각 A와 X를 눌러 실제 기준 위치를 확인한 후 등록
set_reference(wrist_motors, WRIST_ENABLED, WRIST_MAX_DEG)


def control_limited(motors, enabled, maximum,
                    positive_button, negative_button, speed):
    if not motors:
        return
    if not enabled or maximum is None or maximum <= 0:
        for motor in motors:
            motor.stop()
        return

    # 양쪽 버튼을 같이 누르거나 모두 놓으면 정지
    if positive_button == negative_button:
        output = 0
    elif positive_button:
        # 리프트처럼 두 모터가 있으면 하나라도 상한에 닿을 때 같이 정지
        at_limit = any(m.position(DEGREES) >= maximum for m in motors)
        output = 0 if at_limit else speed
    else:
        # 하한은 0도고 제한에 걸려도 반대 방향으로 돌아오는 것은 허용됨
        at_limit = any(m.position(DEGREES) <= 0 for m in motors)
        output = 0 if at_limit else -speed
    for motor in motors:
        command_motor(motor, output)


def show_speed():
    controller.screen.clear_row(1)
    controller.screen.set_cursor(1, 1)
    controller.screen.print("Speed:", speed_limit, "%")

    controller.screen.clear_row(2)
    controller.screen.set_cursor(2, 1)
    controller.screen.print("Lift: READY" if lift_ready else "Lift: press A")

    controller.screen.clear_row(3)
    controller.screen.set_cursor(3, 1)
    controller.screen.print("Claw: READY" if claw_ready else "Claw: press X")


def confirm_lift_reference():
    global lift_ready

    # 실행할 때마다 한 번만 등록하고 움직인 다음 실수로 재등록하는 것을 막음
    if lift_ready or not LIFT_ENABLED:
        return
    if controller.buttonL1.pressing() or controller.buttonL2.pressing():
        return

    # 측정할 때 A를 눌렀던 것과 같은 실제 아래쪽 위치에 놓고 등록하기
    # 자동으로 내려가지 않으며, 현재 위치를 0도로 기록함
    for motor in lift_motors:
        motor.stop()
        motor.set_position(LIFT_LOWER_LIMIT, DEGREES)
    lift_ready = True
    show_speed()


def control_lift():
    if not LIFT_ENABLED or not lift_ready:
        for motor in lift_motors:
            motor.stop()
        return

    up = controller.buttonL2.pressing()
    down = controller.buttonL1.pressing()    
    output = 0

    if up and not down:
        # 상승하면 두 각도가 모두 감소함
        # 하나라도 -1400도에 닿으면 기구가 기울지 않게 둘 다 멈춤
        if all(m.position(DEGREES) > LIFT_UPPER_LIMIT for m in lift_motors):
            output = -LIFT_SPEED
    elif down and not up:
        # 하강하면 각도가 증가하고 하나라도 0도에 닿으면 둘 다 정지
        if all(m.position(DEGREES) < LIFT_LOWER_LIMIT for m in lift_motors):
            output = LIFT_SPEED

    # 양쪽 버튼을 놓거나 같이 눌러도 output은 0이라 HOLD로 정지
    # 이 처리는 끝 위치 제한이며, 양쪽 높이를 자동 동기화하는 기능은 아님
    for motor in lift_motors:
        command_motor(motor, output)

def confirm_claw_reference():
    global claw_ready

    # 한 번 기준을 등록하면 프로그램을 다시 켜기 전까지 재등록하지 않음
    # 집게를 벌린 상태에서 실수로 X를 눌러 기준이 바뀌는 것을 방지
    if claw_ready or not CLAW_ENABLED or not claw_motors:
        return
    
    # 집게를 움직이는 중에는 기준 위치를 바꾸지 못하게 함
    if controller.buttonR1.pressing() or controller.buttonR2.pressing():
        return

    for motor in claw_motors:
        motor.stop()

        # 측정 당시 -59도였던 실제 위치에 집게를 맞추고 X 누르기 ########################### 수정 필요(코드는 변수만 바꾸면 되기 때문에 주석만 수정) ##############################
        # X는 현재 위치에 이름표를 붙이는 것이라 자동으로 닫아주지는 않음
        motor.set_position(CLAW_CLOSED_LIMIT, DEGREES)

    claw_ready = True
    show_speed()


def control_claw():
    if not claw_motors:
        return

    # X로 기준 위치를 등록하기 전에는 집게 조작을 막음
    if not CLAW_ENABLED or not claw_ready:
        for motor in claw_motors:
            motor.stop()
        return

    opening = controller.buttonR1.pressing()
    closing = controller.buttonR2.pressing()

    for motor in claw_motors:
        position = motor.position(DEGREES)

        # 둘 다 누르거나 둘 다 놓으면 정지
        if opening == closing:
            motor.stop()

        elif opening:
            # 집게가 열릴수록 각도가 감소함
            # -388도에 도달하면 더 벌리지 않고 멈춤 ########################### 수정 필요(코드는 변수만 바꾸면 되기 때문에 주석만 수정) ##############################
            if position > CLAW_OPEN_LIMIT:
                motor.spin(REVERSE, CLAW_SPEED, PERCENT)
            else:
                motor.stop()

        elif closing:
            # 닫힐수록 각도가 증가함
            # -59도에 도달하면 더 닫지 않고 멈춤 ########################### 수정 필요(코드는 변수만 바꾸면 되기 때문에 주석만 수정) ##############################
            if position < CLAW_CLOSED_LIMIT:
                motor.spin(FORWARD, CLAW_SPEED, PERCENT)
            else:
                motor.stop()


# 프로그램을 시작할 때마다 도르레는 A, 집게는 X로 기준 등록
controller.buttonA.pressed(confirm_lift_reference)
controller.buttonX.pressed(confirm_claw_reference)

# 최고속도는 고정이므로 위/아래 버튼에 속도 변경 기능을 연결하지 않음
show_speed()

while True:
    # 왼쪽 스틱은 전진/후진과 옆 이동, 오른쪽 스틱 좌우는 회전
    forward = apply_deadzone(controller.axis3.position())
    strafe = apply_deadzone(controller.axis4.position())
    turn = -apply_deadzone(controller.axis1.position())

    # 조금 밀면 섬세하게 움직이고, 끝까지 밀면 원래 최대 입력
    forward = forward * abs(forward) / 100
    strafe = strafe * abs(strafe) / 100
    turn = turn * abs(turn) / 100

    # 옴니휠을 45도로 장착한 일반적인 X-drive 배치를 기준으로 계산
    # 회전 입력이 0이면 양수 strafe에서 왼쪽 앞과 오른쪽 뒤를 정방향으로 구동
    front_left_speed = forward + strafe + turn
    front_right_speed = forward - strafe - turn
    rear_left_speed = forward - strafe + turn
    rear_right_speed = forward + strafe - turn

    # 입력을 합쳐도 최고속도를 넘지 않게 네 바퀴를 같은 비율로 줄임
    largest = max(
        abs(front_left_speed), abs(front_right_speed),
        abs(rear_left_speed), abs(rear_right_speed), 100
    )
    front_left_speed = front_left_speed / largest * speed_limit
    front_right_speed = front_right_speed / largest * speed_limit
    rear_left_speed = rear_left_speed / largest * speed_limit
    rear_right_speed = rear_right_speed / largest * speed_limit
    command_motor(left_front, front_left_speed)
    command_motor(right_front, front_right_speed)
    command_motor(left_rear, rear_left_speed)
    command_motor(right_rear, rear_right_speed)

    # L2 상승 / L1 하강. 버튼을 놓으면 정지
    control_lift()
    
    
    # 집게는 열릴 때 각도가 감소하므로 전용 제한 함수를 사용
    control_claw()
    
    # 왼쪽 방향키: 위 / 오른쪽 방향키: 아래
    control_limited(
       wrist_motors, WRIST_ENABLED, WRIST_MAX_DEG,
        controller.buttonLeft.pressing(),
        controller.buttonRight.pressing(),
        WRIST_SPEED
    )
    wait(20, MSEC)
