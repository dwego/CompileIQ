#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Edge AI Pipeline (Completa e Simples)
-------------------------------------
Fluxo: Interpreter -> Optimize -> Validate -> (Conclusive | Non-Conclusive)

Extras (opcionais):
- Avaliação local via javac/java (compilação/execução) para métricas reais.
- Suporte a "threshold" (em ms) para ajudar a validação.
- Artefatos salvos em disco (JSON final e, se conclusivo, optimized.java).

Requisitos:
    pip install ollama

Uso:
    python edge_ai_pipeline.py --java-file test/Test02.java --model gemma3:4b
    # Opcional (avaliar com javac/java; se não houver Java instalado, o script segue sem travar):
    python edge_ai_pipeline.py --java-file test/Test02.java --evaluate --threshold-ms 2000
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from ollama import chat as ollama_chat
except Exception as e:
    raise SystemExit(
        "ERRO: não foi possível importar 'ollama'. Instale com 'pip install ollama' "
        "e garanta que o serviço 'ollama' está rodando localmente."
    )


# ------------------------- Utilidades de arquivo -------------------------

def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    return path.read_text(encoding="utf-8", errors="ignore")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def extract_public_class_name(java_source: str) -> Optional[str]:
    """
    Extrai o nome da primeira classe pública encontrada.
    """
    m = re.search(r"\bpublic\s+class\s+([A-Za-z_]\w*)", java_source)
    if m:
        return m.group(1)
    return None


# ------------------------- Ollama helpers -------------------------

def _extract_json_block(text: str) -> Optional[str]:
    """
    Tenta extrair um JSON válido retornado pela LLM.
    Suporta:
      - ```json ... ```
      - <json>...</json>
      - Primeiro bloco {...} "maior" do texto (fallback).
    """
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"<json>\s*(\{.*?\})\s*</json>", text, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1)
    candidates = re.findall(r"(\{(?:[^{}]|(?1))*\})", text, flags=re.DOTALL)
    if candidates:
        return max(candidates, key=len)
    return None


def call_ollama_json(model: str, system: str, user: str,
                     temperature: float = 0.2, num_predict: int = 1024) -> Dict[str, Any]:
    """
    Chama o Ollama esperando JSON como saída. Se não der parse,
    levanta exceção com a saída crua para debug.
    """
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    resp = ollama_chat(
        model=model,
        messages=messages,
        options={
            "temperature": temperature,
            "num_predict": num_predict,
        },
    )
    text = resp["message"]["content"] if isinstance(resp, dict) else resp.message.content

    json_block = _extract_json_block(text)
    if not json_block:
        try:
            return json.loads(text)
        except Exception:
            raise RuntimeError(
                "Não foi possível extrair/parsear JSON da resposta da LLM.\n"
                f"Saída (primeiros 1200 chars):\n{text[:1200]}"
            )
    try:
        return json.loads(json_block)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"JSON inválido: {e}\nJSON capturado:\n{json_block[:1200]}")


# ------------------------- Estruturas -------------------------

@dataclass
class InterpreterOutput:
    summary: str
    key_points: List[str]

@dataclass
class OptimizeOutput:
    optimized_code: str
    rationale: List[str]

@dataclass
class ValidateOutput:
    status: str  # "conclusive" | "non_conclusive"
    why: str
    trace: List[str]
    recommendations: List[str]


# ------------------------- Agentes -------------------------

def interpreter_agent(model: str, java_code: str) -> InterpreterOutput:
    system = (
        "Você é um analista sênior de Java. Responda APENAS em JSON, em PT-BR."
    )
    user = f"""
Resuma o código Java a seguir. Liste objetivos, fluxo geral e principais classes/métodos.

Formato obrigatório (JSON):
{{
  "summary": "texto curto",
  "key_points": ["bullet 1", "bullet 2"]
}}

[CÓDIGO .JAVA]
{java_code}
""".strip()
    data = call_ollama_json(model, system, user, temperature=0.1, num_predict=800)
    return InterpreterOutput(
        summary=str(data.get("summary","")).strip(),
        key_points=[str(x) for x in data.get("key_points", [])],
    )


def optimize_agent(model: str, java_code: str, interp: InterpreterOutput) -> OptimizeOutput:
    system = (
        "Você é um otimizador de código Java. Saída APENAS em JSON. "
        "Gere um código compilável, mantendo a funcionalidade, com foco em performance e clareza."
    )
    user = f"""
Com base no resumo e pontos-chave abaixo, produza uma versão otimizada do código.
- Mantenha a assinatura e comportamento essenciais.
- Remova redundâncias e prefira estruturas eficientes.
- NÃO inclua comentários no código final.
- Explique as mudanças no campo "rationale".

Formato obrigatório (JSON):
{{
  "optimized_code": "código_java_completo",
  "rationale": ["mudança 1", "mudança 2"]
}}

[RESUMO]
{interp.summary}

[PONTOS-CHAVE]
{interp.key_points}

[CÓDIGO_ORIGINAL]
{java_code}
""".strip()
    data = call_ollama_json(model, system, user, temperature=0.2, num_predict=2000)
    return OptimizeOutput(
        optimized_code=str(data.get("optimized_code","")).strip(),
        rationale=[str(x) for x in data.get("rationale", [])],
    )


