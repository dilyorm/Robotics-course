# TRIK robot scripting API (Python and JavaScript)

Same objects in both languages; Python adds `self.`-free globals via `from TRIK import *`
(done automatically). Globals: `brick`, `script`, `mailbox`, plus `KeysEnum`
(`Left=105 Up=103 Down=108 Enter=28 Right=106 Power=116 Esc=1`).
Source of truth: trikRuntime `trikControl/include/trikControl/*Interface.h` and
`trikScriptRunner/src/scriptExecutionControl.h`.

## Motors, encoders, sensors

```python
m = brick.motor("M3")
m.setPower(60)          # -100..100 (% PWM). Sign = direction.
m.power()               # last set power
m.powerOff()            # coast
m.brake(500)            # active brake for ms

e = brick.encoder("E3") # V6.2 boards: encoder ports E1..E4 (old V6: B1..B4)
e.read()                # degrees (int), signed, accumulates
e.reset()
e.readRawData()

brick.sensor("A1").read()        # analog ports A1..A6, digital D1, D2 (configure the sensor type in TRIK Studio)
brick.gyroscope().read()         # vector; .calibrate(ms), .isCalibrated()
brick.accelerometer().read()     # vector
brick.battery().readVoltage()    # volts (float)
brick.keys().wasPressed(KeysEnum.Enter); brick.keys().isPressed(code); brick.keys().buttonCode(wait=True)
brick.lidar().read()             # also lineSensor(port), objectSensor(port), colorSensor(port) for the camera
brick.stop()                     # stop all motors and devices
```

## Display, sound, LED

```python
d = brick.display()
d.clear(); d.addLabel("text", x, y); d.redraw()          # x,y in px from top-left
d.setPainterColor("red"); d.drawLine(x1, y1, x2, y2); d.drawRect(x, y, w, h); d.setBackground("white")
brick.playTone(1000, 300)        # Hz, ms
brick.say("hello")
brick.led().red(); brick.led().green(); brick.led().orange(); brick.led().off()
```

## script object

```python
script.wait(ms)                  # sleep; use this instead of time.sleep (the 2D simulator only advances
                                 # its clock through script.wait / timers)
script.time()                    # ms timestamp
script.random(a, b)
script.writeToFile(path, text)   # APPENDS. Relative paths are inside the robot's scripts folder.
script.removeFile(path)          # call before the first writeToFile of a run
script.readAll(path)             # list of lines
script.system("sync", True)      # shell command; True = wait for it to finish
script.timer(ms)                 # repeating timer object (connect to its timeout signal)
script.run() / script.quit()     # event-driven mode / end program
```

## Patterns that matter on the real robot

- **Log to memory, write once.** File I/O inside a fast sampling loop stretches the period.
  Build a list/string during the run, write after the motors stop.
- **Flush to disk.** The robot's SD card caches writes; pulling the battery loses them.
  After writing: `script.system("sync", True)` (Python can also `f.flush(); os.fsync(f.fileno())`
  when using `open()` directly).
- **Python `open()` works** on the robot (real CPython 3 via PythonQt); paths are relative to the
  scripts folder `/home/root/trik/scripts`.
- **Record real timestamps** (`script.time()`), never assume the loop period.
- **Wait after `encoder.reset()`** (~100–500 ms) before trusting reads.
- The program keeps running motors after it ends unless you call `powerOff()`/`brick.stop()`.

## What TRIK Studio generates

`sim.py gen prog.qrs --lang python|javascript` shows the exact code a diagram turns into.
Generated Python wraps everything in `class Program` with `execMain()`; diagram variables become
`self.x`. Generated code is a good template for hand-written programs.
