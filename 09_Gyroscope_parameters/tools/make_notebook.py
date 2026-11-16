"""Write Gyro_parameters.ipynb (Lab 9 analysis) next to lab9_gyro.csv.

usage: python tools/make_notebook.py
       jupyter nbconvert --to notebook --execute --inplace Gyro_parameters.ipynb
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "Gyro_parameters.ipynb"

cells = []


def md(s):
    cells.append({"cell_type": "markdown", "id": "c%d" % len(cells), "metadata": {},
                  "source": s.strip("\n").splitlines(True)})


def code(s):
    cells.append({"cell_type": "code", "id": "c%d" % len(cells), "metadata": {},
                  "execution_count": None, "outputs": [],
                  "source": s.strip("\n").splitlines(True)})


md(r"""
# Lab 9 — Gyroscope parameters

**What this notebook does.** It turns one log, `lab9_gyro.csv`, into the six parameters of the
sensor model from the lab README, the plots the report needs, and the parameter table.

$$\omega_{meas}(t_k) = Q_{\Delta}\Big(\mathrm{sat}_{\pm\omega_{max}}\big[(1+s)\,\omega_{true}(t_k) + b_0 + d\,t_k + n_k\big]\Big)$$

**Before you run it.** Upload `lab9_gyro.csv` (from the robot, or from the 2D model) with the
program `lab9_gyro.py` / `Lab9_gyro.qrs`. Columns: `t_us,phase,u,gz_cal,gz_raw,encL,encR`.
Fill in the geometry from your Lab 5 identification and the slip angle you measured with the
tape mark on the floor.

| Deliverable | Where |
|---|---|
| §1 offset $b_0$, $b_0(T)$, `calibrate_gyro()` | cells below §1 |
| §2 drift $d$, heading drift | §2 |
| §3 range $\pm\omega_{max}$ | §3 |
| §4 resolution $\Delta$, raw → deg/s | §4 |
| §5 noise $\sigma$ | §5 |
| §6 scale factor $s$, sign | §6 |
| Simulated gyro `gyro_sim()` | §7 |
| Parameter table | §8 |
| Short analysis | §9 (write it there) |
""")

code(r"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

CSV = 'lab9_gyro.csv'
try:
    df = pd.read_csv(CSV, comment='#')
except FileNotFoundError:                      # Colab: upload the log
    from google.colab import files
    up = files.upload()
    df = pd.read_csv(list(up)[0], comment='#')

# Geometry from Lab 5 (edit to your identified values)
R_WHEEL = 0.042        # m, wheel radius
L_BASE = 0.194         # m, distance between the wheels

df['t'] = (df.t_us - df.t_us.iloc[0]) / 1e6                 # s
df['gz'] = df.gz_cal / 1000.0                               # deg/s
df['th_enc'] = np.deg2rad(df.encR - df.encL) * R_WHEEL / L_BASE   # rad
df['th_enc_deg'] = np.rad2deg(df.th_enc)

print(df.groupby('phase').agg(n=('t', 'size'), t_start=('t', 'min'), t_end=('t', 'max')))
print('mean sample period: %.1f ms' % (1000 * np.mean(np.diff(df.t))))
print('total: %.1f min' % (df.t.iloc[-1] / 60))
""")

code(r"""
fig, ax = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
ax[0].plot(df.t, df.gz, lw=0.6)
ax[0].set_ylabel('$\\omega_z$ (deg/s)')
ax[1].plot(df.t, df.u, lw=0.6, color='tab:orange')
ax[1].set_ylabel('wheel power u (%)')
ax[1].set_xlabel('t (s)')
for a in ax:
    for ph, g in df.groupby('phase'):
        a.axvspan(g.t.min(), g.t.max(), alpha=0.08)
        a.text(g.t.min(), a.get_ylim()[1], ph, fontsize=8, va='top')
    a.grid(alpha=0.3)
fig.suptitle('whole run: rate and commanded power')
plt.tight_layout()
plt.show()
""")

