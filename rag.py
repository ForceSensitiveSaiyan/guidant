import re, os
from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, SystemMessage

# === Embeddings and Retriever ===
# embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
# chroma_db = Chroma(persist_directory="./chroma_db", embedding_function=embeddings, collection_name="langchain")
# retriever = chroma_db.as_retriever(search_kwargs={"k": 3}) # was 3 and dropped to 2 for fewer tokens spent on context

# === Load Quantised LLM (GGUF via llama-cpp-python) ===
# llm = LlamaCpp(
#    model_path="./models/mistral-7b-instruct-v0.2.Q4_K_M.gguf",  # update with your actual file path
#    temperature=0.5,        # a bit crisper & shorter
#    top_p=0.9,
#    max_tokens=1024,        # was 512 → allow longer completions
#    n_ctx=4096,             # was 2048 → reduces chance of truncation
#    repeat_penalty=1.1,     # helps avoid rambling
#    verbose=False
# )


# === Embeddings & retriever (cached) ===
@lru_cache(maxsize=1)
def get_embeddings():
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


@lru_cache(maxsize=1)
def get_retriever():
    from langchain_chroma import Chroma

    db = Chroma(
        persist_directory="./chroma_db",
        embedding_function=get_embeddings(),
        collection_name="langchain",
    )
    return db.as_retriever(search_kwargs={"k": 3})


# === LLM provider switch (OpenAI by default; local as fallback) ===
@lru_cache(maxsize=1)
def get_llm():
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider in ("openai", "azure_openai"):
        # Managed LLM (fast)
        from langchain_openai import ChatOpenAI

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        # For Azure OpenAI, also set OPENAI_BASE_URL + OPENAI_API_VERSION via env;
        # ChatOpenAI will read them automatically from the OpenAI SDK env vars.
        return ChatOpenAI(model=model, temperature=0.3)
    else:
        # Local CPU fallback (slower)
        from langchain_community.llms import LlamaCpp

        n_threads = int(os.getenv("LLAMA_THREADS", os.cpu_count() or 2))
        return LlamaCpp(
            model_path="./models/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
            temperature=0.5,
            top_p=0.9,
            max_tokens=512,
            n_ctx=2048,
            n_threads=n_threads,
            n_batch=128,
            repeat_penalty=1.1,
            verbose=False,
        )


# === Prompt Setup ===
prompt_template = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content=(
                "You are an AI assistant trained to support social workers by providing clear, policy-informed guidance based solely on the indexed documents, which relate to the Isle of Man. "
                "Always interpret and answer questions using Isle of Man legislation, regulations, and local procedures unless clearly told otherwise. "
                "Your purpose is to assist, not replace, professional judgment. "
                "Use UK English spelling and terminology. "
                "Begin answers naturally — do not use phrases like 'In this context', 'According to the documents', 'Based on the context', or 'An answer could be'. "
                "Avoid explaining whether information was found or not unless you are explicitly instructed to. "
                "Just respond directly, clearly, and concisely. "
                "If no relevant information exists in the documents, say so in a straightforward and respectful way."
                # "Keep answers concise (about 6–10 bullet points or ~180–220 words) unless the user asks for more detail." # If you want to reduce the chance of hitting the cap while keeping answers tight, add a gentle nudge in the
            )
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)


# === Text Cleanup ===
def clean_text(text: str) -> str:
    text = re.sub(r"Page\s*\|*\s*\d+", "", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"-\s+", "", text)
    return text.strip()


def clean_documents(docs):
    for doc in docs:
        doc.page_content = clean_text(doc.page_content)
    return docs


# === Main Query Function ===
def query_rag(query: str) -> dict:
    # Build the retriever and LLM at call-time (both are cached by @lru_cache)
    retriever = get_retriever()
    llm = get_llm()

    # Build the chain using your existing prompt_template
    from langchain.chains import LLMChain

    llm_chain = LLMChain(llm=llm, prompt=prompt_template)

    # Retrieve and clean context
    docs = retriever.invoke(query)
    clean_docs = clean_documents(docs)

    if not clean_docs:
        return {
            "result": "I'm sorry, I couldn't find anything relevant in the available documents to answer that question."
        }

    context = "\n\n".join(doc.page_content for doc in clean_docs)

    # Your prompt_template already has MessagesPlaceholder("messages")
    # so we pass a list of messages as before.
    messages = [
        HumanMessage(
            content=(
                f"Use the following policy and legal guidance to answer the question clearly and naturally. "
                f"Context:\n{context}\n\n"
                f"Question: {query}"
            )
        )
    ]

    answer = llm_chain.invoke({"messages": messages})
    cleaned_answer = re.sub(
        r"(?m)^\s*(Assistant:|Answer:)\s*",
        "",
        answer["text"].strip(),
        flags=re.IGNORECASE,
    )

    # build sources list
    sources = set()
    for d in clean_docs:
        src = d.metadata.get("source", "Unknown source")
        title = d.metadata.get("title", os.path.basename(src))
        sources.add(f"{title} ({os.path.basename(src)})")

    source_text = "\n\n**Sources:**\n" + "\n".join(f"- {s}" for s in sorted(sources))
    return {"result": cleaned_answer + source_text}
