"""
Document management component for the Streamlit RAG chatbot.
"""
import time

import streamlit as st
from src.backend.document_operations import list_documents, upload_document, delete_document, get_document_content


def render_document_management():
    """Render the document management component."""

    col1, col2 = st.columns([2, 1])

    if 'documents' not in st.session_state:
        st.session_state.documents = list_documents()

    with col1:
        st.markdown("### Upload Document")

        uploaded_file = st.file_uploader("", type=["pdf", "txt", "docx", "md"])
        
        if uploaded_file is not None:
            st.write(f"File name: {uploaded_file.name}")
            st.write(f"**Size:** {uploaded_file.size / 1024:.2f} KB")
            st.write(f"File type: {uploaded_file.type}")

            if st.button("Process and Upload Document", type="primary"):
                with st.spinner("Processing and uploading..."):
                    time.sleep(1)
                    file_content = uploaded_file.getvalue()

                    file_type = uploaded_file.name.split(".")[-1]

                    result = upload_document(file_content, uploaded_file.name, file_type)

                    if result:
                        st.success(f"Document uploaded successfully! ID: {result['id']}")
                        st.session_state.documents.append(result)

                    else:
                        st.error("Failed to upload document.")

    with col2:
        st.markdown("### Settings")
        st.checkbox("Split into chunks", value=True)
        st.slider("Chunk size (tokens)", min_value=100, max_value=1000, value=500, step=100)
        st.selectbox("Embedding model", ["OpenAI", "BERT", "Sentence Transformers"])

    st.markdown("### Your Documents")

    list_cols = st.columns([1, 4, 1, 1, 2])
    list_cols[0].markdown("**ID**")
    list_cols[1].markdown("**Title**")
    list_cols[2].markdown("**Type**")
    list_cols[3].markdown("**Size (KB)**")
    list_cols[4].markdown("**Actions**")

    for doc in st.session_state.documents:
        col1_row, col2_row, col3_row, col4_row, col5_row = st.columns([1, 4, 1, 1, 2])

        with col1_row:
            st.write(doc.get("id", "N/A"))
        with col2_row:
            st.write(doc.get("title", "N/A"))
        with col3_row:
            st.write(doc.get("type", "N/A"))
        with col4_row:
            size_kb = doc.get("size", 0) / 1024
            st.write(f"{size_kb:.2f}")

        view_key = f"view_{doc['id']}"
        delete_key = f"delete_{doc['id']}"

        if col5_row.button("View", key=view_key):
            content = get_document_content(doc["id"])
            if content:
                st.text_area("Document content", value=content, height=300, disabled=True)
            else:
                st.error("Could not retrieve document content.")

        if col5_row.button("Delete", key=delete_key):
            if delete_document(doc["id"]):
                st.success(f"Document {doc['id']} deleted successfully!")
                st.rerun()
            else:
                st.error(f"Failed to delete document {doc['id']}.")