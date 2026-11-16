# Lab 10 — Odometry and Gyroscope-Based Localization

## Lecture

**Topic:** Dead reckoning for a differential-drive robot. Covers encoder odometry, gyro-aided odometry, odometry error sources (systematic and non-systematic), and how heading error turns into position error.

**Variables** (same names as in the previous labs):

| Name | Meaning | Unit |
|---|---|---|
| `r`, `B` | wheel radius, wheel base (track width) — from Lab 5 | cm |
| `theta_l`, `theta_r` | left / right wheel angle from the encoders | rad |
| `path`, `prev_path` | distance travelled by the robot centre, now and at the previous step | cm |
| `course_odom` | robot course from the encoders | rad |
| `gyro_inc` | course increment from the gyro in one step | rad |
| `course` | robot course used for localization and control | rad |
| `x`, `y` | robot position | cm |
| `X_ref[i]`, `Y_ref[i]` | waypoint `i` of the ideal trajectory | cm |
| `distance`, `bearing` | distance and direction from the robot to waypoint `i` | cm, rad |
| `courseAngle` | heading error to waypoint `i`, steered to zero by the controller | rad |

**Key ideas**

- **Encoder odometry.** Both the path and the course come from the wheels:

  ```
  theta_l     = encoder E4 * pi / 180
  theta_r     = encoder E3 * pi / 180
  prev_path   = path
  path        = (theta_r + theta_l) * r / 2
  course_odom = (theta_r - theta_l) * r / B
  ```

- **Gyro-aided odometry.** The path still comes from the wheels, but the course comes from the gyro, using `b0` and `s` from Lab 9:

  ```
  gyro_inc = (gz - b0) / (1 + s) * dt          # converted to rad
  ```

- **Course used in each run.**

  ```
  Run A:   course = course_odom
  Run B:   course = course + gyro_inc
  ```

  Lab 11 combines both with a complementary filter: `course = 0.01 * course_odom + 0.99 * (course + gyro_inc)`.

- **Position update and controller inputs.** These are the same in both runs:

  ```
  x           = x + (path - prev_path) * cos(course)
  y           = y + (path - prev_path) * sin(course)
  distance    = sqrt((X_ref[i] - x)^2 + (Y_ref[i] - y)^2)
  bearing     = atan2(Y_ref[i] - y, X_ref[i] - x)
  courseAngle = bearing - course
  ```

- **Error sources.**
  - `course_odom` is hurt by a wrong `r` or `B`, unequal wheel diameters, and wheel slip during turns.
  - The gyro course is not affected by slip or `B`. It is hurt by bias `b0`, scale factor `s` and saturation `w_max`.
  - `path` comes from the encoders in both runs, so its errors are the same in both.
- **Why course matters most.** A course error `e` moves the robot sideways by about `l * e` after a straight segment of length `l`. A 2° error over 1 m is already 3.5 cm.
- **Known bugs in `trajectory_blocks.js`:**
  - *Sign:* `course_odom` must use `(theta_r - theta_l)`. Check it against the gyro sign you found in Lab 9 §6.
  - *Consistency:* use the same `course` for both the position update and `courseAngle`.

**Reading**

- Lecture slides: *16-311 Introduction to Robotics, Lecture 15 — Sensors (for State Estimation) 1*, G. A. Di Caro, CMU-Q (slides 15–19: odometry, INS, drift).
- J. Borenstein, H. R. Everett, L. Feng, *Sensors and Methods for Mobile Robot Positioning*, Univ. of Michigan, 1996. Ch. 5.1 covers systematic and non-systematic odometry errors; Ch. 2 covers gyros as heading sensors: <https://courses.cs.duke.edu/spring06/cps296.1/handouts/robot%20positioning%2096.pdf>
- J. Borenstein, L. Feng, *Measurement and Correction of Systematic Odometry Errors in Mobile Robots* (the UMBmark test): <https://cs.au.dk/~ocaprani/legolab/DigitalControl.dir/NXT/Lesson10.dir/paper58.pdf>
- Siegwart, Nourbakhsh, Scaramuzza, *Introduction to Autonomous Mobile Robots*, Ch. 5.2.4 — odometric position estimation and error propagation.
- Corke, *Robotics, Vision and Control*, Ch. 4 — wheeled mobile robot kinematics.

---

## Goal

Drive the robot along the trajectory of the **last two digits of your student ID** twice. The TRIK Studio program and controller are the same for both runs; only the `course` changes:

