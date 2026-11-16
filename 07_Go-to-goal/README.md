## 1. Lecture

### From "where am I?" to "get me there"

In Week 6 the robot learned to estimate its pose `(x, y, course)` from odometry. This week it uses that estimate to **drive to a goal point** `(X_ref[i], Y_ref[i])`. Chain several goals together and the robot can follow any shape you can describe with coordinates, including your student ID digits.

The controller is only as good as the pose estimate it is fed. Every odometry error from Week 6 shows up here as a missed waypoint.

### Go-to-goal controller

At every control step the robot computes where the current waypoint `i` is relative to itself:

| Quantity | Formula |
|---|---|
| Distance to waypoint | `distance = √((X_ref[i] − x)² + (Y_ref[i] − y)²)` |
| Bearing to waypoint | `bearing = atan2(Y_ref[i] − y, X_ref[i] − x)` |
| Course angle (heading error) | `courseAngle = wrap(bearing − course)` into `(−π, π]` |
| Linear velocity | `v = min(K_v · distance, v_max)` |
| Angular velocity | `ω = K_θ · courseAngle` |
| Wheel speeds | `v_R = v + ω · B / 2`, `v_L = v − ω · B / 2` |

When `distance < ε` (the acceptance radius), the robot switches to the next waypoint, `i = i + 1`.

The pose `(x, y, course)` comes from the Week 6 odometry, using `theta_l`, `theta_r`, `path`, `r` and `B`.

**Always wrap `courseAngle`.** Without `wrap()`, a waypoint slightly to the robot's right can make it spin almost a full circle the wrong way.

### Design choices that shape the trajectory

- **`K_θ` too low.** The robot swings wide arcs and overshoots corners.
- **`K_θ` too high.** The robot oscillates around the line to the waypoint.
- **Constant `v` instead of `K_v · distance`.** The robot arrives fast, cannot turn in time, and cuts corners.
- **Large `ε`.** The robot switches to the next waypoint early, so sharp corners become rounded.
- **Turn-then-drive vs. drive-while-turning.** Stopping to rotate in place first gives sharper digits but slower runs.

### Reading

- Corke, Peter. *Robotics, Vision and Control (Python), 3rd ed.* Ch. 4 — Mobile Robot Vehicles, section "Moving to a Point".
- Egerstedt, Magnus. *Control of Mobile Robots* (Georgia Tech, Coursera / YouTube): go-to-goal behaviour lectures.
- Freiburg SS23 and ETH AMR slides on motion control (links in the Week 1 README).

---

## 2. Practical task — Lab 7

### Goal

Describe **the last two digits of your student ID** as a list of waypoints `X_ref`, `Y_ref`. Drive them with the go-to-goal controller, first in the TRIK Studio simulator and then on the real robot. In Google Colab, compare both recorded trajectories with the **ideal trajectory** using two quantities:

- **`distance`** — how far the robot is from the ideal segment it should be on, in cm.
- **`courseAngle`** — how far the robot's course is from the ideal segment's course, in degrees.

> In the robot program, `distance` and `courseAngle` refer to the **current waypoint**. In the analysis they refer to the **ideal segment** between waypoints `i − 1` and `i`.

Example: ID ending in `17`, waypoints in cm:

```
digit 1: (0,0) → (0,40)
gap:     (0,40) → (20,40)
digit 7: (20,40) → (45,40) → (25,0)

X_ref = [0, 0, 20, 45, 25]
Y_ref = [0, 40, 40, 40, 0]
```

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

Name the files `odometry_data_sim.txt` and `odometry_data_real.txt`. Run the **same program** with the **same gains** in both cases. The robot only logs; the trajectory is reconstructed offline in Colab.

### Colab analysis

**Step 1 — Reconstruct the trajectory.** Use your measured `r` and `B`. Start from the first waypoint, `x = X_ref[0]`, `y = Y_ref[0]`, with `course_0` equal to the robot's initial course. Then, for every logged sample `k`:

```
path[k]   = (theta_r[k] + theta_l[k]) · r / 2
course[k] = course_0 + (theta_r[k] − theta_l[k]) · r / B
x[k]      = x[k−1] + (path[k] − path[k−1]) · cos(course[k])
y[k]      = y[k−1] + (path[k] − path[k−1]) · sin(course[k])
```

Do this for both logs. The simulator log gives the model trajectory; the real log gives the robot's odometry.

**Step 2 — Ideal trajectory.** Segment `i` goes from waypoint `i − 1` to waypoint `i`. Its ideal course is:

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
3. **Waypoint miss.** For each waypoint, the smallest distance between the reconstructed trajectory and that waypoint.
4. A summary for each run:
   - max |`distance`| and RMS `distance`
   - mean |`courseAngle`|
   - the final error to the last waypoint
   - the run time

> - `courseAngle` peaks at every corner while the robot is turning toward the next segment. This is expected. Judge the course error on the straight parts.
> - The real-robot `distance` and `courseAngle` come from the robot's own odometry. They show how well the **controller** worked, not where the robot **actually** went.
> - If `loadtxt` fails, open the file and check for a header line, trailing commas, or `;` instead of `,`.

### Deliverables

Create a repo `CS413-Robotics/Lab7/<content>`:

1. **`go_to_goal_sim.qrs`** and **`go_to_goal_real.qrs`**: the programs with your waypoint list `X_ref`, `Y_ref`, the gains `K_v` and `K_θ`, and the acceptance radius `ε`.
2. **`odometry_data_sim.txt`** and **`odometry_data_real.txt`**: the raw logs.
3. **Colab notebook (`.ipynb`)** with the trajectory reconstruction, the trajectory plot, the `distance` and `courseAngle` plots, the waypoint-miss table and the summary for both runs.
4. **Measured end point.** Measure the real robot's final position with a tape measure. Compare it with the last waypoint and with the last point of the reconstructed real trajectory.
5. **3–6 sentences** answering two questions:
   - On which segments do `distance` and `courseAngle` grow? Which corners were cut or overshot, and which gain or `ε` caused it?
   - Is the remaining real-vs-model gap a **control** problem or a **localization** problem?
