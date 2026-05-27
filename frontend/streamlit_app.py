"""
Maternal Health Assistant — Streamlit chat interface.
Talks to the FastAPI backend running on localhost:8000.
"""
import streamlit as st
import requests

API_URL = "http://localhost:8000"

# -------------------------------------------------------
# Page config
# -------------------------------------------------------
st.set_page_config(
    page_title="Maternal Health Assistant",
    page_icon="🤱",
    layout="centered",
)

st.title("🤱 Maternal Health Assistant")
st.caption(
    "Grounded answers from WHO, Nigerian Federal Ministry of Health, "
    "NPHCDA, UNICEF, and NCDC guidelines."
)
st.divider()

# -------------------------------------------------------
# Session state — conversation history
# -------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.welcomed = False

if not st.session_state.welcomed:
    st.session_state.welcomed = True
    now = __import__("datetime").datetime.now().hour
    if now < 12:
        greeting = "Good morning"
    elif now < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    welcome = (
        f"{greeting}! 👋 Welcome to the Maternal Health Assistant.\n\n"
        "I can help you with questions about:\n"
        "- Pregnancy and antenatal care\n"
        "- Danger signs and emergencies\n"
        "- Childbirth and postnatal care\n"
        "- Newborn and child health\n"
        "- Nutrition and breastfeeding\n\n"
        "All answers are grounded in WHO and Nigerian health guidelines. "
        "**How may I help you today?**"
    )
    st.session_state.messages.append({
        "role": "assistant",
        "content": welcome,
        "citations": [],
    })

# -------------------------------------------------------
# Render existing conversation
# -------------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("citations"):
            with st.expander("📚 Sources", expanded=False):
                for c in msg["citations"]:
                    st.markdown(f"**[{c['index']}]** {c['source']} — {c['filename']}")

# -------------------------------------------------------
# Chat input
# -------------------------------------------------------
if prompt := st.chat_input("Ask a maternal health question..."):

    # Show user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)

    # Build history in the format FastAPI expects
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
    ]

    # Call the FastAPI backend
    with st.chat_message("assistant"):
        with st.spinner("Searching guidelines..."):
            try:
                response = requests.post(
                    f"{API_URL}/chat",
                    json={"question": prompt, "history": history},
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()
                answer = data["answer"]
                citations = data.get("citations", [])

            except requests.exceptions.ConnectionError:
                answer = (
                    "⚠️ Cannot connect to the health assistant server. "
                    "Make sure the FastAPI server is running."
                )
                citations = []
            except requests.exceptions.Timeout:
                answer = "⚠️ The request timed out. Please try again."
                citations = []
            except Exception as e:
                answer = f"⚠️ Unexpected error: {str(e)}"
                citations = []

        st.markdown(answer)

        if citations:
            with st.expander("📚 Sources", expanded=False):
                for c in citations:
                    st.markdown(f"**[{c['index']}]** {c['source']} — {c['filename']}")

    # Save both turns to session state
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "citations": citations,
    })

# -------------------------------------------------------
# Sidebar
# -------------------------------------------------------
with st.sidebar:
    st.header("About")
    st.info(
        "This assistant provides maternal and child health information "
        "grounded in authoritative guidelines. It does not replace "
        "professional medical advice."
    )
    st.divider()
    if st.button("🗑️ Clear conversation"):
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.caption("Sources: WHO · Nigeria MoH · NPHCDA · UNICEF · NCDC")