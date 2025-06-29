import streamlit as st
from summarizer.pipeline import summarize

st.title("Explainable LLM Summarizer")
up_file = st.file_uploader("Upload PDF or TXT")
engine = st.selectbox("Backend", ["gpt4o", "llama"])

if up_file and st.button("Summarize"):
    out = summarize(up_file, backend=engine)

    print("Output:", out)
    st.json(out)
    txt = up_file.getvalue().decode("utf-8", errors="ignore")
    for bullet in out:
        st.markdown(f"**• {bullet['bullet']}**")
        ids = bullet["evidence_ids"]
        for i in ids:
            st.markdown(f"> {i}. {txt.splitlines()[i - 1]}")
