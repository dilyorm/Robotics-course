# Lab 6 — Localization (odometry), digits 9 1

| File | What |
|---|---|
| `trajectory_sim.qrs` | block program for the 2D simulator (`r = 0.028`, `B = 0.154`, logs `odometry_data_sim.txt`) |
| `trajectory_real.qrs` | the same program for the robot (`r = 0.0375`, `B = 0.194`). On the robot it logs `odometry_data_real_91.txt` so it can't delete a classmate's `odometry_data_real.txt`; renamed after pulling |
| `odometry_data_sim.txt` | simulator log, `x,y,time` (m, m, ms), one line per 20 ms, no header |
| `odometry_data_real.txt` | real-robot log, run 2 (2026-10-22, robot trik-6fc169): the run that was measured with the tape |
| `odometry_data_real_run1.txt` | real-robot log, run 1 (no tape measurement), kept to show run-to-run spread |
| `Lab6_odometry.ipynb` | Colab analysis: both trajectories, error vs time and vs distance, tape end point |
| `sim_trajectory.png` | simulator check: odometry belief vs 2D-model ground truth (end error ≈ 1 mm) |

## How the program works

One `PreconditionalLoop` (`seg < N`), every 20 ms:

1. **Odometry** (professor's form, left wheel = E4, right = E3, angles in rad):
   `path = (θ_r + θ_l)·r/2`, `course = (θ_r − θ_l)·r/B`, `x += Δpath·cos(course)`, `y += Δpath·sin(course)`.
2. **Segment controller** — the trajectory is a list of 16 segments (`kind`: 0 straight, 1 turn, 2 pause):
   9 = turn left, up 2a, left a, down a, right a; pause 1.5 s; 1 = diagonal to its foot, up 2a, flag.
   `a = 0.30 m`. Straights hold the heading (`w = KH·e`) and slow down near the end; turns go to an
   absolute heading with a minimum power of 25 % so the robot does not stall in the floor dead zone.
   No `if` in Function blocks, so the segment type is selected with 0/1 factors (`isS`, `isT`, `isP`)
   and `done = max(0, sgn(...))`. Each segment also gives up after 8 s, so the program always ends.
3. **Motors** M4 = `pL = v − w`, M3 = `pR = v + w`, then **Write To File** appends `x,y,time`.

The robot steers by its own odometry. Its log therefore always looks close to the plan. The real
error only shows up when you compare it with a tape measurement.

The real program was checked on a motor model built from the Lab 5 numbers (T_m ≈ 0.16 s,
16.5 rad/s at 100 %, 12–15 % dead zone, extra delay). It finishes in about 25 s with no timeouts.
On the real robot the loop ran every 59 ms (20 ms in the simulator), and every leg overshot by 5–14 cm (see the notebook).

## In class — real run

1. **Measure your robot** and put the numbers into the `init` Function block of `trajectory_real.qrs`:
   `r` = wheel diameter / 2, `B` = distance between the wheels' contact lines (m).
   The professor's two files disagree (`r = 0.0375` in the .py, `0.042` in `Localization_demo.qrs`), so
   measure.
2. **Space:** the robot starts at the bottom of the 9's stem and first turns left. Start frame:
   x = start direction, y = to the left. The path covers x from −0.3 to +0.3 m and y from 0 to 0.6 m.
   Leave about 0.5 m of free floor on every side of that area. Mark the start point on the floor with tape
   (the point between the wheels) and the start direction.
3. **Upload and run** the diagram: TRIK Studio → connect to the robot → *Upload and run*.
   With the skill: `python trik_robot.py --ip 192.168.77.1 start trajectory_real.qrs --diagram`.
   The robot will move — keep a hand near it.
   *If the first turn goes clockwise and the robot keeps spinning,* left/right are swapped on your
   robot: stop it, swap `encoder4` ↔ `encoder3` in the `step` block, and swap the ports of the two
   Motors blocks (M4 ↔ M3).
4. **Tape:** measure the real end point (axle midpoint) in the start frame and write it into the
   notebook (`x_meas, y_meas`).
5. **Get the log:** `python trik_robot.py pull odometry_data_real_91.txt .`, then rename to `odometry_data_real.txt` (or TRIK Studio's file
   manager). Do not edit it.
6. **Colab:** open `Lab6_odometry.ipynb`, upload both txt files, Run all, write the 3–6 sentences.

The README's error (`np.interp` on time) compares positions at equal **time**. The simulated robot is
slower (sim 37 s, real 23–28 s), so that curve mostly shows the speed difference. The notebook also
plots the error at equal **distance travelled**, which shows how different the two paths are in shape.

## Results (run 2)

| | x, m | y, m |
|---|---|---|
| planned end | 0.215 | 0.515 |
| simulator odometry | 0.212 | 0.515 |
| real odometry (last log line) | 0.242 | 0.423 |
| real, measured with tape | 0.190 | 0.535 |

Odometry vs tape: **0.124 m** after 3.2 m of driving (about 4 %). Path length: simulator 2.69 m, real 3.22 m.
Run 1 ended at (0.237, 0.522) m in the robot's own odometry, 10 cm from run 2, with the same program.
The 3–6 sentence discussion is at the end of `Lab6_odometry.ipynb`.
