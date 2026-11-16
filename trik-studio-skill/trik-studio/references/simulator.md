# Headless 2D simulator (2D-model)

TRIK Studio ships `2D-model(.exe)` next to `trik-studio(.exe)`. `scripts/sim.py` wraps it; this file
explains what it does and the traps it works around (all verified on TRIK Studio 2025.4, Windows).

## Command sim.py runs

```
2D-model -b --platform offscreen -m diagram|script -c -t traj.json -r report.json --close prog.qrs
```
(run with the work dir as cwd, `QT_QPA_PLATFORM=offscreen`). `-b` = background: exits when the
program ends. `-s N` speeds up a windowed run; background runs are already faster than real time.
`--platform minimal` crashed in testing — use `offscreen`.

## Traps

| Trap | What happens | Workaround |
|---|---|---|
| `--script-path file.py` | ignored: nothing runs, no trajectory | embed code in the qrs (`sim.py run --code`, or `qrs_tool.py set-code`) |
| script mode file I/O | `script.writeToFile/removeFile/system` are **disabled** in the simulator | debug with `brick.display().addLabel(...)`; sim.py prints display text from the trajectory |
| script mode `print()` | not captured in background mode | same: use the display |
| script mode timestamps | trajectory `timestamp` is always 0 | one sample = 10 ms; sim.py estimates time from sample count |
| diagram mode Write To File | works; file appears in the cwd (work dir) | — |
| infinite programs | never exit (e.g. waiting for a button) | `--timeout` (sim.py kills it; trajectory so far is still summarized) |
| sensor not configured | error "No configured scalar sensor on port: A1" | configure the sensor in TRIK Studio (Robot settings) or don't read it in sim |
| `time.sleep()` in Python | real time, not simulated time | use `script.wait(ms)` |
| `brick.battery()` | returns nothing in the simulator | guard it (`try`/default value) |
| loop timing | diagram blocks tick every 10 ms; tight script loops run slower than on the robot | don't tune timing-sensitive controllers only in sim |
| version warning | "The world model has version ... Please check..." | harmless, filtered out |
| "Could not find platform independent libraries <prefix>" | harmless stderr from embedded Python | filtered out |

## Reading results

- `report.json`: list of `{level: info|error, message}`. Errors = runtime errors in the program.
  sim.py exits 1 if there are any.
- `traj.json`: list of robot samples `{robotId, x, y, rotation, timestamp}` (every 10 ms) mixed with
  device events `{device, port, property, value}` (display contents, etc.). Raw `x, y` = top-left
  corner of the robot's 50×50 px box (rotation is about the box centre), in px.
- sim.py converts to the **wheel-axle midpoint in cm** (the point that stays put in an in-place turn):
  scale 16 px = 5.6 cm (≈ 2.86 px/cm); axle = box centre − 15 px along the heading. y grows
  **downwards**; heading in degrees, positive = clockwise on screen.
- **Checkpoints**: sim.py prints every new robot-display text together with the pose at that moment
  and the distance since the previous one. Put `brick.display().addLabel("side 2", 1, 1)` (or a
  Print Text block) at each step of a program to get a per-leg / per-turn breakdown for free.
- Runs are not bit-for-bit repeatable (the model adds small random motor noise): expect ±1–2° and a
  few mm between identical runs; don't over-tune to one run.

### Simulated robot ≠ course robot

| | 2D model TRIK robot | course robot (professor's code) |
|---|---|---|
| wheel radius | 2.8 cm (16 px diameter) | 3.75 cm |
| track (wheel to wheel) | 44 px = 15.4 cm (encoder odometry with B = 15.4 matched ground truth to ~1 mm over 585° of turns) | 19.4 cm |

An encoder-based program written with the real numbers drives ~25 % short sides and ~86° turns in the
sim — that is the geometry, not a bug. Keep `R`/`TRACK` as constants at the top of the program and
test in sim with R = 2.8, TRACK = 15.4, then switch back for the robot (and calibrate there).
In the sim, encoder E*n* follows motor M*n* (E3 ↔ M3, E4 ↔ M4) and counts up when driving forward.
- The 2D robot is idealized (no dead zone, no motor lag unless `realisticMotors` is on in the world
  settings). Real-robot numbers (encoder counts per second, turning radius) will differ.

## Which motors are the wheels

`worldModel.xml` → `<wheels left=".." right="..">`. TRIK's examples use left=M3/right=M4, the course
template uses left=M4/right=M3. If the simulated robot turns the wrong way or spins, check this
(`qrs_tool.py inspect`) and fix with `qrs_tool.py wheels prog.qrs <LEFT> <RIGHT>`.

## Code generation

`sim.py gen prog.qrs --lang python|javascript -o out` = `2D-model --only-generate --generate-mode ...`.
Useful to (1) check that a hand-built diagram means what you think, (2) explain a diagram to someone
as code, (3) upload a diagram to the robot (TRIK Studio itself uploads the generated JS).
