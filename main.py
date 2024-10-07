import streamlit as st
import streamlit.components.v1 as components


def documentation():
    st.set_page_config(page_title="Documentation",
                       layout="wide")
    iframe_src = "https://dodaro.github.io/cnl2asp"
    components.iframe(iframe_src, height=800, scrolling=True)


pg = st.navigation([
    st.Page("pages/cnl2aspui.py", title="CNL2ASP"),
    st.Page("pages/asp2cnlui.py", title="ASP2CNL"),
    st.Page("pages/cnl2telui.py", title="CNL2TEL"),
    st.Page(documentation, title="Documentation"),
    ]
)
pg.run()
