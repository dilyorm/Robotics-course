# Lab 10 — Odometry and gyroscope localization (digits 9 1)

| File | What |
|---|---|
| `lab10_real.qrs` | block program for the real robot; `MODE = 0` run A (encoder course), `MODE = 1` run B (gyro course) |
| `lab10_sim.qrs` | same program for the 2D model (r = 2.8, B = 15.4, GS = −1, PM = +1) |
| `lab10_A.csv`, `lab10_B.csv` | real-robot logs of run A and run B |
| `lab10_sim_A.csv`, `lab10_sim_B.csv` (+ `_truth.csv`) | 2D-model logs and the simulator's true pose |
| `extra_runs/lab10_A_try1_kh80.csv` | first try of run A (KH = 80, heading weave and an end spin) — replaced, kept for reference |
| `Lab10_localization.ipynb` | Colab analysis: trajectories, 4 recomputed paths, geometry check, comparison table, error growth, short analysis |
| `lab10_visual_explanation.pdf` | visual explanation: model, program, runs, results |

## The program

```
start → init (waypoints, gains, MODE) → remove file → "calibrating" → 10 s still: gsum += gz → b0 = mean → header → clear E3, E4
while hold < 15:
    step:  gyro_inc = GS·(gz/1000 − b0)/(1 + s)·dt·π/180      dt from the gyro clock (TICK = 0.256 ms)
           path = (θr + θl)·r/2,  course_odom = (θr − θl)·r/B
           course = (1 − MODE)·course_odom + MODE·course_g
           x += Δpath·cos(course),  y += Δpath·sin(course)
    ctrl:  waypoint i, courseAngle wrapped to [−π, π]; turn in place until |courseAngle| < ALIGN, then drive with heading hold
           (latched); steering fades out within 15 cm of the waypoint; motors off the moment i reaches N; one CSV line into buf
    M3 = PM·pR, M4 = PM·pL;  if n ≥ 200: write buf;  Timer 10 ms
motors off → write the rest → sync
```

No `if` in Function blocks: every branch is `max(0, sgn(…))`. Log: `t, ts, i, encL, encR, gz, x, y, course, course_odom, course_g, pL, pR`
with the header `# MODE b0 r B s GS TICK`. Raw `gz` and encoders are logged, so both methods can be replayed on both runs.

Waypoints (cm): `X_ref = {0, 0, −30, −30, 0, 30, 30, 21.5}`, `Y_ref = {0, 60, 60, 30, 30, 0, 60, 51.5}` — 7 segments, 264.4 cm, 585° of turning.
Robot constants: r = 4.2 cm, B = 19.4 cm, s = 0.0016 (Lab 9), GS = +1 (CCW positive), PM = −1 (positive power makes this robot's
encoders count down). Gains: ALIGN 0.07 rad, KT 40, KH 35, TMIN/TMAX 20/30 %, VMIN/VMAX 25/40 %, KV 2, EPS 1 cm.

## Running it

1. Tape cross on the floor; robot's axle midpoint on the cross, facing +y (the first segment).
2. TRIK Studio: open `lab10_real.qrs`, set `MODE` in `init`, upload and run — or compile to JS and
   `python trik_robot.py --ip <robot ip> start lab10_A.js`.
3. Hands off for 10 s (gyro calibration), then it drives the “91” (~24 s).
4. `python trik_robot.py --ip <robot ip> pull lab10_log.csv .` → rename to `lab10_A.csv` / `lab10_B.csv`.
5. Colab: upload both logs, Run all.

## Results

Real runs 2026-11-26, robot 192.168.50.198, battery 12.5 V. Loop period **78 ms** (median), not 10 ms. Each run was compiled to JS
with its own log name (`lab10_A_91.csv`, `lab10_B_91.csv`) so the second run could not overwrite the first.

| Seg. | course_ref (°) | course A (°) | course B (°) | d_course A / B (°) | path_ref (cm) | path A (cm) | path B (cm) | d_path A / B (cm) |
|---|---|---|---|---|---|---|---|---|
| 1 | 90 | 95.3 | 93.1 | 5.3 / 3.1 | 60.0 | 59.5 | 59.0 | −0.5 / −1.0 |
| 2 | 180 | 190.4 | 188.7 | 10.4 / 8.7 | 30.0 | 32.5 | 33.8 | 2.5 / 3.8 |
| 3 | 270 | 278.9 | 280.0 | 8.9 / 10.0 | 30.0 | 32.7 | 34.1 | 2.7 / 4.1 |
| 4 | 360 | 371.1 | 369.0 | 11.1 / 9.0 | 30.0 | 35.4 | 35.2 | 5.4 / 5.2 |
| 5 | 315 | 312.2 | 310.7 | −2.8 / −4.3 | 42.4 | 43.8 | 43.7 | 1.4 / 1.2 |
| 6 | 450 | 453.6 | 455.3 | 3.6 / 5.3 | 60.0 | 64.4 | 66.0 | 4.4 / 6.0 |
| 7 | 585 | 609.6 | 606.2 | 24.6 / 21.2 | 12.0 | 17.9 | 16.1 | 5.9 / 4.1 |
| **Summary** | | | | **9.5 / 8.8** (mean abs) | **264.4** | **286.2** | **287.8** | **+21.8 / +23.4 = +8.2 / +8.8 %** |

| Run | final position error | final course error | x, y, course from |
|---|---|---|---|
| A | 3.4 cm | 13.0° | logged estimate (encoder course) |
| A | 5.7 cm | 1.8° | recomputed with the gyro course |
| B | 3.3 cm | 5.2° | logged estimate (gyro course) |
| B | 7.5 cm | 9.1° | recomputed with the encoder course |
| A / B | 8.9 / 8.2 cm | 1.8 / 5.2° | best guess: gyro course, r = 3.75 cm |

- **Calibration:** b0 = 0.109 / 0.087 °/s (10-s mean). The Lab 11 check gives −0.16 °/min left after calibration.
- **Course:** both estimates look alike (each steered by itself). The gyro shows the encoder course losing 2–6° in most left turns
  (slip/scrub; turn 6 is the exception), −11.2° by the end of run A. Run B is closer in course.
- **Path:** the same in both runs (+8 %): same encoders, same r.
- **Geometry (measured after the runs: wheel diameter 7.5 cm, 19.6 cm between the wheels).** The gyro fit gives the real
  r/B = 0.213–0.217. The program's 4.2/19.4 = 0.2165 is within +0.8 %; the ruler values 3.75/19.6 = 0.191 are −10.9 % and would
  make run A's encoder course end 58° short. The effective track for r = 3.75 is ≈ 17.5 cm. r = 4.2 is a correction of r/B, not
  of r: with the real r = 3.75 the path is 12 % shorter (257.9 / 260.2 cm, −2.5 / −1.6 %).
- **Tape check:** end points (20, 11) and (20, 12) cm. x matches the reconstruction, y is ≈ 32 cm lower in both runs by the same
  amount — probably a different reference for y, so not used for conclusions.
- **First try of run A** (KH = 80): ±100 °/s heading weave and a 32° spin after the last waypoint. Fixed (KH 35, steering
  fade-out, motors off at the last waypoint) and repeated; the old log is in `extra_runs/`.
