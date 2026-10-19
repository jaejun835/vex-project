from vex import *

brain = Brain()
controller = Controller(PRIMARY)

# 직접 확인한 방향 기준. 왼쪽은 반전, 오른쪽은 기본 방향.
# 초록색 카트리지를 쓰므로 기어비는 18:1로 맞춤.
left_front = Motor(Ports.PORT1, GearSetting.RATIO_18_1, True)
left_rear = Motor(Ports.PORT3, GearSetting.RATIO_18_1, True)
right_front = Motor(Ports.PORT2, GearSetting.RATIO_18_1, False)
right_rear = Motor(Ports.PORT4, GearSetting.RATIO_18_1, False)
drive_motors = [left_front, left_rear, right_front, right_rear]
for motor in drive_motors:
    motor.set_stopping(BRAKE)

# 스틱을 놓아도 조금씩 들어오는 값을 무시해서 저절로 움직이지 않게 함.
DEADZONE = 5
# 최고속도는 100%로 고정. 스틱을 조금 밀면 그만큼 천천히 움직임.
speed_limit = 100

# 집게 5번, 리프트 왼쪽 도르레 6번, 오른쪽 도르레 7번.
# 집게 회전용 별도 모터는 아직 지정하지 않음.
LIFT_PORT_1 = Ports.PORT6
LIFT_PORT_2 = Ports.PORT7
CLAW_PORT = Ports.PORT5
WRIST_PORT = None

# 측정 때 확인한 도르레 방향을 그대로 사용.
# 두 모터 모두 각도가 감소하는 REVERSE 방향이 리프트 상승.
LIFT_LEFT_REVERSED = False
LIFT_RIGHT_REVERSED = True
# 집게도 REVERSE로 열리고, FORWARD로 닫힘.
CLAW_REVERSED = False
WRIST_REVERSED = False

# 추가 모터도 일단 초록색 기준. 실제 카트리지가 다르면 수정하기.
LIFT_GEARS = GearSetting.RATIO_18_1
CLAW_GEARS = GearSetting.RATIO_18_1
WRIST_GEARS = GearSetting.RATIO_18_1

# 아래 각도는 기구 자체가 아니라 모터 축이 돌아간 각도.
# 실제 끝에 닿기 전에 멈추도록 여유를 두고 측정해서 넣기.
# 리프트는 아래쪽 기준에서 A를 눌러 두 모터를 0도로 등록.
# 집게는 측정 당시 -59도였던 실제 위치에서 X를 눌러 기준 등록.
LIFT_LOWER_LIMIT = 0
LIFT_UPPER_LIMIT = -2600
# A를 누르기 전에는 양쪽 도르레 모두 조작을 막음.
lift_ready = False
CLAW_CLOSED_LIMIT = -59
CLAW_OPEN_LIMIT = -388
# 시작할 때는 집게 위치를 모르므로, X로 기준을 확인하기 전까지 조작 금지.
claw_ready = False
WRIST_MAX_DEG = None

# 포트, 방향, 이동 범위와 시작 위치를 확인한 기구만 True로 변경.
LIFT_ENABLED = True
CLAW_ENABLED = True
WRIST_ENABLED = False

# 리프트는 사용자가 상승을 확인한 속도/토크 100% 설정.
# 끝에서 정지 지연이 생길 수 있어 -2600도 한계는 실제 기구에서 검증 필요.
LIFT_SPEED = 100
CLAW_SPEED = 40
WRIST_SPEED = 15

# 막힌 상태에서 과하게 미는 힘을 줄이기 위한 토크 제한.
# 이 수치가 기어에 안전하다는 보장은 없으므로 기구에 맞춰 확인해야 함.
LIFT_TORQUE = 100
CLAW_TORQUE = 15
WRIST_TORQUE = 20


def apply_deadzone(value):
    # abs는 부호를 뺀 크기. 전진과 후진의 작은 입력을 같이 걸러냄.
    return 0 if abs(value) < DEADZONE else value


