import base64
import zlib
from io import StringIO

from asp2cnl.compiler import compile_rule
from asp2cnl.parser import ASPParser
from cnl2asp.cnl2asp import Cnl2asp
import streamlit as st
from gradio_client import Client

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
    st.session_state[constants.LINK] = f"https://cnl2asp.streamlit.app/asp2cnlui?"
    if compressed_definitions is not None and compressed_asp is not None:
        st.session_state[constants.LINK] += f"asp={compressed_asp}&def={compressed_definitions}"
    elif compressed_definitions is not None:
        st.session_state[constants.LINK] += f"def={compressed_definitions}"
    else:
        st.session_state[constants.LINK] += f"asp={compressed_asp}"


def updated_asp_area():
    st.session_state[constants.ASP_ENCODING] = st.session_state.asp
    st.session_state[constants.ERROR] = None


def updated_definitions():
    st.session_state[constants.DEFINITIONS] = st.session_state.definitions


def call_qwen_llm():
    client = Client("Qwen/Qwen2-72B-Instruct")
    result = client.predict(
        query=f"{st.session_state[constants.CNL_STATEMENTS]}",
        history=[],
        system="Explain the problem provided improving the writing style",
        api_name="/model_chat"
    )
    st.session_state[constants.CNL_STATEMENTS] = result[1][0][1]


def read_asp_file():
    stringio = StringIO(st.session_state.asp_upleader.getvalue().decode("utf-8"))
    string_data = stringio.read()
    st.session_state[constants.ASP_ENCODING] = string_data


def read_definitions_file():
    stringio = StringIO(st.session_state.definitions_uploader.getvalue().decode("utf-8"))
    string_data = stringio.read()
    st.session_state[constants.DEFINITIONS] = string_data


init()
st.set_page_config(page_title="ASP2CNL",
                   layout="wide")
st.title("ASP2CNL")

st.divider()
asp_column, res_column = st.columns(2, gap="medium")
definition_title, import_definitions = asp_column.columns(2)
import_definitions.file_uploader("Upload definitions", key='definitions_uploader', on_change=read_definitions_file)
definition_title.header("DEFINITIONS")
asp_column.text_area("Insert here your definitions", key="definitions", on_change=updated_definitions,
                     height=int(height / 2), max_chars=None, value=st.session_state[constants.DEFINITIONS])

asp_title, import_asp = asp_column.columns(2)
asp_title.header("ASP")
import_asp.file_uploader("Upload ASP encoding", key='asp_upleader', on_change=read_asp_file)

asp_column.text_area("Insert here your ASP encoding", key="asp", on_change=updated_asp_area,
                     height=height, max_chars=None, value=st.session_state[constants.ASP_ENCODING])
asp_column.button(label="Convert", on_click=convert_asp)

generate_link, link_area = asp_column.columns([1, 4])
generate_link.button(label="Generate link", on_click=generate_shareable_link)
link_area.code(st.session_state[constants.LINK], line_numbers=False)

res_column.header("CNL")
if st.session_state[constants.CNL_STATEMENTS] is not None:
    st.markdown('''<style> code {
              white-space : pre-wrap !important;
            } </style>''', unsafe_allow_html=True)
    res_column.code(st.session_state[constants.CNL_STATEMENTS], language='markdown')
    download, improve = res_column.columns(2)
    download.download_button("Download", str(st.session_state[constants.CNL_STATEMENTS]),
                             file_name='cnl.txt')
    improve.button(label='Improve', on_click=call_qwen_llm)
elif st.session_state[constants.ERROR] is not None:
    res_column.error(st.session_state[constants.ERROR])
