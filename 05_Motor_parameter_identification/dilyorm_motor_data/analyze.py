"""Lab 5 - batch motor identification: fit every step response, build the report.

    python analyze.py                      # reads ./motor_data, writes ./report.md + ./figures/
    python analyze.py --data some/dir      # other data folder (or a .zip of the files)
    python analyze.py --step-wheel 1 --step-pwm 60

Model (lecture):  T_m * dw/dt + w = U / k_e,   step from rest:
    theta(t) = w_ss * (t - T_m + T_m * exp(-t / T_m))

For every file: fit (w_ss, T_m) with scipy curve_fit. Per wheel and direction: fit the
linear part w_ss = (U - U0) / k_e, where U = PWM/100 * U_battery and U0 is the
dead-zone voltage. Accepts both file formats used in the course
("time_ms angle_deg" and the older "position_deg time_ms").
"""
import argparse
import math
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import optimize
from scipy.integrate import odeint

HERE = Path(__file__).resolve().parent

MOVE_DEG = 10.0       # final angle below this = wheel did not turn
DZ_FRAC = 0.03        # slower than 3 % of the wheel's top speed = stalled (dead zone)
NOMINAL_VBAT = 12.0   # used only if a file has no valid battery reading


# ---------------------------------------------------------------- loading
def iter_sources(path):
    path = Path(path)
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            for n in sorted(z.namelist()):
                if not n.endswith("/"):
                    yield Path(n).name, z.read(n).decode("utf-8", "replace")
    else:
        for p in sorted(path.rglob("*.txt")):
            yield p.name, p.read_text(encoding="utf-8", errors="replace")


def parse_run(name, text):
    m = re.match(r"wheel_(\d+)_v_(-?\d+)\.txt$", name)
    if not m:
        return None
    head, rows = {}, []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            k, _, v = line[1:].partition(":")
            head[k.strip()] = v.strip()
            continue
        rows.append([float(x) for x in re.split(r"[,\s]+", line)[:2]])
    a = np.array(rows, dtype=float)
    fmt = head.get("format", "position_deg time_ms")
    if fmt.split()[0].startswith("time"):
        t_ms, ang = a[:, 0], a[:, 1]
    else:
        ang, t_ms = a[:, 0], a[:, 1]
    vb = None
    for key in ("battery_voltage_loaded", "battery_voltage", "battery_voltage_mv"):
        try:
            v = float(head[key])
        except (KeyError, ValueError):
            continue
        if v > 1000:          # genuinely in mV
            v /= 1000.0
        if v > 0:
            vb = v
            break
    order = np.argsort(t_ms, kind="stable")
    return dict(
        wheel=int(head.get("wheel_id", m.group(1))),
        label=head.get("wheel_label", ""),
        pwm=int(head.get("pwm_percent", head.get("voltage_percent", m.group(2)))),
        vbat=vb,
        t=(t_ms[order] - t_ms[order][0]) / 1000.0,
        theta=np.radians(ang[order] - ang[order][0]),
        file=name,
    )


def load(path):
    runs, battery = [], {}
    for name, text in iter_sources(path):
        bm = re.match(r"wheel_(\d+)_battery\.txt$", name)
        if bm:
            nums = re.findall(r"[-+]?\d*\.?\d+", text.split(":", 1)[-1])
            if nums and float(nums[0]) > 0:
                v = float(nums[0])
                battery[int(bm.group(1))] = v / 1000.0 if v > 1000 else v
            continue
        r = parse_run(name, text)
        if r is not None and len(r["t"]) >= 5:
            runs.append(r)
    for r in runs:
        if r["vbat"] is None:
            r["vbat"] = battery.get(r["wheel"])
        r["vbat_assumed"] = r["vbat"] is None
        if r["vbat"] is None:
            r["vbat"] = NOMINAL_VBAT
        r["U"] = r["pwm"] / 100.0 * r["vbat"]
    return runs


# ---------------------------------------------------------------- fitting
def theta_model(t, w_ss, T_m):
    return w_ss * (t - T_m + T_m * np.exp(-t / T_m))


