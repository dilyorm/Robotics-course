"""Rebuild Lab9_gyro.qrs from lab9_gyro.py.

Takes the course's Gyro_demo.qrs (for its TRIK robot/world configuration), removes the
block diagram, and stores lab9_gyro.py as the project's Python code. Run after editing
lab9_gyro.py:

    python tools/build_qrs.py
"""
import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent.parent
TEMPLATE = HERE / "Gyro_demo.qrs"
META_SOURCE = HERE / "gyro_test.qrs"   # Gyro_demo.qrs has an empty metaInfo, this one has the kit info
SCRIPT = HERE / "lab9_gyro.py"
OUT = HERE / "Lab9_gyro.qrs"

KIT_KEYS = ("trikStudioVersion", "lastKitId", "RobotsMetamodelVersion")


def is_diagram_element(name):
    m = re.match(r"tree/(graphical|logical)/RobotsMetamodel/RobotsDiagram/([^/]+)/", name)
    return bool(m) and m.group(2) != "RobotsDiagramNode"


def strip_children(xml, keep):
    def repl(m):
        items = re.findall(r'<object id="([^"]+)"/>', m.group(1))
        kept = [i for i in items if keep(i)]
        if not kept:
            return "<children/>"
        return "<children>\n" + "".join('    <object id="%s"/>\n' % i for i in kept) + "  </children>"
    return re.sub(r"<children>(.*?)</children>", repl, xml, flags=re.S)


def set_meta(xml, key, value):
    entry = '<info key="%s" type="QString" value="%s"/>' % (
        key, escape(value, {'"': "&quot;", "\n": "&#xa;", "\t": "&#x9;"}))
    xml, n = re.subn(r'<info key="%s"[^>]*/>' % key, lambda _: entry, xml)
    if n == 0:
        xml = xml.replace("</metaInformation>", "    " + entry + "\n</metaInformation>")
    return xml


def main():
    code = SCRIPT.read_text(encoding="utf-8")
    with zipfile.ZipFile(META_SOURCE) as z:
        meta = z.read("metaInfo.xml").decode("utf-8")
    kit = dict(re.findall(r'<info key="(%s)"[^>]*value="([^"]*)"' % "|".join(KIT_KEYS), meta))
    keep_id = lambda i: "/RobotsDiagramNode/" in i
    with zipfile.ZipFile(TEMPLATE) as zin, zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            name = info.filename
            if is_diagram_element(name):  # block files and their type directories
                continue
            data = zin.read(name)
            if name.startswith("tree/") and not name.endswith("/"):
                data = strip_children(data.decode("utf-8"), keep_id).encode("utf-8")
            elif name == "metaInfo.xml":
                xml = data.decode("utf-8")
                xml = set_meta(xml, "activeCode", code)
                xml = set_meta(xml, "activeCodeLanguageExtension", "py")
                for key in KIT_KEYS:
                    xml = set_meta(xml, key, kit[key])
                data = xml.encode("utf-8")
            zout.writestr(info, data)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
