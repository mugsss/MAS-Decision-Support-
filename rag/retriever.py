"""
RAG retriever — loads the ChromaDB collection and provides a retriever interface.
"""

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from llm_provider import build_embeddings, load_llm_config


class RAGRetriever:
    def __init__(
        self,
        persist_dir: str = "data/chroma",
        collection_name: str = "automotive_docs",
        embeddings: Embeddings | None = None,
        top_k: int = 3,
        relevance_threshold: float = 0.3,
    ):
        self.top_k = top_k
        self.relevance_threshold = relevance_threshold

        if embeddings is None:
            embeddings = build_embeddings(load_llm_config())

        self.vectorstore = Chroma(
            collection_name=collection_name,
            persist_directory=persist_dir,
            embedding_function=embeddings,
        )

    def retrieve(self, query: str) -> tuple[list[Document], bool]:
        results = self.vectorstore.similarity_search_with_relevance_scores(
            query, k=self.top_k
        )
        docs = []
        low_relevance = True
        for doc, score in results:
            doc.metadata["relevance_score"] = score
            docs.append(doc)
            if score >= self.relevance_threshold:
                low_relevance = False

        if not results:
            low_relevance = True

        return docs, low_relevance
