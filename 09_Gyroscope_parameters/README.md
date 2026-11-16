# Lab 09 — Gyroscope Sensor Parameters

## Lecture

**Topic:** Sensors for state estimation — proprioceptive vs. exteroceptive, sensor performance characteristics, inertial sensors (MEMS gyroscope, accelerometer), IMU/INS and why an INS drifts without aiding.

**Key ideas**

- A MEMS vibratory gyro measures angular **rate** ω through the Coriolis force acting on a driven proof mass. It never measures angle directly — heading is obtained by integrating ω, so every error in ω becomes a growing error in θ.
- Sensor model used in this lab (yaw axis) — every parameter you identify plugs into it, so the result is a gyro you can **simulate**:

  ```math
  \omega_{meas}(t_k) = Q_{\Delta}\Big(\mathrm{sat}_{\pm\omega_{max}}\big[(1+s)\,\omega_{true}(t_k) + b_0 + d\,t_k + n_k\big]\Big), \quad n_k \sim \mathcal{N}(0,\sigma^2)
  ```

  | Symbol | Parameter | Section |
  |---|---|---|
  | $b_0$ | offset (bias) | §1 |
  | $d$ | bias drift rate | §2 |
  | $\omega_{max}$ | measurement range (saturation) | §3 |
  | $\Delta$ | resolution (quantisation step) | §4 |
  | $\sigma$ | noise standard deviation | §5 |
  | $s$ | scale-factor error | §6 |

- Integrating the model: a constant bias gives a heading error growing **linearly** in time ($\theta_{err} = b_0 t$); white noise gives an error growing as **√t**. This is the "unlimited drift" of an INS from the lecture.
- Error classes from the lecture: *systematic* (offset, scale factor — can be calibrated out) vs. *non-systematic* (noise — can only be characterised statistically and handled by a filter in Labs 11–12).

**Reading**

- Lecture slides: *16-311 Introduction to Robotics, Lecture 15 — Sensors (for State Estimation) 1*, G. A. Di Caro, CMU-Q (slides 3–19).
- Panasonic, *Basic Knowledge of Inertial Sensors — Gyro and Acceleration Sensors* — Coriolis principle and vibratory gyro mechanism: <https://industrial.panasonic.com/ww/ds/ss/technical/b14>
- O. Woodman, *An Introduction to Inertial Navigation*, Cambridge UCAM-CL-TR-696 — gyro error sources and how they propagate into heading: <https://www.cl.cam.ac.uk/techreports/UCAM-CL-TR-696.pdf>
- VectorNav Inertial Navigation Primer — *IMU Specifications* (how to read a datasheet): <https://www.vectornav.com/resources/inertial-navigation-primer/specifications--and--error-budgets/specs-imuspecs>

---

## Goal

Identify the parameters of the TRIK controller's built-in gyroscope (yaw axis), build a simulated gyro from them, and use it in Lab 10 (gyro-based localization), Lab 11 (complementary filter) and Lab 12 (Kalman filter — σ becomes your **R**).

Every parameter must be reported **with units**, the **method** used, and the **raw log** it was computed from.

### TRIK gyroscope API

Docs: <https://help.trikset.com/trik/programming-code/object-brick/class-gyroscope> · runtime reference: <https://dl.trikset.com/docs/runtime/html/classtrikControl_1_1GyroSensorInterface.html>

| Call | Returns |
|---|---|
| `brick.gyroscope().readRawData()` | 3 angular rates, **uncalibrated** (units not documented — see §6) |
| `brick.gyroscope().read()` | 7 values: `[0..2]` rates in mdeg/s, `[3]` timestamp in µs, `[4..6]` tilt angles in mdeg |

> Do **not** use TRIK's built-in `calibrate()`. The robot only **logs** data. All processing, including your offset calibration (§1), is done offline in Colab.

> Use `readRawData()` for all experiments: it is the sensor output with no correction applied.
> On-robot code: JavaScript / pure Python only (no NumPy). Log to CSV on the robot, analyse offline in Colab.
> Before every static measurement: robot powered on and still for **2 min** (warm-up), on a rigid surface, motors off.
> **One 3-min static log covers §1, §2, §4 and §5.** Record it once and reuse it.

---

## Lab execution

Write **one TRIK program** that drives the robot with a rotation signal and logs the gyro and both encoders together. The analysis compares two angles:

- **Gyro angle:** the integrated bias-corrected rate, $\theta_{gyro}(t) = \int (\omega_z - b_0)\,dt$. This is the sensor under test.
- **Encoder angle:** the heading computed from the wheels, $\theta_{enc}(t) = \frac{r}{L}(\varphi_R - \varphi_L)$, with $r$ and $L$ from Lab 5. This is the reference.

The rotation signal must reach **saturation** (±100 % motor power) at least once. The fastest turns give the measurement range (§3) and show whether the scale factor holds at high rate (§6).

### Step 1 — Static run (motors off)