# ------------------------- Avaliador opcional (javac/java) -------------------------

def _javac_available() -> bool:
    try:
        subprocess.run(["javac", "-version"], capture_output=True, text=True, timeout=5)
        return True
    except Exception:
        return False

def _java_available() -> bool:
    try:
        subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=5)
        return True
    except Exception:
        return False

def _compile_and_run(source_code: str) -> Dict[str, Any]:
    """
    Compila e executa o Java em diretório temporário.
    Retorna métricas de tempo e stdout/stderr.
    """
    metrics = {
        "ok": False,
        "class_name": None,
        "compile_time_ms": None,
        "run_time_ms": None,
        "stdout": "",
        "stderr": "",
        "error": None,
    }
    try:
        class_name = extract_public_class_name(source_code)
        if not class_name:
            metrics["error"] = "Classe pública não encontrada."
            return metrics

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            java_path = tmpdir / f"{class_name}.java"
            write_text(java_path, source_code)

            # Compilar
            t0 = time.time()
            cproc = subprocess.run(["javac", str(java_path)],
                                   capture_output=True, text=True)
            t1 = time.time()
            metrics["compile_time_ms"] = int((t1 - t0) * 1000)

            if cproc.returncode != 0:
                metrics["stderr"] = cproc.stderr
                metrics["error"] = "Falha ao compilar."
                return metrics

            # Executar
            t0 = time.time()
            rproc = subprocess.run(["java", "-cp", str(tmpdir), class_name],
                                   capture_output=True, text=True, timeout=15)
            t1 = time.time()
            metrics["run_time_ms"] = int((t1 - t0) * 1000)
            metrics["stdout"] = rproc.stdout
            metrics["stderr"] = rproc.stderr
            metrics["ok"] = (rproc.returncode == 0)
            metrics["class_name"] = class_name
            return metrics
    except FileNotFoundError as e:
        metrics["error"] = f"Java não encontrado no PATH: {e}"
        return metrics
    except subprocess.TimeoutExpired:
        metrics["error"] = "Execução excedeu timeout."
        return metrics
    except Exception as e:
        metrics["error"] = f"Erro inesperado: {e}"
        return metrics


# ------------------------- Validador -------------------------

def validate_agent(
    model: str,
    original_code: str,
    opt: OptimizeOutput,
    interp: InterpreterOutput,
    metrics_original: Optional[Dict[str, Any]] = None,
    metrics_optimized: Optional[Dict[str, Any]] = None,
    threshold_ms: Optional[int] = None,
) -> ValidateOutput:
    system = (
        "Você é um validador técnico. Responda APENAS em JSON. "
        "Decida entre 'conclusive' ou 'non_conclusive'. Seja objetivo."
    )
    # Formata métricas legíveis
    def fmt(m):
        if not m:
            return "null"
        return json.dumps(m, ensure_ascii=False)

    user = f"""
Avalie se o código otimizado está pronto para ser entregue.

Critérios mínimos para ser "conclusive":
1) Mantém a funcionalidade do original (equivalência funcional plausível).
2) Não introduz mudanças perigosas óbvias.
3) Demonstra melhoria justificada (pelas razões ou por métricas).
4) (Opcional) Se 'threshold_ms' foi fornecido e houver métricas,
   preferir "conclusive" apenas se o tempo de compilação/execução estiver <= threshold.

Formato obrigatório (JSON):
{{
  "status": "conclusive" | "non_conclusive",
  "why": "resumo",
  "trace": ["checagem 1", "checagem 2"],
  "recommendations": ["se non_conclusive, o que fazer; se conclusive, deixe vazio"]
}}

[THRESHOLD_MS]
{threshold_ms if threshold_ms is not None else "null"}

[MÉTRICAS_ORIGINAL]
{fmt(metrics_original)}

[MÉTRICAS_OTIMIZADO]
{fmt(metrics_optimized)}

[RESUMO]
{interp.summary}

[PONTOS-CHAVE]
{interp.key_points}

[CÓDIGO_ORIGINAL]
{original_code}

[CÓDIGO_OTIMIZADO]
{opt.optimized_code}

[JUSTIFICATIVA_DAS_MUDANÇAS]
{opt.rationale}
""".strip()

    data = call_ollama_json(model, system, user, temperature=0.1, num_predict=800)
    status = str(data.get("status","")).strip()
    if status not in {"conclusive", "non_conclusive"}:
        status = "non_conclusive"

    return ValidateOutput(
        status=status,
        why=str(data.get("why","")).strip(),
        trace=[str(x) for x in data.get("trace", [])],
        recommendations=[str(x) for x in data.get("recommendations", [])],
    )


