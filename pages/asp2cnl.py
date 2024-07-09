import base64
import os.path
import zlib

from asp2cnl.compiler import compile_rule
from asp2cnl.parser import ASPParser
from cnl2asp.cnl2asp import Cnl2asp
import streamlit as st
import constants
import json
import dumbo_utils.url as dumbo

height = 400


def init():
    if constants.DEFINITIONS not in st.session_state:
        st.session_state[constants.DEFINITIONS] = ''

    if constants.ASP_ENCODING not in st.session_state:
        st.session_state[constants.ASP_ENCODING] = ''

    if constants.CNL_STATEMENTS not in st.session_state:
        st.session_state[constants.CNL_STATEMENTS] = None

    if constants.ERROR not in st.session_state:
        st.session_state[constants.ERROR] = None

    if constants.LINK not in st.session_state:
        st.session_state[constants.LINK] = ""

    if "asp" in st.query_params:
        try:
            decompressed = zlib.decompress(base64.b64decode(st.query_params["asp"].removesuffix("!").replace(" ", "+")))
            json_obj = json.loads(base64.b64decode(decompressed).decode())
            for element in [constants.ASP_ENCODING]:
                if element in json_obj:
                    st.session_state[element] = json_obj[element]
        except Exception as e:
            pass

    if "def" in st.query_params:
        try:
            decompressed = zlib.decompress(base64.b64decode(st.query_params["def"].removesuffix("!").replace(" ", "+")))
            json_obj = json.loads(base64.b64decode(decompressed).decode())
            for element in [constants.DEFINITIONS]:
                if element in json_obj:
                    st.session_state[element] = json_obj[element]
        except Exception as e:
            pass
    st.query_params.clear()


def reset():
    st.session_state[constants.CNL_STATEMENTS] = None
    st.session_state[constants.ERROR] = None


def get_cnl():
    try:
        cnl = ''
        symbols = Cnl2asp(st.session_state[constants.DEFINITIONS]).get_symbols()
        encoding = ASPParser(st.session_state[constants.ASP_ENCODING]).parse()
        i = 0
        for rule in encoding:
            cnl += f'{compile_rule(rule, symbols)}\n'
            i += 1
        return True, cnl
    except Exception as e:
        return False, str(e)


def convert_asp():
    if not st.session_state[constants.ASP_ENCODING] or \
            st.session_state[constants.ASP_ENCODING].strip() == "":
        return
    reset()
    result, message = get_cnl()
    if result:
        st.session_state[constants.CNL_STATEMENTS] = message
    else:
        st.session_state[constants.ERROR] = message


def generate_shareable_link():
    if st.session_state[constants.ASP_ENCODING].strip() == "" and st.session_state[constants.DEFINITIONS].strip() == "":
        return
    compressed_definitions = None
    compressed_asp = None
    if st.session_state[constants.DEFINITIONS].strip() != "":
        compressed_definitions = dumbo.compress_object_for_url(
            {
                constants.DEFINITIONS: f"{st.session_state[constants.DEFINITIONS]}",
            }
        )
    if st.session_state[constants.ASP_ENCODING]:
        compressed_asp = dumbo.compress_object_for_url(
            {
                constants.ASP_ENCODING: f"{st.session_state[constants.ASP_ENCODING]}",
            }
        )
    st.session_state[constants.LINK] = f"https://cnl2asp.streamlit.app/asp2cnl?"
    if compressed_definitions is not None and compressed_asp is not None:
        st.session_state[constants.LINK] += f"asp={compressed_asp}&def={compressed_definitions}"
    elif compressed_definitions is not None:
        st.session_state[constants.LINK] += f"def={compressed_definitions}"
    else:
        st.session_state[constants.LINK] += f"asp={compressed_asp}"


def updated_asp_area():
    st.session_state[constants.ASP_ENCODING] = st.session_state.asp


def updated_definitions():
    st.session_state[constants.DEFINITIONS] = st.session_state.definitions


init()
st.set_page_config(page_title="asp2nl",
                   layout="wide")
CNL2ASP_button, ASP2NL_button, _ = col1, col2, col3 = st.columns([1, 1, 10])
if CNL2ASP_button.button('CNL2ASP'):
    st.switch_page(os.path.join('pages', 'cnl2asp.py'))
ASP2NL_button.button('ASP2NL', disabled=True)
st.title("ASP2CNL")

st.divider()
asp_column, res_column = st.columns(2, gap="medium")
definition_title, import_definitions = asp_column.columns(2)
file_definitions = import_definitions.file_uploader("Upload definitions")
if file_definitions:
    st.session_state[constants.DEFINITIONS] = file_definitions.read()
definition_title.header("DEFINITIONS")
asp_column.text_area("Insert here your definitions", key="definitions", on_change=updated_definitions,
                     height=int(height / 2), max_chars=None, value=st.session_state[constants.DEFINITIONS])

asp_title, import_asp = asp_column.columns(2)
asp_title.header("ASP")
file_asp_encoding = import_asp.file_uploader("Upload ASP encoding")
if file_asp_encoding:
    st.session_state[constants.ASP_ENCODING] = file_asp_encoding.read()
asp_column.text_area("Insert here your ASP encoding", key="asp", on_change=updated_asp_area,
                     height=height, max_chars=None, value=st.session_state[constants.ASP_ENCODING])
asp_column.button(label="Convert", on_click=convert_asp())

generate_link, link_area = asp_column.columns([1, 4])
generate_link.button(label="Generate link", on_click=generate_shareable_link)
link_area.code(st.session_state[constants.LINK], line_numbers=False)

res_column.header("CNL")
if st.session_state[constants.CNL_STATEMENTS] is not None:
    res_column.code(st.session_state[constants.CNL_STATEMENTS], language='markdown')
    download = res_column.columns(1)[0]
    download.download_button("Download", str(st.session_state[constants.CNL_STATEMENTS]),
                             file_name='cnl.txt')
elif st.session_state[constants.ERROR] is not None:
    res_column.error(st.session_state[constants.ERROR])
