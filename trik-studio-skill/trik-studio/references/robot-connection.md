# Connecting to a real TRIK robot

## Network

- The TRIK controller runs its own **Wi-Fi access point** (SSID shown on the robot's screen / Wi-Fi
  menu). Join it from the laptop. The robot's IP is shown on its screen; the factory default is
  `192.168.77.1`, but robots in a class are often reconfigured (e.g. `192.168.50.254`).
  Pass `--ip` or set `TRIK_IP`.
- Alternatively robot and laptop can join the same router network (robot in client mode) — then use
  the IP the robot shows.
- While connected to the robot's AP the laptop usually has **no internet**. Plan installs first.

## What TRIK Studio's buttons do (so you can do it without the GUI)

| TRIK Studio | trik_robot.py |
|---|---|
| Upload program | `upload prog.qrs` (code, or diagram compiled to JS) |
| Upload and run | `start prog.qrs [--follow 30]` |
| Stop robot | `stop` |
| Robot console output | `--follow N` streams `print()` lines |

Protocol (TCP 8888, from trikRuntime `trikCommunicator/src/connection.cpp`): message =
`<utf8 byte length>:<payload>`; payloads `file:<name>:<contents>`, `run:<name>` (name ending in `.py`
runs as Python, else JS), `stop`, `direct:<cmd>`, `directScript:<js>`, `keepalive`, `configVersion`.
The robot answers `print: <text>` for program output. Port 9000 is telemetry (unused here).

## Files on the robot

- ssh/scp as `root`, **no password**: `ssh root@<ip>`.
- Programs and every relative path a program writes live in `/home/root/trik/scripts/`.
- `trik_robot.py ls`, `pull 'data/*.txt' ./data`, `push file`, `shell "cmd"`.
  scp needs an OpenSSH client (built into Windows 10+, macOS, Linux).
- Run `sync` before switching the robot off, or recent files may be empty/missing.
- ssh host-key checking is disabled in trik_robot.py because many robots share the same IP.

## Before running motors

Put the robot on a stand (wheels in the air) or on the floor with space, and tell the user it is
about to move. A program that ends without `powerOff()`/`brick.stop()` leaves motors running —
`trik_robot.py stop` (or the robot's power button) stops it.

## Common problems

| Symptom | Cause / fix |
|---|---|
| `cannot reach robot` | not on robot's Wi-Fi, wrong IP, robot still booting (~1 min), firewall/VPN |
| upload beeps but nothing runs | program crashed at start: run with `--follow 10` to see the error, or check the robot screen |
| one wheel doesn't turn | wrong port name, motor cable, or power below the dead zone (≈10–15 % on the floor); test each port alone with `exec "brick.motor('M3').setPower(50)"` |
| encoder counts the wrong way | motor/encoder polarity differs per robot; flip the sign in code, don't edit data |
| data files missing after power-off | no `sync` |
| robot keeps driving after the script | add `brick.stop()` at the end; `trik_robot.py stop` |
| `ConnectionAbortedError` during `--follow` | Wi-Fi hiccup (ping 50–400 ms is common on a busy class AP). The run on the robot may be cut short. For runs longer than ~20 s, `start` **without** `--follow`, wait locally, then check the log (`shell "wc -l f.txt; tail -1 f.txt"`) and rerun if it is short |
| a classmate's log overwrote yours | the scripts folder is shared: give every log file a unique name (initials / student digits) |

## Reading the battery voltage

```
trik_robot.py shell "rm -f /tmp/bat.txt"
trik_robot.py exec "script.writeToFile('/tmp/bat.txt', ''+brick.battery().readVoltage()); script.quit();"
trik_robot.py shell "cat /tmp/bat.txt"
```
`writeToFile` appends, hence the `rm`. Read it before and after experiments that need volts (motor
identification). A 3-cell pack reads ≈ 12.6 V full; ~11.9 V still drives fine.
