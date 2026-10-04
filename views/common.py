import streamlit as st
FOOT='Prototype trained on synthetic data. Scores are screening signals; human verification is mandatory.'
def footer(): st.caption(FOOT)
def friendly(fn):
    try: fn()
    except Exception as e:
        st.error('This page could not be rendered. Run `./train.sh` if model artifacts are missing.')
        with st.expander('Technical details'): st.exception(e)
