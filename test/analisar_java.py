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
