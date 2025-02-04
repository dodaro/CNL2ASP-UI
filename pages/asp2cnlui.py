import base64
import zlib
from io import StringIO

from asp2cnl.compiler import compile_rule
from asp2cnl.parser import ASPParser
from cnl2asp.cnl2asp import Cnl2asp
import streamlit as st
from groq import Groq

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


def call_groq_llm():
    try:
        client = Groq(
            api_key=st.secrets["groq_api_key"],
        )
        result = client.chat.completions.create(
            #
            # Required parameters
            #
            messages=[
                # Set an optional system message. This sets the behavior of the
                # assistant and can be used to provide specific instructions for
                # how it should behave throughout the conversation.
                {
                    "role": "system",
                    "content": "You are a helpful assistant which explains the problems provided improving the writing style and clarity.\n"
                               "In your response I just want the rewritten text."
                },
                # Set a user message for the assistant to respond to.
                {
                    "role": "user",
                    "content": f"{st.session_state[constants.CNL_STATEMENTS]}",
                }
            ],

            # The language model which will generate the completion.
            model="llama-3.3-70b-versatile",

            #
            # Optional parameters
            #

            # Controls randomness: lowering results in less random completions.
            # As the temperature approaches zero, the model will become deterministic
            # and repetitive.
            temperature=0.5,

            # The maximum number of tokens to generate. Requests can use up to
            # 32,768 tokens shared between prompt and completion.
            max_completion_tokens=1024,

            # Controls diversity via nucleus sampling: 0.5 means half of all
            # likelihood-weighted options are considered.
            top_p=1,

            # A stop sequence is a predefined or user-specified text string that
            # signals an AI to stop generating content, ensuring its responses
            # remain focused and concise. Examples include punctuation marks and
            # markers like "[end]".
            stop=None,

            # If set, partial message deltas will be sent.
            stream=False,
        )
        st.session_state[constants.CNL_STATEMENTS] = result.choices[0].message.content
    except:
        st.session_state[constants.CNL_STATEMENTS] = None
        st.session_state[constants.ERROR] = 'Could not contact the server, please try again later.'


def read_asp_file():
    if st.session_state.asp_uploader is not None:
        stringio = StringIO(st.session_state.asp_uploader.getvalue().decode("utf-8"))
        string_data = stringio.read()
        st.session_state[constants.ASP_ENCODING] = string_data


def read_definitions_file():
    if st.session_state.definitions_uploader is not None:
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
import_definitions.file_uploader("Upload concept definitions", key='definitions_uploader', on_change=read_definitions_file)
definition_title.header("CNL Concepts")
asp_column.text_area("Insert here the concept definitions", key="definitions", on_change=updated_definitions,
                     height=int(height / 2), max_chars=None, value=st.session_state[constants.DEFINITIONS], placeholder="A movie is identified by an id, and has a name, and a duration.")

asp_title, import_asp = asp_column.columns(2)
asp_title.header("ASP")
import_asp.file_uploader("Upload ASP encoding", key='asp_uploader', on_change=read_asp_file)

asp_column.text_area("Insert here your ASP encoding", key="asp", on_change=updated_asp_area,
                     height=height, max_chars=None, value=st.session_state[constants.ASP_ENCODING],
                     placeholder="movie(1, \"Forrest Gump\", 142).")
asp_column.button(label="Convert", on_click=convert_asp, help="Convert ASP rules to CNL")

generate_link, link_area = asp_column.columns([1, 4])
generate_link.button(label="Generate link", on_click=generate_shareable_link, help="Generate a shareable link to this page")
link_area.code(st.session_state[constants.LINK], line_numbers=False)

res_column.header("CNL")
if st.session_state[constants.CNL_STATEMENTS] is not None:
    st.markdown('''<style> code {
              white-space : pre-wrap !important;
            } </style>''', unsafe_allow_html=True)
    res_column.code(st.session_state[constants.CNL_STATEMENTS], language='markdown')
    download, improve = res_column.columns(2)
    download.download_button("Download", str(st.session_state[constants.CNL_STATEMENTS]),
                             file_name='cnl.txt', help="Download result")
    improve.button(label='Improve Clarity', on_click=call_groq_llm, help="Improve clarity of CNL by calling an external LLM. Note: This might generate inaccurate results!")
elif st.session_state[constants.ERROR] is not None:
    res_column.error(st.session_state[constants.ERROR])
