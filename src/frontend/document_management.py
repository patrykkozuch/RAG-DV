"""
Document management component for the Streamlit RAG chatbot.
"""
import time

import streamlit as st
from src.backend.document_operations import DocumentManager


def render_document_management():
    global _document_manager
    if '_document_manager' not in globals():
        _document_manager = DocumentManager(
            qdrant_url="http://localhost:6333",
            qdrant_collection="documents",
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            embedding_dim=384  # Default dimension for MiniLM
        )
        _document_manager.initialize_from_directory()
    """Render the document management component."""

    col1, _ = st.columns([2, 1])

    if 'documents' not in st.session_state:
        st.session_state.documents = _document_manager.list_documents()

    with col1:
        st.markdown("### Upload Document")

        uploaded_file = st.file_uploader("", type=["txt", "pdf"])

        if uploaded_file is not None:
            st.write(f"File name: {uploaded_file.name}")
            st.write(f"**Size:** {uploaded_file.size / 1024:.2f} KB")
            st.write(f"File type: {uploaded_file.type}")

            if st.button("Process and Upload Document", type="primary"):
                with st.spinner("Processing and uploading..."):
                    time.sleep(1)
                    file_content = uploaded_file.getvalue()

                    metadata = {
                        "file_name": uploaded_file.name,
                        "file_type": uploaded_file.type,
                        "file_size": uploaded_file.size / 1024
                    }

                    result = _document_manager.upload_document(file_content, metadata)
                    print(result)

                    if result:
                        st.success(f"Document uploaded successfully! ID: {result['id']}")
                        st.session_state.documents.append(result)

                    else:
                        st.error("Failed to upload document.")

    st.markdown("### Your Documents")

    list_cols = st.columns([1, 4, 1, 1, 2])
    list_cols[0].markdown("**ID**")
    list_cols[1].markdown("**Title**")
    list_cols[2].markdown("**Type**")
    list_cols[3].markdown("**Size (KB)**")
    list_cols[4].markdown("**Actions**")

    for doc in st.session_state.documents:
        col1_row, col2_row, col3_row, col4_row, col5_row = st.columns([1, 4, 1, 1, 2])

        view_key = f"view_{doc['id']}"
        delete_key = f"delete_{doc['id']}"

        if col5_row.button("View", key=view_key):
            content = _document_manager.get_document_content(doc["id"])
            if content:
                st.text_area("Document content", value=content, height=300, disabled=True)
            else:
                st.error("Could not retrieve document content.")

        if col5_row.button("Delete", key=delete_key):
            _document_manager.delete_document(doc["id"])
            st.session_state.documents.remove(doc)
            st.success(f"Document {doc['id']} deleted successfully!")
            st.rerun()

        with col1_row:
            st.write(doc.get("id", "N/A"))
        with col2_row:
            st.write(doc.get("file_name", "N/A"))
        with col3_row:
            st.write(doc.get("file_type", "N/A"))
        with col4_row:
            size_kb = doc.get("file_size", 0)
            st.write(f"{size_kb:.2f}")
