import subprocess
import os
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
import re


def run_java_analysis(java_file, class_name):
    # 1. Compilar
    compile_proc = subprocess.run(["javac", java_file],
                                  capture_output=True, text=True)
    if compile_proc.returncode != 0:
        raise RuntimeError(f"Erro na compilação: {compile_proc.stderr}")

    # Logs temporários
    gc_log = os.path.join(tempfile.gettempdir(), "gc.log")
    if os.path.exists(gc_log):
        os.remove(gc_log)

    # 2. Rodar com GC + PrintCompilation
    run_proc = subprocess.run([
        "java",
        f"-Xlog:gc*:file={gc_log}:tags,uptime,time,level",
        "-XX:+UnlockDiagnosticVMOptions",
        "-XX:+PrintCompilation",
        class_name
    ], capture_output=True, text=True)

    stdout_text = run_proc.stdout
    stderr_text = run_proc.stderr

    # 3. Ler GC log
    gc_events = []
    if os.path.exists(gc_log):
        with open(gc_log) as f:
            gc_events = [l.strip() for l in f if l.strip()]

    # 4. Construir XML
    root = ET.Element("applicationAnalysis")

    # Program output (filtra tudo que não são compilações JIT)
    prog_elem = ET.SubElement(root, "programOutput")
    prog_lines = [l for l in stdout_text.splitlines()
                  if not re.match(r"^\s*\d+\s", l.strip())]
    prog_elem.text = "\n".join(prog_lines)

    # JIT log
    root.append(parse_jit_log(stdout_text))

    # Errors
    root.append(parse_errors(stderr_text))

    # Garbage Collection
    gc_elem = ET.SubElement(root, "garbageCollection")
    for i, ev in enumerate(gc_events):
        ET.SubElement(gc_elem, "event", timestamp=str(i), detail=ev)

    # Summary
    summary = ET.SubElement(root, "summary")
    ET.SubElement(summary, "executionTime").text = "?"
    ET.SubElement(summary, "totalGCEvents").text = str(len(gc_events))
    ET.SubElement(summary, "totalMethods").text = str(len(root.find("jitLog")))
    ET.SubElement(summary, "totalErrors").text = str(len(root.find("errors")))
    ET.SubElement(summary, "timestamp").text = datetime.now().isoformat()

    with open("analysis.xml", "wb") as f:
        ET.ElementTree(root).write(f, encoding="utf-8", xml_declaration=True)

    return "analysis.xml"


def parse_jit_log(stdout_text):
    """
    Converte linhas de PrintCompilation em <jitLog>.
    """
    jit_elem = ET.Element("jitLog")
    regex = re.compile(
        r"^\s*(\d+)\s+(\d+)?\s*([!n]?)\s*(\d+)\s+([\w.$<>:()]+)\s+\((\d+)\s+bytes\)"
    )
    methods = {}

    for line in stdout_text.splitlines():
        m = regex.match(line.strip())
        if m:
            comp_id, bci, flag, level, method, bytecode = m.groups()
            if method not in methods:
                methods[method] = []
            methods[method].append({
                "id": comp_id,
                "level": level,
                "bytes": bytecode,
                "flag": flag or ""
            })

    for method, comps in methods.items():
        m_elem = ET.SubElement(
            jit_elem,
            "method",
            name=method,
            compilations=str(len(comps)),
            totalTime=f"{sum(int(c['bytes']) for c in comps)}ms"
        )
        for c in comps:
            attribs = {"id": c["id"], "level": c["level"], "bytes": c["bytes"]}
            if c["flag"]:
                attribs["special"] = c["flag"]
            ET.SubElement(m_elem, "compilation", **attribs)

    return jit_elem


def parse_errors(stderr_text):
    """
    Captura exceções e stacktrace.
    """
    errors_elem = ET.Element("errors")
    lines = stderr_text.splitlines()

    error_type = None
    message = None
    stacktrace = []

    for line in lines:
        if "Exception" in line and not error_type:
            parts = line.split(":", 1)
            error_type = parts[0].strip()
            message = parts[1].strip() if len(parts) > 1 else ""
        elif line.strip().startswith("at "):
            stacktrace.append(line.strip())

    if error_type:
        err = ET.SubElement(errors_elem, "error", type=error_type, message=message)
        stack = ET.SubElement(err, "stacktrace")
        for frame in stacktrace:
            ET.SubElement(stack, "frame").text = frame

    return errors_elem


if __name__ == "__main__":
    xml_file = run_java_analysis("../test/Test01.java", "Test01")
    print(f"XML gerado: {xml_file}")
