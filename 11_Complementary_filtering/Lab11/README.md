# Lab 11 — Complementary filter for the robot course (digits 9 1)

| File | What |
|---|---|
| `complementary_filter.qrs` | block program for the real robot; `K`, `TEST`, `T_CAL` at the top of `init` |
| `complementary_filter_sim.qrs` | same program for the 2D model |
| `cf_cal.txt` | calibration check: `TEST = 1`, motors off, K forced to 1, 60 s |
| `cf_098.txt`, `cf_050.txt`, `cf_002.txt` | real runs with K = 0.98 / 0.5 / 0.02, each with a hand disturbance |
| `cf_sim_*.txt` | 2D-model logs (ideal gyro, nobody can grab the robot) — to test the notebook |
| `extra_runs/cf_098_nodisturb.txt` | K = 0.98, nobody grabbed the robot |
| `extra_runs/cf_098_try2_300deg.txt` | K = 0.98, second try: ≈ 300° gap, mostly wheels spinning while held |
| `Lab11_complementary_filter.ipynb` | Colab analysis: calibration check, τ, course plots, disturbance response, trajectories, what-if K, summary |
| `lab11_visual_explanation.pdf` | visual explanation: filter, program, runs, behaviour, choice of K |

## The program

Lab 10's program; three changes:

```
course = K·(course + gyro_inc) + (1 − K)·course_odom          τ = K·dt/(1 − K)
```

1. **Course line** — the complementary filter above, instead of `MODE`.
2. **My calibration** (no `calibrate()`), `T_CAL = 10` s at rest: first 3 s → mean `m1` and std `sd1`; the rest → `b0` = mean of
   the samples within `m1 ± (4·sd1 + 0.02)`. The header logs `b0, sd, ncal, nrej`.
3. **`TEST = 1`** — motors stay off, K is forced to 1 and the loop logs for 60 s: the calibration check.

Log `cf_log.txt`: `t, ts, i, encL, encR, gz, bias, course, course_odom, course_g, x, y, pL, pR`, header
`# K TEST b0 sd ncal nrej T_CAL r B s GS TICK`. Raw `gz` and encoders are logged, so any K can be replayed offline.
Same constants as Lab 10: r = 4.2 cm, B = 19.4 cm, s = 0.0016, GS = +1, PM = −1, TICK = 0.256 ms, same waypoints and gains.

## Running it

1. Calibration check: `TEST = 1`, robot anywhere on the floor, nobody touches the table for 70 s.
2. For K = 0.98, 0.5, 0.02 (`TEST = 0`): robot on the tape cross, hands off for 10 s, then it drives the “91”.
   About 30 cm along the first straight (the stem of the 9): hold it firmly on the floor ≈ 3 s, turn it ≈ 45° to its left, let go.
3. `python trik_robot.py --ip <robot ip> pull cf_log.txt .` → rename to `cf_098.txt` etc.
4. Colab: upload the four logs, Run all. The notebook finds the disturbance in each log by itself.

## Results

Real runs 2026-11-26, robot 192.168.50.198. Loop period **78 ms** (median), so the time constants are very different from what
the K values suggest. Each run was compiled to JS with its own log name (`cf_098_91.txt`, …).

**Calibration check:** b0 = 0.0696 °/s, σ = 0.056 °/s, 357 samples kept, 0 rejected; course after 60 s −0.195° →
**−0.163 °/min, PASS** (< 1 °/min).

| Run | K | τ (dt = 78 ms) | hold (detected) | Δ gyro / Δ encoders in the hold | memory decay | max dist. (gyro path) | final error (gyro path) | behaviour after the disturbance |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.98 | 3.82 s | 2.5–4.7 s | +32° / −237° | 4.0 s | 36.6 cm | 38.2 cm | wheels slipped while held; the estimate kept the gyro's view, then slid to the false encoder course in ≈ 4 s; twisted “91” |
| 2 | 0.5 | 78 ms | 3.4–4.6 s | +36° / −10° | 0.32 s | 7.3 cm | 8.4 cm | estimate = encoders; they caught up ≈ 0.5 s after release, ≈ 10° left; rest of the “91” close |
| 3 | 0.02 | 1.6 ms | 3.3–5.0 s | +51° / +14° | 0.31 s | 20.4 cm | 10.0 cm | estimate = encoders; ≈ 37° of the turn never seen; the “1” drawn rotated |

“Gyro path” = the logged encoder path re-drawn with the calibrated gyro course (the best guess of the real motion; no tape
measurement for these runs). The robots' own estimates all end within 2.6–3.4 cm of the target.

**What-if on the run-1 log:** τ ≥ 5 s needs K ≥ 0.9846 at 78 ms. K = 0.99 still holds 128° of the gyro's view 5 s after the peak,
K = 0.995 holds 186°.

**Short analysis.**
- Only K = 0.98 is a real filter at 78 ms; K = 0.5 and 0.02 forget the gyro within one loop, so runs 2 and 3 are both odometry.
  They differ because of the different hand turns, not the gain.
- Holding a driving robot makes the wheels slip: the encoders counted −237° that never happened. A complementary filter assumes
  odometry is slow but honest. A long τ keeps the gyro's correct answer for a while, but the estimate still ends at the wrong
  odometry.
- Choice: K ≈ 0.995 (τ ≈ 15 s, longer than the whole 25-s run; the gyro drift costs < 0.05°). Better: a Kalman filter, or a gate
  that ignores `course_odom` while |gyro rate − encoder rate| is large.
- Geometry: r = 4.2, B = 19.4 (r/B 0.2165) matches the gyro (Lab 10: 0.213–0.217). The ruler values 3.75/19.6 (r/B 0.191) would
  make `course_odom` 11 % short.
