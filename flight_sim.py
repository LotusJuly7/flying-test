import math
import time
from dataclasses import dataclass

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *


HUD_FONT = globals().get("GLUT_BITMAP_9_BY_15") or globals().get("GLUT_BITMAP_HELVETICA_12")

WINDOW_W = 1280
WINDOW_H = 720


@dataclass
class AircraftState:
    x: float = 0.0
    y: float = 120.0
    z: float = 0.0

    speed: float = 60.0
    throttle: float = 0.0

    pitch: float = 0.0  # degrees, nose up positive
    roll: float = 0.0   # degrees, right wing down positive
    yaw: float = 0.0    # heading degrees

    pitch_rate_cmd: float = 0.0
    roll_rate_cmd: float = 0.0
    yaw_rate_cmd: float = 0.0


state = AircraftState()
last_time = time.time()

# continuous key states
special_keys = set()
normal_keys = set()


# physics params (toy model)
MASS = 1200.0
GRAVITY = 9.81
MAX_THRUST = 24000.0
DRAG_COEF = 0.030
LIFT_COEF = 55.0
STALL_SPEED = 28.0

MAX_ROLL_RATE = 55.0   # deg/s
MAX_PITCH_RATE = 35.0  # deg/s
MAX_YAW_RATE = 25.0    # deg/s


# ---------- utility ----------
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def deg2rad(a):
    return a * math.pi / 180.0


def forward_vector(pitch_deg, yaw_deg):
    pitch = deg2rad(pitch_deg)
    yaw = deg2rad(yaw_deg)
    cp = math.cos(pitch)
    sp = math.sin(pitch)
    cy = math.cos(yaw)
    sy = math.sin(yaw)
    # world axes: x-right, y-up, z-forward
    return (
        sy * cp,
        sp,
        cy * cp,
    )


# ---------- terrain ----------
def terrain_height(x, z):
    # Simple procedural hills
    return (
        8.0 * math.sin(0.02 * x)
        + 5.0 * math.cos(0.018 * z)
        + 3.0 * math.sin(0.015 * (x + z))
    )


def draw_terrain(size=1800, step=24):
    half = size // 2
    glColor3f(0.22, 0.56, 0.26)

    for z in range(-half, half, step):
        glBegin(GL_TRIANGLE_STRIP)
        for x in range(-half, half + step, step):
            y1 = terrain_height(x, z)
            y2 = terrain_height(x, z + step)
            glVertex3f(x, y1, z)
            glVertex3f(x, y2, z + step)
        glEnd()


# ---------- aircraft model (triangles) ----------
def draw_aircraft_model():
    # fuselage
    glColor3f(0.83, 0.83, 0.85)
    glBegin(GL_TRIANGLES)
    # nose cone
    glVertex3f(0.0, 0.0, 9.0)
    glVertex3f(-0.9, 0.5, 2.5)
    glVertex3f(0.9, 0.5, 2.5)

    glVertex3f(0.0, 0.0, 9.0)
    glVertex3f(0.9, -0.5, 2.5)
    glVertex3f(-0.9, -0.5, 2.5)

    # mid body
    glVertex3f(-0.9, 0.5, 2.5)
    glVertex3f(-0.9, -0.5, 2.5)
    glVertex3f(-0.7, 0.0, -5.5)

    glVertex3f(0.9, -0.5, 2.5)
    glVertex3f(0.9, 0.5, 2.5)
    glVertex3f(0.7, 0.0, -5.5)

    glVertex3f(-0.9, 0.5, 2.5)
    glVertex3f(0.9, 0.5, 2.5)
    glVertex3f(0.0, 0.7, -3.2)

    glVertex3f(0.9, -0.5, 2.5)
    glVertex3f(-0.9, -0.5, 2.5)
    glVertex3f(0.0, -0.7, -3.2)

    # tail cone
    glVertex3f(-0.7, 0.0, -5.5)
    glVertex3f(0.7, 0.0, -5.5)
    glVertex3f(0.0, 0.0, -8.5)

    # main wings (left)
    glVertex3f(-0.4, 0.0, 0.0)
    glVertex3f(-12.0, 0.1, -1.5)
    glVertex3f(-4.0, 0.0, 2.0)

    glVertex3f(-0.3, 0.0, -0.8)
    glVertex3f(-9.5, -0.1, -3.0)
    glVertex3f(-12.0, 0.1, -1.5)

    # main wings (right)
    glVertex3f(0.4, 0.0, 0.0)
    glVertex3f(12.0, 0.1, -1.5)
    glVertex3f(4.0, 0.0, 2.0)

    glVertex3f(0.3, 0.0, -0.8)
    glVertex3f(9.5, -0.1, -3.0)
    glVertex3f(12.0, 0.1, -1.5)

    # vertical stabilizer
    glVertex3f(0.0, 0.2, -5.5)
    glVertex3f(0.0, 3.1, -6.8)
    glVertex3f(0.0, 0.0, -8.0)

    # horizontal tail left/right
    glVertex3f(-0.2, 0.0, -6.0)
    glVertex3f(-3.4, 0.1, -7.2)
    glVertex3f(-1.0, 0.0, -8.0)

    glVertex3f(0.2, 0.0, -6.0)
    glVertex3f(3.4, 0.1, -7.2)
    glVertex3f(1.0, 0.0, -8.0)
    glEnd()


