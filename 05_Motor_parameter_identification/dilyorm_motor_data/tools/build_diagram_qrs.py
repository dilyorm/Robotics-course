"""Build motor_identification_diagram.qrs: the Lab 5 data collection as a TRIK block diagram.

Same experiment as collect_motor_data.py, but drawn with blocks so it runs when TRIK Studio
generates JavaScript from the diagram (the default "Upload and run").

    python tools/build_diagram_qrs.py

Layout of the program:
    init -> mkdir -> while wid < 3:                         (wheel 1 = M4/E4 left, wheel 2 = M3/E3 right)
        level (pwm from lvl) -> show+battery -> clear E3,E4 -> wait 500 -> start clock
        -> M3 = pwm*k3, M4 = pwm*k4 -> while tt < 2000: sample into buf, wait 1
        -> loaded battery -> stop M3,M4 -> save file -> wait 1000 -> next level/wheel
    -> done

Three things blocks cannot do are "System Call" blocks with the Code flag (raw JavaScript):
creating the output folder, reading the battery, and writing to a computed file name
(the Write To File block only takes a fixed name).
"""
import uuid
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent.parent
TEMPLATE = HERE.parent / "Motor_identification.qrs"   # robot model / world configuration
OUT = HERE / "motor_identification_diagram.qrs"

NS = "qrm:/RobotsMetamodel/RobotsDiagram/"
ROOT = "qrm:/ROOT_ID/ROOT_ID/ROOT_ID/ROOT_ID"
DIAG_G = NS + "RobotsDiagramNode/{a3f65927-d294-45c6-a407-928b808ff096}"
DIAG_L = NS + "RobotsDiagramNode/{3b75d073-95bd-404d-9552-6b6197f98108}"

SAVE_JS = r'''var fn = "dilyorm_motor_data/wheel_" + wid + "_v_" + pwm + ".txt";
script.removeFile(fn);
script.writeToFile(fn, "# wheel_id: " + wid
    + "\n# wheel_label: " + (wid == 1 ? "left" : "right")
    + "\n# motor_port: " + (wid == 1 ? "M4" : "M3")
    + "\n# encoder_port: " + (wid == 1 ? "E4" : "E3")
    + "\n# pwm_percent: " + pwm
    + "\n# battery_voltage: " + vbat
    + "\n# battery_voltage_loaded: " + vload
    + "\n# format: time_ms angle_deg\n" + buf);
script.system("sync", true);'''

SHOW_JS = r'''try { vbat = brick.battery().readVoltage(); } catch (e) { vbat = -1; }
brick.display().clear();
brick.display().addLabel("W" + wid + " PWM " + pwm + "%", 1, 1);
brick.display().addLabel("bat " + vbat + " V", 1, 30);
brick.display().redraw();'''

DONE_JS = r'''brick.display().clear();
brick.display().addLabel("DONE dilyorm_motor_data", 1, 1);
brick.display().redraw();
brick.playTone(1000, 300);
script.wait(400);'''

# key: (type, x, y, properties)
BLOCKS = {
    "start": ("InitialNode", 0, 0, {}),
    "init": ("Function", 0, 100, {"Body": 'wid = 1;\nlvl = 0;\npwm = 0;\nk3 = 0;\nk4 = 0;\n'
                                           'tt = 0;\nt0 = 0;\nth = 0;\nbuf = "";'}),
    "mkdir": ("TrikSystem", 0, 200, {"Command": 'script.system("mkdir -p dilyorm_motor_data", true);',
                                      "Code": "true", "Evaluate": "false"}),
    "wheels": ("PreconditionalLoop", 0, 300, {"Condition": "wid < 3"}),
    "level": ("Function", 0, 400, {"Body": "pwm = 5 * lvl - 100 + 5 * (sgn(lvl - 19.5) + 1) / 2;\n"
                                           "k4 = 2 - wid;\nk3 = wid - 1;"}),
    "show": ("TrikSystem", 0, 500, {"Command": SHOW_JS, "Code": "true", "Evaluate": "false"}),
    "clear": ("TrikV62ClearEncoder", 0, 600, {"Ports": "E3, E4"}),
    "settle": ("Timer", 0, 700, {"Delay": "500"}),
    "t0": ("Function", 0, 800, {"Body": 'buf = "";\nt0 = time();\ntt = 0;'}),
    "m3": ("TrikV6EnginesForward", 0, 900, {"Ports": "M3", "Power": "pwm * k3"}),
    "m4": ("TrikV6EnginesForward", 0, 1000, {"Ports": "M4", "Power": "pwm * k4"}),
    "samples": ("PreconditionalLoop", 0, 1100, {"Condition": "tt < 2000"}),
    "sample": ("Function", 250, 1100, {"Body": "th = encoder3 * k3 + encoder4 * k4;\ntt = time() - t0;\n"
                                               'buf = buf .. tt .. " " .. th .. "\\n";'}),
    "tick": ("Timer", 250, 1200, {"Delay": "1"}),
    "loaded": ("TrikSystem", 0, 1250, {"Command": "try { vload = brick.battery().readVoltage(); } "
                                                  "catch (e) { vload = -1; }",
                                       "Code": "true", "Evaluate": "false"}),
    "stop": ("TrikV6EnginesStop", 0, 1350, {"Ports": "M3, M4"}),
    "save": ("TrikSystem", 0, 1450, {"Command": SAVE_JS, "Code": "true", "Evaluate": "false"}),
    "rest": ("Timer", 0, 1550, {"Delay": "1000"}),
    "next": ("Function", 0, 1650, {"Body": "lvl = lvl + 1;\nwid = wid + (sgn(lvl - 39.5) + 1) / 2;\n"
                                           "lvl = lvl - 40 * (sgn(lvl - 39.5) + 1) / 2;"}),
    "done": ("TrikSystem", 300, 300, {"Command": DONE_JS, "Code": "true", "Evaluate": "false"}),
    "end": ("FinalNode", 300, 400, {}),
}

