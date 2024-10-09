import base64
import zlib
from io import StringIO

import clingo
from cnl2asp.ASP_elements.solver.telingo_result_parser import TelingoResultParser
from cnl2asp.ASP_elements.solver.telingo_wrapper import Telingo
from cnl2asp.cnl2asp import Cnl2asp
import sys
import streamlit as st
import json
import dumbo_utils.url as dumbo
from cnl2asp.utility.utility import Utility

import constants

height = 400


def init():
    if constants.CNL_STATEMENTS not in st.session_state:
        st.session_state[constants.CNL_STATEMENTS] = ""

    if constants.OPTIMIZE not in st.session_state:
        st.session_state[constants.OPTIMIZE] = False

    if constants.RUN_SOLVER not in st.session_state:
        st.session_state[constants.RUN_SOLVER] = False

    if constants.ASP_ENCODING not in st.session_state:
        st.session_state[constants.ASP_ENCODING] = None

    if constants.ERROR not in st.session_state:
        st.session_state[constants.ERROR] = None

    if constants.LINK not in st.session_state:
        st.session_state[constants.LINK] = ""

    if constants.SYMBOLS not in st.session_state:
        st.session_state[constants.SYMBOLS] = []

    if constants.STR_2_SYMBOL not in st.session_state:
        st.session_state[constants.STR_2_SYMBOL] = {}

    if constants.SELECTED_SYMBOLS not in st.session_state:
        st.session_state[constants.SELECTED_SYMBOLS] = []

    if constants.PARSE_RESULT not in st.session_state:
        st.session_state[constants.PARSE_RESULT] = False

    if "cnl" in st.query_params:
        try:
            decompressed = zlib.decompress(base64.b64decode(st.query_params["cnl"].removesuffix("!").replace(" ", "+")))
            json_obj = json.loads(base64.b64decode(decompressed).decode())
            for element in [constants.CNL_STATEMENTS, constants.RUN_SOLVER, constants.OPTIMIZE,
                            constants.SELECTED_SYMBOLS]:
                if element in json_obj:
                    st.session_state[element] = json_obj[element]
            st.query_params.clear()
        except Exception as e:
            pass


def reset():
    st.session_state[constants.ASP_ENCODING] = None
    st.session_state[constants.ERROR] = None


def get_asp_encoding():
    try:
        sys.stdout = exception = StringIO()
        tool = Cnl2asp(st.session_state[constants.CNL_STATEMENTS])
        asp_encoding = tool.compile()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        if str(exception.getvalue()) != "":
            return False, str(exception.getvalue())
        else:
            st.session_state[constants.SYMBOLS] = []
            st.session_state['str_to_symbols'] = {}
            for symbol in tool.get_symbols():
                if symbol.predicate:
                    symbol_string = f"{symbol.predicate}/{len(symbol.attributes)}"
                    st.session_state[constants.SYMBOLS].append(symbol_string)
                    st.session_state[constants.STR_2_SYMBOL][symbol_string] = symbol
            if st.session_state[constants.OPTIMIZE]:
                selected_symbols = [st.session_state[constants.STR_2_SYMBOL][x]
                                    for x in st.session_state[constants.SELECTED_SYMBOLS]]
                asp_encoding = tool.optimize(asp_encoding, selected_symbols)
            return True, asp_encoding
    except Exception as e:
        return False, str(e)


def convert_text():
    if not st.session_state[constants.CNL_STATEMENTS] or st.session_state[constants.CNL_STATEMENTS].strip() == "":
        return
    reset()
    result, message = get_asp_encoding()
    if result:
        st.session_state[constants.ASP_ENCODING] = message
        if st.session_state[constants.RUN_SOLVER]:
            run_telingo()
    else:
        st.session_state[constants.ERROR] = message


def update_run_solver():
    st.session_state[constants.RUN_SOLVER] = not st.session_state[constants.RUN_SOLVER]
    run_solver.toggle = False


