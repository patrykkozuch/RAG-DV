import os
from datetime import time
from typing import List, Optional, Dict, Any
from pathlib import Path

from haystack import Document, Pipeline, logging
from haystack.components.converters import TextFileToDocument
from haystack.components.preprocessors import DocumentSplitter, DocumentCleaner
from haystack.components.writers import DocumentWriter
from haystack.components.embedders import SentenceTransformersDocumentEmbedder, SentenceTransformersTextEmbedder
from haystack.components.retrievers import InMemoryEmbeddingRetriever
from haystack.document_stores.in_memory import InMemoryDocumentStore


class DocumentManager:
    def __init__(
        self,
        document_store: Optional[InMemoryDocumentStore] = None,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        self.document_store = document_store or InMemoryDocumentStore()
        self.embedding_model = embedding_model


        self.text_converter = TextFileToDocument()
        # self.cleaner = DocumentCleaner(
        #     remove_empty_lines=True,
        #     remove_extra_whitespaces=True,
        #     remove_repeated_substrings=False
        # )
        # self.splitter = DocumentSplitter(
        #     split_by="sentence",
        #     split_length=3,
        #     split_overlap=1
        # )
        self.embedder = SentenceTransformersDocumentEmbedder(
            model=embedding_model,
            progress_bar=True
        )
        self.writer = DocumentWriter(document_store=self.document_store)


        self.processing_pipeline = Pipeline()
        #self.processing_pipeline.add_component("cleaner", self.cleaner)
        #self.processing_pipeline.add_component("splitter", self.splitter)
        self.processing_pipeline.add_component("embedder", self.embedder)
        self.processing_pipeline.add_component("writer", self.writer)


        #self.processing_pipeline.connect("cleaner", "splitter")
        #self.processing_pipeline.connect("splitter", "embedder")
        self.processing_pipeline.connect("embedder", "writer")


        self.text_embedder = SentenceTransformersTextEmbedder(model=embedding_model)
        self.retriever = InMemoryEmbeddingRetriever(document_store=self.document_store)

        self.search_pipeline = Pipeline()
        self.search_pipeline.add_component("text_embedder", self.text_embedder)
        self.search_pipeline.add_component("retriever", self.retriever)
        self.search_pipeline.connect("text_embedder.embedding", "retriever.query_embedding")

    def get_documents(self) -> List[Document]:
        return self.document_store.filter_documents()

    def list_documents(self) -> List[Dict[str, Any]]:
        documents = self.get_documents()
        doc_list = []
        for doc in documents:
            metadata = doc.meta
            doc_info = {
                "id": doc.id,
                "file_name": metadata["file_name"],
                "file_size": metadata["file_size"],
                "file_type": metadata["file_type"],
            }
            doc_list.append(doc_info)

        return doc_list

    def upload_document(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> dict[str, Any]:
        document = Document(content=content, meta=metadata or {})
        metadata["id"] = document.id
        document_ret = self.processing_pipeline.run({"documents": [document]})

        if document_ret:
            return metadata


    def delete_document(self, document_id: str) -> None:
        self.document_store.delete_documents([document_id])


    def get_document_count(self) -> int:
        return self.document_store.count_documents()



    def search_documents(self, query: str, top_k: int = 5) -> List[Document]:
        result = self.search_pipeline.run({
            "text_embedder": {"text": query},
            "retriever": {"top_k": top_k}
        })
        return result["retriever"]["documents"]


    def get_document_content(self, doc_id: str) -> Optional[Document]:
        docs = self.document_store.filter_documents(filters={"field": "id", "operator": "==", "value": doc_id})
        return docs[0].content

    def get_document(self, doc_id: str) -> Optional[Document]:
        docs = self.document_store.filter_documents(filters={"field": "id", "operator": "==", "value": doc_id})
        return docs[0] if docs else None

    def initialize_from_directory(self, directory_path: str = "documents"):
        directory = Path(directory_path)
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            return []

        for file_path in directory.iterdir():
            if file_path.is_file():
                file_content = file_path.read_text(encoding='utf-8')

                metadata = {
                    "file_name": file_path.name,
                    "file_type": file_path.suffix,
                    "file_size": file_path.stat().st_size
                }

                self.upload_document(file_content, metadata)