# (from, to, guard, fromPort, toPort)   ports: 0.5 top, 1.5 right, 2.5 bottom, 3.5 left
LINKS = [
    ("start", "init", "", 2.5, 0.5), ("init", "mkdir", "", 2.5, 0.5), ("mkdir", "wheels", "", 2.5, 0.5),
    ("wheels", "level", "iteration", 2.5, 0.5), ("wheels", "done", "", 1.5, 3.5),
    ("level", "show", "", 2.5, 0.5), ("show", "clear", "", 2.5, 0.5), ("clear", "settle", "", 2.5, 0.5),
    ("settle", "t0", "", 2.5, 0.5), ("t0", "m3", "", 2.5, 0.5), ("m3", "m4", "", 2.5, 0.5),
    ("m4", "samples", "", 2.5, 0.5),
    ("samples", "sample", "iteration", 1.5, 3.5), ("sample", "tick", "", 2.5, 0.5),
    ("tick", "samples", "", 3.5, 2.5),
    ("samples", "loaded", "", 2.5, 0.5), ("loaded", "stop", "", 2.5, 0.5), ("stop", "save", "", 2.5, 0.5),
    ("save", "rest", "", 2.5, 0.5), ("rest", "next", "", 2.5, 0.5), ("next", "wheels", "", 3.5, 3.5),
    ("done", "end", "", 2.5, 0.5),
]

SIZE = 50


def q(v):
    return escape(v, {'"': "&quot;", "\n": "&#xa;", "\t": "&#x9;"})


def ids():
    return "{%s}" % uuid.uuid4(), "{%s}" % uuid.uuid4()


def ref_list(refs):
    if not refs:
        return '<links type="qReal::IdList"/>'
    return '<links type="qReal::IdList">\n%s    </links>' % "".join(
        '      <object id="%s"/>\n' % r for r in refs)


