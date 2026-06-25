from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAI, GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from dotenv import load_dotenv

# Loading the environmental variables
load_dotenv()

def create_vectorstore(pdf_path):
    loader = DirectoryLoader(
        path=pdf_path,
        loader_cls=PyPDFLoader
    )

    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )

    chunks = splitter.split_documents(docs)

    embedding = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001"
    )

    vectorstore = FAISS.from_documents(
        chunks,
        embedding
    )

    return vectorstore


# llm
llm1 = GoogleGenerativeAI(model = 'gemini-2.5-flash')
llm2 = ChatGoogleGenerativeAI(model = 'gemini-2.5-flash', streaming=True)

# Main prompt for llm
prompt = PromptTemplate.from_template(
'''
Previous Conversation:
{history}

Context:
{context}

Question:
{query}

Instructions:
1. First answer using the provided context.
2. If the answer is not present in the context, clearly say:
   "This information was not found in the uploaded documents."
3. You may then provide a general answer based on your knowledge.
4. Clearly separate document information from general knowledge.
5. Never pretend that general knowledge came from the documents.

Answer:
'''
)

# Rewrite prompt for History aware retrieval
rewrite_prompt = PromptTemplate.from_template(
'''
Given the conversation history and the latest user question,
rewrite the question so that it is a standalone question.

History:
{history}

Question:
{query}

Standalone Question:
'''
)

# Context function
def format_docs(text):
    return '\n\n'.join(i.page_content for i in text)

# Source Function
def get_sources(text):
    return list(
        set(
            f"{doc.metadata['source']} "
            f"(Page {doc.metadata['page']+1})"
            for doc in text
        )
    )

# Rewriter Chain
rewriter_chain = (
    rewrite_prompt
    | llm1
    | StrOutputParser()
)

# Generative Chain
generative_chain = prompt | llm2 | StrOutputParser()

# history

# User query
def chat(query, vectorstore, history):

    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 2}
    )
    
    standalone_query = rewriter_chain.invoke({
        "history": history,
        "query": query
    })
    
    data = retriever.invoke(standalone_query)
    context = format_docs(data)
    sources = get_sources(data)


    response_stream = generative_chain.stream({
        'query': query,
        'context': context,
        'history': history
    })

    return response_stream, sources