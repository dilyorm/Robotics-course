"""Write tools/lab9_spec.json - the block diagram of the Lab 9 program.

The layout is one horizontal row per phase, the loop body reading left to right and the
buffer-write branch hanging below it, so the whole run is readable as a top-to-bottom
sequence of rows.

    python tools/make_diagram.py
    python ../../trik-studio-skill/trik-studio/scripts/qrs_tool.py build \
        tools/lab9_spec.json -o Lab9_gyro.qrs --template Gyro_demo.qrs --drop-code
    python ../../trik-studio-skill/trik-studio/scripts/qrs_tool.py wheels Lab9_gyro.qrs M4 M3
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "lab9_spec.json"

COL = 150          # px between blocks in a row
ROW = 380          # px between phase rows

blocks = []
links = []


def blk(bid, btype, x, y, **props):
    blocks.append({"id": bid, "type": btype, "x": x, "y": y,
                   "props": {k: str(v) for k, v in props.items()}})


def link(a, b, guard=""):
    links.append([a, b] + ([guard] if guard else []))


def note(bid, x, y, text):
    blk(bid, "CommentBlock", x, y, Comment=text)


# ---------------------------------------------------------------- header row
blk("start", "InitialNode", 0, 0)
blk("init", "Function", COL, 0, Body=(
    "-- geometry from Lab 5, used offline in the notebook\n"
    "-- r = 0.042 m, B = 0.194 m\n"
    "phase = \"init\"\n"
    "u = 0\n"
    "t = 0\n"
    "t0 = 0\n"
    "A = 0\n"
    "n = 0\n"
    "buf = \"\"\n"
    "gzcal = 0\n"
    "gzraw = 0\n"
    "tus = 0\n"
    "-- CSV header line, written once\n"
    "line = \"# t_us,phase,u,gz_cal,gz_raw,encL,encR\\n\""))
blk("rm", "TrikRemoveFile", 2 * COL, 0, File="lab9_gyro.csv")
blk("hdr", "TrikWriteToFile", 3 * COL, 0, File="lab9_gyro.csv", Text="line")
blk("clr", "TrikV62ClearEncoder", 4 * COL, 0, Ports="E3, E4")
blk("p_warm", "TrikPrintText", 5 * COL, 0, PrintText="warmup", FontSize="20")
blk("t_warm", "Timer", 6 * COL, 0, Delay="120000")

note("c_init", 0, -140,
     "phase  - phase label in every CSV line\n"
     "u      - wheel power, % (left gets -u)\n"
     "t      - seconds since phase start\n"
     "t0     - phase start, ms\n"
     "A      - rotation amplitude, %\n"
     "n      - samples waiting in buf\n"
     "buf    - CSV lines not yet written")
note("c_rm", 480, -140,
     "Write To File appends, so the old log goes first.\n"
     "The file lands in the robot's scripts folder.")
note("c_warm", 920, -140,
     "2 min, motors off, not logged.\n"
     "A MEMS gyro needs thermal equilibrium\n"
     "before its offset is stable.")

link("start", "init")
link("init", "rm")
link("rm", "hdr")
link("hdr", "clr")
link("clr", "p_warm")
link("p_warm", "t_warm")


# ------------------------------------------------------------------- a phase
def phase(tag, y, title, condition, motors, u_body, label, extra_notes=()):
    """One row: print -> set phase -> loop -> [u, motors] -> read -> log -> buffer branch."""
    x = 0
    blk(tag + "_print", "TrikPrintText", x, y, PrintText=title, FontSize="20")
    x += COL
    blk(tag + "_init", "Function", x, y, Body=(
        "phase = \"%s\"\n"
        "-- remember when this phase started\n"
        "t0 = time()" % tag))
    x += COL
    blk(tag + "_loop", "PreconditionalLoop", x, y, Condition=condition)
    x += COL

    if motors:
        blk(tag + "_u", "Function", x, y, Body=u_body)
        x += COL
        blk(tag + "_m3", "TrikV6EnginesForward", x, y, Ports="M3", Power="u")
        x += COL
        blk(tag + "_m4", "TrikV6EnginesBackward", x, y, Ports="M4", Power="u")
        x += COL

    blk(tag + "_raw", "TrikSystem", x, y, Code="true", Evaluate="false",
        Command="gzraw = brick.gyroscope().readRawData()[2];")
    x += COL
    blk(tag + "_g", "Function", x, y, Body=(
        "-- rate in mdeg/s and the sensor timestamp in us\n"
        "gzcal = gyroscope[2]\n"
        "tus = time() * 1000"))
    x += COL
    blk(tag + "_line", "Function", x, y, Body=(
        "-- one CSV line: t_us,phase,u,gz_cal,gz_raw,encL,encR\n"
        "line = tus .. \",\" .. phase .. \",\" .. u .. \",\" .. gzcal .. \",\" .. gzraw .. \",\" .. encoder4 .. \",\" .. encoder3 .. \"\\n\"\n"
        "-- keep it in memory; the card is written in blocks\n"
        "buf = buf .. line\n"
        "n = n + 1"))
    x += COL
    blk(tag + "_if", "IfBlock", x, y, Condition="n >= 200")
    ifx = x
    x += COL
    blk(tag + "_timer", "Timer", x, y, Delay="10")
    timer = tag + "_timer"

    # buffer-write branch, below the row
    blk(tag + "_write", "TrikWriteToFile", ifx, y + 150, File="lab9_gyro.csv", Text="buf")
    blk(tag + "_reset", "Function", ifx + COL, y + 150, Body=(
        "-- the block is on the card, start a new buffer\n"
        "buf = \"\"\n"
        "n = 0"))
    blk(tag + "_fi", "FiBlock", ifx + 2 * COL, y + 190)

    note(tag + "_note", 0, y - 70, label)
    for i, (nx, ny, text) in enumerate(extra_notes):
        note("%s_extra%d" % (tag, i), nx, ny, text)

    # body and back edge
    link(tag + "_print", tag + "_init")
    link(tag + "_init", tag + "_loop")
    link(tag + "_loop", tag + "_u" if motors else tag + "_raw", "iteration")
    chain = ([tag + "_u", tag + "_m3", tag + "_m4"] if motors else []) + \
            [tag + "_raw", tag + "_g", tag + "_line", tag + "_if"]
    for a, b in zip(chain, chain[1:]):
        link(a, b)
    link(tag + "_if", tag + "_write", "true")
    link(tag + "_if", tag + "_fi", "false")
    link(tag + "_write", tag + "_reset")
    link(tag + "_reset", tag + "_fi")
    link(tag + "_fi", timer)
    link(timer, tag + "_loop")


rotation_u = (
    "-- elapsed seconds inside this phase\n"
    "t = (time() - t0) / 1000\n"
    "-- amplitude 30 -> 60 -> 150 % at t = 12 s and t = 24 s\n"
    "A = 30 + 15 * (sgn(t - 12) + 1) + 45 * (sgn(t - 24) + 1)\n"
    "@SIGNAL@\n"
    "-- clip to the motor limit: 150 % becomes 100 %\n"
    "u = max(-100, min(100, u))")

# ---------------------------------------------------------------- phase rows
y = ROW
phase("static", y, "static 3 min", "time() - t0 < 180000", False, "",
      "STATIC LOG - 3 min, motors off",
      [(COL, y + 240,
        "One sample every ~10 ms. Every 200 samples the buffer is\n"
        "written to the card in one go, so file I/O does not stretch\n"
        "the sampling period."),
       (5 * COL, y + 240,
        "Gives the offset b0, the drift d,\n"
        "the resolution and the noise sigma.")])

phase("sin", y + ROW, "sin 36 s", "time() - t0 < 36000", True,
      rotation_u.replace("@SIGNAL@", "u = A * sin(2 * pi * t / 4)"),
      "SINE ROTATION - in place, period 4 s",
      [(5 * COL, y + ROW + 240,
        "In-place turn: right wheel +u, left wheel -u.\n"
        "150 % is clipped to 100 %, so the last 12 s run at\n"
        "maximum rate and the gyro saturates - that is how the\n"
        "measurement range is found (section 3).")])

phase("rect", y + 2 * ROW, "rect 36 s", "time() - t0 < 36000", True,
      rotation_u.replace("@SIGNAL@", "u = A * sgn(sin(2 * pi * t / 4))"),
      "SQUARE ROTATION - in place, period 4 s",
      [(5 * COL, y + 2 * ROW + 240,
        "Same amplitudes as the sine, but the robot spends most of\n"
        "the time at full turn rate - shows whether the scale\n"
        "factor holds at high rate (section 6).")])

phase("rest", y + 3 * ROW, "rest 3 s", "time() - t0 < 3000", False, "",
      "REST - 3 s at standstill, logged",
      [(COL, y + 3 * ROW + 240,
        "So the final gyro and encoder angles can be compared with\n"
        "the robot not moving.")])

# ---------------------------------------------------------------- endblock row
ye = y + 3 * ROW + 420
blk("stop", "TrikV6EnginesStop", 0, ye, Ports="M3, M4", Mode="float")
blk("flush", "TrikWriteToFile", COL, ye, File="lab9_gyro.csv", Text="buf")
blk("sync", "TrikSystem", 2 * COL, ye, Code="true", Evaluate="false",
    Command="script.system(\"sync\", true);")
blk("p_done", "TrikPrintText", 3 * COL, ye, PrintText="done", FontSize="20")
blk("end", "FinalNode", 4 * COL, ye)
note("c_end", 5 * COL, ye,
     "Stop the motors, write the last partial buffer, then sync so\n"
     "the file survives a power-off.\n"
     "Copy lab9_gyro.csv off the robot and run the notebook.")

link("t_warm", "static_print")
link("static_loop", "sin_print")
link("sin_loop", "rect_print")
link("rect_loop", "rest_print")
link("rest_loop", "stop")
link("stop", "flush")
link("flush", "sync")
link("sync", "p_done")
link("p_done", "end")

json.dump({"blocks": blocks, "links": links}, open(OUT, "w"), indent=1)
print("wrote %s - %d blocks, %d links" % (OUT, len(blocks), len(links)))