| Phase label | What the robot does | Duration | Used in |
|---|---|---|---|
| `warmup` | still, not logged | 2 min | — |
| `static` | still, logged | 3 min | §1, §2, §4, §5 |

### Step 2 — Rotation run (choose one option)

**Option A — open loop, in-place rotation** (the inputs from Assignment 1). Wheel powers are $u_R = u(t)$ and $u_L = -u(t)$. The signal is clipped to the motor limit:
$$u(t) = \mathrm{sat}_{\pm 100}\big(A\,f(t)\big)$$

| Phase label | Signal $f(t)$ | Amplitude $A$ | Duration |
|---|---|---|---|
| `sin` | $\sin(2\pi t / T)$, $T = 4$ s | 30 → 60 → 150 % (one step every 3 periods) | 36 s |
| `rect` | square wave ±1, $T = 4$ s | 30 → 60 → 150 % (one step every 3 periods) | 36 s |

$A = 150\,\%$ is clipped to ±100 %. The sine flattens into a near-square wave, so the robot spends time at its maximum turn rate.

**Option B — closed loop, point-to-point trajectory with many turns.** Use your go-to-goal controller from Lab 7 on a waypoint path with sharp heading changes. Good choices are a zigzag, a star, or the digits of your student ID. The path needs at least **8 turns** of ≥ 90°, and the angular-velocity command must hit its saturation limit on the sharp turns. Phase label: `traj`, about 1–2 min.

In both options, log for 3 s at rest after the last move, so that the final angles can be compared at standstill.

### Step 3 — Compare gyro and encoder (offline)

1. Plot $\theta_{gyro}(t)$ and $\theta_{enc}(t)$ on one figure. Plot the error $e(t) = \theta_{gyro} - \theta_{enc}$ underneath.
2. Plot the rate from both sensors: $\omega_z$ against $d\theta_{enc}/dt$. Saturation of the gyro shows as a flat top where the gyro stops following the encoders (§3).
3. Plot $\theta_{gyro}$ against $\theta_{enc}$. The slope of a line fit is $1 + s$ (§6).
4. Explain where $e(t)$ grows. Is it bias (steady growth while the robot is still), scale factor (jumps at every turn), saturation (jumps only on the fastest turns), or wheel slip (encoder error at hard acceleration)?

**Slip check:** put a tape mark on the floor in line with the robot's nose before Step 2. When the robot returns to its start heading, measure the remaining angle with a protractor. Neither sensor is perfect. The mark shows which one is closer to the truth.

### Program requirements

