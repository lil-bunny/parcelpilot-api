from langchain.chat_models import init_chat_model
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings


def get_chat_model():
    settings.apply_env()
    return init_chat_model(settings.llm_model)


def get_embeddings():
    settings.apply_env()
    return OpenAIEmbeddings(model=settings.embedding_model)