def fit_run(r):
    t, th = r["t"], r["theta"]
    dt = np.diff(t)
    r["n"] = len(t)
    r["dt_med_ms"] = float(np.median(dt) * 1000) if len(dt) else float("nan")
    r["dt_max_ms"] = float(dt.max() * 1000) if len(dt) else float("nan")
    r["moving"] = abs(math.degrees(th[-1])) >= MOVE_DEG

    tail = t >= 0.6 * t[-1]
    slope = np.polyfit(t[tail], th[tail], 1)[0] if tail.sum() >= 2 else th[-1] / t[-1]
    r["w_slope"] = float(slope)

    r["w_ss"], r["T_m"], r["rmse_deg"], r["T_m_ok"] = float(slope), float("nan"), float("nan"), False
    if not r["moving"]:
        r["w_ss"] = 0.0
        return
    try:
        (w, T), cov = optimize.curve_fit(theta_model, t, th, p0=[slope, 0.08],
                                         bounds=([-np.inf, 1e-3], [np.inf, 2.0]), maxfev=20000)
        res = th - theta_model(t, w, T)
        r["w_ss"], r["T_m"] = float(w), float(T)
        r["rmse_deg"] = float(np.degrees(np.sqrt(np.mean(res ** 2))))
        # T_m is only trustworthy if a few samples land inside the transient
        n_transient = int(np.sum(t < 3 * T))
        r["T_m_ok"] = n_transient >= 4 and T < 0.5 * t[-1]
        r["n_transient"] = n_transient
    except (RuntimeError, ValueError):
        pass


def fit_line(U, w):
    """w = (U - U0)/k_e  ->  returns k_e, U0 (x-intercept, signed like U)."""
    if len(U) < 2:
        return float("nan"), float("nan")
    s, c = np.polyfit(U, w, 1)
    return 1.0 / s, -c / s


def wheel_summary(runs, min_pwm):
    out = {}
    for wid in sorted({r["wheel"] for r in runs}):
        rs = sorted([r for r in runs if r["wheel"] == wid], key=lambda r: r["pwm"])
        # dead zone: wheel essentially stalled (slower than DZ_FRAC of its top speed)
        top = max(abs(r["w_slope"]) for r in rs)
        for r in rs:
            r["dead"] = (not r["moving"]) or abs(r["w_slope"]) < DZ_FRAC * top
        mov = [r for r in rs if not r["dead"]]
        # encoder direction relative to motor direction
        agree = sum(np.sign(r["w_ss"]) == np.sign(r["pwm"]) for r in mov)
        sign = 1 if agree >= len(mov) / 2 else -1
        S = dict(wheel=wid, label=rs[0]["label"], runs=rs, sign=sign)
        for d, sel in (("fwd", lambda r: r["pwm"] > 0), ("rev", lambda r: r["pwm"] < 0)):
            pts = [r for r in mov if sel(r) and abs(r["pwm"]) >= min_pwm]
            U = np.array([r["U"] for r in pts]); w = np.array([sign * r["w_ss"] for r in pts])
            k_e, U0 = fit_line(U, w)
            S["k_e_" + d], S["U0_" + d] = k_e, U0
            S["fitU_" + d] = (min(abs(U)), max(abs(U))) if len(U) else (0.0, 0.0)
            still = [r for r in rs if sel(r) and r["dead"]]
            S["dz_pwm_" + d] = max(abs(r["pwm"]) for r in still) if still else 0
            S["dz_U_" + d] = max(abs(r["U"]) for r in still) if still else 0.0
        Tm = [r["T_m"] for r in mov if r["T_m_ok"] and abs(r["pwm"]) >= min_pwm]
        S["T_m_med"] = float(np.median(Tm)) if Tm else float("nan")
        S["T_m_iqr"] = (float(np.percentile(Tm, 25)), float(np.percentile(Tm, 75))) if Tm else (float("nan"),) * 2
        S["k_e"] = float(np.nanmean([S["k_e_fwd"], S["k_e_rev"]]))
        S["dz_U"] = max(S["dz_U_fwd"], S["dz_U_rev"])
        S["vbat"] = float(np.median([r["vbat"] for r in rs]))
        S["vbat_assumed"] = any(r["vbat_assumed"] for r in rs)
        S["dt_med_ms"] = float(np.median([r["dt_med_ms"] for r in rs]))
        w100 = [sign * r["w_ss"] for r in rs if r["pwm"] == 100]
        S["w_100"] = w100[0] if w100 else float("nan")
        out[wid] = S
    return out


