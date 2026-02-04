#!/usr/bin/env python3
"""
Apple Health Analyzer GUI

A graphical user interface for analyzing Apple Health data.
"""

import os
import uuid
import sys

from nicegui import ui, app

from app_state import state
from assets import APP_ICON_BASE64

from ui.layout import render_left_drawer
from ui.layout import render_header
from ui.layout import render_body


def main() -> None:
    """Main entry point for the application."""

    render_header()
    render_left_drawer()
    render_body()

    with ui.footer():
        state.log = ui.log(max_lines=10).classes("w-full h-20")

    app.add_static_files("/resources", "resources")
    ui.add_head_html('<link rel="stylesheet" href="/resources/style.css">', shared=True)


if __name__ in {"__main__", "__mp_main__"}:
    secret = (
        uuid.uuid4().hex
        if "pytest" in sys.modules
        else os.getenv("STORAGE_SECRET", "secret")
    )

    ui.run(  # type: ignore[misc]
        main,
        title="Apple Health Analyzer",
        favicon=APP_ICON_BASE64,
        storage_secret=secret,
        uvicorn_reload_includes="resources/**,src/**",
        uvicorn_reload_excludes="tests/**",
    )
