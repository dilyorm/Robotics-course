#!/usr/bin/env python3
"""Run a TRIK Studio project in the 2D simulator headlessly and summarize what the robot did.

    python sim.py run prog.qrs                        # diagram, or embedded code if the qrs has some
    python sim.py run prog.qrs --code my.py           # run my.py (or .js) inside prog.qrs's world
    python sim.py run prog.qrs --mode diagram --timeout 30 --speed 10
    python sim.py gen prog.qrs --lang python [-o out.py]  # diagram -> Python/JS (TRIK's generator)
    python sim.py where                               # show which TRIK Studio install is used

TRIK Studio is found via $TRIK_STUDIO_DIR, then common install folders.
Notes (tested on TRIK Studio 2025.4):
  * 2D-model's --script-path is ignored; code only runs when embedded in the qrs (metaInfo
    activeCode). --code does that embedding on a temporary copy for you.
  * Diagram mode: Write To File blocks write into the work dir.
    Script mode: the simulator DISABLES script.writeToFile / removeFile / system, and print()
    output is not captured. Use brick.display().addLabel(...) for debug output - this script
    prints every text shown on the robot display (it is recorded in the trajectory).
  * Script-mode trajectories have timestamp 0; time is estimated as samples x 10 ms.
  * "Could not find platform independent libraries <prefix>" on stderr is harmless.
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import qrs_tool  # noqa: E402

PX_PER_CM = 16 / 5.6  # TRIK 2D model scale: 16 px wheel = 5.6 cm


def find_trik():
    exe = "2D-model.exe" if os.name == "nt" else "2D-model"
    cands = []
    if os.environ.get("TRIK_STUDIO_DIR"):
        cands.append(Path(os.environ["TRIK_STUDIO_DIR"]))
    home = Path.home()
    cands += [home / "TRIKStudio", home / "Documents" / "TRIKStudio", home / "Documents" / "trickstudio",
              home / "trikStudio", Path("C:/TRIKStudio"), Path("C:/Program Files/TRIKStudio"),
              Path("C:/Program Files (x86)/TRIKStudio"), Path("/opt/TRIKStudio"), Path("/opt/trik-studio"),
              home / "TRIKStudio" / "bin", Path("/Applications/TRIK Studio.app/Contents/MacOS")]
    for c in cands:
        for p in (c / exe, c / "bin" / exe):
            if p.exists():
                return p
    found = shutil.which(exe)
    if found:
        return Path(found)
    # last resort: shallow search of home
    for p in list(home.glob("*/" + exe)) + list(home.glob("*/*/" + exe)):
        return p
    sys.exit("TRIK Studio's %s not found. Set TRIK_STUDIO_DIR to the TRIK Studio install folder." % exe)


def run_2d(exe, args, cwd, timeout):
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    t0 = time.time()
    try:
        p = subprocess.run([str(exe)] + args, cwd=cwd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout, env=env)
        return p.returncode, p.stdout, p.stderr, time.time() - t0, False
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = e.stderr.decode("utf-8", "replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
        return None, out, err, time.time() - t0, True


def load_json_list(path):
    try:
        txt = Path(path).read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return []
    if not txt:
        return []
    try:
        return json.loads(txt)
    except json.JSONDecodeError:  # killed mid-write: close the array
        try:
            return json.loads(txt.rstrip(", \n") + "\n]")
        except json.JSONDecodeError:
            return []


def axle(p):
    """Trajectory x,y is the top-left of the robot's 50x50 px box; it rotates about the box centre.
    The TRIK 2D wheels sit at local (10,3) and (10,47), so the axle midpoint (the point that turns in
    place) is 15 px behind the centre. Returns axle (x, y) in cm, heading in deg."""
    th = math.radians(p["rotation"])
    x = p["x"] + 25 - 15 * math.cos(th)
    y = p["y"] + 25 - 15 * math.sin(th)
    return x / PX_PER_CM, y / PX_PER_CM, p["rotation"]


def summarize_traj(traj):
    pts = [p for p in traj if "x" in p and "y" in p]
    if not pts:
        return None
    ax = [axle(p) for p in pts]
    dist = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(ax, ax[1:]))
    turn = sum(((b[2] - a[2] + 180) % 360) - 180 for a, b in zip(ax, ax[1:]))
    a, b = ax[0], ax[-1]
    t_ms = pts[-1]["timestamp"] - pts[0]["timestamp"]
    return dict(start=a, end=b, path=dist, net=math.hypot(b[0] - a[0], b[1] - a[1]), turn_deg=turn,
                t_ms=t_ms, timed=t_ms > 0, n=len(pts), pts=pts, ax=ax)


def t_of(s, i):
    """ms of trajectory sample i (script mode has no timestamps: 10 ms per sample)."""
    return s["pts"][i]["timestamp"] if s["timed"] else 10 * i


def cmd_run(a):
    exe = find_trik()
    src = Path(a.qrs).resolve()
    work = Path(a.workdir).resolve() if a.workdir else Path(tempfile.mkdtemp(prefix="trik_sim_"))
    work.mkdir(parents=True, exist_ok=True)
    qrs = work / ("_sim_" + src.name)
    shutil.copy(src, qrs)
    proj = qrs_tool.Project(qrs)
    mode = a.mode
    if a.code:
        code = Path(a.code).read_text(encoding="utf-8")
        lang = "py" if a.code.endswith(".py") else "js"
        qrs_tool.write_project(qrs, qrs, meta={"activeCode": code, "activeCodeLanguageExtension": lang},
                               keep_diagram=True)
        mode = "script"
    elif mode == "auto":
        mode = "script" if proj.meta.get("activeCode") else "diagram"
        if mode == "script" and len(proj.to_spec()["blocks"]) > 1:
            print("NOTE: project has both embedded code and a block diagram - running the CODE. "
                  "Use --mode diagram to run the blocks.")
    before = {p.name for p in work.iterdir()}
    args = ["-b", "--platform", "offscreen", "-m", mode, "-c", "-t", "traj.json", "-r", "report.json", "--close"]
    if a.speed:
        args += ["-s", str(a.speed)]
    if a.input:
        args += ["-i", str(Path(a.input).resolve())]
    args.append(qrs.name)
    rc, out, err, dt, timed_out = run_2d(exe, args, work, a.timeout)

    print("mode: %s | exit: %s | wall %.1fs%s | workdir: %s" % (
        mode, "timeout" if timed_out else rc, dt, " (killed after --timeout)" if timed_out else "", work))
    report = load_json_list(work / "report.json")
    msgs = [m for m in report if "world model has version" not in m.get("message", "")]
    for m in msgs:
        print("  [%s] %s" % (m.get("level"), m.get("message")))
    noise = ("Could not find platform independent libraries", "world model has version")
    lines = [l for l in (out + "\n" + err).splitlines() if l.strip() and not any(n in l for n in noise)]
    if lines:
        print("console/stderr:")
        for l in lines[: a.max_lines]:
            print("  " + l)
        if len(lines) > a.max_lines:
            print("  ... %d more lines" % (len(lines) - a.max_lines))
    traj = load_json_list(work / "traj.json")
    s = summarize_traj(traj)
    if s:
        sx, sy, sr = s["start"]
        ex, ey, er = s["end"]
        if s["timed"]:
            print("robot: %.2fs simulated, %d samples" % (s["t_ms"] / 1000, s["n"]))
        else:  # script mode logs no timestamps; one sample per 10 ms tick
            print("robot: ~%.2fs simulated (%d samples x 10 ms)" % (s["n"] / 100, s["n"]))
        print("  pose = wheel-axle midpoint, cm; y points DOWN; heading 0 = +x, + = clockwise on screen")
        print("  start (%.1f, %.1f) cm, heading %.1f deg" % (sx, sy, sr % 360))
        print("  end   (%.1f, %.1f) cm, heading %.1f deg" % (ex, ey, er % 360))
        print("  moved %.1f cm net, path %.1f cm, turned %+.1f deg total" % (s["net"], s["path"], s["turn_deg"]))
        if a.csv:
            with open(a.csv, "w") as f:
                f.write("t_ms,x_cm,y_cm,heading_deg\n")
                for i, (x, y, r) in enumerate(s["ax"]):
                    f.write("%d,%.3f,%.3f,%.3f\n" % (t_of(s, i), x, y, r))
            print("  trajectory csv (axle midpoint):", a.csv)
    else:
        print("robot: no trajectory recorded (program did not start? check messages above)")
    # display text, with the robot pose at the moment it appeared: print a label at each step of
    # your program (e.g. "side 2") to get a per-segment breakdown
    shown, last, k = [], None, -1
    for e in traj:
        if "x" in e:
            k += 1
        elif e.get("device") == "display" and e.get("property") == "objects":
            texts = " | ".join(o.get("text", "") for o in e.get("value") or [] if o.get("type") == "text")
            if texts and texts != last:
                shown.append((max(k, 0), texts))
            last = texts or last
    if shown:
        print("robot display text (pose when it appeared):")
        prev = s["ax"][0] if s else None
        for i, t in shown[-a.max_lines:]:
            if s:
                x, y, r = s["ax"][min(i, s["n"] - 1)]
                d = math.hypot(x - prev[0], y - prev[1])
                print("  t=%5.2fs (%6.1f, %6.1f) cm %6.1f deg  [+%.1f cm since previous]  %s"
                      % (t_of(s, min(i, s["n"] - 1)) / 1000, x, y, r % 360, d, t))
                prev = (x, y, r)
            else:
                print("  " + t)
    new = sorted(p.name for p in work.iterdir() if p.name not in before
                 and p.name not in ("traj.json", "report.json") and not p.name.startswith("lastCode.")
                 and not (a.csv and p.resolve() == Path(a.csv).resolve()))
    if new:
        print("files written by the program (in workdir):", ", ".join(new))
    errors = [m for m in report if m.get("level") == "error"]
    sys.exit(1 if errors else 0)


def cmd_gen(a):
    exe = find_trik()
    work = Path(tempfile.mkdtemp(prefix="trik_gen_"))
    tmp_out = work / ("generated.py" if a.lang == "python" else "generated.js")
    qrs = work / Path(a.qrs).name
    shutil.copy(a.qrs, qrs)
    args = ["-b", "--platform", "offscreen", "--only-generate", "--generate-mode", a.lang,
            "--generate-path", str(tmp_out), qrs.name]
    rc, o, e, _dt, _to = run_2d(exe, args, work, 60)
    if not tmp_out.exists():
        sys.exit("generation failed (exit %s):\n%s%s" % (rc, o, e))
    if a.output:
        shutil.copy(tmp_out, a.output)
        print("wrote", Path(a.output).resolve())
    else:
        sys.stdout.write(tmp_out.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("run")
    s.add_argument("qrs")
    s.add_argument("--code", help=".py/.js file to run in this project's world (embedded into a temp copy)")
    s.add_argument("--mode", choices=["auto", "diagram", "script"], default="auto")
    s.add_argument("--timeout", type=float, default=60, help="wall-clock seconds before killing (default 60)")
    s.add_argument("--speed", type=int, help="simulation speed factor (5..20; higher = faster)")
    s.add_argument("--input", help="inputs file for the program (-i)")
    s.add_argument("--workdir", help="where to run; program output files land here (default: temp dir)")
    s.add_argument("--csv", help="save trajectory as CSV")
    s.add_argument("--max-lines", type=int, default=60)
    s.set_defaults(f=cmd_run)
    s = sub.add_parser("gen")
    s.add_argument("qrs")
    s.add_argument("--lang", choices=["python", "javascript"], default="javascript")
    s.add_argument("-o", "--output", help="save to file (default: print)")
    s.set_defaults(f=cmd_gen)
    s = sub.add_parser("where")
    s.set_defaults(f=lambda a: print(find_trik()))
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
