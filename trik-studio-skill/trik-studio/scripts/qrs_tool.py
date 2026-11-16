#!/usr/bin/env python3
"""Read and write TRIK Studio project files (.qrs) without opening TRIK Studio.

    python qrs_tool.py inspect  prog.qrs                 # summary: kit, language, world, blocks, links
    python qrs_tool.py get-code prog.qrs [-o code.py]    # print/save embedded Python/JS code
    python qrs_tool.py set-code prog.qrs code.py [-o out.qrs] [--strip-diagram]
    python qrs_tool.py dump     prog.qrs [-o spec.json]  # block diagram -> editable JSON spec
    python qrs_tool.py build    spec.json -o out.qrs [--template base.qrs] [--drop-code]
    python qrs_tool.py new      out.qrs [--code prog.py] # new TRIK project (2D world, M4 left / M3 right)
    python qrs_tool.py wheels   prog.qrs M3 M4           # set which motors are the 2D robot's left/right wheels

Spec format (build / dump):
    {"blocks": [{"id": "start", "type": "InitialNode"},
                {"id": "go", "type": "TrikV6EnginesForward", "props": {"Ports": "M3, M4", "Power": "60"}},
                {"id": "wait", "type": "Timer", "props": {"Delay": "1000"}, "x": 0, "y": 200},
                ...],
     "links": [["start", "go"], ["go", "wait"],
               ["loop", "body", "iteration"],                       # [from, to, guard]
               {"from": "if", "to": "a", "guard": "true", "fromPort": 1.5, "toPort": 3.5}]}
Missing x/y: the block goes 100 px below the previous one. Missing ports: picked from relative
position (0.5 top, 1.5 right, 2.5 bottom, 3.5 left). Missing props: TRIK defaults from blocks.json.
Optional "name" per block = the name stored in the project (dump fills it; default = the id).
A project can hold BOTH a diagram and embedded code; build keeps the template's code unless --drop-code.
"""
import argparse
import html
import json
import re
import shutil
import sys
import uuid
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
CATALOG = json.loads((HERE / "blocks.json").read_text(encoding="utf-8"))
DEFAULT_TEMPLATE = HERE.parent / "assets" / "template.qrs"

NS = "qrm:/RobotsMetamodel/RobotsDiagram/"
ROOT = "qrm:/ROOT_ID/ROOT_ID/ROOT_ID/ROOT_ID"
ROOT_FILE = "tree/logical/ROOT_ID/ROOT_ID/ROOT_ID/ROOT_ID"
SIZE = 50
ELEM_RE = re.compile(r'(\s*)<([\w:]+)((?:\s+\w+="[^"]*")*)\s*/>')  # empty element, any attribute order
ATTR_RE = re.compile(r'(\w+)="([^"]*)"')
SKIP_PROPS = {"from", "to", "linkShape", "outgoingExplosion", "fromPort", "toPort", "configuration", "position"}
LOOPS = {"PreconditionalLoop", "Loop"}
MULTI_OUT = {"IfBlock", "SwitchBlock", "Fork"} | LOOPS


def q(v):
    return escape(str(v), {'"': "&quot;", "\n": "&#xa;", "\t": "&#x9;", "\r": "&#xd;"})


def new_id(typ):
    return "%s%s/{%s}" % (NS, typ, uuid.uuid4())


def elements(xml, tag=None):
    """[{attr: unescaped value}] for every empty element <tag a="..." .../> (TRIK varies attribute order,
    and values may hold a raw '>')."""
    return [{k: html.unescape(v) for k, v in ATTR_RE.findall(attrs)}
            for _ws, t, attrs in ELEM_RE.findall(xml) if tag is None or t == tag]


def type_of(qid):
    m = re.match(re.escape(NS) + r"([^/]+)/", qid)
    return m.group(1) if m else None


def path_of(qid, tree):
    return "tree/%s/%s" % (tree, qid[len("qrm:/"):])


# ---------------------------------------------------------------- reading

