import base64
import uuid
import zlib
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
        st.session_state[constants.CNL_STATEMENTS] = ""

    if constants.OPTIMIZE not in st.session_state:
        st.session_state[constants.OPTIMIZE] = False

    if constants.JSON not in st.session_state:
        st.session_state[constants.JSON] = False

    if constants.RUN_SOLVER not in st.session_state:
        st.session_state[constants.RUN_SOLVER] = False

    if constants.ASP_ENCODING not in st.session_state:
        st.session_state[constants.ASP_ENCODING] = None

    if constants.ANSWER_SET not in st.session_state:
        st.session_state[constants.ANSWER_SET] = ""

    if constants.ERROR not in st.session_state:
        st.session_state[constants.ERROR] = None

    if constants.LINK not in st.session_state:
        st.session_state[constants.LINK] = ""

    if "cnl" in st.query_params:
        try:
            decompressed = zlib.decompress(base64.b64decode(st.query_params["cnl"].removesuffix("!").replace(" ", "+")))
            json_obj = json.loads(base64.b64decode(decompressed).decode())
            if "cnl_statements" in json_obj:
                st.session_state[constants.CNL_STATEMENTS] = json_obj["cnl_statements"]
        except Exception as e:
            pass


def reset():
    st.session_state[constants.ASP_ENCODING] = None
    st.session_state[constants.ERROR] = None
    st.session_state[constants.ANSWER_SET] = ""


def get_asp_encoding():
    try:
        sys.stdout = exception = StringIO()
        tool = Cnl2asp(st.session_state[constants.CNL_STATEMENTS])
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


def convert_text():
    if st.session_state[constants.CNL_STATEMENTS].strip() == "":
        return
    reset()
    result, message = get_asp_encoding()
    if result:
        st.session_state[constants.ASP_ENCODING] = message
        if st.session_state[constants.RUN_SOLVER]:
            run_clingo()
    else:
        st.session_state[constants.ERROR] = message


def update_optimize():
    st.session_state[constants.OPTIMIZE] = not st.session_state[constants.OPTIMIZE]
    st.session_state[constants.JSON] = False
    optimize.toggle = False


def update_json():
    st.session_state[constants.JSON] = not st.session_state[constants.JSON]
    st.session_state[constants.OPTIMIZE] = False
    st.session_state[constants.RUN_SOLVER] = False
    my_json.toggle = False


def update_run_solver():
    st.session_state[constants.RUN_SOLVER] = not st.session_state[constants.RUN_SOLVER]
    st.session_state[constants.JSON] = False
    run_solver.toggle = False


def on_model(m):
    st.session_state[constants.ANSWER_SET] = str(m)


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


def generate_shareable_link():
    if st.session_state[constants.CNL_STATEMENTS].strip() == "":
        return
    compressed = dumbo.compress_object_for_url({"cnl_statements": f"{st.session_state[constants.CNL_STATEMENTS]}"})
    st.session_state[constants.LINK] = f"https://cnl2asp.streamlit.app?cnl={compressed}"


def updated_text_area():
    st.session_state[constants.CNL_STATEMENTS] = st.session_state.cnl


if __name__ == '__main__':
    init()
    st.set_page_config(layout="wide")
    st.title("CNL2ASP")
    st.divider()
    cnl_column, asp_column = st.columns(2, gap="medium")
    cnl_column.header("CNL")
    cnl_statements = cnl_column.text_area("Insert here your CNL statements", key="cnl", on_change=updated_text_area,
                                          height=height, max_chars=None, value=st.session_state[constants.CNL_STATEMENTS])
    run_solver, optimize, my_json, convert = cnl_column.columns(4)
    run_solver.toggle(label="Run", value=st.session_state[constants.RUN_SOLVER],
                      help="Run clingo the produced encoding.",
                      on_change=update_run_solver)
    optimize.toggle(label="Optimize", value=st.session_state[constants.OPTIMIZE],
                    help="Optimize encoding using [ngo](https://github.com/potassco/ngo).", on_change=update_optimize)
    my_json.toggle(label="Json", value=st.session_state[constants.JSON], help="Output in json format.",
                   on_change=update_json)
    convert_button = convert.button(label="Convert", on_click=convert_text())
    generate_link, link_area = cnl_column.columns([1, 4])
    generate_link.button(label="Generate link", on_click=generate_shareable_link)
    link_area.code(st.session_state[constants.LINK], line_numbers=False)
    # with st.expander("Upload from file"):
    with st.form("my-form", clear_on_submit=True):
        uploaded_file = st.file_uploader("Choose a CNL file")
        submitted = st.form_submit_button("Import")
        if submitted and uploaded_file is not None:
            stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
            string_data = stringio.read()
            st.session_state[constants.CNL_STATEMENTS] = string_data
            st.rerun()

    asp_column.header("ASP")
    asp_column.markdown("***")
    if st.session_state[constants.ASP_ENCODING] is not None:
        asp_column.code(st.session_state[constants.ASP_ENCODING], language="prolog", line_numbers=True)
        download, asp_chef = asp_column.columns(2)
        if st.session_state[constants.JSON]:
            download.download_button("Download", str(st.session_state[constants.ASP_ENCODING]), file_name="output.json")
        else:
            download.download_button("Download", str(st.session_state[constants.ASP_ENCODING]),
                                     file_name='encoding.asp')
            asp_chef.link_button(label="Open in ASP Chef", url=call_asp_chef())
            if st.session_stateπ
            expander_answer_set = asp_column.expander("Show answer set",
                                                      expanded=st.session_state[constants.ANSWER_SET] != "")
            expander_answer_set.text_area("Answer set", key="answer_set")
            expander_answer_set.download_button("Download", st.session_state[constants.ANSWER_SET],
                                                key="download_answer_set", file_name="answer_set.txt")
    elif st.session_state[constants.ERROR] is not None:
        asp_column.error(st.session_state[constants.ERROR])