# ------------------------- Finalizadores -------------------------

def conclusive_agent(opt: OptimizeOutput, val: ValidateOutput) -> Dict[str, Any]:
    return {
        "type": "conclusive",
        "java_code": opt.optimized_code,
        "trace": val.trace,
        "why": val.why,
    }

def non_conclusive_agent(val: ValidateOutput) -> Dict[str, Any]:
    return {
        "type": "non_conclusive",
        "explanation": val.why,
        "recommendations": val.recommendations,
    }


# ------------------------- Orquestração -------------------------

def run_pipeline(
    java_path: Path,
    model: str = "gemma3:4b",
    evaluate: bool = False,
    threshold_ms: Optional[int] = None,
) -> Dict[str, Any]:
    original_code = read_text(java_path)

    # 1) Interpretar
    interp = interpreter_agent(model, original_code)

    # 2) Otimizar
    opt = optimize_agent(model, original_code, interp)

    # 3) (Opcional) Avaliar ambos
    metrics_original = None
    metrics_optimized = None
    if evaluate and _javac_available() and _java_available():
        metrics_original = _compile_and_run(original_code)
        metrics_optimized = _compile_and_run(opt.optimized_code)
    elif evaluate:
        # avaliação solicitada mas Java não disponível
        metrics_original = {"error": "javac/java indisponível no PATH"}
        metrics_optimized = {"error": "javac/java indisponível no PATH"}

    # 4) Validar
    val = validate_agent(
        model=model,
        original_code=original_code,
        opt=opt,
        interp=interp,
        metrics_original=metrics_original,
        metrics_optimized=metrics_optimized,
        threshold_ms=threshold_ms,
    )

    # 5) Roteamento final
    if val.status == "conclusive":
        final = conclusive_agent(opt, val)
    else:
        final = non_conclusive_agent(val)

    return {
        "final": final,
        "intermediate": {
            "interpreter": {"summary": interp.summary, "key_points": interp.key_points},
            "optimize": {"optimized_code": opt.optimized_code, "rationale": opt.rationale},
            "validate": {
                "status": val.status,
                "why": val.why,
                "trace": val.trace,
                "recommendations": val.recommendations,
            },
            "metrics": {
                "original": metrics_original,
                "optimized": metrics_optimized,
                "threshold_ms": threshold_ms,
            },
        },
    }


# ------------------------- CLI -------------------------

def main():
    parser = argparse.ArgumentParser(description="Pipeline completa de agentes para otimizar código Java (Edge AI).")
    parser.add_argument("--java-file", type=str, default="test/Test02.java", help="Caminho do arquivo .java de entrada")
    parser.add_argument("--model", type=str, default="gemma3:4b", help="Modelo do Ollama (ex.: gemma3:4b)")
    parser.add_argument("--out-dir", type=str, default="artifacts", help="Diretório para salvar as saídas")
    parser.add_argument("--evaluate", action="store_true", help="Avaliar com javac/java (compilação e execução)")
    parser.add_argument("--threshold-ms", type=int, default=None, help="Threshold (ms) para ajudar a validação")
    args = parser.parse_args()

    java_path = Path(args.java_file)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    result = run_pipeline(
        java_path=java_path,
        model=args.model,
        evaluate=args.evaluate,
        threshold_ms=args.threshold_ms,
    )

    # Salva JSON completo
    json_path = out_dir / "pipeline_output.json"
    write_text(json_path, json.dumps(result, ensure_ascii=False, indent=2))

    final = result["final"]
    if final["type"] == "conclusive":
        # Tenta extrair o nome da classe para salvar como .java com nome adequado
        class_name = extract_public_class_name(final["java_code"]) or "Optimized"
        java_out = out_dir / f"{class_name}.java"
        write_text(java_out, final["java_code"])
        print(f"[OK] Conclusivo. Código otimizado salvo em: {java_out}")
        print(f"[TRACE] {' | '.join(final.get('trace', []))}")
    else:
        print("[INFO] Não conclusivo.")
        print(f"Explicação: {final.get('explanation', '')}")
        if final.get("recommendations"):
            print("Recomendações:")
            for rec in final["recommendations"]:
                print(f" - {rec}")

    print(f"Relatório completo: {json_path}")


if __name__ == "__main__":
    main()
