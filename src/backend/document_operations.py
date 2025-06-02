import os
from datetime import time
from typing import List, Optional, Dict, Any
from pathlib import Path

from haystack import Document, Pipeline
from haystack.components.converters import TextFileToDocument
from haystack.components.preprocessors import DocumentSplitter, DocumentCleaner, RecursiveDocumentSplitter
from haystack.components.writers import DocumentWriter
from haystack.components.embedders import SentenceTransformersDocumentEmbedder, SentenceTransformersTextEmbedder
from haystack.dataclasses import ByteStream
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from haystack.components.converters import PyPDFToDocument

class DocumentManager:
    def __init__(
        self,
        qdrant_url: str,
        qdrant_collection: str = "documents",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        embedding_dim: Optional[int] = None
    ):
        self.document_store = QdrantDocumentStore(
            url=qdrant_url,
            index=qdrant_collection,
            embedding_dim=embedding_dim,

        )
        self.embedding_model = embedding_model

        self.text_converter = TextFileToDocument()
        self.pdf_converter = PyPDFToDocument()

        self.cleaner = DocumentCleaner(
            remove_empty_lines=True,
            remove_extra_whitespaces=True,
            remove_repeated_substrings=False
        )

        self.splitter =  RecursiveDocumentSplitter(
            split_length=1000,
            split_overlap=100,
            separators=["\n\n", "\n", ".", " "]
        )

        self.embedder = SentenceTransformersDocumentEmbedder(
            model=embedding_model,
            progress_bar=True
        )

        self.writer = DocumentWriter(document_store=self.document_store)

        self.processing_pipeline = Pipeline()
        self.processing_pipeline.add_component("cleaner", self.cleaner)
        self.processing_pipeline.add_component("splitter", self.splitter)
        self.processing_pipeline.add_component("embedder", self.embedder)
        self.processing_pipeline.add_component("writer", self.writer)
        self.processing_pipeline.connect("cleaner", "splitter")
        self.processing_pipeline.connect("splitter", "embedder")
        self.processing_pipeline.connect("embedder", "writer")


        self.text_embedder = SentenceTransformersTextEmbedder(model=embedding_model)
        self.retriever = QdrantEmbeddingRetriever(document_store=self.document_store)

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
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> dict[str, Any]:
        if metadata["file_type"] in ["pdf", "application/pdf"]:
            return self.upload_pdf_document(content, metadata)
        elif metadata["file_type"] in ["txt", "text/plain"]:
            return self.upload_text_document(content, metadata)
        raise ValueError(f"Unsupported file type: {metadata['file_type']}")

    def upload_text_document(
        self,
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> dict[str, Any]:
        document = Document(content=content.decode(), meta=metadata or {})
        metadata["id"] = document.id
        document_ret = self.processing_pipeline.run({"documents": [document]})

        if document_ret:
            return metadata

        raise ValueError("Failed to process text document.")

    def upload_pdf_document(
        self,
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> dict[str, Any]:
        stream = ByteStream(data=content, mime_type=metadata["file_type"])
        documents = self.pdf_converter.run([stream])["documents"]
        metadata["id"] = documents[0].id
        document_ret = None
        for document in documents:
            document.meta.update(metadata or {})
            document_ret = self.processing_pipeline.run({"documents": documents})

        if document_ret:
            return metadata

        raise ValueError("Failed to process PDF document.")

    def delete_document(self, document_id: str):
        self.document_store.filter_documents()
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
                file_content = file_path.read_bytes()

                metadata = {
                    "file_name": file_path.name,
                    "file_type": file_path.suffix[1:],
                    "file_size": file_path.stat().st_size
                }

                self.upload_document(file_content, metadata)
        return None
