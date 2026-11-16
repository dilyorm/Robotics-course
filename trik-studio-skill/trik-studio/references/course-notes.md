# NewUU CS413 Robotics — course-specific notes

Facts collected while doing the labs (course repo: github.com/NewUU-engineering/Robotics-course,
one folder per week with README + `.qrs` files). Every robot differs a bit — treat these as
starting points and verify on your own robot.

## Robot

- TRIK controller V6.2 (kit `trikV62Kit`), drive motors on **M3/M4**, encoders on **E3/E4**.
- Which side is left differs between files: the course's 2D world uses left = M4, right = M3, TRIK's
  examples use left = M3. Test on the real robot: run one motor at a time (lifted) and look.
- Geometry used in the professor's code: wheel radius `r = 0.0375 m`, track (wheel-to-wheel)
  `W = 0.194 m`. Encoder reads degrees: wheel arc `d = 2·pi·r·Δenc/360`.
  The 2D simulator's robot is smaller (r = 2.8 cm, track 15.4 cm) — see `simulator.md`.
- Reflectance (line) sensors on A3/A4. Real robot: black ≈ 30, white ≈ 0. **2D sim light sensor =
  99 − brightness** (black high). Calibrate (min/max) at start rather than hard-coding thresholds.
- Battery ~12 V; motors weaken as it drops — log `brick.battery().readVoltage()` with experiments
  (the simulator returns no battery value).

## Odometry (lab 6 style, the professor's form)

```
dL = 2*pi*r*(encL - encL_old)/360        dR = same for the right wheel
dS = (dL + dR) / 2                       # distance of the centre
dθ = (dR - dL) / W                       # heading change, rad (sign: check your wheel sides!)
x += dS*cos(θ);  y += dS*sin(θ);  θ += dθ
```
Equivalent with wheel angles in rad: path = (θ_l + θ_r)/2 · r, φ = (θ_r − θ_l)·r / W. Sign of φ
depends on which wheel is left; the professor's code writes (L − R)/W.

## Motor identification (lab 5 / Assignment 1) ballpark

First-order model `T_m·dω/dt + ω = U/k_e`. Measured on one class robot, wheels lifted, ~11.9 V:
- ω at 100 % ≈ 15.7 (left M4) / 16.1 (right M3) rad/s; the wheel already turns at ±10 % (4–5.6 rad/s).
  On the floor it needs ≥ 10–15 % PWM.
- ω(PWM) is **not** proportional: a line through 20–100 % hits PWM = 0 at ≈ ±3.4 (M4) / ±5.7 (M3)
  rad/s (an offset, not a dead zone). Slope ≈ 0.10–0.12 rad/s per %, k_e ≈ 1.0–1.2 V·s/rad.
  The plain `U/k_e` model then fits a chirp/square only ~45–65 %; slope + offset + 10 % dead zone ~70–80 %.
- T_m depends on PWM: ≈ 40 ms at ±100 % up to 300–440 ms at ±10 % (mean ≈ 0.16–0.21 s).
- `curve_fit` of the step model diverges at ±100 % (T_m → 0) without `bounds=([-30, .005], [30, 2])`
  and `p0=[0.15*PWM, 0.1]` (sign of the guess matters).
- ~25 ms from motor command to the first encoder degree; coasting after power 0 lasts 1.3–1.7× the
  model's ω·T_m (a fast wheel may still turn when the next 1 s-later step starts).
- Left and right differ by 10–25 % in k_e and T_m → curved "straight" driving. Two step runs agree
  within ~0.1 rad/s. Encoder counts whole degrees → 0.46 rad/s noise in `np.gradient` at 20 ms.
- Split a step log by the PWM column (`np.diff(u) != 0`); dead zone from a slow ramp from rest
  (chirp start), not from later zero crossings (the wheel is still spinning the other way).

## Block-language gotchas seen in labs

- Names like `S3`, `S4`, `M3`, `E4`, `A1` are reserved (read-only) — pick other variable names.
- No `if` in Function blocks: use IfBlock or branch-free math (`sgn`, `min`, `max`, `abs`).
- String concat is `..`.
- `encoder3`/`encoder4` read E3/E4 directly in expressions.
- Real loop period grows with the number of blocks per pass (the robot's diagram runtime, not file I/O):
  read encoder → Write To File → `Timer 5` ran at **~20 ms**; an odometry + controller loop with
  `Timer 20` + Write To File ran at **~57–60 ms** (20 ms in the simulator). Buffering the log in a
  string and writing once at the end did NOT speed it up. Measure Δt from your log; tune for it.
- TRIK JS threads (Fork, or `Threading`) do **not** share globals: each thread has its own copy. Code
  in the main thread after `killThread` sees stale initial values — don't compute results there.

## Go-to-goal that worked on the real robot (Lab 7 and two Lab 6 rewrites)

```
e   = atan2(sin(bearing - th), cos(bearing - th))        # wrap to [-pi, pi]
v   = clamp(200*dist, 25, 50) * max(0, cos e)^3           # slow down when facing away
w   = clamp(100*e, -40, 40)
left (M4) = v - w,  right (M3) = v + w                    # next waypoint when dist < 3 cm
```
With the ~60 ms loop expect 2–4 cm overshoot per corner and ±3–5 cm weave in the log. Odometry looks
near-perfect (it steers by itself); a tape check showed ~30 cm / ~48° real error after 2.5 m,
consistent with real track `W` ≈ 0.18 m rather than 0.194 (one measurement — verify on yours).
Open-loop timed moves (power, ms) drift with battery and floor; replace them with this loop.
- Some labs restrict you to blocks only (e.g. line race); a single Function block holding a whole
  state machine is allowed and works well.

## Deliverables pattern

Labs usually want: the `.qrs` used, raw data files exactly as the robot wrote them, and a short
report/notebook. Pull data with `trik_robot.py pull`, never hand-edit raw files.