# ---------------------------------------------------------------- simulation
def model_params(S, U):
    d = "fwd" if U > 0 else "rev"
    return S["k_e_" + d], S["U0_" + d], S["dz_U_" + d]


def simulate(t, U, k_e, T_m, U0, dz_U):
    """Lecture model with the identified straight line: T_m*dw/dt + w = (U - U0)/k_e, zero inside the dead zone."""
    u_eff = 0.0 if abs(U) <= dz_U else U - U0

    def motor(state, _t):
        w, _th = state
        return [-w / T_m + u_eff / (T_m * k_e), w]

    return odeint(motor, [0.0, 0.0], t)[:, 1]


# ---------------------------------------------------------------- plots
COLORS = ["#2a6fdb", "#e0542e", "#1f9e6e", "#9b4dca", "#c49000", "#555555"]


def plot_omega_u(W, path, min_pwm):
    fig, ax = plt.subplots(figsize=(8, 5.5), dpi=120)
    lo = max(S["dz_U_rev"] for S in W.values()); hi = max(S["dz_U_fwd"] for S in W.values())
    if lo or hi:
        ax.axvspan(-lo, hi, color="0.85", zorder=0, label="measured dead zone (%.2f / %.2f V)" % (-lo, hi))
    for i, (wid, S) in enumerate(W.items()):
        c = COLORS[i % len(COLORS)]
        live = [r for r in S["runs"] if not r["dead"]]; dead = [r for r in S["runs"] if r["dead"]]
        ax.plot([r["U"] for r in live], [S["sign"] * r["w_ss"] for r in live], "o", ms=4, color=c,
                label="wheel %d %s" % (wid, S["label"]))
        ax.plot([r["U"] for r in dead], [S["sign"] * r["w_slope"] for r in dead], "x", ms=6, color=c)
        for d, sgn in (("fwd", 1), ("rev", -1)):
            k, U0 = S["k_e_" + d], S["U0_" + d]
            if math.isnan(k):
                continue
            a, b = S["fitU_" + d]
            uu = np.linspace(a, b, 20) * sgn
            ax.plot(uu, (uu - U0) / k, "-", color=c, lw=1.2, alpha=0.8,
                    label="  fit %s: k_e=%.3f V*s/rad, U0=%+.2f V" % (d, k, U0))
    ax.axhline(0, color="0.5", lw=0.6); ax.axvline(0, color="0.5", lw=0.6)
    ax.set_xlabel("U = PWM/100 * U_battery  [V]"); ax.set_ylabel("steady-state speed w_ss  [rad/s]")
    ax.set_title("w_ss vs U  (lines fitted on |PWM| >= %d %%, x = stalled)" % min_pwm)
    ax.legend(fontsize=7, loc="upper left"); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def plot_tm(W, path):
    fig, ax = plt.subplots(figsize=(8, 4), dpi=120)
    for i, (wid, S) in enumerate(W.items()):
        c = COLORS[i % len(COLORS)]
        ok = [r for r in S["runs"] if not r["dead"] and not math.isnan(r["T_m"])]
        ax.plot([r["pwm"] for r in ok if r["T_m_ok"]], [r["T_m"] * 1000 for r in ok if r["T_m_ok"]],
                "o-", ms=4, color=c, label="wheel %d %s" % (wid, S["label"]))
        bad = [r for r in ok if not r["T_m_ok"]]
        if bad:
            ax.plot([r["pwm"] for r in bad], [r["T_m"] * 1000 for r in bad], "x", color=c, ms=6)
    ax.set_xlabel("PWM [%]"); ax.set_ylabel("T_m [ms]"); ax.grid(alpha=0.3)
    ax.set_title("Time constant per level (x = unreliable: too few samples in transient)")
    ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(path); plt.close(fig)