md(r"""
## §1 Offset (bias) $b_0$

Mean output at rest, in deg/s, with its standard error $\sigma/\sqrt{N}$. The $b_0(T)$ curve
shows how long the average has to run before it stops moving — that is your recommended
calibration time.
""")

code(r"""
st = df[df.phase == 'static'].reset_index(drop=True)
t_st = st.t.values - st.t.values[0]
gz_st = st.gz.values

Ts = [1, 2, 5, 10, 20, 30, 60, 90, 120, 180]
b0T = np.array([gz_st[t_st < T].mean() for T in Ts])
seT = np.array([gz_st[t_st < T].std(ddof=1) / np.sqrt((t_st < T).sum()) for T in Ts])

fig, ax = plt.subplots(1, 2, figsize=(12, 4))
ax[0].errorbar(Ts, b0T, yerr=seT, marker='o', capsize=3)
ax[0].set_xscale('log')
ax[0].set_xlabel('averaging time T (s)')
ax[0].set_ylabel('$b_0(T)$ (deg/s)')
ax[0].set_title('offset estimate vs averaging time')
ax[0].grid(alpha=0.3)

ax[1].plot(t_st, gz_st, lw=0.4, alpha=0.6)
ax[1].axhline(b0T[-1], color='r', ls='--', label='$b_0$ (180 s)')
ax[1].set_xlabel('t (s)')
ax[1].set_ylabel('$\\omega_z$ (deg/s)')
ax[1].set_title('static log')
ax[1].legend()
ax[1].grid(alpha=0.3)
plt.tight_layout()
plt.show()

print('b0(T):', ', '.join('%d s: %.4f' % (T, b) for T, b in zip(Ts, b0T)))
print('standard error at 180 s: %.5f deg/s' % seT[-1])
""")

code(r"""
def calibrate_gyro(log, window=30.0, k_mad=3.0):
    '''Offset from the first `window` seconds of a static log.

    Median after rejecting samples further than k_mad robust sigmas (MAD) from it, so a bump
    against the table or a spike does not move the calibration.
    '''
    s = log[log.phase == 'static']
    t = s.t.values - s.t.values[0]
    w = s.gz.values[t < window]
    med = np.median(w)
    mad = np.median(np.abs(w - med))
    keep = np.abs(w - med) <= k_mad * 1.4826 * mad
    return float(np.mean(w[keep])), int(keep.sum()), len(w)


b0, kept, total = calibrate_gyro(df, window=30.0)
print('calibrate_gyro(): b0 = %.4f deg/s  (%d of %d samples kept)' % (b0, kept, total))

res_st = gz_st - b0
th_res = np.concatenate([[0], np.cumsum(0.5 * (res_st[1:] + res_st[:-1]) * np.diff(t_st))])
print('heading error left after 3 min with this b0: %.2f deg' % th_res[-1])
""")

md(r"""
## §2 Bias drift $d$

The offset itself moves during a run. Split the 3-min static log into 30-s windows, fit a line
through the window means: the slope is $d$ in deg/s per min. Then integrate the rate with the
real timestamps — raw (dominated by $b_0$) and bias-corrected (residual drift).
""")