def draw_hud():
    text = (
        f"Speed {state.speed:6.1f} m/s  Alt {state.y:6.1f} m  "
        f"Pitch {state.pitch:6.1f}  Roll {state.roll:6.1f}  Yaw {state.yaw:6.1f}"
    )

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glDisable(GL_DEPTH_TEST)
    glColor3f(1.0, 1.0, 1.0)
    glRasterPos2f(15, WINDOW_H - 24)
    for ch in text:
        if HUD_FONT is not None:
            glutBitmapCharacter(HUD_FONT, ord(ch))

    glEnable(GL_DEPTH_TEST)
    glPopMatrix()

    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def handle_controls(dt):
    # Up/Down arrows = accelerate/decelerate throttle command
    if GLUT_KEY_UP in special_keys:
        state.throttle += 0.70 * dt
    if GLUT_KEY_DOWN in special_keys:
        state.throttle -= 0.70 * dt
    state.throttle = clamp(state.throttle, -0.2, 1.0)

    # Left/Right arrows = roll
    state.roll_rate_cmd = 0.0
    if GLUT_KEY_LEFT in special_keys:
        state.roll_rate_cmd = MAX_ROLL_RATE
    if GLUT_KEY_RIGHT in special_keys:
        state.roll_rate_cmd = -MAX_ROLL_RATE

    # PgUp=nose down, PgDn=nose up
    state.pitch_rate_cmd = 0.0
    if GLUT_KEY_PAGE_UP in special_keys:
        state.pitch_rate_cmd = MAX_PITCH_RATE
    if GLUT_KEY_PAGE_DOWN in special_keys:
        state.pitch_rate_cmd = -MAX_PITCH_RATE

    # A / D = yaw left / right
    state.yaw_rate_cmd = 0.0
    if b'a' in normal_keys or b'A' in normal_keys:
        state.yaw_rate_cmd = MAX_YAW_RATE
    if b'd' in normal_keys or b'D' in normal_keys:
        state.yaw_rate_cmd = -MAX_YAW_RATE


def integrate_flight(dt):
    # attitude integration
    state.roll += state.roll_rate_cmd * dt
    state.pitch += state.pitch_rate_cmd * dt
    state.yaw += state.yaw_rate_cmd * dt

    state.roll = clamp(state.roll, -70.0, 70.0)
    state.pitch = clamp(state.pitch, -35.0, 35.0)

    # forces: thrust + drag + lift - weight
    thrust = state.throttle * MAX_THRUST
    drag = DRAG_COEF * state.speed * state.speed

    # lift drops near stall speed
    stall_factor = clamp((state.speed - STALL_SPEED) / (STALL_SPEED * 0.8), 0.0, 1.0)
    lift = LIFT_COEF * state.speed * state.speed * (0.3 + 0.7 * stall_factor)

    forward_acc = (thrust - drag) / MASS
    vertical_acc = (lift * math.cos(deg2rad(state.roll)) - MASS * GRAVITY) / MASS

    state.speed += forward_acc * dt
    state.speed = clamp(state.speed, 8.0, 320.0)

    # gravity effect from pitch and lift
    vx, vy, vz = forward_vector(state.pitch, state.yaw)
    climb_from_pitch = vy * state.speed
    climb_from_lift = vertical_acc * dt * 12.0
    climb_rate = climb_from_pitch + climb_from_lift

    # horizontal turning by bank angle
    turn_rate = math.tan(deg2rad(state.roll)) * (state.speed / 180.0)
    state.yaw += math.degrees(turn_rate) * dt

    # position integrate
    state.x += vx * state.speed * dt
    state.z += vz * state.speed * dt
    state.y += climb_rate * dt

    # ground collision floor
    ground = terrain_height(state.x, state.z) + 4.0
    if state.y < ground:
        state.y = ground
        state.pitch = max(0.0, state.pitch)
        state.speed *= 0.96


def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    # chase camera behind aircraft
    fx, fy, fz = forward_vector(state.pitch, state.yaw)
    cam_dist = 85.0
    cam_h = 24.0
    cx = state.x - fx * cam_dist
    cy = state.y + cam_h
    cz = state.z - fz * cam_dist

    gluLookAt(cx, cy, cz, state.x, state.y, state.z, 0.0, 1.0, 0.0)

    draw_terrain()

    glPushMatrix()
    glTranslatef(state.x, state.y, state.z)
    glRotatef(state.yaw, 0, 1, 0)
    glRotatef(state.pitch, 1, 0, 0)
    glRotatef(state.roll, 0, 0, -1)
    draw_aircraft_model()
    glPopMatrix()

    draw_hud()
    glutSwapBuffers()


def idle():
    global last_time
    now = time.time()
    dt = min(0.033, now - last_time)
    last_time = now

    handle_controls(dt)
    integrate_flight(dt)
    glutPostRedisplay()


def reshape(w, h):
    global WINDOW_W, WINDOW_H
    WINDOW_W, WINDOW_H = max(1, w), max(1, h)

    glViewport(0, 0, WINDOW_W, WINDOW_H)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60.0, WINDOW_W / WINDOW_H, 0.5, 6000.0)
    glMatrixMode(GL_MODELVIEW)


def key_down(k, _x, _y):
    normal_keys.add(k)
    if k == b'\x1b':  # ESC
        raise SystemExit


def key_up(k, _x, _y):
    if k in normal_keys:
        normal_keys.remove(k)


def special_down(k, _x, _y):
    special_keys.add(k)


def special_up(k, _x, _y):
    if k in special_keys:
        special_keys.remove(k)


def init_gl():
    glClearColor(0.44, 0.69, 0.96, 1.0)
    glEnable(GL_DEPTH_TEST)
    glShadeModel(GL_SMOOTH)


def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_W, WINDOW_H)
    glutCreateWindow(b"PyOpenGL Flight Sim")

    init_gl()

    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutIdleFunc(idle)

    glutKeyboardFunc(key_down)
    glutKeyboardUpFunc(key_up)
    glutSpecialFunc(special_down)
    glutSpecialUpFunc(special_up)

    glutMainLoop()


if __name__ == "__main__":
    main()