def plot_step(r, S, path):
    t = r["t"]; tt = np.linspace(0, t[-1], 400)
    k_e, U0, dz = model_params(S, r["U"])
    sim = S["sign"] * simulate(tt, r["U"], k_e, S["T_m_med"], U0, dz)
    fig, ax = plt.subplots(figsize=(8, 5), dpi=120)
    ax.plot(t, r["theta"], ".", ms=3, color="#e0542e", label="measured (%d samples)" % r["n"])
    if not math.isnan(r["T_m"]):
        ax.plot(tt, theta_model(tt, r["w_ss"], r["T_m"]), "-", color="0.3", lw=1,
                label="fit of this run: w_ss=%.2f rad/s, T_m=%.0f ms" % (r["w_ss"], r["T_m"] * 1000))
    ax.plot(tt, sim, "--", color="#2a6fdb", lw=2,
            label="odeint, identified model: k_e=%.3f, T_m=%.0f ms, U0=%+.2f V" % (k_e, S["T_m_med"] * 1000, U0))
    ax.set_xlabel("t [s]"); ax.set_ylabel("theta [rad]"); ax.grid(alpha=0.3)
    ax.set_title("Step response, wheel %d, PWM %d %% (U = %.2f V)" % (r["wheel"], r["pwm"], r["U"]))
    ax.legend(fontsize=8)
    ins = ax.inset_axes([0.58, 0.08, 0.38, 0.32])
    m = t <= max(0.3, 6 * (r["T_m"] if not math.isnan(r["T_m"]) else 0.05))
    m2 = tt <= t[m][-1]
    ins.plot(t[m], r["theta"][m], ".", ms=3, color="#e0542e")
    ins.plot(tt[m2], sim[m2], "--", color="#2a6fdb")
    if not math.isnan(r["T_m"]):
        ins.plot(tt[m2], theta_model(tt[m2], r["w_ss"], r["T_m"]), "-", color="0.3", lw=1)
    ins.set_title("start (transient)", fontsize=7); ins.tick_params(labelsize=6); ins.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def plot_all_steps(W, path):
    n = len(W)
    fig, axes = plt.subplots(1, n, figsize=(5 * n, 4), dpi=110, squeeze=False)
    cmap = plt.get_cmap("coolwarm")
    for ax, (wid, S) in zip(axes[0], W.items()):
        for r in S["runs"]:
            ax.plot(r["t"], np.degrees(r["theta"]), lw=0.8, color=cmap((r["pwm"] + 100) / 200))
        ax.set_title("wheel %d %s: all levels" % (wid, S["label"])); ax.set_xlabel("t [s]")
        ax.set_ylabel("angle [deg]"); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


# ---------------------------------------------------------------- report
def f(x, p=3):
    return "-" if x is None or (isinstance(x, float) and math.isnan(x)) else ("%.*f" % (p, x))


