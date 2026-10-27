"""아트메이트 스트림릿 진입점 (UI만 담당)."""
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from artmate import config, images
from artmate.agent import stream_answer
from artmate.tools.curriculum import index_exists

st.set_page_config(page_title="아트메이트", page_icon="🎨")


def reset_chat():
    st.session_state.messages = []  # 화면 표시용
    st.session_state.lc_history = []  # 모델 전달용
    st.session_state.current_image = None  # 현재 대화의 이미지 (M2 색상 추출용)
    st.session_state.pending_image = None  # 다음 메시지에 첨부할 이미지
    st.session_state.image_error = ""
    st.session_state.trace = []  # 에이전트 동작 보기용 턴별 기록
    # 업로더 값은 직접 지울 수 없어 키를 바꿔 새 위젯으로 만든다
    st.session_state.uploader_key = st.session_state.get("uploader_key", 0) + 1


def on_image_upload():
    file = st.session_state[f"uploader_{st.session_state.uploader_key}"]
    st.session_state.pending_image = None
    st.session_state.image_error = ""
    if file is None:
        return
    try:
        img = images.load_image(file)
    except ValueError as e:
        st.session_state.image_error = str(e)
    else:
        st.session_state.current_image = st.session_state.pending_image = img


def show_message(msg):
    with st.chat_message(msg["role"]):
        if msg.get("image") is not None:
            st.image(msg["image"], width=240)
        st.markdown(msg["content"])


if "messages" not in st.session_state:
    reset_chat()

# 사이드바
with st.sidebar:
    st.title("🎨 아트메이트")
    # 학교급을 바꾸면 수준이 섞이지 않도록 대화를 자동 초기화
    st.radio("학교급", ["초등", "중등"], key="school_level", horizontal=True, on_change=reset_chat)
    st.file_uploader(
        f"이미지 올리기 (JPG·PNG, {config.MAX_IMAGE_MB}MB 이하)",
        type=["jpg", "jpeg", "png"],
        max_upload_size=config.MAX_IMAGE_MB,
        key=f"uploader_{st.session_state.uploader_key}",
        on_change=on_image_upload,
    )
    st.caption("⚠️ 얼굴이나 이름표가 보이는 사진은 올리지 마세요.")
    if st.session_state.image_error:
        st.error(st.session_state.image_error)
    elif st.session_state.pending_image is not None:
        st.caption("다음 질문에 이 이미지가 함께 전달돼요.")
    st.button("대화 초기화", on_click=reset_chat, width="stretch")

# 메인
st.title("아트메이트")
st.caption("미술 시간에 함께 생각하고 탐구하는 학습 도우미예요.")

if not config.GOOGLE_API_KEY:
    st.warning(".env 파일에 GOOGLE_API_KEY를 설정한 뒤 다시 실행해 주세요.")
if not index_exists():
    st.warning("교육과정 검색 인덱스가 없어요. `python -m scripts.build_index`를 실행해 주세요.")

for msg in st.session_state.messages:
    show_message(msg)

if prompt := st.chat_input("궁금한 점을 적어 보세요", disabled=not config.GOOGLE_API_KEY):
    # 업로드한 이미지는 바로 다음 메시지 1회에만 첨부 (design.md §8.3)
    image = st.session_state.pending_image
    st.session_state.pending_image = None
    user_msg = {"role": "user", "content": prompt, "image": image}
    if image is None:
        content = prompt
    else:
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": images.to_data_url(image)},
        ]
    st.session_state.messages.append(user_msg)
    st.session_state.lc_history.append(HumanMessage(content))
    show_message(user_msg)

    turn = {"question": prompt, "calls": [], "error": ""}
    st.session_state.trace.append(turn)
    with st.chat_message("assistant"):
        try:
            answer = st.write_stream(
                stream_answer(st.session_state.lc_history, st.session_state.school_level, turn["calls"])
            )
        except Exception as e:
            turn["error"] = f"{type(e).__name__}: {e}"[:300]
            # 실패한 질문은 이력에서 빼고 이미지도 되돌려 다시 입력할 수 있게 한다
            st.session_state.messages.pop()
            st.session_state.lc_history.pop()
            st.session_state.pending_image = image
            st.error("지금은 답을 만들 수 없어요. 잠시 뒤 다시 질문해 주세요.")
        else:
            st.session_state.messages.append({"role": "assistant", "content": answer})
            st.session_state.lc_history.append(AIMessage(answer))

# 동작 보기는 이번 턴의 기록까지 보이도록 맨 마지막에 그린다
with st.sidebar:
    with st.expander("에이전트 동작 보기"):
        if not st.session_state.trace:
            st.caption("아직 기록이 없어요.")
        for i, turn in reversed(list(enumerate(st.session_state.trace, 1))):
            st.markdown(f"**{i}번째 질문**")
            st.text(turn["question"][:40])
            if not turn["calls"] and not turn["error"]:
                st.caption("도구 호출 없음")
            for call in turn["calls"]:
                args = ", ".join(f"{k}={v!r}" for k, v in call["args"].items())
                st.markdown(f"🔧 `{call['tool']}`")
                st.caption(f"인자: {args}")
                st.caption("결과: " + (", ".join(call["results"]) or "없음"))
            if turn["error"]:
                st.error(turn["error"])