code(r"""
WIN = 30.0
edges = np.arange(0, t_st.max() + WIN, WIN)
centers, means = [], []
for a in edges[:-1]:
    m = (t_st >= a) & (t_st < a + WIN)
    if m.sum() > 10:
        centers.append(a + WIN / 2)
        means.append(gz_st[m].mean())
centers, means = np.array(centers), np.array(means)
d = np.polyfit(centers, means, 1)[0] * 60.0        # deg/s per min

th_raw = np.concatenate([[0], np.cumsum(0.5 * (gz_st[1:] + gz_st[:-1]) * np.diff(t_st))])
th_cor = np.concatenate([[0], np.cumsum(0.5 * ((gz_st - b0)[1:] + (gz_st - b0)[:-1]) * np.diff(t_st))])
slope_raw = np.polyfit(t_st, th_raw, 1)[0] * 60.0  # deg/min

fig, ax = plt.subplots(1, 2, figsize=(12, 4))
ax[0].plot(centers, means, 'o-')
ax[0].plot(centers, np.polyval(np.polyfit(centers, means, 1), centers), 'r--',
           label='slope %.2e deg/s per s' % (d / 60))
ax[0].set_xlabel('window centre (s)')
ax[0].set_ylabel('mean rate (deg/s)')
ax[0].set_title('30-s window means')
ax[0].legend()
ax[0].grid(alpha=0.3)

ax[1].plot(t_st, th_raw, label='raw')
ax[1].plot(t_st, th_cor, label='bias-corrected')
ax[1].set_xlabel('t (s)')
ax[1].set_ylabel('heading (deg)')
ax[1].set_title('heading drift at rest')
ax[1].legend()
ax[1].grid(alpha=0.3)
plt.tight_layout()
plt.show()

print('d = %.3e deg/s per s = %.4f deg/s per min' % (d / 60, d))
print('raw heading drift: %.2f deg/min   (b0*60 = %.2f deg/min)' % (slope_raw, b0 * 60))
for T in (60, 120, 180):
    print('bias-corrected heading error after %3d s: %+.2f deg' % (T, th_cor[t_st <= T][-1]))
""")

md(r"""
## §4 Resolution $\Delta$ and the raw → deg/s factor

`gz_raw` is the uncalibrated sensor output; `gz_cal` is the same rate in mdeg/s. The slope of
`gz_cal` against `gz_raw` during the rotation run is the conversion factor. The smallest
non-zero step between distinct raw values, times that factor, is the resolution.
""")

code(r"""
rot = df[df.phase.isin(['sin', 'rect'])].reset_index(drop=True)
ok = np.abs(rot.gz) < 0.9 * np.abs(rot.gz).max()          # leave the saturated part out
factor, offset_raw = np.polyfit(rot.gz_raw[ok], rot.gz[ok], 1)   # deg/s per count
pred = factor * rot.gz_raw[ok] + offset_raw
r2 = 1 - np.sum((rot.gz[ok] - pred) ** 2) / np.sum((rot.gz[ok] - rot.gz[ok].mean()) ** 2)

vals = np.unique(st.gz_raw.values)
steps = np.diff(vals)
steps = steps[steps > 0]
step_min = steps.min()
step_mode = np.bincount(steps).argmax()

fig, ax = plt.subplots(1, 2, figsize=(12, 4))
ax[0].plot(rot.gz_raw[ok], rot.gz[ok], '.', ms=1, alpha=0.3)
ax[0].plot(rot.gz_raw[ok], pred, 'r-', lw=1, label='fit %.4f deg/s per count' % factor)
ax[0].set_xlabel('gz_raw (counts)')
ax[0].set_ylabel('gz_cal (deg/s)')
ax[0].set_title('raw to deg/s, $R^2$ = %.4f' % r2)
ax[0].legend()
ax[0].grid(alpha=0.3)

ax[1].hist(st.gz_raw.values, bins=60)
ax[1].set_xlabel('gz_raw (counts) at rest')
ax[1].set_ylabel('samples')
ax[1].set_title('quantisation at rest')
ax[1].grid(alpha=0.3)
plt.tight_layout()
plt.show()

print('raw -> deg/s factor: %.5f deg/s per count' % factor)
print('distinct raw values at rest: %d, smallest step %d count(s), most common step %d'
      % (len(vals), step_min, step_mode))
print('resolution: %.4f deg/s (smallest) / %.4f deg/s (typical)'
      % (step_min * factor, step_mode * factor))
""")

md(r"""
## §5 Noise $\sigma$

Standard deviation of the static log after removing $b_0$. This is the measurement noise
**R** for the Kalman filter in Lab 12 at your sample rate. The histogram shows whether the
noise is Gaussian and whether there are spikes.
""")

