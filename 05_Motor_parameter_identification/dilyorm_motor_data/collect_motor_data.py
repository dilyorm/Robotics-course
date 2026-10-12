# Lab 5 - motor parameter identification, automated data collection (TRIK, Python).
#
# One run = every PWM level from -100 % to +100 % in 5 % steps, for every wheel in WHEELS.
# Robot must be LIFTED (wheels spinning freely) unless you deliberately measure under load.
#
# Samples are kept in a Python list during the step and written to disk only after the
# motor is off, so file I/O does not stretch the sampling period.
#
# Output (on the robot, relative to the program's working directory):
#   dilyorm_motor_data/wheel_<N>_v_<PWM>.txt   one file per wheel and PWM level
#   dilyorm_motor_data/wheel_<N>_battery.txt   battery voltage at the start of that wheel's series
#   dilyorm_motor_data/run_info.txt            config + absolute path of the folder

import os
import time

OUT_DIR = "dilyorm_motor_data"

# (wheel_id, motor_port, encoder_port, label). Check ports against your robot.
WHEELS = [
    (1, "M4", "E4", "left"),
    (2, "M3", "E3", "right"),
]

RUN_TIME = 2.0      # s of recording per PWM level
DT = 0.002          # s, sleep between samples (actual period is longer; real time stamps are stored)
SETTLE_TIME = 0.5   # s after encoder reset, before the step
REST_TIME = 1.0     # s with motor off, so the wheel stops before the next level

LEVELS = list(range(-100, 0, 5)) + list(range(5, 105, 5))


def battery_volts():
    # -1 = no battery reading (the 2D simulator has no battery device)
    try:
        return float(brick.battery().readVoltage())
    except Exception:
        return -1.0


def show(line1, line2=""):
    d = brick.display()
    d.clear()
    d.addLabel(line1, 1, 1)
    d.addLabel(line2, 1, 30)
    d.redraw()


def record_step(motor, encoder, power):
    """Apply a PWM step from rest. Returns (samples, loaded_battery_V)."""
    encoder.reset()
    time.sleep(SETTLE_TIME)

    samples = []
    append = samples.append
    read = encoder.read
    clock = time.time

    t0 = clock()
    motor.setPower(power)               # the step: t = 0
    while True:
        a = read()
        t = clock() - t0
        if t > RUN_TIME:
            break
        append((int(round(t * 1000)), a))
        time.sleep(DT)
    loaded = battery_volts()            # voltage while the motor is still under power
    motor.powerOff()
    return samples, loaded


def save(wheel_id, label, motor_port, encoder_port, power, battery_start, battery_loaded, samples):
    name = os.path.join(OUT_DIR, "wheel_%d_v_%d.txt" % (wheel_id, power))
    with open(name, "w") as f:
        f.write("# wheel_id: %d\n" % wheel_id)
        f.write("# wheel_label: %s\n" % label)
        f.write("# motor_port: %s\n" % motor_port)
        f.write("# encoder_port: %s\n" % encoder_port)
        f.write("# pwm_percent: %d\n" % power)
        f.write("# battery_voltage: %s\n" % battery_start)
        f.write("# battery_voltage_loaded: %s\n" % battery_loaded)
        f.write("# format: time_ms angle_deg\n")
        for t_ms, angle in samples:
            f.write("%d %s\n" % (t_ms, angle))


def main():
    if not os.path.exists(OUT_DIR):
        os.makedirs(OUT_DIR)

    with open(os.path.join(OUT_DIR, "run_info.txt"), "w") as f:
        f.write("abs_path: %s\n" % os.path.abspath(OUT_DIR))
        f.write("started: %s\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
        f.write("wheels: %s\n" % (WHEELS,))
        f.write("levels: %s\n" % (LEVELS,))
        f.write("run_time_s: %s  dt_s: %s  settle_s: %s  rest_s: %s\n" % (RUN_TIME, DT, SETTLE_TIME, REST_TIME))
    print("Saving to " + os.path.abspath(OUT_DIR))

    for wheel_id, motor_port, encoder_port, label in WHEELS:
        motor = brick.motor(motor_port)
        encoder = brick.encoder(encoder_port)

        battery = battery_volts()
        with open(os.path.join(OUT_DIR, "wheel_%d_battery.txt" % wheel_id), "w") as f:
            f.write("battery_voltage: %s\n" % battery)
        print("Wheel %d (%s, %s/%s), battery %s V" % (wheel_id, label, motor_port, encoder_port, battery))

        for power in LEVELS:
            show("W%d %s PWM %d%%" % (wheel_id, label, power), "bat %.2f V" % battery)
            samples, loaded = record_step(motor, encoder, power)
            save(wheel_id, label, motor_port, encoder_port, power, battery, loaded, samples)
            dts = [b[0] - a[0] for a, b in zip(samples, samples[1:])]
            mean_dt = float(sum(dts)) / len(dts) if dts else 0.0
            print("W%d PWM %4d %%: %3d samples, mean dt %.1f ms, final %s deg, loaded %.2f V"
                  % (wheel_id, power, len(samples), mean_dt, samples[-1][1] if samples else "-", loaded))
            time.sleep(REST_TIME)

    show("DONE", OUT_DIR)
    brick.playTone(1000, 300)
    print("Done. Files in " + os.path.abspath(OUT_DIR))
    brick.stop()


main()
