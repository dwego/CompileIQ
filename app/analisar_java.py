import subprocess
import time
import os
import re


def remover_ansi(texto):
    """Remove caracteres de controle ANSI, incluindo spinners"""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", texto)


def interpreter_agent(prompt: str, model: str = "gemma3:4b", timeout: int = 300):
    try:
        print("[INFO] Iniciando execução do modelo Ollama...")
        start_time = time.time()

        process = subprocess.Popen(
            ["ollama", "run", model],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )

        output, error = process.communicate(prompt, timeout=timeout)
        elapsed = time.time() - start_time
        print(f"[INFO] Modelo finalizado em {elapsed:.2f}s")

        if process.returncode != 0:
            raise Exception(f"Ollama retornou erro: {remover_ansi(error)}")

        output = remover_ansi(output)
        return output

    except subprocess.TimeoutExpired:
        process.kill()
        print("[ERRO] Execução do modelo excedeu o tempo limite!")
        return None
    except Exception as e:
        print(f"[ERRO] {e}")
        return None


def analisar_java(log_java_filepath: str, java_filepath: str):
    if not os.path.exists(java_filepath):
        raise FileNotFoundError(f"Arquivo não encontrado: {java_filepath}")
    if not os.path.exists(log_java_filepath):
        raise FileNotFoundError(f"Arquivo de log não encontrado: {log_java_filepath}")

    print("[INFO] Lendo código Java...")
    with open(java_filepath, "r", encoding="utf-8") as f:
        conteudo_arquivo_java = f.read()

    print("[INFO] Lendo XML de execução...")
    with open(log_java_filepath, "r", encoding="utf-8") as f:
        conteudo_log_xml = f.read()

    print("[INFO] Montando prompt para IA...")
    prompt = f"""
        Você é um especialista em Java.
        Analise o seguinte código e explique seu funcionamento,
        principais classes, métodos e lógica.

        Além disso, considere os tempos de compilação e execução
        para avaliar a eficiência do programa e sugerir possíveis otimizações.

        Código Java:
        {conteudo_arquivo_java}

        Logs de execução XML:
        {conteudo_log_xml}
    """

    print("[INFO] Enviando prompt para o modelo...")
    resposta = interpreter_agent(prompt, model="gemma3:4b", timeout=600)  # 10 min de timeout

    if resposta is None:
        print("[ERRO] A análise não pôde ser concluída.")
    else:
        print("[INFO] Análise concluída com sucesso.")

    return resposta


if __name__ == "__main__":
    arquivo_java = r"C:/Users/qchac/Documents/CompileIQ/test/Test02.java"
    arquivo_log_java_xml = r"C:/Users/qchac/Documents/CompileIQ/infos/log-java.txt"

    print("[INFO] Iniciando análise do código Java...")
    resultado = analisar_java(arquivo_log_java_xml, arquivo_java)

    if resultado:
        print("\n--- Análise do Código ---\n")
        print(resultado)

if __name__ == "__main__":
    # Raw string para caminhos Windows
    arquivo_java = r"C:\Users\qchac\Documents\CompileIQ\test\Test02.java"
    arquivo_log_java_xml = r"C:\Users\qchac\Documents\CompileIQ\test\log-java.txt"
    resultado = analisar_java(arquivo_log_java_xml, arquivo_java)
    print("\n--- Análise do Código ---\n")
    print(resultado)