code(r"""
res = gz_st - b0
sigma = res.std(ddof=1)
outliers = np.abs(res) > 4 * sigma

fig, ax = plt.subplots(figsize=(7, 4))
ax.hist(res, bins=60, density=True, alpha=0.6, label='data')
x = np.linspace(res.min(), res.max(), 400)
ax.plot(x, np.exp(-x ** 2 / (2 * sigma ** 2)) / (sigma * np.sqrt(2 * np.pi)), 'r-',
        label='Gaussian $\\sigma$ = %.4f deg/s' % sigma)
ax.set_xlabel('$\\omega_z - b_0$ (deg/s)')
ax.set_ylabel('density')
ax.set_title('static noise, 3 min')
ax.legend()
ax.grid(alpha=0.3)
plt.tight_layout()
plt.show()

print('sigma = %.4f deg/s   (%.1f %% of samples beyond 4 sigma)'
      % (sigma, 100.0 * outliers.mean()))
print('sigma at %.0f Hz sample rate: %.4f deg/s' % (1 / np.mean(np.diff(t_st)), sigma))
""")

md(r"""
## §3 Measurement range $\pm\omega_{max}$

Plot the gyro rate against the encoder rate $d\theta_{enc}/dt$. Where the gyro stops following
the encoders, it is saturated: that flat top is the measurement range. The 150 % amplitude is
clipped to ±100 % wheel power, so the robot turns at its maximum rate there.
""")

code(r"""
rate_enc = np.gradient(rot.th_enc_deg.values, rot.t.values)     # deg/s

fig, ax = plt.subplots(figsize=(7, 5))
sc = ax.scatter(rate_enc, rot.gz, c=np.abs(rot.u), s=2, cmap='viridis')
lim = max(np.abs(rate_enc).max(), np.abs(rot.gz).max()) * 1.05
ax.plot([-lim, lim], [-lim, lim], 'r--', lw=1, label='gyro = encoder')
ax.set_xlabel('encoder rate $d\\theta_{enc}/dt$ (deg/s)')
ax.set_ylabel('$\\omega_z$ (deg/s)')
ax.set_title('saturation: gyro vs encoder rate')
ax.legend()
ax.grid(alpha=0.3)
plt.colorbar(sc, label='|u| (%)')
plt.tight_layout()
plt.show()

sat = rot[np.abs(rot.u) >= 100]
wmax_pos = sat[sat.u > 0].gz.median()
wmax_neg = sat[sat.u < 0].gz.median()
print('at |u| = 100 %%: +%.1f / %.1f deg/s' % (wmax_pos, wmax_neg))
print('largest |rate| seen: %.1f deg/s' % np.abs(rot.gz).max())
print('encoder rate at saturation: %.1f deg/s' % np.abs(rate_enc[np.abs(rot.u) >= 100]).max())
""")

md(r"""
## §6 Scale factor $s$ and the sign of positive rotation

$\theta_{gyro} = \int(\omega_z - b_0)\,dt$ against $\theta_{enc} = \frac{r}{L}(\varphi_R-\varphi_L)$.
The slope of a line fit is $1+s$, so $s = \text{slope} - 1$. Fit CCW and CW separately, and each
amplitude separately, to see whether $s$ depends on speed.
""")

code(r"""
gz_rot = rot.gz.values - b0
th_gyro = np.concatenate([[0], np.cumsum(0.5 * (gz_rot[1:] + gz_rot[:-1])
                                         * np.diff(rot.t.values))])
th_enc = rot.th_enc_deg.values - rot.th_enc_deg.values[0]

fig, ax = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
ax[0].plot(rot.t, th_gyro, label='$\\theta_{gyro}$')
ax[0].plot(rot.t, th_enc, label='$\\theta_{enc}$')
ax[0].set_ylabel('heading (deg)')
ax[0].legend()
ax[0].grid(alpha=0.3)
ax[1].plot(rot.t, th_gyro - th_enc, color='tab:red')
ax[1].set_ylabel('$e = \\theta_{gyro} - \\theta_{enc}$ (deg)')
ax[1].set_xlabel('t (s)')
ax[1].grid(alpha=0.3)
fig.suptitle('gyro vs encoder heading')
plt.tight_layout()
plt.show()

fig, ax = plt.subplots(figsize=(6, 6))
ax.plot(th_enc, th_gyro, '.', ms=1, alpha=0.4)
ax.plot([th_enc.min(), th_enc.max()], [th_enc.min(), th_enc.max()], 'k--', lw=1, label='1:1')
ax.set_xlabel('$\\theta_{enc}$ (deg)')
ax.set_ylabel('$\\theta_{gyro}$ (deg)')
ax.set_title('scale factor fit')
ax.legend()
ax.grid(alpha=0.3)
plt.tight_layout()
plt.show()

wmax_abs = max(abs(wmax_pos), abs(wmax_neg))
slope_ang = np.polyfit(th_enc, th_gyro, 1)[0]
print('angle fit, whole run: slope %.4f -> s = %+.2f %%' % (slope_ang, 100 * (slope_ang - 1)))
print('  (saturation and bias drift accumulate in theta, so this is only a first look)')

print('sign check: theta_enc and theta_gyro move together ->',
      'OK' if np.corrcoef(th_enc, th_gyro)[0, 1] > 0 else 'MISMATCH, flip the gyro sign')
""")

