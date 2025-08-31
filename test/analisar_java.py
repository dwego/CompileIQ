import subprocess
import time
import os
import re

def remover_ansi(texto):
    """Remove caracteres de controle ANSI, incluindo spinners"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', texto)

def ask_ollama(prompt: str, model: str = "gemma3:4b"):
    """
    Executa o modelo via Ollama e retorna a resposta limpa.
    Corrige Unicode e spinners do terminal.
    """
    process = subprocess.Popen(
        ["ollama", "run", model],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8"
    )
    output, error = process.communicate(prompt)

    # Levantar exceção só se o processo falhou
    if process.returncode != 0:
        raise Exception(f"Ollama retornou erro: {remover_ansi(error)}")

    # Limpar ANSI da saída para evitar spinners
    output = remover_ansi(output)
    return output

def medir_tempo_java(filepath: str):
    """
    Compila e executa um arquivo Java, retornando tempos e saída.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")

    # Compilação
    inicio_compilacao = time.time()
    compilar = subprocess.run(
        ["javac", filepath],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    fim_compilacao = time.time()
    tempo_compilacao = fim_compilacao - inicio_compilacao

    if compilar.returncode != 0:
        return {"erro": f"Erro de compilação:\n{compilar.stderr}"}

    # Execução
    classe = os.path.splitext(os.path.basename(filepath))[0]
    inicio_execucao = time.time()
    executar = subprocess.run(
        ["java", classe],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    fim_execucao = time.time()
    tempo_execucao = fim_execucao - inicio_execucao

    return {
        "tempo_compilacao": tempo_compilacao,
        "tempo_execucao": tempo_execucao,
        "saida": executar.stdout,
        "erros": executar.stderr
    }

def analisar_java(filepath: str):
    """
    Analisa o código Java com Gemma via Ollama, incluindo tempos de execução.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        conteudo = f.read()

    resultado = medir_tempo_java(filepath)

    if "erro" in resultado:
        return resultado["erro"]

    prompt = f"""
Você é um especialista em Java.
Analise o seguinte código e explique seu funcionamento,
principais classes, métodos e lógica.

Além disso, considere os tempos de compilação e execução
para avaliar a eficiência do programa e sugerir possíveis otimizações.

Código:
{conteudo}

Tempo de compilação: {resultado['tempo_compilacao']:.4f} segundos
Tempo de execução: {resultado['tempo_execucao']:.4f} segundos
Saída do programa:
{resultado['saida']}
"""
    resposta = ask_ollama(prompt, model="gemma3:4b")
    return resposta

if __name__ == "__main__":
    # Raw string para caminhos Windows
    arquivo_java = r"C:\Users\qchac\Documents\CompileIQ\test\Test02.java"
    resultado = analisar_java(arquivo_java)
    print("\n--- Análise do Código ---\n")
    print(resultado)
