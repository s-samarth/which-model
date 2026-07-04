"""Knowledge-base retrieval: Retriever protocol + BM25 implementation."""

from whichmodel.retrieval.base import KBDoc, Retriever
from whichmodel.retrieval.bm25 import BM25Retriever
from whichmodel.retrieval.embedding import EmbeddingRetriever
from whichmodel.retrieval.hybrid import HybridRetriever, build_retriever
from whichmodel.retrieval.loader import load_kb

__all__ = ["KBDoc", "Retriever", "BM25Retriever", "EmbeddingRetriever",
           "HybridRetriever", "build_retriever", "load_kb"]