def write_report(W, runs, args, out):
    fig = Path(args.figures)
    L = ["# Lab 5 - Motor parameter identification", ""]
    L += ["Generated by `analyze.py` from `%s` (%d runs, %d wheels)." % (Path(args.data).name, len(runs), len(W)), ""]
    if any(S["vbat_assumed"] for S in W.values()):
        L += ["> **Warning:** some files have no battery reading; U was computed with %.1f V." % NOMINAL_VBAT, ""]
    L += ["## Identified parameters", "",
          "| Wheel | U_bat [V] | k_e fwd | k_e rev | **k_e** [V*s/rad] | U0 fwd [V] | U0 rev [V] | stalled up to PWM fwd/rev | **T_m** median [ms] | T_m IQR [ms] | w_ss @100 % [rad/s] | encoder sign | median dt [ms] |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for wid, S in W.items():
        L.append("| %d %s | %s | %s | %s | **%s** | %s | %s | %d %% / %d %% | **%s** | %s-%s | %s | %s | %s |" % (
            wid, S["label"], f(S["vbat"], 2), f(S["k_e_fwd"]), f(S["k_e_rev"]), f(S["k_e"]),
            f(S["U0_fwd"], 2), f(S["U0_rev"], 2), S["dz_pwm_fwd"], S["dz_pwm_rev"],
            f(S["T_m_med"] * 1000, 0), f(S["T_m_iqr"][0] * 1000, 0), f(S["T_m_iqr"][1] * 1000, 0),
            f(S["w_100"], 2), "+" if S["sign"] > 0 else "reversed", f(S["dt_med_ms"], 1)))
    L += ["", "k_e and U0 come from a straight-line fit `w_ss = (U - U0)/k_e` on |PWM| >= %d %%, "
          "separately for forward and reverse (U0 is where that line crosses zero speed; it is not the dead zone). "
          "\"Stalled\" = slower than %d %% of the wheel's top speed. T_m is the median over the fitted levels, "
          "using only fits with at least 4 samples inside the transient." % (args.min_pwm, DZ_FRAC * 100), ""]

    L += ["## w_ss against voltage", "", "![w_ss vs U](%s/omega_vs_U.png)" % fig.name, ""]
    L += ["## Step response: measurement vs identified model", "",
          "![step](%s/step_response.png)" % fig.name, "",
          "Grey: two-parameter fit of this single run. Blue dashed: `odeint` simulation of "
          "`T_m*dw/dt + w = (U - U0)/k_e` with the wheel's identified k_e, U0 and median T_m.", ""]
    L += ["![T_m](%s/Tm_vs_pwm.png)" % fig.name, "", "![all](%s/all_steps.png)" % fig.name, ""]

    L += ["## Per-level results", ""]
    for wid, S in W.items():
        L += ["### Wheel %d %s" % (wid, S["label"]), "",
              "| PWM [%] | U [V] | w_ss [rad/s] | T_m [ms] | fit RMSE [deg] | samples | median dt [ms] | max dt [ms] | note |",
              "|---|---|---|---|---|---|---|---|---|"]
        for r in S["runs"]:
            note = "stalled" if r["dead"] else ("" if r["T_m_ok"] else "T_m unreliable")
            L.append("| %d | %s | %s | %s | %s | %d | %s | %s | %s |" % (
                r["pwm"], f(r["U"], 2), f(r["w_ss"], 2), f(r["T_m"] * 1000, 0), f(r["rmse_deg"], 1),
                r["n"], f(r["dt_med_ms"], 1), f(r["dt_max_ms"], 0), note))
        L.append("")

    # numbers for the discussion
    ids = list(W)
    L += ["## Discussion (draft - rewrite in your own words)", ""]
    pts = []
    stall = lambda p: ("stalls up to %d %%" % p) if p else "moves already at 5 %"
    dzs = "; ".join("wheel %d %s forward / %s reverse, line offset U0 = %+.2f / %+.2f V" % (
        w, stall(W[w]["dz_pwm_fwd"]), stall(W[w]["dz_pwm_rev"]), W[w]["U0_fwd"], W[w]["U0_rev"]) for w in ids)
    pts.append("The linear model fails at low voltage: %s. Just outside the dead zone the speed rises faster than "
               "the straight line, so one k_e cannot describe the whole range." % dzs)
    tm = "; ".join("wheel %d: T_m %s ms at low |PWM| vs %s ms at 100 %%" % (
        w, f(np.nanmax([r["T_m"] * 1000 for r in W[w]["runs"] if r["T_m_ok"] and abs(r["pwm"]) <= 40] or [np.nan]), 0),
        f(np.nanmean([r["T_m"] * 1000 for r in W[w]["runs"] if r["T_m_ok"] and abs(r["pwm"]) == 100] or [np.nan]), 0))
        for w in ids)
    pts.append("T_m is not constant either (%s): friction makes the motor look slower at low voltage." % tm)
    asym = ", ".join("wheel %d forward/reverse k_e differ by %.1f %%" % (
        w, 100 * abs(W[w]["k_e_fwd"] - W[w]["k_e_rev"]) / W[w]["k_e"]) for w in ids
        if not math.isnan(W[w]["k_e_fwd"]) and not math.isnan(W[w]["k_e_rev"]))
    if asym:
        pts.append("Directions are not symmetric: %s." % asym)
    if len(ids) >= 2:
        a, b = W[ids[0]], W[ids[1]]
        d = 100 * abs(a["k_e"] - b["k_e"]) / np.mean([a["k_e"], b["k_e"]])
        wa, wb = a["w_100"], b["w_100"]
        eps = (wb - wa) / ((wa + wb) / 2) if not (math.isnan(wa) or math.isnan(wb)) else float("nan")
        R = args.track / 2 * 2 / abs(eps) if eps and not math.isnan(eps) else float("inf")
        pts.append("Wheels %d and %d differ by %.1f %% in fitted k_e; at 100 %% PWM they reach %.2f vs %.2f rad/s. With equal PWM on "
                   "both sides the robot will not go straight: a %.1f %% speed mismatch with a %.3f m track turns it on "
                   "a circle of radius ~%.1f m (about %.0f deg of heading per metre)." % (
                       ids[0], ids[1], d, wa, wb, 100 * abs(eps), args.track, R,
                       math.degrees(1 / R) if R not in (0, float("inf")) else 0.0))
        pts.append("For odometry this means a model that assumes identical motors (or converts PWM to speed instead "
                   "of reading the encoders) accumulates heading error that grows with distance, and heading error "
                   "turns into position error; per-wheel k_e, U0 and T_m from this table should be used in Week 6.")
    L += ["- " + p for p in pts] + [""]
    out.write_text("\n".join(L), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=str(HERE / "motor_data"), help="folder (or .zip) with wheel_N_v_PWM.txt files")
    ap.add_argument("--out", default=str(HERE / "report.md"))
    ap.add_argument("--figures", default=None, help="figure folder (default: figures/ next to the report)")
    ap.add_argument("--min-pwm", type=int, default=20, help="only |PWM| >= this is used for k_e/T_m fits")
    ap.add_argument("--step-wheel", type=int, default=None)
    ap.add_argument("--step-pwm", type=int, default=50)
    ap.add_argument("--wheels", default=None, help="comma list of wheel ids to include, e.g. 1,2")
    ap.add_argument("--track", type=float, default=0.19, help="distance between drive wheels [m], for the drift estimate")
    args = ap.parse_args()

    out = Path(args.out).resolve()
    args.figures = str(Path(args.figures).resolve() if args.figures else out.parent / "figures")
    Path(args.figures).mkdir(parents=True, exist_ok=True)

    runs = load(args.data)
    if args.wheels:
        keep = {int(x) for x in args.wheels.split(",")}
        runs = [r for r in runs if r["wheel"] in keep]
    if not runs:
        sys.exit("no wheel_N_v_PWM.txt files found in %s" % args.data)
    for r in runs:
        fit_run(r)
    W = wheel_summary(runs, args.min_pwm)

    figs = Path(args.figures)
    plot_omega_u(W, figs / "omega_vs_U.png", args.min_pwm)
    plot_tm(W, figs / "Tm_vs_pwm.png")
    plot_all_steps(W, figs / "all_steps.png")
    sw = args.step_wheel if args.step_wheel in W else next(iter(W))
    cand = [r for r in W[sw]["runs"] if not r["dead"]]
    step = min(cand, key=lambda r: abs(r["pwm"] - args.step_pwm))
    plot_step(step, W[sw], figs / "step_response.png")
    write_report(W, runs, args, out)

    print("%-10s %8s %8s %8s %8s %8s %8s %8s" % ("wheel", "k_e", "k_e_fwd", "k_e_rev", "U0f[V]", "U0r[V]", "T_m[ms]", "dt[ms]"))
    for wid, S in W.items():
        print("%-10s %8s %8s %8s %8s %8s %8s %8s" % ("%d %s" % (wid, S["label"]), f(S["k_e"]), f(S["k_e_fwd"]),
              f(S["k_e_rev"]), f(S["U0_fwd"], 2), f(S["U0_rev"], 2), f(S["T_m_med"] * 1000, 0), f(S["dt_med_ms"], 1)))
    print("report:", out)


if __name__ == "__main__":
    main()