class Project:
    def __init__(self, path):
        self.path = Path(path)
        with zipfile.ZipFile(self.path) as z:
            self.infos = z.infolist()
            self.data = {i.filename: z.read(i.filename) for i in self.infos}
        self.meta = {a["key"]: a.get("value", "") for a in elements(self.text("metaInfo.xml"), "info")}
        self.objects = {}  # (tree, qid) -> dict(parent, logicalId, props, children)
        for name in self.data:
            m = re.match(r"tree/(graphical|logical)/(RobotsMetamodel/.+)", name)
            if not m or name.endswith("/"):
                continue
            xml = self.text(name)
            head = re.search(r"<object ([^>]*)>", xml).group(1)
            attrs = dict(re.findall(r'(\w+)="([^"]*)"', head))
            props_xml = re.search(r"<properties>(.*?)</properties>", xml, re.S)
            props = {a["key"]: a.get("value", "") for a in elements(props_xml.group(1) if props_xml else "")
                     if "key" in a}
            ch = re.search(r"<children>(.*?)</children>", xml, re.S)
            self.objects[(m.group(1), "qrm:/" + m.group(2))] = dict(
                parent=attrs.get("parent"), logicalId=attrs.get("logicalId"), props=props,
                children=re.findall(r'<object id="([^"]+)"', ch.group(1)) if ch else [])

    def text(self, name):
        return self.data[name].decode("utf-8") if name in self.data else ""

    def diagrams(self):
        """Graphical RobotsDiagramNode ids (main diagram first)."""
        ds = [k[1] for k in self.objects if k[0] == "graphical" and type_of(k[1]) == "RobotsDiagramNode"]
        return sorted(ds, key=lambda d: self.objects[("graphical", d)]["parent"] != ROOT)

    def main_diagram(self):
        ds = self.diagrams()
        if not ds:
            sys.exit("no RobotsDiagramNode in %s" % self.path)
        g = ds[0]
        return g, self.objects[("graphical", g)]["logicalId"]

    def world(self):
        w = self.text("worldModel.xml")
        wheels = re.search(r'<wheels left="([^"#]+)[^"]*" right="([^"#]+)', w)
        robot = re.search(r'<robot id="([^"]+)"', w)
        return dict(wheels=wheels.groups() if wheels else None, robot=robot.group(1) if robot else None,
                    timelimit=re.findall(r'<timelimit[^>]*value="(\d+)"', w))

    def to_spec(self):
        g_diag, _ = self.main_diagram()
        gnodes = self.objects[("graphical", g_diag)]["children"]
        blocks, links, key_of, used = [], [], {}, set()
        for g in gnodes:
            t = type_of(g)
            go = self.objects.get(("graphical", g))
            if go is None or t == "ControlFlow":
                continue
            lo = self.objects.get(("logical", go["logicalId"]), {"props": {}})
            name = lo["props"].get("name", "")
            if re.fullmatch(r"[A-Za-z_]\w*", name) and name not in used                     and name != CATALOG.get(t, {}).get("label"):
                key = name  # id given by qrs_tool build
            else:
                base = re.sub(r"[^a-z0-9]+", "_", t.lower())
                n = 1
                while "%s%d" % (base, n) in used:
                    n += 1
                key = "%s%d" % (base, n)
            used.add(key)
            key_of[go["logicalId"]] = key
            x, y = (float(v) for v in go["props"].get("position", "0, 0").split(","))
            props = {k: v for k, v in lo["props"].items() if k not in SKIP_PROPS and k != "name"}
            b = dict(id=key, type=t, x=round(x), y=round(y), props=props)
            if name and name != key:
                b["name"] = name
            blocks.append(b)
        for g in gnodes:
            if type_of(g) != "ControlFlow":
                continue
            go = self.objects[("graphical", g)]
            lo = self.objects.get(("logical", go["logicalId"]), {"props": {}})
            a, b = lo["props"].get("from"), lo["props"].get("to")
            if a not in key_of or b not in key_of:
                print("warning: dangling link %s skipped" % g, file=sys.stderr)
                continue
            links.append({"from": key_of[a], "to": key_of[b], "guard": lo["props"].get("Guard", ""),
                          "fromPort": float(go["props"].get("fromPort", 2.5)),
                          "toPort": float(go["props"].get("toPort", 0.5))})
        if len(self.diagrams()) > 1 or any(b["type"] == "Subprogram" for b in blocks):
            print("warning: project has subprograms; only the main diagram is in the spec", file=sys.stderr)
        return {"blocks": blocks, "links": links}


