---
name: trik-studio
description: Work with TRIK Studio and TRIK robots without the GUI - read, explain, create and edit .qrs projects (block diagrams and embedded Python/JavaScript), run them headlessly in the 2D simulator, compile diagrams to code, and upload/run/stop programs and pull data files on a real TRIK robot over Wi-Fi. Use this skill whenever the user mentions TRIK, TRIK Studio, trikStudio, a .qrs file, the 2D model/simulator, TRIK block diagrams (Function, PreconditionalLoop, Motors Forward, encoders E3/E4, motors M3/M4), uploading to the robot, or a NewUU CS413 / robotics lab (line following, motor identification, odometry, go-to-goal) - even if they don't say "TRIK" explicitly but talk about their robot lab, robot program, or a .qrs project.
---

# TRIK Studio

TRIK Studio projects (`.qrs`) are zip files of XML. Everything a student does in the GUI —
read a diagram, add blocks, paste Python, press "Run in 2D model", "Upload and run" — can be done
from the command line with the bundled scripts. Prefer the scripts over hand-editing XML: TRIK Studio
segfaults on a malformed project.

Scripts (Python 3.8+, standard library only; run from anywhere):

| Script | Does |
|---|---|
| `scripts/qrs_tool.py` | `inspect`, `get-code`, `set-code`, `dump` (diagram → JSON), `build` (JSON → diagram), `new`, `wheels` |
| `scripts/sim.py` | `run` a project in the headless 2D simulator and summarize the robot's motion, errors, display text and written files; `gen` diagram → Python/JS; `where` |
| `scripts/trik_robot.py` | real robot: `status`, `start`/`upload`/`run`/`stop`, `exec`, `ls`/`pull`/`push`/`shell` |

`SKILL_DIR` below means the folder containing this file. Each script has `--help`.

## Setup check (once per session, when needed)

- Simulator/generator need TRIK Studio installed: `python SKILL_DIR/scripts/sim.py where`.
  If not found, ask the user for the install folder and set `TRIK_STUDIO_DIR` to it.
- Robot commands need the laptop on the robot's Wi-Fi; IP from the robot screen via `--ip` or
  `TRIK_IP` (default 192.168.77.1).

## One project, two programs

A `.qrs` can contain a block diagram AND embedded code at the same time (lab files often carry
leftover code). `inspect` prints a NOTE when both exist. `sim.py run` and `trik_robot.py start` then
use the **code** by default — when the user means the blocks, pass `--mode diagram` (sim) /
`--diagram` (robot). `build --template` keeps the template's code unless `--drop-code`; ask the user
if it is unclear whether that code still matters.

## Workflows

### Understand / explain an existing project
1. `qrs_tool.py inspect prog.qrs` — kit, 2D wheel mapping, embedded code, and every block in
   execution order with properties and link guards.
