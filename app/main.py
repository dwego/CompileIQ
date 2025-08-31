import time
import os
import re
from langchain_ollama.llms import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings


def remover_ansi(texto: str) -> str:
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", texto)


def _build_retriever(persist_dir: str = "./chrome_langchain_db", k: int = 8):
    if not os.path.exists(persist_dir):
        return None
    embeddings = OllamaEmbeddings(model="mxbai-embed-large")
    vector_store = Chroma(
        collection_name="restaurant_reviews",
        persist_directory=persist_dir,
        embedding_function=embeddings,
    )
    return vector_store.as_retriever(search_kwargs={"k": k})


def _read_text(path: str, limit: int | None = 4000) -> str:
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    return data if limit is None else data[:limit]


def client(
    conteudo_arquivo_java: str,
    contexto_rag: str,
    conteudo_logs_csv: str,
    model_name: str = "gemma3:4b",
) -> str:
    print("[INFO] Iniciando execução do modelo Ollama...")
    start_time = time.time()

    model = OllamaLLM(model=model_name)

    template = """
        Você é um especialista em Java.
        Analise o seguinte código e explique seu funcionamento,
        principais classes, métodos e lógica.

        Além disso, considere os tempos de compilação e execução
        para avaliar a eficiência do programa e sugerir possíveis otimizações.

        Use o CONTEXTO recuperado via RAG (fragmentos indexados dos CSVs) e,
        se necessário, os trechos brutos dos CSVs.

        Responda sempre em PT-br.

        [CONTEXTO RAG]
        {contexto_rag}

        [TRECHOS BRUTOS CSVs]
        {conteudo_logs_csv}

        [CÓDIGO JAVA]
        {conteudo_arquivo_java}
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | model

    try:
        result = chain.invoke(
            {
                "conteudo_arquivo_java": conteudo_arquivo_java,
                "contexto_rag": contexto_rag,
                "conteudo_logs_csv": conteudo_logs_csv,
            }
        )
        elapsed = time.time() - start_time
        print(f"[INFO] Modelo finalizado em {elapsed:.2f}s")

        output = getattr(result, "content", result)
        output = remover_ansi(str(output))
        return output

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[ERRO] Falha ao executar o modelo após {elapsed:.2f}s")
        raise e


def interpreter_agent(
    java_filepath: str,
    errors_csv: str,
    gc_events_csv: str,
    jit_compilation_csv: str,
    program_output_csv: str,
    summary_csv: str,
    model_name: str = "gemma3:4b",
) -> str:
    for p in [
        java_filepath,
        errors_csv,
        gc_events_csv,
        jit_compilation_csv,
        program_output_csv,
        summary_csv,
    ]:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Arquivo não encontrado: {p}")

    print("[INFO] Lendo código Java...")
    conteudo_arquivo_java = _read_text(java_filepath, limit=8000)

    print("[INFO] Lendo CSVs...")
    erros_txt = _read_text(errors_csv, limit=4000)
    gc_txt = _read_text(gc_events_csv, limit=4000)
    jit_txt = _read_text(jit_compilation_csv, limit=4000)
    prog_out_txt = _read_text(program_output_csv, limit=4000)
    summary_txt = _read_text(summary_csv, limit=2000)

    conteudo_logs_csv = (
        "== errors.csv ==\n" + erros_txt + "\n\n"
        "== gc_events.csv ==\n" + gc_txt + "\n\n"
        "== jit_compilation.csv ==\n" + jit_txt + "\n\n"
        "== program_output.csv ==\n" + prog_out_txt + "\n\n"
        "== summary.csv ==\n" + summary_txt
    )

    print("[INFO] Recuperando contexto via RAG (Chroma)...")
    retriever = _build_retriever()
    contexto_rag = ""
    if retriever:
        # query simples baseada no código e intenção de performance/GC/JIT
        query = (
            "Análise de performance de compilação/execução em Java, erros, GC e JIT. Código (trecho): "
            + conteudo_arquivo_java[:800]
        )
        docs = retriever.get_relevant_documents(query)
        partes = []
        for d in docs:
            src = d.metadata.get("source", "desconhecido")
            partes.append(f"[{src}] {d.page_content}")
        contexto_rag = "\n---\n".join(partes)
    else:
        print(
            "[AVISO] Base Chroma não encontrada em ./chrome_langchain_db. Prosseguindo sem RAG."
        )

    resposta = client(
        conteudo_arquivo_java=conteudo_arquivo_java,
        contexto_rag=contexto_rag,
        conteudo_logs_csv=conteudo_logs_csv,
        model_name=model_name,
    )

    if not resposta:
        print("[ERRO] A análise não pôde ser concluída.")
    else:
        print("[INFO] Análise concluída com sucesso.")

    return resposta


if __name__ == "__main__":
    base_dir = r"C:/Users/qchac/Documents/CompileIQ/test/"
    arquivo_java = os.path.join(base_dir, "Test02.java")

    errors_csv = os.path.join(base_dir, "errors.csv")
    gc_events_csv = os.path.join(base_dir, "gc_events.csv")
    jit_compilation_csv = os.path.join(base_dir, "jit_compilations.csv")
    program_output_csv = os.path.join(base_dir, "program_output.csv")
    summary_csv = os.path.join(base_dir, "summary.csv")

    print("[INFO] Iniciando análise do código Java...")
    resultado = interpreter_agent(
        java_filepath=arquivo_java,
        errors_csv=errors_csv,
        gc_events_csv=gc_events_csv,
        jit_compilation_csv=jit_compilation_csv,
        program_output_csv=program_output_csv,
        summary_csv=summary_csv,
        model_name="gemma3:4b",
    )

    if resultado:
        print("\n--- Análise do Código ---\n")
        print(resultado)