def command_motor(motor, speed):
    # 0이면 stop을 써야 설정한 BRAKE/HOLD 방식으로 멈춤.
    if speed == 0:
        motor.stop()
    else:
        motor.spin(FORWARD, speed, PERCENT)


def create_motors(ports, gears, reversed_direction, torque, stopping):
    # 미설정 기구가 있어도 주행은 쓸 수 있도록 빈 목록을 반환함.
    if any(port is None for port in ports):
        return []
    motors = []
    for port in ports:
        motor = Motor(port, gears, reversed_direction)
        motor.set_max_torque(torque, PERCENT)
        motor.set_stopping(stopping)
        motors.append(motor)
    return motors


# 리프트와 회전축은 버튼을 놓으면 현재 위치를 유지하려고 힘을 줌.
# HOLD도 전원이 꺼지면 무게를 지탱하지 못하므로 기계적 지지가 필요함.
lift_left = Motor(LIFT_PORT_1, LIFT_GEARS, LIFT_LEFT_REVERSED)
lift_right = Motor(LIFT_PORT_2, LIFT_GEARS, LIFT_RIGHT_REVERSED)
lift_motors = [lift_left, lift_right]
for motor in lift_motors:
    motor.set_max_torque(LIFT_TORQUE, PERCENT)
    motor.set_stopping(HOLD)
# 집게는 일단 BRAKE 사용. 물체를 계속 잡아주는 힘은 보장하지 않음.
claw_motors = create_motors(
    [CLAW_PORT], CLAW_GEARS, CLAW_REVERSED, CLAW_TORQUE, BRAKE
)
wrist_motors = create_motors(
    [WRIST_PORT], WRIST_GEARS, WRIST_REVERSED, WRIST_TORQUE, HOLD
)


def set_reference(motors, enabled, maximum):
    # 현재 위치를 0이라고 기록할 뿐, 실제 원점을 찾아 움직이지는 않음.
    # 프로그램을 실행할 때마다 기구를 정해둔 기준 위치에 놓아야 함.
    if enabled and maximum is not None and maximum > 0:
        for motor in motors:
            motor.set_position(0, DEGREES)


# 리프트와 집게는 시작 위치를 자동으로 영점 처리하지 않음.
# 각각 A와 X를 눌러 실제 기준 위치를 확인한 후 등록.
set_reference(wrist_motors, WRIST_ENABLED, WRIST_MAX_DEG)


def control_limited(motors, enabled, maximum,
                    positive_button, negative_button, speed):
    if not motors:
        return
    if not enabled or maximum is None or maximum <= 0:
        for motor in motors:
            motor.stop()
        return

    # 양쪽 버튼을 같이 누르거나 모두 놓으면 정지.
    if positive_button == negative_button:
        output = 0
    elif positive_button:
        # 리프트처럼 두 모터가 있으면 하나라도 상한에 닿을 때 같이 정지.
        at_limit = any(m.position(DEGREES) >= maximum for m in motors)
        output = 0 if at_limit else speed
    else:
        # 하한은 0도. 제한에 걸려도 반대 방향으로 돌아오는 것은 허용됨.
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

    # 실행할 때마다 한 번만 등록. 움직인 다음 실수로 재등록하는 것을 막음.
    if lift_ready or not LIFT_ENABLED:
        return
    if controller.buttonL1.pressing() or controller.buttonL2.pressing():
        return

    # 측정할 때 A를 눌렀던 것과 같은 실제 아래쪽 위치에 놓고 등록하기.
    # 자동으로 내려가지 않으며, 현재 위치를 0도로 기록할 뿐임.
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
        # 상승하면 두 각도가 모두 감소함.
        # 하나라도 -2600도에 닿으면 기구가 기울지 않게 둘 다 멈춤.
        if all(m.position(DEGREES) > LIFT_UPPER_LIMIT for m in lift_motors):
            output = -LIFT_SPEED
    elif down and not up:
        # 하강하면 각도가 증가함. 하나라도 0도에 닿으면 둘 다 정지.
        if all(m.position(DEGREES) < LIFT_LOWER_LIMIT for m in lift_motors):
            output = LIFT_SPEED

    # 양쪽 버튼을 놓거나 같이 눌러도 output은 0이라 HOLD로 정지.
    # 이 처리는 끝 위치 제한이며, 양쪽 높이를 자동 동기화하는 기능은 아님.
    for motor in lift_motors:
        command_motor(motor, output)

