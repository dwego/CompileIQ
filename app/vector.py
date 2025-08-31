from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import os
import pandas as pd

errors_df = pd.read_csv("errors.csv")
gc_events_df = pd.read_csv("gc_events.csv")
jit_compilation_df = pd.read_csv("jit_compilation.csv")
program_output_df = pd.read_csv("program_output.csv")
summary_df = pd.read_csv("summary.csv")

embeddings = OllamaEmbeddings(model="mxbai-embed-large")

db_location = "./chrome_langchain_db"
add_documents = not os.path.exists(db_location)

if add_documents:
    documents = []
    ids = []

    for i, row in errors_df.iterrows():
        document = Document(
            page_content=f"error_type: {row['error_type']} | message: {row['message']} | frame_index: {row['frame_index']} | frame_text: {row['frame_text']}",
            metadata={"source": "errors.csv"},
            id=f"errors-{i}",
        )
        ids.append(f"errors-{i}")
        documents.append(document)

    for i, row in gc_events_df.iterrows():
        document = Document(
            page_content=f"index: {row['index']} | detail: {row['detail']}",
            metadata={"source": "gc_events.csv"},
            id=f"gc_events-{i}",
        )
        ids.append(f"gc_events-{i}")
        documents.append(document)

    for i, row in jit_compilation_df.iterrows():
        document = Document(
            page_content=(
                f"method: {row['method']} | compilations: {row['compilations']} | "
                f"total_bytes: {row['total_bytes']} | comp_id: {row['comp_id']} | "
                f"level: {row['level']} | bytes: {row['bytes']} | special: {row['special']}"
            ),
            metadata={"source": "jit_compilation.csv"},
            id=f"jit_compilation-{i}",
        )
        ids.append(f"jit_compilation-{i}")
        documents.append(document)

    for i, row in program_output_df.iterrows():
        document = Document(
            page_content=f"line_no: {row['line_no']} | text: {row['text']}",
            metadata={"source": "program_output.csv"},
            id=f"program_output-{i}",
        )
        ids.append(f"program_output-{i}")
        documents.append(document)

    for i, row in summary_df.iterrows():
        document = Document(
            page_content=(
                f"execution_time_ms: {row['execution_time_ms']} | total_gc_events: {row['total_gc_events']} | "
                f"total_methods: {row['total_methods']} | total_errors: {row['total_errors']} | "
                f"timestamp: {row['timestamp']}"
            ),
            metadata={"source": "summary.csv"},
            id=f"summary-{i}",
        )
        ids.append(f"summary-{i}")
        documents.append(document)

vector_store = Chroma(
    collection_name="logs",
    persist_directory=db_location,
    embedding_function=embeddings,
)

if add_documents:
    vector_store.add_documents(documents=documents, ids=ids)

retriever = vector_store.as_retriever(search_kwargs={"k": 5})
