# The .qrs project format

Read this when `qrs_tool.py` cannot do what you need and you must touch the XML yourself,
or when debugging a project that TRIK Studio refuses to open / crashes on.

## Contents
- Zip layout
- Ids
- Block (node) XML
- Link (ControlFlow) XML
- Guards and ports
- metaInfo.xml
- worldModel.xml
- Rules that crash TRIK Studio if broken

## Zip layout

A `.qrs` is a plain zip:

```
metaInfo.xml                         version, kit, embedded code (activeCode)
worldModel.xml                       2D simulator world + robot (wheels, sensors)
blobs.xml                            usually <root/>
tree/logical/ROOT_ID/ROOT_ID/ROOT_ID/ROOT_ID      root: lists EVERY logical id as children
tree/logical/RobotsMetamodel/RobotsDiagram/<Type>/{uuid}     one file per block/link (semantics)
tree/graphical/RobotsMetamodel/RobotsDiagram/<Type>/{uuid}   one file per block/link (position on canvas)
```

Every block and link exists twice: a **logical** object (properties that matter for execution) and a
**graphical** object (position, ports) that points at it via `logicalId`. The diagram itself is a
`RobotsDiagramNode` (one logical + one graphical). The logical diagram node holds
`devicesConfiguration` (which sensor is on which port) and a copy of the world model.

## Ids

`qrm:/RobotsMetamodel/RobotsDiagram/<Type>/{uuid4}`. The file path is the id without `qrm:/`.
The `<Type>` part must be the block type (see `blocks.md`).

## Block XML

Logical:
```xml
<object parent="qrm:/ROOT_ID/ROOT_ID/ROOT_ID/ROOT_ID" id="qrm:/RobotsMetamodel/RobotsDiagram/Timer/{...}">
  <children/>
  <properties>
    <QString key="Delay" value="1000"/>              <!-- every block property is a QString -->
    <qReal::Id key="from" value="qrm:/ROOT_ID/ROOT_ID/ROOT_ID/ROOT_ID"/>
    <incomingExplosions type="qReal::IdList"/>
    <int key="linkShape" value="0"/>
    <links type="qReal::IdList">                      <!-- logical ids of links touching this block -->
      <object id="qrm:/RobotsMetamodel/RobotsDiagram/ControlFlow/{...}"/>
    </links>
    <QString key="name" value="Timer"/>
    <qReal::Id key="outgoingExplosion" value="qrm:/"/>
    <qReal::Id key="to" value="qrm:/ROOT_ID/ROOT_ID/ROOT_ID/ROOT_ID"/>
  </properties>
</object>
```

Graphical: same shape, plus `logicalId="..."` on `<object>`, `parent` = the graphical
RobotsDiagramNode id, `<QPointF key="position" value="x, y"/>`,
`<QPolygon key="configuration" value="0, 0 : 50, 0 : 50, 50 : 0, 50 : "/>` (50x50 block),
and `links` listing the *graphical* link ids.

Text values are XML-escaped: `"` → `&quot;`, newline → `&#xa;`, tab → `&#x9;`, `<` → `&lt;`, `&` → `&amp;`.
TRIK writes attributes in varying order (`key` before or after `value`) and leaves `>` unescaped.

## Link XML

Logical ControlFlow: `<QString key="Guard" value="..."/>`, `from`/`to` = **logical** block ids,
`name` = "Link".
Graphical ControlFlow: `from`/`to` = **graphical** block ids, `<double key="fromPort">`,
`<double key="toPort">`, `position` = start point, `configuration` = polyline relative to position
(`"0, 0 : dx, dy : "`).

## Guards and ports

| Block | Outgoing links |
|---|---|
| most blocks | exactly one, guard `""` |
| `PreconditionalLoop`, `Loop` | two: guard `iteration` → loop body (body must link back to the loop block), guard `""` → after the loop |
| `IfBlock` | two: guard `true` and guard `false` (TRIK's own examples often leave the else link `""`) |
| `SwitchBlock` | one per case, guard = the case value; one with `""` = default |
| `Fork` | one per thread, guard = thread name; the one guarded `main` continues the main thread |
| `FinalNode` | none |

`FiBlock` ("End if") is optional; it just merges branches. `Join` merges threads.

Ports are positions on the block outline: `0.5` top middle, `1.5` right middle, `2.5` bottom middle,
`3.5` left middle. They only affect drawing.

## metaInfo.xml

```xml
<metaInformation>
    <info key="RobotsMetamodelVersion" type="QString" value="2024.1.0"/>
    <info key="trikStudioVersion" type="QString" value="2025.4"/>
    <info key="lastKitId" type="QString" value="trikV62Kit"/>
    <info key="activeCode" type="QString" value="...escaped program text..."/>    <!-- optional -->
    <info key="activeCodeLanguageExtension" type="QString" value="py"/>          <!-- py or js -->
</metaInformation>
```

A project may hold a diagram, embedded code, or both. The 2D model's `-m script` runs `activeCode`;
`-m diagram` runs the blocks.

## worldModel.xml

```xml
<root version="20251011">
  <world> <walls/> <colorFields/> ... <robot direction=".." position="x:y"><startPosition .../></robot> </world>
  <robots>
    <robot id="trikKitRobot">
      <sensors> <sensor port="A1###input###JA1###sensorA1" type="kitBase::robotModel::robotParts::LightSensor" .../> ... </sensors>
      <wheels left="M4###output###М4###" right="M3###output###М3###"/>   <!-- 2nd М is Cyrillic -->
    </robot>
  </robots>
  <settings realisticSensors="false" realisticMotors="false" realisticPhysics="false"/>
</root>
```
A `<constraints>` section with `<timelimit value="ms"/>` ends simulations automatically (used by checkers).

## Rules that crash TRIK Studio if broken

- Every id listed as a child (root children, diagram children, `links` lists) must have a file.
  A dangling id segfaults TRIK Studio on open.
- Every logical block/link must be in the root object's `<children>`; every graphical one in the
  graphical diagram node's `<children>`.
- Link logical `from`/`to` use logical ids; graphical `from`/`to` use graphical ids. Mixing them
  silently breaks the diagram.
- Zip directory entries (`tree/logical/RobotsMetamodel/RobotsDiagram/Timer/`) are present in files
  TRIK writes; keep them when adding new types (`qrs_tool.py` does).
