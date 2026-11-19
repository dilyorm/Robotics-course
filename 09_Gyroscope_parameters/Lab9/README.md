# Lab 9 — Gyroscope parameters

| File | What |
|---|---|
| `lab9_gyro.qrs` | block program: warm-up, static log, in-place rotation (Option A: sin + square), rest — **one loop**, phase chosen by time |
| `lab9_gyro.csv` | real-robot log (all phases) |
| `lab9_gyro_sim.csv` | 2D-model log of the same program (ideal gyro, clips at ±200 °/s; use `R_WHEEL, L_BASE = 0.028, 0.154`) |
| `Lab9_gyro.ipynb` | Colab analysis: §1–§6, `calibrate_gyro()`, `gyro_sim()`, parameter table, error budget |
| `lab9_visual_explanation.pdf` | visual explanation: model, program, each parameter, analysis |

## The program

```
start → init → remove file + header → Timer WARM (2 min) → clear E3, E4 → t0 = time()
while (time() − t0)/1000 < TEND:                       TEND = 180 + 36 + 36 + 3 = 255 s
    System call:  gzraw = readRawData()[2]
    step:         t → phase (1 static, 2 sin, 3 rect, 4 rest), u, one CSV line into buf
    M3 = +u, M4 = −u                                    in-place turn, 150 % clips to 100 %
    if n ≥ 200: write buf, buf = ""                      file I/O every 200 lines, not every pass
    Timer 10 ms
motors off → write the rest → sync
```

The phase is computed branch-free in one Function block (`a1 = max(0, sgn(t − T1))` …), so the
static phase is the same loop with `u = 0`. All durations are in `init`: for a 2D-model dry run set
`WARM = 2000`, `STATIC = 5`.

CSV: `t_ms,t_us,phase,u,gz_cal,gz_raw,encL,encR` — `t_ms` program clock, `t_us` = `read()[3]`,
`gz_cal` = `read()[2]` (mdeg/s), `gz_raw` = `readRawData()[2]`, `encL` = E4, `encR` = E3 (degrees).

## Running it

1. Robot on a rigid floor, ~40 cm free around it, tape mark in line with its nose.
2. `python trik_robot.py --ip <robot ip> start lab9_gyro.qrs --diagram` (or TRIK Studio → Upload and run).
3. Hands off for 5 min (warm-up + static). Then it spins for 75 s and stops.
4. Protractor: angle between the robot's nose and the tape mark → `SLIP_DEG` in the notebook.
5. `python trik_robot.py --ip <robot ip> pull lab9_gyro.csv .`
6. Colab: upload `lab9_gyro.csv`, Run all.

## Results

Real run 2026-11-19, robot 192.168.50.229, battery 12.39 V, loop period 65 ms (median). Option A (sin + square).

| Parameter | Symbol | Value | Unit | Method |
|---|---|---|---|---|
| Offset (bias) | $b_0$ | 2.1305 | deg/s | median of first 10 s of static, 4·MAD outlier cut |
| Bias drift | $d$ | +0.024 | deg/s per min | 30-s window means, line fit |
| Heading drift, uncorrected | | 129.5 | deg/min | slope of integrated raw rate (b₀·60 = 127.8) |
| Measurement range | ±$\omega_{max}$ | +286.7 / −286.4 | deg/s | flat top in gyro vs encoder rate; encoders reach 390 deg/s |
| Resolution | $\Delta$ | 0.00876 | deg/s | one raw count × raw factor |
| Noise std | $\sigma$ | 0.075 | deg/s | static 3 min, b₀ removed; Gaussian (kurtosis 0.1) |
| Raw → deg/s factor | | 0.00876 | deg/s per count | slope gz_cal vs gz_raw (= 8.75 mdps/LSB, ±250 dps setting) |
| Scale-factor error CCW / CW | $s$ | +11.9 / +12.5 | % | Δθ_gyro/Δθ_enc − 1 per clean turn, encoders with r = 3.75 cm |
| — same, encoders with r = 4.2 cm | $s$ | −0.1 / +0.4 | % | 4.2/3.75 = 1.12: the +12 % is the wheel radius |
| Positive rotation direction | | CCW | — | gyro and encoder heading agree |

- **Calibration:** `calibrate_gyro()` = median of the first 10 s, 4·MAD outlier cut. 10 s is where b₀(T) stays within
  0.01 deg/s of the 30-s value. Heading error left after 3 min at rest: 5.0°, almost all drift.
- **Dominant error:** uncalibrated offset at every time scale (21° / 128° / 383° after 10 s / 1 min / 3 min). Calibrated:
  drift (6.5° at 3 min) > calibration error (1.1°) > noise (0.26°).
- **Saturation:** at A = 150 % the robot spins at up to 390 deg/s, the gyro clips at 287 deg/s and loses 8–17 % of
  each turn: it ends at 111° while the encoders say 157° (r = 3.75) / 175° (r = 4.2). Robot vs tape mark by eye: ≈ 160° left,
  axle 6.3 cm left and 1.5 cm behind the start (not measured with a protractor).
- **On this robot u > 0 turns clockwise** (E3 counts down with M3 positive) — harmless here, the analysis compares gyro and encoders.
- `read()[3]` is not in µs (≈ 3.9 units per ms), so the notebook uses `t_ms`.
