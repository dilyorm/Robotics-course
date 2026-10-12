"""Copy the measurement files from the TRIK robot into ./motor_data (over SSH/SCP).

    python pull_data.py                     # robot at 192.168.77.1 (robot's own Wi-Fi AP)
    python pull_data.py --host 10.0.0.42    # robot on another network
    python pull_data.py --remote /home/root/trik/dilyorm_motor_data   # skip the search

Uses the ssh/scp that ship with Windows 10/11 (OpenSSH client). TRIK logs in as root;
press Enter if it asks for a password.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FOLDER = "dilyorm_motor_data"
SSH_OPTS = ["-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=8"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="192.168.77.1")
    ap.add_argument("--user", default="root")
    ap.add_argument("--remote", default=None, help="absolute folder on the robot (default: search for %s)" % FOLDER)
    ap.add_argument("--dest", default=str(HERE / "motor_data"))
    args = ap.parse_args()

    for tool in ("ssh", "scp"):
        if not shutil.which(tool):
            sys.exit("%s not found. Windows: Settings > Apps > Optional features > OpenSSH Client." % tool)

    target = "%s@%s" % (args.user, args.host)
    remote = args.remote
    if not remote:
        cmd = "find / -xdev -type d -name %s 2>/dev/null | head -5" % FOLDER
        res = subprocess.run(["ssh"] + SSH_OPTS + [target, cmd], capture_output=True, text=True)
        if res.returncode == 255:
            sys.exit("cannot connect to %s: %s\nIs the laptop on the robot's Wi-Fi?" % (target, res.stderr.strip()))
        found = [l.strip() for l in res.stdout.splitlines() if l.strip()]
        if not found:
            sys.exit("could not find %s on the robot (ssh said: %s). Did the program run? "
                     "Pass --remote with the path printed in run_info.txt." % (FOLDER, res.stderr.strip()))
        if len(found) > 1:
            print("several copies found, using the first:\n  " + "\n  ".join(found))
        remote = found[0]

    dest = Path(args.dest)
    if any(dest.glob("wheel_*.txt")):
        sys.exit("%s is not empty - move the old files away first (raw data must not be mixed or overwritten)." % dest)
    dest.mkdir(parents=True, exist_ok=True)

    print("copying %s:%s -> %s" % (target, remote, dest))
    r = subprocess.run(["scp"] + SSH_OPTS + ["-r", "%s:%s/." % (target, remote), str(dest)])
    if r.returncode:
        sys.exit("scp failed (%d)" % r.returncode)
    files = sorted(dest.glob("wheel_*_v_*.txt"))
    print("%d step files copied. Next: python analyze.py" % len(files))


if __name__ == "__main__":
    main()
