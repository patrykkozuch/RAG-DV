from typing import List, Optional, Dict, Any
from pathlib import Path
import uuid

from haystack import Document, Pipeline
from haystack.components.converters import TextFileToDocument
from haystack.components.preprocessors import DocumentCleaner, RecursiveDocumentSplitter
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
    ):
        self.document_store = QdrantDocumentStore(
            url=qdrant_url,
            index=qdrant_collection

        )

        self.text_converter = TextFileToDocument()
        self.pdf_converter = PyPDFToDocument()

        self.cleaner = DocumentCleaner(
            remove_empty_lines=True,
            remove_extra_whitespaces=True,
            remove_repeated_substrings=False
        )

        self.splitter =  RecursiveDocumentSplitter(
            split_length=500,
            split_overlap=100,
            separators=["\n\n", "\n", ".", " "]
        )

        self.embedder = SentenceTransformersDocumentEmbedder()

        self.writer = DocumentWriter(document_store=self.document_store)

        self.processing_pipeline = Pipeline()
        self.processing_pipeline.add_component("cleaner", self.cleaner)
        self.processing_pipeline.add_component("splitter", self.splitter)
        self.processing_pipeline.add_component("embedder", self.embedder)
        self.processing_pipeline.add_component("writer", self.writer)
        self.processing_pipeline.connect("cleaner", "splitter")
        self.processing_pipeline.connect("splitter", "embedder")
        self.processing_pipeline.connect("embedder", "writer")


        self.text_embedder = SentenceTransformersTextEmbedder()
        self.retriever = QdrantEmbeddingRetriever(document_store=self.document_store)

        self.search_pipeline = Pipeline()
        self.search_pipeline.add_component("text_embedder", self.text_embedder)
        self.search_pipeline.add_component("retriever", self.retriever)
        self.search_pipeline.connect("text_embedder.embedding", "retriever.query_embedding")

    def get_documents(self) -> List[Document]:
        return self.document_store.filter_documents()

    def list_documents(self) -> List[Dict[str, Any]]:
        # Group haystack documents by file_id to represent files
        documents = self.get_documents()
        files: Dict[str, Dict[str, Any]] = {}
        for doc in documents:
            meta = doc.meta
            fid = meta.get("file_id")
            if not fid:
                continue
            if fid not in files:
                files[fid] = {
                    "file_id": fid,
                    "file_name": meta.get("file_name"),
                    "file_type": meta.get("file_type"),
                    "file_size": meta.get("file_size"),
                    "doc_count": 0
                }
            files[fid]["doc_count"] += 1
        return list(files.values())

    def upload_document(
        self,
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> dict[str, Any]:
        metadata["file_id"] = uuid.uuid4().hex
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
        document = Document(content=content.decode(), meta=metadata)
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
        for document in documents:
            document.meta.update(metadata)
        document_ret = self.processing_pipeline.run({"documents": documents})

        if document_ret:
            return metadata

        raise ValueError("Failed to process PDF document.")

    def delete_document(self, file_id: str):
        # delete all haystack documents associated with a file_id
        docs = self.document_store.filter_documents(filters={"field": "meta.file_id", "operator": "==", "value": file_id})
        ids = [doc.id for doc in docs]
        if not ids:
            return
        self.document_store.delete_documents(ids)

    def get_document_count(self) -> int:
        return self.document_store.count_documents()

    def search_documents(self, query: str, top_k: int = 5) -> List[Document]:
        result = self.search_pipeline.run({
            "text_embedder": {"text": query},
            "retriever": {"top_k": top_k}
        })
        return result["retriever"]["documents"]

    def get_document_content(self, file_id: str) -> str | None:
        # retrieve and concatenate all content chunks for a file_id
        docs = self.document_store.filter_documents(filters={"field": "meta.file_id", "operator": "==", "value": file_id})
        if not docs:
            return None
        # combine contents in arbitrary order
        return "\n".join([doc.content for doc in docs])

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
