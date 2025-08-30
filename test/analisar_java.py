import subprocess
import json
import os

def ask_ollama(prompt: str, model: str = "gemma3:4b"):
    """Executa o Ollama via subprocess e retorna a saída do modelo"""
    process = subprocess.Popen(
        ["ollama", "run", model],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    output, error = process.communicate(prompt)

    if error:
        raise Exception(f"Erro no Ollama: {error}")
    return output

def analisar_java(filepath: str):
    """Lê o arquivo Java e envia para análise no modelo"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        conteudo = f.read()

    prompt = f"""
Você é um especialista em Java. Analise o seguinte código e explique seu funcionamento,
principais classes, métodos e lógica:

{conteudo}
"""
    resposta = ask_ollama(prompt, model="gemma3:4b")
    return resposta


if __name__ == "__main__":
    arquivo_java = "Test01.java"  # ajuste o caminho do arquivo aqui
    resultado = analisar_java(arquivo_java)
    print("\n--- Análise do Código ---\n")
    print(resultado)