- **Logging.** Every ~10 ms, add one CSV line:
  `t_us, gz_cal, encL, encR
  - `t_us` = `read()[3]` (gyro timestamp, µs)
  - `gz_cal` = `read()[2]` (mdeg/s)
- **Buffering.** Collect lines in a string and write them to the file in blocks. Calling `script.writeToFile` on every sample slows the loop down.
- **Encoder units.** Check whether the encoders return degrees or ticks.

Links:
- TRIK JavaScript API (motors, encoders, gyroscope, `script`): <https://help.trikset.com/trik/programming-code>
- Lecture slide 3: proprioceptive sensors. Encoders and gyro measure the same rotation in different ways.
- Assignment 1: step, sinusoidal and custom inputs.

---

## Parameters to identify

### 1. Offset (bias) — $b_0$

**What:** the mean output when the robot is not rotating, in deg/s.

**How (proposed method — static averaging):**
1. Take the first **T = 30 s** of the static log.
2. $b_0 = \frac{1}{N}\sum_{k=1}^{N}\omega_k$. Report also the standard error $\sigma/\sqrt{N}$.
3. Recompute $b_0$ from the first 1, 2, 5, 10, 20, 30 s and plot $b_0(T)$. Where the curve flattens is your **recommended calibration time**.
4. **Your own calibration method.** Steps 1–3 are the baseline. Write your own offset-calibration function in Colab, `calibrate_gyro(log)`, which takes the static log and returns $b_0$. You choose the algorithm (for example outlier rejection, a median, or a moving window) and the calibration time. Justify both with the $b_0(T)$ plot. Show the heading error left after you subtract your $b_0$ from the rotation run.

Links:
- MakersPortal, *Gyroscope and Accelerometer Calibration with Raspberry Pi* — static-offset calibration in Python: <https://makersportal.com/blog/calibration-of-an-inertial-measurement-unit-imu-with-raspberry-pi-part-ii>
- Lecture slide 7 — systematic vs. non-systematic errors.

---

### 2. Bias drift — $d$

**What:** how fast the offset itself changes during a run, in deg/s per min; and the resulting heading error, in deg/min.

**How:**
1. Use the full **3-min** static log.
2. Split the log into 30-s windows, compute the mean rate in each, fit a line → slope $d$.
3. Integrate (trapezoid rule with the **real timestamps**):
   - (a) raw rate → heading drift dominated by $b_0$, ~linear; report slope in deg/min;
   - (b) rate minus $b_0$ → residual drift; report heading error after 1, 2, 3 min.
4. Check: does (a)'s slope match $b_0 \cdot 60$?

Links:
- Lecture slides 15, 17 — INS drift tables and "unlimited drift".
- Analog Devices, *Gyro Mechanical Performance: The Most Important Parameter* — why real drift is worse than the datasheet: <https://www.analog.com/en/resources/technical-articles/gyro-mechanical-performance.html>

---

### 3. Measurement range — $\omega_{max}$

**What:** the maximum rate the sensor reports before clipping, in ±deg/s.

**How:** use the saturated part of the rotation run (`sin`/`rect` at $A = 150\,\%$, or the sharpest turns of `traj`). Plot `gz_raw` against the encoder rate $d\theta_{enc}/dt$. Saturation shows as a flat top where the gyro stops following the encoders. If the robot cannot reach the limit under its own power, spin it faster by hand on a turntable or office chair. Report both + and − limits.

Links:
- Lecture slide 5 — dynamic range.
- Datasheet example for comparison (range, noise rows) — VectorNav VN-100: <https://www.vectornav.com/docs/default-source/product-brief/vn-100-product-brief.pdf>

---

### 4. Resolution — $\Delta$

**What:** the smallest change in output (quantisation step), in deg/s.

**How:** from the static log, sort the distinct raw values and take the smallest non-zero difference. Convert to deg/s with the factor from §6.

Links: Lecture slide 5 — resolution and A/D conversion.

---

### 5. Noise — $\sigma$

**What:** the random part of the output at rest, in deg/s.

**How** (3-min static log, $b_0$ subtracted):
- Standard deviation σ (deg/s). This is the measurement noise **R** for Lab 12 at your sample rate.
- Histogram with fitted Gaussian. Is the noise Gaussian? Are there outliers or spikes?

Links:
- Lecture slide 7 — precision, random errors.
- VectorNav primer (above) — how σ relates to datasheet noise specs.

---

### 6. Scale factor — $s$ *(added)*

**What:** the gain of the sensor: the raw → deg/s conversion and the scale-factor error $s$ (how much the gyro over- or under-reports a real rotation). The sign of positive rotation is checked here too.

**How:**
1. **Sign:** when $\theta_{enc}$ increases (CCW), is `gz_raw` positive too? It must match the heading convention in your odometry. Recall the encoder sign bug in `trajectory_blocks.js`.
2. **Raw → deg/s:** during the rotation phases, plot `gz_raw` against `gz_cal`. After bias removal, the slope gives the conversion factor.
3. **Scale-factor error:** fit a line to $\theta_{gyro}$ against $\theta_{enc}$ (Step 3 of *Lab execution*). The slope is $1 + s$:
   $$s = \frac{\Delta\theta_{gyro}}{\Delta\theta_{enc}} - 1$$
   Fit CCW and CW segments separately.
   Report $s$ in % for CW and CCW separately. Asymmetry is common.
4. Compare $s$ at the different amplitudes (or slow vs. sharp turns) to check that it does not depend on speed. Use the slip check to judge how far $\theta_{enc}$ can be trusted.

Links:
- Lecture slide 6 — sensitivity and the accuracy formula.
- Woodman TR-696 (above) — calibration errors.

---

## Deliverables

Submit to `CS413 - Robotics/Lab9/`:

1. **Robot program** (`.js` / `.qrs`). It runs the full sequence from *Lab execution*: static run, rotation run (Option A or B, state which), and gyro + encoder logging. No processing on the robot.
2. **Raw log** (`lab9_gyro.csv`) with all phases, plus the floor-mark slip angle.
3. **Colab notebook** with the analysis and plots: $b_0(T)$, drift curves, saturation plot, your `calibrate_gyro()` method, noise histogram, $\theta_{gyro}$ vs. $\theta_{enc}$ with error $e(t)$, scale-factor fit.
4. **Simulated gyro.** A Python function `gyro_sim(omega_true, t)` implementing the model from the Lecture section with your parameters. Feed it a recorded rotation and overlay the simulated output on the real log.
5. **Parameter table:**

| Parameter | Symbol | Value | Unit | Method |
|---|---|---|---|---|
| Offset (bias) | $b_0$ | | deg/s | static mean, T = … |
| Bias drift | $d$ | | deg/s/min | 30-s window means |
| Heading drift, uncorrected | | | deg/min | slope of θ(t) |
| Measurement range | ±$\omega_{max}$ | | deg/s | saturation test |
| Resolution | $\Delta$ | | deg/s | quantisation step |
| Noise std | $\sigma$ | | deg/s | static, 3 min |
| Raw → deg/s factor | | | — | §6 |
| Scale-factor error CCW / CW | $s$ | | % | gyro vs. encoder angle |
| Positive rotation direction | | CCW / CW | — | §6 |

6. **Short analysis** (≤ 1 page). Which error source dominates heading error after 10 s, 1 min and 3 min of driving? How does your calibration method work, how long does it need to run, and how much heading error does it leave after 3 min?
