"""아트메이트 스트림릿 진입점 (UI만 담당)."""
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from artmate import config
from artmate.llm import get_chat_model
from artmate.prompts import build_system_prompt

st.set_page_config(page_title="아트메이트", page_icon="🎨")


def reset_chat():
    st.session_state.messages = []  # 화면 표시용
    st.session_state.lc_history = []  # 모델 전달용


if "messages" not in st.session_state:
    reset_chat()

# 사이드바
with st.sidebar:
    st.title("🎨 아트메이트")
    # 학교급을 바꾸면 수준이 섞이지 않도록 대화를 자동 초기화
    st.radio("학교급", ["초등", "중등"], key="school_level", horizontal=True, on_change=reset_chat)
    st.button("대화 초기화", on_click=reset_chat, width="stretch")

# 메인
st.title("아트메이트")
st.caption("미술 시간에 함께 생각하고 탐구하는 학습 도우미예요.")

if not config.GOOGLE_API_KEY:
    st.warning(".env 파일에 GOOGLE_API_KEY를 설정한 뒤 다시 실행해 주세요.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("궁금한 점을 적어 보세요", disabled=not config.GOOGLE_API_KEY):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.lc_history.append(HumanMessage(prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            system = SystemMessage(build_system_prompt(st.session_state.school_level))
            llm_messages = [system] + st.session_state.lc_history
            answer = st.write_stream(
                chunk.text for chunk in get_chat_model().stream(llm_messages)
            )
        except Exception:
            # 실패한 질문은 이력에서 빼서 다시 입력할 수 있게 한다
            st.session_state.messages.pop()
            st.session_state.lc_history.pop()
            st.error("지금은 답을 만들 수 없어요. 잠시 뒤 다시 질문해 주세요.")
        else:
            st.session_state.messages.append({"role": "assistant", "content": answer})
            st.session_state.lc_history.append(AIMessage(answer))
