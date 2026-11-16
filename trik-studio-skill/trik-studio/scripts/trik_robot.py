#!/usr/bin/env python3
"""Talk to a real TRIK robot over Wi-Fi: upload/run/stop programs, copy files, run shell commands.

Connect your computer to the robot's Wi-Fi access point first (or the same network).
Robot IP: --ip, else $TRIK_IP, else 192.168.77.1 (TRIK default; shown on the robot's screen).

    python trik_robot.py status                     # is the robot reachable?
    python trik_robot.py start prog.py --follow 30  # upload + run, show robot print() output for 30 s
    python trik_robot.py start prog.qrs             # embedded code, or the diagram compiled to JS
    python trik_robot.py upload prog.js [--name x.js]
    python trik_robot.py run x.js
    python trik_robot.py stop
    python trik_robot.py exec "brick.motor('M3').setPower(0);"   # run a JS snippet
    python trik_robot.py ls [dir]                   # (ssh) default dir = robot scripts folder
    python trik_robot.py pull 'data/*.txt' ./local  # (scp) relative paths = scripts folder
    python trik_robot.py push local.txt [remote]
    python trik_robot.py shell "cat /proc/loadavg"

Protocol (trikRuntime trikCommunicator, TCP port 8888): every message is "<utf8 byte length>:<payload>".
Payloads: "file:<name>:<contents>" (save into the scripts folder, robot beeps), "run:<name>" (.py runs
as Python, otherwise JS), "stop", "directScript:<js>", "keepalive", "configVersion". The robot sends
back "print: <text>" for every print() of the running program.
ssh/scp log in as root with no password; host-key checking is off because classroom robots share IPs.
"""
import argparse
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORT = 8888
SCRIPTS_DIR = "/home/root/trik/scripts"

def _null_file():
    # Git-for-Windows (MSYS) ssh treats "nul" as a real file in the cwd; it wants /dev/null.
    ssh = shutil.which("ssh") or ""
    if os.name == "nt" and "system32" not in ssh.lower():
        return "/dev/null"
    return os.devnull


SSH_OPTS = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=" + _null_file(),
            "-o", "ConnectTimeout=5", "-o", "LogLevel=ERROR"]


def ip_of(a):
    return a.ip or os.environ.get("TRIK_IP") or "192.168.77.1"


class Robot:
    def __init__(self, ip, timeout=5):
        self.ip = ip
        try:
            self.sock = socket.create_connection((ip, PORT), timeout=timeout)
        except OSError as e:
            sys.exit("cannot reach robot at %s:%d (%s). Joined the robot's Wi-Fi? Right IP (see robot screen)?"
                     % (ip, PORT, e))
        self.buf = b""

    def send(self, payload):
        data = payload.encode("utf-8")
        self.sock.sendall(str(len(data)).encode() + b":" + data)

    def recv(self, timeout):
        """Yield decoded messages until timeout seconds pass with nothing new."""
        self.sock.settimeout(timeout)
        while True:
            while b":" in self.buf:
                n, rest = self.buf.split(b":", 1)
                if not n.isdigit() or len(rest) < int(n):
                    break
                msg, self.buf = rest[:int(n)], rest[int(n):]
                yield msg.decode("utf-8", "replace")
            try:
                chunk = self.sock.recv(65536)
            except socket.timeout:
                return
            if not chunk:
                return
            self.buf += chunk

    def follow(self, seconds):
        end = time.time() + seconds
        last_ka = 0
        while time.time() < end:
            if time.time() - last_ka > 3:
                self.send("keepalive")
                last_ka = time.time()
            for m in self.recv(0.5):
                if m.startswith("print: "):
                    m = m[len("print: "):]
                sys.stdout.write(m if m.endswith("\n") else m + "\n")
                sys.stdout.flush()

    def close(self):
        time.sleep(0.2)  # let the robot read everything before we hang up
        self.sock.close()


