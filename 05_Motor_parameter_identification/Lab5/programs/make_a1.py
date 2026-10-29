"""Write block-diagram specs for Assignment 1: Program A (step series) and Program B (complex signal).

usage: python make_a1.py OUTDIR
Writes spec_steps_<M>.json and spec_<signal>_<M>.json for both drive motors (left M4/E4, right M3/E3).
Every program is pure blocks (no System Call / JS), as the assignment requires.
"""
import json
import sys
from pathlib import Path

OUT = Path(sys.argv[1])
MOTORS = {"M4": "encoder4", "M3": "encoder3"}   # left, right
TAG = "91"                                      # file suffix: classmates share the robot's scripts folder


def log_loop(prefix, cond, pwm, logfile, x, y):
    """Blocks + links for: while cond: read encoder, append line, wait 5 ms."""
    b = [
        {"id": f"{prefix}_loop", "type": "PreconditionalLoop", "props": {"Condition": cond}, "x": x, "y": y},
        {"id": f"{prefix}_read", "type": "Function", "props": {"Body": "theta = ENC\nt = time()"}, "x": x + 200, "y": y},
        {"id": f"{prefix}_write", "type": "TrikWriteToFile",
         "props": {"File": logfile, "Text": f'theta .. "," .. t .. "," .. {pwm} .. "\\n"'}, "x": x + 400, "y": y},
        {"id": f"{prefix}_wait", "type": "Timer", "props": {"Delay": "5"}, "x": x + 400, "y": y + 100},
    ]
    links = [[f"{prefix}_loop", f"{prefix}_read", "iteration"], [f"{prefix}_read", f"{prefix}_write"],
             [f"{prefix}_write", f"{prefix}_wait"], [f"{prefix}_wait", f"{prefix}_loop"]]
    return b, links


def fill(spec, motor):
    s = json.dumps(spec).replace("ENC", MOTORS[motor]).replace("MOTOR", motor)
    return json.loads(s)


def steps_spec(motor, run=""):
    logfile = f"steps_{motor}{run}_{TAG}.txt"
    blocks = [
        {"id": "start", "type": "InitialNode", "x": 0, "y": 0},
        {"id": "rm", "type": "TrikRemoveFile", "props": {"File": logfile}, "x": 0, "y": 100},
        {"id": "init", "type": "Function", "props": {"Body": "level = -100\nt0 = time()"}, "x": 0, "y": 200},
        {"id": "note", "type": "CommentBlock", "props": {"Comment":
            f"Program A: 3 s zero-drift record, then steps -100..100 % (10 % apart, 0 skipped) on MOTOR; "
            f"each step 2 s on + 1 s coasting, logged as angle, time, PWM into {logfile}"}, "x": 700, "y": 0},
    ]
    links = [["start", "rm"], ["rm", "init"], ["init", "z_loop"]]
    b, l = log_loop("z", "time() - t0 < 3000", "0", logfile, 0, 300); blocks += b; links += l
    blocks += [
        {"id": "s_loop", "type": "PreconditionalLoop", "props": {"Condition": "level <= 100"}, "x": 0, "y": 500},
        {"id": "nonzero", "type": "IfBlock", "props": {"Condition": "level != 0"}, "x": 0, "y": 600},
        {"id": "step_t0", "type": "Function", "props": {"Body": "t0 = time()"}, "x": 0, "y": 700},
        {"id": "motor_on", "type": "TrikV6EnginesForward", "props": {"Ports": "MOTOR", "Power": "level"}, "x": 0, "y": 800},
        {"id": "motor_off", "type": "TrikV6EnginesForward", "props": {"Ports": "MOTOR", "Power": "0"}, "x": 0, "y": 1100},
        {"id": "next", "type": "Function", "props": {"Body": "level = level + 10"}, "x": -250, "y": 1400},
        {"id": "stop", "type": "TrikV6EnginesStop", "props": {"Ports": "MOTOR", "Mode": "float"}, "x": -250, "y": 500},
        {"id": "end", "type": "FinalNode", "x": -250, "y": 600},
    ]
    links += [["z_loop", "s_loop", ""], ["s_loop", "nonzero", "iteration"], ["s_loop", "stop", ""], ["stop", "end"],
              ["nonzero", "step_t0", "true"], ["nonzero", "next", "false"], ["step_t0", "motor_on"], ["motor_on", "on_loop"]]
    b, l = log_loop("on", "time() - t0 < 2000", "level", logfile, 0, 900); blocks += b; links += l
    links += [["on_loop", "motor_off", ""], ["motor_off", "off_loop"]]
    b, l = log_loop("off", "time() - t0 < 3000", "0", logfile, 0, 1200); blocks += b; links += l
    links += [["off_loop", "next", ""], ["next", "s_loop"]]
    return fill({"blocks": blocks, "links": links}, motor)


