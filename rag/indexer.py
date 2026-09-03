"""
RAG indexer — loads markdown docs from docs/ and indexes them into ChromaDB.
"""

import sys
from pathlib import Path

# Allow running directly as `python rag/indexer.py` as well as `python -m rag.indexer`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

from config_loader import env_or_default
from llm_provider import build_embeddings, load_llm_config


def build_index(
    docs_dir: str = "docs",
    persist_dir: str = "data/chroma",
    collection_name: str = "automotive_docs",
    embeddings: Embeddings | None = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> Chroma:
    docs_path = Path(docs_dir)
    loader = DirectoryLoader(
        str(docs_path),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    chunks = splitter.split_documents(documents)

    for chunk in chunks:
        source = Path(chunk.metadata.get("source", ""))
        chunk.metadata["doc_name"] = source.stem

    if embeddings is None:
        embeddings = build_embeddings(load_llm_config())

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=persist_dir,
    )
    return vectorstore


if __name__ == "__main__":
    load_dotenv()
    vs = build_index(
        docs_dir=env_or_default("DOCS_DIR"),
        persist_dir=env_or_default("CHROMA_PERSIST_DIR"),
    )
    print(f"Indexed {vs._collection.count()} chunks into ChromaDB")
