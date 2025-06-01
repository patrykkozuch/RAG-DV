"""
Main Streamlit application for the RAG chatbot.
"""
import streamlit as st

from src.backend.document_operations import DocumentManager
from src.frontend.chat_interface import render_chat_interface
from src.frontend.document_management import render_document_management


st.set_page_config(
    page_title="RAG Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main():
    global _document_manager
    if '_document_manager' not in globals():
        _document_manager = DocumentManager()
        _document_manager.initialize_from_directory()

    chat_page = st.Page(render_chat_interface, title="Chat", icon=":material/add_circle:")
    documents_page = st.Page(render_document_management(_document_manager), title="Document Management", icon=":material/delete:")

    pg = st.navigation([chat_page, documents_page])
    pg.run()

if __name__ == "__main__":
    main()