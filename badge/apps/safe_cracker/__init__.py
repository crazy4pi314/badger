import os
import sys
import math

APP_DIR = "/system/apps/safe_cracker"
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

from badgeware import State
from gesture import GestureRecognizer

screen.font = font.nope

BG = color.rgb(17, 23, 31)
PANEL = color.rgb(37, 47, 59)
STEEL = color.rgb(144, 164, 174)
DIM = color.rgb(90, 105, 115)
GOLD = color.rgb(245, 190, 62)
GREEN = color.rgb(66, 205, 120)
RED = color.rgb(238, 86, 78)
WHITE = color.rgb(245, 247, 250)

GESTURES = ("TURN_LEFT", "TURN_RIGHT", "TIP_UP", "TIP_DOWN")
LABELS = {
    "TURN_LEFT": "TURN LEFT",
    "TURN_RIGHT": "TURN RIGHT",
    "TIP_UP": "TIP UP",
    "TIP_DOWN": "TIP DOWN",
}
SYMBOLS = {
    "TURN_LEFT": "<",
    "TURN_RIGHT": ">",
    "TIP_UP": "^",
    "TIP_DOWN": "v",
}
BUTTONS = {
    BUTTON_LEFT: "TURN_LEFT",
    BUTTON_RIGHT: "TURN_RIGHT",
    BUTTON_UP: "TIP_UP",
    BUTTON_DOWN: "TIP_DOWN",
}


class Screen:
    INTRO = 0
    CALIBRATE = 1
    TEACH = 2
    PLAY = 3
    FEEDBACK = 4
    OPEN = 5


saved = {"best_streak": 0}
State.load("safe_cracker", saved)

view = Screen.INTRO
motion_mode = True
practice_mode = False
diagnostics = False
recognizer = GestureRecognizer()
combination = []
step = 0
streak = 0
message = ""
message_pen = WHITE
state_started_at = badge.ticks
seed = badge.ticks or 1


def next_random(limit):
    global seed
    seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
    return seed % limit


