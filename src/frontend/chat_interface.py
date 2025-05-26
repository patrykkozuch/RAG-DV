"""
Chat interface component for the Streamlit RAG chatbot.
"""
import time

import streamlit as st

from src.backend.llm_operations import query_llm, get_chat_history
from src.backend.message import Message


def display_chat_message(message: Message) -> None:
    st.markdown(message.content)

    if message.sources:
        with st.expander("Sources"):
            for source in message.sources:
                st.markdown(f"**Document:** {source['id']} (Relevance: {source['relevance']:.2f})")

    if metadata := message.metadata_string():
        st.caption(metadata)


def render_chat_interface():
    """Render the chat interface component."""
    st.subheader('Chat with RAG')

    if "messages" not in st.session_state:
        st.session_state.messages = get_chat_history()

    for message in st.session_state.messages:
        with st.chat_message(message.role):
            display_chat_message(message)

    if prompt := st.chat_input("Ask a question..."):
        message = Message(role="user", content=prompt)

        with st.chat_message(message.role):
            display_chat_message(message)

        st.session_state.messages.append(message)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                time.sleep(3)  # should be removed at some point :)
                response = query_llm(prompt)
                display_chat_message(response)

        st.session_state.messages.append(response)
