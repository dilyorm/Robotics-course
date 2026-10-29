# Lab 5 — Motor parameter identification (Assignment 1, student 240191)

| File | What |
|---|---|
| `motor_steps.qrs` | Program A, step series −100…100 % on M4 (blocks only) |
| `motor_signal.qrs` | Program B, chirp 60 %, 0.2 → 4 Hz over 10 s on M4 (blocks only) |
| `programs/` | every program run on the robot: steps M4/M3 (+ `_run2`), chirp and square on M4/M3; `make_a1.py` writes their block specs |
| `motor_data/` | raw files exactly as the robot wrote them (`angle deg, time ms, PWM %`) + `battery.txt` |
| `robotics_lab5_240191.ipynb` | Colab notebook: processing, plots, parameter table, model vs real, artifacts; runs top to bottom on `motor_data/` |
| `scripts/make_notebook.py` | regenerates the notebook (`python scripts/make_notebook.py .`) |

Robot trik-6fc169, lifted (wheels free), 2026-10-29, battery 11.83–11.91 V. Left = M4/E4, right = M3/E3.
`steps_M4_91.txt` and `steps_M3_run2_91.txt` are reruns: the first attempts were cut off by a Wi-Fi drop.

Colab: zip `motor_data/` as `motor_data.zip`, upload when the first cell asks, Run all.
The model explanation (section 1) and the four analysis paragraphs (section 9) are left for you to write.