code(r"""
# The rotation run is 3 x 12 s per phase, A = 30, 60, 150 % (clipped to 100 %).
# Fit each 12-s segment on its own: a saturation in one segment then cannot bias the others.
wmax_abs = max(abs(wmax_pos), abs(wmax_neg))
s_seg = []
for ph in ('sin', 'rect'):
    g = rot[rot.phase == ph].reset_index(drop=True)
    t0 = g.t.values[0]
    for i, A in enumerate((30, 60, 150)):
        m = (g.t.values - t0 >= 12 * i) & (g.t.values - t0 < 12 * (i + 1))
        if m.sum() < 50:
            continue
        idx = np.where(rot.phase.values == ph)[0][m]
        sl = np.polyfit(th_enc[idx], th_gyro[idx], 1)[0]
        sat = np.mean(np.abs(rot.gz.values[idx]) >= 0.98 * wmax_abs)
        print('%s A=%3d %%: slope %.4f -> s = %+.2f %%   (%.0f %% of samples saturated)%s'
              % (ph, A, sl, 100 * (sl - 1), 100 * sat,
                 '  <- s not meaningful here' if sat > 0.01 else ''))
        if sat <= 0.01:
            s_seg.append((sl - 1, m.sum()))

s_est = float(np.average([s for s, _ in s_seg], weights=[n for _, n in s_seg]))
print('s from the unsaturated segments: %+.2f %%' % (100 * s_est))

# CCW and CW inside those same segments
s_ccw_list, s_cw_list = [], []
for ph in ('sin', 'rect'):
    g = rot[rot.phase == ph].reset_index(drop=True)
    t0 = g.t.values[0]
    for i in range(3):
        m = (g.t.values - t0 >= 12 * i) & (g.t.values - t0 < 12 * (i + 1))
        idx = np.where(rot.phase.values == ph)[0][m]
        if len(idx) < 50 or np.mean(np.abs(rot.gz.values[idx]) >= 0.98 * wmax_abs) > 0.01:
            continue
        for sign, acc in ((1, s_ccw_list), (-1, s_cw_list)):
            mm = idx[rate_enc[idx] * sign > 1.0]
            if len(mm) > 100:
                acc.append(np.polyfit(th_enc[mm], th_gyro[mm], 1)[0] - 1)

s_ccw = float(np.mean(s_ccw_list))
s_cw = float(np.mean(s_cw_list))
print('CCW: s = %+.2f %%   CW: s = %+.2f %%' % (100 * s_ccw, 100 * s_cw))
""")

md(r"""
## §7 Simulated gyro

`gyro_sim()` implements the model from the lecture with the parameters identified above. Feed it
the encoder rate as the true rate and overlay the result on the real log.
""")

