## 1. Lecture

### What localization means for a wheeled robot

Localization answers one question: **where is the robot right now?** That means its position `(x, y)` and its course `course` in a fixed world frame.

This week we use the simplest answer available on every wheeled robot: **odometry (dead reckoning)**. The robot never sees the world. It only counts how far each wheel has turned and integrates those increments into a pose. Everything later in the course exists to fix what goes wrong here: gyroscope fusion (Week 10), complementary filtering (Week 11) and Kalman filtering (Week 12).

### Differential-drive odometry

For a robot with wheel radius `r` and wheel base `B` (distance between the wheels):

| Quantity | Formula |
|---|---|
| Wheel angles | `theta_l = encoder E4 · π / 180`, `theta_r = encoder E3 · π / 180` (radians) |
| Path of the robot centre | `path = (theta_r + theta_l) · r / 2` |
| Course | `course = (theta_r − theta_l) · r / B` |
| Position update (each step) | `x ← x + (path − prev_path) · cos(course)`, `y ← y + (path − prev_path) · sin(course)` |
| Distance and bearing to waypoint `i` | `distance = √((X_ref[i] − x)² + (Y_ref[i] − y)²)`, `bearing = atan2(Y_ref[i] − y, X_ref[i] − x)` |
| Course angle to waypoint `i` | `courseAngle = bearing − course` |

TRIK encoders report **degrees**, so convert them before using the formulas. Measure `r` and `B` on your own robot; do not trust nominal values.

### Why the model and the robot disagree

Odometry is the robot's **belief**, not the truth. The errors are systematic and they accumulate:

- **Wheel slip.** The encoder turns but the robot does not move, or moves less.
- **Wrong `r` or `B`.** A 2 % error in `B` turns every 90° corner into an 88° or 92° corner, and the error grows with every turn.
- **Unequal wheels or motors.** The robot drifts even when it is commanded to go straight (recall your Week 5 motor parameters).
- **Course error dominates.** A small error in `course` early on becomes a large error in `(x, y)` later.

The simulator has none of these effects, which is exactly why comparing the two is useful.

### Reading

- Thrun, Burgard, Fox. *Probabilistic Robotics.* Ch. 5 — Robot Motion (odometry motion model).
- Siegwart, Nourbakhsh, Scaramuzza. *Introduction to Autonomous Mobile Robots.* Ch. 5 — Mobile Robot Localization.
- Freiburg SS23 and ETH AMR slides on motion models and localization (links in the Week 1 README).
- ETH / Duckietown, differential-drive robot modeling: <https://ethz.ch/content/dam/ethz/special-interest/mavt/dynamic-systems-n-control/idsc-dam/Lectures/amod/AMOD_2020/20201019-02%20-%20ETHZ%20-%20Modeling.pdf>

---

## 2. Practical task — Lab 6

### Goal

Drive the trajectory of **the last two digits of your student ID** (as in Lab 1), first in the simulator and then on the real robot, and log the robot's odometry in both. In Google Colab, compare each recorded trajectory with the **ideal trajectory** using two quantities:

- **`distance`** — how far the robot is from the ideal segment it should be on, in m.
- **`courseAngle`** — how far the robot's course is from the ideal segment's course, in degrees.

> In the robot program, `distance` and `courseAngle` refer to the **current waypoint**. In the analysis they refer to the **ideal segment** between waypoints `i − 1` and `i`.

### Log format

Both runs write a plain text file, one line per sample, **no header**, comma-separated:

```
theta_l,theta_r,time
0.000,0.000,0
0.052,0.049,50
...
```

- `theta_l`, `theta_r` — left and right wheel angles in **rad** (`encoder · π / 180`)
- `time` — milliseconds since program start

Name the files `odometry_data_sim.txt` (simulator) and `odometry_data_real.txt` (real robot). Run the **same program** in both cases. The robot only logs; the trajectory is reconstructed offline in Colab.

### Colab analysis

**Step 1 — Reconstruct the trajectory.** Use your measured `r` and `B`. Start from the start pose of the ideal trajectory: `x = X_ref[0]`, `y = Y_ref[0]`, and `course` = the course of the first segment. Then, for every logged sample `k`:

```
path[k]   = (theta_r[k] + theta_l[k]) · r / 2
course[k] = course_0 + (theta_r[k] − theta_l[k]) · r / B
x[k]      = x[k−1] + (path[k] − path[k−1]) · cos(course[k])
y[k]      = y[k−1] + (path[k] − path[k−1]) · sin(course[k])
```

Do this for both logs. The simulator log gives the model trajectory; the real log gives the robot's odometry.

**Step 2 — Ideal trajectory.** Write the waypoints `X_ref`, `Y_ref` (in m) that your program drives to. Segment `i` goes from waypoint `i − 1` to waypoint `i`, and its ideal course is:

```
course_ref[i] = atan2(Y_ref[i] − Y_ref[i−1], X_ref[i] − X_ref[i−1])
```

**Step 3 — Assign samples to segments.** For each sample, find the ideal segment `i` it belongs to: the nearest segment to `(x[k], y[k])`. Move through the segments in order. Allow only the current segment or the next one, so that the samples do not jump between segments that cross or touch.

**Step 4 — `distance` and `courseAngle`.** For every sample on segment `i`:

```
distance    = −(x − X_ref[i−1]) · sin(course_ref[i]) + (y − Y_ref[i−1]) · cos(course_ref[i])
courseAngle = course_ref[i] − course                        (wrapped to [−180°, 180°])
```

- `distance` is signed: it is positive when the robot is to the left of the ideal segment and negative when it is to the right.
- `distance = 0` and `courseAngle = 0` everywhere means the robot followed the ideal trajectory exactly.

**Step 5 — Plots and summary**, for both runs:

1. The ideal trajectory, the simulator trajectory and the real trajectory on one x–y plot.
2. `distance(t)` and `courseAngle(t)`, with the simulator and the real robot on the same axes.
3. A summary for each run: max |`distance`|, RMS `distance`, mean |`courseAngle`|, and the final error to the last waypoint.

> `courseAngle` peaks at every corner while the robot is turning toward the next segment. This is expected. Judge the course error on the straight parts.
> If `loadtxt` fails, open the file and check for a header line, trailing commas, or `;` instead of `,`.

### Deliverables

Create a repo `CS413-Robotics/Lab6/<content>`:

1. **`trajectory_sim.qrs`** and **`trajectory_real.qrs`** — the programs used, with odometry logging.
2. **`odometry_data_sim.txt`** and **`odometry_data_real.txt`** — the raw logs.
3. **Colab notebook (`.ipynb`)** with the trajectory reconstruction, the trajectory plot, the `distance` and `courseAngle` plots, and the printed summary for both runs.
4. **Measured end point.** After the real run, measure the robot's actual final position with a tape measure. Compare it with the last point of the reconstructed real trajectory and with the last ideal waypoint.
5. **3–6 sentences:**
   - On which segments do `distance` and `courseAngle` grow, in the simulator and on the real robot?
   - Which error source from the lecture explains it?
   - Does the robot *know* it is wrong? Compare the logged final position with the tape measurement.