# ---------------------------------------------------------------- writing

def set_meta(xml, key, value):
    entry = '<info key="%s" type="QString" value="%s"/>' % (key, q(value))
    hit = []

    def repl(m):
        if m.group(2) != "info" or dict(ATTR_RE.findall(m.group(3))).get("key") != key:
            return m.group(0)
        hit.append(m)
        return m.group(1) + entry if len(hit) == 1 else ""
    xml = ELEM_RE.sub(repl, xml)
    if not hit:
        xml = xml.replace("</metaInformation>", "    " + entry + "\n</metaInformation>")
    return xml


def del_meta(xml, key):
    return ELEM_RE.sub(lambda m: "" if m.group(2) == "info" and dict(ATTR_RE.findall(m.group(3))).get("key") == key
                       else m.group(0), xml)


def with_children(xml, refs):
    body = "<children>\n%s  </children>" % "".join('    <object id="%s"/>\n' % r for r in refs) if refs \
        else "<children/>"
    return re.sub(r"<children/>|<children>.*?</children>", lambda _: body, xml, count=1, flags=re.S)


def is_diagram_element(name):
    m = re.match(r"tree/(graphical|logical)/RobotsMetamodel/RobotsDiagram/([^/]+)/", name)
    return bool(m) and m.group(2) != "RobotsDiagramNode"


