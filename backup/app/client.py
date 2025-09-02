from ollama import chat
from ollama import ChatResponse
import xml_java.xml_java as xml_java
import xml.etree.ElementTree as ET
import re

codigos_java = []
time_limit_ms_global = 0


def interpreter_agent(java_filepath: str) -> ChatResponse:
    with open(java_filepath, "r", encoding="utf-8") as f:
        java_file_content = f.read()

    resp = chat(
        model="qwen2.5-coder:1.5b",
        messages=[
            {
                "role": "system",
                "content": """
                Você é um analisador estático de código Java.
                Leia o código fornecido e produza um JSON com as seguintes chaves:

                {
                  "tempo_execucao_estimado": "...",
                  "pontos_ruins": ["..."],
                  "metricas_otimizacao": ["..."],
                  "observacoes": ["..."]
                }

                Regras:
                - Se o código estiver vazio ou não for Java, responda com {}
                - Não repita informações
                - Seja conciso e objetivo
                - Responda sempre em PT-br
                """,
            },
            {"role": "user", "content": f"{java_file_content}"},
        ],
        options={"temperature": 0.2},
    )

    print(resp.message.content)
    dinamic_agent(java_filepath, "Test01", resp.message.content)


def dinamic_agent(java_filepath: str, class_name: str, about_code: str):
    xml_path = xml_java.run_java_analysis(java_filepath, class_name)
    print(f"[LOG] XML gerado em: {xml_path}")

    with open(xml_path, "r", encoding="utf-8") as f:
        xml_file_content = f.read()

    resp = chat(
        model="qwen2.5-coder:1.5b",
        messages=[
            {
                "role": "system",
                "content": """
                Você é um analisador dinâmico de código Java.

                Entrada:
                - Um XML contendo informações de execução.
                - Um JSON anterior da análise estática.

                Tarefa:
                1. Ler o XML e extrair métricas principais.
                2. Comparar com hipóteses anteriores.
                3. Destacar gargalos e problemas.
                4. Retornar **somente JSON válido em português**.

                Estrutura do JSON:
                {
                  "tempo_execucao": "...",
                  "uso_memoria": "...",
                  "pontos_criticos_execucao": ["..."],
                  "confirmacao_estatica": ["..."],
                  "novos_problemas": ["..."],
                  "sugestoes_otimizacao": ["..."],
                  "metricas_execucao": {
                    "cpu_percentual": "...",
                    "memoria_mb": "...",
                    "threads_ativas": "...",
                    "tempo_gc": "..."
                  },
                  "observacoes": ["..."]
                }
                """,
            },
            {
                "role": "user",
                "content": f"INFORMACOES DE EXECUCAO:\n{xml_file_content}\n\nHIPOTESES ESTATICAS:\n{about_code}",
            },
        ],
        options={"temperature": 0.2},
    )

    print(resp.message.content)
    optimize_agent(java_filepath, resp.message.content, 190)
    return resp


def optimize_agent(java_filepath: str, exec_metrics: str, time_limit_ms: int):
    global codigos_java

    with open(java_filepath, "r", encoding="utf-8") as f:
        java_code = f.read()

    prompt = f"""
    Você é um otimizador de código Java.
    Entrada:
    - Código original (Java).
    - Métricas de execução (XML resumido).
    - Tempo limite: {time_limit_ms} ms.

    Objetivo:
    - Propor 3 versões diferentes do código, explorando otimizações distintas.
    - Garantir que respeitem o tempo limite.
    - Retornar SOMENTE no formato exigido.
    """

    resp = chat(
        model="qwen2.5-coder:1.5b",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"CÓDIGO ORIGINAL:\n{java_code}\n\n\n{exec_metrics}"},
        ],
        options={"temperature": 0.3},
    )

    raw = resp.message.content or ""
    print("Resposta bruta do modelo:\n", raw)

    padrao = re.compile(
        r"###\s*SOLU(?:C|Ç)AO\s*\d+\s*?\r?\n\s*DESCRICAO:\s*(.*?)\r?\n```java\r?\n(.*?)\r?\n```",
        re.IGNORECASE | re.DOTALL,
    )
    matches = padrao.findall(raw)

    if not matches:
        code_fence = re.compile(r"```java\r?\n(.*?)\r?\n```", re.DOTALL | re.IGNORECASE)
        blocks = code_fence.findall(raw)
        descricoes = ["(sem descrição)"] * len(blocks)
        matches = list(zip(descricoes, blocks))

    codigos_java = []
    for desc, code in matches[:3]:
        cleaned = code.strip()
        if "class " not in cleaned:
            cleaned = (
                "public class Test01 {\n"
                " public static void main(String[] args) {\n"
                " // TODO: chame seu método aqui\n"
                " }\n"
                f"{cleaned}\n"
                "}\n"
            )
        codigos_java.append(cleaned)

    global time_limit_ms_global
    time_limit_ms_global = time_limit_ms
    conclusive_agent()


def validate_code():
    execution_times = []

    for i in range(len(codigos_java)):
        class_name = f"TestHardCode{i+1}"
        filepath = fr"C:\Users\qchac\Documents\CompileIQ\test\{class_name}.java"

        codigo = codigos_java[i]
        codigo_modificado = replace_class_name(codigo, class_name)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(codigo_modificado)

        tempo_ms, xml_path = test_execution_time(filepath, class_name)
        print(f"[LOG] Código {i+1} ({class_name}) executou em {tempo_ms}ms")
        execution_times.append({filepath: tempo_ms})

    best = min(execution_times, key=lambda x: list(x.values())[0])
    best_filepath = list(best.keys())[0]
    best_time = list(best.values())[0]
    print(f"[LOG] Melhor até agora: {best_filepath} com {best_time}ms")

    return best_filepath, best_time


def replace_class_name(codigo: str, novo_nome: str) -> str:
    return re.sub(r"(public\s+class\s+|class\s+)\w+", r"\1" + novo_nome, codigo, count=1)


def test_execution_time(filepath: str, class_name: str):
    

    xml_path = xml_java.run_java_analysis(filepath, class_name)
    tree = ET.parse(xml_path)
    root = tree.getroot()
    val = root.findtext(".//executionTimeSec")

    if val is None:
        print(f"[LOG] Arquivo {filepath} não retornou tempo de execução no XML.")
        return 0

    try:
        tempo_ms = int(float(val) * 1000)
        print(f"[LOG] Tempo reportado no XML para {class_name}: {tempo_ms}ms")
        return tempo_ms, xml_path
    except ValueError:
        print(f"[ERRO] Valor inválido no XML: {val}")
        return 0


def conclusive_agent():
    best_filepath, best_time = validate_code()

    if best_time < time_limit_ms_global:
        print(f"[RESULTADO] Melhor código encontrado em {best_filepath} com tempo de {best_time}ms ✅")
    else:
        print(f"[RESULTADO] Nenhum código atingiu o limite de {time_limit_ms_global}ms ❌")
        non_conclusive_agent()


def non_conclusive_agent():
    print("[AVISO] Nenhuma solução conseguiu atingir o tempo limite.")
    print("[INFO] Melhor código gerado foi (mas não atingiu a meta):")
    interpreter_agent(r"C:\Users\qchac\Documents\CompileIQ\test\Test01.java")

if __name__ == "__main__":
    java_file = r"C:\Users\qchac\Documents\CompileIQ\test\Test01.java"

    print("[INICIO] Rodando análise estática e dinâmica no código base...")
    interpreter_agent(java_file)

    print("[FIM] Processo concluído.")
