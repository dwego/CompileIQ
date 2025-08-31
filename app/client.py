from ollama import chat
from ollama import ChatResponse
import xml_java.xml_java as xml_java
import json

codigos_java = []
time_limit_ms_global = 0
class_name = ""

import re
import json

def safe_json_loads(text: str):
    import re, json

    # Remove blocos markdown ```json ... ```
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```", "", text)

    # Extrai o primeiro bloco { ... }
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("Nenhum JSON válido encontrado na resposta do modelo.")
    json_str = match.group(0)

    # Corrige chave errada
    json_str = json_str.replace("soluções", "solucoes")

    # Remove concatenação estilo JS
    json_str = re.sub(r'"\s*\+\s*"', '', json_str)

    # Escapa aspas dentro de código Java no campo codigo_java
    # Transforma:  System.out.print(i + " ");
    # em:         System.out.print(i + \" \");
    json_str = re.sub(r'(?<=\+) "(.*?)"', lambda m: ' \\"' + m.group(1) + '\\"', json_str)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print("JSON bruto que falhou:\n", json_str)
        raise e




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
                "tempo_execucao_estimado": "Hipótese curta sobre a ordem de grandeza do tempo de execução (ex: rápido, médio, lento, depende do tamanho da entrada)",
                "pontos_ruins": ["Liste de forma curta possíveis gargalos, riscos ou más práticas"],
                "metricas_otimizacao": ["Sugira melhorias rápidas de desempenho ou eficiência"],
                "observacoes": ["Outros insights relevantes de forma bem resumida"]
                }

                Responda SOMENTE em JSON válido, sem explicações adicionais.

                REGRAS:
                - Se o código estiver vazio ou não for Java, responda com um JSON vazio: {}
                - Não repita informaçoes, e englobe as informaçoes realmente necessarias para a validação de analise estatica
                - Seja conciso e objetivo

                Responda sempre em PT-br.
                """,
            },
            {
                "role": "user",
                "content": f"{java_file_content}"
            },
        ],
        options={"temperature": 0.2},
    )

    print(resp.message.content)

    dinamic_agent(java_filepath, "Test01", resp.message.content)

def dinamic_agent(java_filepath: str, class_name: str, about_code: str):
    xml_path = xml_java.run_java_analysis(java_filepath, class_name)

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
                - Um XML contendo informações de execução (profiling, logs, métricas).
                - Um JSON anterior com hipóteses da análise estática.

                Tarefa:
                1. Ler o XML e identificar métricas principais (tempo, CPU, memória, GC, IO, threads).
                2. Comparar com o JSON anterior e indicar quais hipóteses foram confirmadas ou não.
                3. Destacar pontos críticos da execução, incluindo gargalos e comportamentos inesperados.
                4. Produzir um resumo FINAL **somente em JSON válido e em português**.

                Regras obrigatórias:
                - Não escreva texto explicativo fora do JSON.
                - Use apenas português nas chaves e nos valores.
                - Estrutura do JSON:
                - Precisa retornar o tempo de execução total que esta no XML

                {
                "tempo_execucao": "Resumo em português do tempo total de execução e principais variações observadas",
                "uso_memoria": "Resumo em português do consumo de memória durante a execução",
                "pontos_criticos_execucao": [
                    "Métodos, classes ou blocos que apresentaram gargalos"
                ],
                "confirmacao_estatica": [
                    "Quais objeções levantadas pela análise estática se confirmaram"
                ],
                "novos_problemas": [
                    "Problemas detectados apenas na execução dinâmica"
                ],
                "sugestoes_otimizacao": [
                    "Sugestões de otimização baseadas nos dados de execução"
                ],
                "metricas_execucao": {
                    "cpu_percentual": "Média ou pico de uso de CPU em %",
                    "memoria_mb": "Pico de uso de memória em MB",
                    "threads_ativas": "Número de threads ativas",
                    "tempo_gc": "Tempo gasto com Garbage Collector em ms"
                },
                "observacoes": [
                    "Outros insights relevantes"
                ]
                }

                Responda SOMENTE com esse JSON e nada mais.
                """,
            },
            {
                "role": "user",
                "content": f"INFORMACOES DE EXECUCAO: \n{xml_file_content}\n\nHIPOTESES ESTATICAS: \n{about_code}"
            },
        ],
        options={"temperature": 0.2},
    )

    print(resp.message.content)

    optimize_agent(java_filepath, resp.message.content, 190)

    return resp

def optimize_agent(java_filepath: str, exec_metrics: str, time_limit_ms: int):
    with open(java_filepath, "r", encoding="utf-8") as f:
        java_code = f.read()

    prompt = f""" 
    Você é um otimizador de código Java. 
    
    Entrada: 
        - Código original (Java). 
        - Métricas de execução (JSON ou XML resumido). 
        - Tempo limite de execução em ms: {time_limit_ms}. 
    Objetivo: 
        - Propor **3 versões diferentes** do código, cada uma explorando um caminho distinto de otimização (ex: paralelismo, algoritmos melhores, estruturas de dados mais eficientes, técnicas de caching, remoção de waits, etc). - Garantir que as soluções respeitem o tempo limite estimado. - Produzir saídas somente em JSON válido, com o seguinte formato: {{ "solucoes": [ {{ "descricao": "Explicação curta do que foi otimizado", "codigo_java": "Código Java completo otimizado" }}, {{ "descricao": "Outra abordagem diferente", "codigo_java": "Outro código Java completo" }}, {{ "descricao": "Terceira abordagem diferente", "codigo_java": "Terceiro código Java completo" }} ] }} Regras: - Use apenas PT-BR nos textos descritivos. - Os códigos Java devem estar **completos, prontos para compilar e rodar**. - Não repita a mesma técnica em mais de uma solução. - Evite comentários longos, apenas se forem essenciais. - Foco em otimização de tempo de execução, respeitando o limite de {time_limit_ms}ms.
 """

    resp = chat(
        model="qwen2.5-coder:1.5b",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"CÓDIGO ORIGINAL:\n{java_code}\n\nMÉTRICAS DE EXECUÇÃO:\n{exec_metrics}"}
        ],
        options={"temperature": 0.4},
    )

    filter_response = resp.message.content

    print(filter_response)

    try:
        parsed = safe_json_loads(filter_response)
    except Exception as e:
        print("Erro ao converter JSON:", e)
        return

    parsed = safe_json_loads(filter_response)
    solucoes = parsed["solucoes"]

    for sol in solucoes:
        codigo = sol["codigo_java"]
        # Decodifica \n em quebras de linha reais
        codigo = codigo.encode().decode("unicode_escape")
        codigos_java.append(codigo.strip())


    global time_limit_ms_global
    time_limit_ms_global = time_limit_ms
    conclusive_agent()

def validate_code():
    execution_times = []
    for i in range(len(codigos_java)):
        filepath = r"C:\Users\qchac\Documents\CompileIQ\test\\" + class_name + ".java"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(codigos_java[i])
        execution_times.append({filepath: test_execution_time(filepath, class_name)})

    best = min(
        execution_times,
        key=lambda x: list(x.values())[0]  # pega o valor (tempo) de cada dict
    )

    # best vai ser algo tipo {"TestCode2": 87}
    best_filepath = list(best.keys())[0]
    best_time = list(best.values())[0]

    return best_filepath, best_time
    

def test_execution_time(filepath: str, class_name: str):
    xml_path = xml_java.run_java_analysis(filepath, class_name)

    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Exemplo: suponha que você queira pegar o campo <executionTime>
    return root.findtext(".//executionTimeSec")



def conclusive_agent():
    best_filepath, best_time = validate_code()
    if best_time < time_limit_ms_global:
        print(f"Melhor código encontrado em {best_filepath} com tempo de {best_time}ms")
    else:
        non_conclusive_agent()


def non_conclusive_agent():
    print("Nenhum código conseguiu atingir o tempo limite.")
    print("Melhor código gerado foi:")


# Executa o agente principal
interpreter_agent(r"C:\Users\qchac\Documents\CompileIQ\test\Test01.java")