| Run | `course` used for localization and control |
|---|---|
| **A — odometry only** | `course = course_odom` |
| **B — odometry + gyro** | `course = course + gyro_inc` (Lab 9 parameters) |

Then compare the **course** and the **path** of every segment with the ideal trajectory. Which localization brings the robot closer to the ideal digits?

---

## Lab execution

### Step 1 — Ideal trajectory

- Write the waypoints of your two digits as `X_ref`, `Y_ref` in cm, using straight segments only.
- For each segment `i`, compute the **ideal course** and the **ideal path length**:

  ```
  course_ref[i] = atan2(Y_ref[i+1] - Y_ref[i], X_ref[i+1] - X_ref[i])
  path_ref[i]   = sqrt((X_ref[i+1] - X_ref[i])^2 + (Y_ref[i+1] - Y_ref[i])^2)
  ```

### Step 2 — Robot program (TRIK Studio)

**Controller.** Use the same controller in both runs. Recommended: at each waypoint, turn in place until `courseAngle` is close to 0. Then drive until `distance` is below the acceptance radius, holding `courseAngle` at 0 with a P-controller.

- *Turn-then-drive* gives one clean course and one clean path length per segment.
- The go-to-goal controller from Lab 7 is also allowed, but it cuts corners, and the segments are then harder to compare.
- Wrap `courseAngle` to [−π, π]. Otherwise the robot may turn the long way round.
- Keep the turn rate **below the gyro range** `w_max` from Lab 9. A saturated gyro loses course in run B.

**Localization.** A variable `MODE` selects the `course` formula for run A or run B. In run B, `gyro_inc` uses `dt` from the gyro timestamp.

- Do not use the built-in gyro calibration. Instead, keep the robot at rest for 10 s at the start and subtract `b0`: either the mean of those 10 s or your Lab 9 method.
- Subtracting `b0` and computing the pose for the controller are the only processing done on the robot.

**Logging.** In every control cycle (~10 ms), write one line to the log file:

`t, theta_l, theta_r, gz`

- `i` is the index of the current target waypoint.
- Log the raw sensors as well as the estimate. Both localization methods can then be recomputed offline from **both** runs.

### Step 3 — Runs

- Mark the start pose on the floor with tape, and start both runs from exactly this pose.
- Do run A, then run B. If a run fails (stall, collision), repeat it.

### Step 4 — Analysis in Colab

1. **Trajectories.** Plot `X_ref, Y_ref` and the logged `x, y` of runs A and B on one x–y figure.
2. **Offline recomputation.** Recompute both localization methods from both logs. This gives 4 paths.
   - Check that the on-robot `x, y, course` match your offline recomputation.
   - Look at run A recomputed with the gyro course, and run B recomputed with `course_odom`. Where do the two methods disagree?
3. **Course.** For every segment, compare `course_ref[i]` with the logged `course` (mean on the segment):

   ```
   d_course[i] = course[i] - course_ref[i]
   ```

   Also plot `course(t)` and `course_odom(t)` for both runs over `course_ref`, which is a staircase.
4. **Path.** For every segment, compare `path_ref[i]` with the logged `path` increment on the segment:

   ```
   d_path[i] = path[i] - path_ref[i]
   ```

   Also report the total path-length error in %.
5. **Error growth.** Plot `d_course[i]` and the distance from `x, y` to the ideal trajectory against the segment number. Does the error accumulate or stay bounded? After which turn does it jump?

---

## Deliverables

Submit to `CS413 - Robotics/Lab10/`:

1. **Robot program** (`.qrs`) with `MODE` for runs A and B.
2. **Logs** of run A and run B.
3. **Colab notebook** with the plots from Step 4.
4. **Comparison table** (one row per segment, plus a summary row):

| Seg. | `course_ref` (°) | `course` A (°) | `course` B (°) | `d_course` A / B (°) | `path_ref` (cm) | `path` A (cm) | `path` B (cm) | `d_path` A / B (cm) |
|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | | |
| … | | | | | | | | |
| **Summary** | | | | mean abs(`d_course`) | total | | | total, % |

   Also report: final position error A / B (cm) and final course error A / B (°) relative to the last waypoint.

5. **Short analysis** (≤ 1 page):
   - Which run is closer to the ideal trajectory in course, and which in path? Why are the path errors similar while the course errors are not?
   - Which error source dominated each run: slip, `B`, bias or scale factor? Back this up with the offline recomputation from Step 4.2.
   - How would you combine `course_odom` and `gyro_inc`? This leads into Lab 11, the complementary filter.
