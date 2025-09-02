import subprocess
import os
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import datetime
import re
import sys


def run_java_analysis(java_file, class_name):
    # 1. Compilar
    compile_proc = subprocess.run(["javac", java_file], capture_output=True, text=True)
    if compile_proc.returncode != 0:
        raise RuntimeError(f"Erro na compilação: {compile_proc.stderr}")

    # Logs temporários
    gc_log = os.path.join(tempfile.gettempdir(), "gc.log")
    if os.path.exists(gc_log):
        os.remove(gc_log)

    # 2. Rodar com GC + PrintCompilation
    inicio_exec = time.time()
    run_proc = subprocess.run(
        [
            "java",
            f"-Xlog:gc*:file={gc_log}:tags,uptime,time,level",
            "-XX:+UnlockDiagnosticVMOptions",
            "-XX:+PrintCompilation",
            class_name,
        ],
        capture_output=True,
        text=True,
    )
    fim_exec = time.time()
    tempo_execucao = fim_exec - inicio_exec

    stdout_text = run_proc.stdout
    stderr_text = run_proc.stderr

    # 3. Ler GC log (contar eventos)
    gc_events = []
    if os.path.exists(gc_log):
        with open(gc_log) as f:
            gc_events = [l.strip() for l in f if l.strip()]

    # 4. Métricas principais
    root = ET.Element("executionMetrics")

    ET.SubElement(root, "executionTimeSec").text = f"{tempo_execucao:.3f}"
    ET.SubElement(root, "gcEvents").text = str(len(gc_events))
    ET.SubElement(root, "jitCompiledMethods").text = str(len(parse_jit_methods(stdout_text)))
    ET.SubElement(root, "errors").text = str(len(parse_errors(stderr_text).findall('error')))
    ET.SubElement(root, "timestamp").text = datetime.now().isoformat()

    # (Opcional: se você quiser estimar threads ativas)
    threads = len(re.findall(r"Thread-", stdout_text))
    ET.SubElement(root, "threadsAtivas").text = str(threads)

    # Salvar XML final
    xml_path = r"C:\Users\qchac\Documents\CompileIQ\infos\\" + class_name + "-metrics.xml"
    with open(xml_path, "wb") as f:
        ET.ElementTree(root).write(f, encoding="utf-8", xml_declaration=True)

    return xml_path


def parse_jit_methods(stdout_text):
    """
    Extrai métodos compilados com estatísticas resumidas.
    """
    regex = re.compile(
        r"^\s*(\d+)\s+(\d+)?\s*([!n]?)\s*(\d+)\s+([\w.$<>:()]+)\s+\((\d+)\s+bytes\)"
    )
    methods = {}

    for line in stdout_text.splitlines():
        m = regex.match(line.strip())
        if m:
            _, _, _, _, method, bytecode = m.groups()
            if method not in methods:
                methods[method] = {"compilations": 0, "bytes": 0}
            methods[method]["compilations"] += 1
            methods[method]["bytes"] += int(bytecode)

    return methods


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
    
    xml_file = run_java_analysis(sys.argv[1], sys.argv[2])
    print(xml_file)