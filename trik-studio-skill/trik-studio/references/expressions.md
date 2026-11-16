# Block-diagram expression language

Used in `Function` (Body), `IfBlock`/`PreconditionalLoop` (Condition), `SwitchBlock` (Expression),
and in any numeric block property such as `Power`, `Delay`, `TachoLimit` — those accept formulas
too (`Power` = `pwm * k3`). It is a small Lua subset (TRIK's qrtext), not JavaScript or Python.

## Statements (Function block)

- Only **assignments and expressions**. Separate them with newlines or `;`.
  `x = 0`  `t0 = time()`  `buf = buf .. tt .. " " .. th .. "\n"`
- **No `if`, `while`, `for`, `function`, `local`** — the lexer knows the words but the parser
  rejects them. Branch with an `IfBlock`, loop with `PreconditionalLoop`/`Loop`.
  Branch-free tricks: `sgn(x)`, `abs`, `min`, `max`; e.g. `k = (sgn(lvl - 19.5) + 1) / 2` is 0 or 1.
- Variables are global to the whole diagram and created on first assignment.

## Operators

`+ - * / % ^` (power), `//` (integer divide), comparisons `== != ~= < <= > >=`,
`and or not`, string concatenation **`..`** (not `+`), `#a` = length.

## Values

Numbers (int/float), strings `"..."` / `'...'` with `\n` escapes, `true`/`false`, arrays
`a = {1, 0, 1}` indexed **from 0**: `a[0]`.

## Built-in functions

`time()` ms since program start · `sin cos atan asin acos atan2(y, x) exp ln sqrt abs` ·
`sgn` · `ceil floor` · `min(a, b) max(a, b)` · `random(n)` → 0..n-1 · `sensor("A1")` ·
`print(x)` · constant `pi`.

## Reserved (read-only) variables — TRIK V6.2 kit

| Name | Meaning |
|---|---|
| `encoder1`..`encoder4` | encoder angle in degrees on E1..E4 (E3/E4 are the drive wheels on most robots) |
| `sensorA1`..`sensorA6`, `sensorD1`, `sensorD2` | sensor readings (only if a sensor is configured on that port) |
| `gyroscope`, `accelerometer` | vectors |
| `buttonUp`, `buttonDown`, `buttonLeft`, `buttonRight`, `buttonEnter`, `buttonEsc`, `buttonPower` | 1 while pressed |
| `objectSensorX`, `objectSensorY`, `objectSensorSize`, `colorSensor`, `gamepadWheel`, `gamepadConnected` | camera / gamepad values |
| port names `M1`..`M4`, `E1`..`E4`, `A1`.., `S1`.. | port name strings — **do not use them as your own variable names** |

Assigning to a reserved name is an error ("variable is read-only"), a common surprise with
names like `S3`, `M3`, `E4`, `A1`.

## Things blocks cannot do → use a `TrikSystem` block with Code=true

The `TrikSystem` ("System Call") block with properties `Code="true"`, `Evaluate="false"` runs its
`Command` as **raw JavaScript** on the robot when the diagram is uploaded (TRIK compiles diagrams to
JS). Diagram variables are visible there. Use it for: reading the battery
(`vbat = brick.battery().readVoltage();`), writing to a computed file name
(`script.writeToFile("run_" + n + ".txt", buf);`), `script.system("mkdir -p data", true);`, `sync`.
The 2D simulator does not execute system/file calls, so test such diagrams on the robot.

`TrikWriteToFile` (Write To File) takes a **fixed** file name; `Text` is an expression
(`"laps " .. n`). It **appends** — pair it with `TrikRemoveFile` at program start.
