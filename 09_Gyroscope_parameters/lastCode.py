# Lab 9 - gyroscope parameters: data collection (TRIK, Python).
#
# One run does the whole sequence from the lab README:
#   warmup  2 min  still, not logged
#   static  3 min  still, logged                      -> b0, drift, resolution, noise
#   sin     36 s   in-place rotation, A = 30 -> 60 -> 150 %   -> range, scale factor
#   rect    36 s   the same with a square wave
#   rest    3 s    still, logged
#
# Output on the robot, relative to the program's working directory:
#   lab9_gyro/lab9_gyro.csv   one line per sample
#   lab9_gyro/run_info.txt    config + absolute path of the folder
#
# CSV columns: t_us,phase,u,gz_cal,gz_raw,encL,encR
#   t_us   gyroscope timestamp, read()[3], microseconds
#   phase  warmup (not logged) / static / sin / rect / rest
#   u      commanded wheel power, % (right wheel; the left one gets -u)
#   gz_cal read()[2], mdeg/s
#   gz_raw readRawData()[2], uncalibrated counts
#   encL   encoder E4, deg since the last reset
#   encR   encoder E3, deg since the last reset
#
# Nothing is processed on the robot: all calibration and fitting happens offline.

import math
import os
import time

OUT_DIR = "lab9_gyro"
OUT_FILE = os.path.join(OUT_DIR, "lab9_gyro.csv")

# Check the ports against your robot: on the course robots M3/E3 is the right wheel.
MOTOR_RIGHT = "M3"
MOTOR_LEFT = "M4"
ENC_RIGHT = "E3"
ENC_LEFT = "E4"

WARMUP_S = 120.0
STATIC_S = 180.0
REST_S = 3.0
DT = 0.010              # s, target sampling period (the real one is longer, timestamps are logged)

PERIOD = 4.0            # s, one period of the rotation signal
AMPLITUDES = (30, 60, 150)
PERIODS_PER_AMPLITUDE = 3
ROTATION_S = PERIOD * PERIODS_PER_AMPLITUDE * len(AMPLITUDES)

BLOCK = 200             # samples buffered before a write, so file I/O does not stretch the loop


def show(line1, line2=""):
    d = brick.display()
    d.clear()
    d.addLabel(line1, 1, 1)
    d.addLabel(line2, 1, 30)
    d.redraw()


def clip(x):
    return -100 if x < -100 else 100 if x > 100 else x


def set_power(u):
    brick.motor(MOTOR_RIGHT).setPower(int(u))
    brick.motor(MOTOR_LEFT).setPower(int(-u))


def stop():
    brick.motor(MOTOR_RIGHT).powerOff()
    brick.motor(MOTOR_LEFT).powerOff()


class Log(object):
    def __init__(self, path):
        self.f = open(path, "a")
        self.buf = []
        self.n = 0

    def line(self, phase, u):
        g = brick.gyroscope().read()
        raw = brick.gyroscope().readRawData()
        # the 2D model may return a shorter list than the real sensor
        t_us = g[3] if len(g) > 3 else int(time.time() * 1000000)
        self.buf.append("%d,%s,%d,%d,%d,%.1f,%.1f\n" % (
            t_us, phase, int(u), g[2], raw[2],
            brick.encoder(ENC_LEFT).read(), brick.encoder(ENC_RIGHT).read()))
        self.n += 1
        if len(self.buf) >= BLOCK:
            self.flush()

    def flush(self):
        if self.buf:
            self.f.write("".join(self.buf))
            self.buf = []
        self.f.flush()
        os.fsync(self.f.fileno())   # a switched-off robot loses cached files


def run_phase(log, phase, duration, u_of_t=None):
    """Log one phase. u_of_t(t) gives the wheel power; None means the motors stay off."""
    t0 = time.time()
    shown = -1
    while True:
        t = time.time() - t0
        if t >= duration:
            break
        u = 0 if u_of_t is None else u_of_t(t)
        if u_of_t is not None:
            set_power(u)
        log.line(phase, u)
        if int(t) != shown:
            shown = int(t)
            show(phase, "%d / %d s" % (shown, int(duration)))
        time.sleep(DT)
    log.flush()


def amplitude(t):
    i = int(t // (PERIOD * PERIODS_PER_AMPLITUDE))
    return AMPLITUDES[min(i, len(AMPLITUDES) - 1)]


def sine_u(t):
    return clip(amplitude(t) * math.sin(2 * math.pi * t / PERIOD))


def rect_u(t):
    return clip(amplitude(t) * (1 if math.sin(2 * math.pi * t / PERIOD) >= 0 else -1))


def main():
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)

    with open(os.path.join(OUT_DIR, "run_info.txt"), "w") as f:
        f.write("abs_path: %s\n" % os.path.abspath(OUT_DIR))
        f.write("started: %s\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
        f.write("motors: right=%s left=%s\n" % (MOTOR_RIGHT, MOTOR_LEFT))
        f.write("encoders: right=%s left=%s\n" % (ENC_RIGHT, ENC_LEFT))
        f.write("warmup_s: %s  static_s: %s  rest_s: %s  dt_s: %s\n"
                % (WARMUP_S, STATIC_S, REST_S, DT))
        f.write("rotation: Option A, sin + rect, T=%s s, A=%s %%, %s periods each\n"
                % (PERIOD, list(AMPLITUDES), PERIODS_PER_AMPLITUDE))

    log = Log(OUT_FILE)
    log.f.write("# lab9_gyro.csv - Lab 9 gyroscope parameters\n")
    log.f.write("# columns: t_us,phase,u,gz_cal,gz_raw,encL,encR\n")
    log.f.write("# gz_cal = gyroscope().read()[2] (mdeg/s), gz_raw = readRawData()[2], encoders in deg\n")
    log.f.write("# phases: warmup (not logged), static, sin, rect, rest\n")
    log.f.write("t_us,phase,u,gz_cal,gz_raw,encL,encR\n")
    log.flush()

    stop()
    show("warmup", "do not touch the robot")
    time.sleep(WARMUP_S)

    brick.encoder(ENC_LEFT).reset()
    brick.encoder(ENC_RIGHT).reset()
    run_phase(log, "static", STATIC_S)

    brick.encoder(ENC_LEFT).reset()
    brick.encoder(ENC_RIGHT).reset()
    run_phase(log, "sin", ROTATION_S, sine_u)
    stop()
    time.sleep(0.5)
    run_phase(log, "rect", ROTATION_S, rect_u)
    stop()

    run_phase(log, "rest", REST_S)

    log.flush()
    log.f.close()
    show("done", "%d samples" % log.n)
    print("Saving to " + os.path.abspath(OUT_DIR))
    print("%d samples" % log.n)


main()