def main():
    nodes = {k: (NS + t + "/" + ids()[0], NS + t + "/" + ids()[1]) for k, (t, *_r) in BLOCKS.items()}
    links = []
    for a, b, guard, fp, tp in LINKS:
        g, l = ids()
        links.append(dict(a=a, b=b, guard=guard, fp=fp, tp=tp, g=NS + "ControlFlow/" + g, l=NS + "ControlFlow/" + l))

    files = {}
    for k, (typ, x, y, props) in BLOCKS.items():
        gid, lid = nodes[k]
        lrefs = [lk["l"] for lk in links if k in (lk["a"], lk["b"])]
        grefs = [lk["g"] for lk in links if k in (lk["a"], lk["b"])]
        extra = "".join('    <QString key="%s" value="%s"/>\n' % (pk, q(pv)) for pk, pv in props.items())
        files["tree/logical/" + lid[len("qrm:/"):]] = (
            '<object parent="%s" id="%s">\n  <children/>\n  <properties>\n%s'
            '    <qReal::Id key="from" value="%s"/>\n    <incomingExplosions type="qReal::IdList"/>\n'
            '    <int key="linkShape" value="0"/>\n    %s\n    <QString key="name" value="%s"/>\n'
            '    <qReal::Id key="outgoingExplosion" value="qrm:/"/>\n    <qReal::Id key="to" value="%s"/>\n'
            '  </properties>\n</object>\n' % (ROOT, lid, extra, ROOT, ref_list(lrefs), k, ROOT))
        files["tree/graphical/" + gid[len("qrm:/"):]] = (
            '<object parent="%s" id="%s" logicalId="%s">\n  <children/>\n  <properties>\n'
            '    <QPolygon key="configuration" value="0, 0 : %d, 0 : %d, %d : 0, %d : "/>\n'
            '    <qReal::Id key="from" value="%s"/>\n    <double key="fromPort" value="0"/>\n    %s\n'
            '    <QString key="name" value="%s"/>\n    <QPointF key="position" value="%d, %d"/>\n'
            '    <qReal::Id key="to" value="%s"/>\n    <double key="toPort" value="0"/>\n'
            '  </properties>\n  <graphicalParts/>\n</object>\n' % (
                DIAG_G, gid, lid, SIZE, SIZE, SIZE, SIZE, ROOT, ref_list(grefs), k, x, y, ROOT))

    def port_xy(k, p):
        _t, x, y, _p = BLOCKS[k]
        side, frac = int(p), p - int(p)
        return {0: (x + frac * SIZE, y), 1: (x + SIZE, y + frac * SIZE),
                2: (x + (1 - frac) * SIZE, y + SIZE), 3: (x, y + (1 - frac) * SIZE)}[side]

    for lk in links:
        (x0, y0), (x1, y1) = port_xy(lk["a"], lk["fp"]), port_xy(lk["b"], lk["tp"])
        files["tree/logical/" + lk["l"][len("qrm:/"):]] = (
            '<object parent="%s" id="%s">\n  <children/>\n  <properties>\n'
            '    <QString key="Guard" value="%s"/>\n    <qReal::Id key="from" value="%s"/>\n'
            '    <incomingExplosions type="qReal::IdList"/>\n    <int key="linkShape" value="0"/>\n'
            '    <links type="qReal::IdList"/>\n    <QString key="name" value="Link"/>\n'
            '    <qReal::Id key="outgoingExplosion" value="qrm:/"/>\n    <qReal::Id key="to" value="%s"/>\n'
            '  </properties>\n</object>\n' % (ROOT, lk["l"], lk["guard"], nodes[lk["a"]][1], nodes[lk["b"]][1]))
        files["tree/graphical/" + lk["g"][len("qrm:/"):]] = (
            '<object parent="%s" id="%s" logicalId="%s">\n  <children/>\n  <properties>\n'
            '    <QPolygon key="configuration" value="0, 0 : %g, %g : "/>\n'
            '    <qReal::Id key="from" value="%s"/>\n    <double key="fromPort" value="%g"/>\n'
            '    <links type="qReal::IdList"/>\n    <QString key="name" value="Link"/>\n'
            '    <QPointF key="position" value="%g, %g"/>\n    <qReal::Id key="to" value="%s"/>\n'
            '    <double key="toPort" value="%g"/>\n  </properties>\n  <graphicalParts/>\n</object>\n' % (
                DIAG_G, lk["g"], lk["l"], x1 - x0, y1 - y0, nodes[lk["a"]][0], lk["fp"], x0, y0,
                nodes[lk["b"]][0], lk["tp"]))

    children_g = [nodes[k][0] for k in BLOCKS] + [lk["g"] for lk in links]
    children_root = [DIAG_G, DIAG_L] + [nodes[k][1] for k in BLOCKS] + [lk["l"] for lk in links]

    def with_children(xml, refs):
        import re
        body = "<children>\n%s  </children>" % "".join('    <object id="%s"/>\n' % r for r in refs)
        return re.sub(r"<children/>|<children>.*?</children>", lambda _: body, xml, count=1, flags=re.S)

    with zipfile.ZipFile(TEMPLATE) as zin, zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            n = info.filename
            parts = n.split("/")
            if len(parts) > 4 and parts[2] == "RobotsMetamodel" and parts[4] != "RobotsDiagramNode":
                continue                                    # professor's blocks
            data = zin.read(n).decode("utf-8") if not n.endswith("/") else ""
            if n.startswith("tree/graphical/") and "/RobotsDiagramNode/{" in n:
                data = with_children(data, children_g)
            elif n == "tree/logical/ROOT_ID/ROOT_ID/ROOT_ID/ROOT_ID":
                data = with_children(data, children_root)
            elif n == "metaInfo.xml":
                import re
                data = re.sub(r'\s*<info key="activeCode(LanguageExtension)?"[^>]*/>', "", data)
            zout.writestr(info, data.encode("utf-8") if data else b"")
        have = set(zout.namelist())
        for d in sorted({p.rsplit("/", 1)[0] + "/" for p in files}):
            if d not in have:
                zout.writestr(d, b"")
        for path, xml in sorted(files.items()):
            zout.writestr(path, xml.encode("utf-8"))
    print("wrote", OUT, "-", len(BLOCKS), "blocks,", len(links), "links")


if __name__ == "__main__":
    main()