SIGNALS = {
    # u(tau), tau in ms since the signal start; frac(x) = x - floor(x)
    "square": ("A = 60\nP = 1000\nT = 8000",
               "ph = tau / P - floor(tau / P)\nu = A * (1 - 2 * floor(2 * ph))",
               "square wave, A = 60 %, period 1 s, 8 s"),
    "chirp": ("A = 60\nF0 = 0.2\nF1 = 4\nT = 10000",
              "s = tau / 1000\nu = A * sin(2 * pi * (F0 * s + (F1 - F0) * s * s / (2 * T / 1000)))",
              "chirp (swept sine), A = 60 %, 0.2 -> 4 Hz over 10 s"),
}


def signal_spec(motor, kind):
    params, formula, desc = SIGNALS[kind]
    logfile = f"signal_{kind}_{motor}_{TAG}.txt"
    blocks = [
        {"id": "start", "type": "InitialNode", "x": 0, "y": 0},
        {"id": "rm", "type": "TrikRemoveFile", "props": {"File": logfile}, "x": 0, "y": 100},
        {"id": "init", "type": "Function", "props": {"Body": params + "\nt0 = time()"}, "x": 0, "y": 200},
        {"id": "note", "type": "CommentBlock", "props": {"Comment":
            f"Program B: {desc} on MOTOR, PWM recomputed every pass; then 1 s coasting. Log: angle, time, PWM -> {logfile}"},
         "x": 700, "y": 0},
        {"id": "sig_loop", "type": "PreconditionalLoop", "props": {"Condition": "time() - t0 < T"}, "x": 0, "y": 300},
        {"id": "signal", "type": "Function", "props": {"Body":
            "tau = time() - t0\n" + formula + "\nu = floor(u + 0.5)"}, "x": 200, "y": 300},
        {"id": "motor", "type": "TrikV6EnginesForward", "props": {"Ports": "MOTOR", "Power": "u"}, "x": 400, "y": 300},
        {"id": "read", "type": "Function", "props": {"Body": "theta = ENC\nt = time()"}, "x": 600, "y": 300},
        {"id": "write", "type": "TrikWriteToFile",
         "props": {"File": logfile, "Text": 'theta .. "," .. t .. "," .. u .. "\\n"'}, "x": 600, "y": 400},
        {"id": "wait", "type": "Timer", "props": {"Delay": "5"}, "x": 400, "y": 400},
        {"id": "motor_off", "type": "TrikV6EnginesForward", "props": {"Ports": "MOTOR", "Power": "0"}, "x": 0, "y": 500},
        {"id": "coast_t0", "type": "Function", "props": {"Body": "t0 = time()"}, "x": 0, "y": 600},
        {"id": "stop", "type": "TrikV6EnginesStop", "props": {"Ports": "MOTOR", "Mode": "float"}, "x": 0, "y": 900},
        {"id": "end", "type": "FinalNode", "x": 0, "y": 1000},
    ]
    links = [["start", "rm"], ["rm", "init"], ["init", "sig_loop"],
             ["sig_loop", "signal", "iteration"], ["signal", "motor"], ["motor", "read"], ["read", "write"],
             ["write", "wait"], ["wait", "sig_loop"], ["sig_loop", "motor_off", ""], ["motor_off", "coast_t0"],
             ["coast_t0", "c_loop"]]
    b, l = log_loop("c", "time() - t0 < 1000", "0", logfile, 0, 700); blocks += b; links += l
    links += [["c_loop", "stop", ""], ["stop", "end"]]
    return fill({"blocks": blocks, "links": links}, motor)


OUT.mkdir(parents=True, exist_ok=True)
for m in MOTORS:
    (OUT / f"spec_steps_{m}.json").write_text(json.dumps(steps_spec(m), indent=1), encoding="utf-8")
    (OUT / f"spec_steps_{m}_run2.json").write_text(json.dumps(steps_spec(m, "_run2"), indent=1), encoding="utf-8")
    for k in SIGNALS:
        (OUT / f"spec_{k}_{m}.json").write_text(json.dumps(signal_spec(m, k), indent=1), encoding="utf-8")
print("ok")
