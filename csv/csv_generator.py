import subprocess
import os
import tempfile
import csv
from datetime import datetime
import re
import xml.etree.ElementTree as ET  # apenas se você ainda quiser manter parse XML antigo (não usamos aqui)


def run_java_analysis_to_csv(java_file, class_name, out_dir="."):
    """
    Compila e executa uma classe Java com flags de GC e PrintCompilation
    e escreve os resultados em CSVs.

    Arquivos gerados:
      - program_output.csv        (colunas: line_no, text)
      - jit_compilations.csv      (colunas: method, compilations, total_bytes, comp_id, level, bytes, special)
      - errors.csv                (colunas: error_type, message, frame_index, frame_text)
      - gc_events.csv             (colunas: index, detail)
      - summary.csv               (colunas: execution_time_ms, total_gc_events, total_methods, total_errors, timestamp)
    """
    os.makedirs(out_dir, exist_ok=True)

    # 1) Compilar
    compile_proc = subprocess.run(["javac", java_file], capture_output=True, text=True)
    if compile_proc.returncode != 0:
        raise RuntimeError(f"Erro na compilação: {compile_proc.stderr}")

    # 2) Preparar log de GC temporário
    gc_log = os.path.join(tempfile.gettempdir(), "gc.log")
    if os.path.exists(gc_log):
        os.remove(gc_log)

    # 3) Executar com GC + PrintCompilation
    # Medimos tempo total de execução em ms
    start = datetime.now()
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
    end = datetime.now()
    execution_ms = int((end - start).total_seconds() * 1000)

    stdout_text = run_proc.stdout or ""
    stderr_text = run_proc.stderr or ""

    # 4) Ler GC log
    gc_events = []
    if os.path.exists(gc_log):
        with open(gc_log, encoding="utf-8", errors="ignore") as f:
            gc_events = [l.strip() for l in f if l.strip()]

    # 5) PROGRAM OUTPUT -> CSV (filtra linhas que NÃO são de PrintCompilation)
    # PrintCompilation geralmente inicia com um número/colunas; vamos filtrar por regex igual ao seu XML
    prog_lines = [
        l for l in stdout_text.splitlines() if not re.match(r"^\s*\d+\s", l.strip())
    ]
    program_output_csv = os.path.join(out_dir, "program_output.csv")
    with open(program_output_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["line_no", "text"])
        for i, line in enumerate(prog_lines, start=1):
            w.writerow([i, line])

    # 6) JIT LOG -> CSV
    # Parser semelhante ao anterior, mas agora escrevemos diretamente linhas tabulares
    jit_regex = re.compile(
        r"^\s*(\d+)\s+(\d+)?\s*([!n]?)\s*(\d+)\s+([\w.$<>:()]+)\s+\((\d+)\s+bytes\)"
    )

    # methods -> { method_name: [ {id, level, bytes, flag}, ... ] }
    methods = {}
    for line in stdout_text.splitlines():
        m = jit_regex.match(line.strip())
        if m:
            comp_id, bci, flag, level, method, bytecode = m.groups()
            methods.setdefault(method, []).append(
                {"id": comp_id, "level": level, "bytes": bytecode, "flag": (flag or "")}
            )

    jit_csv = os.path.join(out_dir, "jit_compilations.csv")
    with open(jit_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "method",
                "compilations",
                "total_bytes",
                "comp_id",
                "level",
                "bytes",
                "special",
            ]
        )
        for method, comps in methods.items():
            total_bytes = sum(int(c["bytes"]) for c in comps)
            for c in comps:
                w.writerow(
                    [
                        method,
                        len(comps),
                        total_bytes,
                        c["id"],
                        c["level"],
                        c["bytes"],
                        c["flag"],
                    ]
                )

    # 7) ERRORS -> CSV
    error_type, message, stacktrace = parse_errors(stderr_text)
    errors_csv = os.path.join(out_dir, "errors.csv")
    with open(errors_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["error_type", "message", "frame_index", "frame_text"])
        if error_type:
            if stacktrace:
                for idx, frame in enumerate(stacktrace):
                    w.writerow([error_type, message, idx, frame])
            else:
                w.writerow([error_type, message, "", ""])

    # 8) GC EVENTS -> CSV
    gc_csv = os.path.join(out_dir, "gc_events.csv")
    with open(gc_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["index", "detail"])
        for i, ev in enumerate(gc_events):
            w.writerow([i, ev])

    # 9) SUMMARY -> CSV
    total_gc_events = len(gc_events)
    total_methods = len(methods)
    total_errors = 1 if error_type else 0
    summary_csv = os.path.join(out_dir, "summary.csv")
    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "execution_time_ms",
                "total_gc_events",
                "total_methods",
                "total_errors",
                "timestamp",
            ]
        )
        w.writerow(
            [
                execution_ms,
                total_gc_events,
                total_methods,
                total_errors,
                datetime.now().isoformat(),
            ]
        )

    return {
        "program_output": program_output_csv,
        "jit_compilations": jit_csv,
        "errors": errors_csv,
        "gc_events": gc_csv,
        "summary": summary_csv,
    }


def parse_errors(stderr_text: str):
    """
    Retorna (error_type, message, stacktrace_list)
    """
    lines = (stderr_text or "").splitlines()
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

    return error_type, (message or ""), stacktrace


if __name__ == "__main__":
    # Exemplo de uso (ajuste paths conforme seu projeto)
    paths = run_java_analysis_to_csv("../test/Test01.java", "Test01", out_dir=".")
    for name, path in paths.items():
        print(f"{name}: {path}")