import os, shutil
from pathlib import Path
from functools import partial

from langchain_community.document_loaders import (
    PyPDFLoader,
    DirectoryLoader,
    TextLoader,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from PyPDF2 import PdfReader

DOCS_DIR = "./docs"
CHROMA_DB_DIR = "./chroma_db"
COLLECTION_NAME = "langchain"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def get_pdf_title(file_path: str) -> str:
    try:
        reader = PdfReader(file_path)
        title = getattr(reader.metadata, "title", None)
        if title:
            return str(title).strip()
    except Exception:
        pass
    return os.path.basename(file_path)


def load_docs():
    docs = []

    # PDFs
    pdf_files = list(Path(DOCS_DIR).rglob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF(s).")
    for file in pdf_files:
        loader = PyPDFLoader(str(file))
        pdf_docs = loader.load()
        title = get_pdf_title(str(file))
        for d in pdf_docs:
            d.metadata["source"] = str(file)
            d.metadata["title"] = title
            docs.append(d)

    # TXTs
    txt_loader = DirectoryLoader(
        DOCS_DIR, glob="**/*.txt", loader_cls=partial(TextLoader, encoding="utf-8")
    )
    txt_docs = txt_loader.load()
    print(f"Found {len(txt_docs)} TXT doc(s).")
    for d in txt_docs:
        src = d.metadata.get("source") or d.metadata.get("file_path") or "unknown.txt"
        d.metadata["source"] = src
        d.metadata["title"] = os.path.basename(src)
        docs.append(d)

    print(f"Total raw docs: {len(docs)}")
    return docs


def main():
    if not os.path.isdir(DOCS_DIR):
        raise SystemExit(f"Docs dir not found: {DOCS_DIR}")

    docs = load_docs()

    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
    splits = splitter.split_documents(docs)
    for s in splits:
        s.metadata.setdefault("source", s.metadata.get("file_path", "unknown"))
        s.metadata.setdefault(
            "title", os.path.basename(s.metadata.get("source", "unknown"))
        )
    print(f"Loaded and split into {len(splits)} chunks.")

    # Fresh rebuild
    if os.path.exists(CHROMA_DB_DIR):
        shutil.rmtree(CHROMA_DB_DIR)

    # Embeddings
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

    # Create the vector store, then add documents in batches (reliable across versions)
    vectordb = Chroma(
        persist_directory=CHROMA_DB_DIR,
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME,
    )

    batch = 500
    total = len(splits)
    for i in range(0, total, batch):
        chunk = splits[i : i + batch]
        vectordb.add_documents(chunk)
        print(f"Indexed {min(i+batch, total)}/{total}")

    print("ChromaDB rebuilt successfully.")


if __name__ == "__main__":
    main()
PY
