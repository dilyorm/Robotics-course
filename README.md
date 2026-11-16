# CS413 Mobile Robotics

**New Uzbekistan University · School of Computing · Fall 2026**

<p align="center">
  <img src="https://habrastorage.org/r/w1560/getpro/habr/upload_files/73e/1d1/7ca/73e1d17ca3d733989c1056ef01698a4e.png" alt="TRIK differential-drive robot" width="420">
</p>

A 16-week hands-on course on mobile robot control, localization and navigation, built on the differential-drive TRIK robot (TRIK Studio, JavaScript/Python) with an optional Raspberry Pi + ROS2 extension.

## Course goals

- **Sim-to-real gap** — understand why the same program behaves differently in the simulator and on the real robot, and treat that difference as information.
- **Experiment analysis** — log, plot and compare planned, simulated and real trajectories, and explain the errors.
- **Mobile robot navigation** — apply standard practices: PID, odometry, go-to-goal, sensor fusion, pure pursuit, mapping.
- **System identification** — build physical models of motors and sensors and fit their parameters from measured data.

## Methodology

Each week starts with a short lecture on one algorithm and its known failure modes. Students implement it in TRIK Studio and run it first in the simulator, then on the real robot, logging the same data in both. The logs are processed in Google Colab to compare model, simulation and reality. Each new week builds on the previous one, so every model error found becomes the motivation for the next topic.

## Schedule

| Week | Topic | Week | Topic |
|---|---|---|---|
| 1 | [TRIK Studio introduction](01_TRIK_studio_introduction) | 9 | [Gyroscope parameters](09_Gyroscope_parameters) |
| 2 | [PID controller](02_PID_controller) | 10 | [Odometry + gyroscope localization](10_Odometry+Gyroscope_localization) |
| 3 | [Line following](03_Line_following) | 11 | [Complementary filtering](11_Complementary_filtering) |
| 4 | [Line-following competition](04_Big_line) | 12 | [Kalman filtering](12_Kalman_filtering) |
| 5 | [Motor parameter identification](05_Motor_parameter_identification) | 13 | [Move-to-pose + obstacle avoidance](13_Move-to-pose+Obstacle_avoidance) |
| 6 | [Localization (odometry)](06_Localization) | 14 | [Pure pursuit control](14_Pure_pursuit_control) |
| 7 | [Go-to-goal](07_Go-to-goal) | 15 | [Mapping](15_Mapping) |
| 8 | [Midterm exam](08_Midterm_exam) | 16 | [Final exam](16_Final_exam) |

## Assignments

**Assignment 1 — Motor parameter identification (Week 5, 4 points).** Build a TRIK Studio visual program that drives both motors with step inputs in both directions and at least one complex signal (square, sawtooth, triangle, chirp or PRBS). In Google Colab, fit the first-order DC motor model to estimate the steady-state speed ω₀, time constant T_m and back-EMF constant k_e at each PWM level. Use the identified model to predict the response to the complex signal and report the fit. Quantify artifacts such as forward/backward asymmetry, dead zone, zero drift, backlash and battery sag. Starter notebook: [Motor_identification.ipynb](05_Motor_parameter_identification/Motor_identification.ipynb).

**Assignment 2 — Popular-science post (6 points).** Write a popular-science article on a current topic in mobile robotics, about 6 minutes of reading time. The post must be published on a moderated platform with editorial or peer review (e.g. Habr, Medium publications, dev.to). It should explain the topic for a general technical audience and cite its sources.

## Grading (100 points)

| Component | Points |
|---|---|
| Labs: ID ride 2, PID 2, Line following 2, Competition 2, Identification 3, Odometry 2, Go-to-goal 3, Gyro 2, Odom+Gyro 3, Complementary 3, Kalman 4, Move-to-pose 4, Pure pursuit 4, Mapping 4 | 40 |
| Assignment 1 | 4 |
| Assignment 2 | 6 |
| Midterm exam (week 8) | 20 |
| Final exam (week 16) | 30 |

Winner of the Week 4 line-following race gets +4 bonus points.

## Resources

- Lecture base: [Freiburg — Introduction to Mobile Robotics SS23](http://ais.informatik.uni-freiburg.de/teaching/ss23/robotics/), [ETH Zürich — Autonomous Mobile Robots](https://asl.ethz.ch/education/lectures/autonomous_mobile_robots/spring-2021.html)
- Corke, *Robotics, Vision and Control (Python)*; Thrun, Burgard, Fox, *Probabilistic Robotics*
- Susskind, Hrabovsky, *The Theoretical Minimum* — math and mechanics background
- Joseph, *Mastering ROS for Robotics Programming* — ROS2 extension

## Hardware and software

TRIK differential-drive robot programmed in TRIK Studio (no NumPy/SciPy on-robot — standard library only). For ROS2, a Raspberry Pi is connected via a USB–RJ45 adapter (ASIX chipset), with a TRIK script streaming data to ROS2. Offline analysis runs in Google Colab.