def run_telingo():
    if st.session_state[constants.ASP_ENCODING] is None:
        return
    ctl = Telingo()
    to_show = '\n'.join([f"#show {x}." for x in st.session_state[constants.SELECTED_SYMBOLS]])
    ctl.load(st.session_state[constants.ASP_ENCODING] + to_show)
    solve = ctl.solve(120)
    st.session_state.answer_set = solve
    if st.session_state[constants.PARSE_RESULT]:
        st.session_state.answer_set = TelingoResultParser(Cnl2asp(st.session_state[constants.CNL_STATEMENTS]).parse_input()).parse_model(solve)



def generate_shareable_link():
    if st.session_state[constants.CNL_STATEMENTS].strip() == "":
        return
    compressed = dumbo.compress_object_for_url(
        {
            constants.CNL_STATEMENTS: f"{st.session_state[constants.CNL_STATEMENTS]}",
            constants.RUN_SOLVER: st.session_state[constants.RUN_SOLVER],
            constants.OPTIMIZE: st.session_state[constants.OPTIMIZE],
            constants.SELECTED_SYMBOLS: st.session_state[constants.SELECTED_SYMBOLS]
        }
    )
    st.session_state[constants.LINK] = f"https://cnl2asp.streamlit.app/cnl2telui?cnl={compressed}"


def updated_text_area():
    st.session_state[constants.CNL_STATEMENTS] = st.session_state.cnl


def update_print_with_functions():
    Utility.PRINT_WITH_FUNCTIONS = st.session_state.print_fn

def update_parse_result():
    st.session_state[constants.PARSE_RESULT] = not st.session_state[constants.PARSE_RESULT]

init()
st.set_page_config(page_title="CNL2TEL",
                   layout="wide")
st.title("CNL2TEL")

st.divider()
cnl_column, asp_column = st.columns(2, gap="medium")
cnl_column.header("CNL")
cnl_statements = cnl_column.text_area("Insert here your CNL statements", key="cnl", on_change=updated_text_area,
                                      height=height, max_chars=None, value=st.session_state[constants.CNL_STATEMENTS])
run_solver, optimize, convert = cnl_column.columns(3)
run_solver.toggle(label="Run", value=st.session_state[constants.RUN_SOLVER],
                  help="Run telingo with the produced encoding.",
                  on_change=update_run_solver)
run_solver.toggle(label="Print with functions", key='print_fn',
                  help="Print the fields as functions, when the field is itself defined as a concept.",
                  on_change=update_print_with_functions)
run_solver.toggle(label="Parse result", value=st.session_state[constants.PARSE_RESULT],
                  help="Parse the telingo result.",
                  on_change=update_parse_result)
convert_button = convert.button(label="Convert", on_click=convert_text(), help="Convert CNL statements to TELINGO")
selected = cnl_column.multiselect("Filter output", options=st.session_state[constants.SYMBOLS],
                                  default=st.session_state[constants.SELECTED_SYMBOLS])
st.session_state[constants.SELECTED_SYMBOLS] = selected
generate_link, link_area = cnl_column.columns([1, 4])
generate_link.button(label="Generate link", on_click=generate_shareable_link, help="Generate a shareable link to this page")
link_area.code(st.session_state[constants.LINK], line_numbers=False)

with st.form("my-form", clear_on_submit=True):
    uploaded_file = st.file_uploader("Choose a CNL file")
    submitted = st.form_submit_button("Import")
    if submitted and uploaded_file is not None:
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        string_data = stringio.read()
        st.session_state[constants.CNL_STATEMENTS] = string_data
        st.rerun()

asp_column.header("TELINGO")
asp_column.markdown("***")
if st.session_state[constants.ASP_ENCODING] is not None:
    asp_column.code(st.session_state[constants.ASP_ENCODING], language="prolog", line_numbers=True)
    download, asp_chef = asp_column.columns(2)
    download.download_button("Download", str(st.session_state[constants.ASP_ENCODING]),
                             file_name='encoding.asp', help="Download ASP encoding")
    if st.session_state[constants.RUN_SOLVER]:
        asp_column.text_area("Answer set", key="answer_set", height=300)
        asp_column.download_button("Download", st.session_state.answer_set,
                                   file_name="answer_set.txt", help="Download answer set")
elif st.session_state[constants.ERROR] is not None:
    asp_column.error(st.session_state[constants.ERROR])
