import streamlit as st

pg = st.navigation([st.Page("pages/cnl2aspui.py", title="CNL2ASP"), st.Page("pages/asp2cnlui.py", title="ASP2CNL")])
pg.run()
