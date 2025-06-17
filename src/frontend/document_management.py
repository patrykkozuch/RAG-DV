"""
Document management component for the Streamlit RAG chatbot.
"""
import time

import streamlit as st
from src.backend.document_operations import DocumentManager


def render_document_management():
    """Render the document management component."""
    global _document_manager
    if '_document_manager' not in globals():
        _document_manager = DocumentManager(
            qdrant_url="http://localhost:6333",
            qdrant_collection="documents"
        )
        _document_manager.initialize_from_directory()

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
                    if result:
                        st.success(f"File uploaded successfully! file_id: {result['file_id']}")
                        # Refresh the list of documents to get the updated doc_count
                        st.session_state.documents = _document_manager.list_documents()
                        st.rerun() # Ensure UI updates immediately
                    else:
                        st.error("Failed to upload document.")

    st.markdown("### Your Files")

    if "delete_message" in st.session_state:
        st.success(st.session_state.delete_message)
        del st.session_state.delete_message

    # Display files grouping chunks
    list_cols = st.columns([5, 1, 1, 1, 2])
    list_cols[0].markdown("**Title**")
    list_cols[1].markdown("**Type**")
    list_cols[2].markdown("**Size (KB)**")
    list_cols[3].markdown("**Chunks**")
    list_cols[4].markdown("**Actions**")

    for file in st.session_state.documents:
        # rows for name, type, size, chunks, actions
        cols = st.columns([5, 1, 1, 1, 2])
        col1_row, col2_row, col3_row, col4_row, col5_row = cols
        view_key = f"view_{file['file_id']}"
        delete_key = f"delete_{file['file_id']}"

        if col5_row.button("View", key=view_key):
            content = _document_manager.get_document_content(file["file_id"])
            if content:
                st.text_area("File content", value=content, height=300, disabled=True)
            else:
                st.error("Could not retrieve file content.")

        if col5_row.button("Delete", key=delete_key):
            _document_manager.delete_document(file["file_id"])
            st.session_state.delete_message = f"File {file['file_id']} deleted successfully!"
            st.session_state.documents = _document_manager.list_documents()
            st.rerun()

        with col1_row:
            st.write(file.get("file_name", "N/A"))
        with col2_row:
            st.write(file.get("file_type", "N/A"))
        with col3_row:
            size_kb = file.get("file_size", 0)
            st.write(f"{size_kb:.2f}")
        with col4_row:
            st.write(file.get("doc_count", 0))
