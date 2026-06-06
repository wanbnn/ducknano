# -*- coding: utf-8 -*-
from ducknano.terminal_gui import TerminalGUI, terminal_gui


def provider_name() -> str:
    return terminal_gui.provider_name()


def masked_api_key() -> str:
    return terminal_gui.masked_api_key()


def render_dashboard(hist_enabled: bool = False, rag_status: str = ""):
    return terminal_gui.render_dashboard(hist_enabled=hist_enabled, rag_status=rag_status)


def render_intro(hist_enabled: bool = False, rag_status: str = ""):
    return terminal_gui.render_intro(hist_enabled=hist_enabled, rag_status=rag_status)


def render_home(hist_enabled: bool = False, rag_status: str = ""):
    return terminal_gui.render_home(hist_enabled=hist_enabled, rag_status=rag_status)


def render_shortcuts():
    return terminal_gui.render_shortcuts()


def prompt_markup() -> str:
    return terminal_gui.prompt_markup()


def read_user_input() -> str:
    return terminal_gui.read_user_input()


def render_saved_provider():
    return terminal_gui.render_saved_provider()


def run_provider_setup(harness=None, load_models=None):
    return terminal_gui.run_provider_setup(harness=harness, load_models=load_models)


def render_error(message: str):
    return terminal_gui.render_error(message)
