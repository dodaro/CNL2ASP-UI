import base64
import uuid
from io import StringIO

import clingo
from cnl2asp.cnl2asp import Cnl2asp
import sys
import streamlit as st
import constants
import json
import dumbo_utils.url as dumbo

height = 400

def init():
    if constants.CNL_STATEMENTS not in st.session_state:
        st.session_state[constants.CNL_STATEMENTS] = None

    if constants.OPTIMIZE not in st.session_state:
        st.session_state[constants.OPTIMIZE] = False

    if constants.JSON not in st.session_state:
        st.session_state[constants.JSON] = False

    if constants.ASP_MODEL not in st.session_state:
        st.session_state[constants.ASP_MODEL] = ""

    if constants.ASP_ENCODING not in st.session_state:
        st.session_state[constants.ASP_ENCODING] = None

    if constants.ERROR not in st.session_state:
        st.session_state[constants.ERROR] = None

    if "cnl" in st.query_params:
        try:
            st.session_state[constants.CNL_STATEMENTS] = base64.b64decode(st.query_params["cnl"]).decode()
        except Exception:
            print("eccezione")
            pass


def reset():
    st.session_state[constants.ASP_ENCODING] = None
    st.session_state[constants.ERROR] = None


def get_asp_encoding(cnl):
    if cnl == "":
        return
    try:
        sys.stdout = exception = StringIO()
        tool = Cnl2asp(cnl)
        if st.session_state[constants.JSON]:
            asp_encoding = json.dumps(tool.cnl_to_json(), indent=4)
        else:
            asp_encoding = tool.compile()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        if str(exception.getvalue()) != "":
            return False, str(exception.getvalue())
        else:
            if st.session_state[constants.OPTIMIZE]:
                asp_encoding = tool.optimize(asp_encoding)
            return True, asp_encoding
    except Exception as e:
        return False, str(e)


def convert_text(cnl):
    if cnl == "":
        return
    reset()

    result, message = get_asp_encoding(cnl)
    if result:
        st.session_state[constants.ASP_ENCODING] = message
        st.toast("Converted", icon=":material/check:")
    else:
        st.session_state[constants.ERROR] = message
        st.toast("Error during conversion", icon=":material/error:")


def upload_file():
    st.session_state.cnl = st.session_state[constants.CNL_STATEMENTS]


def update_optimize():
    st.session_state[constants.OPTIMIZE] = not st.session_state[constants.OPTIMIZE]


def update_json():
    st.session_state[constants.JSON] = not st.session_state[constants.JSON]


def on_model(m):
    st.session_state.answer_set = str(m)


def run_clingo():
    if st.session_state[constants.ASP_ENCODING] is None:
        return
    ctl = clingo.Control()
    ctl.add("base", [], f"{st.session_state[constants.ASP_ENCODING]}")
    ctl.ground([("base", [])])
    ctl.solve(on_model=on_model)


def call_asp_chef():
    if st.session_state[constants.ASP_ENCODING] is None:
        return
    my_dict = {
            "input": [st.session_state[constants.ASP_ENCODING]],
            "encode_input": False,
            "decode_output": False,
            "show_help": True,
            "show_operations": True,
            "show_io_panel": True,
            "show_ingredient_details": True,
            "readonly_ingredients": False,
            "show_ingredient_headers": True,
            "pause_baking": False,
            "recipe": [
                {
                    "id": f"{uuid.uuid4()}",
                    "operation": "Search Models",
                    "options": {
                        "stop": False,
                        "apply": True,
                        "show": True,
                        "readonly": False,
                        "hide_header": False,
                        "height": 400,
                        "rules": "",
                        "number": 1,
                        "raises": True,
                        "input_as_constraints": False,
                        "decode_predicate": "_base64_",
                        "echo_encoded_content": False
                    }
                }
            ]
        }
    return f"https://asp-chef.alviano.net/#{dumbo.compress_object_for_url(my_dict)}"


if __name__ == '__main__':
    init()
    st.set_page_config(layout="wide")
    st.title("CNL2ASP")
    st.divider()
    cnl_column, asp_column = st.columns(2, gap="medium")
    cnl_column.header("CNL")
    if st.session_state[constants.CNL_STATEMENTS] is None:
        cnl_statements = cnl_column.text_area("Insert here your CNL statements", key="cnl", height=height)
    else:
        cnl_statements = cnl_column.text_area("Insert here your CNL statements", key="cnl", value=st.session_state[constants.CNL_STATEMENTS], height=height)
    optimize, my_json, convert = cnl_column.columns(3)
    optimize.toggle(label="Optimize encoding", value=st.session_state[constants.OPTIMIZE],
                    help="Optimize encoding using [ngo](https://github.com/potassco/ngo).", on_change=update_optimize)
    my_json.toggle(label="Json output", value=st.session_state[constants.JSON], help="Output in json format.",
                   on_change=update_json)
    convert.button(label="Convert", on_click=convert_text(cnl_statements))
    expander = cnl_column.expander("Import from file")
    uploaded_file = expander.file_uploader("Choose a CNL file")
    if uploaded_file is not None:
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        string_data = stringio.read()
        st.session_state[constants.CNL_STATEMENTS] = string_data
        expander.button(label="Import", on_click=upload_file)

    asp_column.header("ASP")
    asp_column.markdown("***")
    if st.session_state[constants.ASP_ENCODING] is not None:
        asp_column.code(st.session_state[constants.ASP_ENCODING], language="prolog", line_numbers=True)
        download, asp_chef, run = asp_column.columns(3)
        if st.session_state[constants.JSON]:
            download.download_button("Download", str(st.session_state[constants.ASP_ENCODING]), file_name='output.json')
        else:
            download.download_button("Download", str(st.session_state[constants.ASP_ENCODING]),
                                     file_name='encoding.asp')
            asp_chef.link_button(label="Open in ASP Chef", url=call_asp_chef())
            run.button(label="Run", on_click=run_clingo)
            expander_answer_set = asp_column.expander("Show answer set")
            expander_answer_set.text_area("Answer set", key="answer_set")
            expander_answer_set.download_button("Download", st.session_state.answer_set,
                                                key="download_answer_set", file_name='answer_set.txt')
    elif st.session_state[constants.ERROR] is not None:
        asp_column.error(st.session_state[constants.ERROR])
