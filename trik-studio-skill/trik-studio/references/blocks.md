# TRIK Studio block catalog

Generated from TRIK Studio's metamodel (`robotsMetamodel.xml`, `trikMetamodel.xml`).
`Type` is the XML type used in `.qrs` paths (`tree/logical/RobotsMetamodel/RobotsDiagram/<Type>/{uuid}`).
Properties are stored as `<QString key="<prop>" value="..."/>` (bools as `true`/`false`).

## Common — Algorithms

| Type | Label | Properties (default) | What it does |
|---|---|---|---|
| `InitialNode` | Initial Node | — | The entry point of the program execution. Each diagram should have only one such block, it must not have incomming links and it must have only one outgoing… |
| `FinalNode` | Final Node | — | The final node of the program. If the program consists of some parallel execution lines the reachment of this block terminates the corresponding execution… |
| `VariableInit` | Variable Initialization | `variable` = `x`; `value` = `0` | Assigns a given value to a given variable. |
| `IfBlock` | Condition | `Condition` = `x > 0` | Separates program execution in correspondece with the given condition. The 'Condition' parameter value must be some boolean expression that will determine… |
| `FiBlock` | End if | — | Unites control flow from different condition branches. |
| `PreconditionalLoop` | Pre-conditional Loop | `Condition` = `x > 0` | This block executes a sequence of blocks while condition in 'Condition' is true. This block must have two outgoing links. One of them must be marked with… |
| `Loop` | Loop | `Iterations` = `10` | This block executes a sequence of blocks for a given number of times. The number of repetitions is specified by the 'Iterations' parameter. This block must… |
| `SwitchBlock` | Switch | `Expression` = `x` | Selects the program execution branch in correspondence with some expression value. The value of the expression written in 'Expression' property is compared… |
| `Function` | Expression | `Body` | Evaluates a value of the given expression. Also new variables can be defined in this block. See the 'Expressions Syntax' chapter in help for more… |
| `Subprogram` | Subprogram | — | Subprogram call. Subprograms are used for splitting repetitive program parts into a separate diagram and then calling it from main diagram or other… |
| `Fork` | Fork | — | Separates program execution into a number of threads that will be executed concurrently from the programmers`s point of view. For example in such way signal… |
| `Join` | Join | — | Joins a number of threads into one. 'Guard' property of the single outgoing link must contain an identifier of one of threads being joined. The specified… |
| `KillThread` | Kill Thread | `Thread` = `main` | Terminates execution of a specified thread. |
| `Randomizer` | Random Initialization | `Variable` = `x`; `LowerBound` = `0`; `UpperBound` = `10` | Sets a variable value to a random value inside given interval. |
| `CommentBlock` | Comment | `Comment` = `Enter some text here...` | This block can hold text notes that are ignored by generators and interpreters. Use it for improving the diagram readability. |

## Common — Actions

| Type | Label | Properties (default) | What it does |
|---|---|---|---|
| `SendMessageThreads` | Send Message To Thread | `Thread`; `Message` | Sends a message to a specified thread. |
| `GetButtonCode` | Get Button Code | `Variable` = `x`; `Wait` = `true` | Assigns a given variable a value of pressed button. If no button is pressed at the moment and 'Wait' property is false when variable is set to -1. |

## Common — Wait

| Type | Label | Properties (default) | What it does |
|---|---|---|---|
| `Timer` | Timer | `Delay` = `1000` | Waits for a given time in milliseconds. |
| `ReceiveMessageThreads` | Receive Message From Thread | `Variable`; `Synchronized` = `true` | Receive a message sent to a thread from which this block is called. |
| `Input` | User Input | `variable` = `x`; `default`; `prompt` | Reads a value into variable from an input dialog. |

## Common — Drawing

| Type | Label | Properties (default) | What it does |
|---|---|---|---|
| `PrintText` | Print Text | `XCoordinateText` = `1`; `YCoordinateText` = `1`; `PrintText` = `Enter some text here`; `Evaluate` = `false`; `Redraw` = `true` | Prints a given line in the specified coordinates on the robot`s screen. The value of 'Text' property is interpreted as a plain text unless 'Evaluate'… |
| `ClearScreen` | Clear Screen | `Redraw` = `true` | Clears everything drawn on the robot`s screen. |
| `MarkerDown` | Marker Down | `Color` = `blue` | Moves the marker of the 2D model robot down to the floor: the robot will draw its trace on the floor after that. If the marker of another color is already… |
| `MarkerUp` | Marker Up | — | Lifts the marker of the 2D model robot up: the robot stops drawing its trace on the floor after that. |

## TRIK — Actions

| Type | Label | Properties (default) | What it does |
|---|---|---|---|
| `TrikPlayTone` | Play Sound | `FileName` = `media/beep.wav` | Plays on the robot a sound file (.wav or .mp3) previously uploaded to it. |
| `TrikPlayToneHz` | Play Tone | `Frequency` = `1000`; `Duration` = `1000` | Plays on the robot a sound with the given frequency and duration. |
| `TrikV6EnginesForward` | Motors Forward | `Power` = `100`; `Ports` = `M3, M4` | Enables motors on the given ports with the given power. Ports are specified in accordance with TRIK controller notations (for example M1, E2) and divided by… |
| `TrikV6EnginesBackward` | Motors Backward | `Power` = `100`; `Ports` = `M3, M4` | Enables motors on the given ports in reverse mode with the given power. Ports are specified in accordance with TRIK controller notations (for example M1,… |
| `TrikV6EnginesStop` | Stop Motors | `Mode` = `float`; `Ports` = `M1, M2, M3, M4` | Disables motors on the given ports. |
| `TrikV6ClearEncoder` | Clear Encoder | `Ports` = `B1, B2, B3, B4` | Nullifies tacho limit of the motors on the given ports. |
| `TrikV62ClearEncoder` | Clear Encoder | `Ports` = `E1, E2, E3, E4` | Nullifies tacho limit of the motors on the given ports. |
| `TrikSay` | Say | `Text` = `Hi!`; `Evaluate` = `false` | Synthesizes the given phrase and plays it on the robot. If 'Evaluate' property is set to true then the value of 'Text' property is interpreted as a formula,… |
| `TrikLed` | Led | `Color` = `red` | Sets the color of the LED on the robot`s front panel. |
| `TrikAngularServo` | Angular Servo | `Ports` = `E1`; `Power` = `0` | Manages angular servomotor. Sets up rotation angle on the given port in degrees. Values from 0 to 90 are correspond to a clockwise rotation and values from… |
| `TrikV62AngularServo` | Angular Servo | `Ports` = `S1`; `Power` = `0` | Manages angular servomotor. Sets up rotation angle on the given port in degrees. Values from 0 to 90 are correspond to a clockwise rotation and values from… |
| `TrikSystem` | System Call | `Command` = `echo 123`; `Code` = `false`; `Evaluate` = `false` | Invokes bash script-style command on the robot. If 'Evaluate' property is set to true then the value of 'Command' property is interpreted as a formula,… |
| `TrikInitCamera` | Initialize Videocamera | `Mode` = `line`; `DrawStream` = `true`; `VideoPort` = `video2` | Enables line or object or color detector by videocamera and draws videostream on the robot`s screen. |
| `TrikStopCamera` | Stop Videocamera | `Mode` = `line`; `StopCameraMode` = `StopAll`; `VideoPort` = `video2` | Stops line or object or color detector by videocamera. |
| `TrikDetect` | Detect by Videocamera | `Mode` = `line`; `VideoPort` = `video2` | Initializes videocamera line or object detector with the color of the object in the middle of the camera`s sight. |
| `TrikDetectorToVariable` | Line Detector into Variable | `Variable` = `err`; `VideoPort` = `video2` | Stores videocamera line detector`s value into a given variable. |
| `TrikInitVideoStreaming` | Enable Video Streaming | `Grayscaled` = `false`; `Quality` = `30`; `VideoPort` = `video2`; `Detached` = `false` | Enables video stream on robot. Video then can be watched on TRIK gamepad or in browser using URL http://ROBOT.IP.ADDRESS:8080/?action=stream |
| `TrikStopVideoStreaming` | Disable Video Streaming | `VideoPort` = `video2` | Disables video stream on robot. |
| `TrikSendMessage` | Send message | `Message`; `HullNumber` | Sends message to another robot. |
| `TrikWriteToFile` | Write To File | `File` = `output.txt`; `Text` | Writes a given message to a file. File path may be absolute or relative to a directory containing TRIK Studio executable. |
| `TrikRemoveFile` | Remove File | `File` = `output.txt` | Removes a file. File path may be absolute or relative to a directory containing TRIK Studio executable. |
| `TrikCalibrateGyroscope` | Calibrate gyroscope | — | Sets gyroscope's angle to zero in current position. |
| `TrikReadLidar` | Read Lidar To Variable | `variable` = `x` | Assigns a value from lidar to a given variable. |
| `TrikJoinNetwork` | Join Network | `Address` = `192.168.77.1`; `IPPort` = `8889`; `HullNumber` = `1` | Sets the hull number and connects with a peer by a (host)name or an IP-address. Target IP-port can be changed too if required. |

## TRIK — Wait

| Type | Label | Properties (default) | What it does |
|---|---|---|---|
| `TrikWaitForGyroscope` | Wait for Gyroscope | `Degrees` = `0`; `Sign` = `greater` | Waits till the value returned by the gyroscope on the given port will be greater or less than the given in the 'Degrees' parameter value. |
| `TrikWaitForTouchSensor` | Wait for Touch Sensor | `Port` = `A1` | Waits till the touch sensor is pressed. The only parameter is a sensor`s port number (1, 2, 3 or 4). |
| `TrikWaitForLight` | Wait for Light | `Port` = `A1`; `Percents` = `0`; `Sign` = `greater` | Waits till the value returned by the light sensor on the given port will be greater or less than the given in the 'Percents' parameter value (0 to 100). |
| `TrikWaitForSonarDistance` | Wait for Ultrasonic Distance | `Port` = `D1`; `Distance` = `0`; `Sign` = `greater` | Waits till the value returned by the ultrasonic sensor on the given port will be greater or less than the given in the 'Distance' parameter value (the… |
| `TrikWaitForIRDistance` | Wait for Infrared Distance | `Port` = `A1`; `Distance` = `0`; `Sign` = `greater` | Waits till the value returned by the infrared sensor on the given port will be greater or less than the given in the 'Distance' parameter value. By default… |
| `TrikWaitForEncoder` | Wait for Encoder | `Port` = `B3`; `TachoLimit`; `Sign` = `greater` | Waits till the tacho limit of the motor on the given port will reach the value of the 'Tacho Limit' parameter. |
| `TrikV62WaitForEncoder` | Wait for Encoder | `Port` = `E3`; `TachoLimit`; `Sign` = `greater` | Waits till the tacho limit of the motor on the given port will reach the value of the 'Tacho Limit' parameter. |
| `TrikWaitForButton` | Wait for Button | `Button` = `Up` | Waits for press of a button on a brick. |
| `TrikWaitForMessage` | Wait for Message | `Variable`; `Synchronized` = `true` | Stores a message from another robot into a given variable. When no incoming messages are present at the moment, a robot will wait for incoming message if… |
| `TrikWaitGamepadButton` | Wait Gamepad Button | `Button` = `1` | Waits for Android gamepad 'magic button' press. Buttons are identified by numbers from 1 to 5 (from left to right) |
| `TrikWaitPadPress` | Wait Pad Press | `Pad` = `1` | Waits for Android gamepad pad press (left pad has number 1, right pad - number 2). |
| `TrikWaitGamepadWheel` | Wait for Gamepad Wheel | `Angle` = `0`; `Sign` = `greater` | Waits till the value returned by gamepad wheel be greater or less than the given in the 'Angle' parameter value. Angle is measured from -100 (max left) to… |
| `TrikWaitGamepadDisconnect` | Wait for Gamepad Disconnect | — | Waits until Android gamepad is disconnected. |
| `TrikWaitGamepadConnect` | Wait for Gamepad Connect | — | Waits until Android gamepad is connected. |

## TRIK — Drawing

| Type | Label | Properties (default) | What it does |
|---|---|---|---|
| `TrikPrintText` | Print Text | `XCoordinateText` = `1`; `YCoordinateText` = `1`; `PrintText` = `Enter some text here`; `Evaluate` = `false`; `Redraw` = `true`; `FontSize` = `20` | Prints a given line in the specified coordinates and font size on the robot`s screen. The value of 'Text' property is interpreted as a plain text unless… |
| `TrikSetPainterColor` | Painter Color | `Color` = `black` | Sets the painter color. |
| `TrikSetPainterWidth` | Painter Width | `Width` = `1` | Sets the painter width. |
| `TrikDrawPixel` | Draw Pixel | `XCoordinatePix` = `5`; `YCoordinatePix` = `5`; `Redraw` = `true` | Draws one pixel in the specified coordinates on the robot screen. |
| `TrikDrawLine` | Draw Line | `X1CoordinateLine` = `0`; `Y1CoordinateLine` = `0`; `X2CoordinateLine` = `10`; `Y2CoordinateLine` = `10`; `Redraw` = `true` | Draws a segment on the robot screen. The parameters specify the ends of the segment. |
| `TrikDrawRect` | Draw Rectangle | `XCoordinateRect` = `0`; `YCoordinateRect` = `0`; `WidthRect` = `5`; `HeightRect` = `5`; `Filled` = `false`; `Redraw` = `true` | Draws a rectangle on the robot screen. The parameters specify the coordinates of top-left corner, the width and the height of the rectangle. |
| `TrikDrawEllipse` | Draw Ellipse | `XCoordinateEllipse` = `0`; `YCoordinateEllipse` = `0`; `WidthEllipse` = `5`; `HeightEllipse` = `5`; `Filled` = `false`; `Redraw` = `true` | Draws the ellipse defined by the rectangle beginning at (x, y) with the given width and height. |
| `TrikDrawArc` | Draw Arc | `XCoordinateArc` = `0`; `YCoordinateArc` = `0`; `WidthArc` = `5`; `HeightArc` = `5`; `StartAngle` = `20`; `SpanAngle` = `20`; `Redraw` = `true` | Draws the arc defined by the rectangle beginning at (x, y) with the specified width and height, and the given startAngle and spanAngle. |
| `TrikSmile` | Smile | — | Draws a smile on the robot`s screen :) |
| `TrikSadSmile` | Sad Smile | — | Draws a sad smile on the robot`s screen :( |
| `TrikSetBackground` | Background Color | `Color` = `white`; `Redraw` = `true` | Sets the background color of the current picture on the robot`s screen. |
