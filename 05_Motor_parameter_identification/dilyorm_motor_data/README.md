# Lab 5 — automated motor identification (dilyorm)

The professor's demo (`../Motor_identification.qrs`) records **one** step (M4 at 100 %) and writes
to the file inside the loop, which gives one sample every ~42 ms. Here a single program runs **all
40 PWM levels (−100…+100 %, 5 % steps) on both drive wheels** (80 steps, about 5 minutes). It keeps
the samples in memory while the motor runs, so it samples every few ms. A second script fits every
run and writes the report.

| File | What it is |
|---|---|
| `motor_identification.qrs` | Deliverable 1. TRIK Studio project; its Python code = `collect_motor_data.py` |
| `collect_motor_data.py` | Source of the robot program (edit this, then rebuild the `.qrs`) |
| `pull_data.py` | Copies the result folder from the robot into `motor_data/` (SSH/SCP) |
| `analyze.py` | Fits every file, makes the plots, writes `report.md` (deliverable 3) |
| `motor_data/` | Deliverable 2. Raw robot files, **never edit them** |
| `tools/build_qrs.py` | Rebuilds the `.qrs` after you change `collect_motor_data.py` |

## Procedure

1. **Check ports.** In `collect_motor_data.py`, `WHEELS` is set to left = `M4/E4` (wheel 1) and
   right = `M3/E3` (wheel 2). If your robot is wired differently, change it and run
   `python tools/build_qrs.py`.
2. **Charge the battery.** Lift the robot so both wheels spin freely.
3. Open `motor_identification.qrs` in TRIK Studio, connect to the robot, then **Upload and run**.
   The display shows the current wheel and PWM level, and the robot beeps when finished.
   The files are written on the robot to `dilyorm_motor_data/`. The unique name stops classmates'
   runs from overwriting each other.
4. With the laptop still on the robot's Wi-Fi, run:
   ```
   python pull_data.py
   ```
   If SSH does not work, copy the `dilyorm_motor_data` folder into `motor_data/` with WinSCP
   (host `192.168.77.1`, user `root`, empty password). `run_info.txt` contains the absolute path.
5. Run:
   ```
   python analyze.py
   ```
   This writes `report.md` and `figures/`. Then rewrite the *Discussion (draft)* section in your own words.

Requirements on the laptop: `pip install numpy scipy matplotlib`.

## What the analysis does

- For each file it fits `θ(t) = ω_ss·(t − T_m + T_m·e^(−t/T_m))` with `curve_fit`.
- It reads `U = PWM/100 · U_battery` from the file header. The robot logs both the idle voltage and
  the voltage under load; the loaded value is used.
- Levels where the wheel is slower than 3 % of its top speed are marked *stalled*, which is the measured dead zone.
- On |PWM| ≥ 20 % it fits `ω_ss = (U − U0)/k_e` per wheel and per direction. T_m is the median of the
  levels whose fit has at least 4 samples inside the transient.
- It simulates the identified model with `odeint` and plots it against one measured run. The default is
  wheel 1 at 50 %; change it with `--step-wheel 2 --step-pwm 70`.
- If the encoder counts backwards relative to the motor, it detects this and reports it. The raw data is left untouched.

Tested on the course reference data: `python analyze.py --data ../src/motor_data/data.zip --out /tmp/ref/report.md`.
The robot program was also run end to end in the TRIK 2D simulator, which has no battery, so files there
show `-1`.
