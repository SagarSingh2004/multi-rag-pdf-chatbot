import streamlit as st
from rag import chat
from rag import create_vectorstore
import os
import shutil

st.title("Multi PDF RAG Chatbot")

# Session state
if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Display old messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Sidebar
with st.sidebar:
    st.header("Upload PDFs")

    uploaded_files = st.file_uploader(
        "Choose PDF files",
        type="pdf",
        accept_multiple_files=True
    )

    process = st.button("Process PDFs")

    if process:

        if uploaded_files:

            # Remove old PDFs
            if os.path.exists("temp"):
                shutil.rmtree("temp")

            os.makedirs("temp")

            # Save uploaded files
            for file in uploaded_files:
                with open(
                    f"temp/{file.name}",
                    "wb"
                ) as f:
                    f.write(file.getbuffer())

            st.success("Files saved successfully!")

            with st.spinner("Creating embeddings..."):

                vectorstore = create_vectorstore(
                    "temp"
                )

                st.session_state.vectorstore = (
                    vectorstore
                )

                # Clear old chat
                st.session_state.messages = []
                st.session_state.chat_history = []

            st.success(
                "PDFs processed successfully!"
            )

        else:
            st.warning(
                "Please upload at least one PDF."
            )
    
    # Knowledge base status
    st.divider()

    if st.session_state.vectorstore is None:
        st.warning("No knowledge base loaded.")
    else:
        st.success("Knowledge base ready.")


# Chat input
query = st.chat_input(
    "Ask a question",
    disabled=st.session_state.vectorstore is None
)

if query:

    # Store user message
    st.session_state.messages.append({
        "role": "user",
        "content": query
    })

    # Show user message
    with st.chat_message("user"):
        st.markdown(query)

    # Build history
    history = "\n".join(
        st.session_state.chat_history
    )

    # Get response stream
    response_stream, sources = chat(
        query,
        st.session_state.vectorstore,
        history
    )

    # Stream answer
    with st.chat_message("assistant"):

        placeholder = st.empty()

        full_response = ""

        for chunk in response_stream:
            full_response += chunk
            placeholder.markdown(
                full_response + "▌"
            )

        placeholder.markdown(
            full_response
        )

        if "This information was not found" in full_response:
            sources = []

        if sources:
            st.markdown("**Sources:**")

            for source in sources:
                st.markdown(f"- {source}")

    # Save assistant message
    st.session_state.messages.append({
        "role": "assistant",
        "content": full_response
    })

    # Save history for query rewriting
    st.session_state.chat_history.append(
        f"Human: {query}"
    )

    st.session_state.chat_history.append(
        f"AI: {full_response}"
    )