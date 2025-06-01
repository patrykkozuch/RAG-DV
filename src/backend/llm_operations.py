"""
This module contains LLM operations for the RAG system.
"""
import time
from typing import List, Dict, Any, Optional

from .message import Message
from .llm_node import LLMNode
from .document_operations import DocumentManager


class RAGSystem:

    def __init__(
        self,
        llm_base_url: str = "http://localhost:8080",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        self.llm_node = LLMNode(llm_base_url)
        self.document_manager = DocumentManager(embedding_model=embedding_model)
        self.chat_history: List[Message] = []


        self.chat_history.append(
            Message(
                role="system",
                content="You are an assistant with RAG capabilities. When provided with context from documents, use that information to enhance your responses."
            )
        )

    def initialize_documents(self, directory_path: str = "documents") -> Dict[str, Any]:
        return self.document_manager.initialize_from_directory(directory_path)


def query_llm(query: str, use_rag: bool = True) -> Message:
    global _rag_system
    if '_rag_system' not in globals():
        _rag_system = RAGSystem()

    start_time = time.time()

    user_message = Message(role="user", content=query)
    _rag_system.chat_history.append(user_message)

    sources = []
    enhanced_query = query

    if use_rag:
        relevant_docs = _rag_system.document_manager.search_documents(query, top_k=3)

        if relevant_docs:
            context_parts = []
            for i, doc in enumerate(relevant_docs):
                context_parts.append(f"Document {i+1}: {doc.content}")
                sources.append({
                    "id": doc.id,
                    "file_name": doc.meta["file_name"],
                    "metadata": doc.meta,
                    "relevance": 1.0 - (i * 0.1)
                })

            context = "\n\n".join(context_parts)
            enhanced_query = f"""Context from relevant documents:
                            {context}
                            
                            Based on the above context, please answer the following question:
                            {query}"""

    messages = []
    for msg in _rag_system.chat_history[-5:]:
        if msg.role != "user" or msg.content != query:
            messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": enhanced_query})

    response = _rag_system.llm_node.chat_completion(messages)


    response.sources = sources
    if not response.processing_time:
        response.processing_time = round(time.time() - start_time, 2)

    _rag_system.chat_history.append(response)

    return response


def get_chat_history() -> List[Message]:
    global _rag_system
    if '_rag_system' not in globals():
        _rag_system = RAGSystem()
        _rag_system.initialize_documents()

    return _rag_system.chat_history.copy()