code(r"""
def gyro_sim(omega_true, t, b0, d, sigma, s, wmax, delta, seed=0):
    '''Simulated yaw-rate measurement: scale error, bias, drift, noise, saturation, quantisation.'''
    rng = np.random.default_rng(seed)
    w = (1 + s) * np.asarray(omega_true, float) + b0 + d * np.asarray(t, float) \
        + rng.normal(0, sigma, len(t))
    w = np.clip(w, -wmax, wmax)
    return np.round(w / delta) * delta


def smooth(x, n=9):
    k = np.ones(n) / n
    return np.convolve(x, k, mode='same')

sim = gyro_sim(smooth(rate_enc), rot.t.values, b0, d / 60, sigma, s_est,
               max(abs(wmax_pos), abs(wmax_neg)), step_mode * factor)

fig, ax = plt.subplots(figsize=(12, 4))
ax.plot(rot.t, rot.gz, lw=0.6, label='measured')
ax.plot(rot.t, sim, lw=0.6, alpha=0.8, label='simulated')
ax.set_xlabel('t (s)')
ax.set_ylabel('$\\omega_z$ (deg/s)')
ax.set_title('simulated gyro on the recorded rotation')
ax.legend()
ax.grid(alpha=0.3)
plt.tight_layout()
plt.show()

print('RMS difference measured - simulated: %.2f deg/s' % np.sqrt(np.mean((rot.gz - sim) ** 2)))
""")

md(r"""
## §8 Parameter table

Copy this into the report. Every row needs its unit, the method and the log it came from.
""")

code(r"""
table = pd.DataFrame([
    ('Offset (bias)', 'b0', '%.4f' % b0, 'deg/s', 'static mean, T = 30 s, MAD rejection'),
    ('Bias drift', 'd', '%.4f' % d, 'deg/s/min', '30-s window means, line fit'),
    ('Heading drift, uncorrected', '', '%.2f' % slope_raw, 'deg/min', 'slope of theta(t), static'),
    ('Measurement range', 'wmax', '+%.1f / %.1f' % (wmax_pos, wmax_neg), 'deg/s', 'saturation test, |u| = 100 %'),
    ('Resolution', 'Delta', '%.4f' % (step_mode * factor), 'deg/s', 'distinct raw values, static'),
    ('Noise std', 'sigma', '%.4f' % sigma, 'deg/s', 'static, 3 min, b0 removed'),
    ('Raw -> deg/s factor', '', '%.5f' % factor, 'deg/s per count', 'gz_cal vs gz_raw, rotation'),
    ('Scale-factor error CCW', 's', '%+.2f' % (100 * s_ccw), '%', 'theta_gyro vs theta_enc, CCW, unsaturated'),
    ('Scale-factor error CW', 's', '%+.2f' % (100 * s_cw), '%', 'theta_gyro vs theta_enc, CW, unsaturated'),
    ('Positive rotation', '', 'CCW' if np.corrcoef(th_enc, th_gyro)[0, 1] > 0 else 'CW', '-', 'sign check, §6'),
], columns=['Parameter', 'Symbol', 'Value', 'Unit', 'Method'])
table
""")

md(r"""
## §9 Short analysis (≤ 1 page)

Answer these in your own words, with numbers from the cells above:

1. **Which error source dominates after 10 s, 1 min and 3 min of driving?** Compare
   $b_0 t$ (linear), $\sigma\sqrt{t}$ (random walk) and the scale-factor term $s\cdot\theta$.
2. **How does your calibration work, how long does it need, and what does it leave behind?**
   Refer to the $b_0(T)$ curve and the residual heading error after 3 min.
3. **Where does $e(t)$ grow in the rotation run?** Steady growth while still = bias; jumps at
   every turn = scale factor; jumps only on the fastest turns = saturation; encoder error at
   hard acceleration = wheel slip. Use the tape-mark angle to say which sensor was closer.
4. **Does $s$ depend on speed?** Compare the per-amplitude fits and the CCW/CW asymmetry.

*Your text here.*
""")

md(r"""
## Checklist before submitting

- [ ] `lab9_gyro.py` (or `Lab9_gyro.qrs`) — the program that produced the log
- [ ] `lab9_gyro.csv` — the raw log, all phases, plus the tape-mark slip angle
- [ ] this notebook, executed, with the plots
- [ ] `gyro_sim()` and the overlay
- [ ] the parameter table with units and methods
- [ ] the short analysis
""")

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
        "colab": {"provenance": []},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}
OUT.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print("wrote", OUT)
