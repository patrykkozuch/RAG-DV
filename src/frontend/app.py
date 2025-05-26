"""
Main Streamlit application for the RAG chatbot.
"""
import streamlit as st
from src.frontend.chat_interface import render_chat_interface
from src.frontend.document_management import render_document_management


st.set_page_config(
    page_title="RAG Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main():
    chat_page = st.Page(render_chat_interface, title="Chat", icon=":material/add_circle:")
    documents_page = st.Page(render_document_management, title="Document Management", icon=":material/delete:")

    pg = st.navigation([chat_page, documents_page])
    pg.run()

if __name__ == "__main__":
    main()