# Lab 7 — Go-to-goal, digits 9 1

| File | What |
|---|---|
| `go_to_goal_sim.qrs` | block program for the 2D simulator (`r = 0.028`, `B = 0.154`, logs `odometry_data_sim.txt`) |
| `go_to_goal_real.qrs` | the same program and gains for the robot (`r = 0.0375`, `B = 0.194`). On the robot it logs `go_to_goal_real_91.txt` so it can't delete a classmate's file; rename to `odometry_data_real.txt` after pulling |
| `odometry_data_sim.txt` | simulator log, `x,y,time` (cm, cm, ms), one line per 20 ms, no header |
| `odometry_data_real.txt` | real-robot log (2026-10-29, robot trik-6fc169, battery 12.3 V), pulled as `go_to_goal_real_91.txt` and renamed |
| `Lab7_go_to_goal.ipynb` | Colab analysis: planned vs model vs real, waypoint-miss table, run times, off-path distance, tape end point |
| `lab7_visual_explanation.pdf` | 12-page visual explanation: controller, angle wrapping, tuning, real run, tape analysis |
| `sim_trajectory.png` | simulator check: odometry belief vs 2D-model ground truth (end difference 0.15 cm) |

## Waypoints (m, start frame: x = start direction, y = to the left)

```
digit 9: (0,0) → (0,0.60) → (−0.30,0.60) → (−0.30,0.30) → (0,0.30)
gap:     (0,0.30) → (0.30,0)
digit 1: (0.30,0) → (0.30,0.60) → (0.215,0.515)      flag
```

## How the program works

`init` holds `r`, `B`, the waypoint arrays `wx`, `wy`, and the gains. One `PreconditionalLoop`
(`hold < 15 and t < 90000`) runs every 20 ms:

1. **Odometry** (Lab 6): `path = (θ_r + θ_l)·r/2`, `course = (θ_r − θ_l)·r/B`,
   `x += Δpath·cos(course)`, `y += Δpath·sin(course)`; left = E4, right = E3.
2. **Go-to-goal** towards waypoint `k`:
   `ρ = √(dx² + dy²)`, `θ_g = atan2(dy, dx)`,
   `e = atan2(sin(θ_g − course), cos(θ_g − course))` (wrapped into (−π, π]),
   `v = clamp(K_v·ρ, 25, 50)·max(0, cos e)³`, `ω = clamp(K_θ·e, −40, 40)`,
   `pL = v − ω` → M4, `pR = v + ω` → M3 (motor %).
3. **Switch** when `ρ < ε`: `i = i + max(0, sgn(ε − ρ))`. Function blocks have no `if`, so
   `active = max(0, sgn(N − i))` zeroes the motors after the last waypoint; 15 more passes then end the loop.
4. Each pass appends `x·100, y·100, t` to a string; **Write To File** writes it once after the loop.
   This did *not* speed up the real robot: its loop still ran every 57 ms (Lab 6, writing every pass: 59 ms),
   so the slow loop is the robot's runtime, not file I/O. The simulator runs every 20 ms.

| Gain | Value | Why |
|---|---|---|
| `K_v` | 200 %/m | full 50 % until 25 cm from the waypoint, then slows down |
| `VMIN` | 25 % | the real floor dead zone is 12–15 %; lower and the robot stalls near a waypoint |
| `K_θ` | 100 %/rad | sharp corners; 60 gave 5 cm bows; 150 is about the same on the real-robot model but closer to oscillating |
| `cos(e)³` | — | forward speed drops to 0 when the goal is to the side: turns are nearly in place |
| `ε` | 0.03 m | 0.05 switched early and missed the corners by up to 4.7 cm |

Sim tuning (headless TRIK simulator, ground truth from the 2D model):

| K_θ | cos power | ε | time | worst corner miss | worst off-path |
|---|---|---|---|---|---|
| 60 | 1 | 0.05 | 27.8 s | 4.7 cm | 5.3 cm |
| 100 | 3 | 0.05 | 28.5 s | 4.8 cm | 2.6 cm |
| **100** | **3** | **0.03** | **30.9 s** | **2.7 cm** | **2.6 cm** |
| 150 | 4 | 0.03 | 31.1 s | 2.7 cm | 1.9 cm |

The chosen gains were also run on a motor model of the real robot (Lab 5 numbers: T_m 0.16 s,
16.5 rad/s, 12 % dead zone, ±5 % wheel mismatch) at 25 ms and 60 ms loop periods: all 8 waypoints
reached, ~21 s, worst miss 0.9 cm, worst off-path 3.6 cm, no oscillation.

## In class — real run

1. **Geometry:** same robot as Lab 6, so `init` already has the same `r = 0.0375`, `B = 0.194`. Nothing to change.
2. **Space:** start at the bottom of the 9's stem, facing x. The path spans x −0.3…+0.3 m, y 0…0.6 m;
   leave ~0.5 m free around it. Tape the start point (axle midpoint) and direction.
3. **Run:** TRIK Studio → *Upload and run*, or
   `python trik_robot.py --ip <robot ip> start go_to_goal_real.qrs --diagram`. The robot moves — keep a hand near it.
   If it spins clockwise on the spot instead of turning left, left/right are swapped: swap
   `encoder4` ↔ `encoder3` and the M4 ↔ M3 motor ports.
4. **Tape** the end point → `x_meas, y_meas` (cm) in the notebook.
5. **Log:** `python trik_robot.py pull go_to_goal_real_91.txt .`, rename to `odometry_data_real.txt`.
6. **Colab:** upload both txt files, Run all, write the 3–6 sentences.

## Results

| | x, cm | y, cm |
|---|---|---|
| last waypoint | 21.5 | 51.5 |
| simulator odometry (last log line) | 23.4 | 53.4 |
| simulator ground truth | 23.5 | 53.5 |
| real odometry (last log line) | 21.9 | 50.7 |
| real, tape | 6.0 | 26.0 |

| | worst corner miss | worst off-path | run time | final heading |
|---|---|---|---|---|
| simulator | 2.7 cm | 2.6 cm | 30.9 s | −135° |
| real (odometry) | 0.8 cm | 5.4 cm | 17.4 s | −128° |
| real (tape) | — | — | — | ≈ −80° |

The controller did its job on both: every waypoint within 2.7 cm of the robot's own estimate. On the
real robot it overshot every corner by 2–4.5 cm (simulator ≤ 0.4 cm) and weaved up to 5.4 cm (57 ms loop + motor lag with `K_θ = 100`).
The tape is 29 cm and about 48° away from the odometry: a localization error (≈ 8 % over-turn → `B` probably
≈ 0.18 m, not 0.194, plus slip in the fast turns). Discussion at the end of the notebook.