def confirm_claw_reference():
    global claw_ready

    # 한 번 기준을 등록하면 프로그램을 다시 켜기 전까지 재등록하지 않음.
    # 집게를 벌린 상태에서 실수로 X를 눌러 기준이 바뀌는 것을 방지.
    if claw_ready or not CLAW_ENABLED or not claw_motors:
        return
    
    # 집게를 움직이는 중에는 기준 위치를 바꾸지 못하게 함.
    if controller.buttonR1.pressing() or controller.buttonR2.pressing():
        return

    for motor in claw_motors:
        motor.stop()

        # 측정 당시 -59도였던 실제 위치에 집게를 맞추고 X 누르기.
        # X는 현재 위치에 이름표를 붙이는 것이라 자동으로 닫아주지는 않음.
        motor.set_position(CLAW_CLOSED_LIMIT, DEGREES)

    claw_ready = True
    show_speed()


def control_claw():
    if not claw_motors:
        return

    # X로 기준 위치를 등록하기 전에는 집게 조작을 막음.
    if not CLAW_ENABLED or not claw_ready:
        for motor in claw_motors:
            motor.stop()
        return

    opening = controller.buttonR1.pressing()
    closing = controller.buttonR2.pressing()

    for motor in claw_motors:
        position = motor.position(DEGREES)

        # 둘 다 누르거나 둘 다 놓으면 정지.
        if opening == closing:
            motor.stop()

        elif opening:
            # 집게가 열릴수록 각도가 감소함.
            # -388도에 도달하면 더 벌리지 않고 멈춤.
            if position > CLAW_OPEN_LIMIT:
                motor.spin(REVERSE, CLAW_SPEED, PERCENT)
            else:
                motor.stop()

        elif closing:
            # 닫힐수록 각도가 증가함.
            # -59도에 도달하면 더 닫지 않고 멈춤.
            if position < CLAW_CLOSED_LIMIT:
                motor.spin(FORWARD, CLAW_SPEED, PERCENT)
            else:
                motor.stop()


# 프로그램을 시작할 때마다 도르레는 A, 집게는 X로 기준 등록.
controller.buttonA.pressed(confirm_lift_reference)
controller.buttonX.pressed(confirm_claw_reference)

# 최고속도는 고정이므로 위/아래 버튼에 속도 변경 기능을 연결하지 않음.
show_speed()

while True:
    # 왼쪽 상하: 전진/후진, 오른쪽 좌우: 회전.
    forward = apply_deadzone(controller.axis3.position())
    turn = apply_deadzone(controller.axis1.position())
    left_speed = forward + turn
    right_speed = forward - turn

    # 전진과 회전을 더하면 100을 넘을 수 있어 양쪽을 같은 비율로 줄임.
    # 마지막에 최고속도를 적용하므로 회전할 때도 설정값을 넘지 않음.
    largest = max(abs(left_speed), abs(right_speed), 100)
    left_speed = left_speed / largest * speed_limit
    right_speed = right_speed / largest * speed_limit
    command_motor(left_front, left_speed)
    command_motor(left_rear, left_speed)
    command_motor(right_front, right_speed)
    command_motor(right_rear, right_speed)

    # L2 상승 / L1 하강. 버튼을 놓으면 정지.
    control_lift()
    
    
    # 집게는 열릴 때 각도가 감소하므로 전용 제한 함수를 사용.
    control_claw()
    
    # 왼쪽 방향키: 위 / 오른쪽 방향키: 아래.
    control_limited(
       wrist_motors, WRIST_ENABLED, WRIST_MAX_DEG,
        controller.buttonLeft.pressing(),
        controller.buttonRight.pressing(),
        WRIST_SPEED
    )
    wait(20, MSEC)
