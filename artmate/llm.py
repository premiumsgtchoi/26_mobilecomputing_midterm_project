"""Gemini 채팅·임베딩 객체 생성."""
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from artmate import config


def get_chat_model(**kwargs) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL, google_api_key=config.GOOGLE_API_KEY, **kwargs
    )


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=config.EMBEDDING_MODEL, google_api_key=config.GOOGLE_API_KEY
    )


if __name__ == "__main__":
    # 호출 테스트: python -m artmate.llm
    reply = get_chat_model().invoke("미술을 한 문장으로 소개해 줘.")
    print(f"[채팅] {config.GEMINI_MODEL}: {reply.text}")

    vec = get_embeddings().embed_query("명암")
    print(f"[임베딩] {config.EMBEDDING_MODEL}: 차원 {len(vec)}, 앞 5개 {vec[:5]}")