2. Embedded code: `qrs_tool.py get-code prog.qrs`. Diagram as code: `sim.py gen prog.qrs --lang python`
   (TRIK's own generator — the most faithful reading of what a diagram does).
3. When explaining to a student, walk the flow from InitialNode, say what each block does physically
   (motor power, waits, encoder thresholds), what each variable means, and point out loops/branches.
   Block meanings and property names: `references/blocks.md`; expression syntax:
   `references/expressions.md`.

### Write a program as code (Python or JS)
1. Write `prog.py` against the robot API (`references/robot-api.md`). Use `script.wait()` not
   `time.sleep()`; end with `brick.stop()`.
2. Test in the simulator: `sim.py run world.qrs --code prog.py` (world.qrs = the lab's .qrs, or
   `qrs_tool.py new world.qrs`). The sim disables file writes and print in script mode — put debug
   output on the display (`brick.display().addLabel(...)`); sim.py prints each new display text with
   the robot pose at that moment, so a label per step gives a per-step check.
   **The simulated robot is smaller than the course robot** (wheel r 2.8 vs 3.75 cm, track 15.4 vs
   19.4 cm): distance/angle programs must use sim geometry to look right in sim
   (`references/simulator.md`). Tell the user which numbers to use on the real robot.
3. Deliver it inside a project when the lab wants a `.qrs`: `qrs_tool.py new prog.qrs --code prog.py`,
   or into an existing lab file `qrs_tool.py set-code lab.qrs prog.py -o lab_solution.qrs`
   (keeps the diagram unless `--strip-diagram`).

### Create or edit a block diagram
Labs sometimes require blocks only. Work in the JSON spec, never in raw XML:
1. Existing project: `qrs_tool.py dump lab.qrs -o spec.json`. New: write the spec from scratch
   (format in `qrs_tool.py --help`; blocks from `references/blocks.md`).
2. Edit `spec.json`. Rules the builder validates: one InitialNode; loops have exactly an `iteration`
   link (body, which must lead back to the loop block) and a `""` link (exit); IfBlock has `true` and
   `false`/`""` links; other blocks have one outgoing link; FinalNode none. Property values are strings
   and may be expressions (`"Power": "50 + u"`).
3. `qrs_tool.py build spec.json -o lab_v2.qrs --template lab.qrs` — reuses the lab's robot config and
   2D world, replaces the diagram. Without `--template` the bundled course template is used.
4. Verify: `sim.py gen lab_v2.qrs --lang python` (prints the code) reads back as the logic you
   intended, and `sim.py run lab_v2.qrs --mode diagram` behaves sensibly. Then the user opens it in
   TRIK Studio.

Subprograms are not supported by `build` (it refuses); edit those in the GUI.

### Simulate
`sim.py run prog.qrs [--timeout 60] [--csv traj.csv] [--workdir out]`. Reports exit status, runtime
errors (with line numbers), start/end pose (wheel-axle midpoint, cm), distance and turn, display text
with poses, and files the program wrote. Runs vary by ±1–2° (motor noise). Programs that never end are killed at `--timeout` and still summarized. If the robot turns the
wrong way, the 2D wheel mapping may not match the code: `qrs_tool.py inspect` shows it,
`qrs_tool.py wheels prog.qrs M3 M4` changes it. Details and traps: `references/simulator.md`.

### Run on the real robot
Before starting anything that drives motors, tell the user the robot will move and that it should be
on a stand or have space — then:
- `trik_robot.py --ip IP start prog.py --follow 20` (also `.js`, or `.qrs`: its embedded code, or the
  diagram compiled to JS exactly like TRIK Studio's "Upload and run").
- `trik_robot.py stop` to halt. `exec "<js>"` for one-off commands, e.g. testing one motor.
- Data: `trik_robot.py pull 'wheel_*.txt' ./data` (paths relative to `/home/root/trik/scripts`).
Network and troubleshooting: `references/robot-connection.md`.

## Gotchas worth remembering

- `script.writeToFile` **appends** — `removeFile` first. Write after the run, not inside fast loops.
  Run `sync` (`script.system("sync", True)`) so files survive power-off.
- Function blocks: no `if`/`while`; `..` joins strings; arrays index from 0; port-like names
  (`S3`, `M3`, `E4`, `A1`) are reserved and read-only.
- `TrikWriteToFile` takes a fixed file name; for computed names or battery reads use a `TrikSystem`
  block with `Code=true` (raw JS on the robot).
- Long robot runs (> ~20 s): `start` without `--follow`, wait, then check the log length — a Wi-Fi
  drop during `--follow` can cut the run. Battery read recipe: `references/robot-connection.md`.
- Encoders read degrees; motor power is -100..100. Real motors have a dead zone (~10–15 % on the floor)
  that the simulator does not model.
- Overwriting commands (`set-code` without `-o`, `wheels`) save `<file>.bak` first; still prefer `-o`
  to a new file so the student keeps their original.
- `.qrs` internals (ids, guards, ports, what crashes TRIK Studio): `references/qrs-format.md`.
- NewUU CS413 course facts (ports, wheel geometry, odometry form, lab tips):
  `references/course-notes.md`.