def program_from(path, diagram=False):
    """(robot file name, code) for a .py/.js file or a .qrs project."""
    p = Path(path)
    if p.suffix.lower() != ".qrs":
        return p.name, p.read_text(encoding="utf-8")
    sys.path.insert(0, str(HERE))
    import qrs_tool
    proj = qrs_tool.Project(p)
    code = None if diagram else proj.meta.get("activeCode")
    if code and len(proj.to_spec()["blocks"]) > 1:
        print("NOTE: %s has both embedded code and a block diagram - uploading the CODE "
              "(use --diagram for the blocks)" % p.name)
    if code:
        ext = proj.meta.get("activeCodeLanguageExtension", "js")
        return p.stem + "." + ext, code
    # diagram: compile with TRIK Studio's own generator, like its "Upload and run" button does
    out = Path(tempfile.mkdtemp(prefix="trik_gen_")) / (p.stem + ".js")
    subprocess.run([sys.executable, str(HERE / "sim.py"), "gen", str(p), "--lang", "javascript", "-o", str(out)],
                   check=True)
    return out.name, out.read_text(encoding="utf-8")


def safe_name(name):
    return name.replace(":", "_").replace(" ", "_")


def cmd_status(a):
    r = Robot(ip_of(a))
    r.send("configVersion")
    got = list(r.recv(2))
    r.close()
    print("robot %s:%d reachable%s" % (r.ip, PORT, (" - " + "; ".join(got)) if got else ""))


def cmd_upload(a, run=False):
    name, code = program_from(a.file, a.diagram)
    name = safe_name(a.name or name)
    r = Robot(ip_of(a))
    r.send("file:%s:%s" % (name, code))
    print("uploaded %s (%d bytes) to %s/%s" % (name, len(code.encode()), SCRIPTS_DIR, name))
    if run:
        time.sleep(0.3)
        r.send("run:" + name)
        print("running", name)
        if a.follow:
            print("--- robot output (%gs) ---" % a.follow)
            r.follow(a.follow)
    r.close()


def cmd_run(a):
    r = Robot(ip_of(a))
    r.send("run:" + a.name)
    print("running", a.name)
    if a.follow:
        r.follow(a.follow)
    r.close()


def cmd_stop(a):
    r = Robot(ip_of(a))
    r.send("stop")
    r.close()
    print("stop sent")


def cmd_exec(a):
    r = Robot(ip_of(a))
    r.send("directScript:" + a.code)
    if a.follow:
        r.follow(a.follow)
    r.close()


def remote(path):
    return path if path.startswith("/") else SCRIPTS_DIR + "/" + path


def ssh(a, command):
    return subprocess.call(["ssh"] + SSH_OPTS + ["root@" + ip_of(a), command])


def cmd_ls(a):
    sys.exit(ssh(a, "ls -la %s" % remote(a.dir or "")))


def cmd_shell(a):
    sys.exit(ssh(a, a.command))


def cmd_pull(a):
    dest = a.local or "."
    sys.exit(subprocess.call(["scp", "-r"] + SSH_OPTS + ["root@%s:%s" % (ip_of(a), remote(a.remote)), dest]))


def cmd_push(a):
    target = remote(a.remote or Path(a.local).name)
    rc = subprocess.call(["scp", "-r"] + SSH_OPTS + [a.local, "root@%s:%s" % (ip_of(a), target)])
    if rc == 0:
        ssh(a, "sync")
    sys.exit(rc)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ip", help="robot IP (default $TRIK_IP or 192.168.77.1)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(f=cmd_status)
    for nm, run in (("upload", False), ("start", True)):
        s = sub.add_parser(nm)
        s.add_argument("file", help=".py, .js or .qrs")
        s.add_argument("--name", help="file name on the robot")
        s.add_argument("--diagram", action="store_true", help=".qrs: upload the block diagram even if code is embedded")
        s.add_argument("--follow", type=float, default=0, help="seconds to stream the robot's print() output")
        s.set_defaults(f=lambda a, run=run: cmd_upload(a, run))
    s = sub.add_parser("run"); s.add_argument("name"); s.add_argument("--follow", type=float, default=0)
    s.set_defaults(f=cmd_run)
    sub.add_parser("stop").set_defaults(f=cmd_stop)
    s = sub.add_parser("exec"); s.add_argument("code"); s.add_argument("--follow", type=float, default=0)
    s.set_defaults(f=cmd_exec)
    s = sub.add_parser("ls"); s.add_argument("dir", nargs="?"); s.set_defaults(f=cmd_ls)
    s = sub.add_parser("shell"); s.add_argument("command"); s.set_defaults(f=cmd_shell)
    s = sub.add_parser("pull"); s.add_argument("remote"); s.add_argument("local", nargs="?")
    s.set_defaults(f=cmd_pull)
    s = sub.add_parser("push"); s.add_argument("local"); s.add_argument("remote", nargs="?")
    s.set_defaults(f=cmd_push)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