def make_combination():
    length = min(3 + streak // 2, 6)
    result = []
    while len(result) < length:
        gesture = GESTURES[next_random(len(GESTURES))]
        if not result or gesture != result[-1]:
            result.append(gesture)
    return result


def enter(new_view):
    global view, state_started_at
    view = new_view
    state_started_at = badge.ticks


def start_game():
    global combination, step
    combination = make_combination()
    step = 0
    if motion_mode:
        recognizer.reset(badge.ticks)
        enter(Screen.CALIBRATE)
    else:
        enter(Screen.TEACH)


def handle_intro():
    global motion_mode, practice_mode

    if badge.pressed(BUTTON_LEFT) or badge.pressed(BUTTON_RIGHT):
        motion_mode = not motion_mode
    if badge.pressed(BUTTON_UP) or badge.pressed(BUTTON_DOWN):
        practice_mode = not practice_mode
    if badge.pressed(BUTTON_SELECT):
        start_game()


def handle_calibration():
    recognizer.update(badge.imu(), badge.ticks)
    if recognizer.calibrated:
        enter(Screen.TEACH)
    elif badge.pressed(BUTTON_BACK):
        enter(Screen.INTRO)


def handle_teach():
    if badge.pressed(BUTTON_SELECT):
        enter(Screen.PLAY)
    elif badge.pressed(BUTTON_BACK):
        enter(Screen.INTRO)


def read_button_gesture():
    for button, gesture in BUTTONS.items():
        if badge.pressed(button):
            return gesture
    return None


def handle_play():
    gesture = None
    if motion_mode:
        result = recognizer.update(badge.imu(), badge.ticks)
        if result and result["confidence"] >= 0.35:
            gesture = result["label"]
    else:
        gesture = read_button_gesture()

    if gesture:
        check_step(gesture)
    elif badge.pressed(BUTTON_BACK):
        enter(Screen.INTRO)


def check_step(gesture):
    global step, message, message_pen, streak

    if gesture == combination[step]:
        step += 1
        message = "CLICK!"
        message_pen = GREEN
        if step == len(combination):
            streak += 1
            if streak > saved["best_streak"]:
                saved["best_streak"] = streak
                State.save("safe_cracker", saved)
            enter(Screen.OPEN)
        else:
            enter(Screen.FEEDBACK)
        return

    message = "MISSED - TRY AGAIN"
    message_pen = RED
    if not practice_mode:
        streak = 0
    step = 0
    enter(Screen.FEEDBACK)


def handle_feedback():
    if badge.ticks - state_started_at >= 650:
        enter(Screen.PLAY)


def handle_open():
    if badge.pressed(BUTTON_SELECT):
        start_game()
    elif badge.pressed(BUTTON_BACK):
        enter(Screen.INTRO)


def draw_background():
    screen.pen = BG
    screen.rectangle(screen.clip)
    screen.pen = PANEL
    screen.shape(shape.rounded_rectangle(8, 7, screen.width - 16, screen.height - 14, 8))
    screen.pen = STEEL
    screen.shape(shape.rounded_rectangle(12, 11, screen.width - 24, screen.height - 22, 6))
    screen.pen = PANEL
    screen.shape(shape.rounded_rectangle(15, 14, screen.width - 30, screen.height - 28, 5))


def centered(text, y, pen=WHITE):
    width, _ = screen.measure_text(text)
    screen.pen = pen
    screen.text(text, (screen.width - width) / 2, y)


def draw_dial(angle=0, open_amount=0):
    x = screen.width / 2
    y = 55
    radius = 25 + open_amount
    screen.pen = color.rgb(8, 12, 17, 100)
    screen.shape(shape.circle(x + 2, y + 2, radius + 3))
    screen.pen = DIM
    screen.shape(shape.circle(x, y, radius + 3))
    screen.pen = PANEL
    screen.shape(shape.circle(x, y, radius))
    screen.pen = GOLD
    for index in range(12):
        radians = (angle + index * 30) * 0.0174532925
        outer_x = x + math.sin(radians) * (radius - 2)
        outer_y = y - math.cos(radians) * (radius - 2)
        inner_x = x + math.sin(radians) * (radius - 6)
        inner_y = y - math.cos(radians) * (radius - 6)
        screen.line(inner_x, inner_y, outer_x, outer_y)
    screen.shape(shape.circle(x, y, 4))


def draw_progress():
    spacing = 18
    start = (screen.width - (len(combination) - 1) * spacing) / 2
    for index, gesture in enumerate(combination):
        if index < step:
            pen = GREEN
        elif index == step and view in (Screen.PLAY, Screen.FEEDBACK):
            pen = GOLD
        else:
            pen = DIM
        centered_at(SYMBOLS[gesture], start + index * spacing, 88, pen)


def centered_at(text, x, y, pen):
    width, _ = screen.measure_text(text)
    screen.pen = pen
    screen.text(text, x - width / 2, y)


def draw_intro():
    centered("SAFE CRACKER", 20, GOLD)
    draw_dial((badge.ticks / 12) % 360)
    centered("< %s >" % ("MOTION" if motion_mode else "BUTTONS"), 84)
    centered("^ %s v" % ("PRACTICE" if practice_mode else "STREAK"), 97, DIM)
    centered("SELECT TO START", 108, WHITE)


def draw_calibration():
    centered("HOLD STILL", 23, GOLD)
    draw_dial()
    width = 86
    screen.pen = DIM
    screen.rectangle((screen.width - width) / 2, 91, width, 7)
    screen.pen = GREEN
    screen.rectangle(
        (screen.width - width) / 2,
        91,
        width * recognizer.calibration_progress,
        7,
    )
    centered("calibrating motion", 103, WHITE)


def draw_teach():
    centered("COMBINATION", 20, GOLD)
    centered("MEMORIZE", 33, DIM)
    y = 57
    for index, gesture in enumerate(combination):
        centered_at(SYMBOLS[gesture], 45 + index * (70 / max(1, len(combination) - 1)), y, WHITE)
    centered("SELECT WHEN READY", 96, WHITE)
    centered("Best streak: %d" % saved["best_streak"], 108, DIM)


def draw_play():
    centered("STEP %d OF %d" % (step + 1, len(combination)), 19, GOLD)
    angle = (badge.ticks / 5) % 360 if recognizer.state == recognizer.MOVING else step * 35
    draw_dial(angle)
    draw_progress()
    if step < len(combination):
        if motion_mode:
            centered("Move: %s" % LABELS[combination[step]], 104, WHITE)
        else:
            centered("Press the matching arrow", 104, WHITE)


def draw_feedback():
    draw_play()
    centered(message, 75, message_pen)


def draw_open():
    pulse = int((badge.ticks - state_started_at) / 40) % 7
    centered("SAFE OPEN!", 20, GREEN)
    draw_dial((badge.ticks / 4) % 360, pulse / 3)
    centered("Streak: %d" % streak, 88, WHITE)
    centered("Best: %d" % saved["best_streak"], 99, DIM)
    centered("SELECT: NEXT", 108, GOLD)


def draw_diagnostics():
    centered("MOTION DIAGNOSTICS", 19, GOLD)
    screen.pen = WHITE
    screen.text("state: %d" % recognizer.state, 24, 37)
    screen.text(
        "gyro: %d %d %d" % tuple(recognizer.last_sample[3:]),
        24,
        51,
    )
    screen.text(
        "base: %d %d %d" % tuple(int(value) for value in recognizer.baseline[3:]),
        24,
        65,
    )
    screen.text(
        "gate: %d %d %d" % tuple(int(value) for value in recognizer.gyro_thresholds),
        24,
        79,
    )
    centered("MENU TO CLOSE", 103, DIM)


def update():
    global diagnostics

    draw_background()

    if badge.pressed(BUTTON_MENU):
        diagnostics = not diagnostics
    if diagnostics:
        draw_diagnostics()
        return

    if view == Screen.INTRO:
        handle_intro()
        draw_intro()
    elif view == Screen.CALIBRATE:
        handle_calibration()
        draw_calibration()
    elif view == Screen.TEACH:
        handle_teach()
        draw_teach()
    elif view == Screen.PLAY:
        handle_play()
        draw_play()
    elif view == Screen.FEEDBACK:
        handle_feedback()
        draw_feedback()
    else:
        handle_open()
        draw_open()


badge.default_clear = BG
run(update)
