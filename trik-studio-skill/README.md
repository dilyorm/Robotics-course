# trik-studio skill for Claude Code

Lets Claude read, explain, build and edit TRIK Studio `.qrs` projects, run them in the headless 2D
simulator, and upload/run programs on a real TRIK robot over Wi-Fi.

## Install

Needs: Claude Code (desktop app or CLI), Python 3.8+, TRIK Studio installed (for the simulator).

Copy the `trik-studio` folder to your skills folder:

- Windows: `C:\Users\<you>\.claude\skills\trik-studio\`
- macOS/Linux: `~/.claude/skills/trik-studio/`

(or unzip `trik-studio.skill` there — it is a zip of the same folder). Restart Claude Code.

If TRIK Studio is not in a usual place (`~/TRIKStudio`, `C:\TRIKStudio`, `~/Documents/...`), set
an environment variable `TRIK_STUDIO_DIR` to the folder containing `2D-model.exe`.

## Try

- "Explain what my lab3.qrs diagram does, block by block"
- "Change the loop in lab5.qrs to log both encoders, test it in the simulator"
- "Write a Python program for TRIK that drives a 50 cm square, put it in square.qrs and simulate it"
- "Upload square.qrs to my robot at 192.168.77.1 and run it" (laptop on the robot's Wi-Fi)
- "Pull all wheel_*.txt files from the robot"

## Scripts (usable without Claude too)

```
python trik-studio/scripts/qrs_tool.py --help
python trik-studio/scripts/sim.py --help
python trik-studio/scripts/trik_robot.py --help
```
