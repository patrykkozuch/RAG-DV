"""
Document management component for the Streamlit RAG chatbot.
"""
import streamlit as st
from src.backend.document_operations import list_documents, upload_document, delete_document, get_document_content


def render_document_management():
    """Render the document management component."""

    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Upload Document")

        uploaded_file = st.file_uploader("Choose a file", type=["pdf", "txt", "docx", "md"])
        
        if uploaded_file is not None:
            st.write(f"File name: {uploaded_file.name}")
            st.write(f"File size: {uploaded_file.size} bytes")
            st.write(f"File type: {uploaded_file.type}")

            # Upload button
            if st.button("Upload Document"):
                with st.spinner("Uploading..."):
                    file_content = uploaded_file.getvalue()

                    file_type = uploaded_file.name.split(".")[-1]

                    result = upload_document(file_content, uploaded_file.name, file_type)
                    
                    if result:
                        st.success(f"Document uploaded successfully! ID: {result['id']}")
                    else:
                        st.error("Failed to upload document.")
    
    with col2:
        st.markdown("### Settings")
        st.checkbox("Split into chunks", value=True)
        st.slider("Chunk size (tokens)", min_value=100, max_value=1000, value=500, step=100)
        st.selectbox("Embedding model", ["OpenAI", "BERT", "Sentence Transformers"])

    st.markdown("### Your Documents")

    documents = list_documents()
    
    if not documents:
        st.info("No documents found. Upload a document to get started.")
    else:
        col1, col2, col3, col4, col5 = st.columns([1, 3, 1, 1, 1])
        col1.markdown("**ID**")
        col2.markdown("**Title**")
        col3.markdown("**Type**")
        col4.markdown("**Size**")
        col5.markdown("**Actions**")

        for doc in documents:
            col1, col2, col3, col4, col5 = st.columns([1, 3, 1, 1, 1])
            col1.write(doc["id"])
            col2.write(doc["title"])
            col3.write(doc["type"])
            col4.write(f"{doc['size']} B")

            view_key = f"view_{doc['id']}"
            delete_key = f"delete_{doc['id']}"

            if col5.button("View", key=view_key):
                content = get_document_content(doc["id"])
                if content:
                    st.text_area("Document content", value=content, height=300, disabled=True)
                else:
                    st.error("Could not retrieve document content.")
            
            if col5.button("Delete", key=delete_key):
                if delete_document(doc["id"]):
                    st.success(f"Document {doc['id']} deleted successfully!")
                    st.rerun()
                else:
                    st.error(f"Failed to delete document {doc['id']}.")