def write_project(template, out, files=None, meta=None, drop_meta=(), keep_diagram=False):
    """Copy template to out. Unless keep_diagram, drop every block/link and add `files`
    (dict path -> xml) as the new diagram. meta: dict of metaInfo keys to set."""
    proj = Project(template)
    g_diag, l_diag = proj.main_diagram()
    files = files or {}
    new_g = [k for k in files if k.startswith("tree/graphical/")]
    new_l = [k for k in files if k.startswith("tree/logical/")]
    to_id = lambda p: "qrm:/" + p.split("/", 2)[2]
    if not keep_diagram and len(proj.diagrams()) > 1:
        print("warning: template has subprogram diagrams; they are dropped", file=sys.stderr)
    out_tmp = Path(str(out) + ".tmp")
    with zipfile.ZipFile(out_tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        written = set()
        for info in proj.infos:
            n = info.filename
            if not keep_diagram:
                if is_diagram_element(n):
                    continue
                if "/RobotsDiagramNode/{" in n and to_id(n) not in (g_diag, l_diag):
                    continue  # subprogram diagram nodes
            data = proj.data[n]
            if n == "metaInfo.xml":
                xml = data.decode("utf-8")
                for k in drop_meta:
                    xml = del_meta(xml, k)
                for k, v in (meta or {}).items():
                    xml = set_meta(xml, k, v)
                data = xml.encode("utf-8")
            elif not keep_diagram and n == path_of(g_diag, "graphical"):
                data = with_children(data.decode("utf-8"), [to_id(p) for p in sorted(new_g)]).encode("utf-8")
            elif not keep_diagram and n == ROOT_FILE:
                data = with_children(data.decode("utf-8"),
                                     [g_diag, l_diag] + [to_id(p) for p in sorted(new_l)]).encode("utf-8")
            zout.writestr(info, data)
            written.add(n)
        for d in sorted({p.rsplit("/", 1)[0] + "/" for p in files}):
            if d not in written:
                zout.writestr(d, b"")
        for p, xml in sorted(files.items()):
            zout.writestr(p, xml.encode("utf-8"))
    backup_if_same(template, out)
    out_tmp.replace(out)


def backup_if_same(src, out):
    """Keep the previous version as <name>.qrs.bak when a command overwrites its own input."""
    if Path(out).exists() and Path(out).resolve() == Path(src).resolve():
        shutil.copy2(out, str(out) + ".bak")


def ref_list(refs):
    if not refs:
        return '<links type="qReal::IdList"/>'
    return '<links type="qReal::IdList">\n%s    </links>' % "".join('      <object id="%s"/>\n' % r for r in refs)


def norm_link(lk):
    if isinstance(lk, dict):
        return dict(lk)
    keys = ["from", "to", "guard", "fromPort", "toPort"]
    return dict(zip(keys, lk))


def validate(blocks, links):
    errors, warns = [], []
    ids = [b["id"] for b in blocks]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        errors.append("duplicate block ids: %s" % sorted(dup))
    byid = {b["id"]: b for b in blocks}
    for lk in links:
        for end in ("from", "to"):
            if lk.get(end) not in byid:
                errors.append("link %s -> %s: unknown block %r" % (lk.get("from"), lk.get("to"), lk.get(end)))
    if errors:
        return errors, warns
    if any(b["type"] == "Subprogram" for b in blocks):
        errors.append("Subprogram blocks are not supported by build (their diagrams would be lost); "
                      "inline the blocks, or edit subprograms in TRIK Studio")
    starts = [b["id"] for b in blocks if b["type"] == "InitialNode"]
    if len(starts) != 1:
        errors.append("need exactly one InitialNode, found %d" % len(starts))
    for b in blocks:
        t = b["type"]
        if t not in CATALOG:
            warns.append("%s: unknown block type %r (see references/blocks.md)" % (b["id"], t))
        else:
            unknown = set(b.get("props", {})) - set(CATALOG[t]["props"]) - {"Init", "dynamicProperties"}  # legacy
            if unknown:
                warns.append("%s (%s): unknown properties %s, expected %s" % (
                    b["id"], t, sorted(unknown), sorted(CATALOG[t]["props"])))
        out = [lk for lk in links if lk["from"] == b["id"]]
        guards = sorted(lk.get("guard", "") or "" for lk in out)
        if t == "FinalNode" and out:
            errors.append("%s: FinalNode cannot have outgoing links" % b["id"])
        elif t in LOOPS and guards != ["", "iteration"]:
            errors.append("%s (%s): needs two outgoing links, guards 'iteration' (body) and '' (exit); got %s"
                          % (b["id"], t, guards))
        elif t == "IfBlock" and not (len(out) == 2 and len(set(guards)) == 2 and set(guards) <= {"true", "false", ""}
                                     and set(guards) != {"false", ""}):
            errors.append("%s (IfBlock): needs two outgoing links guarded 'true' and 'false' (or '' for else); "
                          "got %s" % (b["id"], guards))
        elif t not in MULTI_OUT and t not in ("FinalNode", "CommentBlock") and len(out) != 1:
            (errors if len(out) > 1 else warns).append(
                "%s (%s): %d outgoing links (expected 1)" % (b["id"], t, len(out)))
        if t not in ("InitialNode", "CommentBlock") and not any(lk["to"] == b["id"] for lk in links):
            warns.append("%s (%s): unreachable, nothing links to it" % (b["id"], t))
    return errors, warns


def auto_ports(a, b):
    dx, dy = b["x"] - a["x"], b["y"] - a["y"]
    if abs(dy) >= abs(dx):
        return (2.5, 0.5) if dy > 0 else (0.5, 2.5)
    return (1.5, 3.5) if dx > 0 else (3.5, 1.5)


def port_xy(b, p):
    x, y = b["x"], b["y"]
    side, frac = int(p), p - int(p)
    return {0: (x + frac * SIZE, y), 1: (x + SIZE, y + frac * SIZE),
            2: (x + (1 - frac) * SIZE, y + SIZE), 3: (x, y + (1 - frac) * SIZE)}[side % 4]


def spec_to_files(spec, g_diag):
    blocks = [dict(b) for b in spec["blocks"]]
    links = [norm_link(lk) for lk in spec.get("links", [])]
    errors, warns = validate(blocks, links)
    for w in warns:
        print("warning:", w, file=sys.stderr)
    if errors:
        sys.exit("spec errors:\n  " + "\n  ".join(errors))

    px, py = 0, -100
    for b in blocks:
        b["x"] = b.get("x", px)
        b["y"] = b.get("y", py + 100)
        px, py = b["x"], b["y"]
        props = dict(CATALOG.get(b["type"], {}).get("props", {}))
        props.update({k: str(v) for k, v in b.get("props", {}).items()})
        b["props"] = props
        b["name"] = b.get("name") or b["id"]
        b["lid"], b["gid"] = new_id(b["type"]), new_id(b["type"])
    byid = {b["id"]: b for b in blocks}
    for lk in links:
        lk["guard"] = lk.get("guard") or ""
        fp, tp = auto_ports(byid[lk["from"]], byid[lk["to"]])
        lk["fromPort"] = float(lk["fromPort"]) if lk.get("fromPort") is not None else fp
        lk["toPort"] = float(lk["toPort"]) if lk.get("toPort") is not None else tp
        lk["lid"], lk["gid"] = new_id("ControlFlow"), new_id("ControlFlow")

    files = {}
    for b in blocks:
        mine = [lk for lk in links if b["id"] in (lk["from"], lk["to"])]
        extra = "".join('    <QString key="%s" value="%s"/>\n' % (k, q(v)) for k, v in sorted(b["props"].items()))
        files[path_of(b["lid"], "logical")] = (
            '<object parent="%s" id="%s">\n  <children/>\n  <properties>\n%s'
            '    <qReal::Id key="from" value="%s"/>\n    <incomingExplosions type="qReal::IdList"/>\n'
            '    <int key="linkShape" value="0"/>\n    %s\n    <QString key="name" value="%s"/>\n'
            '    <qReal::Id key="outgoingExplosion" value="qrm:/"/>\n    <qReal::Id key="to" value="%s"/>\n'
            '  </properties>\n</object>\n' % (ROOT, b["lid"], extra, ROOT, ref_list([lk["lid"] for lk in mine]),
                                              q(b["name"]), ROOT))
        files[path_of(b["gid"], "graphical")] = (
            '<object parent="%s" id="%s" logicalId="%s">\n  <children/>\n  <properties>\n'
            '    <QPolygon key="configuration" value="0, 0 : %d, 0 : %d, %d : 0, %d : "/>\n'
            '    <qReal::Id key="from" value="%s"/>\n    <double key="fromPort" value="0"/>\n    %s\n'
            '    <QString key="name" value="%s"/>\n    <QPointF key="position" value="%g, %g"/>\n'
            '    <qReal::Id key="to" value="%s"/>\n    <double key="toPort" value="0"/>\n'
            '  </properties>\n  <graphicalParts/>\n</object>\n' % (
                g_diag, b["gid"], b["lid"], SIZE, SIZE, SIZE, SIZE, ROOT, ref_list([lk["gid"] for lk in mine]),
                q(b["name"]), b["x"], b["y"], ROOT))
    for lk in links:
        a, b = byid[lk["from"]], byid[lk["to"]]
        (x0, y0), (x1, y1) = port_xy(a, lk["fromPort"]), port_xy(b, lk["toPort"])
        files[path_of(lk["lid"], "logical")] = (
            '<object parent="%s" id="%s">\n  <children/>\n  <properties>\n'
            '    <QString key="Guard" value="%s"/>\n    <qReal::Id key="from" value="%s"/>\n'
            '    <incomingExplosions type="qReal::IdList"/>\n    <int key="linkShape" value="0"/>\n'
            '    <links type="qReal::IdList"/>\n    <QString key="name" value="Link"/>\n'
            '    <qReal::Id key="outgoingExplosion" value="qrm:/"/>\n    <qReal::Id key="to" value="%s"/>\n'
            '  </properties>\n</object>\n' % (ROOT, lk["lid"], q(lk["guard"]), a["lid"], b["lid"]))
        files[path_of(lk["gid"], "graphical")] = (
            '<object parent="%s" id="%s" logicalId="%s">\n  <children/>\n  <properties>\n'
            '    <QPolygon key="configuration" value="0, 0 : %g, %g : "/>\n'
            '    <qReal::Id key="from" value="%s"/>\n    <double key="fromPort" value="%g"/>\n'
            '    <links type="qReal::IdList"/>\n    <QString key="name" value="Link"/>\n'
            '    <QPointF key="position" value="%g, %g"/>\n    <qReal::Id key="to" value="%s"/>\n'
            '    <double key="toPort" value="%g"/>\n  </properties>\n  <graphicalParts/>\n</object>\n' % (
                g_diag, lk["gid"], lk["lid"], x1 - x0, y1 - y0, a["gid"], lk["fromPort"], x0, y0,
                b["gid"], lk["toPort"]))
    return files, len(blocks), len(links)


# ---------------------------------------------------------------- commands

def cmd_inspect(a):
    p = Project(a.qrs)
    print("file:     ", p.path)
    print("version:  ", p.meta.get("trikStudioVersion", "?"), "| kit:", p.meta.get("lastKitId", "?"))
    w = p.world()
    print("2D world: ", "robot", w["robot"], "| wheels left=%s right=%s" % w["wheels"] if w["wheels"] else "",
          "| timelimit %s ms" % w["timelimit"][0] if w["timelimit"] else "")
    code = p.meta.get("activeCode")
    if code:
        lang = p.meta.get("activeCodeLanguageExtension", "js")
        print("code:      %s, %d lines embedded (get-code to read it)" % (lang, code.count("\n") + 1))
    spec = p.to_spec()
    if code and len(spec["blocks"]) > 1:
        print("NOTE:      project has BOTH embedded code and a block diagram. sim.py run / trik_robot.py start\n"
              "           use the CODE by default; pass --mode diagram / --diagram for the blocks.")
    if not spec["blocks"]:
        print("diagram:   empty")
        return
    print("diagram:   %d blocks, %d links" % (len(spec["blocks"]), len(spec["links"])))
    outs = {}
    for lk in spec["links"]:
        outs.setdefault(lk["from"], []).append(lk)
    order, seen = [], set()
    byid = {b["id"]: b for b in spec["blocks"]}
    stack = [b["id"] for b in spec["blocks"] if b["type"] == "InitialNode"][::-1]
    while stack:  # depth-first along the links, loop bodies first
        k = stack.pop()
        if k in seen:
            continue
        seen.add(k)
        order.append(byid[k])
        nxt = sorted(outs.get(k, []), key=lambda lk: lk["guard"] in ("iteration", "true"))
        stack += [lk["to"] for lk in nxt]
    order += [b for b in sorted(spec["blocks"], key=lambda b: (b["y"], b["x"])) if b["id"] not in seen]
    for b in order:
        props = "; ".join("%s=%s" % (k, v.replace("\n", "\\n")) for k, v in b["props"].items() if v != "")
        print("  [%s] %s @(%d,%d)%s" % (b["id"], b["type"], b["x"], b["y"], ("  " + props) if props else ""))
        for lk in outs.get(b["id"], []):
            print("      -> %s%s" % (lk["to"], " [%s]" % lk["guard"] if lk["guard"] else ""))


def cmd_get_code(a):
    p = Project(a.qrs)
    code = p.meta.get("activeCode")
    if code is None:
        sys.exit("no embedded code (this is a block-diagram project; use inspect/dump)")
    if a.output:
        Path(a.output).write_bytes(code.encode("utf-8"))  # keep LF line endings
        print("wrote", a.output, "(%s)" % p.meta.get("activeCodeLanguageExtension", "js"))
    else:
        sys.stdout.buffer.write(code.encode("utf-8"))


def cmd_set_code(a):
    code = Path(a.code).read_text(encoding="utf-8")
    lang = a.lang or ("py" if a.code.endswith(".py") else "js")
    out = a.output or a.qrs
    write_project(a.qrs, out, meta={"activeCode": code, "activeCodeLanguageExtension": lang},
                  keep_diagram=not a.strip_diagram)
    print("wrote %s (%s code, %d lines%s)" % (out, lang, code.count("\n") + 1,
                                              ", diagram removed" if a.strip_diagram else ", diagram kept"))


def cmd_dump(a):
    s = json.dumps(Project(a.qrs).to_spec(), ensure_ascii=False, indent=1)
    if a.output:
        Path(a.output).write_text(s, encoding="utf-8")
        print("wrote", a.output)
    else:
        print(s)


def cmd_build(a):
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    template = a.template or DEFAULT_TEMPLATE
    g_diag, _ = Project(template).main_diagram()
    files, nb, nl = spec_to_files(spec, g_diag)
    has_code = bool(Project(template).meta.get("activeCode"))
    drop = ("activeCode", "activeCodeLanguageExtension") if a.drop_code else ()
    write_project(template, a.output, files, drop_meta=drop)
    print("wrote %s - %d blocks, %d links (template %s)" % (a.output, nb, nl, Path(template).name))
    if has_code:
        print("note: template's embedded code was %s" % (
            "removed (--drop-code)" if a.drop_code else
            "KEPT - the project has code + diagram; simulate the blocks with sim.py run --mode diagram, "
            "or rebuild with --drop-code"))


def cmd_wheels(a):
    """Rewrite which motor ports drive the 2D-model robot's left/right wheels."""
    port = lambda p: "%s###output###%s###" % (p, p.replace("M", "М"))
    plain = '<wheels left="%s" right="%s"/>' % (port(a.left), port(a.right))
    esc = plain.replace("<", "&lt;").replace('"', "&quot;")
    proj = Project(a.qrs)
    out = Path(str(a.output or a.qrs) + ".tmp")
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for info in proj.infos:
            data = proj.data[info.filename]
            if info.filename == "worldModel.xml" or "/RobotsDiagramNode/" in info.filename:
                t = data.decode("utf-8")
                t, k1 = re.subn(r'<wheels left="[^"]*" right="[^"]*"\s*/>', lambda _: plain, t)
                t, k2 = re.subn(r'&lt;wheels left=&quot;.*?&quot; right=&quot;.*?&quot;\s*/>', lambda _: esc, t)
                n += k1 + k2
                data = t.encode("utf-8")
            z.writestr(info, data)
    backup_if_same(a.qrs, a.output or a.qrs)
    out.replace(a.output or a.qrs)
    print("set 2D wheels left=%s right=%s in %d place(s)" % (a.left, a.right, n))


def cmd_new(a):
    meta = {}
    if a.code:
        meta = {"activeCode": Path(a.code).read_text(encoding="utf-8"),
                "activeCodeLanguageExtension": "py" if a.code.endswith(".py") else "js"}
    write_project(DEFAULT_TEMPLATE, a.output, {}, meta=meta,
                  drop_meta=() if a.code else ("activeCode", "activeCodeLanguageExtension"))
    print("wrote", a.output, "(with %s)" % a.code if a.code else "")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("inspect"); s.add_argument("qrs"); s.set_defaults(f=cmd_inspect)
    s = sub.add_parser("get-code"); s.add_argument("qrs"); s.add_argument("-o", "--output"); s.set_defaults(f=cmd_get_code)
    s = sub.add_parser("set-code"); s.add_argument("qrs"); s.add_argument("code")
    s.add_argument("-o", "--output", help="default: overwrite input")
    s.add_argument("--lang", choices=["py", "js"], help="default: from code file extension")
    s.add_argument("--strip-diagram", action="store_true", help="also delete the block diagram")
    s.set_defaults(f=cmd_set_code)
    s = sub.add_parser("dump"); s.add_argument("qrs"); s.add_argument("-o", "--output"); s.set_defaults(f=cmd_dump)
    s = sub.add_parser("build"); s.add_argument("spec"); s.add_argument("-o", "--output", required=True)
    s.add_argument("--template", help="qrs whose robot/world settings to reuse (its diagram is replaced)")
    s.add_argument("--drop-code", action="store_true", help="also remove the template's embedded code")
    s.set_defaults(f=cmd_build)
    s = sub.add_parser("new"); s.add_argument("output")
    s.add_argument("--code", help=".py/.js to embed in the new project"); s.set_defaults(f=cmd_new)
    s = sub.add_parser("wheels", help="set 2D-model wheel motors, e.g. wheels prog.qrs M3 M4")
    s.add_argument("qrs"); s.add_argument("left"); s.add_argument("right"); s.add_argument("-o", "--output")
    s.set_defaults(f=cmd_wheels)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    main()
