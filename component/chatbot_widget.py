from html import escape

import streamlit as st
from streamlit_float import float_css_helper

from ai.chatbot import ask_chatbot

MAX_HISTORY = 20


def _inject_widget_css():

    st.markdown(
        """
        <style>

        /* ================= Floating Button ================= */

        div[class*="st-key-chat_toggle"] button {
            width:58px;
            height:58px;
            border-radius:50%;
            background:linear-gradient(145deg,#E8A33D,#C77F1F);
            color:white;
            border:none;
            font-size:1.55rem;
            padding:0;
            box-shadow:0 14px 30px -12px rgba(199,127,31,.6);
            transition:.2s;
        }

        div[class*="st-key-chat_toggle"] button:hover{
            transform:scale(1.07);
            box-shadow:0 18px 36px -10px rgba(199,127,31,.7);
        }

        div[class*="st-key-chat_toggle"] button p{
            color:white !important;
            font-size:1.55rem;
        }

        /* ================= Chat Window ================= */

        div[class*="st-key-chat_window"]{

            animation:fadeIn .2s ease;
        }

        @keyframes fadeIn{
            from{
                opacity:0;
                transform:translateY(10px);
            }
            to{
                opacity:1;
                transform:translateY(0px);
            }
        }

        .chatbot-header{

            display:flex;
            justify-content:space-between;
            align-items:center;

            padding-bottom:.7rem;
            margin-bottom:.8rem;

            border-bottom:1px solid #D9DDE2;
        }

        .chatbot-title{

            font-family:Fraunces,serif;
            font-size:1.05rem;
            font-weight:600;
            color:#16243F;
        }

        .chatbot-status{

            font-size:.68rem;

            color:#1F7A5C;

            background:rgba(31,122,92,.12);

            padding:.18rem .6rem;

            border-radius:999px;

            font-weight:600;
        }

        .chatbot-empty{

            background:#F5F6F3;

            border:1px solid #D9DDE2;

            border-radius:12px;

            padding:.8rem;

            color:#16243F;

            font-size:.87rem;

            margin-bottom:1rem;

            line-height:1.5;
        }

        div[class*="st-key-chat_window"] div[data-testid="stChatMessage"]{

            background:#F5F6F3;

            border:1px solid #D9DDE2;

            border-radius:12px;

            padding:.2rem;
        }

        div[class*="st-key-chat_window"] div[data-testid="stChatInput"]{

            margin-top:.9rem;
            background:linear-gradient(180deg,#FFFFFF 0%,#FBF9F3 100%);
            border:1px solid #D9DDE2;
            border-radius:22px;
            padding:.6rem .65rem;
            box-shadow:0 18px 34px -26px rgba(22,36,63,.55);
        }

        div[class*="st-key-chat_window"] div[data-testid="stChatInput"] > div{

            background:transparent;
            gap:.45rem;
        }

        div[class*="st-key-chat_window"] div[data-testid="stChatInput"] textarea{

            background:transparent !important;
            color:#16243F !important;
            caret-color:#16243F !important;
            border:none !important;
            box-shadow:none !important;
            font-size:.98rem;
            line-height:1.45;
            padding:.45rem .35rem !important;
            min-height:56px;
            resize:none;
        }

        div[class*="st-key-chat_window"] div[data-testid="stChatInput"] textarea::placeholder{

            color:#8A92A3;
            opacity:1;
            font-weight:500;
        }

        div[class*="st-key-chat_window"] div[data-testid="stChatInput"] textarea:focus{

            background:#FFFFFF !important;
            outline:none !important;
            box-shadow:none !important;
        }

        div[class*="st-key-chat_window"] div[data-testid="stChatInput"] button{

            background:linear-gradient(145deg,#E8A33D,#C77F1F) !important;
            color:#FFFFFF !important;
            border:none !important;
            border-radius:14px !important;
            min-width:48px;
            min-height:48px;
            box-shadow:0 12px 24px -16px rgba(199,127,31,.85) !important;
            transition:.2s ease !important;
        }

        div[class*="st-key-chat_window"] div[data-testid="stChatInput"] button:hover{

            transform:translateY(-1px);
            box-shadow:0 16px 28px -14px rgba(199,127,31,.9) !important;
        }

        .chat-message-row{
            display:flex;
            width:100%;
            margin:.55rem 0;
        }

        .chat-message-row.user{
            justify-content:flex-end;
        }

        .chat-message-row.assistant{
            justify-content:flex-start;
        }

        .chat-message-bubble{
            max-width:82%;
            padding:.75rem .9rem;
            border-radius:14px;
            font-size:.92rem;
            line-height:1.5;
            white-space:normal;
            word-break:break-word;
        }

        .chat-message-row.user .chat-message-bubble{
            background:#E8A33D;
            color:#fff;
            border-top-right-radius:4px;
        }

        .chat-message-row.assistant .chat-message-bubble{
            background:#F5F6F3;
            color:#16243F;
            border:1px solid #D9DDE2;
            border-top-left-radius:4px;
        }

        .chat-message-meta{
            font-size:.68rem;
            font-weight:700;
            margin-bottom:.25rem;
            opacity:.78;
        }

        .chat-message-row.user .chat-message-meta{
            text-align:right;
        }

        div[class*="st-key-chat_window"] textarea{

            border-radius:12px !important;

            border:1px solid #D9DDE2 !important;
        }

        div[class*="st-key-chat_window"] textarea:focus{

            border:1px solid #E8A33D !important;

            box-shadow:0 0 0 3px rgba(232,163,61,.18) !important;
        }

        div[class*="st-key-clear_chat"] button{

            background:none;

            border:none;

            color:#C77F1F;

            font-size:.75rem;

            font-weight:600;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


def render_chatbot():

    _inject_widget_css()

    if "chat_open" not in st.session_state:
        st.session_state.chat_open = False

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # ================= Floating Button ================= #

    fab = st.container(key="chat_fab")

    with fab:

        icon = "✕" if st.session_state.chat_open else "🤖"

        if st.button(icon, key="chat_toggle"):

            st.session_state.chat_open = not st.session_state.chat_open
            st.rerun()

    fab.float(

        float_css_helper(

            width="58px",

            bottom="1.8rem",

            right="1.8rem",

            background="transparent",

            z_index="1001",
        )
    )

    # ================= Chat Window ================= #

    if not st.session_state.chat_open:
        return

    window = st.container(key="chat_window")
    window.float(

                        float_css_helper(

                            width="390px",

                            bottom="6.3rem",

                            right="1.8rem",

                            background="white",

                            border="1px solid #D9DDE2",

                            border_radius="18px",

                            padding="1rem",

                            box_shadow="0 24px 60px -24px rgba(22,36,63,.40)",

                            max_height="650px",

                            overflow_y="auto",

                            z_index="1000",
                        )
                    )

    with window:

        col1, col2 = st.columns([5, 1])

        with col1:
            st.subheader("🤖 HomeDesk Assistant")

        with col2:
            if st.button("🗑", key="clear_chat", help="Clear Chat"):
                st.session_state.messages = []
                st.rerun()

        st.caption("🟢 Online")

        if not st.session_state.messages:

            st.markdown(
                """
                <div class="chatbot-empty">

                👋 <b>Welcome to HomeDesk!</b><br><br>

                I can help you with:

                • Cook Service<br>
                • Driver Service<br>
                • Security Guard Service<br>
                • Estimated Pricing<br>
                • Booking Process<br>
                • Requirement Forms<br>
                • Frequently Asked Questions

                <br><br>

                Ask me anything related to HomeDesk.

                </div>
                """,
                unsafe_allow_html=True,
            )

        for message in st.session_state.messages:
            role = message["role"]
            content = escape(message["content"]).replace("\n", "<br>")

            st.markdown(
                f'''
                <div class="chat-message-row {role}">
                    <div class="chat-message-bubble">
                        <div class="chat-message-meta">{'You' if role == 'user' else 'HomeDesk Assistant'}</div>
                        <div>{content}</div>
                    </div>
                </div>
                ''',
                unsafe_allow_html=True,
            )

        prompt = st.chat_input(
            "Ask anything about our services...",
            key="chat_input_box",
        )

        if prompt:
            prompt = prompt.strip()

            if prompt:
                st.session_state.messages.append(
                    {
                        "role": "user",
                        "content": prompt,
                    }
                )

                with st.spinner("Thinking..."):
                    response = ask_chatbot(prompt)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": response,
                    }
                )

                if len(st.session_state.messages) > MAX_HISTORY:
                    st.session_state.messages = st.session_state.messages[-MAX_HISTORY:]

                st.rerun()

