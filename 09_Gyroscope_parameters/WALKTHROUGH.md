# Lab 9 — walkthrough

The lab asks for one thing: **six numbers that describe your gyroscope**, measured from data,
plus a simulated gyro built from them. Everything else (plots, table, one page of text) is
just how you show the work. The six numbers are the offset $b_0$, the drift $d$, the range
$\pm\omega_{max}$, the resolution $\Delta$, the noise $\sigma$ and the scale-factor error $s$.

You do not calibrate anything on the robot. The robot only **logs**; all the thinking happens
in the notebook.

## 0. Before you start

- Robot charged, on a **rigid** floor (not carpet), motors off, nobody touching the table.
- A piece of tape on the floor in line with the robot's nose, and a protractor.
- Your Lab 5 numbers: wheel radius $r$ and wheel base $L$ (the notebook uses 0.042 m and
  0.194 m — replace them with yours).
- Laptop on the robot's Wi-Fi (`192.168.77.1`).

## 1. Open the program in TRIK Studio

`Lab9_gyro.qrs` is a **block diagram**: open it with *File → Open* and the blocks appear on the
canvas, each part with a comment beside it. `lab9_gyro.py` is the same logic as code, if you
prefer to read it that way.

Check the ports against your robot: on the course robots the right wheel is **M3/E3** and the
left is **M4/E4**. The 2D model is already set to left = M4, right = M3.

Run it once in the **2D model** to see the sequence. Two things to know about that run:

- The model's gyro is ideal, so you will get $b_0 \approx 0$, $\sigma \approx 0$ and $s \approx 0$.
  That is expected — the real parameters must come from the real robot.
- The model does not run System Call blocks, so the `gz_raw` column stays 0 there. The notebook
  falls back to the quantisation of `gz_cal` when that happens.
- The full sequence is 4.5 minutes of simulated time. To make a quick dry run, shorten the Timer
  blocks (120000 → 2000, 180000 → 5000, 36000 → 2000) and put them back before the real run.

## 2. What the program does

| Phase | Duration | Robot | What it is for |
|---|---|---|---|
| `warmup` | 2 min | still, not logged | the MEMS gyro needs to reach thermal equilibrium |
| `static` | 3 min | still, logged | §1 offset, §2 drift, §4 resolution, §5 noise |
| `sin` | 36 s | in-place rotation, $A$ = 30 → 60 → 150 % | §3 range, §6 scale factor |
| `rect` | 36 s | the same with a square wave | §3, §6 at a different rate profile |
| `rest` | 3 s | still, logged | compare the final angles at standstill |

The 150 % amplitude is clipped to ±100 % wheel power, so the robot turns at its maximum rate
and the gyro saturates — that is the point of that step.

**Do not touch the robot during `warmup` and `static`.** A bump on the table during the static
log shows up as a spike in the noise histogram and ruins $b_0$.

The diagram reads top to bottom: initialise → remove the old log → write the header → clear the
encoders → warm-up timer → one loop per phase. Inside each loop: read the sensors, build one CSV
line, and every 200 lines write the buffer to the card. The rotation loops set the wheel power
from the signal, then log.

## 3. Get the log off the robot

The program writes `lab9_gyro/lab9_gyro.csv` and `lab9_gyro/run_info.txt` in the robot's
working directory. `run_info.txt` contains the absolute path. Copy the folder with
`scp root@192.168.77.1:<path>/lab9_gyro.csv .` (or the file manager in TRIK Studio).

## 4. Run the notebook

Open `Gyro_parameters.ipynb` in Google Colab, upload `lab9_gyro.csv`, set `R_WHEEL` and
`L_BASE` to your Lab 5 values, then *Runtime → Run all*. Every section prints the number it
found and draws the plot the report needs.

## 5. What each section is really asking

| Section | Question | What you report |
|---|---|---|
| §1 | What does the gyro say when nothing moves? | $b_0$ in deg/s, its standard error, the $b_0(T)$ curve, your `calibrate_gyro()` and the heading error it leaves after 3 min |
| §2 | Does that offset stay put? | $d$ in deg/s/min, the uncorrected heading drift in deg/min, and the residual drift after 1, 2, 3 min |
| §3 | At what rate does the sensor stop following? | $\pm\omega_{max}$ in deg/s, from the flat top of the gyro-vs-encoder-rate plot |
| §4 | What is the smallest change it can see? | $\Delta$ in deg/s, and the raw → deg/s factor |
| §5 | How noisy is it? | $\sigma$ in deg/s, the histogram, whether the noise is Gaussian |
| §6 | Does it over- or under-report a real rotation? | $s$ in % for CCW and CW, the sign convention, and whether $s$ depends on speed |

The one-page analysis at the end is the part that earns the marks: say **which error source
dominates** after 10 s, 1 min and 3 min, and **where the error $e(t)$ grows** in the rotation
run — steady growth while still is bias, jumps at every turn are scale factor, jumps only on
the fastest turns are saturation, and encoder error at hard acceleration is wheel slip.

## 6. Mistakes that cost marks

- Using `brick.gyroscope().calibrate()` — the lab forbids it, the offset must come from your
  own offline method.
- Calling `script.writeToFile` on every sample — it stretches the loop period. The program
  buffers 200 lines and writes them in one go.
- Assuming the sample period is exactly 10 ms. It is not; always use the logged `t_us`.
- Fitting $s$ over the saturated part of the run. The gyro stops following there, so the
  slope collapses; the notebook fits each 12-s segment separately and flags the saturated ones.
- Forgetting the tape-mark angle. It is the only independent check of which sensor is right.
- Reporting a number without a unit, a method and the log it came from.

## 7. Submission

1. `lab9_gyro.py` or `Lab9_gyro.qrs`
2. `lab9_gyro.csv` + the tape-mark slip angle
3. `Gyro_parameters.ipynb`, executed, with the plots
4. `gyro_sim()` and the overlay on the recorded rotation
5. the parameter table
6. the short analysis

## Rebuilding the project file

The diagram is generated from `tools/lab9_spec.json` with the TRIK Studio skill's builder:

```bash
python ../trik-studio-skill/trik-studio/scripts/qrs_tool.py build tools/lab9_spec.json \
    -o Lab9_gyro.qrs --template Gyro_demo.qrs --drop-code
python ../trik-studio-skill/trik-studio/scripts/qrs_tool.py wheels Lab9_gyro.qrs M4 M3
```

Edit the spec, rebuild, and the `.qrs` carries the new diagram. `tools/make_notebook.py`
regenerates the notebook the same way.
